#!/usr/bin/env bash
set -euo pipefail
set -C
TASK_ROOT=/workspace/users/2022810001/ICSE2027_6658_IndependentCalibration_20261105_v10/experiment
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1
python3 -m venv --system-site-packages "$TASK_ROOT/runtime_gpu"
"$TASK_ROOT/runtime_gpu/bin/python" -m pip install --disable-pip-version-check 'transformers==4.56.2' 'accelerate==1.10.1' > "$TASK_ROOT/runtime_install.log" 2>&1
"$TASK_ROOT/runtime_gpu/bin/python" "$TASK_ROOT/run.py" > "$TASK_ROOT/inference.log" 2>&1
