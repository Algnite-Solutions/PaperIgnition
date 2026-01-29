import requests
from AIgnite.generation.generator import GeminiBlogGenerator_default, GeminiBlogGenerator_recommend, AsyncvLLMGenerator
from AIgnite.data.docset import DocSet
import os
import json
import yaml
import asyncio
from typing import Optional
#from backend.index_service import index_papers, find_similar
#from backend.user_service import get_all_users, get_user_interest

# Import storage utilities
from storage_util import LocalStorageManager, create_local_storage_manager

# 加载配置文件
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "../backend/configs/app_config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

# @ch, replace it with backend.user_service
"""
to do:
以下两个接口缺少一个安全验证机制
"""
def get_all_users():
    """
        获取所有用户信息（username 和 interests_description）,返回json，示例如下
        [
            {
                'username': '3220102841@zju.edu.cn', 
                'interests_description': ['大型语言模型', '图神经网络']
            },
            {
                'username': 'chtest@qq.com', 
                'interests_description': ['大型语言模型', '图神经网络']
            }
        ]
    """
    response = requests.get(f"{config['APP_SERVICE']['host']}/api/users/all")
    response.raise_for_status()  # Raises an exception for bad status codes
    users_data = response.json()
    
    # Transform the data to the desired format
    transformed_users = []
    for user in users_data:
        transformed_users.append({
            "username": user.get("username"),
            "interests_description": user.get("interests_description", [])
        })
    return transformed_users

def get_user_interest(username: str):
    """
        获取指定用户的研究兴趣（interests_description）,返回json，示例如下
        ['大型语言模型', '图神经网络']
    """
    # 实际上username和user_email保持一致
    response = requests.get(f"{config['APP_SERVICE']['host']}/api/users/by_email/{username}") 
    response.raise_for_status() # Raises an exception for bad status codes (e.g., 404)
    user_data = response.json()
    return user_data.get("interests_description", [])

# Use this
def run_Gemini_blog_generation_default(papers, output_path="./blogByGemini"):
    generator = GeminiBlogGenerator_default(
        data_path="./imgs/", 
        output_path=output_path)
    blog = generator.generate_digest(papers)

def run_Gemini_blog_generation_recommend(papers, output_path="./blogByGemini"):
    generator = GeminiBlogGenerator_recommend(
        data_path="./imgs/", 
        output_path=output_path)
    blog = generator.generate_digest(papers)


async def run_batch_generation(papers, output_path="./blogs"):
    generator = AsyncvLLMGenerator(
        model_name=config['BLOG_GENERATION']['model_name'], 
        api_base=config['BLOG_GENERATION']['api_base'],
        data_path=config['BLOG_GENERATION']['data_path'], 
        output_path=output_path)
    
    prompt_config_path = os.path.join(os.path.dirname(__file__), "./config/prompt.yaml")
    with open(prompt_config_path, "r") as f:
        prompt_config = yaml.safe_load(f)

    system_prompt = prompt_config['prompts']['blog_generation']['system_prompt']
    user_prompt_template = prompt_config['prompts']['blog_generation']['user_prompt_template']

    prompts = []
    for paper in papers:
        # 准备图片路径
        image_path = generator.data_path
        
        prompt = user_prompt_template.format(
            title=paper.title, 
            authors=paper.authors, 
            abstract=paper.abstract, 
            text_chunks=paper.text_chunks,
            image_path=image_path,
            arxiv_id=paper.doc_id,
            table_chunks=paper.table_chunks,
        )
        if len(paper.text_chunks) > 10000:
            prompt = prompt[:10000]
        prompts.append(prompt)
    try:
        blog = await generator.batch_generate(prompts=prompts, system_prompts=system_prompt, max_tokens=config['BLOG_GENERATION']['max_tokens'], papers=papers)
        return blog
    except Exception as e:
        print(f"Error: {e}")
        return None

async def run_batch_generation_abs(papers, storage_manager: Optional[LocalStorageManager] = None):
    """
    Generate blog abstracts for papers.
    
    Args:
        papers: List of DocSet objects
        storage_manager: Optional LocalStorageManager for reading blog files
    """
    generator = AsyncvLLMGenerator(
        model_name=config['BLOG_GENERATION']['model_name'], 
        api_base=config['BLOG_GENERATION']['api_base'],
        data_path=config['BLOG_GENERATION']['data_path'], 
        output_path=config['BLOG_GENERATION']['output_path'])
    
    prompt_config_path = os.path.join(os.path.dirname(__file__), "./config/prompt.yaml")
    with open(prompt_config_path, "r") as f:
        prompt_config = yaml.safe_load(f)

    system_prompt = prompt_config['prompts']['blog_generation_abs']['system_prompt']
    user_prompt_template = prompt_config['prompts']['blog_generation_abs']['user_prompt_template']

    prompts = []
    for paper in papers:  # 遍历 papers 而不是 blogs
        blog_content = None
        
        if storage_manager:
            # Use storage_manager to read blog
            blog_content = storage_manager.read_blog(paper.doc_id)
        else:
            # Fallback to direct file reading (legacy behavior)
            try:
                with open(f"./orchestrator/blogs/{paper.doc_id}.md", encoding="utf-8") as file:
                    blog_content = file.read()
            except FileNotFoundError:
                pass
        
        if blog_content is None:
            print(f"❌ Blog file not found for {paper.doc_id}")
            continue
        
        prompt = user_prompt_template.format(
            blog=blog_content
        )
        prompts.append(prompt)
    
    try:
        abs = await generator.batch_generate_not_save(prompts=prompts, system_prompts=system_prompt, max_tokens=config['BLOG_GENERATION']['max_tokens'], papers=papers)
        return abs
    except Exception as e:
        print(f"Error: {e}")
        return None


async def run_batch_generation_title(papers):
    generator = AsyncvLLMGenerator(
        model_name=config['BLOG_GENERATION']['model_name'], 
        api_base=config['BLOG_GENERATION']['api_base'],
        data_path=config['BLOG_GENERATION']['data_path'], 
        output_path=config['BLOG_GENERATION']['output_path'])
    
    prompt_config_path = os.path.join(os.path.dirname(__file__), "./config/prompt.yaml")
    with open(prompt_config_path, "r") as f:
        prompt_config = yaml.safe_load(f)

    system_prompt = prompt_config['prompts']['blog_generation_title']['system_prompt']
    user_prompt_template = prompt_config['prompts']['blog_generation_title']['user_prompt_template']

    prompts = []
    for paper in papers:  # 遍历 papers 而不是 blogs
        prompt = user_prompt_template.format(
            title=paper.title
        )
        prompts.append(prompt)
    
    try:
        titles = await generator.batch_generate_not_save(prompts=prompts, system_prompts=system_prompt, max_tokens=config['BLOG_GENERATION']['max_tokens'], papers=papers)
        return titles
    except Exception as e:
        print(f"Error: {e}")
        return None

async def main():
    # Create storage manager for main execution
    base_dir = os.path.dirname(__file__)
    storage_manager = create_local_storage_manager(base_dir)
    
    # Load papers using storage_manager
    papers = storage_manager.load_all_paper_docsets()[:2]  # Limit to 2 papers for testing
    
    if not papers:
        # Fallback to legacy method
        json_folder = config['PAPER_STORAGE']['json_folder'] or "/data3/guofang/peirongcan/PaperIgnition/orchestrator/jsons"
        for file in os.listdir(json_folder):
            if len(papers) >= 2:
                break
            with open(f"{json_folder}/{file}", "r") as f:
                data = json.load(f)
                papers.append(DocSet(**data))
                print(file)
    
    blog = await run_batch_generation(papers)
    
    #abs = await run_batch_generation_abs(papers, storage_manager=storage_manager)
    #print("摘要：",abs)
    #titles = await run_batch_generation_title(papers)
    #print("标题：",titles)
    #blog = run_Gemini_blog_generation(papers)
    #print("Blog generation completed:", blog)
    abs = "摘要"
    titles = "标题"

if __name__ == "__main__":
    asyncio.run(main())