# Prospective task-disjoint configuration selection (v10)

This is a new study, not a recovery of the historical manual calibration process.
The historical rubric reused evaluation tasks; its leakage is not repaired by this
experiment. No historical reviewer/model identity or human validation is inferred.

Before inference, use full SWE-bench test revision
e48e2bd1e9fecd5bbd641e9414ac59da9f2e69f6 and published SWE-agent GPT-4 results from
experiments commit 40f164d5b8f1d249bf95a6df8b74b577fd8e519d. Exclude all 707 tasks
in the prior Lite/Verified union and archived review packets. Eligible tasks have
an applied, nonempty agent prediction and historical logs, are not resolved, and
are absent from listed setup/reset/test-error/test-timeout exceptions. Require a
nonempty developer patch and distinct agent/developer diffs. Absence from the
resolved list is a historical functional proxy, not a newly executed harness or
maintainer-quality label. Null/empty predictions and every ID with duplicate
prediction records are excluded before selection; no arbitrary duplicate is kept.

Order eligible task IDs by SHA-256 of the fixed salt in selection_audit.json plus
task ID. Select first 40 development tasks and next 100 heldout tasks. Use both
developer and unresolved-agent patches per task. Check no task, exact issue text,
or exact candidate diff overlaps between partitions. Same repositories may occur
in both partitions. Semantic duplication and model pretraining exposure are not
ruled out. The split is task-disjoint, not repository- or temporal-disjoint.

Freeze two prompts, strict and adjusted, plus all inputs/configuration/code before
inference. Both use the same issue, repository, base commit, whole candidate diff,
output schema, and truthful no-execution-result instruction. Neither reveals
source, execution label, reference patch, or the paired patch to the model. Patch
text can retain provenance/style cues. No artificial assertion of passing tests.
The adjusted prompt is a prospective maintainer-style adaptation, not an exact
historical replay. Neither uses per-task rubrics or human refinement.

Use pinned Qwen2.5-Coder-7B-Instruct revision
c03e6d358207e414f1eca0bb1891e29f1db0e242, greedy bfloat16 inference, seed 6658,
full context without truncation, maximum 512 generated tokens. Context limit,
batching and parser are in config.json/run.py/prompts.py. Preserve malformed,
length-capped, too-long and OOM cases; do not repair or convert them to REJECT.
OOM batch splitting is a resource recovery, recorded explicitly.

Run 160 development calls first (40 tasks x 2 patches x 2 prompts). Choose the
configuration with larger (developer ACCEPT + unresolved-agent REJECT)/80 planned
development patches. Invalid/missing decisions earn zero correct; they have no
imputed verdict. Since classes are equal, this is planned-denominator balanced
proxy agreement. Ties choose strict. This is finite configuration selection,
not iterative/manual rubric optimization or probability calibration. Seal all
development output hashes, scores and selected configuration in an exclusive
selection file BEFORE heldout inference. Do not change the rule after outcomes.

Then run 400 heldout calls (100 x 2 x 2). Evaluate the selected configuration and
also disclose the fixed alternative, without selecting again. Report each class'
valid/planned/accepted counts, complete matched pairs, discordance/McNemar exact
test, selected proxy agreement, configuration deltas, and task-bootstrap 95% CIs
with fixed seed 6658. Invalid outputs are explicit; complete-pair analyses never
impute them. Developer-vs-unresolved rates assess this narrow functional proxy,
not independent maintainer agreement, universal calibration or equivalence.

Both development and heldout materials are public benchmark data. Partition
labels are known to the orchestration code but never supplied in model messages.
Run code enforces a development-seal-before-heldout sequence. This procedural
control does not establish third-party preregistration or analyst blinding.
No new model weights, full benchmark harness, or human ratings are requested.
