#!/bin/bash

export PATH="/data3/guofang/anaconda3/bin:$PATH"
eval "$(/data3/guofang/anaconda3/bin/conda shell.bash hook)"

conda activate vllm

# --- 启动 vLLM 后台 ---
CUDA_VISIBLE_DEVICES=1,2,3,4 \
vllm serve /data3/guofang/peirongcan/vllm_log/Qwen3-235B-A22B-Instruct-2507-FP8 \
    --tensor-parallel-size 4 \
    --trust-remote-code \
    --host 0.0.0.0 \
    --port 5666 \
    --served-model-name Qwen3-235B-A22B-Instruct-2507-FP8 \
    > vllm.log 2>&1 &

VLLM_PID=$!
echo "[INFO] vLLM started with PID ${VLLM_PID}"

# --- 注册脚本退出时自动清理 vLLM ---
cleanup() {
    echo "[INFO] Cleaning up vLLM (PID $VLLM_PID)..."
    kill $VLLM_PID 2>/dev/null
}
trap cleanup EXIT

# --- 等待端口5666可访问 ---
echo "[INFO] Waiting for vLLM API to become ready..."
while ! nc -z 127.0.0.1 5666; do
    sleep 1
done
echo "[INFO] vLLM API is ready."

# --- 继续执行 orchestrator ---
conda activate prc_aignite

export VOLCENGINE_AK=""
export VOLCENGINE_SK=""
export http_proxy="http://127.0.0.1:7890"
export https_proxy="http://127.0.0.1:7890"

python /data3/guofang/peirongcan/PaperIgnition/orchestrator/orchestrator.py development_config.yaml
