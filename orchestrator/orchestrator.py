"""
Daily Task Orchestrator for PaperIgnition
Converts daily_task.sh into a comprehensive Python orchestrator
"""

import asyncio
import os
import sys
import logging
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from generate_blog import run_Gemini_blog_generation_default, run_Gemini_blog_generation_recommend, run_batch_generation_abs, run_batch_generation_title

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from job_util import JobLogger
from api_clients import IndexAPIClient, BackendAPIClient
from paper_pull import PaperPullService
from AIgnite.data.docset import DocSet


def load_orchestrator_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load orchestrator configuration from YAML file

    Args:
        config_path: Path to config file. If None, loads development config by default.

    Returns:
        Configuration dictionary
    """
    if config_path is None:
        # Use path relative to this script's directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "development_config.yaml")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


class PaperIgnitionOrchestrator:
    """Orchestrator for daily PaperIgnition tasks"""

    def __init__(
        self,
        orchestrator_config_path: Optional[str] = None
    ):
        self.setup_environment()

        # Load orchestrator configuration
        self.orch_config = load_orchestrator_config(orchestrator_config_path)

        self.setup_logging()

        # Use configuration from orchestrator config (no need for separate backend config files)
        self.backend_config = self.orch_config
        self.index_api_url = str(self.orch_config["index_service"]["host"])
        self.backend_api_url = str(self.orch_config["backend_service"]["host"])

        logging.info(f"Using unified configuration")
        logging.info(f"Index API URL: {self.index_api_url}")
        logging.info(f"Backend API URL: {self.backend_api_url}")

        # Initialize API clients
        self.index_client = IndexAPIClient(self.index_api_url)
        self.backend_client = BackendAPIClient(self.backend_api_url)

        # Initialize paper pull service with config
        base_dir = os.path.join(self.project_root, "orchestrator")
        paper_config = self.orch_config["paper_pull"]

        self.paper_service = PaperPullService(
            base_dir=base_dir,
            max_workers=paper_config["max_workers"],
            time_slots_count=paper_config["time_slots_count"],
            location=paper_config["location"],
            count_delay=paper_config["count_delay"],
            max_papers=paper_config.get("max_papers")
        )

        # Initialize job logger with orchestrator config
        self.job_logger = JobLogger(config=self.orch_config)

    def setup_logging(self):
        """Setup logging configuration"""
        logs_dir = Path(__file__).parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        log_file = logs_dir / "paperignition_execution.log"

        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        # Create formatters
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Create file handler
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # Add handlers to root logger
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        root_logger.setLevel(logging.INFO)

    def setup_environment(self):
        """Setup environment variables and paths"""
        self.project_root = str(Path(__file__).parent.parent)
        os.environ['PYTHONPATH'] = self.project_root
        os.chdir(self.project_root)

    async def run_fetch_daily_papers(self) -> List[DocSet]:
        """Fetch daily papers using paper_pull module"""
        logging.info("Starting daily paper fetch...")
        job_id = await self.job_logger.start_job_log(job_type="daily_paper_fetch", username="system")

        success = False
        papers = []
        try:
            # 1. Check connection health before indexing
            if not self.index_client.is_healthy():
                logging.error("Index service not healthy or not ready")
                await self.job_logger.complete_job_log(job_id, status="failed", details={"message": "Index service not healthy"})
                return papers

            # 2. Fetch daily papers using PaperPullService
            papers = self.paper_service.fetch_daily_papers()
            logging.info(f"Fetched {len(papers)} papers from arXiv")

            # 3. Index papers
            if papers:
                self.index_client.index_papers(papers)

            success = len(papers) > 0
            logging.info(f"Daily paper fetch complete. Fetched {len(papers)} papers.")

            status = "success" if success else "failed"
            details = f"Fetched {len(papers)} papers" if success else "Paper fetch failed"
            await self.job_logger.complete_job_log(job_id, status=status, details={"message": details})

        except Exception as e:
            await self.job_logger.complete_job_log(job_id, status="failed", error_message=str(e))
            raise

        return papers

    async def all_paper_blog_generation(self, all_papers: List[DocSet]):
        """
        Generate blog digests for all papers in batches.
        """
        username = "BlogBot@gmail.com"

        job_id = await self.job_logger.start_job_log(
            job_type="daily_blog_generation", username=username
        )
        logging.info(f"Start JobLogger for job: {job_id}")

        seen_paper_ids = set()
        unique_papers = []
        for paper in all_papers:
            if paper.doc_id not in seen_paper_ids:
                seen_paper_ids.add(paper.doc_id)
                unique_papers.append(paper)
        
        logging.info(f"去重前论文数量: {len(all_papers)}")
        logging.info(f"去重后论文数量: {len(unique_papers)}")
        
        # 使用去重后的论文列表
        all_papers = unique_papers

        # 4. Generate blog digests for users in batches
        logging.info("Generating blog digests for users...")
        
        batch_size = 50
        total_papers = len(all_papers)
        processed_count = 0
        failed_batches = 0

        for batch_start in range(0, total_papers, batch_size):
            batch_end = min(batch_start + batch_size, total_papers)
            batch_papers = all_papers[batch_start:batch_end]
            
            logging.info(f"🔄 Processing batch {batch_start//batch_size + 1}: papers {batch_start+1}-{batch_end} of {total_papers}")
            
            try:
                # 生成当前批次的博客
                output_path = self.orch_config["blog_generation"]["output_path"]
                # Convert to absolute path based on project root
                if not os.path.isabs(output_path):
                    output_path = os.path.join(self.project_root, output_path)
                run_Gemini_blog_generation_default(batch_papers, output_path=output_path)
            
                logging.info(f"✅ Blog generation completed for batch {batch_start//batch_size + 1}")
                
                # 立即处理并保存当前批次的论文
                paper_infos = []
                for paper in batch_papers:
                    try:
                        # 使用绝对路径，基于当前脚本所在目录
                        blog_path = os.path.join(output_path, f"{paper.doc_id}.md")
                        with open(blog_path, encoding="utf-8") as file:
                            blog = file.read()
                    except FileNotFoundError:
                        blog = None

                    paper_infos.append({
                        "paper_id": paper.doc_id,
                        "title": paper.title,
                        "authors": ", ".join(paper.authors),
                        "abstract": paper.abstract,
                        "url": "https://arxiv.org/pdf/"+ paper.doc_id,
                        "content": paper.abstract,
                        "blog": blog,
                        "recommendation_reason": f"This is a dummy recommendation reason for paper {paper.title}",
                        "submitted": paper.published_date,
                        "relevance_score": 0.5
                    })
                
                # 保存当前批次
                logging.info(f"💾 Saving batch {batch_start//batch_size + 1} ({len(paper_infos)} papers)...")
                # TODO: Remove after migration
                self.backend_client.recommend_papers_batch(username, paper_infos)

                # Update papers blog field in index service
                papers_blog_data = [
                    {"paper_id": p["paper_id"], "blog_content": p["blog"]}
                    for p in paper_infos if p.get("paper_id") and p.get("blog")
                ]
                if papers_blog_data:
                    self.index_client.update_papers_blog(papers_blog_data)
                processed_count += len(batch_papers)
                logging.info(f"📊 Progress: {processed_count}/{total_papers} papers processed")
                
            except Exception as e:
                logging.error(f"❌ Blog generation failed for batch {batch_start//batch_size + 1}: {e}")
                failed_batches += 1
                continue
        detials = f"Total Papers: {total_papers}, Processed: {processed_count}, Failed Batches: {failed_batches}"
        await self.job_logger.complete_job_log(job_id=job_id, status="success" if failed_batches == 0 else "partial", details=detials) 
        logging.info(f"🎉 All batches completed! Details: {detials}")

    async def run_all_papers_blog_generation(self, papers: List[DocSet]):
        """Run blog generation task"""
        logging.info("Starting blog generation...")
        await self.all_paper_blog_generation(papers)
        logging.info("Blog generation completed successfully")

    async def blog_generation_for_all_users(self):
        """
        Generate blog digests for all users based on their interests
        """
        all_users = self.backend_client.get_all_users()
        logging.info(f"✅ 共获取到 {len(all_users)} 个用户")

        for user in all_users:
            username = user.get("username")
            if username == "BlogBot@gmail.com": continue
            job_id = await self.job_logger.start_job_log(job_type="daily_blog_generation", username=username)

            interests = self.backend_client.get_user_interests(username)
            logging.info(f"\n=== 用户: {username}，兴趣: {interests} ===")
            if not interests:
                logging.warning(f"用户 {username} 无兴趣关键词，跳过推荐。")
                continue

            # 获取用户已有的论文推荐，用于过滤
            existing_paper_ids = self.backend_client.get_existing_paper_ids(username)
            if existing_paper_ids:
                logging.info(f"用户 {username} 已有 {len(existing_paper_ids)} 篇论文推荐")
                logging.info(f"已有论文ID: {existing_paper_ids[:5]}...")  # 只显示前5个
            
            all_papers = []
            
            for query in interests:
                logging.info(f"[VECTOR] 用户 {username} 兴趣: {query}")
                
                # 构建过滤器，排除用户已有的论文ID，同时只包含最近3天的论文
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime('%Y-%m-%d')
                # arxiv API has two day delay, so we extend to 5 days for recent 3 days
                start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')

                 # 构建过滤器，排除用户已有的论文ID
                filter_params = None
                if existing_paper_ids:
                    filter_params = {
                        "include": {
                        "published_date": [start_date, end_date]
                        },
                        "exclude": {
                            "doc_ids": existing_paper_ids
                        }
                    }
                    logging.info(f"应用过滤器，排除 {len(existing_paper_ids)} 个已有论文ID")

                # Search for papers matching the query
                user_rec_config = self.orch_config["user_recommendation"]
                papers = self.index_client.find_similar(
                    query=query,
                    top_k=user_rec_config["top_k"],
                    search_strategy=user_rec_config["search_strategy"],
                    similarity_cutoff=user_rec_config["similarity_cutoff"],
                    filters=filter_params
                )
                
                all_papers.extend(papers)

            # 添加去重逻辑：确保论文ID不重复
            seen_paper_ids = set()
            unique_papers = []
            for paper in all_papers:
                if paper.doc_id not in seen_paper_ids:
                    seen_paper_ids.add(paper.doc_id)
                    unique_papers.append(paper)
            
            logging.info(f"去重前论文数量: {len(all_papers)}")
            logging.info(f"去重后论文数量: {len(unique_papers)}")
            
            # 使用去重后的论文列表
            all_papers = unique_papers

            # 4. Generate blog digests for users
            logging.info("Generating blog digests for users...")
            if all_papers:
                output_path = self.orch_config["blog_generation"]["output_path"]
                # Convert to absolute path based on project root
                if not os.path.isabs(output_path):
                    output_path = os.path.join(self.project_root, output_path)
                blog = run_Gemini_blog_generation_recommend(all_papers, output_path=output_path)
                logging.info("Digest generation complete.")

                #blog_abs = await run_batch_generation_abs(all_papers)
                #blog_title = await run_batch_generation_title(all_papers)

                blog_abs = ""
                blog_title = ""
                
                paper_infos = []
                for i, paper in enumerate(all_papers):
                    try:
                        # Use the configured output_path
                        output_path = self.orch_config["blog_generation"]["output_path"]
                        if not os.path.isabs(output_path):
                            output_path = os.path.join(self.project_root, output_path)
                        blog_path = os.path.join(output_path, f"{paper.doc_id}.md")
                        with open(blog_path, encoding="utf-8") as file:
                            blog = file.read()
                    except FileNotFoundError:
                        blog = None  # Blog file not found, will be skipped by API
                    
                    # 获取对应的博客摘要和标题
                    blog_abs_content = blog_abs[i] if blog_abs and i < len(blog_abs) else None
                    blog_title_content = blog_title[i] if blog_title and i < len(blog_title) else None
                    
                    paper_infos.append({
                        "paper_id": paper.doc_id,
                        "title": paper.title,
                        "authors": ", ".join(paper.authors),
                        "abstract": paper.abstract,
                        "url": "https://arxiv.org/pdf/"+paper.doc_id,
                        "content": paper.abstract,  # 这里用abs填充吧
                        "blog": blog,
                        "recommendation_reason": "This is a dummy recommendation reason for paper " + paper.title,
                        "relevance_score": 0.5,
                        "blog_abs": blog_abs_content,
                        "blog_title": blog_title_content,
                        "submitted": paper.published_date,
                    })

                # 5. Write recommendations
                self.backend_client.recommend_papers_batch(username, paper_infos)
                await self.job_logger.complete_job_log(job_id=job_id, details=f"Recommended {len(paper_infos)} papers.")
            else:
                logging.warning(f"用户 {username} 没有找到相关论文，跳过博客生成和推荐保存")
                await self.job_logger.complete_job_log(job_id=job_id, status="failed", details="No relevant papers found.")
                continue

    async def update_papers_blog_field(self, paper_infos: List[Dict[str, Any]]):
        """Update blog field in papers table for each paper via index service API"""
        try:
            import httpx
            
            # Prepare the request data
            papers_data = []
            for paper_info in paper_infos:
                paper_id = paper_info.get("paper_id")
                blog_content = paper_info.get("blog")
                
                if paper_id and blog_content:
                    papers_data.append({
                        "paper_id": paper_id,
                        "blog_content": blog_content
                    })
                else:
                    logging.warning(f"Skipping paper {paper_id} - missing paper_id or blog content")
            
            if not papers_data:
                logging.warning("No valid papers to update")
                return
            
            # Call the index service API directly to update papers blog field
            request_data = {"papers": papers_data}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(
                    f"{self.index_api_url}/update_papers_blog/",
                    json=request_data
                )
                response.raise_for_status()
                
                result = response.json()
                logging.info(f"✅ Index service API response: {result}")
                
        except httpx.HTTPError as e:
            logging.error(f"❌ HTTP error when updating papers blog field: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"❌ Failed to update papers blog field: {str(e)}")
            raise

    async def run_per_user_blog_generation(self):
        """Run recommendation generation task for each user"""
        logging.info("Starting recommendation generation...")
        logging.info("Starting blog generation for existing users...")
        await self.blog_generation_for_all_users()
        logging.info("Blog generation for existing users complete.")

    async def run_all_tasks(self):
        """Run all daily tasks based on configuration and return results"""
        start_time = datetime.now()
        logging.info(f"Starting all daily tasks at {start_time}")

        # Get stage configuration
        stages = self.orch_config["stages"]
        parallel_execution = self.orch_config["job_execution"]["enable_parallel_blog_generation"]

        overall_job_id = await self.job_logger.start_job_log(job_type="daily_tasks_orchestrator", username="system")

        results = {
            "start_time": start_time.isoformat(),
            "paper_fetch": False,
            "all_papers_blog_generation": False,
            "per_user_blog_generation": False,
            "papers_count": 0,
            "stages_run": []
        }

        try:
            papers = []

            # === Step 1: Fetch and Index Papers ===
            if stages["fetch_daily_papers"]:
                logging.info("=== Step 1: Fetching daily papers ===")
                results["stages_run"].append("fetch_daily_papers")
                await self.job_logger.update_job_log(overall_job_id, status="running", details={"step": "paper_fetch"})

                papers = await self.run_fetch_daily_papers()
                results["papers_fetched"] = len(papers)
                results["paper_fetch"] = len(papers) > 0

                if len(papers) == 0:
                    logging.warning("No papers fetched, skipping downstream tasks")
                    await self.job_logger.complete_job_log(
                        overall_job_id,
                        status="partial",
                        details={"reason": "No papers were fetched", "stages_run": results["stages_run"]}
                    )
                    return results
            else:
                logging.info("Skipping paper fetch stage (disabled in config)")

            # === Step 2: Blog Generation ===
            if stages["generate_all_papers_blog"] or stages["generate_per_user_blogs"]:
                if len(papers) == 0:
                    logging.warning("No papers available for default blog generation")
                logging.info("=== Step 2: Blog generation ===")
                await self.job_logger.update_job_log(overall_job_id, status="running", details={"step": "blog_generation"})

                try:
                    tasks = []

                    if stages["generate_all_papers_blog"] and papers:
                        results["stages_run"].append("generate_all_papers_blog")
                        tasks.append(("all_papers", self.run_all_papers_blog_generation(papers)))

                    if stages["generate_per_user_blogs"]:
                        results["stages_run"].append("generate_per_user_blogs")
                        tasks.append(("per_user", self.run_per_user_blog_generation()))

                    # Run tasks based on configuration
                    if parallel_execution and len(tasks) > 1:
                        logging.info("Running blog generation tasks in parallel")
                        blog_gen_results = await asyncio.gather(
                            *[task[1] for task in tasks],
                            return_exceptions=True
                        )
                        for i, (task_name, _) in enumerate(tasks):
                            result = blog_gen_results[i]
                            if isinstance(result, Exception):
                                logging.error(f"{task_name} blog generation failed: {result}")
                                results[f"{task_name}_blog_generation"] = False
                            else:
                                results[f"{task_name}_blog_generation"] = True
                    else:
                        logging.info("Running blog generation tasks sequentially")
                        for task_name, task_coro in tasks:
                            try:
                                await task_coro
                                results[f"{task_name}_blog_generation"] = True
                            except Exception as e:
                                logging.error(f"{task_name} blog generation failed: {e}")
                                results[f"{task_name}_blog_generation"] = False

                except Exception as e:
                    logging.error(f"Blog generation tasks failed: {e}")
                    results["error"] = str(e)
            else:
                logging.info("Skipping all blog generation stages (disabled in config)")

            # Complete overall job
            success_conditions = []
            if stages["fetch_daily_papers"]:
                success_conditions.append(results["paper_fetch"])
            if stages["generate_all_papers_blog"]:
                success_conditions.append(results.get("all_papers_blog_generation", True))
            if stages["generate_per_user_blogs"]:
                success_conditions.append(results.get("per_user_blog_generation", True))

            final_status = "success" if all(success_conditions) else "partial"

            await self.job_logger.complete_job_log(
                overall_job_id,
                status=final_status,
                details=results
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logging.info(f"=== All daily tasks completed in {duration:.2f} seconds ===")
            logging.info(f"Results: {results}")

            return results

        except Exception as e:
            logging.error(f"Daily tasks orchestrator failed: {e}")
            await self.job_logger.complete_job_log(
                overall_job_id,
                status="failed",
                error_message=str(e),
                details=results
            )
            raise
        finally:
            await self.job_logger.close()


# Main execution
async def main():
    orchestrator = PaperIgnitionOrchestrator()

    try:
        results = await orchestrator.run_all_tasks()
        return results
    except Exception as e:
        logging.error(f"Orchestration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())