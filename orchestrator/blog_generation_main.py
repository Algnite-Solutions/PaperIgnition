import sys
import os
import asyncio
sys.path.append(os.path.dirname(__file__))
import utils
import paper_pull
from generate_blog import run_batch_generation
#from backend.index_service import index_papers
import requests
import os
from backend.app.db_utils import load_config as load_backend_config
from AIgnite.data.docset import DocSetList, DocSet
import httpx
import sys
import yaml

async def blog_generation_for_storage(index_api_url: str, backend_api_url: str, all_papers):
    """
    Generate blog digests for existing users based on their interests.
    This function is a placeholder and should be replaced with the actual implementation.
    """
    username = "BlogBot@gmail.com"
    
    seen_paper_ids = set()
    unique_papers = []
    for paper in all_papers:
        if paper.doc_id not in seen_paper_ids:
            seen_paper_ids.add(paper.doc_id)
            unique_papers.append(paper)
    
    print(f"去重前论文数量: {len(all_papers)}")
    print(f"去重后论文数量: {len(unique_papers)}")
    
    # 使用去重后的论文列表
    all_papers = unique_papers

    # 4. Generate blog digests for users in batches
    print("Generating blog digests for users...")
    
    batch_size = 50
    total_papers = len(all_papers)
    processed_count = 0
    
    for batch_start in range(0, total_papers, batch_size):
        batch_end = min(batch_start + batch_size, total_papers)
        batch_papers = all_papers[batch_start:batch_end]
        
        print(f"🔄 Processing batch {batch_start//batch_size + 1}: papers {batch_start+1}-{batch_end} of {total_papers}")
        
        try:
            # 生成当前批次的博客
            await run_batch_generation(batch_papers)
            print(f"✅ Blog generation completed for batch {batch_start//batch_size + 1}")
            
            # 立即处理并保存当前批次的论文
            paper_infos = []
            for paper in batch_papers:
                try:
                    # 使用绝对路径，基于当前脚本所在目录
                    blog_path = os.path.join("/data3/guofang/peirongcan/PaperIgnition/orchestrator/blogs", f"{paper.doc_id}.md")
                    with open(blog_path, encoding="utf-8") as file:
                        blog = file.read()
                except FileNotFoundError:
                    blog = None
                

                paper_url = f"https://arxiv.org/abs/{paper.doc_id}"
                
                paper_infos.append({
                    "paper_id": paper.doc_id,
                    "title": paper.title,
                    "authors": ", ".join(paper.authors),
                    "abstract": paper.abstract,
                    "url": paper_url,
                    "content": paper.abstract,
                    "blog": blog,
                    "recommendation_reason": f"This is a dummy recommendation reason for paper {paper.title}",
                    "relevance_score": 0.5
                })
            
            # 保存当前批次
            print(f"💾 Saving batch {batch_start//batch_size + 1} ({len(paper_infos)} papers)...")
            utils.save_recommendations(username, paper_infos, backend_api_url)
            
            processed_count += len(batch_papers)
            print(f"📊 Progress: {processed_count}/{total_papers} papers processed")
            
        except Exception as e:
            print(f"❌ Blog generation failed for batch {batch_start//batch_size + 1}: {e}")
            continue
    
    print(f"🎉 All batches completed! Total processed: {processed_count}/{total_papers}")


def main():
    config_path = os.path.join(os.path.dirname(__file__), "../backend/configs/app_config.yaml")
    config = load_backend_config(config_path)
    index_api_url = config['INDEX_SERVICE']["host"]
    backend_api_url = config['APP_SERVICE']["host"]
    print("backend：",backend_api_url)
    print("index：",index_api_url)


    #print("Starting daily paper fetch...")
    papers = utils.fetch_daily_papers(index_api_url, config)
    #print("Daily paper fetch complete.")

    print("Starting blog generation for existing users...")
    asyncio.run(blog_generation_for_storage(index_api_url, backend_api_url, papers))
    print("Blog generation for existing users complete.")
    
if __name__ == "__main__":
    main()