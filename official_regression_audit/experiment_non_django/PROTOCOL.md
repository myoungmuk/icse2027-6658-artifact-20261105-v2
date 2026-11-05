# Official regression replay, non-Django extension (22 tasks)

This adds all remaining non-Django tasks in the archived hosted reviewer's 38 nonaccepted officially-unresolved candidates. It is a census of this stratum, not all saved reviewer outputs or all failing patches.

Three isolated full pinned-source trees per task: base + official test_patch; archived candidate + official test_patch; developer + official test_patch. No tested source compatibility edits. Native extensions, when required, are compiled from the same pinned base and shared only across these Python-only patch variants. Native build failures are infrastructure failures, never candidate failures. Build/dependency retries retain separate logs and artifacts.

Targets are every official FAIL_TO_PASS function, expanded to all parameter values; short SymPy identifiers map mechanically to matching top-level functions in official test-patch files. One preselected collateral target, xarray3305 sortby, comes from official PASS_TO_PASS and the archived rationale. No other collateral claims are presumed tested.

Run the project's original source under Python 3.9 with isolated pinned dependency environments. PYTHONPATH gives pinned source priority over installed release code. Disable external pytest plugin autoload; project conftest/plugins remain in use. Use real pytest JUnit XML and preserve stdout/stderr, process status and timing. At most four CPU processes; single-threaded BLAS; timeout 240 seconds per variant, process group killed on timeout. Build/dependency/collection errors and skips remain explicit. Repaired environments may be replayed in a new output directory; previous failed attempts remain intact.

Successful functional discrimination requires actual executed test failure/error in candidate and successful developer control with no collection/startup error. A functional failure does not validate every rationale sentence, maintainability objection, security hypothesis or original human review. No new human labels, hosted model calls, full SWEbench container harness runs, or GPU allocation.
