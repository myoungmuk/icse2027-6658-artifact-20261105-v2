#!/usr/bin/env python3
"""Phase 7: decision distribution (merge / request_changes / reject) per calibrated
reviewer, for agent vs gold packets. Emits results/tables/decisions_table.tex.
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = ROOT / "data" / "review_packets"
REVIEW_DIR = ROOT / "data" / "llm_reviews"
TAB = ROOT / "results" / "tables"

MODELS = [("7B", "reviewer-7b-cal"), ("14B", "reviewer-14b-cal"), ("32B", "reviewer-32b-cal")]


def dist(split, reviewer, source):
    key = {k["packet_id"]: k for k in json.loads((PACKET_DIR / split / "packets_key.json").read_text())}
    d = REVIEW_DIR / split / reviewer
    c = Counter()
    for f in d.glob("pk_*.json"):
        r = json.loads(f.read_text())
        if key.get(f.stem, {}).get("candidate_source") != source:
            continue
        dec = r.get("merge_decision")
        if dec in ("merge", "request_changes", "reject"):
            c[dec] += 1
    tot = sum(c.values()) or 1
    return {k: round(100 * c[k] / tot, 1) for k in ("merge", "request_changes", "reject")}


def main() -> int:
    TAB.mkdir(parents=True, exist_ok=True)
    rows = [r"\begin{tabular}{lll ccc}", r"\toprule",
            r"Model & Source & Split & Merge\% & Req.-changes\% & Reject\% \\", r"\midrule"]
    for sz, rev in MODELS:
        for source in ("agent", "gold"):
            for split, cap in (("lite", "Lite"), ("verified", "Verified")):
                d = dist(split, rev, source)
                rows.append(f"{sz} & {source} & {cap} & {d['merge']} & {d['request_changes']} & {d['reject']} \\\\")
        rows.append(r"\midrule")
    rows[-1] = r"\bottomrule"
    rows.append(r"\end{tabular}")
    (TAB / "decisions_table.tex").write_text("\n".join(rows) + "\n")
    print("wrote decisions_table.tex")
    # also print agent merge vs gold merge for sanity
    for sz, rev in MODELS:
        a = dist("lite", rev, "agent"); g = dist("lite", rev, "gold")
        print(f"{sz} Lite: agent merge {a['merge']}% reject {a['reject']}% | gold merge {g['merge']}% reject {g['reject']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
