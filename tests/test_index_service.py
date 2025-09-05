#!/usr/bin/env python3
"""
Index服务测试
测试论文索引和搜索功能
"""

import sys
import os
import asyncio
from pathlib import Path
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.db_utils import load_config
from orchestrator import utils
from AIgnite.data.docset import DocSet

def test_index_paper():
    """直接测试论文索引API"""
    print("🔍 测试论文索引API...")
    
    try:
        config_path = project_root / "backend/configs/app_config.yaml"
        config = load_config(config_path)
        index_url = config['INDEX_SERVICE']["host"]
        
        # 创建一个测试论文
        test_paper = DocSet(
            doc_id="test_paper_api_001",
            title="Test Paper for API Indexing",
            authors=["Test Author 1", "Test Author 2"],
            categories=["cs.AI", "cs.LG"],  # 添加必需的categories字段
            published_date="2024-01-01",  # 添加必需的published_date字段
            abstract="This is a test paper abstract for testing the indexing API functionality. It contains some technical terms like machine learning, artificial intelligence, and natural language processing.",
            content="This is the full content of the test paper. It includes detailed information about the research methodology and results.",
            pdf_path="/tmp/test_paper_api.pdf",  # 添加必需的pdf_path字段
            HTML_path="/tmp/test_paper_api.html"
        )
        
        print(f"   测试论文ID: {test_paper.doc_id}")
        print(f"   标题: {test_paper.title}")
        
        # 直接调用索引API
        import httpx
        from AIgnite.data.docset import DocSetList
        
        # 创建DocSetList
        docset_list = DocSetList(docsets=[test_paper])
        data = docset_list.dict()
        
        print(f"   索引API URL: {index_url}/index_papers/")
        
        # 发送POST请求
        response = httpx.post(
            f"{index_url}/index_papers/", 
            json=data, 
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 论文索引API调用成功")
            print(f"   响应: {result}")
            return True
        else:
            print(f"❌ 论文索引API调用失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ 论文索引API测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search_papers_tfidf():
    """直接测试TF-IDF搜索API"""
    print("\n🔍 测试TF-IDF搜索API...")
    
    try:
        config_path = project_root / "backend/configs/app_config.yaml"
        config = load_config(config_path)
        index_url = config['INDEX_SERVICE']["host"]
        
        # 测试查询
        test_query = "machine learning"
        print(f"   搜索查询: '{test_query}'")
        
        # 直接调用搜索API
        import httpx
        
        payload = {
            "query": test_query,
            "top_k": 1,
            "similarity_cutoff": 0.1,
            "strategy_type": "tf-idf"
        }
        
        print(f"   搜索API URL: {index_url}/find_similar/")
        print(f"   请求参数: {payload}")
        
        response = httpx.post(
            f"{index_url}/find_similar/",
            json=payload,
            timeout=30.0
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ TF-IDF搜索API调用成功")
            
            if results and len(results) > 0:
                print(f"   找到 {len(results)} 篇相关论文")
                
                # 显示前3个结果
                for i, result in enumerate(results[:3]):
                    doc_id = result.get('doc_id', 'N/A')
                    title = result.get('title', 'N/A')[:50]
                    score = result.get('score', 'N/A')
                    print(f"   结果 {i+1}: {doc_id} - {title}...")
                    print(f"     相似度: {score}")
            else:
                print("   ⚠️  没有找到相关论文")
            
            return True
        else:
            print(f"❌ TF-IDF搜索API调用失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ TF-IDF搜索API测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search_papers_vector():
    """直接测试向量搜索API"""
    print("\n🔍 测试向量搜索API...")
    
    try:
        config_path = project_root / "backend/configs/app_config.yaml"
        config = load_config(config_path)
        index_url = config['INDEX_SERVICE']["host"]
        
        # 测试查询
        test_query = "artificial intelligence"
        print(f"   搜索查询: '{test_query}'")
        
        # 直接调用搜索API
        import httpx
        
        payload = {
            "query": test_query,
            "top_k": 1,
            "similarity_cutoff": 0.1,
            "strategy_type": "vector"
        }
        
        print(f"   搜索API URL: {index_url}/find_similar/")
        print(f"   请求参数: {payload}")
        
        response = httpx.post(
            f"{index_url}/find_similar/",
            json=payload,
            timeout=30.0
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ 向量搜索API调用成功")
            
            if results and len(results) > 0:
                print(f"   找到 {len(results)} 篇相关论文")
                
                # 显示前3个结果
                for i, result in enumerate(results[:3]):
                    doc_id = result.get('doc_id', 'N/A')
                    title = result.get('title', 'N/A')[:50]
                    score = result.get('score', 'N/A')
                    print(f"   结果 {i+1}: {doc_id} - {title}...")
                    print(f"     相似度: {score}")
            else:
                print("   ⚠️  没有找到相关论文")
            
            return True
        else:
            print(f"❌ 向量搜索API调用失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ 向量搜索API测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search_with_filters():
    """直接测试带过滤器的搜索API"""
    print("\n🔍 测试带过滤器的搜索API...")
    
    try:
        config_path = project_root / "backend/configs/app_config.yaml"
        config = load_config(config_path)
        index_url = config['INDEX_SERVICE']["host"]
        
        # 测试查询和过滤器
        test_query = "deep learning"
        exclude_papers = ["test_paper_api_001"]  # 排除我们之前创建的测试论文
        
        filter_params = {
            "exclude": {
                "doc_ids": exclude_papers
            }
        }
        
        print(f"   搜索查询: '{test_query}'")
        print(f"   排除论文: {exclude_papers}")
        
        # 直接调用搜索API
        import httpx
        
        payload = {
            "query": test_query,
            "top_k": 1,
            "similarity_cutoff": 0.1,
            "strategy_type": "vector",
            "filters": filter_params
        }
        
        print(f"   搜索API URL: {index_url}/find_similar/")
        print(f"   请求参数: {payload}")
        
        response = httpx.post(
            f"{index_url}/find_similar/",
            json=payload,
            timeout=30.0
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ 带过滤器搜索API调用成功")
            
            if results and len(results) > 0:
                print(f"   找到 {len(results)} 篇相关论文")
                
                # 检查是否真的排除了指定论文
                excluded_found = any(result.get('doc_id') in exclude_papers for result in results)
                if not excluded_found:
                    print("✅ 过滤器工作正常，成功排除了指定论文")
                else:
                    print("⚠️  过滤器可能未正常工作，仍包含被排除的论文")
                
                # 显示前3个结果
                for i, result in enumerate(results[:3]):
                    doc_id = result.get('doc_id', 'N/A')
                    title = result.get('title', 'N/A')[:50]
                    print(f"   结果 {i+1}: {doc_id} - {title}...")
            else:
                print("   ⚠️  没有找到相关论文")
            
            return True
        else:
            print(f"❌ 带过滤器搜索API调用失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ 带过滤器搜索API测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_index_health_check():
    """直接测试Index服务健康检查API"""
    print("\n🔍 测试Index服务健康检查API...")
    
    try:
        config_path = project_root / "backend/configs/app_config.yaml"
        config = load_config(config_path)
        index_url = config['INDEX_SERVICE']["host"]
        
        # 直接调用健康检查API
        import httpx
        
        health_url = f"{index_url}/health"
        print(f"   健康检查URL: {health_url}")
        
        response = httpx.get(health_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Index服务健康检查API调用成功")
            print(f"   状态: {data.get('status')}")
            print(f"   索引器就绪: {data.get('indexer_ready')}")
            
            if data.get("status") == "healthy" and data.get("indexer_ready"):
                return True
            elif data.get("status") == "healthy" and not data.get("indexer_ready"):
                print("⚠️  Index服务运行中但索引器未就绪")
                return False
            else:
                print("❌ Index服务状态不健康")
                return False
        else:
            print(f"❌ Index服务健康检查API调用失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Index服务健康检查API测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有Index服务测试"""
    print("=" * 60)
    print("🚀 开始Index服务测试")
    print("=" * 60)
    
    results = []
    
    # 测试各个功能
    results.append(("Index服务健康检查API", test_index_health_check()))
    results.append(("论文索引API", test_index_paper()))
    results.append(("TF-IDF搜索API", test_search_papers_tfidf()))
    results.append(("向量搜索API", test_search_papers_vector()))
    results.append(("带过滤器搜索API", test_search_with_filters()))
    
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
        print("🎉 所有Index服务测试通过！")
        return True
    else:
        print("⚠️  部分Index服务测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
