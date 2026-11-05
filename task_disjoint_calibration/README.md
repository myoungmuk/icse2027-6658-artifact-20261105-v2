# New task-disjoint configuration-selection study (v10)

This separate 7B study does not reconstruct or validate historical manual rubric
development. All 707 previously reviewed Lite/Verified tasks are excluded. Forty
development tasks select one of two frozen configurations; 100 disjoint heldout
tasks evaluate that selection. Candidate source/outcomes are hidden in prompts.
Full issue/diff text is retained. See experiment/PROTOCOL.md for the frozen design.

560 inputs were planned, 558 generations actually ran, and two overlength inputs
were skipped without truncation or replacement. Status counts and valid/complete
pair denominators are explicit in evidence/experiment_analysis.json. Invalid
responses are never imputed as REJECT. The development selection file and all
160 development output hashes were sealed before heldout inference began.

Offline analysis and validation require Python's standard library only:

    python task_disjoint_calibration/tools/analyze_experiment.py --output /tmp/icse6658-new-heldout-analysis.json

This recomputes scores, selection, parsing, frozen message/input hashes, temporal
receipts, complete-pair statistics and task-bootstrap intervals. It performs no
model inference, network request or GPU allocation. Choose a new output filename.

To regenerate the selected candidates, install pyarrow 18.1.0 in your own CPU
environment and use the included, hash-recorded official sources:

    python task_disjoint_calibration/tools/prepare_experiment.py --sources task_disjoint_calibration/sources --excluded-audit task_disjoint_calibration/experiment/selection_audit.json --experiment /tmp/icse6658-new-task-selection

Candidate and configuration bytes are deterministic. Audit JSON values match;
repository-count dictionary key serialization order can differ. No source models,
credentials, author-only human-rater key or private review records are included.
The old source filename ending all_preds.jsonl.json contains original JSONL bytes.
All 12 duplicated prediction IDs are excluded rather than choosing a duplicate.

Fresh inference requires a new work copy/output directory and the recorded pinned
model, runtime and GPU. Do not execute the preserved run_gpu.sh: it records the
original AISE path and is provenance. In a new directory update the local model
path/shell launcher and generate a new freeze manifest before executing run.py;
that is a new run, not a change to these preserved records. GPU allocations must
follow the site's operating policy. No model weights are distributed here.

The official agent predictions were historically applied, had logs and were not
resolved; listed setup/test exceptions are excluded. These are functional proxies,
not newly executed tests or maintainer-quality truth. This task split does not
exclude repository overlap, semantic duplicates or pretraining exposure. The
developer/source text remains third-party material under its upstream terms; no
new blanket license is applied. See the repository's existing license notices.
