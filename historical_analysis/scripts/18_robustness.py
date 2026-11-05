#!/usr/bin/env python3
"""Reviewer-feedback robustness: (A) 5-fold cross-validation of the calibrated metrics over
gold instances (the calibration prompt is fixed, so per-fold test metrics measure stability /
absence of overfitting); (B) frontier missingness analysis (is the 154-packet rate-limit loss
content-independent / MCAR?).
"""
from __future__ import annotations
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = {k["packet_id"]: k for k in
       json.loads((ROOT / "data/review_packets/verified/packets_key.json").read_text())}
PACK = {p["packet_id"]: p for p in
        (json.loads(l) for l in (ROOT / "data/review_packets/verified/packets.jsonl")
         .read_text().splitlines() if l.strip())}


def load(rev, base="data/llm_reviews/verified"):
    d = ROOT / base / rev
    out = {}
    if d.exists():
        for f in d.glob("pk_*.json"):
            r = json.loads(f.read_text())
            if r.get("mergeable") is not None:
                out[f.stem] = bool(r["mergeable"])
    return out


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def fold_metrics(rev):
    v = load(rev)
    # group by instance (5 folds, deterministic by sorted instance hash)
    insts = sorted({KEY[p]["instance_id"] for p in v})
    folds = {}
    for i, iid in enumerate(insts):
        folds.setdefault(i % 5, set()).add(iid)
    res = []
    for k, test_iids in folds.items():
        gold = {KEY[p]["instance_id"]: m for p, m in v.items()
                if KEY[p]["candidate_source"] == "gold" and KEY[p]["instance_id"] in test_iids}
        agent = {KEY[p]["instance_id"]: m for p, m in v.items()
                 if KEY[p]["candidate_source"] == "agent" and KEY[p]["instance_id"] in test_iids}
        if not gold or not agent:
            continue
        fr = 100 * (1 - sum(gold.values()) / len(gold))
        rap = 100 * sum(agent.values()) / len(agent)
        sh = set(agent) & set(gold)
        b = sum(1 for i in sh if gold[i] and not agent[i])
        c = sum(1 for i in sh if agent[i] and not gold[i])
        res.append({"false_rej": round(fr, 1), "rap": round(rap, 1),
                    "mcnemar_p": round(mcnemar(b, c), 3), "n_test": len(test_iids)})
    return res


def main() -> int:
    out = {"calibration_cv": {}, "frontier_missingness": {}}
    print("=== (A) 5-fold CV of calibrated metrics (gold false-rejection should be stable) ===")
    for rev in ["reviewer-14b-cal", "reviewer-32b-cal", "reviewer-7b-cal",
                "reviewer-llama8b-cal", "reviewer-dscoder-cal", "reviewer-claude-frontier"]:
        folds = fold_metrics(rev)
        if not folds:
            continue
        frs = [f["false_rej"] for f in folds]
        raps = [f["rap"] for f in folds]
        rec = {"folds": len(folds),
               "false_rej_mean": round(statistics.mean(frs), 1),
               "false_rej_sd": round(statistics.pstdev(frs), 1),
               "false_rej_range": [min(frs), max(frs)],
               "rap_mean": round(statistics.mean(raps), 1),
               "rap_sd": round(statistics.pstdev(raps), 1)}
        out["calibration_cv"][rev] = rec
        print(f"  {rev:26s} false-rej {rec['false_rej_mean']}±{rec['false_rej_sd']} "
              f"(range {rec['false_rej_range']})  RAP {rec['rap_mean']}±{rec['rap_sd']}")

    print("\n=== (B) frontier missingness (completed vs missing; MCAR check) ===")
    done = set(load("reviewer-claude-frontier"))
    # also count error/none files as done-but-invalid? we deleted errors, so missing = no file
    have_file = {f.stem for f in (ROOT / "data/llm_reviews/verified/reviewer-claude-frontier").glob("pk_*.json")}
    allp = set(PACK)
    missing = allp - have_file
    comp = have_file & allp
    def summary(pids):
        ag = sum(1 for p in pids if KEY[p]["candidate_source"] == "agent")
        go = sum(1 for p in pids if KEY[p]["candidate_source"] == "gold")
        dsz = [PACK[p]["diff_stats"]["added_lines"] + PACK[p]["diff_stats"]["removed_lines"] for p in pids]
        repos = len({PACK[p]["repo"] for p in pids})
        return {"n": len(pids), "agent": ag, "gold": go,
                "median_diff_lines": int(statistics.median(dsz)) if dsz else 0,
                "n_repos": repos}
    out["frontier_missingness"] = {"completed": summary(comp), "missing": summary(missing)}
    print(f"  completed: {summary(comp)}")
    print(f"  missing:   {summary(missing)}")
    (ROOT / "results/reports/robustness.json").write_text(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
