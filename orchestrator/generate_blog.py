from AIgnite.generation import BlogGenerator
from backend.index_service import index_papers, find_similar_papers
from backend.user_service import get_all_users, get_user_interest

generator = BlogGenerator()

def run_batch_generation():
    users = get_all_users()
    for user in users:
        interests = get_user_interest(user)
        papers = find_similar_papers(interests)
        blog = generator.generate_digest(papers)
        print(f"Blog for {user['id']}:\n{blog}\n")