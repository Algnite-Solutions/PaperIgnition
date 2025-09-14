#!/usr/bin/env python3
"""
vLLM Generator测试
测试博客生成功能，包括vLLM服务连接和博客生成
"""

import sys
import os
import asyncio
from pathlib import Path
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from AIgnite.data.docset import DocSet
from orchestrator.generate_blog import run_batch_generation, run_batch_generation_abs, run_batch_generation_title

def create_test_paper():
    """创建一个测试论文对象"""
    return DocSet(
        doc_id="test_paper_vllm_001",
        title="Attention Is All You Need: A Comprehensive Study of Transformer Architecture",
        authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
        categories=["cs.CL", "cs.LG"],  # 添加必需的categories字段
        published_date="2017-06-12",  # 添加必需的published_date字段
        abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature. We show that the Transformer generalizes well to other tasks by applying it successfully to English constituency parsing with large and limited training data.",
        content="This is the full content of the test paper about Transformer architecture. It includes detailed information about the research methodology, experimental results, and conclusions.",
        pdf_path="/tmp/test_paper_vllm.pdf",  # 添加必需的pdf_path字段
        HTML_path="/tmp/test_paper_vllm.html"
    )

def test_vllm_connection():
    """测试vLLM服务连接"""
    print("🔍 测试vLLM服务连接...")
    
    try:
        import aiohttp
        
        # 测试连接到vLLM服务
        vllm_url = "http://localhost:5666"
        
        async def check_connection():
            try:
                async with aiohttp.ClientSession() as session:
                    # 尝试发送一个简单的请求
                    async with session.get(f"{vllm_url}/health", timeout=5) as response:
                        if response.status == 200:
                            print("✅ vLLM服务连接成功")
                            return True
                        else:
                            print(f"❌ vLLM服务响应异常: {response.status}")
                            return False
            except Exception as e:
                print(f"❌ vLLM服务连接失败: {e}")
                return False
        
        # 运行异步连接测试
        result = asyncio.run(check_connection())
        return result
        
    except ImportError:
        print("❌ aiohttp模块未安装，无法测试vLLM连接")
        return False
    except Exception as e:
        print(f"❌ vLLM连接测试失败: {e}")
        return False

def test_blog_generation():
    """测试博客生成功能"""
    print("\n🔍 测试博客生成功能...")
    
    try:
        # 创建测试论文
        test_papers = [create_test_paper()]
        
        print(f"   测试论文: {test_papers[0].title}")
        print(f"   论文ID: {test_papers[0].doc_id}")
        
        # 调用博客生成功能
        async def run_generation():
            try:
                result = await run_batch_generation(test_papers)
                return result
            except Exception as e:
                print(f"   博客生成异常: {e}")
                return None
        
        result = asyncio.run(run_generation())
        
        if result is not None:
            print("✅ 博客生成功能测试通过")
            return True
        else:
            print("❌ 博客生成功能测试失败")
            return False
        
    except Exception as e:
        print(f"❌ 博客生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_blog_abs_generation():
    """测试博客摘要生成功能"""
    print("\n🔍 测试博客摘要生成功能...")
    
    try:
        # 创建测试论文
        test_papers = [create_test_paper()]
        
        print(f"   测试论文: {test_papers[0].title}")
        
        # 调用博客摘要生成功能
        async def run_abs_generation():
            try:
                result = await run_batch_generation_abs(test_papers)
                return result
            except Exception as e:
                print(f"   博客摘要生成异常: {e}")
                return None
        
        result = asyncio.run(run_abs_generation())
        
        if result is not None:
            print("✅ 博客摘要生成功能测试通过")
            if result and len(result) > 0:
                print(f"   生成的摘要长度: {len(result[0])} 字符")
            return True
        else:
            print("❌ 博客摘要生成功能测试失败")
            return False
        
    except Exception as e:
        print(f"❌ 博客摘要生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_blog_title_generation():
    """测试博客标题生成功能"""
    print("\n🔍 测试博客标题生成功能...")
    
    try:
        # 创建测试论文
        test_papers = [create_test_paper()]
        
        print(f"   测试论文: {test_papers[0].title}")
        
        # 调用博客标题生成功能
        async def run_title_generation():
            try:
                result = await run_batch_generation_title(test_papers)
                return result
            except Exception as e:
                print(f"   博客标题生成异常: {e}")
                return None
        
        result = asyncio.run(run_title_generation())
        
        if result is not None:
            print("✅ 博客标题生成功能测试通过")
            if result and len(result) > 0:
                print(f"   生成的标题: {result[0]}")
            return True
        else:
            print("❌ 博客标题生成功能测试失败")
            return False
        
    except Exception as e:
        print(f"❌ 博客标题生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_blog_file_save():
    """测试博客文件保存功能"""
    print("\n🔍 测试博客文件保存功能...")
    
    try:
        # 创建测试论文
        test_papers = [create_test_paper()]
        
        # 先生成博客
        async def generate_and_check():
            try:
                await run_batch_generation(test_papers)
                
                # 检查博客文件是否生成
                blog_path = project_root / "orchestrator" / "blogs" / f"{test_papers[0].doc_id}.md"
                
                if blog_path.exists():
                    print(f"✅ 博客文件保存成功: {blog_path}")
                    
                    # 检查文件内容
                    with open(blog_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        print(f"   文件大小: {len(content)} 字符")
                        print(f"   内容预览: {content[:200]}...")
                    
                    return True
                else:
                    print(f"❌ 博客文件未找到: {blog_path}")
                    return False
                    
            except Exception as e:
                print(f"   博客生成和保存异常: {e}")
                return False
        
        result = asyncio.run(generate_and_check())
        return result
        
    except Exception as e:
        print(f"❌ 博客文件保存测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_batch_processing():
    """测试批量处理功能"""
    print("\n🔍 测试批量处理功能...")
    
    try:
        # 创建多个测试论文
        test_papers = [
            create_test_paper(),
            DocSet(
                doc_id="test_paper_vllm_002",
                title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
                authors=["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
                categories=["cs.CL", "cs.LG"],  # 添加必需的categories字段
                published_date="2018-10-11",  # 添加必需的published_date字段
                abstract="We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers. As a result, the pre-trained BERT model can be fine-tuned with just one additional output layer to create state-of-the-art models for a wide range of tasks, such as question answering and language inference, without substantial task-specific architecture modifications.",
                content="This is the full content of the BERT paper.",
                pdf_path="/tmp/test_paper_vllm_002.pdf",  # 添加必需的pdf_path字段
                HTML_path="/tmp/test_paper_vllm_002.html"
            )
        ]
        
        print(f"   测试论文数量: {len(test_papers)}")
        
        # 调用批量博客生成功能
        async def run_batch_generation_test():
            try:
                result = await run_batch_generation(test_papers)
                return result
            except Exception as e:
                print(f"   批量博客生成异常: {e}")
                return None
        
        result = asyncio.run(run_batch_generation_test())
        
        if result is not None:
            print("✅ 批量处理功能测试通过")
            return True
        else:
            print("❌ 批量处理功能测试失败")
            return False
        
    except Exception as e:
        print(f"❌ 批量处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有vLLM Generator测试"""
    print("=" * 60)
    print("🚀 开始vLLM Generator测试")
    print("=" * 60)
    
    results = []
    
    # 测试各个功能
    results.append(("vLLM服务连接", test_vllm_connection()))
    results.append(("博客生成功能", test_blog_generation()))
    results.append(("博客摘要生成功能", test_blog_abs_generation()))
    results.append(("博客标题生成功能", test_blog_title_generation()))
    results.append(("博客文件保存功能", test_blog_file_save()))
    results.append(("批量处理功能", test_batch_processing()))
    
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
        print("🎉 所有vLLM Generator测试通过！")
        return True
    else:
        print("⚠️  部分vLLM Generator测试失败")
        if not results[0][1]:  # vLLM服务连接失败
            print("💡 提示: 请确保vLLM服务正在运行 (端口5666)")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
