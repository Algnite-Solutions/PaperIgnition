import requests
from AIgnite.generation.generator import GeminiBlogGenerator
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

generator = GeminiBlogGenerator(data_path="../imgs/", output_path="./orchestrator/blogs/")

def run_batch_generation():
    """discarded."""
    users = get_all_users()
    for user in users:
        #interests = get_user_interest(user)
        #papers = find_similar(interests, top_k=5, cutoff=0.0)
        blog = generator.generate_digest(papers)
        print(f"Blog for {user['username']}:\n{blog}\n")

def run_dummy_blog_generation(papers):
    blog = generator.generate_digest(papers)


