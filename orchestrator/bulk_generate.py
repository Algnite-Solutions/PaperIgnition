#!/usr/bin/env python3
"""
基于数据库状态批量生成论文博客脚本

逻辑：
1. 连接 Metadata 数据库
2. 查询 blog 字段为空的 paper doc_id
3. 从 jsons 目录加载对应的论文数据创建 DocSet 对象
4. 调用 generate_blog.py 的 run_batch_generation 批量生成博客
5. 保存生成的博客到 blogs 目录
6. 调用 API 更新数据库中的 blog 字段

使用方法：
    python bulk_generate.py
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path
from typing import List
import logging
import yaml
import json
from tqdm import tqdm
import httpx

# 添加项目路径到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root.parent / "AIgnite"))  # 假设AIgnite路径

# 导入 DocSet 和生成函数
from AIgnite.data.docset import DocSet
from generate_blog import run_batch_generation, load_config as gb_load_config

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bulk_generate.log')
    ]
)

# 禁用第三方库的 DEBUG 日志
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('asyncpg').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class BulkBlogGenerator:
    def __init__(self, config_path: str = None, batch_size: int = 10):
        # --- 配置加载逻辑 ---
        if config_path:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    full_config = yaml.safe_load(f)
                
                self.index_config = full_config.get('index_service', {})
                self.blog_config = full_config.get('blog_generation', {})
                
                # 获取数据库连接 URL
                self.db_url = self.index_config.get('metadata_db', {}).get('db_url')
                if not self.db_url:
                    raise ValueError("配置文件中缺少 index_service.metadata_db.db_url")
                
                # API URL
                self.api_host = self.index_config.get('host', "http://localhost:8002")
                self.update_blogs_endpoint = f"{self.api_host.rstrip('/')}/update_papers_blog/"
                
                # JSON 文件目录
                self.json_folder = full_config.get('PAPER_STORAGE', {}).get('json_folder', 
                    "/data3/guofang/peirongcan/PaperIgnition/orchestrator/jsons")
                
                # 博客输出目录
                self.output_path = self.blog_config.get('output_path', 
                    "/data3/guofang/peirongcan/PaperIgnition/orchestrator/blogs")
                
                logger.info(f"✅ 成功加载配置文件: {config_path}")
                
            except Exception as e:
                logger.error(f"❌ 配置加载失败: {e}，使用硬编码默认值")
                self.db_url = "postgresql://postgres:11111@localhost:5432/paperignition"
                self.api_host = "http://localhost:8002"
                self.update_blogs_endpoint = f"{self.api_host.rstrip('/')}/update_papers_blog/"
                self.json_folder = "/data3/guofang/peirongcan/PaperIgnition/orchestrator/jsons"
                self.output_path = "/data3/guofang/peirongcan/PaperIgnition/orchestrator/blogs"
        else:
            logger.error("❌ 必须提供配置文件路径")
            sys.exit(1)
        
        self.batch_size = batch_size
        
        # 统计信息
        self.total_target_papers = 0
        self.loaded_papers = 0
        self.missing_json_files = 0
        self.successful_generations = 0
        self.failed_generations = 0
        self.successful_db_updates = 0
        self.failed_db_updates = 0
        
        logger.info(f"🗄️  DB URL: {self.db_url.split('@')[-1]}")  # 隐藏密码
        logger.info(f"📁 JSON目录: {self.json_folder}")
        logger.info(f"📁 输出目录: {self.output_path}")
        logger.info(f"🔧 API URL: {self.update_blogs_endpoint}")

    async def fetch_missing_blog_doc_ids(self) -> List[str]:
        """
        连接数据库，查询所有 blog 字段为空或NULL的 paper doc_id
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
            doc_ids = [row['doc_id'] for row in rows]
            
            logger.info(f"📋 数据库中共有 {len(doc_ids)} 篇论文缺少博客内容")
            self.total_target_papers = len(doc_ids)
            return doc_ids
            
        except Exception as e:
            logger.error(f"❌ 数据库查询失败: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    async def load_papers_from_doc_ids(self, doc_ids: List[str]) -> List[DocSet]:
        """
        根据doc_id列表，从JSON目录加载论文数据创建DocSet对象
        """
        papers = []
        json_folder_path = Path(self.json_folder)
        
        if not json_folder_path.exists():
            logger.error(f"❌ JSON目录不存在: {json_folder_path}")
            return []
        
        logger.info("📂 开始加载论文数据...")
        
        with tqdm(total=len(doc_ids), desc="📖 加载论文", unit="篇", ncols=100) as pbar:
            for doc_id in doc_ids:
                json_file = json_folder_path / f"{doc_id}.json"
                
                if json_file.exists():
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        if data:
                            paper = DocSet(**data)
                            papers.append(paper)
                            self.loaded_papers += 1
                        else:
                            logger.warning(f"⚠️ JSON文件为空: {json_file}")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ 加载JSON出错 {json_file}: {e}")
                        self.missing_json_files += 1
                else:
                    logger.warning(f"⚠️ JSON文件不存在: {json_file}")
                    self.missing_json_files += 1
                
                pbar.update(1)
        
        logger.info(f"✅ 加载完成: 找到 {len(papers)} 篇论文数据")
        if self.missing_json_files > 0:
            logger.warning(f"⚠️  有 {self.missing_json_files} 篇论文缺少JSON文件")
        
        return papers

    async def run_generation(self, papers: List[DocSet]) -> int:
        """
        调用run_batch_generation生成博客，每批生成后立即更新数据库
        分批生成以避免并发过载，返回总成功生成数
        """
        if not papers:
            return 0
        
        total_successful = 0
        total_batches = (len(papers) + self.batch_size - 1) // self.batch_size
        
        logger.info(f"🚀 开始分批生成 {len(papers)} 篇博客 (每批 {self.batch_size} 篇，共 {total_batches} 批)")
        
        with tqdm(total=total_batches, desc="📝 生成批次", unit="批") as batch_pbar:
            for i in range(0, len(papers), self.batch_size):
                batch_papers = papers[i:i + self.batch_size]
                batch_start = i + 1
                batch_end = min(i + self.batch_size, len(papers))
                
                batch_successful = 0
                try:
                    logger.info(f"处理第 {batch_start}-{batch_end} 篇 (批次 {i//self.batch_size + 1}/{total_batches})")
                    blogs = await run_batch_generation(batch_papers, output_path=self.output_path)
                    
                    if blogs:
                        # 假设成功，收集本批 doc_ids 并立即更新 DB
                        batch_doc_ids = [paper.doc_id for paper in batch_papers]
                        await self.update_to_database(batch_doc_ids)
                        batch_successful = len(batch_papers)
                        self.successful_generations += batch_successful
                        logger.info(f"✅ 批次 {i//self.batch_size + 1} 生成并更新 DB 成功: {batch_successful} 篇")
                    else:
                        self.failed_generations += len(batch_papers)
                        logger.warning(f"⚠️ 批次 {i//self.batch_size + 1} 生成失败: {len(batch_papers)} 篇 (跳过 DB 更新)")
                    
                except Exception as e:
                    logger.error(f"❌ 批次 {i//self.batch_size + 1} 生成出错: {e}")
                    self.failed_generations += len(batch_papers)
                    logger.warning(f"⚠️ 批次 {i//self.batch_size + 1} 跳过 DB 更新")
                
                total_successful += batch_successful
                batch_pbar.update(1)
                await asyncio.sleep(1.0)  # 批次间延迟，避免服务器过载
        
        logger.info(f"✅ 整体生成完成: {total_successful} 篇成功 (已每批更新 DB)")
        return total_successful

    async def update_to_database(self, doc_ids: List[str]) -> bool:
        """
        读取生成的.md文件，调用API批量更新数据库中的blog字段
        """
        if not doc_ids:
            return False
        
        # 收集论文数据：paper_id 和 blog_content
        papers_data = []
        blogs_dir_path = Path(self.output_path)
        
        if not blogs_dir_path.exists():
            logger.error(f"❌ 博客目录不存在: {blogs_dir_path}")
            return False
        
        logger.info("📂 开始准备DB更新数据...")
        
        with tqdm(total=len(doc_ids), desc="📖 读取博客文件", unit="篇", ncols=100) as pbar:
            for doc_id in doc_ids:
                md_file = blogs_dir_path / f"{doc_id}.md"
                
                if md_file.exists():
                    try:
                        with open(md_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        
                        if content:
                            papers_data.append({
                                "paper_id": doc_id,
                                "blog_content": content
                            })
                        else:
                            logger.warning(f"⚠️ 博客文件为空: {md_file}")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ 读取博客文件出错 {md_file}: {e}")
                else:
                    logger.warning(f"⚠️ 博客文件不存在: {md_file}")
                
                pbar.update(1)
        
        if not papers_data:
            logger.warning("⚠️  未找到任何生成的博客文件，无法更新DB")
            return False
        
        logger.info(f"🚀 开始通过 API 更新 {len(papers_data)} 篇论文的博客到数据库...")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            total_batches = (len(papers_data) + self.batch_size - 1) // self.batch_size
            
            with tqdm(total=total_batches, desc="💾 提交DB更新", unit="批次") as pbar:
                for i in range(0, len(papers_data), self.batch_size):
                    batch = papers_data[i : i + self.batch_size]
                    request_data = {"papers": batch}
                    
                    try:
                        response = await client.put(
                            self.update_blogs_endpoint,
                            json=request_data,
                            timeout=120.0
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            updated_count = result.get("updated_count", 0)
                            self.successful_db_updates += updated_count
                            logger.info(f"✅ 批次更新成功: {updated_count}/{len(batch)} 篇")
                        else:
                            failed_count = len(batch)
                            self.failed_db_updates += failed_count
                            logger.error(f"❌ 批次更新失败: HTTP {response.status_code} - {response.text}")
                        
                    except Exception as e:
                        failed_count = len(batch)
                        self.failed_db_updates += failed_count
                        logger.error(f"❌ API 请求出错: {e}")
                    
                    pbar.update(1)
                    await asyncio.sleep(0.2)  # 避免请求过快
        
        logger.info("✅ DB更新完成")
        return True

    async def run(self, dry_run: bool = False):
        """
        主流程
        """
        # 1. 从数据库获取目标doc_ids
        doc_ids = await self.fetch_missing_blog_doc_ids()
        if not doc_ids:
            logger.info("✨ 数据库中所有论文均已有博客，无需生成")
            return
        
        # 2. 加载论文数据
        papers = await self.load_papers_from_doc_ids(doc_ids)
        if not papers:
            logger.warning("⚠️  未找到任何可生成的论文数据")
            return
        
        if dry_run:
            logger.info("🔍 Dry Run 模式结束，不生成博客")
            return
        
        # 3. 生成博客 (每批内已更新 DB)
        total_generated = await self.run_generation(papers)
        
        # 4. 无需额外更新 (已在每批内处理)
        if total_generated == 0:
            logger.warning("⚠️  无成功生成的博客")
        
        # 5. 打印摘要
        self.print_summary()

    def print_summary(self):
        print("\n" + "="*60)
        print("📊 生成与更新结果摘要")
        print("="*60)
        print(f"📋 DB中缺少博客总数: {self.total_target_papers}")
        print(f"📂 成功加载论文: {self.loaded_papers}")
        print(f"👻 缺少JSON文件: {self.missing_json_files}")
        print("-" * 30)
        print(f"✅ 成功生成博客:   {self.successful_generations}")
        print(f"❌ 生成失败:         {self.failed_generations}")
        print("-" * 30)
        print(f"✅ 成功更新DB:      {self.successful_db_updates}")
        print(f"❌ DB更新失败:       {self.failed_db_updates}")
        print("="*60)


async def main():
    # 配置文件路径
    config_path = "/data3/guofang/peirongcan/PaperIgnition/orchestrator/development_config.yaml"
    
    try:
        generator = BulkBlogGenerator(
            config_path=config_path,
            batch_size=10  # 生成较慢，批次小
        )
        await generator.run(dry_run=False)
        
    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
