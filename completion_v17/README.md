# v17 PostgreSQL follow-up and 10-page manuscript

This supplement adds three actual PostgreSQL test processes (39 slots) for Django 16560. The developer patch passes all 13 methods; the candidate has one failure and nine errors. The four previously skipped PostgreSQL-only methods now execute for all three variants. One initial initdb dependency failure produced no study results and is preserved separately.

The combined 38-case ledger retains unchanged v11 results for 36 cases and existing v13 Dask results for one case. The new PostgreSQL execution replaces only the remaining case. All fixed official target IDs are retained. It contains 114 selected variant processes and 447 executed slots, zero skips. This is not 38 freshly rerun tasks, a full SWE-bench container harness, or independent adjudication of every rationale. B03 remains partial; checklist coverage remains 50/58.

This folder is additive to the preserved v15 repository. To replay the analysis with Python's standard library, from the repository root:

```bash
python completion_v17/tools/reproduce_combined_ledger.py --output-dir /tmp/icse-v17-replay-new-directory
```

The replay reads preserved `official_regression_audit` and `residual_diagnostics` raw outputs. New PostgreSQL raw test events, commands, full source-file hashes, package URLs/digests and shutdown evidence are included here. Reconstructing the live test uses the pinned Django commit `51c9bb7cd16081133af4f0ab6d06572660309730` plus the three patches in `official_regression_audit/experiment/sources/django__django-16560/`. Python/dependency versions are in the raw records. No model inference or new human rating is added.

The current manuscript is in `completion_v17/paper`, and the current PDF/source are release assets. Earlier paper directories, tags, raw data and assets remain historical versions. The scientific paper has exactly ten pages; no font, margin, historical-model data, bibliography or figure changes are introduced. Final conference upload, rights and publisher certification await the official author kit.
