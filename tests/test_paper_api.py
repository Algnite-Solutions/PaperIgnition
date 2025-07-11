import requests

BASE_URL = "http://localhost:8000/papers"

def test_get_papers_by_ids():
    # 假设有这些paper_id
    paper_ids = ["2023.24680", "2023.12345"]
    response = requests.post(f"{BASE_URL}/by_ids", json=paper_ids)
    print("get_papers_by_ids 返回：")
    print(response.status_code)
    print(response.json())

def test_get_paper_markdown_content(paper_id):
    response = requests.get(f"{BASE_URL}/paper_content/{paper_id}")
    print(f"get_paper_markdown_content({paper_id}) 返回：")
    print(response.status_code)
    print(response.json())

if __name__ == "__main__":
    test_get_papers_by_ids()
    test_get_paper_markdown_content("2023.24680")