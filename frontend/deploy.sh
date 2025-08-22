#!/bin/bash

# PaperIgnition 前端部署脚本
echo "开始部署 PaperIgnition 前端..."

# 检查是否安装了必要的依赖
if ! command -v pnpm &> /dev/null; then
    echo "错误: pnpm 未安装，请先安装 pnpm"
    echo "安装命令: npm install -g pnpm"
    exit 1
fi

if ! command -v nginx &> /dev/null; then
    echo "错误: nginx 未安装，请先安装 nginx"
    exit 1
fi

# 安装依赖
echo "安装项目依赖..."
pnpm install

# 构建H5版本
echo "构建H5版本..."
pnpm run build:h5

# 检查构建是否成功
if [ ! -d "dist" ]; then
    echo "错误: 构建失败，dist目录不存在"
    exit 1
fi

echo "构建成功！"

# 获取当前目录的绝对路径
CURRENT_DIR=$(pwd)
DIST_PATH="$CURRENT_DIR/dist"

# 更新nginx配置文件中的路径
echo "更新nginx配置文件中的路径..."
sed -i "s|/path/to/your/frontend/dist|$DIST_PATH|g" nginx.conf

# 复制nginx配置到系统配置目录
echo "配置nginx..."
sudo cp nginx.conf /etc/nginx/sites-available/paperignition
sudo ln -sf /etc/nginx/sites-available/paperignition /etc/nginx/sites-enabled/

# 测试nginx配置
echo "测试nginx配置..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "nginx配置测试通过"
    
    # 重启nginx
    echo "重启nginx..."
    sudo systemctl reload nginx
    
    echo "部署完成！"
    echo "前端访问地址: http://localhost"
    echo "API代理地址: http://localhost/api/"
    echo ""
    echo "请确保你的后端服务正在 10.0.1.226:8888 上运行"
else
    echo "nginx配置测试失败，请检查配置文件"
    exit 1
fi 