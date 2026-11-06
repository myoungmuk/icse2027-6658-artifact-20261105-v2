#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT=/workspace/users/2022810001/ICSE2027_6658_Rerun_20261106_v14
TASK_RUNTIME=/tmp/icse6658-v14-runtime
export PYTHONUNBUFFERED=1
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_NO_USAGE_STATS=1
export DO_NOT_TRACK=1
python3 -m venv --system-site-packages "$TASK_RUNTIME"
"$TASK_RUNTIME/bin/python" -m pip install --no-cache-dir --disable-pip-version-check 'vllm==0.10.2' 'transformers==4.56.2' > "$TASK_ROOT/evidence/runtime_install.log" 2>&1
for TASK_WAIT_STEP in $(seq 1 180); do
  if [[ -f "$TASK_ROOT/evidence/model_acquisition.json" ]]; then break; fi
  sleep 5
done
test -f "$TASK_ROOT/evidence/model_acquisition.json"
"$TASK_RUNTIME/bin/python" "$TASK_ROOT/tools/run_inference.py" > "$TASK_ROOT/evidence/inference.log" 2>&1
