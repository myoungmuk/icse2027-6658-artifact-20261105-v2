# Post-hoc targeted longitudinal source-history audit

Scope frozen before retrieving history: ALL THREE nonaccepted historical gold
patches in archived hosted reviewer Verified outputs (django11179,
matplotlib26113, scikit-learn11578). This is an exhaustive tiny reviewer-specific
subgroup, not all gold patches or other reviewers. No outcome-driven case selection.

Locate original PR, merge SHA/time. Follow default-branch history for 365 days
strictly after merge, for every source file touched by the supplied gold patch.
Record commit counts, file additions/deletions and whether subsequent hunks intersect
the gold-modified functions. Inspect messages/diffs for evidence linked to the
reviewer's specific concern. Pure churn is not a defect; a later fix or shared-file
change alone cannot be attributed causally to the original patch. Explicit linked
regression/bug and overlapping code are stronger descriptive evidence, not proof.
Save API URLs, queried refs, pagination, fetched_at, content hashes and source
receipts. Missing, truncated or inaccessible histories remain unknown, never zero.
Use immutable merge and end commit refs where available; include end-of-window
commit for default-branch snapshot. Report each case and limitations separately.
This is not independent maintainer defect adjudication or all-gold error incidence.
