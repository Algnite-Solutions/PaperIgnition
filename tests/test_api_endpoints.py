import httpx
import asyncio
import yaml
import tempfile
import os
from pathlib import Path
from typing import Dict, Any
from AIgnite.data.docset import DocSet, TextChunk, ChunkType, DocSetList
from backend.index_service.config import load_config

# Load config from tests/config.yaml
config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
config = load_config(config_path)

BASE_URL = config['index_api_url']

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

async def initialize_database(recreate_databases: bool = True) -> bool:
    """Initialize the database and indexer.
    
    Args:
        recreate_databases: If True, drops and recreates all databases.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Print the request payload for debugging
            request_data = {"config": config}
            print(f"\nSending request with payload: {request_data}")
            
            response = await client.post(
                f"{BASE_URL}/init_database",
                json=request_data,
                params={"recreate_databases": recreate_databases}
            )
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            
            assert response.status_code == 200, f"Database initialization failed: {response.text}"
            data = response.json()
            action = "recreated" if recreate_databases else "created"
            assert data["message"] == f"Database {action} and indexer creation successful"
            print(f"✅ Database {action} successfully")
            return True
    except Exception as e:
        print(f"\n❌ Error initializing database: {str(e)}")
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

async def test_database_initialization():
    """Test database initialization with different settings."""
    # Test initialization with database recreation (default)
    assert await initialize_database(recreate_databases=True), "Failed to recreate database"
    await asyncio.sleep(1)  # Give time for initialization to complete
    
    # Test initialization without database recreation
    assert await initialize_database(recreate_databases=False), "Failed to create database without recreation"
    await asyncio.sleep(1)  # Give time for initialization to complete
    
    print("✅ Database initialization tests passed")

async def test_index_papers():
    """Test paper indexing endpoint."""
    async with httpx.AsyncClient() as client:
        # Convert DocSetList to dict and ensure HTML_path is included
        data = sample_papers.dict()
        response = await client.post(
            f"{BASE_URL}/index_papers/",
            json=data,
            timeout=30.0
        )
        assert response.status_code == 200, f"Indexing failed: {response.text}"
        data = response.json()
        assert "message" in data, "Response missing 'message' field"
        assert "5 papers indexed successfully" in data["message"]
        print("✅ Papers indexed successfully")

async def test_get_metadata():
    """Test metadata retrieval endpoint."""
    async with httpx.AsyncClient() as client:
        # Test first paper
        response = await client.get(f"{BASE_URL}/get_metadata/paper_001")
        assert response.status_code == 200, f"Metadata fetch failed: {response.text}"
        data = response.json()
        assert data["title"] == "Example Paper on FastAPI", "Incorrect paper title"
        assert data["authors"] == ["Alice", "Bob"], "Incorrect authors"
        
        # Test last paper
        response = await client.get(f"{BASE_URL}/get_metadata/paper_005")
        assert response.status_code == 200, f"Metadata fetch failed: {response.text}"
        data = response.json()
        assert data["title"] == "Bayesian Optimization in Machine Learning", "Incorrect paper title"
        print("✅ Metadata retrieved successfully")

async def test_find_similar():
    """Test similarity search endpoint with different search strategies."""
    async with httpx.AsyncClient() as client:
        # Test vector search
        vector_query = {
            "query": "transformer models and NLP",
            "top_k": 3,
            "similarity_cutoff": 0.8,
            "strategy_type": "vector"
        }
        response = await client.post(
            f"{BASE_URL}/find_similar/",
            json=vector_query,
            timeout=10.0
        )
        assert response.status_code == 200, "Vector search failed"
        vector_results = response.json()
        assert isinstance(vector_results, list), "Expected list of results for vector search"
        assert len(vector_results) > 0, "Expected at least one similar paper for vector search"
        
        # Verify vector search results
        for result in vector_results:
            assert result["search_method"] == "vector"
            assert "transformer" in result["title"].lower() or "nlp" in result["title"].lower() or \
                   "transformer" in result["abstract"].lower() or "nlp" in result["abstract"].lower(), \
                   "Vector search results should contain relevant transformer/NLP papers"
        print(f"✅ Vector search: Found {len(vector_results)} relevant papers")
        
        # Test TF-IDF search
        tfidf_query = {
            "query": "deep learning in computer vision",
            "top_k": 3,
            "similarity_cutoff": 1.0,
            "strategy_type": "tf-idf"
        }
        response = await client.post(
            f"{BASE_URL}/find_similar/",
            json=tfidf_query,
            timeout=10.0
        )
        assert response.status_code == 200, "TF-IDF search failed"
        tfidf_results = response.json()
        
        assert isinstance(tfidf_results, list), "Expected list of results for TF-IDF search"
        assert len(tfidf_results) > 0, "Expected at least one similar paper for TF-IDF search"
        
        # Verify TF-IDF search results
        
        for result in tfidf_results:
            assert result["search_method"] == "tf-idf"
            assert "vision" in result["title"].lower() or "vision" in result["abstract"].lower() or \
                   "deep learning" in result["title"].lower() or "deep learning" in result["abstract"].lower(), \
                   "TF-IDF search results should contain relevant computer vision papers"
            assert "matched_text" in result, "TF-IDF results should include matched text"
        print(f"✅ TF-IDF search: Found {len(tfidf_results)} relevant papers")
        
        # Test hybrid search
        hybrid_query = {
            "query": "attention mechanisms in neural networks",
            "top_k": 3,
            "similarity_cutoff": 0.5,
            "strategy_type": "hybrid"
        }
        response = await client.post(
            f"{BASE_URL}/find_similar/",
            json=hybrid_query,
            timeout=10.0
        )
        assert response.status_code == 200, "Hybrid search failed"
        hybrid_results = response.json()
        assert isinstance(hybrid_results, list), "Expected list of results for hybrid search"
        assert len(hybrid_results) > 0, "Expected at least one similar paper for hybrid search"
        
        # Verify hybrid search results
        print(hybrid_results)
        for result in hybrid_results:
            assert result["search_method"] == "hybrid"
            assert "attention" in result["title"].lower() or "attention" in result["abstract"].lower() or \
                   "neural" in result["title"].lower() or "neural" in result["abstract"].lower(), \
                   "Hybrid search results should contain relevant attention/neural network papers"
            # Hybrid search should combine features of both vector and TF-IDF
            assert "similarity_score" in result, "Hybrid results should include similarity score"
            assert "matched_text" in result, "Hybrid results should include matched text"
        print(f"✅ Hybrid search: Found {len(hybrid_results)} relevant papers")
        
        # Verify results are different for each strategy
        vector_ids = {r["doc_id"] for r in vector_results}
        tfidf_ids = {r["doc_id"] for r in tfidf_results}
        hybrid_ids = {r["doc_id"] for r in hybrid_results}
        
        # There should be some variation in results between strategies
        assert len(vector_ids.intersection(tfidf_ids)) < len(vector_ids), \
            "Vector and TF-IDF search should return some different results"
        
        # Print detailed results for manual verification
        print("\nDetailed Results:")
        print("\nTop Vector Search Result:")
        print(f"Title: {vector_results[0]['title']}")
        print(f"Score: {vector_results[0]['similarity_score']:.3f}")
        
        print("\nTop TF-IDF Search Result:")
        print(f"Title: {tfidf_results[0]['title']}")
        print(f"Score: {tfidf_results[0]['similarity_score']:.3f}")
        print(f"Matched Text: {tfidf_results[0]['matched_text'][:100]}...")
        
        print("\nTop Hybrid Search Result:")
        print(f"Title: {hybrid_results[0]['title']}")
        print(f"Score: {hybrid_results[0]['similarity_score']:.3f}")
        print(f"Matched Text: {hybrid_results[0]['matched_text'][:100]}...")

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
            
        # Test database initialization scenarios
        print("\nTesting database initialization...")
        await test_database_initialization()
        
        # Basic health and functionality tests
        await test_connection_health()
        await test_index_papers()
        await asyncio.sleep(1)  # Give indexing time to complete
        await test_get_metadata()
        await test_find_similar()
        
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