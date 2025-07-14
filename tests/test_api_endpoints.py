import httpx
import asyncio
import yaml
import tempfile
import os
from pathlib import Path
from typing import Dict, Any
from AIgnite.data.docset import DocSet, TextChunk, ChunkType, DocSetList
from backend.configs.config import load_index_config

config = load_index_config()

BASE_URL = config['host']

# Create temporary directory for test files
TEMP_DIR = tempfile.mkdtemp()

# Update vector_db path in config to be under TEMP_DIR
config['vector_db']['db_path'] = os.path.join(TEMP_DIR, config['vector_db']['db_path'])

# Create necessary directories
print(config['vector_db']['db_path'])
os.makedirs(os.path.dirname(config['vector_db']['db_path']), exist_ok=True)

# Create test PDF files
def setup_test_files():
    """Create test PDF files."""
    test_pdfs = {}
    for i in range(5):
        pdf_path = os.path.join(TEMP_DIR, f"test_paper_{i}.pdf")
        with open(pdf_path, 'wb') as f:
            f.write(f"Test PDF content for paper {i}".encode())
        test_pdfs[f"paper_{i+1:03d}"] = pdf_path  # Changed key format to match paper_id
    return test_pdfs

# Create test files
test_pdfs = setup_test_files()

async def check_server_running(url: str, timeout: float = 5.0) -> bool:
    """Check if the API server is running and accessible."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{url}/health", timeout=timeout)
            return response.status_code == 200 and response.json()["status"] == "healthy"
    except Exception as e:
        print(f"\n❌ Error: API server not accessible at {url}")
        print(f"Please ensure the server is running with:")
        print("    cd PaperIgnition")
        print(f"    uvicorn backend.index_service.main:app --host 0.0.0.0 --port {url.split(':')[-1]}")
        print(f"\nError details: {str(e)}")
        return False

# Create sample papers using proper DocSet models
docsets = []
for i in range(5):
    paper_id = f"paper_{i+1:03d}"
    text_chunks = []
    if i == 0:
        text_chunks = [
            TextChunk(id="t1", type=ChunkType.TEXT, text="This paper explores API design with FastAPI."),
            TextChunk(id="t2", type=ChunkType.TEXT, text="We demonstrate LLM-based retrieval.")
        ]
        title = "Example Paper on FastAPI"
        abstract = "This is a demo abstract."
        authors = ["Alice", "Bob"]
        categories = ["cs.AI"]
        published_date = "2024-12-01"
    elif i == 1:
        text_chunks = [
            TextChunk(id="t1", type=ChunkType.TEXT, text="Transformers improve contextual understanding in NLP."),
            TextChunk(id="t2", type=ChunkType.TEXT, text="This paper benchmarks BERT and GPT models.")
        ]
        title = "Transformer Models for NLP"
        abstract = "Explores transformer architecture for language tasks."
        authors = ["Carol", "Dave"]
        categories = ["cs.CL"]
        published_date = "2023-10-15"
    elif i == 2:
        text_chunks = [
            TextChunk(id="t1", type=ChunkType.TEXT, text="Deep learning approaches revolutionize computer vision tasks."),
            TextChunk(id="t2", type=ChunkType.TEXT, text="We analyze vision transformers and CNN architectures.")
        ]
        title = "Deep Learning in Computer Vision: A Survey"
        abstract = "This paper surveys deep learning approaches in computer vision, focusing on vision transformers and modern architectures like attention mechanisms for image recognition tasks."
        authors = ["Eve", "Frank"]
        categories = ["cs.CV"]
        published_date = "2023-08-20"
    elif i == 3:
        text_chunks = [
            TextChunk(id="t1", type=ChunkType.TEXT, text="Reinforcement learning enables adaptive motor control."),
            TextChunk(id="t2", type=ChunkType.TEXT, text="Policies are trained using PPO and DDPG.")
        ]
        title = "Reinforcement Learning for Robotics"
        abstract = "Investigates RL for controlling robotic arms."
        authors = ["Grace", "Hank"]
        categories = ["cs.AI", "cs.LG"]
        published_date = "2022-07-01"
    else:
        text_chunks = [
            TextChunk(id="t1", type=ChunkType.TEXT, text="Bayesian optimization efficiently searches parameter space."),
            TextChunk(id="t2", type=ChunkType.TEXT, text="Applications include AutoML and black-box optimization.")
        ]
        title = "Bayesian Optimization in Machine Learning"
        abstract = "Reviews BO methods for hyperparameter tuning."
        authors = ["Ivy", "Jack"]
        categories = ["stat.ML"]
        published_date = "2023-05-01"
    
    docset = DocSet(
        doc_id=paper_id,
        title=title,
        abstract=abstract,
        authors=authors,
        categories=categories,
        published_date=published_date,
        pdf_path=test_pdfs[paper_id],  # Use actual temporary file path
        HTML_path=None,
        text_chunks=text_chunks,
        figure_chunks=[],
        table_chunks=[],
        metadata={}
    )
    docsets.append(docset)

# Create DocSetList instance
sample_papers = DocSetList(docsets=docsets)

async def test_connection_health():
    """Test the API connection health check endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data["status"] == "healthy", "Unexpected health check response"
        assert data["indexer_ready"] == True, "Indexer not ready"
        print("✅ Connection health check passed")

async def test_index_2_papers():
    """Index the first 2 papers only."""
    async with httpx.AsyncClient() as client:
        data = DocSetList(docsets=docsets[:2]).dict()
        response = await client.post(
            f"{BASE_URL}/index_papers/",
            json=data,
            timeout=30.0
        )
        assert response.status_code == 200, f"Indexing first 2 papers failed: {response.text}"
        data = response.json()
        assert "message" in data, "Response missing 'message' field"
        assert "2 papers indexed successfully" in data["message"]
        print("✅ Indexed first 2 papers")

async def test_get_metadata_2():
    """Test metadata retrieval after indexing 2 papers."""
    async with httpx.AsyncClient() as client:
        for i in range(2):
            pid = f"paper_{i+1:03d}"
            # returns string of metadata
            response = await client.get(f"{BASE_URL}/get_metadata/{pid}")
            assert response.status_code == 200, f"Metadata fetch failed for {pid}: {response.text}"
        for i in range(2, 5):
            pid = f"paper_{i+1:03d}"
            response = await client.get(f"{BASE_URL}/get_metadata/{pid}")
            assert response.status_code == 404, f"Expected 404 for {pid}, got {response.status_code}"
        print("✅ Metadata check after 2 papers indexed")

async def test_indexer_reload_and_incremental_indexing():
    """Re-init indexer (without recreating DB), index last 3 papers."""
    async with httpx.AsyncClient() as client:
        data = DocSetList(docsets=docsets[2:]).dict()
        response = await client.post(
            f"{BASE_URL}/index_papers/",
            json=data,
            timeout=30.0
        )
        assert response.status_code == 200, f"Indexing last 3 papers failed: {response.text}"
        data = response.json()
        assert "message" in data, "Response missing 'message' field"
        assert "3 papers indexed successfully" in data["message"]
        print("✅ Indexed last 3 papers with new indexer")

async def test_get_metadata_all():
    """Test metadata retrieval after all 5 papers are indexed."""
    async with httpx.AsyncClient() as client:
        for i in range(5):
            pid = f"paper_{i+1:03d}"
            response = await client.get(f"{BASE_URL}/get_metadata/{pid}")
            assert response.status_code == 200, f"Metadata fetch failed for {pid}: {response.text}"
        print("✅ Metadata check after all papers indexed")

async def test_find_similar_2():
    async with httpx.AsyncClient() as client:
        # 1. Vector search: should match one of the first two papers
        vector_query = {"query": "API design", "top_k": 5, "similarity_cutoff": 0.5, "strategy_type": "vector"}
        response = await client.post(f"{BASE_URL}/find_similar/", json=vector_query, timeout=10.0)
        assert response.status_code == 200, "Vector search failed"
        results = response.json()
        assert len(results) <= 2, f"Expected at most 2 results, got {len(results)} for vector search"
        print(f"✅ [2 papers] Vector search: Found {len(results)} results for query '{vector_query['query']}'")

        # 2. TF-IDF search: should match one of the first two papers
        tfidf_query = {"query": "transformer models", "top_k": 5, "similarity_cutoff": 0.0, "strategy_type": "tf-idf"}
        response = await client.post(f"{BASE_URL}/find_similar/", json=tfidf_query, timeout=10.0)
        assert response.status_code == 200, "TF-IDF search failed"
        results = response.json()
        assert len(results) <= 2, f"Expected at most 2 results, got {len(results)} for tf-idf search"
        print(f"✅ [2 papers] TF-IDF search: Found {len(results)} results for query '{tfidf_query['query']}'")

        # 3. No result case: query that should not match any paper
        no_result_query = {"query": "quantum entanglement", "top_k": 5, "similarity_cutoff": 0.5, "strategy_type": "vector"}
        response = await client.post(f"{BASE_URL}/find_similar/", json=no_result_query, timeout=10.0)
        assert response.status_code == 200, "No-result search failed"
        results = response.json()
        assert len(results) == 0, f"Expected 0 results, got {len(results)} for no-result search"
        print(f"✅ [2 papers] No-result search: Found {len(results)} results for query '{no_result_query['query']}'")

async def test_find_similar_all():
    async with httpx.AsyncClient() as client:
        # 1. Vector search: should match all 5 papers
        vector_query = {"query": "deep learning", "top_k": 5, "similarity_cutoff": 0.5, "strategy_type": "vector"}
        response = await client.post(f"{BASE_URL}/find_similar/", json=vector_query, timeout=10.0)
        assert response.status_code == 200, "Vector search failed"
        results = response.json()
        assert len(results) >0, f"Expected more than  0  results, got {len(results)} for vector search"
        print(f"✅ [all papers] Vector search: Found {len(results)} results for query '{vector_query['query']}'")

        # 2. TF-IDF search: should match all 5 papers
        tfidf_query = {"query": "controlling robotic", "top_k": 5, "similarity_cutoff": 0.0, "strategy_type": "tf-idf"}
        response = await client.post(f"{BASE_URL}/find_similar/", json=tfidf_query, timeout=10.0)
        assert response.status_code == 200, "TF-IDF search failed"
        results = response.json()
        assert len(results) > 0, f"Expected more than 0 results, got {len(results)} for tf-idf search"
        print(f"✅ [all papers] TF-IDF search: Found {len(results)} results for query '{tfidf_query['query']}'")

        # 3. No result case: query that should not match any paper
        no_result_query = {"query": "quantum entanglement", "top_k": 5, "similarity_cutoff": 0.5, "strategy_type": "vector"}
        response = await client.post(f"{BASE_URL}/find_similar/", json=no_result_query, timeout=10.0)
        assert response.status_code == 200, "No-result search failed"
        results = response.json()
        assert len(results) == 0, f"Expected 0 results, got {len(results)} for no-result search"
        print(f"✅ [all papers] No-result search: Found {len(results)} results for query '{no_result_query['query']}'")

async def test_error_cases():
    """Test error handling."""
    async with httpx.AsyncClient() as client:
        # Test non-existent document
        response = await client.get(f"{BASE_URL}/get_metadata/nonexistent_id")
        assert response.status_code == 404, "Expected 404 for non-existent document"
        
        # Test invalid similarity search params
        response = await client.post(
            f"{BASE_URL}/find_similar/",
            json={"query": "", "top_k": -1, "similarity_cutoff": 2.0}
        )
        assert response.status_code == 422, "Expected 422 for invalid parameters"
        
        '''
        # Test invalid database initialization params
        invalid_config = {}  # Empty config should fail validation
        response = await client.post(
            f"{BASE_URL}/init_database",
            json={"config": invalid_config}
        )
        assert response.status_code == 422, "Expected 422 for invalid config"
        '''
        print("✅ Error cases handled correctly")

async def run_tests():
    """Run all tests in sequence."""
    print(f"\nRunning tests against {BASE_URL}")
    print("=" * 50)
    
    try:
        # Check if server is running first
        if not await check_server_running(BASE_URL):
            return
        
        # Basic health and functionality tests
        await test_connection_health()
        await test_index_2_papers()
        await test_get_metadata_2()
        await test_find_similar_2()
        await test_indexer_reload_and_incremental_indexing()
        await test_get_metadata_all()
        await test_find_similar_all()
        
        # Error case tests
        await test_error_cases()
        
        print("\n✅ All tests passed successfully!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {str(e)}")
    except Exception as e:
        print(f"\n❌ Error during tests: {str(e)}")
    finally:
        # Clean up temporary files
        import shutil
        shutil.rmtree(TEMP_DIR, ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(run_tests()) 