@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM PaperIgnition 前端 Docker 构建和推送脚本 (Windows版本)
echo 🔨 开始构建和推送 PaperIgnition 前端镜像...

REM 配置变量
set IMAGE_NAME=paperignition-frontend
set TAG=%1
set REGISTRY=%2

REM 设置默认值
if "%TAG%"=="" set TAG=latest
if "%REGISTRY%"=="" (
    set FULL_IMAGE_NAME=%IMAGE_NAME%
) else (
    set FULL_IMAGE_NAME=%REGISTRY%/%IMAGE_NAME%
)

echo 📦 镜像名称: %FULL_IMAGE_NAME%:%TAG%

REM 检查 Docker 是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: Docker 未运行或无法连接
    echo 💡 请确保 Docker Desktop 已启动
    pause
    exit /b 1
)

echo ✅ Docker 环境检查通过

REM 构建镜像
echo 🏗️  构建 Docker 镜像...
echo 💡 使用最小化 Dockerfile (避开系统包安装)...
docker build -f Dockerfile.minimal -t %FULL_IMAGE_NAME%:%TAG% .

if errorlevel 1 (
    echo ❌ 镜像构建失败
    pause
    exit /b 1
)

echo ✅ 镜像构建成功: %FULL_IMAGE_NAME%:%TAG%

REM 显示镜像信息
echo 📋 镜像信息:
docker images | findstr %IMAGE_NAME%

REM 询问是否推送到仓库
set /p PUSH_CHOICE=🚀 是否推送镜像到仓库? (y/N): 
if /i "%PUSH_CHOICE%"=="y" (
    if not "%REGISTRY%"=="" (
        echo 🔐 登录到 Docker Hub...
        docker login
        
        if errorlevel 1 (
            echo ❌ Docker Hub 登录失败
            pause
            exit /b 1
        )
    )
    
    echo 📤 推送镜像到仓库...
    docker push %FULL_IMAGE_NAME%:%TAG%
    
    if errorlevel 1 (
        echo ❌ 镜像推送失败
        pause
        exit /b 1
    ) else (
        echo ✅ 镜像推送成功!
        echo 🌐 镜像地址: %FULL_IMAGE_NAME%:%TAG%
        echo.
        echo 📋 在 Linux 服务器上使用以下命令拉取和运行:
        echo    docker pull %FULL_IMAGE_NAME%:%TAG%
        echo    docker run -d -p 10086:10086 ^
        echo      -e SERVER_NAME=你的服务器IP ^
        echo      -e BACKEND_API_URL=http://10.0.1.226:8888 ^
        echo      --name paperignition-frontend ^
        echo      %FULL_IMAGE_NAME%:%TAG%
    )
) else (
    echo ⏸️  跳过推送，镜像仅保存在本地
    echo.
    echo 💡 如需推送，请运行:
    echo    docker push %FULL_IMAGE_NAME%:%TAG%
)

echo.
echo 🎉 构建流程完成!
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 📦 本地镜像: %FULL_IMAGE_NAME%:%TAG%
echo 🔧 使用方法:
echo    构建: docker-build-and-push.bat
echo    指定标签: docker-build-and-push.bat v1.0.0
echo    指定仓库: docker-build-and-push.bat latest your-dockerhub-username
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pause 