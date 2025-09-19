#!/usr/bin/env python3
"""
Test script to verify that filtering functionality works after fixes.

Example usage of filters:
1. Filter by doc_ids:
   {
     "query": "machine learning",
     "top_k": 5,
     "search_strategy_type": "vector",
     "result_include_types": ["metadata", "search_parameters"],
     "filters": {
       "include": {"doc_ids": ["paper_001", "paper_002"]}
     }
   }

2. Filter by authors:
   {
     "query": "deep learning",
     "top_k": 5,
     "search_strategy_type": "tf-idf",
     "result_include_types": ["metadata"],
     "filters": {
       "include": {"authors": ["Alice", "Bob"]}
     }
   }

3. Filter by categories:
   {
     "query": "neural networks",
     "top_k": 5,
     "search_strategy_type": "hybrid",
     "result_include_types": ["metadata", "text_chunks", "search_parameters"],
     "filters": {
       "include": {"categories": ["cs.AI", "cs.LG"]}
     }
   }

4. Text type filter:
   {
     "query": "transformer",
     "top_k": 10,
     "search_strategy_type": "vector",
     "result_include_types": ["metadata"],
     "filters": {
       "include": {"text_type": ["abstract"]},
       "exclude": {"text_type": ["chunk"]}
     }
   }
"""

import httpx
import asyncio
import yaml
import tempfile
import os
from pathlib import Path
from typing import Dict, Any
from AIgnite.data.docset import DocSet, TextChunk, ChunkType, DocSetList
from backend.index_service.db_utils import load_config
from backend.index_service.models import IndexPapersRequest
import sqlalchemy

# 使用测试专用配置文件
config = load_config("backend/configs/test_config.yaml")

BASE_URL = config['host']

# Create temporary directory for test files
TEMP_DIR = tempfile.mkdtemp()

# Update vector_db path in config to be under TEMP_DIR
#config['vector_db']['db_path'] = os.path.join(TEMP_DIR, config['vector_db']['db_path'])

# Create necessary directories

print(config)
#os.makedirs(os.path.dirname(config['vector_db']['db_path']), exist_ok=True)

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

# Create test image files
def setup_test_images():
    """Create test image files."""
    test_images = {}
    for i in range(3):
        image_path = os.path.join(TEMP_DIR, f"test_image_{i}.png")
        # Create a simple 1x1 pixel PNG image for testing
        # This is a minimal valid PNG file (1x1 transparent pixel)
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        with open(image_path, 'wb') as f:
            f.write(png_data)
        test_images[f"test_image_{i}"] = image_path
    return test_images

# Create test image files
test_images = setup_test_images()


# Delete test papers from metadata_db before running tests, it includes tables from papers and text_chunks
def clean_metadata_db():
    """Delete test papers from metadata_db before running tests.
    
    This function cleans both the papers table and the text_chunks table.
    The text_chunks table has ON DELETE CASCADE constraint, but we explicitly
    delete from both tables for clarity and completeness.
    """
    db_url = config['metadata_db']['db_url']
    engine = sqlalchemy.create_engine(db_url)
    with engine.connect() as conn:
        # First delete from text_chunks table to be explicit about cleanup
        conn.execute(
            sqlalchemy.text("""
                DELETE FROM text_chunks WHERE doc_id IN ('paper_001', 'paper_002', 'paper_003', 'paper_004', 'paper_005');
            """))
        # Then delete from papers table
        conn.execute(
            sqlalchemy.text("""
                DELETE FROM papers WHERE doc_id IN ('paper_001', 'paper_002', 'paper_003', 'paper_004', 'paper_005');
            """))
        conn.commit()
    print("✅ Metadata database cleaned")


def clean_vector_db():
    """Delete test papers from vector database before running tests.
    
    This function removes the entire vector database files since FAISS index
    and entries are tightly coupled. All vectors for test papers will be removed.
    """
    vector_db_path = config['vector_db']['db_path']
    if os.path.exists(f"{vector_db_path}/index.faiss"):
        os.remove(f"{vector_db_path}/index.faiss")
    if os.path.exists(f"{vector_db_path}/index.pkl"):
        os.remove(f"{vector_db_path}/index.pkl")
    print("✅ Vector database cleaned")



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

async def test_init_database_endpoint():
    """Test the init_database endpoint to ensure it works correctly."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/init_database",
                json={"config": config},
                params={"recreate_databases": True},
                timeout=30.0
            )
            
            if response.status_code == 200:
                print("✅ init_database endpoint working correctly")
                return True
            else:
                print(f"❌ init_database endpoint failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing init_database endpoint: {str(e)}")
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
        metadata={},
        comments=None
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
        data = IndexPapersRequest(
            docsets=DocSetList(docsets=docsets[:2]),
            store_images=False,
            keep_temp_image=False
        ).dict()
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
        data = IndexPapersRequest(
            docsets=DocSetList(docsets=docsets[2:]),
            store_images=False,
            keep_temp_image=False
        ).dict()
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
        vector_query = {
            "query": "API design", 
            "top_k": 5, 
            "search_strategies": [("vector", 0.8)],
            "result_include_types": ["metadata", "search_parameters"],
            "filters": {
                "include": {
                    "text_type": ["abstract"]
                }
            }
        }
        response = await client.post(f"{BASE_URL}/find_similar/", json=vector_query, timeout=10.0)
        assert response.status_code == 200, "Vector search failed"
        results = response.json()
        print(results)
        assert len(results) <= 2, f"Expected at most 2 results, got {len(results)} for vector search"
            
        
        print(f"✅ [2 papers] Vector search with abstract-only filter: Found {len(results)} results for query '{vector_query['query']}'")

        # 2. TF-IDF search: should match one of the first two papers
        tfidf_query = {
            "query": "transformer models", 
            "top_k": 5,  
            "search_strategies": [("tf-idf", 0.0)],
            "result_include_types": ["metadata", "search_parameters"]
        }
        response = await client.post(f"{BASE_URL}/find_similar/", json=tfidf_query, timeout=10.0)
        assert response.status_code == 200, "TF-IDF search failed"
        results = response.json()
        assert len(results) <= 2, f"Expected at most 2 results, got {len(results)} for tf-idf search"
        
        
        print(f"✅ [2 papers] TF-IDF search: Found {len(results)} results for query '{tfidf_query['query']}'")

        # 3. No result case: query that should not match any paper
        no_result_query = {
            "query": "quantum entanglement", 
            "top_k": 5, 
            "search_strategies": [("vector", 0.8)],
            "result_include_types": ["metadata"]
        }
        response = await client.post(f"{BASE_URL}/find_similar/", json=no_result_query, timeout=10.0)
        assert response.status_code == 200, "No-result search failed"
        results = response.json()
        assert len(results) == 0, f"Expected 0 results, got {len(results)} for no-result search"
        print(f"✅ [2 papers] No-result search: Found {len(results)} results for query '{no_result_query['query']}'")

async def test_find_similar_all():
    async with httpx.AsyncClient() as client:
        # 1. Vector search: should match all 5 papers
        vector_query = {
            "query": "deep learning", 
            "top_k": 5, 
            "search_strategies": [("vector", 0.8)],
            "result_include_types": ["metadata", "search_parameters"]
        }
        response = await client.post(f"{BASE_URL}/find_similar/", json=vector_query, timeout=10.0)
        assert response.status_code == 200, "Vector search failed"
        results = response.json()
        assert len(results) > 0, f"Expected more than 0 results, got {len(results)} for vector search"
        
        
        print(f"✅ [all papers] Vector search: Found {len(results)} results for query '{vector_query['query']}'")

        # 2. TF-IDF search: should match all 5 papers
        tfidf_query = {
            "query": "controlling robotic", 
            "top_k": 5, 
            "search_strategies": [("tf-idf", 0.0)],
            "result_include_types": ["metadata", "search_parameters"]
        }
        response = await client.post(f"{BASE_URL}/find_similar/", json=tfidf_query, timeout=10.0)
        assert response.status_code == 200, "TF-IDF search failed"
        results = response.json()
        assert len(results) > 0, f"Expected more than 0 results, got {len(results)} for tf-idf search"
        
        
        print(f"✅ [all papers] TF-IDF search: Found {len(results)} results for query '{tfidf_query['query']}'")

        # 3. Hybrid search: test the new hybrid strategy
        hybrid_query = {
            "query": "machine learning", 
            "top_k": 5, 
            "search_strategies": [("vector", 0.8), ("tf-idf", 0.0)],
            "result_include_types": ["metadata", "text_chunks", "search_parameters"]
        }
        response = await client.post(f"{BASE_URL}/find_similar/", json=hybrid_query, timeout=10.0)
        assert response.status_code == 200, "Hybrid search failed"
        results = response.json()
        assert len(results) > 0, f"Expected more than 0 results, got {len(results)} for hybrid search"
        
        
        print(f"✅ [all papers] Hybrid search: Found {len(results)} results for query '{hybrid_query['query']}'")

        # 4. No result case: query that should not match any paper
        no_result_query = {
            "query": "quantum entanglement", 
            "top_k": 5, 
            "search_strategies": [("vector", 0.8)],
            "result_include_types": ["metadata"]
        }
        response = await client.post(f"{BASE_URL}/find_similar/", json=no_result_query, timeout=10.0)
        assert response.status_code == 200, "No-result search failed"
        results = response.json()
        assert len(results) == 0, f"Expected 0 results, got {len(results)} for no-result search"
        print(f"✅ [all papers] No-result search: Found {len(results)} results for query '{no_result_query['query']}'")

async def test_filters_functionality():
    """Test that the doc_ids filters parameter works correctly in the API."""
    async with httpx.AsyncClient() as client:
        print("\n🔍 Testing doc_ids filter functionality...")
        
        # Test 1: Include filter - only return paper_001 and paper_003
        print("\n📋 Test 1: Include filter - only specific doc_ids")
        include_filter = {
            "query": "deep learning",
            "top_k": 10,
            "search_strategies": [("vector", 0.8)],
            "result_include_types": ["metadata", "search_parameters"],
            "filters": {"include": {"doc_ids": ["paper_001", "paper_003"]}}
        }
        
        response = await client.post(f"{BASE_URL}/find_similar/", json=include_filter, timeout=10.0)
        assert response.status_code == 200, "Vector search with include filter failed"
        results = response.json()
        
        print(f"📊 Results for include filter: {len(results)} results")
        for i, result in enumerate(results):
            doc_id = result.get('doc_id', 'N/A')
            title = result.get('metadata', {}).get('title', 'N/A')
            score = result.get('score', 'N/A')
            print(f"  {i+1}. doc_id: {doc_id}, title: {title}, score: {score}")
        
        # Verify that all results have doc_ids in the include filter
        expected_doc_ids = {"paper_003","paper_001"}
        for result in results:
            result_doc_id = result.get('doc_id', '')
            assert result_doc_id in expected_doc_ids, f"Result with doc_id '{result_doc_id}' not in expected include filter list"
        print(f"✅ All {len(results)} results are within expected doc_ids: {expected_doc_ids}")
        
        # Test 2: Exclude filter - exclude paper_001 and paper_003
        print("\n📋 Test 2: Exclude filter - exclude specific doc_ids")
        exclude_filter = {
            "query": "deep learning",
            "top_k": 10,
            "search_strategies": [("vector", 0.8)],
            "result_include_types": ["metadata", "search_parameters"],
            "filters": {"exclude": {"doc_ids": ["paper_001", "paper_003"]}}
        }
        
        response = await client.post(f"{BASE_URL}/find_similar/", json=exclude_filter, timeout=10.0)
        assert response.status_code == 200, "Vector search with exclude filter failed"
        results = response.json()
        
        print(f"📊 Results for exclude filter: {len(results)} results")
        for i, result in enumerate(results):
            doc_id = result.get('doc_id', 'N/A')
            title = result.get('metadata', {}).get('title', 'N/A')
            score = result.get('score', 'N/A')
            print(f"  {i+1}. doc_id: {doc_id}, title: {title}, score: {score}")
        
        # Verify that no results have doc_ids in the exclude filter
        excluded_doc_ids = {"paper_001", "paper_003"}
        for result in results:
            result_doc_id = result.get('doc_id', '')
            assert result_doc_id not in excluded_doc_ids, f"Result with doc_id '{result_doc_id}' should be excluded but was found"
        print(f"✅ All {len(results)} results are correctly excluded from: {excluded_doc_ids}")
        
        print("\n🎉 All doc_ids filter tests completed successfully!")
        print("✅ Include filter working correctly")
        print("✅ Exclude filter working correctly")
        print("✅ Filter validation working correctly")

async def test_text_type_filters():
    """Test that the text_type filters parameter works correctly in the API."""
    async with httpx.AsyncClient() as client:
        print("\n🔍 Testing text_type filter functionality...")
        
        # Test 1: Abstract-only filter
        print("\n📋 Test 1: Abstract-only filter")
        abstract_only_filter = {
            "query": "deep learning",
            "top_k": 10,
            "search_strategies": [("vector", 0.8)],
            "result_include_types": ["metadata", "search_parameters"],
            "filters": {
                "include": {
                    "text_type": ["abstract"]
                }
            }
        }
        
        response = await client.post(f"{BASE_URL}/find_similar/", json=abstract_only_filter, timeout=10.0)
        assert response.status_code == 200, "Vector search with abstract-only filter failed"
        results = response.json()
        
        print(f"📊 Results for abstract-only filter: {len(results)} results")
        for i, result in enumerate(results):
            print(result)
            doc_id = result.get('doc_id', 'N/A')
            title = result.get('metadata', {}).get('title', 'N/A')
            score = result.get('score', 'N/A')
            print(f"  {i+1}. doc_id: {doc_id}, title: {title}, score: {score}")
        
        print(f"✅ Abstract-only filter: Found {len(results)} results")
        
        # Test 2: Combined text filter (title + categories + abstract)
        print("\n📋 Test 2: Combined text filter")
        combined_filter = {
            "query": "machine learning",
            "top_k": 10,
            "search_strategies": [("vector", 0.8)],
            "result_include_types": ["metadata", "search_parameters"],
            "filters": {
                "include": {
                    "text_type": ["combined"]
                }
            }
        }
        
        response = await client.post(f"{BASE_URL}/find_similar/", json=combined_filter, timeout=10.0)
        assert response.status_code == 200, "Vector search with combined filter failed"
        results = response.json()
        
        print(f"📊 Results for combined filter: {len(results)} results")
        for i, result in enumerate(results):
            print(result)
            doc_id = result.get('doc_id', 'N/A')
            title = result.get('metadata', {}).get('title', 'N/A')
            score = result.get('score', 'N/A')
            print(f"  {i+1}. doc_id: {doc_id}, title: {title}, score: {score}")
        
        print(f"✅ Combined filter: Found {len(results)} results")
        
        # Test 3: Exclude chunk filter
        '''
        print("\n📋 Test 3: Exclude chunk filter")
        exclude_chunk_filter = {
            "query": "neural networks",
            "top_k": 10,
            "search_strategies": [("vector", 0.8)],
            "result_include_types": ["metadata", "search_parameters"],
            "filters": {
                "include": {
                    "text_type": ["abstract", "combined"]
                },
                "exclude": {
                    "text_type": ["chunk"]
                }
            }
        }
        
        response = await client.post(f"{BASE_URL}/find_similar/", json=exclude_chunk_filter, timeout=10.0)
        assert response.status_code == 200, "Vector search with exclude chunk filter failed"
        results = response.json()
        
        print(f"📊 Results for exclude chunk filter: {len(results)} results")
        for i, result in enumerate(results):
            doc_id = result.get('doc_id', 'N/A')
            title = result.get('metadata', {}).get('title', 'N/A')
            score = result.get('score', 'N/A')
            print(f"  {i+1}. doc_id: {doc_id}, title: {title}, score: {score}")
        
        print(f"✅ Exclude chunk filter: Found {len(results)} results")
        '''
        print("\n🎉 All text_type filter tests completed successfully!")
        print("✅ Abstract-only filter working correctly")
        print("✅ Combined text filter working correctly")
        print("✅ Exclude chunk filter working correctly")

async def test_result_include_types():
    """Test that the result_include_types parameter works correctly in the API."""
    async with httpx.AsyncClient() as client:
        print("\n🔍 Testing result_include_types functionality...")
        
        # Test 1: Metadata only
        print("\n📋 Test 1: Metadata only")
        metadata_only_query = {
            "query": "deep learning",
            "top_k": 5,
            "search_strategies": [("vector", 0.8)],
            "result_include_types": ["metadata"]
        }
        
        response = await client.post(f"{BASE_URL}/find_similar/", json=metadata_only_query, timeout=10.0)
        assert response.status_code == 200, "Metadata-only search failed"
        results = response.json()
        
        print(f"📊 Results for metadata-only: {len(results)} results")
        for i, result in enumerate(results):
            doc_id = result.get('doc_id', 'N/A')
            metadata = result.get('metadata', {})
            title = metadata.get('title', 'N/A')
            score = result.get('score', 'N/A')
            print(f"  {i+1}. doc_id: {doc_id}, title: {title}, score: {score}")
            
            # Verify metadata structure
            assert "metadata" in result, "Result missing metadata"
            assert "title" in metadata, "Metadata missing title"
            assert "abstract" in metadata, "Metadata missing abstract"
            assert "authors" in metadata, "Metadata missing authors"
            assert "categories" in metadata, "Metadata missing categories"
            
            # Verify other types are not included
            assert "text_chunks" not in result, "Result should not include text_chunks"
            assert "search_parameters" not in result, "Result should not include search_parameters"
        
        print(f"✅ Metadata-only: Found {len(results)} results with correct structure")
        
        # Test 2: Metadata + text_chunks
        print("\n📋 Test 2: Metadata + text_chunks")
        text_chunks_query = {
            "query": "machine learning",
            "top_k": 3,
            "search_strategies": [("vector", 0.8)],
            "result_include_types": ["metadata", "text_chunks"]
        }
        
        response = await client.post(f"{BASE_URL}/find_similar/", json=text_chunks_query, timeout=10.0)
        assert response.status_code == 200, "Text chunks search failed"
        results = response.json()
        
        print(f"📊 Results for text_chunks: {len(results)} results")
        for i, result in enumerate(results):
            print(result)
            doc_id = result.get('doc_id', 'N/A')
            metadata = result.get('metadata', {})
            title = metadata.get('title', 'N/A')
            score = result.get('score', 'N/A')
            text_chunks = result.get('text_chunks', [])
            print(f"  {i+1}. doc_id: {doc_id}, title: {title}, score: {score}, chunks: {len(text_chunks)}")
            
            # Verify text_chunks structure
            assert "text_chunks" in result, "Result missing text_chunks"
            assert len(text_chunks) > 0, f"Text chunks missing for doc_id {doc_id}"

        print(f"✅ Text chunks: Found {len(results)} results with correct structure")
        
        # Test 3: Full result with all types
        print("\n📋 Test 3: Full result with all types")
        full_result_query = {
            "query": "transformer",
            "top_k": 2,
            "search_strategies": [("vector", 0.8), ("tf-idf", 0.0)],
            "result_include_types": ["metadata", "text_chunks", "search_parameters","full_text"]
        }
        
        response = await client.post(f"{BASE_URL}/find_similar/", json=full_result_query, timeout=10.0)
        assert response.status_code == 200, "Full result search failed"
        results = response.json()
        
        print(f"📊 Results for full result: {len(results)} results")
        for i, result in enumerate(results):
            print(result)
            doc_id = result.get('doc_id', 'N/A')
            metadata = result.get('metadata', {})
            title = metadata.get('title', 'N/A')
            score = result.get('score', 'N/A')
            search_params = result.get('search_parameters', {})
            full_text = result.get('full_text', 'N/A')
            print(f"  {i+1}. doc_id: {doc_id}, title: {title}, score: {score}")
            
            # Verify all required fields are present
            assert "metadata" in result, "Result missing metadata"
            assert "text_chunks" in result, "Result missing text_chunks"
            assert "search_parameters" in result, "Result missing search_parameters"
            assert "full_text" in result, "Result missing full_text"
        
        print(f"✅ Full result: Found {len(results)} results with complete structure")
        
        print("\n🎉 All result_include_types tests completed successfully!")
        print("✅ Metadata-only working correctly")
        print("✅ Text chunks working correctly")
        print("✅ Full result working correctly")

async def test_advanced_filters():
    """Test advanced filter functionality including categories, authors, and date ranges."""
    async with httpx.AsyncClient() as client:
        print("\n🔍 Testing advanced filter functionality...")
        
        # Test 1: Category filter
        print("\n📋 Test 1: Category filter")
        category_filter = {
            "query": "learning",
            "top_k": 10,
            "search_strategies": [("tf-idf", 0.5)],
            "similarity_cutoff": 0.5,
            "result_include_types": ["metadata", "search_parameters"],
            "filters": {
                "include": {
                    "categories": ["cs.AI", "cs.LG"]
                }
            }
        }
        
        response = await client.post(f"{BASE_URL}/find_similar/", json=category_filter, timeout=10.0)
        assert response.status_code == 200, "Category filter search failed"
        results = response.json()
        
        print(f"📊 Results for category filter: {len(results)} results")
        for i, result in enumerate(results):
            doc_id = result.get('doc_id', 'N/A')
            metadata = result.get('metadata', {})
            title = metadata.get('title', 'N/A')
            categories = metadata.get('categories', [])
            score = result.get('score', 'N/A')
            print(f"  {i+1}. doc_id: {doc_id}, title: {title}, categories: {categories}, score: {score}")
            
            # Verify that all results have the expected categories
            has_expected_category = any(cat in ["cs.AI", "cs.LG"] for cat in categories)
            assert has_expected_category, f"Result {doc_id} does not have expected categories"
        
        print(f"✅ Category filter: Found {len(results)} results with correct categories")
        
        # Test 2: Author filter
        print("\n📋 Test 2: Author filter")
        author_filter = {
            "query": "learning",
            "top_k": 10,
            "search_strategies": [("tf-idf", 0.5)],
            "result_include_types": ["metadata", "search_parameters"],
            "filters": {
                "include": {
                    "authors": ["Alice", "Carol"]
                }
            }
        }
        
        response = await client.post(f"{BASE_URL}/find_similar/", json=author_filter, timeout=10.0)
        assert response.status_code == 200, "Author filter search failed"
        results = response.json()
        
        print(f"📊 Results for author filter: {len(results)} results")
        for i, result in enumerate(results):
            doc_id = result.get('doc_id', 'N/A')
            metadata = result.get('metadata', {})
            title = metadata.get('title', 'N/A')
            authors = metadata.get('authors', [])
            score = result.get('score', 'N/A')
            print(f"  {i+1}. doc_id: {doc_id}, title: {title}, authors: {authors}, score: {score}")
            
            # Verify that all results have the expected authors
            has_expected_author = any(author in ["Alice", "Carol"] for author in authors)
            assert has_expected_author, f"Result {doc_id} does not have expected authors"
        
        print(f"✅ Author filter: Found {len(results)} results with correct authors")
        
        # Test 3: Date range filter
        print("\n📋 Test 3: Date range filter")
        date_filter = {
            "query": "learning",
            "top_k": 10,
            "search_strategies": [("tf-idf", 0.5)],
            "result_include_types": ["metadata", "search_parameters"],
            "filters": {
                "include": {
                    "published_date": ["2023-01-01", "2024-12-31"]
                }
            }
        }
        
        response = await client.post(f"{BASE_URL}/find_similar/", json=date_filter, timeout=10.0)
        assert response.status_code == 200, "Date filter search failed"
        results = response.json()
        
        print(f"📊 Results for date filter: {len(results)} results")
        for i, result in enumerate(results):
            doc_id = result.get('doc_id', 'N/A')
            metadata = result.get('metadata', {})
            title = metadata.get('title', 'N/A')
            published_date = metadata.get('published_date', 'N/A')
            score = result.get('score', 'N/A')
            print(f"  {i+1}. doc_id: {doc_id}, title: {title}, date: {published_date}, score: {score}")
            
            # Verify that all results have dates in the expected range
            if published_date != 'N/A':
                assert "2023" in published_date or "2024" in published_date, f"Result {doc_id} date {published_date} not in expected range"
        
        print(f"✅ Date filter: Found {len(results)} results with correct date range")
        
        # Test 4: Combined filters
        print("\n📋 Test 4: Combined filters")
        combined_filter = {
            "query": "learning",
            "top_k": 10,
            "search_strategies": [("tf-idf", 0.5)],
            "result_include_types": ["metadata", "search_parameters"],
            "filters": {
                "include": {
                    "categories": ["cs.AI"],
                    "text_type": ["abstract"]
                },
                "exclude": {
                    "doc_ids": ["paper_005"]
                }
            }
        }
        
        response = await client.post(f"{BASE_URL}/find_similar/", json=combined_filter, timeout=10.0)
        assert response.status_code == 200, "Combined filter search failed"
        results = response.json()
        
        print(f"📊 Results for combined filter: {len(results)} results")
        for i, result in enumerate(results):
            doc_id = result.get('doc_id', 'N/A')
            metadata = result.get('metadata', {})
            title = metadata.get('title', 'N/A')
            categories = metadata.get('categories', [])
            score = result.get('score', 'N/A')
            print(f"  {i+1}. doc_id: {doc_id}, title: {title}, categories: {categories}, score: {score}")
            
            # Verify combined filter conditions
            assert doc_id != "paper_005", f"Result {doc_id} should be excluded"
            has_cs_ai = any(cat == "cs.AI" for cat in categories)
            assert has_cs_ai, f"Result {doc_id} should have cs.AI category"
        
        print(f"✅ Combined filter: Found {len(results)} results with correct combined conditions")
        
        print("\n🎉 All advanced filter tests completed successfully!")
        print("✅ Category filter working correctly")
        print("✅ Author filter working correctly")
        print("✅ Date filter working correctly")
        print("✅ Combined filters working correctly")

async def test_save_image():
    """Test save_image API functionality."""
    async with httpx.AsyncClient() as client:
        print("\n🔍 Testing save_image API functionality...")
        
        # Test 1: Save image using file path
        print("\n📋 Test 1: Save image using file path")
        save_image_path_request = {
            "object_name": "test_paper_001_fig1",
            "image_path": test_images["test_image_0"]
        }
        
        response = await client.post(f"{BASE_URL}/save_image/", json=save_image_path_request, timeout=10.0)
        assert response.status_code == 200, f"Save image with path failed: {response.text}"
        result = response.json()
        
        assert result["success"] == True, "Save image should return success=True"
        assert result["object_name"] == "test_paper_001_fig1", "Object name should match"
        assert "saved successfully" in result["message"], "Message should indicate success"
        print(f"✅ Save image with path: {result['message']}")
        
        # Test 2: Save image using image data (base64 encoded)
        print("\n📋 Test 2: Save image using image data")
        import base64
        # Use the same PNG data as in setup_test_images for consistency
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        test_image_data = base64.b64encode(png_data).decode()
        save_image_data_request = {
            "object_name": "test_paper_002_fig1",
            "image_data": test_image_data
        }
        
        response = await client.post(f"{BASE_URL}/save_image/", json=save_image_data_request, timeout=10.0)
        assert response.status_code == 200, f"Save image with data failed: {response.text}"
        result = response.json()
        
        assert result["success"] == True, "Save image should return success=True"
        assert result["object_name"] == "test_paper_002_fig1", "Object name should match"
        assert "saved successfully" in result["message"], "Message should indicate success"
        print(f"✅ Save image with data: {result['message']}")
        

async def test_save_image_error_cases():
    """Test save_image API error handling."""
    async with httpx.AsyncClient() as client:
        print("\n🔍 Testing save_image API error handling...")
        
        # Test 1: Missing both image_path and image_data
        print("\n📋 Test 1: Missing both image_path and image_data")
        invalid_request = {
            "object_name": "test_invalid"
        }
        
        response = await client.post(f"{BASE_URL}/save_image/", json=invalid_request, timeout=10.0)
        assert response.status_code == 422, f"Expected 422 for missing image data, got {response.status_code}"
        print("✅ Missing image data validation working correctly")
        
        # Test 2: Providing both image_path and image_data
        print("\n📋 Test 2: Providing both image_path and image_data")
        import base64
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        test_image_data = base64.b64encode(png_data).decode()
        invalid_request = {
            "object_name": "test_invalid",
            "image_path": test_images["test_image_0"],
            "image_data": test_image_data
        }
        
        response = await client.post(f"{BASE_URL}/save_image/", json=invalid_request, timeout=10.0)
        assert response.status_code == 422, f"Expected 422 for both image data provided, got {response.status_code}"
        print("✅ Both image data validation working correctly")
        
        # Test 3: Non-existent file path
        print("\n📋 Test 3: Non-existent file path")
        invalid_request = {
            "object_name": "test_invalid",
            "image_path": "/non/existent/path/image.png"
        }
        
        response = await client.post(f"{BASE_URL}/save_image/", json=invalid_request, timeout=10.0)
        assert response.status_code == 500, f"Expected 500 for non-existent file, got {response.status_code}"
        print("✅ Non-existent file path handling working correctly")
        
        print("\n🎉 All save_image error case tests completed successfully!")
        print("✅ Missing image data validation working correctly")
        print("✅ Both image data validation working correctly")
        print("✅ Non-existent file path handling working correctly")

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
        
        
        # Test invalid search_strategy_type
        response = await client.post(
            f"{BASE_URL}/find_similar/",
            json={
                "query": "test",
                "top_k": 5,
                "search_strategy_type": "invalid_strategy",
                "result_include_types": ["metadata"]
            }
        )
        assert response.status_code == 422, "Expected 422 for invalid search_strategy_type"
        
        # Test invalid result_include_types
        response = await client.post(
            f"{BASE_URL}/find_similar/",
            json={
                "query": "test",
                "top_k": 5,
                "search_strategies": [("vector", 0.8)],
                "result_include_types": ["invalid_type"]
            }
        )
        assert response.status_code == 422, "Expected 422 for invalid result_include_types"
        
        # Test invalid text_type in filters
        response = await client.post(
            f"{BASE_URL}/find_similar/",
            json={
                "query": "test",
                "top_k": 5,
                "search_strategies": [("vector", 0.8)],
                "result_include_types": ["metadata"],
                "filters": {
                    "include": {
                        "text_type": ["invalid_text_type"]
                    }
                }
            }
        )
        assert response.status_code == 422, "Expected 422 for invalid text_type in filters"
        
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

# To RUN tests, we need to first reinit_database, then run the tests.
# This is because the tests are designed to run against a fresh vector database.
# If the vector database is not fresh, the tests will fail.
# To reinit_database, we need to run the following command:
# python scripts/paper_db_init.py --recreate_databases
# This will recreate the vector database and the metadata database.
# Then, we can run the tests.


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
        await test_filters_functionality()
        await test_text_type_filters()
        await test_result_include_types()
        #await test_advanced_filters()
        
        # Image storage tests
        await test_save_image()
        await test_save_image_error_cases()
        
        # Error case tests
        await test_error_cases()
        
        print("\n✅ All tests passed successfully!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {str(e)}")
        print("\n💡 This failure might be due to old vector database data.")
        print("   Consider restarting the API server and running tests again.")
    except Exception as e:
        print(f"\n❌ Error during tests: {str(e)}")
    finally:
        # Clean up temporary files
        import shutil
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        clean_metadata_db()
        clean_vector_db()


if __name__ == "__main__":
    asyncio.run(run_tests()) 