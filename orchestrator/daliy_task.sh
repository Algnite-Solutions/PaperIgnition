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

# 执行博客生成脚本
echo "Starting blog generation..." >> /data3/guofang/peirongcan/PaperIgnition/orchestrator/logs/paperignition_execution.log
python3 generate_default_blogs.py
echo "Blog generation completed at $(date)" >> /data3/guofang/peirongcan/PaperIgnition/orchestrator/logs/paperignition_execution.log

# 执行推荐生成脚本
echo "Starting recommendation generation..." >> /data3/guofang/peirongcan/PaperIgnition/orchestrator/logs/paperignition_execution.log
python3 run_all_generate.py
echo "Recommendation generation completed at $(date)" >> /data3/guofang/peirongcan/PaperIgnition/orchestrator/logs/paperignition_execution.log

# 记录总执行完成时间
echo "All tasks completed at $(date)" >> /data3/guofang/peirongcan/PaperIgnition/orchestrator/logs/paperignition_execution.log