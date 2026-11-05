#!/usr/bin/env python3
"""Phase 2: build blind, PR-like review packets from test-passing patches.

For every instance that the agent RESOLVED (test-passing per the official harness),
emit two blind review packets:
  - candidate_source = "agent": the agent's patch (Agentless-1.5 / GPT-4o)
  - candidate_source = "gold":  the developer-merged patch (positive control)

Reviewer-visible packet content = issue text + repo/base_commit + the unified diff +
parsed changed-file list. It NEVER contains: the gold patch alongside the agent patch,
the test_patch, hints_text, or any provenance marker (leakage / blinding policy).

The source label lives only in a separate keyfile (packets_key.json), so the reviewer
stage is blind. Packet ordering is shuffled with a fixed seed.

Usage
-----
    python scripts/02_build_packets.py --splits lite verified
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INST_DIR = ROOT / "data" / "swebench_instances"
RES_DIR = ROOT / "data" / "swebench_results"
PRED = {
    "lite": ROOT / "data/raw/agentless/agentless_swebench_lite/agentless_swebench_lite/all_preds.jsonl",
    "verified": ROOT / "data/raw/agentless/agentless_swebench_verified/agentless_swebench_verified/all_preds.jsonl",
}
OUT_DIR = ROOT / "data" / "review_packets"

DIFF_FILE_RE = re.compile(r"^diff --git a/(\S+) b/(\S+)", re.M)


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def changed_files(diff: str) -> list[str]:
    files = []
    for m in DIFF_FILE_RE.finditer(diff or ""):
        files.append(m.group(2))
    return sorted(set(files))


def diff_stats(diff: str) -> dict:
    add = sum(1 for l in (diff or "").splitlines() if l.startswith("+") and not l.startswith("+++"))
    rem = sum(1 for l in (diff or "").splitlines() if l.startswith("-") and not l.startswith("---"))
    return {"added_lines": add, "removed_lines": rem}


def packet_id(split: str, iid: str, source: str) -> str:
    h = hashlib.sha1(f"{split}|{iid}|{source}".encode()).hexdigest()[:12]
    return f"pk_{h}"


def build(split: str) -> tuple[list[dict], list[dict]]:
    instances = {r["instance_id"]: r for r in load_jsonl(INST_DIR / f"{split}.jsonl")}
    preds = {r["instance_id"]: r for r in load_jsonl(PRED[split])}
    resolved = json.loads((RES_DIR / f"{split}_resolved.json").read_text())["resolved_ids"]

    packets, key = [], []
    for iid in sorted(resolved):
        inst = instances.get(iid)
        if inst is None:
            continue
        agent_patch = (preds.get(iid) or {}).get("model_patch") or ""
        gold_patch = inst.get("patch") or ""
        for source, diff in (("agent", agent_patch), ("gold", gold_patch)):
            if not diff.strip():
                continue
            pid = packet_id(split, iid, source)
            packets.append({
                "packet_id": pid,
                "repo": inst.get("repo"),
                "base_commit": inst.get("base_commit"),
                "issue_text": inst.get("problem_statement") or "",
                "changed_files": changed_files(diff),
                "diff_stats": diff_stats(diff),
                "diff": diff,
            })
            key.append({
                "packet_id": pid, "split": split, "instance_id": iid,
                "candidate_source": source, "resolved": True,
            })
    return packets, key


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", nargs="+", default=["lite", "verified"],
                    choices=["lite", "verified"])
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    for split in args.splits:
        packets, key = build(split)
        rng.shuffle(packets)
        out = OUT_DIR / split
        out.mkdir(parents=True, exist_ok=True)
        (out / "packets.jsonl").write_text(
            "\n".join(json.dumps(p) for p in packets) + "\n")
        (out / "packets_key.json").write_text(json.dumps(key, indent=2))
        n_agent = sum(1 for k in key if k["candidate_source"] == "agent")
        n_gold = sum(1 for k in key if k["candidate_source"] == "gold")
        print(f"[{split}] packets={len(packets)}  agent={n_agent}  gold={n_gold}  -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
