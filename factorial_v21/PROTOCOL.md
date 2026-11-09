# ICSE #6658: new test-blind factorial extension, v21

This is a new instrument, not exact recovery of historical prompts, model sessions,
or the causal explanation of the submitted experiment. Tasks have been inspected in
earlier studies; they are not an unseen-task validation set. No maintainer truth or
human adjudication is created by this experiment.

## Fixed scope and factors

Evaluate all 707 distinct developer patches from Lite300 and Verified500 (93 shared
tasks once), all194 resolved Verified Agentless packets and all302 available nonempty
unresolved Verified packets: 1,203 candidates, four conditions, two pinned models.
Four unresolved tasks lack a nonempty candidate and cannot be inferred. Existing
harness labels define functional strata only; the present study does not rerun tests.

Factor E: explain that test files may be omitted from benchmark source packets, or
do not explain that omission. Factor B: use ordinary severity definitions, or add
the narrower concrete-correctness/regression/compatibility blocking guidance.
Conditions E0B0, E1B0, E0B1, E1B1 have identical issue/diff and response schema.
All conditions explicitly withhold execution outcomes, candidate origin and gold
status, and make no claim that tests passed. Full issue and diff are retained.
This also differs from the historical compound prompt in removing its false test
pass claim and retaining full raw responses. E/B effects therefore apply to this
new instrument only, not to the original observed shift.

## Execution and missing data

Reuse shared pinned Qwen2.5-Coder-7B-Instruct and14B-Instruct-AWQ. The14B model is
quantized; between-model differences are not an isolated model-size effect.
vLLM0.10.2, native Torch2.8/CUDA12.8, float16, seed6658, temperature0, output1200,
context32768. JSON-object constrained decoding, not schema-constrained decoding.
One generation per eligible candidate-condition; no answer-driven retries, prompt
tuning or repairing outputs. Reserve1200 output tokens. A candidate exceeding the
context budget under any condition is excluded from all four conditions for that
model. No input truncation. Invalid schema and output length exhaustion remain
missing, never rejections. Store all four planned records including exclusions.
Runtime failure may resume only missing records in a NEW attempt directory with
unchanged frozen inputs; keep submitted-but-unreturned request accounting. No
selective rerun of an observed answer. Both models get the same deterministic
SHA256-shuffled candidate order and counterbalanced condition order.

Store raw text, parsed data, finish reason, token counts, acceptance, prompt hash,
model/config/revision, timestamp, job/node, submitted/completed requests and freeze
hash. Binary acceptance = merge_decision==merge AND no blocking issue. A JSON object
with merge plus a blocker is valid but not accepted. Strict schema checks do not
coerce missing or unknown decisions/severities. Config/tokenizer hashes are checked;
an independent all-weight rehash is not claimed.

## Prespecified analysis

Report planned/eligible/valid/truncated/malformed counts and available-case rates
with Wilson95% intervals; also [accepted/planned, (accepted+missing)/planned] bounds.
For each condition report full gold acceptance in Lite and Verified separately
(overlap is not independent), and all707 unique gold. Compare same-task agent and
developer acceptance separately in194 resolved and302 unresolved populations,
complete pairs only, exact McNemar p and paired task bootstrap95% difference CI.
Functional label agreement is a proxy and not evidence of maintainer agreement.

On complete four-condition candidates, compute E's average effect across B,
B's average effect across E, and the difference-in-differences interaction.
Use task-cluster bootstrap95% intervals so candidate types from a task remain
together. Report these for all candidates and each candidate type. Simple E/B
contrasts use exact McNemar; primary family = four contrasts x three candidate
types x two models (24 tests), Holm adjustment across that family. These are
exploratory task-reuse analyses, not confirmatory unseen-data tests. Do not call
nonsignificance equivalence or optimize the rubric against outcomes.

Report per-condition between-model binary agreement/Cohen kappa on common valid
records, with the quantization/runtime caveat. Publish negative and null results,
all missingness and failures. This extension does not complete unavailable native
Cihan GPT4o/Gemini runs, human-guided refinement, independent human ratings, or
historical snapshot/rubric recovery. No remaining item is marked complete merely
because a new experiment ran. Paper remains ten total pages.
