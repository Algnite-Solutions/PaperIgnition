#!/usr/bin/env python3
"""
API连接测试
测试backend和index服务的健康状态和基本功能
"""

import sys
import os
import requests
import httpx
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.db_utils import load_config

def test_backend_api_health():
    """测试Backend API的健康状态"""
    print("🔍 测试Backend API连接...")
    
    try:
        config_path = project_root / "backend/configs/app_config.yaml"
        config = load_config(config_path)
        backend_url = config['APP_SERVICE']["host"]
        
        # 测试健康检查端点
        health_url = f"{backend_url}/api/health"
        response = requests.get(health_url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Backend API健康检查通过: {backend_url}")
            print(f"   响应: {response.json()}")
            return True
        else:
            print(f"❌ Backend API健康检查失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Backend API连接失败: {e}")
        return False

def test_index_api_health():
    """测试Index API的健康状态"""
    print("\n🔍 测试Index API连接...")
    
    try:
        config_path = project_root / "backend/configs/app_config.yaml"
        config = load_config(config_path)
        index_url = config['INDEX_SERVICE']["host"]
        
        # 测试健康检查端点
        health_url = f"{index_url}/health"
        response = requests.get(health_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Index API健康检查通过: {index_url}")
            print(f"   状态: {data.get('status')}")
            print(f"   索引器就绪: {data.get('indexer_ready')}")
            return True
        else:
            print(f"❌ Index API健康检查失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Index API连接失败: {e}")
        return False

def test_backend_user_api():
    """测试Backend用户相关API"""
    print("\n🔍 测试Backend用户API...")
    
    try:
        config_path = project_root / "backend/configs/app_config.yaml"
        config = load_config(config_path)
        backend_url = config['APP_SERVICE']["host"]
        
        # 测试获取所有用户
        users_url = f"{backend_url}/api/users/all"
        response = requests.get(users_url, timeout=10)
        
        if response.status_code == 200:
            users = response.json()
            print(f"✅ 用户API测试通过，获取到 {len(users)} 个用户")
            if users:
                print(f"   示例用户: {users[0].get('username', 'N/A')}")
            return True
        else:
            print(f"❌ 用户API测试失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 用户API测试失败: {e}")
        return False

def test_backend_paper_recommendation_api():
    """测试Backend论文推荐API"""
    print("\n🔍 测试Backend论文推荐API...")
    
    try:
        config_path = project_root / "backend/configs/app_config.yaml"
        config = load_config(config_path)
        backend_url = config['APP_SERVICE']["host"]
        
        # 测试获取推荐论文（使用一个测试用户）
        test_username = "test1@tongji.edu.cn"
        rec_url = f"{backend_url}/api/papers/recommendations/{test_username}"
        response = requests.get(rec_url, timeout=10)
        
        if response.status_code == 200:
            papers = response.json()
            print(f"✅ 论文推荐API测试通过，用户 {test_username} 有 {len(papers)} 篇推荐论文")
            return True
        else:
            print(f"❌ 论文推荐API测试失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 论文推荐API测试失败: {e}")
        return False

def main():
    """运行所有API连接测试"""
    print("=" * 60)
    print("🚀 开始API连接测试")
    print("=" * 60)
    
    results = []
    
    # 测试各个API
    results.append(("Backend API健康检查", test_backend_api_health()))
    results.append(("Index API健康检查", test_index_api_health()))
    results.append(("Backend用户API", test_backend_user_api()))
    results.append(("Backend论文推荐API", test_backend_paper_recommendation_api()))
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有API连接测试通过！")
        return True
    else:
        print("⚠️  部分API连接测试失败，请检查服务状态")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
