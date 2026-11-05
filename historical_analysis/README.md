# Beyond %Resolved — ICSE 2027 #6658 analysis package

Camera-ready working revision, 2026-11-03. Authors: Myeongmuk Kang and Geunseok Yang,
Hankyong National University. This is a local handoff package; a public repository URL
and persistent release identifier have not yet been verified.

## Recreate the revised results without inference

Python 3.12.13 was used. Install the analysis dependencies in your own environment:

```bash
python -m pip install -r requirements-analysis.txt
python scripts/22_camera_ready.py
```

The command works from any current directory, makes no network/model calls, and writes
only `results/camera_ready/`. It reads the supplied task/source keys, normalized verdicts,
pilot responses, and archived aggregate reports. It regenerates all eight revised tables
and three figures, including exact paired tests, valid denominators, cross-agent results,
agreement, pilot calculations, and the seeded paired bootstrap interval. It exits with
an error on a failed evidence check. The current run passes 223 checks and inventories
9,256 saved verdict JSON files. This is a saved-output analysis, not a fresh reproduction
of the model decisions or the SWE-bench execution harness.

| Input/output | Meaning |
|---|---|
| `PROMPTS.md`, `PROMPT_CHANGES.md` | Exact open-review prompts, hosted assembly details, joint rubric changes and input error |
| `data/review_packets/` | Review packets and separate task/source keys; includes disjoint failing tasks |
| `data/llm_reviews/` | Saved normalized verdicts, including invalid/error records and available `_attempt` fields |
| `data/human_study/` | One non-independent rater's 40-packet form, responses, source key |
| `data/swebench_instances/`, `data/swebench_results/` | Preserved task metadata and adopted official resolved-ID sets |
| `data/source_metadata/` | Pinned official entry metadata, result lists, acquisition URLs/hashes and archived provenance audit |
| `results/camera_ready/metrics.json` | Revised metrics, supplementary numeric claims, and every evidence check |
| `results/camera_ready/tables/`, `figures/` | The eight table inputs and three PDF figures used in the revised manuscript |
| `results/camera_ready/verdict_inventory.csv` | Per-file SHA-256, validity and available retry metadata |
| `scripts/00_...` through `21_...`, other `results/` | Historical pipeline and reports, retained as evidence; see corrections below |

## Corrections needed when reading historical materials

- A verdict is accepted when `merge_decision == "merge"` **and** no issue has severity
  `blocking`. Gold acceptance measures agreement with a historical merge outcome; it
  does not prove that a patch or a review objection is correct.
- Historical `hallucinated_review_rate` is the percentage of valid gold verdicts with
  at least one blocking issue. The revised name is **gold blocking rate**. It differs
  from gold rejection and is not a factual hallucination label.
- Historical `calibration_cv` is a five-subset stability calculation on fixed verdicts,
  using sorted instance IDs modulo five. The rubric was not developed separately in
  held-out folds. Gold examples from the evaluated cohort informed rubric development;
  inspected IDs, intermediate edits and iteration count are unrecorded.
- Two prompt changes were applied jointly. Neither the test-context explanation nor
  the blocking criterion has an isolated causal effect estimate.
- Failing-patch reviews incorrectly reused pass assertions in the system prompt,
  user heading and final reminder. The revised table retains observations under this
  erroneous information. It does **not** validate functional discrimination under
  accurate information. Positive and negative tasks do not overlap. The hosted 81
  outputs occupy positions 1–79 and 81–82, not an exact first-81 prefix; position 80
  is unexplained. DeepSeek has 296 valid failing-patch outputs out of 302.
- Qwen-14B's non-significant cross-agent comparisons do not extend to all reviewers.
  Adjusted Qwen-32B has significant paired differences for SWE-agent and OpenHands.
  Non-significance is not equivalence.
- The pilot has one non-independent rater, with undocumented review experience and
  exact development relationship. Human input limits (1,800/9,000 issue/diff characters)
  differ from LLM limits (6,000/24,000). This is descriptive, not maintainer validation.

Historical scripts and reports retain their old wording and field names for traceability.
Use `22_camera_ready.py` for the revised manuscript. Running historical analysis scripts
may replace their own old reports and will not recreate the corrected manuscript inputs.

## What fresh inference would require

Open reviewers were Qwen2.5-Coder-7B/14B/32B-Instruct (AWQ for 14B/32B),
Llama-3.1-8B-Instruct, and DeepSeek-Coder-6.7B-Instruct behind a local OpenAI-compatible
endpoint. The preserved script allows three total attempts: temperature 0 on the first,
0.3 on retries, with a 1,200-token output limit. It is not uniformly greedy. Inference
requires separate weights, endpoint/client software, compute and the recorded templates;
unrecorded weight revisions/serving details limit exact recreation. The minimal analysis
requirements above intentionally do not install inference or Docker-harness dependencies.

The hosted path uses Claude Code CLI (`claude -p ... --output-format text`) without
`--model`. Exact provider model ID/snapshot, CLI version and decoding settings are
unrecorded. The development account places runs on June 30–July 1, 2026, but there is no
request-level log establishing those dates. Do not infer the model from current defaults.
Saved-output analysis is reproducible; an exact new hosted inference run is not established.
No new reviews or harness runs were performed for this revision.

## Upstream acquisition and rights

Official submission metadata/results are pinned to SWE-bench experiments commit
`40f164d5b8f1d249bf95a6df8b74b577fd8e519d`:
<https://github.com/SWE-bench/experiments/tree/40f164d5b8f1d249bf95a6df8b74b577fd8e519d/evaluation>.
`data/source_metadata/restoration_manifest.json` records exact URLs, hashes and entry IDs
for Agentless Lite/Verified, RAG, SWE-agent and OpenHands. Its `path` fields identify the
original acquisition location; matching small files are included under `data/source_metadata/`.
The old full `data/raw/` predictions/harness archive is not bundled. It is not needed for
the saved-verdict command. Consult the acquisition manifest and the historical packet
builders to obtain original predictions for an end-to-end provenance/harness rerun.

Task metadata, issues and diffs originate in SWE-bench and the respective upstream
repositories; their upstream terms continue to apply. This package does not grant new
rights over upstream materials or invent a project-wide license. A public release owner,
URL/version and appropriate licensing notices still need to be finalized before publication.
