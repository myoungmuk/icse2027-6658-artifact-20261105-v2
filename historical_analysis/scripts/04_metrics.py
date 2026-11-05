#!/usr/bin/env python3
"""Phase 4: compute %Resolved, RAP, MRR, Resolution-Mergeability Gap, taxonomy,
reviewer calibration, and significance tests from LLM reviews.

Outputs results/reports/metrics_<reviewer>.json and a markdown summary.

Usage
-----
    python scripts/04_metrics.py --reviewer reviewer-14b --splits lite verified
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = ROOT / "data" / "review_packets"
REVIEW_DIR = ROOT / "data" / "llm_reviews"
RES_DIR = ROOT / "data" / "swebench_results"
OUT = ROOT / "results" / "reports"

TAX_ORDER = [f"F{i}" for i in range(1, 12)]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, (c - h) / d, (c + h) / d)


def mcnemar(b: int, c: int) -> float:
    """Two-sided exact-ish McNemar p (binomial on discordant pairs)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    # binomial tail *2 at p=0.5
    cum = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * cum)


def load_reviews(split: str, reviewer: str) -> dict:
    d = REVIEW_DIR / split / reviewer
    out = {}
    for f in d.glob("pk_*.json"):
        out[f.stem] = json.loads(f.read_text())
    return out


def analyze(split: str, reviewer: str) -> dict:
    key = json.loads((PACKET_DIR / split / "packets_key.json").read_text())
    by_pid = {k["packet_id"]: k for k in key}
    reviews = load_reviews(split, reviewer)
    res = json.loads((RES_DIR / f"{split}_resolved.json").read_text())
    n_total = res["n_total"]
    n_resolved = res["n_resolved"]

    # join per instance
    agent, gold = {}, {}
    for pid, k in by_pid.items():
        r = reviews.get(pid)
        if not r or r.get("mergeable") is None:
            continue
        rec = {"mergeable": bool(r["mergeable"]), "issues": r.get("issues", []),
               "decision": r.get("merge_decision")}
        (agent if k["candidate_source"] == "agent" else gold)[k["instance_id"]] = rec

    n_agent = len(agent)
    n_gold = len(gold)
    merge_agent = sum(1 for v in agent.values() if v["mergeable"])
    merge_gold = sum(1 for v in gold.values() if v["mergeable"])

    rap, rap_lo, rap_hi = wilson(merge_agent, n_agent)
    mrr = merge_agent / n_total if n_total else 0.0
    pct_resolved = n_resolved / n_total if n_total else 0.0
    gap = pct_resolved - mrr
    gold_merge_rate, gm_lo, gm_hi = wilson(merge_gold, n_gold)

    # reviewer-quality metrics on the gold positive control:
    # gold was merged by maintainers, so accepting it is the correct decision and any
    # blocking issue raised on it is a hallucinated merge-blocker.
    gold_blocking = sum(1 for v in gold.values()
                        if any(i["severity"] == "blocking" for i in v["issues"]))
    halluc_rate = gold_blocking / n_gold if n_gold else 0.0
    gold_decision_acc = merge_gold / n_gold if n_gold else 0.0

    # paired McNemar agent vs gold on shared instances
    shared = set(agent) & set(gold)
    b = sum(1 for i in shared if gold[i]["mergeable"] and not agent[i]["mergeable"])  # gold ok, agent not
    c = sum(1 for i in shared if agent[i]["mergeable"] and not gold[i]["mergeable"])  # agent ok, gold not
    p_mcnemar = mcnemar(b, c)

    # failure taxonomy among non-mergeable agent patches (blocking + major)
    tax = {f: 0 for f in TAX_ORDER}
    tax_blocking = {f: 0 for f in TAX_ORDER}
    sev = {"blocking": 0, "major": 0, "minor": 0}
    nonmerge_agent = [v for v in agent.values() if not v["mergeable"]]
    for v in nonmerge_agent:
        seen = set()
        for it in v["issues"]:
            fm = it["failure_mode"]
            sev[it["severity"]] = sev.get(it["severity"], 0) + 1
            if it["severity"] == "blocking":
                tax_blocking[fm] = tax_blocking.get(fm, 0) + 1
            if fm not in seen:
                tax[fm] = tax.get(fm, 0) + 1
                seen.add(fm)

    return {
        "split": split, "reviewer": reviewer,
        "n_total": n_total, "n_resolved": n_resolved,
        "n_agent_reviewed": n_agent, "n_gold_reviewed": n_gold,
        "pct_resolved": round(100 * pct_resolved, 2),
        "merge_agent": merge_agent, "merge_gold": merge_gold,
        "RAP": round(100 * rap, 2), "RAP_ci": [round(100 * rap_lo, 2), round(100 * rap_hi, 2)],
        "MRR": round(100 * mrr, 2),
        "Resolution_Mergeability_Gap": round(100 * gap, 2),
        "gold_mergeable_rate": round(100 * gold_merge_rate, 2),
        "gold_mergeable_ci": [round(100 * gm_lo, 2), round(100 * gm_hi, 2)],
        "gold_false_rejection_rate": round(100 * (1 - gold_merge_rate), 2),
        "hallucinated_review_rate": round(100 * halluc_rate, 2),
        "gold_decision_accuracy": round(100 * gold_decision_acc, 2),
        "mcnemar": {"gold_ok_agent_not": b, "agent_ok_gold_not": c, "p_value": round(p_mcnemar, 5)},
        "failure_taxonomy_any": tax,
        "failure_taxonomy_blocking": tax_blocking,
        "severity_counts": sev,
        "n_nonmergeable_agent": len(nonmerge_agent),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--splits", nargs="+", default=["lite", "verified"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    all_res = {s: analyze(s, args.reviewer) for s in args.splits}
    (OUT / f"metrics_{args.reviewer}.json").write_text(json.dumps(all_res, indent=2))

    md = [f"# Metrics — reviewer `{args.reviewer}`", ""]
    md += ["| Split | %Resolved | RAP (mergeable|resolved) | MRR | Gap | Gold-merge% | FalseRej% | McNemar p |",
           "|-------|-----------|--------------------------|-----|-----|-------------|-----------|-----------|"]
    for s in args.splits:
        r = all_res[s]
        md.append(f"| {s} | {r['pct_resolved']} | {r['RAP']} [{r['RAP_ci'][0]},{r['RAP_ci'][1]}] | "
                  f"{r['MRR']} | {r['Resolution_Mergeability_Gap']} | {r['gold_mergeable_rate']} | "
                  f"{r['gold_false_rejection_rate']} | {r['mcnemar']['p_value']} |")
    md += ["", "## Failure taxonomy (share of non-mergeable agent patches flagged, any severity)", ""]
    for s in args.splits:
        r = all_res[s]
        n = max(1, r["n_nonmergeable_agent"])
        md.append(f"**{s}** (n_nonmergeable={r['n_nonmergeable_agent']}): " +
                  ", ".join(f"{f}={r['failure_taxonomy_any'][f]}" for f in TAX_ORDER
                            if r['failure_taxonomy_any'][f]))
    (OUT / f"metrics_{args.reviewer}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
