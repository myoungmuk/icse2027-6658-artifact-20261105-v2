#!/usr/bin/env python3
"""Phase 6: inter-reviewer agreement across the three calibrated LLM reviewers.

Computes Fleiss' kappa (3 raters, binary mergeable/not) over agent packets, gold packets,
and all packets, per split, plus pairwise Cohen's kappa. Quantifies how reliable
review-based mergeability is across reviewer models (RQ3).

Usage
-----
    python scripts/06_agreement.py --reviewers reviewer-7b-cal reviewer-14b-cal reviewer-32b-cal
"""
from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = ROOT / "data" / "review_packets"
REVIEW_DIR = ROOT / "data" / "llm_reviews"
OUT = ROOT / "results" / "reports"


def load(split: str, reviewer: str) -> dict:
    d = REVIEW_DIR / split / reviewer
    out = {}
    if d.exists():
        for f in d.glob("pk_*.json"):
            r = json.loads(f.read_text())
            if r.get("mergeable") is not None:
                out[f.stem] = bool(r["mergeable"])
    return out


def fleiss_kappa(rows: list[list[int]]) -> float:
    """rows[i] = [count_category0, count_category1] for item i; n raters constant."""
    rows = [r for r in rows if sum(r) > 0]
    if not rows:
        return float("nan")
    N = len(rows)
    n = sum(rows[0])
    if n < 2:
        return float("nan")
    p = [sum(rows[i][c] for i in range(N)) / (N * n) for c in range(2)]
    P = [(sum(x * x for x in rows[i]) - n) / (n * (n - 1)) for i in range(N)]
    Pbar = sum(P) / N
    Pe = sum(pc * pc for pc in p)
    if 1 - Pe == 0:
        return float("nan")
    return (Pbar - Pe) / (1 - Pe)


def cohen_kappa(a: dict, b: dict) -> float:
    keys = set(a) & set(b)
    if not keys:
        return float("nan")
    n = len(keys)
    both1 = sum(1 for k in keys if a[k] and b[k])
    both0 = sum(1 for k in keys if not a[k] and not b[k])
    po = (both1 + both0) / n
    pa1 = sum(1 for k in keys if a[k]) / n
    pb1 = sum(1 for k in keys if b[k]) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return (po - pe) / (1 - pe) if (1 - pe) else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviewers", nargs="+",
                    default=["reviewer-7b-cal", "reviewer-14b-cal", "reviewer-32b-cal"])
    ap.add_argument("--splits", nargs="+", default=["lite", "verified"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    result = {}
    for split in args.splits:
        key = json.loads((PACKET_DIR / split / "packets_key.json").read_text())
        src = {k["packet_id"]: k["candidate_source"] for k in key}
        decisions = {rv: load(split, rv) for rv in args.reviewers}
        common = set.intersection(*[set(d) for d in decisions.values()]) if all(decisions.values()) else set()

        def fleiss_for(subset_pids):
            rows = []
            for pid in subset_pids:
                votes = [decisions[rv][pid] for rv in args.reviewers]
                rows.append([votes.count(False), votes.count(True)])
            return round(fleiss_kappa(rows), 4)

        agent_pids = [p for p in common if src.get(p) == "agent"]
        gold_pids = [p for p in common if src.get(p) == "gold"]
        pairwise = {f"{a}|{b}": round(cohen_kappa(decisions[a], decisions[b]), 4)
                    for a, b in combinations(args.reviewers, 2)}
        result[split] = {
            "n_common": len(common),
            "fleiss_all": fleiss_for(common),
            "fleiss_agent": fleiss_for(agent_pids),
            "fleiss_gold": fleiss_for(gold_pids),
            "pairwise_cohen": pairwise,
            "per_model_accept_rate": {rv: round(100 * sum(decisions[rv].values()) / max(1, len(decisions[rv])), 2)
                                      for rv in args.reviewers},
        }

    (OUT / "agreement.json").write_text(json.dumps(result, indent=2))
    for split, r in result.items():
        print(f"[{split}] n={r['n_common']} Fleiss all={r['fleiss_all']} "
              f"agent={r['fleiss_agent']} gold={r['fleiss_gold']}  pairwise={r['pairwise_cohen']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
