import requests
from AIgnite.generation.generator import GeminiBlogGenerator, AsyncvLLMGenerator
from AIgnite.data.docset import DocSet
import os
import json
import yaml
import asyncio
#from backend.index_service import index_papers, find_similar
#from backend.user_service import get_all_users, get_user_interest

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
    response = requests.get("http://localhost:8000/api/users/all") # Assuming your backend runs on localhost:8000
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
    response = requests.get(f"http://localhost:8000/api/users/by_email/{username}") 
    response.raise_for_status() # Raises an exception for bad status codes (e.g., 404)
    user_data = response.json()
    return user_data.get("interests_description", [])


def run_Gemini_blog_generation(papers):
    generator = GeminiBlogGenerator(
        data_path="../orchestrator/imgs/", 
        output_path="/data3/guofang/peirongcan/PaperIgnition/blogByGemini")
    blog = generator.generate_digest(papers)



async def run_batch_generation(papers):
    generator = AsyncvLLMGenerator(
        model_name="Qwen/Qwen3-32B", 
        api_base="http://localhost:5666/v1",
        data_path="../orchestrator/imgs/", 
        output_path="/data3/guofang/peirongcan/PaperIgnition/blogByQwen")
    
    config_path = os.path.join(os.path.dirname(__file__), "./config/prompt.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    system_prompt = config['prompts']['blog_generation']['system_prompt']
    user_prompt_template = config['prompts']['blog_generation']['user_prompt_template']

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
            arxiv_id=paper.doc_id
        )
        if len(paper.text_chunks) > 10000:
            prompt = prompt[:10000]
        prompts.append(prompt)
    try:
        blog = await generator.batch_generate(prompts=prompts, max_tokens=2048, papers=papers)
        return blog
    except Exception as e:
        print(f"Error: {e}")
        return None

async def main():
    papers = []
    for file in os.listdir("/data3/guofang/peirongcan/PaperIgnition/orchestrator/jsons"):
        if len(papers) >= 10:
            break
        with open(f"/data3/guofang/peirongcan/PaperIgnition/orchestrator/jsons/{file}", "r") as f:
            data = json.load(f)
            papers.append(DocSet(**data))
            print(file)
    
    blog = await run_batch_generation(papers)
    #blog = run_Gemini_blog_generation(papers)
    #print("Blog generation completed:", blog)

if __name__ == "__main__":
    asyncio.run(main())