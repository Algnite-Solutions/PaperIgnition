#!/usr/bin/env python3
"""
基于数据库状态批量更新论文博客脚本

逻辑变更：
1. 连接 Metadata 数据库
2. 查询 blog 字段为空的 paper_id
3. 检查本地是否存在对应的 .md 文件
4. 读取文件并调用 API 更新

使用方法：
    python batch_update_blogs_db_driven.py
"""

import os
import sys
import asyncio
import httpx
import time
import asyncpg
from pathlib import Path
from typing import List, Dict, Optional, Set
import logging
from tqdm import tqdm

# 添加项目路径到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.index_service.db_utils import load_config

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('batch_update_blogs.log')
    ]
)

# 禁用第三方库的 DEBUG 日志
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('asyncpg').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class BatchBlogUpdater:
    def __init__(self, api_url: str = None, config_path: str = None, batch_size: int = 50):
        # --- 配置加载逻辑 ---
        if config_path:
            try:
                self.config = load_config(config_path)
                logger.info(f"✅ 成功加载配置文件: {config_path}")
                
                # 获取 API URL
                if not api_url:
                    api_url = self.config.get('index_service', {}).get('host', "http://10.0.1.226:8002")
                
                # 获取数据库连接 URL
                self.db_url = self.config.get('index_service', {}).get('metadata_db', {}).get('db_url')
                if not self.db_url:
                    raise ValueError("配置文件中缺少 index_service.metadata_db.db_url")
                    
            except Exception as e:
                logger.error(f"❌ 配置加载失败: {e}，使用硬编码默认值")
                self.config = load_config(config_path)
                api_url = "http://10.0.1.226:8002"
                self.db_url = "postgresql://postgres:11111@localhost:5432/paperignition"

        else:
            logger.error("❌ 必须提供配置文件路径")
            sys.exit(1)

        self.api_url = api_url.rstrip('/')
        self.batch_size = batch_size
        
        # 博客文件目录 (从配置中读取，如果配置没有则使用硬编码默认值)
        config_blog_path = self.config.get('blog_generation', {}).get('output_path')
        self.blogs_dir = Path(config_blog_path) if config_blog_path else Path("/data3/guofang/peirongcan/PaperIgnition/orchestrator/blogs")
        
        self.update_blogs_endpoint = f"{self.api_url}/update_papers_blog/"
        self.health_endpoint = f"{self.api_url}/health"
        
        # 统计信息
        self.total_target_papers = 0
        self.found_local_files = 0
        self.missing_local_files = 0
        self.successful_updates = 0
        self.failed_updates = 0
        self.results = []

        logger.info(f"🔧 API URL: {self.api_url}")
        logger.info(f"🗄️  DB URL: {self.db_url.split('@')[-1]}") # 隐藏密码只显示主机
        logger.info(f"📁 本地博客目录: {self.blogs_dir}")

    async def check_server_health(self) -> bool:
        """检查API服务器是否运行"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.health_endpoint)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("indexer_ready", False)
                return False
        except Exception as e:
            logger.error(f"❌ 无法连接到服务器 {self.api_url}: {e}")
            return False

    async def fetch_missing_blog_ids(self) -> List[str]:
        """
        连接数据库，查询所有 blog 字段为空或NULL的 paper_id
        """
        logger.info("🔍 正在连接数据库查询缺失博客的论文...")
        conn = None
        try:
            conn = await asyncpg.connect(self.db_url)
            
            # 查询 blog 为 NULL 或 空字符串 或 只有空白字符 的记录
            query = """
                SELECT doc_id 
                FROM papers 
                WHERE blog IS NULL 
                   OR trim(blog) = ''
            """
            
            rows = await conn.fetch(query)
            paper_ids = [row['doc_id'] for row in rows]
            
            logger.info(f"📋 数据库中共有 {len(paper_ids)} 篇论文缺少博客内容")
            return paper_ids
            
        except Exception as e:
            logger.error(f"❌ 数据库查询失败: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    def prepare_update_data(self, target_paper_ids: List[str]) -> List[Dict[str, str]]:
        """
        根据目标ID列表，去本地查找对应的文件
        """
        papers_data = []
        self.total_target_papers = len(target_paper_ids)
        
        if not self.blogs_dir.exists():
            logger.error(f"❌ 本地博客目录不存在: {self.blogs_dir}")
            return []

        logger.info("📂 开始匹配本地文件...")
        
        # 为了提高效率，先获取目录下所有文件的集合
        local_files_map = {f.stem: f for f in self.blogs_dir.glob("*.md")}
        
        with tqdm(total=len(target_paper_ids), desc="📖 匹配并读取", unit="篇", ncols=100) as pbar:
            for paper_id in target_paper_ids:
                # 尝试多种文件名匹配 (有时候文件名可能有版本号差异，这里假设严格匹配或基本匹配)
                # 优先直接匹配 paper_id.md
                md_file = local_files_map.get(paper_id)
                
                if md_file and md_file.exists():
                    try:
                        with open(md_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        
                        if content:
                            papers_data.append({
                                "paper_id": paper_id,
                                "blog_content": content
                            })
                            self.found_local_files += 1
                        else:
                            # 文件存在但为空
                            pass
                            
                    except Exception as e:
                        logger.warning(f"⚠️ 读取文件出错 {md_file}: {e}")
                else:
                    self.missing_local_files += 1
                
                pbar.update(1)

        logger.info(f"✅ 匹配完成: 需更新 {len(target_paper_ids)} 篇 -> 找到本地文件 {len(papers_data)} 篇")
        if self.missing_local_files > 0:
            logger.warning(f"⚠️  有 {self.missing_local_files} 篇论文在数据库中缺少博客，且本地未找到对应文件")
            
        return papers_data

    async def update_blogs_batch(self, client: httpx.AsyncClient, papers_data: List[Dict[str, str]]) -> Dict:
        """调用API批量更新博客 (逻辑保持不变)"""
        request_data = {"papers": papers_data}
        try:
            response = await client.put(
                self.update_blogs_endpoint,
                json=request_data,
                timeout=120.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "success",
                    "updated_count": result.get("updated_count", 0),
                    "total_requested": len(papers_data),
                    "message": result.get("message", "更新成功")
                }
            else:
                return {
                    "status": "failed",
                    "updated_count": 0,
                    "total_requested": len(papers_data),
                    "message": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "status": "failed",
                "updated_count": 0,
                "total_requested": len(papers_data),
                "message": str(e)
            }

    async def run(self, dry_run: bool = False):
        """主流程"""
        # 1. 检查 API 健康
        if not await self.check_server_health():
            logger.error("❌ 服务器未就绪，终止操作")
            return

        # 2. 从数据库获取目标列表
        target_ids = await self.fetch_missing_blog_ids()
        if not target_ids:
            logger.info("✨ 数据库中所有论文均已有博客，无需更新")
            return

        # 3. 准备数据（读取本地文件）
        papers_to_update = self.prepare_update_data(target_ids)
        if not papers_to_update:
            logger.warning("⚠️  未找到任何可更新的本地博客文件")
            return

        if dry_run:
            logger.info("🔍 Dry Run 模式结束，不发送请求")
            return

        # 4. 批量更新
        logger.info(f"🚀 开始通过 API 更新 {len(papers_to_update)} 篇论文...")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            total_batches = (len(papers_to_update) + self.batch_size - 1) // self.batch_size
            
            with tqdm(total=total_batches, desc="💾 提交更新", unit="批次") as pbar:
                for i in range(0, len(papers_to_update), self.batch_size):
                    batch = papers_to_update[i : i + self.batch_size]
                    result = await self.update_blogs_batch(client, batch)
                    
                    self.results.append(result)
                    if result["status"] == "success":
                        self.successful_updates += result["updated_count"]
                    else:
                        self.failed_updates += result["total_requested"]
                        logger.error(f"批次失败: {result['message']}")
                    
                    pbar.update(1)
                    await asyncio.sleep(0.2)

        self.print_summary()

    def print_summary(self):
        print("\n" + "="*60)
        print("📊 更新结果摘要")
        print("="*60)
        print(f"📋 DB中缺少博客总数: {self.total_target_papers}")
        print(f"📂 本地找到对应文件: {self.found_local_files}")
        print(f"👻 本地缺失对应文件: {self.missing_local_files}")
        print("-" * 30)
        print(f"✅ 成功写入数据库:   {self.successful_updates}")
        print(f"❌ 写入失败:         {self.failed_updates}")
        print("="*60)


async def main():
    # 配置文件路径
    config_path = "/data3/guofang/peirongcan/PaperIgnition/orchestrator/production_config.yaml"
    
    try:
        updater = BatchBlogUpdater(
            config_path=config_path,
            batch_size=50
        )
        await updater.run(dry_run= True)
        
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())