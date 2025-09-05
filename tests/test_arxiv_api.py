#!/usr/bin/env python3
"""
ArXiv API测试
直接测试ArXiv API调用，参考htmlparser.py的实现
"""

import sys
import os
import asyncio
import requests
import arxiv
from pathlib import Path
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from AIgnite.data.docset import DocSet

def test_arxiv_client_connection():
    """测试ArXiv客户端连接"""
    print("🔍 测试ArXiv客户端连接...")
    
    try:
        # 创建ArXiv客户端
        client = arxiv.Client()
        print("✅ ArXiv客户端创建成功")
        
        # 测试简单查询
        query = "cat:cs.* AND submittedDate:[" + "202509020000" + " TO " + "202509030000" + "]"
        search = arxiv.Search(
            query=query,
            max_results=1,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        # 执行搜索
        results = list(client.results(search))
        
        if results:
            print(f"✅ ArXiv API连接成功，获取到 {len(results)} 个结果")
            first_result = results[0]
            print(f"   示例论文: {first_result.title[:50]}...")
            return True
        else:
            print("⚠️  ArXiv API连接成功，但没有获取到结果")
            return False
            
    except Exception as e:
        print(f"❌ ArXiv客户端连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_arxiv_paper_fetch():
    """直接测试从ArXiv抓取论文"""
    print("\n🔍 测试ArXiv论文抓取...")
    
    try:
        # 设置时间范围（最近1天）
        end_time = datetime.now() - timedelta(days=1)
        start_time = end_time - timedelta(days=1)
        
        start_time_str = start_time.strftime('%Y%m%d')
        end_time_str = end_time.strftime('%Y%m%d')
        
        print(f"   时间范围: {start_time_str} 到 {end_time_str}")
        
        # 创建ArXiv客户端
        client = arxiv.Client()
        
        # 构建查询
        query = f"cat:cs.* AND submittedDate:[{start_time_str} TO {end_time_str}]"
        print(f"   查询语句: {query}")
        
        search = arxiv.Search(
            query=query,
            max_results=1,  # 限制为1篇论文进行测试
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        # 执行搜索
        results = list(client.results(search))
        
        if results:
            print(f"✅ ArXiv论文抓取成功，获取到 {len(results)} 篇论文")
            
            # 显示第一篇论文的信息
            first_result = results[0]
            print(f"   示例论文:")
            print(f"     ID: {first_result.entry_id.split('/')[-1]}")
            print(f"     标题: {first_result.title[:100]}...")
            print(f"     作者: {', '.join([author.name for author in first_result.authors[:3]])}...")
            print(f"     摘要长度: {len(first_result.summary)} 字符")
            print(f"     发布日期: {first_result.published}")
            
            return results
        else:
            print("⚠️  ArXiv论文抓取成功，但没有获取到论文")
            return []
            
    except Exception as e:
        print(f"❌ ArXiv论文抓取失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_paper_html_download():
    """直接测试论文HTML下载和保存"""
    print("\n🔍 测试论文HTML下载和保存...")
    
    try:
        # 先抓取一篇论文
        results = test_arxiv_paper_fetch()
        if not results:
            print("❌ 没有论文可用于测试HTML下载")
            return False
        
        # 测试下载第一篇论文的HTML
        result = results[0]
        arxiv_id = result.entry_id.split('/')[-1]
        
        # 构建HTML URL
        html_url = result.pdf_url.replace("pdf", "html")
        print(f"   HTML URL: {html_url}")
        
        # 下载HTML内容
        response = requests.get(html_url, timeout=30)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        article_tag = soup.find('article')
        
        if article_tag is not None:
            # 创建测试目录
            test_dir = "/data3/guofang/peirongcan/PaperIgnition/tests"
            
            # 保存HTML文件
            html_path = test_dir + f"/{arxiv_id}.html"
            with open(html_path, 'w', encoding='utf-8') as html_file:
                html_file.write(str(article_tag))
            
            print(f"✅ 论文HTML下载成功: {html_path}")
            
            # 检查文件大小
            file_size = os.path.getsize(html_path)
            print(f"   文件大小: {file_size} 字节")
            
            return True
        else:
            print("❌ 无法找到论文的article标签")
            return False
            
    except Exception as e:
        print(f"❌ 论文HTML下载测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有ArXiv API测试"""
    print("=" * 60)
    print("🚀 开始ArXiv API测试")
    print("=" * 60)
    
    results = []
    
    # 测试各个功能
    results.append(("ArXiv客户端连接", test_arxiv_client_connection()))
    results.append(("ArXiv论文抓取和HTML下载", test_paper_html_download()))
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
        print("🎉 所有ArXiv API测试通过！")
        return True
    else:
        print("⚠️  部分ArXiv API测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
