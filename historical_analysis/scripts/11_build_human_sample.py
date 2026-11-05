#!/usr/bin/env python3
"""Build a blinded human-review pilot from the Verified pipeline.

Samples N instances that Agentless resolved (so both the agent patch and the gold patch
exist), emits BOTH candidates per instance as blinded packets, shuffled, into:
  - data/human_study/review_form.md   (human-readable: issue + diff per packet)
  - data/human_study/responses_TEMPLATE.csv  (packet_id, decision, blocking, notes)
  - data/human_study/key.json         (hidden source/instance map; do NOT open before review)

Reviewers fill the CSV (one row per packet) with decision in
{merge, request_changes, reject} and blocking in {yes, no}. Multiple reviewers => copy the
template to responses_<rater>.csv. Instructions match the calibrated LLM rubric.
"""
from __future__ import annotations
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/review_packets/verified"
OUT = ROOT / "data/human_study"
N_INSTANCES = 20  # -> 40 packets (agent+gold)

INSTRUCTIONS = """# Human code-review pilot

You are a maintainer deciding whether to MERGE each pull request. The project's tests
(reproduction + regression) ALREADY PASS for every patch; test files are intentionally not
shown, so do NOT reject for "no tests". Judge the source change as a real maintainer would:
merge if it correctly resolves the issue without clear correctness, regression, or
compatibility problems. Minor style issues are not blocking.

For each packet below, fill one row in responses_TEMPLATE.csv:
  - decision: merge | request_changes | reject
  - blocking: yes | no  (is there an issue you would refuse to merge over?)
  - notes: optional one line

Mergeable = decision is "merge" AND blocking = no. Do not open key.json until done.
"""


def load_packets():
    pk = [json.loads(l) for l in (PACK / "packets.jsonl").read_text().splitlines() if l.strip()]
    key = {k["packet_id"]: k for k in json.loads((PACK / "packets_key.json").read_text())}
    return {p["packet_id"]: p for p in pk}, key


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    packets, key = load_packets()
    # group by instance, keep instances having both agent and gold
    by_inst = {}
    for pid, k in key.items():
        by_inst.setdefault(k["instance_id"], {})[k["candidate_source"]] = pid
    both = sorted(i for i, d in by_inst.items() if "agent" in d and "gold" in d)
    rng = random.Random(7)
    rng.shuffle(both)
    chosen = both[:N_INSTANCES]

    sample_pids = []
    keyout = []
    for iid in chosen:
        for src in ("agent", "gold"):
            pid = by_inst[iid][src]
            sample_pids.append(pid)
            keyout.append({"packet_id": pid, "instance_id": iid, "candidate_source": src})
    rng.shuffle(sample_pids)

    # review form
    md = [INSTRUCTIONS, "\n---\n"]
    for n, pid in enumerate(sample_pids, 1):
        p = packets[pid]
        issue = (p["issue_text"] or "")[:1800]
        diff = p["diff"]
        if len(diff) > 9000:
            diff = diff[:9000] + "\n... [diff truncated for length] ..."
        md += [f"## Packet {n}/{len(sample_pids)} — `{pid}`",
               f"**Repository:** {p['repo']}  ", f"**Files:** {', '.join(p['changed_files'][:12])}  ",
               f"**Changes:** +{p['diff_stats']['added_lines']}/-{p['diff_stats']['removed_lines']}",
               "", "### Issue", "", issue, "", "### Patch", "", "```diff", diff, "```", "\n---\n"]
    (OUT / "review_form.md").write_text("\n".join(md))

    # response template
    rows = ["packet_id,decision,blocking,notes"]
    rows += [f"{pid},,," for pid in sample_pids]
    (OUT / "responses_TEMPLATE.csv").write_text("\n".join(rows) + "\n")

    (OUT / "key.json").write_text(json.dumps(keyout, indent=2))
    print(f"built human pilot: {len(sample_pids)} packets ({N_INSTANCES} instances x agent+gold)")
    print(f"  form: {OUT/'review_form.md'}")
    print(f"  fill: {OUT/'responses_TEMPLATE.csv'} -> copy to responses_<yourname>.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
