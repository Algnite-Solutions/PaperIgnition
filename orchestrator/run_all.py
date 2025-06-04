import paper_pull
#import generate_blog
#from backend.index_service import index_papers


def main():
    print("Fetching today's arXiv papers...")
    papers = paper_pull.fetch_daily_papers()
    #papers = paper_pull.dummy_paper_fetch("orchestrator/arxiv_papers.txt")
    print(f"Fetched {len(papers)} papers.")

    #print("Indexing papers via index service...")
    #index_papers(papers[:10])
    #print("Papers indexed.")

    #print("Generating blog digests for users...")
    #generate_blog.run_dummy_blog_generation(papers)
    #print("Digest generation complete.")

if __name__ == "__main__":
    main()