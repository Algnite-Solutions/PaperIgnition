# PaperIgnition 前端 Docker 部署指南

## 🐳 Docker 部署方式

本项目支持两种Docker部署方式：拉取预构建镜像或本地构建镜像。

### 方式一：拉取预构建镜像（推荐）

如果有预构建的镜像在Docker Hub上，可以直接拉取使用：

```bash
# 拉取镜像
docker pull your-dockerhub-username/paperignition-frontend:latest

# 运行容器
docker run -d -p 10086:10086 \
  -e SERVER_NAME=你的服务器IP \
  -e BACKEND_API_URL=http://10.0.1.226:8888 \
  --name paperignition-frontend \
  your-dockerhub-username/paperignition-frontend:latest
```

### 方式二：本地构建镜像

```bash
# 1. 检查Docker环境
docker info

# 2. 构建镜像
docker build -t paperignition-frontend:latest .

# 3. 查看镜像信息
docker images | grep paperignition-frontend

# 4. 运行容器
docker run -d -p 10086:10086 \
  -e SERVER_NAME=你的服务器IP \
  -e BACKEND_API_URL=http://10.0.1.226:8888 \
  --name paperignition-frontend \
  paperignition-frontend:latest
```
