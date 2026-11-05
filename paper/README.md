# ICSE #6658 camera-ready candidate (2026-11-05, v2)

The approved displayed title is **Beyond %Resolved:Reassessing SWE-bench Through Human
and LLM Code Review**. Authors: Myeongmuk Kang and Geunseok Yang, Hankyong National University.
This is a revised local manuscript, with outstanding publication facts tracked separately.

## Build the supplied source

The generated table/figure inputs are included. No model calls or result analysis are
needed to typeset the supplied source. Use Tectonic 0.17.0:

```bash
make build
```

The first build can fetch TeX resources from the specified `tlextras-2022.0r0.tar` bundle.
An existing cache permits adding `--only-cached` to `TECTONIC_FLAGS`. Alternatively,
compile `main.tex` with a standard LaTeX/BibTeX toolchain containing IEEEtran and the
listed packages. The supplied build selects T1 font encoding before IEEEtran.

For historical analysis reproduction, follow `../historical_analysis/REPRODUCE.md`.
The resulting eight `.tex` tables and three PDF figures go under `paper/generated/`.
`make analyze` performs this copy from the historical package beside this directory.
For the new pilots, run `python ../tools/reproduce_pilots.py --output <new-directory>`
with a new directory outside this repository. This does not perform new inference.

This manuscript uses IEEE `10pt,conference` with the standard margins and body font size.
The user's binding limit is **9 body pages + 1 reference page, 10 pages total**.
Both user-supplied ORCIDs are included. The public artifact is versioned at
https://github.com/myoungmuk/icse2027-6658-artifact-20261105-v2/releases/tag/2026.11.05-v2 .
The new Table IX reports the prospective disjoint pilot, separately from historical data.
Shi's formal AI-SQE 2026 citation is verified through Crossref; the experimental
method remains pinned to arXiv:2511.10865v1.

Confirm the latest private author kit, corresponding-author designation, rights/DOI
metadata, and any publisher-specific PDF validation before final conference upload.
Do not substitute invented values. The supplied PDF was built from this source;
its SHA-256 is recorded in `../submission_metadata.json`. Local checks do not certify
PDF eXpress acceptance. No final conference upload is claimed.
