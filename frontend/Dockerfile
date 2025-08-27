# 修复版 Dockerfile - 确保启动脚本正确
FROM node:20 AS builder

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV NODE_ENV=production
ENV TARO_BUILD_TYPE=h5
ENV NODE_OPTIONS="--max-old-space-size=4096"

# 配置npm使用国内镜像源
RUN npm config set registry https://registry.npmmirror.com/

# 安装pnpm
RUN npm install -g pnpm@latest

# 验证环境
RUN node --version && npm --version && pnpm --version

# 复制package文件
COPY package.json pnpm-lock.yaml* ./

# 配置pnpm
RUN pnpm config set registry https://registry.npmmirror.com/ && \
    pnpm config set network-timeout 300000

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制源代码
COPY . .

# 构建项目
RUN pnpm run build:h5

# 验证构建结果
RUN ls -la dist/

# 第二阶段：运行阶段
FROM nginx:1.24-alpine

# 安装envsubst
RUN apk add --no-cache gettext

# 复制构建产物
COPY --from=builder /app/dist /var/www/paperignition

# 复制nginx配置模板
COPY nginx.docker.conf /etc/nginx/conf.d/default.conf.template

# 复制启动脚本（使用COPY而不是echo）
COPY docker-entrypoint.sh /docker-entrypoint.sh

# 设置启动脚本权限
RUN chmod +x /docker-entrypoint.sh

# 设置目录权限
RUN mkdir -p /var/www/paperignition && \
    chown -R nginx:nginx /var/www/paperignition

# 暴露端口
EXPOSE 10086

# 启动
CMD ["/docker-entrypoint.sh"] 