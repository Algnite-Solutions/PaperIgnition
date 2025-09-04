#!/bin/sh
# Docker容器启动脚本

echo "🚀 启动 PaperIgnition 前端服务..."
echo "🌐 服务器名称: $SERVER_NAME"
echo "🔗 后端API地址: $BACKEND_API_URL"

# 生成nginx配置
echo "⚙️ 生成Nginx配置..."
envsubst "\$SERVER_NAME \$BACKEND_API_URL" < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

echo "✅ 配置生成完成"
echo "🌟 启动Nginx服务..."

# 启动nginx
nginx -g "daemon off;" 