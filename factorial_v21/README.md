# ICSE #6658 v21: new test-blind factorial extension

Two pinned Qwen models each evaluate1203candidates under four frozen conditions:
707unique developer gold patches,194resolved and302unresolved same-task Agentless
candidates. E explains potentially omitted test files; B narrows merge-blocking
guidance. All conditions withhold test outcomes and candidate source. This is a
new instrument, not historical causal recovery or unseen-task validation. The14B
model is AWQ; a cross-model comparison does not isolate a size effect.

Full raw responses, inputs, four-condition exclusions/failures, request accounting,
frozen prompts/code and analysis are in the release evidence ZIP. Missing outputs
are never recoded as rejections. No answer-driven retries or significance hunting.
Functional labels are inherited proxies, not maintainer truth. Independent humans,
native unavailable prior-system APIs and historical snapshots remain unresolved.

## Offline analysis

Unzip the evidence ZIP into a NEW folder. Install Python3.12, numpy2.5.4 and
scipy1.17.1 in a suitable environment. From any directory:

    python /path/to/bundle/tools/reproduce_offline.py /path/to/bundle /path/to/NEW_output

The output directory must not exist. The relocation map verifies every frozen
resource, including bundled small model metadata, then replays the original frozen
analysis and requires identical JSON values. No model weights, API keys or GPU are
needed for this analysis. Model weights are not included. Original source paths in
FREEZE.json and all inference-record freeze hashes are preserved unchanged.

Fresh inference needs the shared model revisions, GPU/runtime and protocol; absolute
workspace paths in the original scripts require adaptation. Such adaptation is a
new run, not a claim of bitwise inference identity.

The paper remains ten total pages. One redundant rates-only figure is replaced by
the new factorial table; font/margin settings are unchanged. Historical results and
limitations remain. The test-patch definition is clarified. This is no conference
submission or publisher PDF certification. All prior data and releases remain.
