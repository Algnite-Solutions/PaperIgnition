#!/bin/bash

# PaperIgnition 前端快速部署脚本 (pnpm版本)
echo "🚀 开始部署 PaperIgnition 前端 (使用 pnpm)..."

# 检查pnpm是否安装
if ! command -v pnpm &> /dev/null; then
    echo "❌ 错误: pnpm 未安装"
    echo "💡 请先安装 pnpm: npm install -g pnpm"
    exit 1
fi

# 检查nginx是否安装
if ! command -v nginx &> /dev/null; then
    echo "❌ 错误: nginx 未安装，请先安装 nginx"
    exit 1
fi

echo "✅ 环境检查通过"

# 使用pnpm安装依赖（更快）
echo "📦 安装项目依赖 (使用 pnpm)..."
pnpm install --frozen-lockfile

# 构建H5版本
echo "🔨 构建H5版本..."
NODE_ENV=production pnpm run build:h5

# 检查构建是否成功
if [ ! -d "dist" ]; then
    echo "❌ 构建失败，dist目录不存在"
    exit 1
fi

echo "✅ 构建成功！"

# 获取当前目录的绝对路径
CURRENT_DIR=$(pwd)
DIST_PATH="$CURRENT_DIR/dist"

echo "📁 前端文件路径: $DIST_PATH"

# 创建nginx配置的备份
if [ -f "/etc/nginx/sites-available/paperignition" ]; then
    echo "🔄 备份现有nginx配置..."
    sudo cp /etc/nginx/sites-available/paperignition /etc/nginx/sites-available/paperignition.backup.$(date +%Y%m%d_%H%M%S)
fi

# 更新nginx配置文件中的路径
echo "⚙️  更新nginx配置文件中的路径..."
sed "s|/path/to/your/frontend/dist|$DIST_PATH|g" nginx.conf > nginx.conf.tmp
mv nginx.conf.tmp nginx.conf

# 复制nginx配置
echo "🌐 配置nginx..."
sudo cp nginx.conf /etc/nginx/sites-available/paperignition
sudo ln -sf /etc/nginx/sites-available/paperignition /etc/nginx/sites-enabled/

# 移除默认站点（如果存在）
if [ -f "/etc/nginx/sites-enabled/default" ]; then
    echo "🗑️  移除nginx默认站点配置..."
    sudo rm -f /etc/nginx/sites-enabled/default
fi

# 测试nginx配置
echo "🔍 测试nginx配置..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ nginx配置测试通过"
    
    # 重启nginx
    echo "🔄 重启nginx..."
    sudo systemctl reload nginx
    
    echo ""
    echo "🎉 部署完成！"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📱 前端访问地址: http://47.84.81.246:10086/"
    echo "🔗 API代理地址: http://47.84.81.246:10086/api/"
    echo "📂 静态文件目录: $DIST_PATH"
    echo "🔧 后端服务地址: 10.0.1.226:8888"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "💡 提示:"
    echo "   - 如果使用服务器IP访问，请将localhost替换为实际IP"
    echo "   - 确保防火墙开放80端口"
    echo "   - 确保后端服务正在运行"
    echo ""
    echo "🔍 故障排除:"
    echo "   - 查看nginx日志: sudo tail -f /var/log/nginx/error.log"
    echo "   - 检查nginx状态: sudo systemctl status nginx"
    echo "   - 重启nginx: sudo systemctl restart nginx"
else
    echo "❌ nginx配置测试失败，请检查配置文件"
    echo "🔍 查看错误详情: sudo nginx -t"
    exit 1
fi 