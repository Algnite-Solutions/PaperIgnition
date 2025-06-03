from AIgnite.generation.generator import GeminiBlogGenerator
#from backend.index_service import index_papers, find_similar
#from backend.user_service import get_all_users, get_user_interest

# @ch, replace it with backend.user_service
def get_all_users():
    # Placeholder for user fetching logic
    return [
        {"id": "user1", "interests": "long context large language models, KV Cache"},
        {"id": "user2", "interests": "vision language models, image generation"},
        {"id": "user3", "interests": "reinforcement learning, multi-agent systems"},
        # Add more users as needed
    ]

def get_user_interest(user):
    # Placeholder for user interest fetching logic
    return user["interests"]

generator = GeminiBlogGenerator(data_path="../imgs/", output_path="./orchestrator/blogs/")

def run_batch_generation():
    users = get_all_users()
    for user in users:
        #interests = get_user_interest(user)
        #papers = find_similar(interests, top_k=5, cutoff=0.0)
        blog = generator.generate_digest(papers)
        print(f"Blog for {user['id']}:\n{blog}\n")

def run_dummy_blog_generation(papers):
    blog = generator.generate_digest(papers)