#!/usr/bin/env python3
"""Scale the frontier reviewer (Claude, headless) to the full Verified set (388 packets:
194 agent + 194 gold) so it is on the same footing as the open models (n=194 each).

Pre-seeds from the 40 already-reviewed human-subset packets. Resumable; modest concurrency.
Output: data/llm_reviews/verified/reviewer-claude-frontier/<pid>.json
"""
from __future__ import annotations
import os
import importlib.util
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
OUT = ROOT / "data/llm_reviews/verified/reviewer-claude-frontier"
SEED = ROOT / "data/llm_reviews/human_subset/reviewer-claude-frontier"

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
    for attempt in range(2):
        try:
            r = subprocess.run([CLAUDE, "-p", prompt, "--output-format", "text"],
                               capture_output=True, text=True, timeout=180, cwd="/tmp",
                               stdin=subprocess.DEVNULL)
            if r.stdout.strip():
                return r.stdout.strip()
        except Exception:  # noqa: BLE001
            pass
    return "__ERR__"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # pre-seed the 40 already done
    seeded = 0
    if SEED.exists():
        for f in SEED.glob("pk_*.json"):
            dst = OUT / f.name
            if not dst.exists():
                shutil.copy(f, dst)
                seeded += 1
    packets = [json.loads(l) for l in (ROOT / "data/review_packets/verified/packets.jsonl")
               .read_text().splitlines() if l.strip()]
    todo = [p for p in packets if not (OUT / f"{p['packet_id']}.json").exists()]
    print(f"verified frontier: total={len(packets)} seeded={seeded} todo={len(todo)}", flush=True)

    lock = threading.Lock()
    done = [0]

    def work(p):
        raw = call(build_prompt(p))
        v = m.parse_verdict(raw)
        out = (m.normalize(v) if v else
               {"error": raw[:200], "mergeable": None, "merge_decision": "error", "issues": []})
        out["packet_id"] = p["packet_id"]
        (OUT / f"{p['packet_id']}.json").write_text(json.dumps(out))
        with lock:
            done[0] += 1
            if done[0] % 20 == 0:
                print(f"  {done[0]}/{len(todo)}", flush=True)

    with ThreadPoolExecutor(max_workers=2) as ex:
        for _ in as_completed([ex.submit(work, p) for p in todo]):
            pass
    errs = sum(1 for p in packets
               if json.loads((OUT / f"{p['packet_id']}.json").read_text()).get("error"))
    print(f"done. errors={errs}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
