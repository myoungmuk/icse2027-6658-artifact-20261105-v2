# Third-party provenance and rights notices

This package contains task metadata, issue text, source patches, and saved outputs
derived from SWE-bench, public agent submissions, and upstream repositories. They
retain their applicable upstream terms. This document does not apply a new blanket
license or claim that all materials share one license. No project-wide license for
the researchers' own code has been assigned by this preparation step.

The original acquisition links, hashes, and official experiments commit are recorded
under `data/source_metadata/`. `README.md` explains the historical labels, corrected
metrics, and available acquisition paths. Model weights are not distributed here.

## Representative upstream license snapshots

One task was selected per upstream repository by sorted instance ID, without using
results. The complete license text was fetched at that task's actual base commit.
These samples preserve useful attribution evidence but do not establish coverage
for every base commit or every file. See the manifest for exact URLs and hashes.

| Upstream repository | Representative task | Base commit | Included license text |
|---|---|---|---|
| astropy/astropy | astropy__astropy-12907 | d16bfe05a744909de4b27f5875fe0d4ed41ce607 | third_party/license_snapshots/astropy__astropy__d16bfe05a744.txt |
| django/django | django__django-10097 | b9cf764be62e77b4777b3a75ec256f6209a57671 | third_party/license_snapshots/django__django__b9cf764be62e.txt |
| matplotlib/matplotlib | matplotlib__matplotlib-13989 | a3e2897bfaf9eaac1d6649da535c4e721c89fa69 | third_party/license_snapshots/matplotlib__matplotlib__a3e2897bfaf9.txt |
| mwaskom/seaborn | mwaskom__seaborn-2848 | 94621cef29f80282436d73e8d2c0aa76dab81273 | third_party/license_snapshots/mwaskom__seaborn__94621cef29f8.txt |
| pallets/flask | pallets__flask-4045 | d8c37f43724cd9fb0870f77877b7c4c7e38a19e0 | third_party/license_snapshots/pallets__flask__d8c37f43724c.txt |
| psf/requests | psf__requests-1142 | 22623bd8c265b78b161542663ee980738441c307 | third_party/license_snapshots/psf__requests__22623bd8c265.txt |
| pydata/xarray | pydata__xarray-2905 | 7c4e2ac83f7b4306296ff9b7b51aaf016e5ad614 | third_party/license_snapshots/pydata__xarray__7c4e2ac83f7b.txt |
| pylint-dev/pylint | pylint-dev__pylint-4551 | 99589b08de8c5a2c6cc61e13a37420a868c80599 | third_party/license_snapshots/pylint-dev__pylint__99589b08de8c.txt |
| pytest-dev/pytest | pytest-dev__pytest-10051 | aa55975c7d3f6c9f6d7f68accc41bb7cadf0eb9a | third_party/license_snapshots/pytest-dev__pytest__aa55975c7d3f.txt |
| scikit-learn/scikit-learn | scikit-learn__scikit-learn-10297 | b90661d6a46aa3619d3eec94d5281f5888add501 | third_party/license_snapshots/scikit-learn__scikit-learn__b90661d6a46a.txt |
| sphinx-doc/sphinx | sphinx-doc__sphinx-10323 | 31eba1a76dd485dc633cae48227b46879eda5df4 | third_party/license_snapshots/sphinx-doc__sphinx__31eba1a76dd4.txt |
| sympy/sympy | sympy__sympy-11400 | 8dcb12a6cf500e8738d6729ab954a261758f49ca | third_party/license_snapshots/sympy__sympy__8dcb12a6cf50.txt |

## Local publication status

The package is a prepublication candidate. Before publishing, the release owner
must ensure the notices and redistribution scope match the actual included files.
The representative snapshots are evidence, not a substitute for that decision.
No persistent URL, DOI, or release date is asserted by this document.
