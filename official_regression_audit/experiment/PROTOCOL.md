# v11 official-regression replay of all 16 Django hosted-negative rejections

The scope is fixed before execution: every archived hosted nonaccepted Django
candidate in the Verified negative cohort, 16 of 38 nonaccepted failing candidates.
No new model judgments or independent human ratings are obtained. The other 22
cases and other reviewers are outside this replay. Existing saved judgments stay
unchanged; this study does not rehabilitate their false test-pass input assertions.

For each case use the complete upstream repository at the immutable SWE-bench
base commit, archived candidate source diff, official developer source diff and
official SWE-bench test_patch. Three isolated variants are base+test_patch,
candidate+test_patch, and developer+test_patch. Preserve every patch-application
failure; do not repair candidate/developer logic or alter official test assertions.
Record source archive hashes, patch hashes, modified source/test hashes and full
application output. Reuse an existing archive only at the identical commit/hash.

Select official regression targets mechanically, before running any test: from
test_patch identify added-line locations in files under tests/ named test*.py or
tests.py. After applying test_patch, select unittest test_* methods whose AST
span (including decorators) intersects added lines. If a touched test module has
no such method, run that whole module. Models/helpers are applied but not treated
as standalone tests. Also include every official FAIL_TO_PASS method ID that can
be mechanically resolved against the complete source. Normalize duplicated method
suffixes in archived labels and map description-only labels to matching method
docstrings; retain unresolved labels explicitly. Final targets are recorded after
source acquisition, before execution, in TARGETS_FINAL.json. Record targets and require the same target list for all
three variants. This mapping is distinct from reproducing every historical
FAIL_TO_PASS/PASS_TO_PASS label, some of which are shortened human descriptions.
It is not the entire upstream test suite or full SWE-bench container harness.

Run official tests/runtests.py with --settings=test_sqlite --parallel=1 and
--verbosity=2. Use fresh CPU processes on recorded Python 3.12 and pinned shared
dependencies under this new workspace. Old Django imports may need setuptools'
vendored distutils, provided before loading Django without changing tested code.
This is a modern replay environment, not the historical execution image. Bound
each process to 180 seconds; timeouts, infrastructure/import errors and skipped
tests remain explicit. Up to four CPU subprocesses may run concurrently.

Freeze protocol, case inputs, launcher, orchestration and all selected target/
source receipts before the first test process. Record per-test success, failure,
error and skip events, exact traceback and process exit code. No failed output is
imputed as a genuine regression when no test ran or infrastructure setup failed.

Primary comparison is candidate versus developer on identical recorded regression
tests. Report base outcomes as a check that a test detects the original issue.
Separate (1) candidate fails and developer passes, (2) both pass, (3) both fail,
(4) candidate passes/developer fails, and (5) incomplete/infra-confounded cases.
Preserve within-case exact failure/assertion details. Passing a targeted regression
does not prove overall patch correctness; a failing regression does not establish
that every sentence in a saved rejection rationale was factually justified.

Only individually checked claim-to-assertion links may be stated as supported.
Counts of regression-supported cases are not a rationale-accuracy estimate.
No independent adjudication, population objection-error rate, causal test-status
experiment, maintainer-quality truth, or replacement for deferred humans is claimed.
New official-test executions are counted separately from full harness runs (zero).
