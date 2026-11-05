#!/usr/bin/env python3
"""Analyze filled human-review responses against the gold control and the LLM reviewers.

Reads data/human_study/responses_*.csv (one per rater; skips the TEMPLATE), key.json, and
the calibrated LLM verdicts for the sampled packets. Reports, per rater and (if >=2)
adjudicated by majority:
  - human acceptance of agent vs gold patches + McNemar (do humans separate them?)
  - human false-rejection on gold (human positive control)
  - human vs each calibrated LLM reviewer agreement (Cohen's kappa)
  - inter-rater agreement (if >=2 raters)
Emits results/reports/human_study.json + a short markdown summary.
"""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HS = ROOT / "data/human_study"
RV = ROOT / "data/llm_reviews/verified"
OUT = ROOT / "results/reports"
LLM = ["reviewer-7b-cal", "reviewer-14b-cal", "reviewer-32b-cal",
       "reviewer-llama8b-cal", "reviewer-dscoder-cal"]


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


def read_responses(path):
    out = {}
    for row in csv.DictReader(open(path)):
        pid = (row.get("packet_id") or "").strip()
        dec = (row.get("decision") or "").strip().lower()
        blk = (row.get("blocking") or "").strip().lower()
        if not pid or not dec:
            continue
        out[pid] = (dec == "merge") and (blk in ("no", "n", ""))
    return out


def llm_verdicts(reviewer, pids):
    d = RV / reviewer
    out = {}
    for pid in pids:
        f = d / f"{pid}.json"
        if f.exists():
            r = json.loads(f.read_text())
            if r.get("mergeable") is not None:
                out[pid] = bool(r["mergeable"])
    return out


def main() -> int:
    key = {k["packet_id"]: k for k in json.loads((HS / "key.json").read_text())}
    raters = sorted(p for p in HS.glob("responses_*.csv") if "TEMPLATE" not in p.name)
    if not raters:
        print("No responses_*.csv yet. Fill responses_TEMPLATE.csv -> responses_<name>.csv.")
        return 0

    rater_dec = {p.stem.replace("responses_", ""): read_responses(p) for p in raters}
    # adjudicated (majority) over packets all raters answered
    common = set.intersection(*[set(d) for d in rater_dec.values()]) if rater_dec else set()
    adj = {}
    for pid in common:
        votes = [rater_dec[r][pid] for r in rater_dec]
        adj[pid] = sum(votes) > len(votes) / 2

    def split_rates(dec):
        ag = {p: m for p, m in dec.items() if key[p]["candidate_source"] == "agent"}
        go = {p: m for p, m in dec.items() if key[p]["candidate_source"] == "gold"}
        # pair by instance
        iid_ag = {key[p]["instance_id"]: m for p, m in ag.items()}
        iid_go = {key[p]["instance_id"]: m for p, m in go.items()}
        shared = set(iid_ag) & set(iid_go)
        b = sum(1 for i in shared if iid_go[i] and not iid_ag[i])
        c = sum(1 for i in shared if iid_ag[i] and not iid_go[i])
        return {
            "n_agent": len(ag), "n_gold": len(go),
            "agent_accept": round(100 * sum(ag.values()) / len(ag), 1) if ag else None,
            "gold_accept": round(100 * sum(go.values()) / len(go), 1) if go else None,
            "gold_false_rej": round(100 * (1 - sum(go.values()) / len(go)), 1) if go else None,
            "mcnemar_p": round(mcnemar(b, c), 4),
        }

    result = {"raters": {}, "n_raters": len(rater_dec)}
    for r, dec in rater_dec.items():
        result["raters"][r] = split_rates(dec)
    if len(rater_dec) >= 2:
        names = list(rater_dec)
        result["inter_rater_cohen"] = round(cohen(rater_dec[names[0]], rater_dec[names[1]]), 3)
        result["adjudicated"] = split_rates(adj)
        human = adj
    else:
        human = next(iter(rater_dec.values()))

    # human vs each calibrated LLM reviewer
    pids = list(human)
    result["human_vs_llm_cohen"] = {}
    for rv in LLM:
        lv = llm_verdicts(rv, pids)
        result["human_vs_llm_cohen"][rv] = round(cohen(human, lv), 3)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "human_study.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
