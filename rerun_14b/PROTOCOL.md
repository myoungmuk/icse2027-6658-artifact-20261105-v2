# v14: known-condition 14B rerun and separate prospective validation

The user authorized the previously unexecuted evaluations. Original research,
previous releases and v13 remain unchanged. No human labels are collected.

## Archived-instrument rerun

Repeat all2,197 archived14B packet/configuration records: Lite192 and Verified388
each under strict and calibrated prompts; negative-control302, additional-agent
gold288, RAG14, SWE-agent168 and OpenHands265 under the calibrated prompt.
Use the original issue/diff truncation, templates, taxonomy, parser and
normalizer, including three attempts with temperatures0/.3/.3 and1,200-token cap.
Store every raw response, retry, finish reason, invalid result and normalized
verdict separately. Do not write into review_swe. Repeated packets across scopes
are not independent observations.

The original negative-control pass assertion is false. Preserve it explicitly
to measure the archived instrument again; do not present this arm as a corrected
or validated functional-discrimination experiment. Its results cannot justify
merging a test-failing patch. Historical normalization may accept noncanonical
schema fields; record a separate strict-schema flag without silently changing
the historical rules.

The named repository is Qwen/Qwen2.5-Coder-14B-Instruct-AWQ, pinned now to
eb3172f06a6d6b3a15f08947b0668d782e4d2d2c. The catalog had no HF14B-AWQ snapshot;
download into the canonical shared immutable path and verify upstream LFS SHA256.
Do not substitute installed Ollama/GGUF or non-Coder models. Use vLLM0.10.2,
float16/AWQ-Marlin, seed6658, max context32768, JSON-object constraint as requested
by the original client. Model revision, historical server build, seed/hardware
and numerical behavior were not fully recorded in the old experiment. Thus this
is a rerun of known inputs/settings, not an exact historical runtime recovery,
bit-identical reproduction or missing hosted-model snapshot reconstruction.

## Separate task-disjoint validation

Use the pinned full SWE-bench and SWE-agent historical sources from v10. Exclude
the707 previously reviewed tasks AND the140 v10 development/heldout tasks.
From the remaining eligible nonempty unresolved predictions, fix SHA256 ordering
with new v14 salt. Select40 development tasks and100 heldout tasks. Freeze both
strict/adjusted test-blind7B-study prompt adaptations, now applied to14B. No test
outcomes, paired/reference patch or source label enter the judging messages.
Do not truncate complete issue/diff inputs. Retain context-overlength cases as
missing, not rejections or replacement tasks. Each task has developer and
official-unresolved candidates under both arms,560 planned records.

Generate160 development records, choose higher planned-denominator proxy
agreement (developer ACCEPT + unresolved REJECT)/80; invalid counts as0 correct,
ties choose strict. Seal choice and all development hashes BEFORE generating
400 heldout records. Do not retune after heldout results. Record all arms and
the selected arm; report valid/planned counts, complete-pair proxy agreement,
class acceptance, McNemar discordance and task-bootstrap95% intervals.

Historical functional labels are proxies, not maintainer decisions. This new
task-disjoint experiment cannot repair historical task reuse. Repository overlap,
semantic similarity and training exposure are not excluded. Prior7B outputs
have been examined, but these140 tasks were not in their development/heldout set.

## Native prior systems and delivery

Cihan's native Azure GPT-4o/Gemini requires a user-owned API connection. None is
configured; the user explicitly chose to continue14B without that connection.
Do not use credentials embedded in a third-party replication package. Shi's
full pipeline includes excluded human refinement; its prior draft adaptation is
not renamed a full reproduction. The exact old hosted snapshot is unavailable.
Record these boundaries as unexecuted, with no invented outputs.

Freeze protocol, complete inputs and execution scripts before first model call.
GPU work uses aise-node/aise-gpu only. Record canonical node, job ID, status and
automatic release. Produce analysis and reports in new paths; retain the10-page
manuscript limit. Adding runs does not automatically change49/58 checklist count.
