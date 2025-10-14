# 初始化conda环境
conda init
conda activate prc_aignite
export PAPERIGNITION_LOCAL_MODE="false"
export VOLCENGINE_AK="${VOLCENGINE_AK}"
export VOLCENGINE_SK="${VOLCENGINE_SK}"
export http_proxy="http://127.0.0.1:7890" 
export https_proxy="http://127.0.0.1:7890"
cd /data3/guofang/peirongcan/PaperIgnition
python3 orchestrator/orchestrator.py