#!/bin/bash

# use crontab -e 定时执行
cd /data3/guofang/peirongcan/PaperIgnition
# 设置环境变量
export PYTHONPATH=/data3/guofang/peirongcan/PaperIgnition

# 激活conda环境
source /data3/guofang/anaconda3/etc/profile.d/conda.sh
conda activate aignite

# 切换到工作目录
cd /data3/guofang/peirongcan/PaperIgnition/orchestrator

# 创建日志目录（如果不存在）
mkdir -p logs

# 执行脚本
python generate_default_blogs.py

# 记录执行时间
echo "Script executed at $(date)" >> /data3/guofang/peirongcan/PaperIgnition/orchestrator/logs/paperignition_execution.log