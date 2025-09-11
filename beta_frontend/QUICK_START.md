# Beta Frontend 快速部署指南

## 🚀 一键部署到服务器

### Windows 用户

```bash
# 1. 构建 Docker 镜像
docker-build-and-push.bat latest your-dockerhub-username

# 2. 登录服务器
ssh user@your-server

# 3. 拉取并运行
docker pull your-dockerhub-username/paperignition-beta-frontend:latest
docker run -d --name paperignition-beta-frontend -p 3001:80 --restart unless-stopped your-dockerhub-username/paperignition-beta-frontend:latest

# 4. 访问应用
http://your-server-ip:3001
```

### Linux/Mac 用户

```bash
# 1. 构建 Docker 镜像
chmod +x docker-build-and-push.sh
./docker-build-and-push.sh latest your-dockerhub-username

# 2. 登录服务器
ssh user@your-server

# 3. 拉取并运行
docker pull your-dockerhub-username/paperignition-beta-frontend:latest
docker run -d --name paperignition-beta-frontend -p 3001:80 --restart unless-stopped your-dockerhub-username/paperignition-beta-frontend:latest

# 4. 访问应用
http://your-server-ip:3001
```

## 🛠️ 本地测试

```bash
# 构建本地镜像
docker build -t paperignition-beta-frontend .

# 本地运行测试
docker run -d --name test-frontend -p 8080:80 paperignition-beta-frontend

# 访问测试
http://localhost:8080
```

## 📝 重要配置

1. **后端API地址**: 确保前端代码中的 API_BASE_URL 指向正确的后端服务器
2. **防火墙**: 确保服务器开放了对应端口 (如 3001)
3. **域名**: 可选配置域名和SSL证书

## 📞 获取帮助

详细部署文档: [DEPLOYMENT.md](./DEPLOYMENT.md) 