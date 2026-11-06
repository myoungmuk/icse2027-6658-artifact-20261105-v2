# Fresh 14B-AWQ rerun and separate task-disjoint validation

This version performs fresh inference for all 2,197 archived 14B packet/configuration
records and 560 separately frozen task-disjoint inputs. Actual generation calls:
2,756. It is not merely a replay of saved author outputs.
Every retry, raw output, finish reason, context exclusion and normalized verdict is
retained. Byte-exact historical baseline JSON and packet keys support offline
old/new comparisons. Repeated packets/scopes are not independent tasks.

The new 140-task selection excludes the previous 847 tasks, uses 40 development
and 100 heldout tasks, and seals the selected arm and development hashes before
heldout inference. Selected arm: adjusted. Functional labels are
historical proxies, not new maintainer ratings or a fresh container harness.

Recompute with standard Python using a NEW output path:

    python rerun_14b/tools/analyze_portable_v6.py --output /tmp/icse6658-v14-analysis.json

Four setup attempts failed before generation; run_v1, run_v2 and run_v3 retain
their environment records. Cache-path, process-identity and engine JSON-backend
recoveries are frozen in RUNTIME_AMENDMENT_V4.json, V5.json and V6.json.
A shared dependency-installation failure created no run_v4 directory; the ephemeral
runtime recovery is frozen in V7.json. ACTIVE_RUN_V3.json selects run_v4.
A fifth setup attempt was cancelled after a stalled optional dependency download;
V8.json pins the previously installed package versions without unused Ray cgraph
CuPy/cuda-pathfinder. The sixth attempt initialized and submitted 48 first-batch requests, but Triton
host-C compilation failed before any output. V9.json provides a verified compiler
and adds request submission/completion ledgers. ACTIVE_RUN_V4.json selects run_v5.
Those 48 earlier failed submissions are separate from completed generation calls.
No account changes or replaced model results.

The Triton host launcher uses verified Zig 0.13. See compiler_acquisition.json
for its official URL/hash and the included GPU preflight receipts. The compiler
archive and extracted binaries are not redistributed; obtain it in a NEW runtime
for new inference.

Model repository: Qwen/Qwen2.5-Coder-14B-Instruct-AWQ; immutable revision
eb3172f06a6d6b3a15f08947b0668d782e4d2d2c. Acquisition receipts verify every shard
against upstream SHA256. Weights are not redistributed. The new serving stack is
vLLM 0.10.2, AWQ-Marlin and float16 with a fixed seed. Historical revision/server/
numerical identity was incompletely logged, so exact old-runtime reproduction is
not claimed. The archived negative-control assertion of passing tests is known
false and remains present ONLY to rerun that historical instrument. These repeats
do not repair or validate that control. The disjoint study supplies no test result.

Native Cihan GPT-4o/Gemini inference requires a user-owned connection; the user
confirmed none and chose to continue 14B. Third-party embedded credentials are not
used or bundled. Shi's full human refinement remains excluded. No adapted method
or native saved-output replay is relabeled a full original-system replication.

Local preparation scripts record site-specific source/model paths. For new
inference create a NEW workspace and runtime, obtain original public source data,
update paths in a new configuration and freeze it again. Do not rerun preparation
against preserved trees. The standard-library result analysis is portable.
All upstream patches, benchmark inputs and third-party source retain their
original terms; no blanket new license is assigned. No model weights, private
review record, human answer key or authentication files are included.

The manuscript remains 9 body + 1 reference pages. Earlier artifacts/releases and
protected originals remain intact. Conference submission and portal-title
verification are separate and incomplete. Checklist coverage remains 49/58;
new generation counts are not an automatic completion percentage.

The completed archived rerun contains 2,197 valid canonical-schema decisions and
one retry (2,198 returned requests). The disjoint study generates 558/560 inputs;
two development inputs exceed context and remain missing, with no replacement.
All 400 heldout inputs are valid. There are 2,756 returned generation requests and
48 separately retained failed-batch submissions (2,804 submissions in total).
