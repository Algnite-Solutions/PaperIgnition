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
from generate_blog import run_batch_generation, run_batch_generation_abs, run_batch_generation_title

def get_user_interest(username: str,backend_api_url):
        response = requests.get(f"{backend_api_url}/api/users/by_email/{username}")
        response.raise_for_status()
        user_data = response.json()
        return user_data.get("interests_description", [])

def get_all_users(backend_api_url):
    """
    获取所有用户信息，返回用户字典列表（含 username, interests_description 等）
    """
    resp = requests.get(f"{backend_api_url}/api/users/all", timeout=100.0)
    resp.raise_for_status()
    return resp.json()

async def blog_generation_for_existing_user(index_api_url: str, backend_api_url: str):
    """
    Generate blog digests for existing users based on their interests.
    This function is a placeholder and should be replaced with the actual implementation.
    """
    all_users = get_all_users(backend_api_url)
    print(f"✅ 共获取到 {len(all_users)} 个用户")
    print([user.get("username") for user in all_users])
    for user in all_users:
        username = user.get("username")
        if username != "test@tongji.edu.cn":
            continue
        interests = get_user_interest(username,backend_api_url)
        print(f"\n=== 用户: {username}，兴趣: {interests} ===")
        if not interests:
            print(f"用户 {username} 无兴趣关键词，跳过推荐。")
            continue
        
        # 获取用户已有的论文推荐，用于过滤
        try:
            import requests
            user_papers_response = requests.get(f"{backend_api_url}/api/papers/recommendations/{username}")
            if user_papers_response.status_code == 200:
                user_existing_papers = user_papers_response.json()
                existing_paper_ids = [paper["id"] for paper in user_existing_papers if paper.get("id")]
                print(f"用户 {username} 已有 {len(existing_paper_ids)} 篇论文推荐")
                print(f"已有论文ID: {existing_paper_ids[:5]}...")  # 只显示前5个
            else:
                existing_paper_ids = []
                print(f"获取用户 {username} 已有论文失败，状态码: {user_papers_response.status_code}")
        except Exception as e:
            print(f"获取用户 {username} 已有论文时出错: {e}")
            existing_paper_ids = []
        
        all_papers = []
        '''for query in interests:
            print(f"[TF-IDF] 用户 {username} 兴趣: {query}")
            papers = search_papers_via_api(index_api_url, query, 'tf-idf', 0.1)
            all_papers.extend(papers)'''
        
        for query in interests:
            print(f"[VECTOR] 用户 {username} 兴趣: {query}")
            
            # 构建过滤器，排除用户已有的论文ID
            if existing_paper_ids:
                filter_params = {
                    "exclude": {
                        "doc_ids": existing_paper_ids
                    }
                }
                print(f"应用过滤器，排除 {len(existing_paper_ids)} 个已有论文ID")
                papers = utils.search_papers_via_api(index_api_url, "llm", 'tf-idf', 0.1, filter_params)
            else:
                papers = utils.search_papers_via_api(index_api_url, query, 'vector', 0.1)
            
            all_papers.extend(papers)

        # 添加去重逻辑：确保论文ID不重复
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

        # 4. Generate blog digests for users
        print("Generating blog digests for users...")
        if all_papers:
            #run_batch_generation(all_papers)
            blog = await run_batch_generation(all_papers)
            print("Digest generation complete.")

            blog_abs = await run_batch_generation_abs(all_papers)
            blog_title = await run_batch_generation_title(all_papers)
            paper_infos = []
            for i, paper in enumerate(all_papers):
                try:
                    # 使用绝对路径，基于当前脚本所在目录
                    blog_path = os.path.join(os.path.dirname(__file__), "blogs", f"{paper.doc_id}.md")
                    with open(blog_path, encoding="utf-8") as file:
                        blog = file.read()
                except FileNotFoundError:
                    blog = None  # 或者其他处理方式
                
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
            utils.save_recommendations(username, paper_infos, backend_api_url)
        else:
            print("没有找到相关论文，跳过博客生成和推荐保存")
            continue

def main():
    config_path = os.path.join(os.path.dirname(__file__), "../backend/configs/app_config.yaml")
    config = load_backend_config(config_path)
    index_api_url = config['INDEX_SERVICE']["host"]
    backend_api_url = config['APP_SERVICE']["host"]
    print("backend：",backend_api_url)
    print("index：",index_api_url)

    print("Starting blog generation for existing users...")
    asyncio.run(blog_generation_for_existing_user(index_api_url, backend_api_url))
    print("Blog generation for existing users complete.")
    
if __name__ == "__main__":
    main()