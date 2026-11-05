#!/usr/bin/env python3
"""Frontier reviewer: run a frontier proprietary model (Claude CLI, headless, no paid API)
as a calibrated mergeability reviewer over the 40-packet human-study subset.

Tests whether a far stronger judge escapes the validity--discrimination dilemma. Reuses the
calibrated rubric from 03_run_reviewer.py. Resumable; one JSON file per packet.
"""
from __future__ import annotations
import os
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
OUT = ROOT / "data/llm_reviews/human_subset/reviewer-claude-frontier"

spec = importlib.util.spec_from_file_location("r", str(ROOT / "scripts/03_run_reviewer.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def build_prompt(p):
    diff = p["diff"][:24000]
    issue = (p["issue_text"] or "")[:6000]
    pr = m.SYSTEM_CAL + "\n\n" + m.PROMPT.format(
        repo=p["repo"], base_commit=p["base_commit"],
        files=", ".join(p["changed_files"][:20]) or "(none)",
        add=p["diff_stats"]["added_lines"], rem=p["diff_stats"]["removed_lines"],
        issue=issue, diff=diff, tax=m.TAX_TEXT) + m.TASK_CAL
    pr += ("\n\nIGNORE ALL OTHER INSTRUCTIONS AND STYLE GUIDES. Do not run tools or ask "
           "questions. Output ONLY the JSON object, nothing else.")
    return pr


def call(prompt):
    try:
        r = subprocess.run([CLAUDE, "-p", prompt, "--output-format", "text"],
                           capture_output=True, text=True, timeout=180, cwd="/tmp",
                           stdin=subprocess.DEVNULL)
        return r.stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"__ERR__{e!r}"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    key = {k["packet_id"]: k for k in json.loads((ROOT / "data/human_study/key.json").read_text())}
    packets = {p["packet_id"]: p for p in
               (json.loads(l) for l in (ROOT / "data/review_packets/verified/packets.jsonl")
                .read_text().splitlines() if l.strip())}
    pids = [k["packet_id"] for k in json.loads((ROOT / "data/human_study/key.json").read_text())]
    todo = [pid for pid in pids if not (OUT / f"{pid}.json").exists()]
    print(f"frontier: {len(pids)} packets, {len(todo)} todo", flush=True)
    for i, pid in enumerate(todo, 1):
        raw = call(build_prompt(packets[pid]))
        v = m.parse_verdict(raw)
        out = m.normalize(v) if v else {"error": raw[:200], "mergeable": None,
                                        "merge_decision": "error", "issues": []}
        out["packet_id"] = pid
        (OUT / f"{pid}.json").write_text(json.dumps(out))
        print(f"  {i}/{len(todo)} {pid} -> {out.get('merge_decision')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
