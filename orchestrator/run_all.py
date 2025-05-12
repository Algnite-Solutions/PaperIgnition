from orchestrator import paper_pull, generate_blog
from backend.index_service import index_papers

def main():
    print("Fetching today's arXiv papers...")
    papers = paper_pull.fetch_daily_papers()
    print(f"Fetched {len(papers)} papers.")

    print("Indexing papers via index service...")
    index_papers(papers)
    print("Papers indexed.")

    print("Generating blog digests for users...")
    generate_blog.run_batch_generation()
    print("Digest generation complete.")

if __name__ == "__main__":
    main()