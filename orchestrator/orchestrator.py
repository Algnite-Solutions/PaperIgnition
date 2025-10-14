"""
Daily Task Orchestrator for PaperIgnition
Converts daily_task.sh into a comprehensive Python orchestrator
"""

import asyncio
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import requests
from generate_blog import run_batch_generation, run_Gemini_blog_generation, run_batch_generation_abs, run_batch_generation_title

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import utils
from job_util import JobLogger
from backend.app.db_utils import load_config
from AIgnite.data.docset import DocSetList, DocSet


def get_user_interest(username: str, backend_api_url: str) -> List[str]:
    """
    获取指定用户的研究兴趣（interests_description）
    """
    response = requests.get(f"{backend_api_url}/api/users/by_email/{username}")
    response.raise_for_status()
    user_data = response.json()
    return user_data.get("interests_description", [])


def get_all_users(backend_api_url: str) -> List[Dict]:
    """
    获取所有用户信息，返回用户字典列表（含 username, interests_description 等）
    """
    resp = requests.get(f"{backend_api_url}/api/users/all", timeout=100.0)
    resp.raise_for_status()
    return resp.json()


class PaperIgnitionOrchestrator:
    """Orchestrator for daily PaperIgnition tasks"""

    def __init__(self, local_mode: bool = True):
        self.local_mode = local_mode
        self.setup_logging()
        self.setup_environment()
        logging.info(f"PaperIgnitionOrchestrator: local mode: {local_mode}")

        # Load configuration
        config_file = "test_config.yaml" if local_mode else "app_config.yaml"
        config_path = os.path.join(self.project_root, "backend", "configs", config_file)
        self.config = load_config(config_path=config_path)
        self.index_api_url = str(self.config["INDEX_SERVICE"]["host"])
        self.backend_api_url = str(self.config["APP_SERVICE"]["host"])

        logging.info(f"Configuration loaded from {config_path}, config: {self.config}")

        # Initialize job logger
        self.job_logger = JobLogger(config_path=config_path)

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
            papers = utils.fetch_daily_papers(self.index_api_url, config=self.config, job_logger=self.job_logger)
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
                output_path = ""
                if self.local_mode:
                    output_path = "./blogsByGemini"
                    run_Gemini_blog_generation(batch_papers, output_path=output_path)
                else:
                    output_path="/data3/guofang/peirongcan/PaperIgnition/orchestrator/blogs"
                    await run_batch_generation(batch_papers, output_path=output_path)
            
                logging.info(f"✅ Blog generation completed for batch {batch_start//batch_size + 1}")
                
                for paper in batch_papers:
                    try:
                        # 使用绝对路径，基于当前脚本所在目录
                        blog_path = os.path.join(output_path, f"{paper.doc_id}.md")
                        with open(blog_path, encoding="utf-8") as file:
                            blog = file.read()
                    except FileNotFoundError:
                        blog = None

                    # 立即处理并保存当前批次的论文
                    paper_infos = []
                    paper_infos.append({
                        "paper_id": paper.doc_id,
                        "title": paper.title,
                        "authors": ", ".join(paper.authors),
                        "abstract": paper.abstract,
                        "url": paper.HTML_path,
                        "content": paper.abstract,
                        "blog": blog,
                        "recommendation_reason": f"This is a dummy recommendation reason for paper {paper.title}",
                        "relevance_score": 0.5
                    })
                
                # 保存当前批次
                logging.info(f"💾 Saving batch {batch_start//batch_size + 1} ({len(paper_infos)} papers)...")
                utils.save_recommendations(username, paper_infos, self.backend_api_url)
                
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
        # await self.all_paper_blog_generation(papers)
        logging.info("Blog generation completed successfully")

    async def blog_generation_for_all_users(self, user_filters: List[str] = None, skip_existing_papers: bool = True):
        """
        Generate blog digests for users based on their interests

        Args:
            user_filters: Optional list of usernames to filter. If provided, only generates for these users.
            skip_existing_papers: If True, excludes papers user already has. If False, includes all papers.
        """
        use_llm_rerank = os.getenv("USE_LLM_RERANK", "false").lower() == "true"
        logging.info(f"LLM Reranking enabled: {use_llm_rerank}")

        all_users = get_all_users(self.backend_api_url)
        logging.info(f"✅ 共获取到 {len(all_users)} 个用户")

        # Apply user filters if specified
        if user_filters:
            all_users = [u for u in all_users if u.get("username") in user_filters]
            logging.info(f"🔍 User filters applied: {user_filters} ({len(all_users)} user(s) matched)")
            if not all_users:
                logging.error(f"❌ No users found matching filters {user_filters}")
                return

        for user in all_users:
            username = user.get("username")
            if username == "BlogBot@gmail.com": continue
            job_id = await self.job_logger.start_job_log(job_type="daily_blog_generation", username=username)
            interests = get_user_interest(username, self.backend_api_url)
            logging.info(f"\n=== 用户: {username}，兴趣: {interests} ===")
            if not interests:
                logging.warning(f"用户 {username} 无兴趣关键词，跳过推荐。")
                continue
            
            # 获取用户已有的论文推荐，用于过滤（仅在skip_existing_papers=True时）
            existing_paper_ids = []
            if skip_existing_papers:
                try:
                    user_papers_response = requests.get(f"{self.backend_api_url}/api/papers/recommendations/{username}")
                    if user_papers_response.status_code == 200:
                        user_existing_papers = user_papers_response.json()
                        existing_paper_ids = [paper["id"] for paper in user_existing_papers if paper.get("id")]
                        logging.info(f"用户 {username} 已有 {len(existing_paper_ids)} 篇论文推荐")
                        logging.info(f"已有论文ID: {existing_paper_ids[:5]}...")  # 只显示前5个
                    else:
                        logging.error(f"获取用户 {username} 已有论文失败，状态码: {user_papers_response.status_code}")
                except Exception as e:
                    logging.error(f"获取用户 {username} 已有论文时出错: {e}")
            else:
                logging.info(f"⚠️ Skip existing papers disabled - will include all papers")

            
            all_papers = []
            
            for query in interests:
                logging.info(f"[VECTOR] 用户 {username} 兴趣: {query}")
                # 如果llm_rerank启用，需要更多初始结果
                top_k = 50 if use_llm_rerank else 5
                # 构建过滤器，排除用户已有的论文ID
                if existing_paper_ids:
                    filter_params = {
                        "exclude": {
                            "doc_ids": existing_paper_ids
                        }
                    }
                    logging.info(f"应用过滤器，排除 {len(existing_paper_ids)} 个已有论文ID")
                    papers = utils.search_papers_via_api(self.index_api_url, query, top_k, 'tf-idf', 0.1, filter_params)
                else:
                    papers = utils.search_papers_via_api(self.index_api_url, query, top_k, 'tf-idf', 0.1, filters=None)
                # Optional: LLM reranking for this query's papers
                if use_llm_rerank and papers:
                    logging.info(f"🤖 LLM reranking enabled for query: {query}")
                    try:
                        papers = await utils.rerank_papers_with_llm(
                            query=query,
                            papers=papers,
                            top_k=5,
                            api_key=self.config.get('OPENAI_SERVICE', {}).get('api_key')
                        )
                        logging.info(f"✅ LLM reranking complete: papers now {len(papers)} items")
                    except Exception as e:
                        logging.error(f"⚠️ LLM reranking failed: {e}, continuing with original results")

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
            logging.info(f"用户 {username} papers id: {[paper.doc_id for paper in unique_papers]}")
            
            # 使用去重后的论文列表
            all_papers = unique_papers

            # 4. Generate blog digests for users
            logging.info("Generating blog digests for users...")
            if all_papers:
                output_path = ""
                try:
                    if self.local_mode:
                        output_path = "./orchestrator/blogsByGemini"
                        logging.info(f"📝 Generating blogs using Gemini API, output: {output_path}")
                        run_Gemini_blog_generation(all_papers, output_path=output_path)
                        logging.info(f"✅ Gemini blog generation complete")
                    else:
                        output_path = "./orchestrator/blogs"
                        logging.info(f"📝 Generating blogs using vLLM API, output: {output_path}")
                        await run_batch_generation(all_papers, output_path=output_path)
                        logging.info(f"✅ vLLM blog generation complete")
                except Exception as e:
                    logging.error(f"❌ Blog generation failed for user {username}: {e}")
                    import traceback
                    traceback.print_exc()
                    await self.job_logger.complete_job_log(job_id=job_id, status="failed", error_message=str(e))
                    continue
                logging.info("Digest generation complete.")

                blog_abs = await run_batch_generation_abs(all_papers)
                blog_title = await run_batch_generation_title(all_papers)
                paper_infos = []
                for i, paper in enumerate(all_papers):
                    try:
                        # 使用绝对路径，基于当前脚本所在目录
                        blog_path = os.path.join(output_path, f"{paper.doc_id}.md")
                        with open(blog_path, encoding="utf-8") as file:
                            blog = file.read()
                    except FileNotFoundError:
                        logging.warning(f"❌ Blog file not found for {paper.doc_id}, skipping this paper")
                        continue  # Skip papers without blogs
                    
                    # 获取对应的博客摘要和标题
                    blog_abs_content = blog_abs[i] if blog_abs and i < len(blog_abs) else None
                    blog_title_content = blog_title[i] if blog_title and i < len(blog_title) else None
                    
                    paper_infos.append({
                        "paper_id": paper.doc_id,
                        "title": paper.title,
                        "authors": ", ".join(paper.authors),
                        "abstract": paper.abstract,
                        "url": paper.HTML_path,
                        "content": paper.abstract,  # 或其他内容
                        "blog": blog,
                        "recommendation_reason": "This is a dummy recommendation reason for paper " + paper.title,
                        "relevance_score": 0.5,
                        "blog_abs": blog_abs_content,
                        "blog_title": blog_title_content,
                    })

                # 5. Write recommendations
                utils.save_recommendations(username, paper_infos, self.backend_api_url)
                await self.job_logger.complete_job_log(job_id=job_id, details=f"Recommended {len(paper_infos)} papers.")
            else:
                logging.warning(f"用户 {username} 没有找到相关论文，跳过博客生成和推荐保存")
                await self.job_logger.complete_job_log(job_id=job_id, status="failed", details="No relevant papers found.")
                continue

    async def run_per_user_blog_generation(self):
        """Run recommendation generation task for each user"""
        logging.info("Starting recommendation generation...")
        logging.info("Starting blog generation for existing users...")
        await self.blog_generation_for_all_users()
        logging.info("Blog generation for existing users complete.")

    async def run_all_tasks(self):
        """Run all daily tasks and return results"""
        start_time = datetime.now()
        logging.info(f"Starting all daily tasks at {start_time}")

        overall_job_id = await self.job_logger.start_job_log(job_type="daily_tasks_orchestrator", username="system")

        results = {
            "start_time": start_time.isoformat(),
            "paper_fetch": False,
            "all_papers_blog_generation": False,
            "per_user_blog_generation": False,
            "papers_count": 0
        }

        try:
            # === Step 1: Fetching daily papers ===
            logging.info("=== Step 1: Fetching daily papers ===")
            await self.job_logger.update_job_log(overall_job_id, status="running", details={"step": "paper_fetch"})
            papers = []
            # papers = await self.run_fetch_daily_papers()
            results["papers_fetched"] = len(papers)
            results["paper_fetch"] = len(papers) > 0

            # if len(papers) == 0:
            #     logging.warning("No papers fetched, skipping blog generation tasks")
            #     await self.job_logger.complete_job_log(
            #         overall_job_id,
            #         status="partial",
            #         details={"reason": "No papers were fetched"}
            #     )
            #     return results

            # === Step 2: Blog generation for all papers ===
            logging.info("=== Step 2: Blog generation for all papers ===")
            await self.job_logger.update_job_log(overall_job_id, status="running", details={"step": "all_papers_blog_gen"})

            try:
                all_papers_task = self.run_all_papers_blog_generation(papers)
                per_user_task = self.run_per_user_blog_generation()

                # Run both tasks in parallel
                blog_gen_results = await asyncio.gather(all_papers_task, per_user_task, return_exceptions=True)

                all_papers_result = blog_gen_results[0]
                per_user_result = blog_gen_results[1]

                # Check results
                results["all_papers_blog_generation"] = not isinstance(all_papers_result, Exception)
                results["per_user_blog_generation"] = not isinstance(per_user_result, Exception)

                if isinstance(all_papers_result, Exception):
                    logging.error(f"All papers blog generation failed: {all_papers_result}")

                if isinstance(per_user_result, Exception):
                    logging.error(f"Per user blog generation failed: {per_user_result}")

            except Exception as e:
                logging.error(f"Blog generation tasks failed: {e}")
                results["error"] = str(e)

            # Complete overall job
            final_status = "success" if results["paper_fetch"] and results["all_papers_blog_generation"] and results["per_user_blog_generation"] else "partial"

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
    """Main function for running daily orchestration"""
    local_mode = os.getenv("PAPERIGNITION_LOCAL_MODE", "true").lower() == "true"
    orchestrator = PaperIgnitionOrchestrator(local_mode=local_mode)

    try:
        results = await orchestrator.run_all_tasks()
        return results
    except Exception as e:
        logging.error(f"Orchestration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())