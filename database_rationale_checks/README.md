# Targeted real SQLite checks (v9)

Two purpose-selected follow-ups use complete pinned Django source packages with a
real SQLite database. Five separate variant processes cover 15 scenarios across
two tasks. These are not full Django-suite or SWE-bench harness runs, human
adjudication, historical-runtime reproduction or a rationale-accuracy estimate.

- Django 11179: regular cascade and two-instance paths clear PKs before and after
  the archived developer patch, contradicting the focal stale-PK objection. Only
  the fast-single path needs the one-line fix.
- Django 13028: base and the archived failing candidate raise NotSupportedError
  on the real ForeignKey filter with filterable=False; the developer patch
  returns the expected row. True and no-field controls succeed in all versions.

The first five startup attempts failed because Python 3.12 removed distutils.
Their logs and the prior probe are retained. The successful run uses setuptools
80.9.0's real vendored distutils; tested Django logic is unchanged.

Offline observation verification (no source download or inference):

    python database_rationale_checks/tools/verify_integration_results.py --output /tmp/icse6658-new-db-observation-check.json

To rerun the actual database checks, choose a new work directory and a Python 3.12
environment. Source archives are downloaded from immutable commit URLs; no model
files, credentials, GPU or model API are needed. Do not reuse an existing output.

    python database_rationale_checks/tools/acquire_django_integration.py --output /tmp/icse6658-new-db-run
    python -m pip install --target /tmp/icse6658-new-db-run/runtime_dependencies --no-compile requests==2.32.5 pytz==2020.1 sqlparse==0.3.1 asgiref==3.2.10 setuptools==80.9.0
    python database_rationale_checks/tools/run_django_integration.py --integration /tmp/icse6658-new-db-run --run-name execution_v2
    python database_rationale_checks/tools/verify_integration_results.py --integration /tmp/icse6658-new-db-run --output /tmp/icse6658-new-db-rerun-check.json

The acquisition tool itself requires requests. Install that in the calling Python
environment if needed. Preserved full-source machine paths are provenance, not
portable dependencies; observation verification follows recorded paths without
requiring those local trees. Archive/file SHA verification additionally runs when
the reacquired sources are present. The runtime is modern, not the original one.

The census covers exactly lite/verified/verified_negctrl; agents/human_subset are
outside scope. It indexes 7,011 saved outputs, including 18 explicit null/parse
failures. 3,262 nonaccepted records remain NOT_ADJUDICATED. Repeated outputs are not
independent tasks. The 221 absent hosted-negative positions are candidate-pool
positions, not 221 established failed calls. See census_v1_SCOPE.md.

    python database_rationale_checks/tools/census_archived_rationales.py --historical historical_analysis --output /tmp/icse6658-new-census

The public packet/verdict/diff inputs predate this supplement and remain unchanged.
The two upstream Django licenses are included. No blanket license is assigned to
third-party source materials. Full downloaded research-paper PDFs and private
review/response documents are excluded from this public package.
