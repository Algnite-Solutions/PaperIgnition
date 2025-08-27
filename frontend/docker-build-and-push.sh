#!/bin/bash

# PaperIgnition 前端 Docker 构建和推送脚本
# 在 Windows 上构建镜像并推送到 Docker Hub

echo "🔨 开始构建和推送 PaperIgnition 前端镜像..."

# 配置变量
IMAGE_NAME="paperignition-frontend"
TAG=${1:-latest}
REGISTRY=${2:-""}  # 可选：指定 Docker Hub 用户名

# 如果指定了 registry，则使用完整名称
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME"
else
    FULL_IMAGE_NAME="$IMAGE_NAME"
fi

echo "📦 镜像名称: $FULL_IMAGE_NAME:$TAG"

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ 错误: Docker 未运行或无法连接"
    echo "💡 请确保 Docker Desktop 已启动"
    exit 1
fi

echo "✅ Docker 环境检查通过"

# 构建镜像
echo "🏗️  构建 Docker 镜像..."
docker build -t $FULL_IMAGE_NAME:$TAG .

# 检查构建是否成功
if [ $? -ne 0 ]; then
    echo "❌ 镜像构建失败"
    exit 1
fi

echo "✅ 镜像构建成功: $FULL_IMAGE_NAME:$TAG"

# 显示镜像信息
echo "📋 镜像信息:"
docker images | grep $IMAGE_NAME

# 询问是否推送到仓库
read -p "🚀 是否推送镜像到仓库? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -n "$REGISTRY" ]; then
        echo "🔐 登录到 Docker Hub..."
        docker login
        
        if [ $? -ne 0 ]; then
            echo "❌ Docker Hub 登录失败"
            exit 1
        fi
    fi
    
    echo "📤 推送镜像到仓库..."
    docker push $FULL_IMAGE_NAME:$TAG
    
    if [ $? -eq 0 ]; then
        echo "✅ 镜像推送成功!"
        echo "🌐 镜像地址: $FULL_IMAGE_NAME:$TAG"
        echo ""
        echo "📋 在 Linux 服务器上使用以下命令拉取和运行:"
        echo "   docker pull $FULL_IMAGE_NAME:$TAG"
        echo "   docker run -d -p 10086:10086 \\"
        echo "     -e SERVER_NAME=你的服务器IP \\"
        echo "     -e BACKEND_API_URL=http://10.0.1.226:8888 \\"
        echo "     --name paperignition-frontend \\"
        echo "     $FULL_IMAGE_NAME:$TAG"
    else
        echo "❌ 镜像推送失败"
        exit 1
    fi
else
    echo "⏸️  跳过推送，镜像仅保存在本地"
    echo ""
    echo "💡 如需推送，请运行:"
    echo "   docker push $FULL_IMAGE_NAME:$TAG"
fi

echo ""
echo "🎉 构建流程完成!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 本地镜像: $FULL_IMAGE_NAME:$TAG"
echo "🔧 使用方法:"
echo "   构建: ./docker-build-and-push.sh"
echo "   指定标签: ./docker-build-and-push.sh v1.0.0"
echo "   指定仓库: ./docker-build-and-push.sh latest your-dockerhub-username"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" 