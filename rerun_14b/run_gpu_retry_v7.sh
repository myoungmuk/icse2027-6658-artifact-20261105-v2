#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT=/workspace/users/2022810001/ICSE2027_6658_Rerun_20261106_v14
TASK_RUNTIME=/var/tmp/icse6658-v14-runtime-v6
export PYTHONUNBUFFERED=1
# getpass.getuser() requires a process-local identity; no account/auth changes.
export LOGNAME=2022810001
export USER=2022810001
export TORCHINDUCTOR_CACHE_DIR=/var/tmp/icse6658-v14-inductor
export TRITON_CACHE_DIR=/var/tmp/icse6658-v14-triton
export VLLM_CACHE_ROOT=/var/tmp/icse6658-v14-vllm-cache
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_NO_USAGE_STATS=1
export DO_NOT_TRACK=1
python3 -m venv --system-site-packages "$TASK_RUNTIME"
"$TASK_RUNTIME/bin/python" -m pip install --no-cache-dir --no-deps --disable-pip-version-check -r "$TASK_ROOT/runtime_requirements_v8.txt" > "$TASK_ROOT/evidence/runtime_install_retry_v6.log" 2>&1
"$TASK_RUNTIME/bin/python" -c "import getpass; from vllm.model_executor.models.qwen2 import Qwen2ForCausalLM; print('IDENTITY_AND_MODEL_IMPORT_OK', getpass.getuser())" > "$TASK_ROOT/evidence/import_preflight_v6.log" 2>&1
"$TASK_RUNTIME/bin/python" "$TASK_ROOT/tools/run_inference_retry_v4.py" > "$TASK_ROOT/evidence/inference_retry_v6.log" 2>&1
