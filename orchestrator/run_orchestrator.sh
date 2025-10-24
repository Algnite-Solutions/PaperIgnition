#!/bin/bash

# 设置conda环境路径
export PATH="/data3/guofang/anaconda3/bin:$PATH"

# 初始化conda环境
eval "$(/data3/guofang/anaconda3/bin/conda shell.bash hook)"

# 激活conda环境
conda activate prc_aignite

# 设置环境变量
export VOLCENGINE_AK="YOUR_VOLCENGINE_ACCESS_KEY"
export VOLCENGINE_SK="YOUR_VOLCENGINE_SECRET_KEY"
export http_proxy="http://127.0.0.1:7890" 
export https_proxy="http://127.0.0.1:7890"

# 运行orchestrator
python orchestrator.py production_config.yaml