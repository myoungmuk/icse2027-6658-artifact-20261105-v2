# ICSE 2027 #6658 — local release candidate, 2026-11-05

Paper: **Beyond %Resolved:Reassessing SWE-bench Through Human and LLM Code Review**.
Authors: Myeongmuk Kang and Geunseok Yang, Hankyong National University.

This is a new local analysis release candidate. It has not been uploaded or publicly
released. The original `README.md` describes the November 3 handoff and the scientific
corrections. Read it together with this update; do not infer a public release from a ZIP.

## Reproduction now verified in a fresh environment

Python 3.12.13, a new venv, and a fresh installation of every version in
`requirements-analysis.txt` were used. Running `python scripts/22_camera_ready.py`
from outside this directory passed **223 checks** on 9,256 saved verdict JSON files.
All **13 outputs** matched the November 3 revised outputs byte for byte, including
the eight table inputs and three figures. No models, inference services, GPUs, or
SWE-bench harness executions were used. This verifies the saved-output analysis,
not the missing hosted snapshot or the validity of flawed historical control inputs.

See `REPRODUCE.md`, `release_evidence/fresh_environment_reproduction.json`, and
`release_evidence/fresh_environment_packages.txt`.

## Before any actual publication

Select and verify the real repository/release, record the exact published version,
complete the rights notices appropriate to the files, and add that actual URL to the
paper. The existing origin did not provide unauthenticated access in the November 5
check. No public repository, DOI, ORCID, or corresponding-author designation is invented
here. `CITATION.cff` describes this local candidate and has no fabricated release URL.

`THIRD_PARTY_NOTICES.md` and `third_party/license_snapshot_manifest.json` include
representative pinned license texts for all 12 upstream repositories represented in
the included task metadata. These are one snapshot per repository, not a claim that
every historical commit or redistribution question has been audited.

The accompanying SHA-256 manifest and `tools/verify_manifest.py` support file checking.
The manifest establishes bytes, not scientific validity, participant consent, or rights.
