#!/usr/bin/env python3
"""Analyze the frontier (Claude) reviewer on the 40-packet subset: agent/gold acceptance,
agent-vs-gold McNemar, frontier-vs-human and frontier-vs-open-LLM agreement. Adds the
frontier point to the dilemma frontier and reports."""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FR = ROOT / "data/llm_reviews/human_subset/reviewer-claude-frontier"
KEY = {k["packet_id"]: k for k in json.loads((ROOT / "data/human_study/key.json").read_text())}


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def cohen(a, b):
    ks = set(a) & set(b)
    if not ks:
        return float("nan")
    n = len(ks)
    po = sum(1 for k in ks if a[k] == b[k]) / n
    pa = sum(a[k] for k in ks) / n
    pb = sum(b[k] for k in ks) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if (1 - pe) else float("nan")


def frontier_verdicts():
    out = {}
    for f in FR.glob("pk_*.json"):
        r = json.loads(f.read_text())
        if r.get("mergeable") is not None:
            out[f.stem] = bool(r["mergeable"])
    return out


def human():
    out = {}
    for row in csv.DictReader(open(ROOT / "data/human_study/responses_rater1.csv")):
        if row["decision"]:
            out[row["packet_id"]] = (row["decision"] == "merge") and (row["blocking"] in ("no", ""))
    return out


def open_llm(reviewer, pids):
    d = ROOT / "data/llm_reviews/verified" / reviewer
    out = {}
    for pid in pids:
        f = d / f"{pid}.json"
        if f.exists():
            r = json.loads(f.read_text())
            if r.get("mergeable") is not None:
                out[pid] = bool(r["mergeable"])
    return out


def main() -> int:
    fr = frontier_verdicts()
    if not fr:
        print("no frontier verdicts yet")
        return 0
    hu = human()
    agent = {p: m for p, m in fr.items() if KEY[p]["candidate_source"] == "agent"}
    gold = {p: m for p, m in fr.items() if KEY[p]["candidate_source"] == "gold"}
    a_iid = {KEY[p]["instance_id"]: m for p, m in agent.items()}
    g_iid = {KEY[p]["instance_id"]: m for p, m in gold.items()}
    sh = set(a_iid) & set(g_iid)
    b = sum(1 for i in sh if g_iid[i] and not a_iid[i])
    c = sum(1 for i in sh if a_iid[i] and not g_iid[i])
    res = {
        "n_agent": len(agent), "n_gold": len(gold),
        "agent_accept": round(100 * sum(agent.values()) / len(agent), 1) if agent else None,
        "gold_accept": round(100 * sum(gold.values()) / len(gold), 1) if gold else None,
        "gold_false_rej": round(100 * (1 - sum(gold.values()) / len(gold)), 1) if gold else None,
        "mcnemar_agent_gold_p": round(mcnemar(b, c), 4),
        "kappa_vs_human": round(cohen(fr, hu), 3),
    }
    for rv in ["reviewer-7b-cal", "reviewer-14b-cal", "reviewer-32b-cal",
               "reviewer-llama8b-cal", "reviewer-dscoder-cal"]:
        res[f"kappa_vs_{rv}"] = round(cohen(fr, open_llm(rv, list(fr))), 3)
    (ROOT / "results/reports/frontier.json").write_text(json.dumps(res, indent=2))

    # add frontier point (subset) to dilemma figure data
    pts = json.loads((ROOT / "results/reports/dilemma_points.json").read_text())
    pts = [p for p in pts if p.get("model") != "Frontier"]
    pts.append({"model": "Frontier", "calibrated": True,
                "gold": res["gold_accept"], "agent": res["agent_accept"], "subset": True})
    (ROOT / "results/reports/dilemma_points.json").write_text(json.dumps(pts, indent=2))
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
