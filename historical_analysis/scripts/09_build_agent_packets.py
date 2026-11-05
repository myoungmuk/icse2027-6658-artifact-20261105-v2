#!/usr/bin/env python3
"""Build blind packets for the extra agents (verified). Agent packets are namespaced
per agent under data/review_packets/agents/<key>/; gold packets are shared (one set,
deduped by instance) under data/review_packets/agents/_gold/ so gold is reviewed once.
"""
from __future__ import annotations
import hashlib
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INST = ROOT / "data/swebench_instances/verified.jsonl"
AGDIR = ROOT / "data/raw/agents"
RES = ROOT / "data/swebench_results"
OUT = ROOT / "data/review_packets/agents"
AGENTS = ["rag-gpt4", "sweagent-claude35", "openhands-codeact"]
DIFF_FILE_RE = re.compile(r"^diff --git a/(\S+) b/(\S+)", re.M)


def changed_files(d): return sorted({m.group(2) for m in DIFF_FILE_RE.finditer(d or "")})
def stats(d):
    a = sum(1 for l in (d or "").splitlines() if l.startswith("+") and not l.startswith("+++"))
    r = sum(1 for l in (d or "").splitlines() if l.startswith("-") and not l.startswith("---"))
    return {"added_lines": a, "removed_lines": r}
def jl(p): return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def make_packet(pid, inst, diff):
    return {"packet_id": pid, "repo": inst.get("repo"), "base_commit": inst.get("base_commit"),
            "issue_text": inst.get("problem_statement") or "", "changed_files": changed_files(diff),
            "diff_stats": stats(diff), "diff": diff}


def main() -> int:
    instances = {r["instance_id"]: r for r in jl(INST)}
    rng = random.Random(42)
    gold_needed = {}

    for key in AGENTS:
        preds = {r["instance_id"]: r["model_patch"] for r in jl(AGDIR / key / "all_preds.jsonl")}
        resolved = json.load(open(RES / f"{key}_resolved.json"))["resolved_ids"]
        packets, akey = [], []
        for iid in resolved:
            inst = instances.get(iid)
            diff = preds.get(iid, "")
            if not inst or not diff.strip():
                continue
            pid = "pa_" + hashlib.sha1(f"{key}|{iid}".encode()).hexdigest()[:12]
            packets.append(make_packet(pid, inst, diff))
            akey.append({"packet_id": pid, "split": "verified", "instance_id": iid,
                         "candidate_source": "agent", "agent": key, "resolved": True})
            gold_needed[iid] = inst
        rng.shuffle(packets)
        d = OUT / key
        d.mkdir(parents=True, exist_ok=True)
        (d / "packets.jsonl").write_text("\n".join(json.dumps(p) for p in packets) + "\n")
        (d / "packets_key.json").write_text(json.dumps(akey, indent=2))
        print(f"{key}: {len(packets)} agent packets")

    # shared gold set (union of all agents' resolved instances)
    gpackets, gkey = [], []
    for iid, inst in gold_needed.items():
        diff = inst.get("patch") or ""
        if not diff.strip():
            continue
        pid = "pg_" + hashlib.sha1(iid.encode()).hexdigest()[:12]
        gpackets.append(make_packet(pid, inst, diff))
        gkey.append({"packet_id": pid, "split": "verified", "instance_id": iid,
                     "candidate_source": "gold", "agent": "_gold", "resolved": True})
    rng.shuffle(gpackets)
    gd = OUT / "_gold"
    gd.mkdir(parents=True, exist_ok=True)
    (gd / "packets.jsonl").write_text("\n".join(json.dumps(p) for p in gpackets) + "\n")
    (gd / "packets_key.json").write_text(json.dumps(gkey, indent=2))
    print(f"_gold (shared): {len(gpackets)} packets over {len(gold_needed)} instances")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
