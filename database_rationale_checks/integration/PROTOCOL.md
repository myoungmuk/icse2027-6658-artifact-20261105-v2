# Two pinned-source Django integration checks

Frozen before the first execution of this supplement. These are post-hoc,
purpose-selected checks of two already selected v7 cases, not a new random sample.

1. `django__django-11179`: the entire Django package at
   `19fc6376ce67d01ca37a91ef2f55ef769f50513a`, with and without the archived
   developer candidate. Use real SQLite tables and ORM instances. Check single
   fast deletion, regular deletion with a cascading relation, and two-instance
   Collector deletion. The saved objection says regular-path primary keys remain
   stale. Record actual deleted-row counts, remaining in-memory PKs and SQL.
2. `django__django-13028`: the entire Django package at
   `78ad4b4b0201003792bfdbf1a7781cbc9ee03539`, unmodified, with the archived
   failing candidate, and separately with the official developer patch. Reproduce
   a real ForeignKey QuerySet filter with a related model's `filterable=False`
   field. Include `True` and no-such-field controls. Record real database reads,
   returned row counts and exceptions. Do not substitute attribute-only stand-ins.

Preserve pristine archive hashes, modified file hashes, complete patches, stdout,
stderr, return codes, environment and any execution failures. Run each variant
in a separate process. Never change archived verdicts, project originals or v8.
Runtime compatibility workarounds, if necessary on Python 3.12, must be explicit;
they must not alter the tested Django logic. Versions of third-party runtime
dependencies are recorded. This is not the original historical runtime.

Expectations recorded before execution: in case 11179 the regular paths clear
PKs in both versions while only the fast-single path needs the one-line fix; in
case 13028 the base and failing candidate raise NotSupportedError for False,
whereas the developer patch returns the matching row. Expectations are not results.

Scope: targeted integration against SQLite, not the complete Django suite or
SWE-bench harness, maintainer assessment, independent human adjudication, a
reviewer-wide correctness estimate, or proof of overall patch mergeability.
No GPU, new model calls, or human ratings are planned.
