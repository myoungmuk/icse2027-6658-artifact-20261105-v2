# Prospective full-split gold and same-task unresolved controls, v1

Frozen before this run's new verdicts. This is a new evaluation of the pinned
Qwen2.5-Coder-7B-Instruct test-blind maintainer adapter already used in the two
pilots. It does not reconstruct or revalidate the historical 14B/hosted instruments.
No rubric or prompt is tuned on this run's outputs. Prior pilot overlap is disclosed;
this is not an independent calibration-development experiment.

Include ALL 300 Lite and 500 Verified developer patches from preserved metadata.
Deduplicate shared task IDs ONLY after asserting identical repository, base, issue
and developer diff; report each split separately and overlap (93), not as 800
independent cases. There are 707 unique gold tasks. No agent-resolved selection,
length restriction, or diff/issue truncation. No tests-passed assertion.

Also include ALL 302 nonempty officially unresolved Agentless candidate packets
in the preserved Verified negative-control collection. Each is compared to its
own developer fix, available in the full 500-gold cohort. Four remaining unresolved
cases have no nonempty candidate packet and are explicitly absent, not assigned
REJECT. Report coverage against 306 unresolved tasks and 302 available candidates.
This does not retroactively repair the historical false-pass negative control.

Exactly the existing icse_test_blind prompt and fenced-JSON parser from follow-up
v2. Source, execution label, task code and the other candidate are hidden from the
judge. No additional rubric/reference enters the candidate prompt. Preserve all
rendered messages, raw responses, token counts, finish reasons and failures.

Model: Qwen/Qwen2.5-Coder-7B-Instruct, revision
c03e6d358207e414f1eca0bb1891e29f1db0e242, existing shared path.
Transformers4.56.2, accelerate1.10.1, bfloat16, greedy, seed6658, sdpa.
Maximum input32256 + output512 <=32768 configured model context. Any excess input
is an explicitly reported unevaluated case, never shortened. Output truncation,
invalid JSON/labels or runtime errors are failures, never mapped to REJECT.

Execution order: increasing exact input-token length, stable task-code tie-break.
Fixed batching: up to8 candidates and max(padded length)*batch <=16384 input tokens;
longer candidates singly. This scheduling is computational only, independent of
outcomes. On CUDA OOM before producing saved responses, clear cache and recursively
split a batch; singleton OOM is recorded. No verdict retries, repair or tuning.

Primary: full-split developer acceptance and format coverage, with both valid and
planned denominators. Secondary: on 302 same-task failing/developer pairs, report
2x2 counts, candidate/developer acceptance, exact McNemar and Wilson intervals.
Intervals/tests are descriptive, not equivalence or causal correctness claims.
Functional labels are inherited; no fresh harness. No human judgments. No claims
of contamination freedom or independently developed historical calibration.

Record input/config/source hashes BEFORE inference, model-config hashes (not a
claim to independently hash all weight shards), runtime and GPU status/job/node.
Run via aise-gpu and verify terminal state/automatic GPU release. Preserve all
previous data, releases and reports. No manuscript page increase: 9+1 pages.
