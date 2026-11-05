#!/usr/bin/env python3
"""Figure: agent vs gold acceptance across all reviewer configurations (Verified).
Every reviewer (5 models x naive/calibrated) lies on the y=x line: the reviewer applies
the same bar to agent and gold at every strictness, so 'mergeability' is a global leniency
dial, not agent-specific discrimination. Outputs results/figures/dilemma_frontier.pdf and
appends r/gap macros to paper/numbers.tex (and paper_ko/numbers.tex).
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
pts = json.loads((ROOT / "results/reports/dilemma_points.json").read_text())

# r/gap describe the OPEN-model pool only; the frontier point is shown but excluded.
open_pts = [p for p in pts if p.get("model") != "Frontier"]
golds = [p["gold"] for p in open_pts]
agents = [p["agent"] for p in open_pts]
n = len(open_pts)
mg, ma = sum(golds)/n, sum(agents)/n
r = (sum((golds[i]-mg)*(agents[i]-ma) for i in range(n)) /
     ((sum((g-mg)**2 for g in golds)*sum((a-ma)**2 for a in agents))**0.5))
mean_gap = sum(abs(p["gold"]-p["agent"]) for p in open_pts)/n

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
COL = {"7B": "#2980b9", "14B": "#27ae60", "32B": "#c0392b",
       "Llama8B": "#8e44ad", "DSCoder": "#e67e22"}
fig, ax = plt.subplots(figsize=(4.3, 4.0))
ax.plot([0, 100], [0, 100], "--", color="gray", lw=1, label="$y=x$ (no discrimination)")
seen = set()
for p in pts:
    if p["model"] == "Frontier":
        ax.scatter(p["gold"], p["agent"], s=200, marker="*", facecolor="#111111",
                   edgecolor="k", linewidth=0.8, zorder=4, label="Frontier (Claude, subset)")
        ax.annotate("frontier", (p["gold"], p["agent"]), textcoords="offset points",
                    xytext=(-38, -4), fontsize=7)
        continue
    c = COL[p["model"]]
    ax.scatter(p["gold"], p["agent"], s=70,
               facecolor=c if p["calibrated"] else "white", edgecolor=c, linewidth=1.6,
               marker="o", zorder=3,
               label=p["model"] if p["model"] not in seen else None)
    seen.add(p["model"])
ax.set_xlabel("Gold acceptance % (validity)")
ax.set_ylabel("Agent acceptance % (RAP)")
ax.set_xlim(-3, 100); ax.set_ylim(-3, 100)
ax.set_title(f"Open reviewers: agent $\\approx$ gold ($r={r:.3f}$); frontier breaks the line\n"
             f"(filled=calibrated, hollow=naive)", fontsize=9)
ax.legend(fontsize=7, loc="lower right", framealpha=0.9)
fig.tight_layout()
(ROOT / "results/figures").mkdir(parents=True, exist_ok=True)
fig.savefig(ROOT / "results/figures/dilemma_frontier.pdf")

macro = (f"\\newcommand{{\\dilemmaR}}{{{r:.3f}}}\n"
         f"\\newcommand{{\\dilemmaGap}}{{{mean_gap:.1f}}}\n")
for nt in (ROOT/"paper/numbers.tex", ROOT/"paper_ko/numbers.tex"):
    t = nt.read_text()
    if "dilemmaR" not in t:
        nt.write_text(t + macro)
print(f"wrote dilemma_frontier.pdf  r={r:.3f}  mean_gap={mean_gap:.1f}")
