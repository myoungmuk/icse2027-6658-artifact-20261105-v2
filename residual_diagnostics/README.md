# v13: residual diagnostics beyond four earlier limits

Four post-hoc cases use13 complete pinned source trees. Final26 CPU processes
comprise13 original/amended-policy test runs(122 executed slots, zero skips) and
13 witness runs(51 scenarios). Ten replaced setup/collection attempts remain
archived,36 attempts total. Infrastructure errors are not product failures.

- Django13568: actual missing-import NameError. An import-only diagnostic then
  suppresses E003/W004 for multi-field and conditional constraints; the developer
  control retains those checks. The diagnostic is distinct from the candidate.
- sklearn25102: default-output NameError and integer StandardScaler truncation
  to[-1,0,1]. The PCA renamed-column path succeeds in every variant, limiting broad
  assertions about all changing-column outputs.
- Astropy13236: ordinary Column conversion occurs in candidate and developer,
  so type change alone does not prove premature incompatibility. The candidate
  emits a misleading future warning and loses structured masks. Separately
  ignoring FutureWarning still leaves the official masked-column test failing.
  Original and amended warning policies are reported separately.
- xarray6744: Dask2022.9.2 enables all32 slots per variant, including48 slots
  skipped across the three variants in v11. Base6 failures, candidate12, developer0.
  NumPy/Dask witnesses under two min_periods conditions reproduce repeated labels
  and missing right-edge windows. All final developer controls pass.

Recompute offline with Python's standard library, using a new output:

    python residual_diagnostics/tools/analyze_v13.py --output /tmp/icse6658-v13.json

This reads preserved raw unittest/JUnit/observation outputs and verifies input and
amendment hashes. Full source, dependencies and native binaries are omitted; the
copied-source manifest records immutable original archive/commit provenance in
the existing official_regression_audit evidence. CASES includes exact patches and
test inputs. For fresh execution acquire source into a NEW directory, apply the
recorded patches, reproduce v11 runtimes/native builds, then install the11 pinned
dependency wheels into a separate v13 target. Preparatory scripts record site-local
recipes; they are not portable container harnesses. Never rerun preparation against
preserved source trees. Third-party source/test terms remain those of upstream;
no blanket new license is assigned to their patches.

Post-hoc purposeful witnesses are not population error estimates or independent
human ratings. Full-native same-task comparisons, historical snapshot recovery
and independent rationale adjudication remain incomplete. Reflog/unreachable-object
audit finds no additional records in this repository; external absence is not
proved. No new model inference, GPU allocation or human response. The manuscript
remains9 body+1 reference pages; prior releases and all protected originals remain.
