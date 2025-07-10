import httpx
import asyncio
import pytest
import tempfile
import os
import json
from typing import Dict, Any, List
from backend.configs.config import load_backend_config

# 加载配置
config = load_backend_config()

# 配置测试URL
BASE_URL = config['api_url']  # 从配置文件读取后端API服务地址

# 测试用户数据
TEST_USER = config['test_user']  # 从配置文件读取测试用户数据

# 存储认证令牌
auth_token = ""

# 创建临时目录用于测试文件
TEMP_DIR = tempfile.mkdtemp()

async def check_server_running(url: str, timeout: float = 5.0) -> bool:
    """检查后端API服务是否运行并可访问"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{url}/health", timeout=timeout)
            return response.status_code == 200
    except Exception as e:
        print(f"\n❌ 错误: 后端API服务无法访问 {url}")
        print(f"请确保服务已启动:")
        print("    cd PaperIgnition")
        print(f"    uvicorn backend.app.main:app --reload --port 8000")
        print(f"\n错误详情: {str(e)}")
        return False

async def test_health_check():
    """测试健康检查端点"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200, f"健康检查失败: {response.text}"
        data = response.json()
        assert data["status"] == "ok", "API状态不正常"
        print("✅ 健康检查测试通过")

async def test_register_user():
    """测试用户注册功能"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/register-email",
            json=TEST_USER
        )
        
        # 如果用户已存在，会返回400，这也是可接受的结果
        if response.status_code == 200:
            data = response.json()
            assert data["username"] == TEST_USER["username"], "返回的用户名不匹配"
            assert data["email"] == TEST_USER["email"], "返回的邮箱不匹配"
            print("✅ 用户注册测试通过")
        elif response.status_code == 400:
            print("✅ 用户已存在，继续测试")
        else:
            assert False, f"用户注册失败，状态码: {response.status_code}, 响应: {response.text}"

async def test_login():
    """测试用户登录功能"""
    async with httpx.AsyncClient() as client:
        login_data = {
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        }
        response = await client.post(
            f"{BASE_URL}/auth/login-email",
            json=login_data
        )
        assert response.status_code == 200, f"登录失败: {response.text}"
        data = response.json()
        assert "access_token" in data, "响应中没有访问令牌"
        assert data["token_type"] == "bearer", "令牌类型不是bearer"
        
        # 保存令牌供后续测试使用
        global auth_token
        auth_token = data["access_token"]
        print("✅ 用户登录测试通过")

async def test_get_user_info():
    """测试获取用户信息"""
    if not auth_token:
        await test_login()
        
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await client.get(
            f"{BASE_URL}/users/me",
            headers=headers
        )
        assert response.status_code == 200, f"获取用户信息失败: {response.text}"
        data = response.json()
        assert data["username"] == TEST_USER["username"], "返回的用户名不匹配"
        assert data["email"] == TEST_USER["email"], "返回的邮箱不匹配"
        print("✅ 获取用户信息测试通过")

async def test_get_research_domains():
    """测试获取研究领域列表"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/domains")
        assert response.status_code == 200, f"获取研究领域失败: {response.text}"
        domains = response.json()
        assert isinstance(domains, list), "返回的研究领域不是列表"
        if domains:
            assert "id" in domains[0], "研究领域缺少id字段"
            assert "name" in domains[0], "研究领域缺少name字段"
        print("✅ 获取研究领域测试通过")

async def test_update_user_interests():
    """测试更新用户研究兴趣"""
    if not auth_token:
        await test_login()
        
    # 先获取可用的研究领域
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await client.get(f"{BASE_URL}/domains")
        assert response.status_code == 200, f"获取研究领域失败: {response.text}"
        domains = response.json()
        
        if not domains:
            print("⚠️ 没有可用的研究领域，跳过更新兴趣测试")
            return
            
        # 选择第一个研究领域
        domain_id = domains[0]["id"]
        
        # 更新用户兴趣
        interests_data = {
            "research_domain_ids": [domain_id],
            "interests_description": ["人工智能", "机器学习"]
        }
        
        response = await client.post(
            f"{BASE_URL}/users/interests",
            json=interests_data,
            headers=headers
        )
        assert response.status_code == 200, f"更新用户兴趣失败: {response.text}"
        data = response.json()
        assert domain_id in data["research_domain_ids"], "返回的研究领域ID不匹配"
        print("✅ 更新用户研究兴趣测试通过")

async def test_get_paper_recommendations():
    """测试获取论文推荐"""
    if not auth_token:
        await test_login()
        
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await client.get(
            f"{BASE_URL}/papers/recommendations/{TEST_USER['username']}",
            headers=headers
        )
        assert response.status_code == 200, f"获取论文推荐失败: {response.text}"
        papers = response.json()
        assert isinstance(papers, list), "返回的推荐论文不是列表"
        print(f"✅ 获取论文推荐测试通过，返回了 {len(papers)} 篇论文")

async def run_tests():
    """运行所有测试"""
    print(f"\n运行后端API测试，目标URL: {BASE_URL}")
    print("=" * 50)
    
    try:
        # 检查服务是否运行
        if not await check_server_running(BASE_URL):
            return
            
        # 基础API测试
        await test_health_check()
        
        # 用户认证测试
        await test_register_user()
        await test_login()
        await test_get_user_info()
        
        # 研究领域和兴趣测试
        await test_get_research_domains()
        await test_update_user_interests()
        
        # 论文推荐测试
        await test_get_paper_recommendations()
        
        print("\n✅ 所有后端API测试通过!")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {str(e)}")
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {str(e)}")
    finally:
        # 清理临时文件
        import shutil
        shutil.rmtree(TEMP_DIR, ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(run_tests()) 