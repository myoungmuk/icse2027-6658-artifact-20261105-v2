#!/usr/bin/env python3
"""Negative control: build blind packets for Agentless-verified patches that FAILED the
official harness (test-failing = did not satisfy FAIL_TO_PASS). These are known-worse,
"plausible but incorrect" patches. A valid, discriminating reviewer should reject them
MORE than developer-merged gold; if calibrated reviewers accept them at ~the gold rate,
that is direct evidence of false acceptance (the gold positive control bounds only false
rejection). Same packet format/pipeline as 02, so they are on equal footing with the
resolved-agent and gold packets already reviewed.

Output:
  data/review_packets/verified_negctrl/packets.jsonl
  data/review_packets/verified_negctrl/packets_key.json   (candidate_source="agent_failing")
"""
from __future__ import annotations
import importlib.util
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("b", str(ROOT / "scripts/02_build_packets.py"))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

INST = ROOT / "data/swebench_instances/verified.jsonl"
PRED = ROOT / "data/raw/agentless/agentless_swebench_verified/agentless_swebench_verified/all_preds.jsonl"
RESOLVED = ROOT / "data/swebench_results/verified_resolved.json"
OUT = ROOT / "data/review_packets/verified_negctrl"


def main() -> int:
    instances = {r["instance_id"]: r for r in b.load_jsonl(INST)}
    preds = {r["instance_id"]: r for r in b.load_jsonl(PRED)}
    resolved = set(json.loads(RESOLVED.read_text())["resolved_ids"])
    nonres = sorted(i for i in preds if i not in resolved)

    packets, key = [], []
    for iid in nonres:
        inst = instances.get(iid)
        if inst is None:
            continue
        diff = (preds.get(iid) or {}).get("model_patch") or ""
        if not diff.strip():
            continue
        pid = b.packet_id("verified_negctrl", iid, "agent_failing")
        packets.append({
            "packet_id": pid,
            "repo": inst.get("repo"),
            "base_commit": inst.get("base_commit"),
            "issue_text": inst.get("problem_statement") or "",
            "changed_files": b.changed_files(diff),
            "diff_stats": b.diff_stats(diff),
            "diff": diff,
        })
        key.append({"packet_id": pid, "split": "verified_negctrl",
                    "instance_id": iid, "candidate_source": "agent_failing",
                    "resolved": False})

    # deterministic shuffle (fixed seed), same convention as 02
    rng = random.Random(1234)
    idx = list(range(len(packets)))
    rng.shuffle(idx)
    packets = [packets[i] for i in idx]
    key = [key[i] for i in idx]

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "packets.jsonl").write_text("\n".join(json.dumps(p) for p in packets) + "\n")
    (OUT / "packets_key.json").write_text(json.dumps(key, indent=2))
    print(f"negctrl packets: {len(packets)} test-failing (non-resolved) Agentless-verified patches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
