#!/bin/bash

# PaperIgnition 前端 Docker 部署脚本
echo "🐳 开始 Docker 部署 PaperIgnition 前端..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker 未安装"
    echo "💡 请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ 错误: Docker Compose 未安装"
    echo "💡 请先安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ 环境检查通过"

# 检查部署类型
DEPLOY_TYPE=${1:-dev}
if [ "$DEPLOY_TYPE" = "prod" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    echo "🎯 生产环境部署"
else
    COMPOSE_FILE="docker-compose.yml"
    echo "🔧 开发环境部署"
fi

# 创建必要的目录
echo "📂 创建必要的目录..."
mkdir -p logs

# 停止并删除现有容器
echo "🔄 停止现有容器..."
docker-compose -f $COMPOSE_FILE down

# 删除现有镜像（强制重新构建）
echo "🗑️  删除现有镜像..."
docker-compose -f $COMPOSE_FILE down --rmi all

# 构建镜像
echo "🔨 构建 Docker 镜像..."
docker-compose -f $COMPOSE_FILE build --no-cache

# 检查构建是否成功
if [ $? -ne 0 ]; then
    echo "❌ Docker 构建失败"
    exit 1
fi

echo "✅ 镜像构建成功！"

# 启动服务
echo "🚀 启动服务..."
docker-compose -f $COMPOSE_FILE up -d

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose -f $COMPOSE_FILE ps

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 15

# 检查服务健康状态
echo "🏥 检查服务健康状态..."
if curl -f http://localhost:10086/ > /dev/null 2>&1; then
    echo "✅ 前端服务运行正常"
else
    echo "⚠️  前端服务可能还在启动中"
    echo "🔍 查看容器日志: docker-compose -f $COMPOSE_FILE logs"
fi

echo ""
echo "🎉 Docker 部署完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$DEPLOY_TYPE" = "prod" ]; then
    echo "📱 前端访问地址: http://120.55.55.116:10086/"
    echo "🔗 API代理地址: http://120.55.55.116:10086/api/"
else
    echo "📱 前端访问地址: http://localhost:10086/"
    echo "🔗 API代理地址: http://localhost:10086/api/"
fi

echo "🔧 后端服务地址: 10.0.1.226:8888"
echo "📦 使用配置文件: $COMPOSE_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 常用命令:"
echo "   - 查看服务状态: docker-compose -f $COMPOSE_FILE ps"
echo "   - 查看日志: docker-compose -f $COMPOSE_FILE logs -f"
echo "   - 停止服务: docker-compose -f $COMPOSE_FILE down"
echo "   - 重启服务: docker-compose -f $COMPOSE_FILE restart"
echo "   - 更新服务: docker-compose -f $COMPOSE_FILE up -d --build"
echo ""
echo "🔍 故障排除:"
echo "   - 查看容器日志: docker-compose -f $COMPOSE_FILE logs paperignition-frontend"
echo "   - 进入容器: docker-compose -f $COMPOSE_FILE exec paperignition-frontend sh"
echo "   - 检查端口: netstat -tlnp | grep 10086" 