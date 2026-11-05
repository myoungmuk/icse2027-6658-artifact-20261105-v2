# Revised abstract — 2026-11-03

Passing benchmark tests does not establish that a maintainer would merge a coding-agent
patch. Large language model (LLM) reviewers offer a scalable additional assessment, but their
decisions also require validation. We study test-passing patches from four coding-agent
scaffolds on SWE-bench Lite and Verified, pairing agent patches with developer-merged gold
patches under source-blinded review. The headline naive reviewer, Qwen2.5-Coder-14B-AWQ,
rejects 94.79\% and 93.3\% of the gold patches on Lite and
Verified. After jointly adjusting test-context disclosure and the merge-blocking rubric,
its gold rejection falls to 27.08\% and 25.26\%; the same data were
used during rubric development and evaluation, so this is not independent calibration
validation. Across ten open-weight reviewer/prompt configurations on Verified, agent and
gold acceptance rates correlate at $r=0.994$, while agreement across five adjusted
reviewers is low (Fleiss $\kappa\approx0.02$). A hosted Claude reviewer accepts $164/194$
agent patches and $191/194$ paired gold patches (exact McNemar $p<0.001$), but its exact
model snapshot was not recorded and these decisions were not validated against maintainers.
The archived failing-patch comparison also supplied an incorrect test-pass assertion and
used different tasks; it cannot establish discrimination under correct test information.
A single non-independent rater's $40$-packet pilot provides descriptive observations only.
Our contribution is a control-based diagnosis of reviewer-dependent acceptance, together
with packets, verdicts, and analysis procedures. Historical gold acceptance is a useful
reference, but neither agreement with that reference nor a reviewer-specific agent--gold
difference establishes real-world mergeability.
