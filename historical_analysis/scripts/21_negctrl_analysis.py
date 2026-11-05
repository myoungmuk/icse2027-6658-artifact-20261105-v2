#!/usr/bin/env python3
"""Negative-control analysis: does a calibrated reviewer that passes the gold POSITIVE control
also REJECT known-bad (test-failing) patches, or does it accept them too (false acceptance)?

For each calibrated reviewer we compare, on Verified:
  - accept_gold        : acceptance on developer-merged gold  (positive control; should be high)
  - accept_agent_ok    : acceptance on resolved (test-passing) agent patches
  - accept_agent_fail  : acceptance on NON-resolved (test-failing) agent patches  <-- negative control
A valid + discriminating reviewer wants accept_gold high AND accept_agent_fail low. If
accept_agent_fail is close to accept_gold, the reviewer accepts even patches that do not fix the
bug -> false acceptance, i.e. its acceptance does not track real patch quality.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = {k["packet_id"]: k for k in
       json.loads((ROOT / "data/review_packets/verified/packets_key.json").read_text())}


def load(d):
    out = {}
    p = ROOT / d
    if p.exists():
        for f in p.glob("pk_*.json"):
            r = json.loads(f.read_text())
            if r.get("mergeable") is not None:
                out[f.stem] = bool(r["mergeable"])
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (100 * p, 100 * (c - h) / d, 100 * (c + h) / d)


def rate(v):
    n = len(v)
    k = sum(v.values())
    p, lo, hi = wilson(k, n)
    return {"n": n, "accept_pct": round(p, 1), "ci": [round(lo, 1), round(hi, 1)]}


def main() -> int:
    names = ["reviewer-7b-cal", "reviewer-14b-cal", "reviewer-32b-cal",
             "reviewer-llama8b-cal", "reviewer-dscoder-cal", "reviewer-claude-frontier"]
    reviewers = [(nm, f"data/llm_reviews/verified/{nm}",
                  f"data/llm_reviews/verified_negctrl/{nm}") for nm in names]
    out = {}
    for name, main_dir, neg_dir in reviewers:
        main_v = load(main_dir)
        gold = {p: m for p, m in main_v.items()
                if KEY.get(p, {}).get("candidate_source") == "gold"}
        agent_ok = {p: m for p, m in main_v.items()
                    if KEY.get(p, {}).get("candidate_source") == "agent"}
        fail = load(neg_dir)  # negctrl keys are agent_failing
        if not fail:
            print(f"{name:26s} negctrl verdicts not ready yet")
            continue
        rec = {
            "accept_gold": rate(gold),
            "accept_agent_resolved": rate(agent_ok),
            "accept_agent_FAILING": rate(fail),
        }
        rec["false_acceptance_gap_gold_minus_fail"] = round(
            rec["accept_gold"]["accept_pct"] - rec["accept_agent_FAILING"]["accept_pct"], 1)
        out[name] = rec
        print(f"\n=== {name} ===")
        print(f"  gold (merged, positive control): {rec['accept_gold']['accept_pct']}%  (n={rec['accept_gold']['n']})")
        print(f"  agent resolved (test-passing)  : {rec['accept_agent_resolved']['accept_pct']}%  (n={rec['accept_agent_resolved']['n']})")
        print(f"  agent FAILING (neg control)    : {rec['accept_agent_FAILING']['accept_pct']}%  (n={rec['accept_agent_FAILING']['n']})")
        print(f"  gold - failing gap             : {rec['false_acceptance_gap_gold_minus_fail']} pts "
              f"({'discriminates on quality' if rec['false_acceptance_gap_gold_minus_fail']>=15 else 'FALSE ACCEPTANCE (accepts known-bad ~ gold)'})")

    (ROOT / "results/reports/negctrl.json").write_text(json.dumps(out, indent=2))

    # emit LaTeX macros (idempotent providecommand+renewcommand), appended to both numbers.tex
    def sm(name, val):
        return f"\\providecommand{{\\{name}}}{{}}\\renewcommand{{\\{name}}}{{{val}}}\n"
    def g(rv, field, sub="accept_pct"):
        return out[rv][field][sub] if rv in out else "NA"
    lines = ["\n% --- negative control (21) ---\n"]
    if "reviewer-7b-cal" in out:
        lines += [sm("negFailSeven", g("reviewer-7b-cal", "accept_agent_FAILING")),
                  sm("negGoldSeven", g("reviewer-7b-cal", "accept_gold")),
                  sm("negGapSeven", out["reviewer-7b-cal"]["false_acceptance_gap_gold_minus_fail"])]
    if "reviewer-14b-cal" in out:
        lines += [sm("negFailFourteen", g("reviewer-14b-cal", "accept_agent_FAILING")),
                  sm("negGoldFourteen", g("reviewer-14b-cal", "accept_gold")),
                  sm("negGapFourteen", out["reviewer-14b-cal"]["false_acceptance_gap_gold_minus_fail"])]
        lines += [sm("negN", out["reviewer-14b-cal"]["accept_agent_FAILING"]["n"])]
    for rv, tok in [("reviewer-32b-cal", "ThirtyTwo"), ("reviewer-llama8b-cal", "Llama"),
                    ("reviewer-dscoder-cal", "Dscoder")]:
        if rv in out:
            lines += [sm("negFail" + tok, g(rv, "accept_agent_FAILING")),
                      sm("negGold" + tok, g(rv, "accept_gold"))]
    if "reviewer-dscoder-cal" in out:
        lines += [sm("negDscoderN", out["reviewer-dscoder-cal"]["accept_agent_FAILING"]["n"])]
    if "reviewer-claude-frontier" in out:
        fci = out["reviewer-claude-frontier"]["accept_agent_FAILING"]["ci"]
        lines += [sm("negFailFrontier", g("reviewer-claude-frontier", "accept_agent_FAILING")),
                  sm("negGapFrontier", out["reviewer-claude-frontier"]["false_acceptance_gap_gold_minus_fail"]),
                  sm("negFrontierN", out["reviewer-claude-frontier"]["accept_agent_FAILING"]["n"]),
                  sm("negFailFrontierLo", fci[0]), sm("negFailFrontierHi", fci[1])]
    block = "".join(lines)
    # paper macros only when the LaTeX sources are present (skipped in the flat artifact)
    for nt in ("paper/numbers.tex", "paper_ko/numbers.tex"):
        if (ROOT / nt).exists():
            (ROOT / nt).write_text((ROOT / nt).read_text() + block)
    print("\ndone; results/reports/negctrl.json written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
