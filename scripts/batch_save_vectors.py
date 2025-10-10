#!/usr/bin/env python3
"""
批量保存论文向量到FAISS数据库的脚本

该脚本会：
1. 读取配置文件获取API服务器地址
2. 调用 /get_all_metadata_doc_ids/ API 获取所有论文的doc_id
3. 调用 /get_all_vector_doc_ids/ API 获取已存储向量的doc_id
4. 计算差集，找出未存储向量的论文
5. 调用 /get_metadata/{doc_id} API 批量获取这些论文的元数据
6. 调用 /save_vectors/ API 端点将向量保存到FAISS数据库
7. 提供详细的进度显示和错误报告

使用方法：
    python batch_save_vectors.py [--api-url URL] [--config CONFIG] [--batch-size SIZE] [--dry-run]

参数：
    --api-url: API服务器地址 (默认从配置文件读取)
    --config: 配置文件路径 (默认: ../backend/configs/app_config.yaml)
    --batch-size: 每批处理的论文数量 (默认: 50)
    --dry-run: 仅显示将要处理的论文，不实际保存

配置文件格式：
    脚本会自动从配置文件中读取INDEX_SERVICE.host配置
    
注意：
    此脚本完全通过 HTTP API 工作，不需要直接的数据库连接
"""

import os
import sys
import argparse
import asyncio
import httpx
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
import logging
from tqdm import tqdm

# 添加项目路径到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.index_service.db_utils import load_config
from AIgnite.data.docset import DocSet, DocSetList

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('batch_save_vectors.log')
    ]
)

# 禁用第三方库的 DEBUG 日志，只保留 WARNING 及以上级别
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def get_api_url_from_config(config: Dict) -> str:
    """从配置中获取API URL"""
    try:
        return config['INDEX_SERVICE']['host']
    except KeyError:
        logger.warning("配置中未找到INDEX_SERVICE.host，使用默认值")
        return "http://localhost:8002"


class BatchVectorSaver:
    def __init__(self, api_url: str = None, config_path: str = None, batch_size: int = 50):
        """初始化批量向量保存器
        
        Args:
            api_url: API服务器地址（可选，优先使用配置文件中的地址）
            config_path: 配置文件路径
            batch_size: 每批处理的论文数量
        """
        # 优先级：配置文件 > 命令行参数 > 默认值
        
        # 加载配置
        if config_path:
            try:
                self.config = load_config(config_path)
                logger.info(f"✅ 成功加载配置文件: {config_path}")
                
                # 优先从配置文件获取 API URL
                config_api_url = get_api_url_from_config(self.config)
                if config_api_url:
                    # 如果命令行也提供了 api_url，显示警告
                    if api_url is not None and api_url != config_api_url:
                        logger.warning(f"⚠️  命令行 API URL ({api_url}) 将被配置文件中的地址覆盖")
                    api_url = config_api_url
                    logger.info(f"✅ 从配置文件获取 API URL: {api_url}")
                elif api_url is None:
                    # 配置文件中没有，且命令行也没提供
                    api_url = "http://localhost:8002"
                    logger.warning(f"⚠️  配置文件中未找到 API URL，使用默认值: {api_url}")
                    
            except Exception as e:
                logger.error(f"❌ 配置加载失败: {e}")
                self.config = None
                if api_url is None:
                    api_url = "http://localhost:8002"
                    logger.warning(f"⚠️  使用默认 API URL: {api_url}")
        else:
            self.config = None
            if api_url is None:
                api_url = "http://localhost:8002"
                logger.warning(f"⚠️  未提供配置文件，使用默认 API URL: {api_url}")
            else:
                logger.info(f"✅ 使用命令行提供的 API URL: {api_url}")
        
        self.api_url = api_url.rstrip('/')
        self.batch_size = batch_size
        
        # API 端点配置
        self.save_vectors_endpoint = f"{self.api_url}/save_vectors/"
        self.health_endpoint = f"{self.api_url}/health"
        self.get_all_metadata_doc_ids_endpoint = f"{self.api_url}/get_all_metadata_doc_ids/"
        self.get_all_vector_doc_ids_endpoint = f"{self.api_url}/get_all_vector_doc_ids/"
        self.get_metadata_endpoint = f"{self.api_url}/get_metadata"
        
        # 统计信息
        self.total_papers = 0
        self.successful_saves = 0
        self.failed_saves = 0
        self.skipped_papers = 0
        self.results = []
        
        # 显示配置信息
        logger.info(f"🔧 API URL: {self.api_url}")
        logger.info(f"📦 批处理大小: {self.batch_size}")
    
    async def check_server_health(self) -> bool:
        """检查API服务器是否运行"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.health_endpoint)
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ 服务器健康检查通过: {data}")
                    return data.get("indexer_ready", False)
                else:
                    logger.error(f"❌ 服务器健康检查失败: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"❌ 无法连接到服务器 {self.api_url}: {e}")
            return False
    
    async def get_missing_doc_ids(self, client: httpx.AsyncClient) -> Set[str]:
        """通过 API 获取未存储向量的doc_ids
        
        Args:
            client: HTTP 客户端
            
        Returns:
            未存储向量的doc_id集合
        """
        try:
            # 调用 API 获取所有 metadata doc_ids
            logger.info("📊 正在从 MetadataDB 获取所有论文ID...")
            metadata_response = await client.get(
                self.get_all_metadata_doc_ids_endpoint,
                timeout=30.0
            )
            
            if metadata_response.status_code != 200:
                logger.error(f"❌ 获取metadata doc_ids失败: {metadata_response.status_code}")
                return set()
            
            metadata_result = metadata_response.json()
            all_doc_ids = set(metadata_result.get('doc_ids', []))
            logger.info(f"   找到 {len(all_doc_ids)} 篇论文")
            
            # 调用 API 获取所有 vector doc_ids
            logger.info("📊 正在从 VectorDB 获取已存储向量的论文ID...")
            vector_response = await client.get(
                self.get_all_vector_doc_ids_endpoint,
                timeout=30.0
            )
            
            if vector_response.status_code != 200:
                logger.error(f"❌ 获取vector doc_ids失败: {vector_response.status_code}")
                return set()
            
            vector_result = vector_response.json()
            vector_doc_ids = set(vector_result.get('doc_ids', []))
            logger.info(f"   找到 {len(vector_doc_ids)} 篇已存储向量的论文")
            
            # 计算差集
            missing_doc_ids = all_doc_ids - vector_doc_ids
            logger.info(f"📊 需要存储向量的论文数: {len(missing_doc_ids)}")
            
            return missing_doc_ids
            
        except Exception as e:
            logger.error(f"❌ 获取缺失doc_ids失败: {e}")
            return set()
    
    async def fetch_papers_metadata(self, client: httpx.AsyncClient, doc_ids: Set[str]) -> List[Dict]:
        """通过 API 批量获取论文元数据
        
        Args:
            client: HTTP 客户端
            doc_ids: 需要获取元数据的doc_id集合
            
        Returns:
            论文元数据字典列表
        """
        papers_metadata = []
        failed_count = 0
        
        logger.info(f"📊 正在获取 {len(doc_ids)} 篇论文的元数据...")
        
        # 使用 tqdm 显示进度条
        with tqdm(total=len(doc_ids), desc="📥 获取元数据", unit="篇", ncols=100) as pbar:
            for doc_id in doc_ids:
                try:
                    response = await client.get(
                        f"{self.get_metadata_endpoint}/{doc_id}",
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        metadata = response.json()
                        papers_metadata.append(metadata)
                        pbar.set_postfix({"成功": len(papers_metadata), "失败": failed_count})
                    elif response.status_code == 404:
                        failed_count += 1
                        pbar.set_postfix({"成功": len(papers_metadata), "失败": failed_count})
                    else:
                        failed_count += 1
                        pbar.set_postfix({"成功": len(papers_metadata), "失败": failed_count})
                        
                except Exception as e:
                    failed_count += 1
                    pbar.set_postfix({"成功": len(papers_metadata), "失败": failed_count})
                finally:
                    pbar.update(1)  # 无论成功失败都更新进度
        
        logger.info(f"📊 成功获取 {len(papers_metadata)} 篇论文的元数据")
        if failed_count > 0:
            logger.warning(f"⚠️  失败 {failed_count} 篇")
        
        return papers_metadata
    
    def build_docsets(self, papers_metadata: List[Dict]) -> List[DocSet]:
        """从元数据构建DocSet对象列表
        
        Args:
            papers_metadata: 论文元数据字典列表
            
        Returns:
            DocSet对象列表
        """
        docsets = []
        
        for metadata in papers_metadata:
            try:
                docset = DocSet(
                    doc_id=metadata.get('doc_id'),
                    title=metadata.get('title', ''),
                    abstract=metadata.get('abstract', ''),
                    authors=metadata.get('authors', []),
                    categories=metadata.get('categories', []),
                    published_date=metadata.get('published_date', ''),
                    pdf_path=metadata.get('pdf_path', ''),
                    HTML_path=metadata.get('HTML_path'),
                    text_chunks=[],  # save_vectors不需要text_chunks
                    figure_chunks=[],  # save_vectors不需要figure_chunks
                    table_chunks=[],  # save_vectors不需要table_chunks
                    metadata=metadata.get('metadata', {}),
                    comments=metadata.get('comments')
                )
                docsets.append(docset)
            except Exception as e:
                logger.error(f"❌ 构建DocSet失败 {metadata.get('doc_id', 'unknown')}: {e}")
        
        logger.info(f"📦 成功构建 {len(docsets)} 个DocSet对象")
        return docsets
    
    async def save_vectors_batch(self, client: httpx.AsyncClient, docsets: List[DocSet]) -> Dict:
        """调用API批量保存向量
        
        Args:
            client: HTTP客户端
            docsets: DocSet对象列表
            
        Returns:
            保存结果字典
        """
        request_data = {
            "docsets": {
                "docsets": [docset.dict() for docset in docsets]
            },
            "indexing_status": None
        }
        
        try:
            logger.info(f"📤 正在保存 {len(docsets)} 篇论文的向量...")
            response = await client.post(
                self.save_vectors_endpoint,
                json=request_data,
                timeout=120.0  # 向量计算可能需要较长时间
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    logger.info(f"✅ 批次保存成功: {result.get('message', '')}")
                    return {
                        "status": "success",
                        "papers_processed": result.get("papers_processed", len(docsets)),
                        "message": result.get("message", "保存成功")
                    }
                else:
                    logger.error(f"❌ 批次保存失败: {result.get('message', '未知错误')}")
                    return {
                        "status": "failed",
                        "papers_processed": 0,
                        "message": result.get("message", "保存失败")
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"❌ 批次保存失败: {error_msg}")
                return {
                    "status": "failed",
                    "papers_processed": 0,
                    "message": error_msg
                }
                
        except httpx.TimeoutException:
            error_msg = "请求超时"
            logger.error(f"❌ 批次保存失败: {error_msg}")
            return {
                "status": "failed",
                "papers_processed": 0,
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(f"❌ 批次保存失败: {error_msg}")
            return {
                "status": "failed",
                "papers_processed": 0,
                "message": error_msg
            }
    
    async def batch_save_vectors(self, dry_run: bool = False) -> Dict:
        """批量保存向量主流程
        
        Args:
            dry_run: 是否为演练模式
            
        Returns:
            处理结果摘要
        """
        logger.info("🚀 开始批量保存向量...")
        
        # 创建 HTTP client
        async with httpx.AsyncClient(timeout=120.0) as client:
            # 1. 获取缺失的doc_ids
            missing_doc_ids = await self.get_missing_doc_ids(client)
            self.total_papers = len(missing_doc_ids)
            
            if self.total_papers == 0:
                logger.info("✅ 所有论文的向量已存储，无需处理")
                return self.get_summary()
            
            logger.info(f"📋 将要处理 {self.total_papers} 篇论文")
            
            missing_doc_ids = list(missing_doc_ids)
            # 2. 获取论文元数据
            papers_metadata = await self.fetch_papers_metadata(client, missing_doc_ids)
            if not papers_metadata:
                logger.error("❌ 未能获取任何论文元数据")
                return self.get_summary()
            
            # 3. 构建DocSet对象
            all_docsets = self.build_docsets(papers_metadata)
            if not all_docsets:
                logger.error("❌ 未能构建任何DocSet对象")
                return self.get_summary()
            
            if dry_run:
                logger.info("🔍 干运行模式，不实际保存向量")
                logger.info(f"📋 将要保存向量的论文:")
                for i, docset in enumerate(all_docsets[:10], 1):  # 只显示前10个
                    logger.info(f"  {i}. {docset.doc_id}: {docset.title[:60]}...")
                if len(all_docsets) > 10:
                    logger.info(f"  ... 还有 {len(all_docsets) - 10} 篇论文")
                return self.get_summary()
            
            # 4. 检查服务器健康状态
            logger.info("🔍 检查服务器状态...")
            if not await self.check_server_health():
                logger.error("❌ 服务器未就绪或indexer未初始化")
                return self.get_summary()
            
            # 5. 分批处理
            logger.info(f"💾 开始批量保存向量（每批 {self.batch_size} 篇）...")
            start_time = time.time()
            
            total_batches = (len(all_docsets) + self.batch_size - 1) // self.batch_size
            
            # 使用 tqdm 显示批处理进度
            with tqdm(total=total_batches, desc="💾 批量保存", unit="批次", ncols=100) as pbar:
                for batch_idx in range(0, len(all_docsets), self.batch_size):
                    batch_docsets = all_docsets[batch_idx:batch_idx + self.batch_size]
                    current_batch = batch_idx // self.batch_size + 1
                    
                    # 更新进度条描述
                    pbar.set_description(f"💾 批次 {current_batch}/{total_batches}")
                    
                    result = await self.save_vectors_batch(client, batch_docsets)
                    self.results.append(result)
                    
                    if result["status"] == "success":
                        self.successful_saves += result["papers_processed"]
                        pbar.set_postfix({"成功": self.successful_saves, "失败": self.failed_saves})
                    else:
                        self.failed_saves += len(batch_docsets)
                        pbar.set_postfix({"成功": self.successful_saves, "失败": self.failed_saves})
                    
                    pbar.update(1)  # 更新进度
                    
                    # 添加小延迟避免过于频繁的请求
                    await asyncio.sleep(0.5)
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"⏱️  总耗时: {duration:.2f} 秒")
        if self.total_papers > 0:
            logger.info(f"📊 平均每篇论文: {duration/self.total_papers:.2f} 秒")
        
        return self.get_summary()
    
    def get_summary(self) -> Dict:
        """获取处理结果摘要"""
        return {
            "total_papers": self.total_papers,
            "successful_saves": self.successful_saves,
            "failed_saves": self.failed_saves,
            "skipped_papers": self.skipped_papers,
            "success_rate": (self.successful_saves / self.total_papers * 100) if self.total_papers > 0 else 0,
            "results": self.results
        }
    
    def print_summary(self):
        """打印处理结果摘要"""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("📊 批量向量保存结果摘要")
        print("="*60)
        print(f"📁 总论文数: {summary['total_papers']}")
        print(f"✅ 成功保存: {summary['successful_saves']}")
        print(f"❌ 保存失败: {summary['failed_saves']}")
        print(f"⏭️  跳过论文: {summary['skipped_papers']}")
        print(f"📈 成功率: {summary['success_rate']:.1f}%")
        
        if summary['failed_saves'] > 0:
            print("\n❌ 失败的批次:")
            for i, result in enumerate(summary['results'], 1):
                if result['status'] == 'failed':
                    print(f"  批次 {i}: {result['message']}")
        
        print("="*60)


async def main():
    parser = argparse.ArgumentParser(
        description="批量保存论文向量到FAISS数据库",
        epilog="优先级: 配置文件中的API URL > --api-url参数 > 默认值(http://localhost:8002)"
    )
    parser.add_argument("--api-url", 
                       help="API服务器地址 (可选，用于覆盖配置文件中的地址)")
    parser.add_argument("--config", 
                       help="配置文件路径 (默认: ../backend/configs/app_config.yaml)",
                       default=str(Path(__file__).parent.parent / "backend" / "configs" / "app_config.yaml"))
    parser.add_argument("--batch-size", 
                       type=int,
                       default=50,
                       help="每批处理的论文数量 (默认: 50)")
    parser.add_argument("--dry-run", action="store_true", 
                       help="仅显示将要处理的论文，不实际保存")
    
    args = parser.parse_args()

    args.config = "/data3/guofang/AIgnite-Solutions/PaperIgnition/backend/configs/app_config.yaml"
    args.dry_run = False

    try:
        saver = BatchVectorSaver(
            api_url=args.api_url,
            config_path=args.config,
            batch_size=args.batch_size
        )
        
        await saver.batch_save_vectors(dry_run=args.dry_run)
        saver.print_summary()
        
        # 如果有失败的保存，退出码为1
        if saver.failed_saves > 0:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


