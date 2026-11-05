# Recreate the revised saved-verdict results

Use an extracted working copy and Python 3.12. The supplied requirements were
fresh-installed successfully with Python 3.12.13 for this release candidate.

```sh
python -m venv .analysis-env
.analysis-env/bin/python -m pip install -r requirements-analysis.txt
.analysis-env/bin/python tools/verify_manifest.py
.analysis-env/bin/python scripts/22_camera_ready.py
.analysis-env/bin/python tools/verify_manifest.py
```

The analysis can run from another current directory using the absolute script path.
It writes only `results/camera_ready/`; run it in your extracted working copy.
The packaged results were regenerated in a new environment, and all 13 expected
outputs matched their frozen November 3 hashes. The second manifest check verifies
the same files after your own regeneration. Keep your installation environment and
logs outside the included file set; they are not scientific observations.

Eight `.tex` tables and three `.pdf` figures can be copied into the separately
packaged paper's `generated/tables/` and `generated/figures/`. `metrics.json` and
`verdict_inventory.csv` are the other two regenerated outputs.

No model downloads, model/API calls, independent human labels, or external repository
test commands are needed. The exact hosted Claude snapshot and intermediate rubric
history remain unavailable. The negative-control inputs contained a false test-pass
assertion; regenerating those archived rates does not repair that experiment.
