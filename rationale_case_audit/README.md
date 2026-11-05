# Six focused technical rationale checks

This post-hoc audit selects the first two non-accepted instances in lexical ID order
separately for resolved-agent (30 available), historical-gold (3), and failing-agent
(38) archived Claude CLI outputs. It is not preregistered and does not sample other
reviewers or accepted patches. The focal claim for each case and scope of each probe
are recorded in RESULTS.json. Secondary statements are not all checked.

Each directory preserves the rendered packet, saved verdict, immutable upstream base
file, applied candidate file, diff, download URLs/hashes and exact upstream license.
Diff application was checked against the pinned base without fuzzy patching. No
historical verdict is changed. Stand-ins/synthetic inputs are explicitly documented.

    python tools/probe_rationale_cases.py --output /path/to/new-output-directory

Five focused local claims are supported, while the django-11179 gold objection about
regular-path PK cleanup is contradicted by existing cleanup in both base and patched
source. The matplotlib-26113 gold concern has local support. These observations do
not make all gold rejections erroneous or all model reasons correct, and do not
establish a hallucination rate or maintainer mergeability truth.

The probes execute exact extracted functions or branches; their surrounding libraries
and databases are not integrated. There are no new full SWE-bench harness runs,
model calls, independent human judgments, or post-merge bugs/churn measurements.
Python version and complete input/binding scope are recorded in the results. An
initial implementation selected another reducer expression in the Matplotlib file;
the extractor was corrected to select Axes.hexbin's len(acc) branch before the final
six-case run. This was an extraction bug, not a changed case selection or model output.

Upstream Django, Matplotlib and Astropy source retains its included exact-commit
license. This supplement assigns no blanket license to third-party materials.
