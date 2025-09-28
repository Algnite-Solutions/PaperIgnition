#!/usr/bin/env python3
"""
Test script to verify image storage functionality works correctly.

This test covers:
1. Integrated image storage during index_papers (store_images=True)
2. Delayed image storage using store_images API (store_images=False)
3. Image storage status checking
4. Image retrieval functionality
5. Error handling for image operations

Example usage of image storage APIs:
1. Store images during indexing:
   {
     "docsets": [...],
     "store_images": true,
     "keep_temp_image": false
   }

2. Delayed image storage:
   {
     "docsets": [...],
     "keep_temp_image": false
   }

3. Check image storage status:
   {
     "doc_id": "paper001"
   }

4. Retrieve image:
   {
     "image_id": "paper001_fig1"
   }
"""

import httpx
import asyncio
import yaml
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List
from AIgnite.data.docset import DocSet, TextChunk, ChunkType, DocSetList, FigureChunk
from backend.index_service.db_utils import load_config
from backend.index_service.models import IndexPapersRequest, StoreImagesRequest, GetImageRequest, GetImageStorageStatusRequest
import sqlalchemy

# 使用测试专用配置文件
config = load_config("backend/configs/test_config.yaml")

BASE_URL = config['host']

# Create temporary directory for test files
TEMP_DIR = tempfile.mkdtemp()

# Create necessary directories
print(config)

# Create test PDF files (7 papers total)
def setup_test_files():
    """Create test PDF files."""
    test_pdfs = {}
    for i in range(7):
        pdf_path = os.path.join(TEMP_DIR, f"test_paper_{i}.pdf")
        with open(pdf_path, 'wb') as f:
            f.write(f"Test PDF content for paper {i}".encode())
        test_pdfs[f"paper{i+1:03d}"] = pdf_path
    return test_pdfs

# Create test files
test_pdfs = setup_test_files()

# Create test image files (more images for testing)
def setup_test_images():
    """Create test image files."""
    test_images = {}
    for i in range(5):  # Create 5 test images
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

# Delete test papers from metadata_db before running tests
def clean_metadata_db():
    """Delete test papers from metadata_db before running tests."""
    db_url = config['metadata_db']['db_url']
    engine = sqlalchemy.create_engine(db_url)
    with engine.connect() as conn:
        # Delete from text_chunks table
        conn.execute(
            sqlalchemy.text("""
                DELETE FROM text_chunks WHERE doc_id IN ('paper001', 'paper002', 'paper003', 'paper004', 'paper005', 'paper006', 'paper007');
            """))
        # Delete from papers table
        conn.execute(
            sqlalchemy.text("""
                DELETE FROM papers WHERE doc_id IN ('paper001', 'paper002', 'paper003', 'paper004', 'paper005', 'paper006', 'paper007');
            """))
        conn.commit()
    print("✅ Metadata database cleaned")

def clean_vector_db():
    """Delete test papers from vector database before running tests."""
    vector_db_path = config['vector_db']['db_path']
    if os.path.exists(f"{vector_db_path}/index.faiss"):
        os.remove(f"{vector_db_path}/index.faiss")
    if os.path.exists(f"{vector_db_path}/index.pkl"):
        os.remove(f"{vector_db_path}/index.pkl")
    print("✅ Vector database cleaned")

def clean_image_db():
    """Delete test images from MinIO image database before running tests."""
    try:
        from AIgnite.db.image_db import MinioImageDB
        
        # Initialize MinIO client
        image_db = MinioImageDB(
            endpoint=config['minio_db']['endpoint'],
            access_key=config['minio_db']['access_key'],
            secret_key=config['minio_db']['secret_key'],
            bucket_name=config['minio_db']['bucket_name'],
            secure=config['minio_db']['secure']
        )
        
        # Generate expected image IDs from sample_papers
        expected_image_ids = []
        for docset in sample_papers.docsets:
            for figure_chunk in docset.figure_chunks:
                image_id = f"{docset.doc_id}_{figure_chunk.id}"
                expected_image_ids.append(image_id)
        
        # Delete only the expected test images
        deleted_count = 0
        for image_id in expected_image_ids:
            try:
                success = image_db.delete_image(image_id)
                if success:
                    deleted_count += 1
                    print(f"🗑️  Deleted image: {image_id}")
                else:
                    print(f"⚠️  Image not found or already deleted: {image_id}")
            except Exception as e:
                print(f"Warning: Failed to delete image {image_id}: {str(e)}")
        
        print(f"✅ Image database cleaned: {deleted_count} test images deleted")
        
    except Exception as e:
        print(f"Warning: Failed to clean image database: {str(e)}")
        print("This might be expected if MinIO is not running or accessible")

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

# Create sample papers with figure_chunks for image storage testing
docsets = []
for i in range(7):
    paper_id = f"paper{i+1:03d}"
    text_chunks = []
    figure_chunks = []
    
    # Create figure_chunks for each paper (2-3 figures per paper)
    # Each paper gets its own copy of test images to avoid file sharing issues
    for j in range(2):
        figure_id = f"fig{j+1}"
        # Create unique image files for each paper to avoid sharing issues
        unique_image_path = os.path.join(TEMP_DIR, f"{paper_id}_{figure_id}.png")
        
        # Copy the test image to a unique location for this paper
        import shutil
        source_image = test_images[f"test_image_{(i+j) % 5}"]
        shutil.copy2(source_image, unique_image_path)
        
        figure_chunk = FigureChunk(
            id=figure_id,
            type=ChunkType.FIGURE,
            image_path=unique_image_path,
            caption=f"Figure {j+1} for {paper_id}",
            metadata={"figure_type": "diagram", "page": j+1}
        )
        figure_chunks.append(figure_chunk)
    
    # Add text chunks based on paper index
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
    elif i == 4:
        text_chunks = [
            TextChunk(id="t1", type=ChunkType.TEXT, text="Bayesian optimization efficiently searches parameter space."),
            TextChunk(id="t2", type=ChunkType.TEXT, text="Applications include AutoML and black-box optimization.")
        ]
        title = "Bayesian Optimization in Machine Learning"
        abstract = "Reviews BO methods for hyperparameter tuning."
        authors = ["Ivy", "Jack"]
        categories = ["stat.ML"]
        published_date = "2023-05-01"
    elif i == 5:
        text_chunks = [
            TextChunk(id="t1", type=ChunkType.TEXT, text="Graph neural networks process structured data effectively."),
            TextChunk(id="t2", type=ChunkType.TEXT, text="We explore GCN and GraphSAGE architectures.")
        ]
        title = "Graph Neural Networks for Structured Data"
        abstract = "Investigates GNN architectures for graph-based learning."
        authors = ["Kate", "Leo"]
        categories = ["cs.LG"]
        published_date = "2023-03-15"
    else:  # i == 6
        text_chunks = [
            TextChunk(id="t1", type=ChunkType.TEXT, text="Federated learning enables privacy-preserving machine learning."),
            TextChunk(id="t2", type=ChunkType.TEXT, text="We analyze FedAvg and FedProx algorithms.")
        ]
        title = "Federated Learning: Privacy-Preserving ML"
        abstract = "Reviews federated learning approaches for distributed training."
        authors = ["Mia", "Noah"]
        categories = ["cs.LG", "cs.CR"]
        published_date = "2023-01-10"
    
    docset = DocSet(
        doc_id=paper_id,
        title=title,
        abstract=abstract,
        authors=authors,
        categories=categories,
        published_date=published_date,
        pdf_path=test_pdfs[paper_id],
        HTML_path=None,
        text_chunks=text_chunks,
        figure_chunks=figure_chunks,
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

async def test_index_papers_with_images():
    """Test indexing papers with integrated image storage (first 5 papers)."""
    async with httpx.AsyncClient() as client:
        print("\n🔍 Testing integrated image storage during indexing...")
        
        # Index first 5 papers with image storage enabled
        data = IndexPapersRequest(
            docsets=DocSetList(docsets=docsets[:5]),
            store_images=True,
            keep_temp_image=False
        ).model_dump()
        
        response = await client.post(
            f"{BASE_URL}/index_papers/",
            json=data,
            timeout=30.0
        )
        
        assert response.status_code == 200, f"Indexing with images failed: {response.text}"
        result = response.json()
        assert "message" in result, "Response missing 'message' field"
        assert "5 papers indexed successfully" in result["message"]
        print("✅ Indexed first 5 papers with image storage enabled")
        
        # Verify that images were stored by checking storage status
        for i in range(5):
            paper_id = f"paper{i+1:03d}"
            status_request = GetImageStorageStatusRequest(doc_id=paper_id)
            response = await client.post(
                f"{BASE_URL}/get_image_storage_status/",
                json=status_request.model_dump(),
                timeout=10.0
            )
            
            assert response.status_code == 200, f"Storage status check failed for {paper_id}: {response.text}"
            status_data = response.json()
            assert status_data["success"] == True, f"Storage status check unsuccessful for {paper_id}"
            assert "storage_status" in status_data, f"Missing storage_status for {paper_id}"
            
            storage_status = status_data["storage_status"]
            print(f"📊 Storage status for {paper_id}: {storage_status}")
            
            # Verify that images were stored (should have entries for fig1 and fig2)
            expected_figures = [f"{paper_id}_fig1", f"{paper_id}_fig2"]
            for fig_id in expected_figures:
                assert fig_id in storage_status, f"Missing storage status for {fig_id}"
                assert storage_status[fig_id] == True, f"Image {fig_id} not stored successfully"
        
        print("✅ All images stored successfully during indexing")

async def test_delayed_image_storage():
    """Test delayed image storage for last 2 papers."""
    async with httpx.AsyncClient() as client:
        print("\n🔍 Testing delayed image storage...")
        
        # First, index last 2 papers without image storage
        data = IndexPapersRequest(
            docsets=DocSetList(docsets=docsets[5:]),
            store_images=False,
            keep_temp_image=False
        ).model_dump()
        
        response = await client.post(
            f"{BASE_URL}/index_papers/",
            json=data,
            timeout=30.0
        )
        
        assert response.status_code == 200, f"Indexing without images failed: {response.text}"
        result = response.json()
        assert "message" in result, "Response missing 'message' field"
        assert "2 papers indexed successfully" in result["message"]
        print("✅ Indexed last 2 papers without image storage")
        
        # Verify initial state - no images should be stored
        for i in range(5, 7):
            paper_id = f"paper{i+1:03d}"
            status_request = GetImageStorageStatusRequest(doc_id=paper_id)
            response = await client.post(
                f"{BASE_URL}/get_image_storage_status/",
                json=status_request.model_dump(),
                timeout=10.0
            )
            
            if response.status_code == 404:
                print(f"📊 No storage status found for {paper_id} (expected for papers without images)")
            else:
                assert response.status_code == 200, f"Unexpected response for {paper_id}: {response.text}"
                status_data = response.json()
                if status_data["success"]:
                    storage_status = status_data.get("storage_status", {})
                    print(f"📊 Initial storage status for {paper_id}: {storage_status}")
        
        # Now use store_images API to store images for these papers
        store_request = StoreImagesRequest(
            docsets=DocSetList(docsets=docsets[5:]),
            keep_temp_image=False
        )
        
        response = await client.post(
            f"{BASE_URL}/store_images/",
            json=store_request.model_dump(),
            timeout=30.0
        )
        
        assert response.status_code == 200, f"Store images API failed: {response.text}"
        result = response.json()
        assert result["success"] == True, "Store images API returned success=False"
        assert "2 papers" in result["message"], "Unexpected message from store_images API"
        print("✅ Store images API completed successfully")
        
        # Verify that images are now stored
        for i in range(5, 7):
            paper_id = f"paper{i+1:03d}"
            status_request = GetImageStorageStatusRequest(doc_id=paper_id)
            response = await client.post(
                f"{BASE_URL}/get_image_storage_status/",
                json=status_request.model_dump(),
                timeout=10.0
            )
            
            assert response.status_code == 200, f"Storage status check failed for {paper_id}: {response.text}"
            status_data = response.json()
            assert status_data["success"] == True, f"Storage status check unsuccessful for {paper_id}"
            
            storage_status = status_data["storage_status"]
            print(f"📊 Final storage status for {paper_id}: {storage_status}")
            
            # Verify that images were stored
            expected_figures = [f"{paper_id}_fig1", f"{paper_id}_fig2"]
            for fig_id in expected_figures:
                assert fig_id in storage_status, f"Missing storage status for {fig_id}"
                assert storage_status[fig_id] == True, f"Image {fig_id} not stored successfully"
        
        print("✅ Delayed image storage completed successfully")

async def test_image_retrieval():
    """Test image retrieval functionality."""
    async with httpx.AsyncClient() as client:
        print("\n🔍 Testing image retrieval...")
        
        # Test retrieving images from the first paper
        test_image_ids = ["paper001_fig1", "paper001_fig2"]
        
        for image_id in test_image_ids:
            request = GetImageRequest(image_id=image_id)
            response = await client.post(
                f"{BASE_URL}/get_image/",
                json=request.model_dump(),
                timeout=10.0
            )
            
            assert response.status_code == 200, f"Image retrieval failed for {image_id}: {response.text}"
            result = response.json()
            assert result["success"] == True, f"Image retrieval unsuccessful for {image_id}"
            assert "image_data" in result, f"Missing image_data for {image_id}"
            assert result["image_data"] is not None, f"Empty image_data for {image_id}"
            
            print(f"✅ Successfully retrieved image {image_id}")
        
        # Test error case - non-existent image
        invalid_request = GetImageRequest(image_id="nonexistent_image")
        response = await client.post(
            f"{BASE_URL}/get_image/",
            json=invalid_request.model_dump(),
            timeout=10.0
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent image, got {response.status_code}"
        print("✅ Error handling for non-existent image working correctly")

async def test_image_storage_status():
    """Test image storage status checking for all papers."""
    async with httpx.AsyncClient() as client:
        print("\n🔍 Testing image storage status checking...")
        
        # Check status for all 7 papers
        for i in range(7):
            paper_id = f"paper{i+1:03d}"
            status_request = GetImageStorageStatusRequest(doc_id=paper_id)
            response = await client.post(
                f"{BASE_URL}/get_image_storage_status/",
                json=status_request.model_dump(),
                timeout=10.0
            )
            
            assert response.status_code == 200, f"Storage status check failed for {paper_id}: {response.text}"
            status_data = response.json()
            assert status_data["success"] == True, f"Storage status check unsuccessful for {paper_id}"
            assert "storage_status" in status_data, f"Missing storage_status for {paper_id}"
            
            storage_status = status_data["storage_status"]
            print(f"📊 Storage status for {paper_id}: {storage_status}")
            
            # Verify that all expected images are stored
            expected_figures = [f"{paper_id}_fig1", f"{paper_id}_fig2"]
            for fig_id in expected_figures:
                assert fig_id in storage_status, f"Missing storage status for {fig_id}"
                assert storage_status[fig_id] == True, f"Image {fig_id} not stored successfully"
        
        print("✅ All papers have correct image storage status")

async def test_error_cases():
    """Test error handling for image operations."""
    async with httpx.AsyncClient() as client:
        print("\n🔍 Testing error cases...")
        
        # Test invalid doc_id for storage status
        invalid_status_request = GetImageStorageStatusRequest(doc_id="invalid_doc_id")
        response = await client.post(
            f"{BASE_URL}/get_image_storage_status/",
            json=invalid_status_request.model_dump(),
            timeout=10.0
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid doc_id, got {response.status_code}"
        print("✅ Error handling for invalid doc_id working correctly")
        
        # Test empty image_id
        empty_image_request = GetImageRequest(image_id="")
        response = await client.post(
            f"{BASE_URL}/get_image/",
            json=empty_image_request.model_dump(),
            timeout=10.0
        )
        
        assert response.status_code == 422, f"Expected 422 for empty image_id, got {response.status_code}"
        print("✅ Error handling for empty image_id working correctly")

async def run_image_storage_tests():
    """Run all image storage tests in sequence."""
    print(f"\nRunning image storage tests against {BASE_URL}")
    print("=" * 60)
    try:
        
        # Check if server is running first
        if not await check_server_running(BASE_URL):
            return
        
        # Clean databases before starting tests
        print("🧹 Cleaning databases before starting tests...")
        clean_metadata_db()
        clean_vector_db()
        clean_image_db()
        
        # Initialize database
        await test_init_database_endpoint()
        
        # Basic health check
        await test_connection_health()
        
        # Test integrated image storage (first 5 papers)
        await test_index_papers_with_images()
        
        # Test delayed image storage (last 2 papers)
        await test_delayed_image_storage()
        
        # Test image retrieval
        await test_image_retrieval()
        
        # Test storage status checking
        await test_image_storage_status()
        
        # Test error cases
        await test_error_cases()
        
        print("\n✅ All image storage tests passed successfully!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {str(e)}")
        print("\n💡 This failure might be due to old database data.")
        print("   Consider restarting the API server and running tests again.")
    except Exception as e:
        print(f"\n❌ Error during tests: {str(e)}")
    finally:
        # Clean up temporary files
        import shutil
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        clean_metadata_db()
        clean_vector_db()
        clean_image_db()

if __name__ == "__main__":
    asyncio.run(run_image_storage_tests())
