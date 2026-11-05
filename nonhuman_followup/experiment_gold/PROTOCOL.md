# Full-package gold rejection witnesses (v12)

All three hosted nonaccepted gold cases; post-hoc technical inspection. Archived
gold diff equals the official developer patch byte for byte for every task.
Base and gold are separate full source trees at immutable task base commits, with
the same official test patch. Native extensions are built from that source once
and used unchanged across Python-only variants; no release-wheel overlays.

Official controls: exact FAIL_TO_PASS pytest parameter labels for sklearn and
Matplotlib; the full Django FastDeleteTests class containing the official new
regression. Full-package witnesses for Matplotlib use empty/singleton C with
max/min/mean reductions and default/explicit mincnt. sklearn compares all fold
scores, selected C, coefficients, intercepts and predictions on Iris, crossing
fit_intercept True/False with ovr/multinomial. A separate external constructor
instrumentation run records the omitted/passed keyword without editing source.

Two diagnostic interventions are explicitly not historical patches: restoring
fit_intercept in the gold sklearn constructor; changing only default mincnt to
one in gold Matplotlib, matching the focal source change in the documented later
upstream fix. They isolate mechanisms; they do not confer maintainer acceptance.
The sklearn comparison records exact equality and maximum numerical differences.
No untested concern is automatically true and no independent human truth labels
or rationale-accuracy percentage are produced.

Freeze case inputs, protocol, targets, launchers and prepared source hashes before
the first test. Use isolated existing CPU dependency environments without changing
them; extra build dependencies live in v12. Preserve every startup/build/test retry
under a distinct output name. Bounded CPU processes, no GPU or model calls.
