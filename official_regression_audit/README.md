# Official regression replay of 38 hosted failing rejections (v11)

This is the entire archived hosted-reviewer nonaccepted failing-candidate stratum:
16 Django tasks and 22 other tasks. It is not all reviewers, all 7,011 saved outputs,
or all failing patches. Every task uses its immutable base source and official test
patch in three separate variants: base, archived candidate, and developer patch.

All 38 candidates and bases fail actual executed tests; all 38 developer controls
pass. The final 114 processes enumerate 447 test slots: 387 execute and 60 skip.
24 earlier infrastructure/collection attempts are retained (138 total attempts).
Skips are not executed passes; Django subtest events are not separate test methods.
The official targets expand parameterized labels to full functions and map short
SymPy labels to official test-patch files. One preselected additional PASS_TO_PASS
target, xarray3305 sortby, reproduces the rationale's keep_attrs NameError.

Several archived issue-resolved summaries conflict with official regressions.
The evidence cards explicitly separate observed failures from untested latent
claims. These are author technical notes, not independent human labels or a
rationale-accuracy estimate. Functional rejection support does not prove every
rationale sentence. No full SWEbench container harness, new model inference,
human ratings or GPU work is added by v11. Historical labels remain unchanged.

Recompute the analysis offline with Python's standard library, using a new output:

    python official_regression_audit/tools/analyze_regressions.py --output /tmp/icse6658-v11-new-analysis.json

This checks frozen inputs, raw JUnit/unittest outcomes, controls and denominators.
Original paths in receipts preserve provenance, not portable execution commands.
Full source downloads and compiled binaries are omitted. Receipts record pinned
codeload URLs and archive hashes; CASE_INPUTS contains all tested patches, official
test patches and labels. Native extensions were built from the pinned task source,
not overlaid from release wheels. Generated version metadata, pinned dependencies,
required pytest plugins and preserved failed attempts are disclosed. Core patched
source/test hashes and all 66 non-Django source imports were checked after replay.

For fresh test execution use a new work directory, restore the pinned source from
its receipt, apply the recorded patches, recreate the environment, and freeze that
new run. Do not run acquisition/build tools against these preserved directories.
The original preparatory scripts have site-local Python/runtime paths and form a
recorded recipe, not a general container harness. Upstream terms continue to apply;
no blanket new license is applied to third-party source or tests.
