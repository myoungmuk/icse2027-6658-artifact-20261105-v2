#!/usr/bin/env python3
"""Full-Verified frontier analysis: frontier reviewer on 194 agent + 194 gold packets,
on the same footing as the open models. Updates the dilemma point to full N, recomputes
McNemar (powered), frontier-vs-human (40 overlap) and frontier-vs-open (full) agreement,
refreshes macros + figure data.
"""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FR = ROOT / "data/llm_reviews/verified/reviewer-claude-frontier"
KEYV = {k["packet_id"]: k for k in
        json.loads((ROOT / "data/review_packets/verified/packets_key.json").read_text())}
KEYH = {k["packet_id"]: k for k in
        json.loads((ROOT / "data/human_study/key.json").read_text())}


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0, 0)
    p = k / n
    d = 1 + z*z/n
    c = p + z*z/(2*n)
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return (p, (c-h)/d, (c+h)/d)


def cohen(a, b):
    ks = set(a) & set(b)
    if not ks:
        return float("nan")
    n = len(ks)
    po = sum(1 for k in ks if a[k] == b[k]) / n
    pa = sum(a[k] for k in ks)/n
    pb = sum(b[k] for k in ks)/n
    pe = pa*pb + (1-pa)*(1-pb)
    return (po-pe)/(1-pe) if (1-pe) else float("nan")


def load(d):
    out = {}
    for f in d.glob("pk_*.json"):
        r = json.loads(f.read_text())
        if r.get("mergeable") is not None:
            out[f.stem] = bool(r["mergeable"])
    return out


def main() -> int:
    fr = load(FR)
    agent = {p: m for p, m in fr.items() if KEYV.get(p, {}).get("candidate_source") == "agent"}
    gold = {p: m for p, m in fr.items() if KEYV.get(p, {}).get("candidate_source") == "gold"}
    a_iid = {KEYV[p]["instance_id"]: m for p, m in agent.items()}
    g_iid = {KEYV[p]["instance_id"]: m for p, m in gold.items()}
    sh = set(a_iid) & set(g_iid)
    b = sum(1 for i in sh if g_iid[i] and not a_iid[i])
    c = sum(1 for i in sh if a_iid[i] and not g_iid[i])
    rap, rlo, rhi = wilson(sum(agent.values()), len(agent))
    grate = 100*sum(gold.values())/len(gold)

    # bootstrap CI on the paired gold-agent acceptance difference (seeded, reproducible)
    import random
    rng = random.Random(20260701)
    shl = sorted(sh)
    pair = [(1 if g_iid[i] else 0) - (1 if a_iid[i] else 0) for i in shl]
    diffs = []
    n = len(pair)
    for _ in range(10000):
        s = sum(pair[rng.randrange(n)] for _ in range(n))
        diffs.append(100.0 * s / n)
    diffs.sort()
    gap_lo, gap_hi = diffs[249], diffs[9749]  # 95% percentile CI
    gap_pt = 100.0 * sum(pair) / n

    # human kappa (40 overlap)
    hu = {}
    for row in csv.DictReader(open(ROOT / "data/human_study/responses_rater1.csv")):
        if row["decision"]:
            hu[row["packet_id"]] = (row["decision"] == "merge") and (row["blocking"] in ("no", ""))
    # frontier vs open (full verified)
    kappas = {}
    for rv in ["reviewer-7b-cal", "reviewer-14b-cal", "reviewer-32b-cal",
               "reviewer-llama8b-cal", "reviewer-dscoder-cal"]:
        ov = load(ROOT / "data/llm_reviews/verified" / rv)
        kappas[rv] = round(cohen(fr, ov), 3)

    res = {
        "n_agent": len(agent), "n_gold": len(gold), "n_paired": len(sh),
        "agent_accept": round(100*sum(agent.values())/len(agent), 1),
        "gold_accept": round(grate, 1),
        "gold_false_rej": round(100-grate, 1),
        "RAP_ci": [round(100*rlo, 1), round(100*rhi, 1)],
        "mcnemar_b_goldok_agentnot": b, "mcnemar_c_agentok_goldnot": c,
        "mcnemar_p": round(mcnemar(b, c), 4),
        "paired_gap_pt": round(gap_pt, 1),
        "paired_gap_ci": [round(gap_lo, 1), round(gap_hi, 1)],
        "kappa_vs_human40": round(cohen(fr, hu), 3),
        "kappa_vs_open": kappas,
    }
    (ROOT / "results/reports/frontier_full.json").write_text(json.dumps(res, indent=2))

    # update dilemma point (full) + macros
    pts = json.loads((ROOT / "results/reports/dilemma_points.json").read_text())
    pts = [p for p in pts if p.get("model") != "Frontier"]
    pts.append({"model": "Frontier", "calibrated": True,
                "gold": res["gold_accept"], "agent": res["agent_accept"]})
    (ROOT / "results/reports/dilemma_points.json").write_text(json.dumps(pts, indent=2))

    # idempotent: providecommand defines if absent, renewcommand always sets the value,
    # so re-running (or a base file that already defines these) never triggers a duplicate error.
    def setmac(name, val):
        return f"\\providecommand{{\\{name}}}{{}}\\renewcommand{{\\{name}}}{{{val}}}\n"
    pfmt = "<0.001" if res["mcnemar_p"] < 0.001 else "=" + str(res["mcnemar_p"])
    mac = ("\n% --- frontier full-N (17) ---\n"
           + setmac("frontGold", res["gold_accept"])
           + setmac("frontAgent", res["agent_accept"])
           + setmac("frontFalseRej", res["gold_false_rej"])
           + setmac("frontMcNemar", pfmt)
           + setmac("frontNpair", res["n_paired"])
           + setmac("frontNvalid", res["n_agent"] + res["n_gold"])
           + setmac("frontAgentN", res["n_agent"])
           + setmac("frontGoldN", res["n_gold"])
           + setmac("frontGapPt", res["paired_gap_pt"])
           + setmac("frontGapCIlo", res["paired_gap_ci"][0])
           + setmac("frontGapCIhi", res["paired_gap_ci"][1])
           + setmac("frontKappaHumanFull", res["kappa_vs_human40"]))
    for nt in ("paper/numbers.tex", "paper_ko/numbers.tex"):
        if (ROOT / nt).exists():
            (ROOT / nt).write_text((ROOT / nt).read_text() + mac)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
