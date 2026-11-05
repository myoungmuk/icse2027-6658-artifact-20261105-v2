# ICSE #6658: two related-work adapters, frozen pilot v1

This is a newly executed, controlled **pilot of method adaptations**, not a
reproduction of the original papers' reported results. Protocol and executable
prompts are frozen by `freeze_manifest.json` before any new model verdicts.
The date in the directory is the work date, not the original data collection date.

## Scope and sources

1. Shi et al., *Towards a Human-in-the-Loop Framework for Reliable Patch
   Evaluation Using an LLM-as-a-Judge*, arXiv:2511.10865v1, sections 3.1, 3.2,
   6.1. We implement the **unrefined draft-rubric ablation**: generate one
   per-issue rubric from the issue and developer patch; evaluate candidates with
   the rubric. Its original human editing and second-human confirmation are
   **not performed**. No golden-rubric or human-consensus claims are allowed.
   No runnable author implementation or exact prompt was identified in the
   retrieved manuscript. Our prompt is a documented reconstruction.
2. Cihan et al., *Evaluating Large Language Models for Code Review*,
   arXiv:2505.20206v1, section III-B, figure 2; Zenodo 14962566 replication
   package. We adapt its problem-description condition, retaining functionality,
   edge-case and change-required checks. A repository diff replaces a standalone
   HumanEval function. The correction-generation task is removed and the output
   is standardized to a common binary JSON schema. This does not reproduce its
   correction/regression metrics, original GPT-4o/Gemini models, or three runs.
3. ICSE comparator: a new test-blind adaptation of the calibrated maintainer
   review prompt, retaining functional, regression, compatibility and quality
   concerns. False claims that CI passed are removed. This is **not** a rerun of
   the historical calibrated instrument unchanged.

## Sample frozen without seeing new verdicts

Use preserved SWE-bench Verified metadata and Agentless 1.5 GPT-4o packets.
Select ten officially resolved and ten officially unresolved nonempty Agentless
patches, separately, by ascending SHA256 of
`ICSE6658-two-baselines-v1:` + instance_id. Eligibility requires the complete
issue <=6000 characters, agent patch <=16000, developer patch <=16000, and their
combined length <=30000. No truncation. Record all exclusions.
For each of the twenty tasks, include its agent and developer patches: **40
patches x 3 arms = 120 binary judgments**, plus twenty draft-rubric generations.
The selection does not aim for repository balance; report its repository mix.
Candidate source, packet ID, execution label and the other candidate are hidden
from judging messages. Rubric generation never receives the agent patch or
candidate execution outcome.

## Shared and method-specific conditions

All arms: the same pinned Qwen2.5-Coder-7B-Instruct backbone, complete issue and
candidate diff, single greedy generation (no sampling), seed 6658, bfloat16,
batch size 4, at most 12288 input tokens and 512 new tokens per judgment.
Rubric generation: same model, at most 1024 new tokens. Overlong input is a
reported failure; never silently truncate. The model uses its local chat
template. There are no new model downloads and no external model APIs.

Binary output for all arms: `{"verdict":"ACCEPT|REJECT","reason":"..."}`.
Parse only the required JSON object with exact allowed values. No retry,
repair, or mapping a missing/malformed answer to REJECT. Record input/output
tokens, raw output, finish reason, elapsed time, failure and all messages.

The draft-rubric arm has **additional reference information and generation
cost**: its rubric comes from the developer patch. The other arms do not receive
that reference. This is method-native information access, **not an
information-matched causal comparison**. Results cannot establish which complete
system is better. Gold acceptance in that arm is particularly reference-biased.

## Endpoints and analysis

Primary descriptive endpoint: binary agreement with **official functional
execution labels on the twenty agent patches**, with 10 positives and 10
negatives. Those labels are inherited, not newly harness-tested here, and are
not human mergeability truth. Report coverage, confusion counts, accuracy,
sensitivity, specificity and balanced accuracy. Accuracy on valid responses is
accompanied by planned-denominator correct fraction and failures; no imputation.
Report Wilson intervals for accuracy, sensitivity and specificity; intervals
are descriptive for this small, restricted pilot.

Secondary endpoint: developer-patch acceptance on twenty tasks, separately.
Developer patches are historical reference fixes, not newly executed ground
truth here. Do not mix their assumed correctness into primary accuracy.
All methods use the same tasks. Report paired decision differences and raw
counts; no confirmatory superiority claim or post hoc tuning. One call per
candidate is not a stability or model-family study. No human review or utility
validation is claimed. Any later revision must be a new protocol/run version.

## Preservation and run completion

Read original files only; all new files live in this new directory. SHA256 all
input files and verify they remain unchanged. Save frozen source/prompt/sample
hashes, model config hashes, runtime package versions, GPU job IDs/logs/status.
Use `aise-gpu` on a canonical node verified by `aise-node status`. Confirm
terminal job state and automatic GPU release. Never overwrite existing ICSE
reports, camera-ready PDF, archives or original research files.
