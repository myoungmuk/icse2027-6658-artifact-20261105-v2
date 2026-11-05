#!/usr/bin/env python3
"""Per-agent mergeability metrics across multiple scaffolds (verified, calibrated).

For each agent and each calibrated reviewer: RAP (agent mergeable rate), the gold
mergeable rate on the SAME instances, and a paired McNemar test. Also averages RAP across
the three reviewers. Emits results/reports/agent_metrics.json and a LaTeX table.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PK = ROOT / "data/review_packets/agents"
RV = ROOT / "data/llm_reviews/agents"
RES = ROOT / "data/swebench_results"
TAB = ROOT / "results/tables"
REP = ROOT / "results/reports"

AGENTS = [("rag-gpt4", "RAG+GPT-4"), ("sweagent-claude35", "SWE-agent+Claude-3.5"),
          ("agentless", "Agentless+GPT-4o"), ("openhands-codeact", "OpenHands-CodeAct")]
REVIEWERS = ["reviewer-7b-cal", "reviewer-14b-cal", "reviewer-32b-cal"]


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n))


def verdicts(split, reviewer):
    d = RV / split / reviewer
    out = {}
    if d.exists():
        for f in d.glob("*.json"):
            r = json.loads(f.read_text())
            if r.get("mergeable") is not None:
                out[f.stem] = bool(r["mergeable"])
    return out


def keymap(split):
    return {k["packet_id"]: k["instance_id"]
            for k in json.loads((PK / split / "packets_key.json").read_text())}


def main() -> int:
    REP.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    gold_pid2iid = keymap("_gold")

    result = {}
    for key, label in AGENTS:
        # Agentless reuses the main verified pipeline; the others use agents/<key>.
        if key == "agentless":
            apk = {k["packet_id"]: k["instance_id"]
                   for k in json.loads((ROOT / "data/review_packets/verified/packets_key.json").read_text())
                   if k["candidate_source"] == "agent"}
            gpk = {k["packet_id"]: k["instance_id"]
                   for k in json.loads((ROOT / "data/review_packets/verified/packets_key.json").read_text())
                   if k["candidate_source"] == "gold"}
            agent_dir = lambda rv: verdicts("../verified", rv) if False else _vmain("verified", rv, "agent")
            gold_dir = lambda rv: _vmain("verified", rv, "gold")
        else:
            apk = keymap(key)
            agent_dir = lambda rv, k=key: {apk[p]: m for p, m in verdicts(k, rv).items() if p in apk}
            gold_dir = lambda rv: {gold_pid2iid[p]: m for p, m in verdicts("_gold", rv).items() if p in gold_pid2iid}

        res = json.loads((RES / f"{key}_resolved.json").read_text()) if (RES / f"{key}_resolved.json").exists() \
            else json.loads((RES / "verified_resolved.json").read_text())
        pct = res["pct_resolved"]
        per_rev = {}
        rap_vals = []
        for rv in REVIEWERS:
            if key == "agentless":
                a = {apk[p]: m for p, m in _vmain("verified", rv, "agent").items()}
                g = {gpk[p]: m for p, m in _vmain("verified", rv, "gold").items()}
            else:
                a = agent_dir(rv)
                g = gold_dir(rv)
            shared = set(a) & set(g)
            if not shared:
                continue
            rap = 100 * sum(a[i] for i in a) / len(a)
            goldrate = 100 * sum(g[i] for i in shared) / len(shared)
            b = sum(1 for i in shared if g[i] and not a[i])
            c = sum(1 for i in shared if a[i] and not g[i])
            per_rev[rv] = {"n": len(a), "RAP": round(rap, 1), "gold_rate": round(goldrate, 1),
                           "mcnemar_p": round(mcnemar(b, c), 4)}
            rap_vals.append(rap)
        result[key] = {"label": label, "pct_resolved": pct,
                       "RAP_mean": round(sum(rap_vals) / len(rap_vals), 1) if rap_vals else None,
                       "per_reviewer": per_rev}

    (REP / "agent_metrics.json").write_text(json.dumps(result, indent=2))

    # table: agent x reviewer RAP, plus gold and McNemar (14B shown)
    t = [r"\begin{tabular}{llccccc}", r"\toprule",
         r"Agent & \%Resolved & RAP$_{7B}$ & RAP$_{14B}$ & RAP$_{32B}$ & RAP$_\text{mean}$ & McNemar $p$ (14B) \\",
         r"\midrule"]
    for key, label in AGENTS:
        r = result.get(key, {})
        pr = r.get("per_reviewer", {})
        def g(rv, f): return pr.get(rv, {}).get(f, "--")
        t.append(f"{label} & {r.get('pct_resolved','--')} & {g('reviewer-7b-cal','RAP')} & "
                 f"{g('reviewer-14b-cal','RAP')} & {g('reviewer-32b-cal','RAP')} & {r.get('RAP_mean','--')} & "
                 f"{g('reviewer-14b-cal','mcnemar_p')} \\\\")
    t += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "agents_table.tex").write_text("\n".join(t) + "\n")
    for key, label in AGENTS:
        r = result.get(key, {})
        print(f"{label:24s} %Res={r.get('pct_resolved')}  RAP_mean={r.get('RAP_mean')}  "
              f"14B: {r.get('per_reviewer',{}).get('reviewer-14b-cal')}")
    return 0


def _vmain(split, reviewer, source):
    """verdicts for the main verified pipeline, filtered by source."""
    key = {k["packet_id"]: k["candidate_source"]
           for k in json.loads((ROOT / f"data/review_packets/{split}/packets_key.json").read_text())}
    d = ROOT / "data/llm_reviews" / split / reviewer
    out = {}
    if d.exists():
        for f in d.glob("*.json"):
            if key.get(f.stem) != source:
                continue
            r = json.loads(f.read_text())
            if r.get("mergeable") is not None:
                out[f.stem] = bool(r["mergeable"])
    return out


if __name__ == "__main__":
    raise SystemExit(main())
