# Beta Frontend Dockerfile - 纯静态文件部署
FROM nginx:1.24-alpine

# 移除默认的nginx配置
RUN rm /etc/nginx/conf.d/default.conf

# 复制nginx配置文件
COPY nginx.conf /etc/nginx/conf.d/

# 复制静态文件到nginx目录
COPY . /usr/share/nginx/html/

# 暴露端口
EXPOSE 80

# 启动nginx
CMD ["nginx", "-g", "daemon off;"] 