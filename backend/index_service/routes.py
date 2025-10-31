from fastapi import APIRouter, HTTPException, Query, Body
from .models import CustomerQuery, SaveImageRequest, GetImageRequest, ImageResponse, StoreImagesRequest, StoreImagesResponse, IndexPapersRequest, GetImageRequest, GetImageResponse, GetImageStorageStatusRequest, GetImageStorageStatusResponse, SaveVectorsRequest, SaveVectorsResponse, GetAllDocIdsResponse, DeleteVectorDocumentRequest, DeleteVectorDocumentResponse
from AIgnite.data.docset import DocSet, TextChunk, FigureChunk, TableChunk, ChunkType, DocSetList
from typing import Dict, Any, List, Optional
from .service import paper_indexer, index_papers, get_metadata, find_similar, create_indexer, save_image, store_images, get_image, get_image_storage_status, save_vectors, get_all_metadata_doc_ids, get_all_vector_doc_ids, delete_vector_document
from AIgnite.index.paper_indexer import PaperIndexer
from pydantic import BaseModel, validator
import logging
from .db_utils import init_databases, load_config

# Set up logging
logger = logging.getLogger(__name__)

# Define request model
class InitDatabaseRequest(BaseModel):
    config: Dict[str, Any]

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "indexer_ready": paper_indexer is not None}

@router.post("/init_database")
async def init_database_route(
    request: InitDatabaseRequest,
    recreate_databases: bool = Query(False, description="Whether to recreate databases from scratch")
) -> Dict[str, str]:
    """Initialize or reinitialize the databases and indexer using AIgnite's architecture.
    
    This endpoint initializes the three-database architecture:
    - MetadataDB (PostgreSQL): For paper metadata and full-text search
    - VectorDB (FAISS): For semantic vector search
    - MinioImageDB (MinIO): For image storage
    
    Args:
        request: Configuration for database initialization
        recreate_databases: If True, drops and recreates all databases
        
    Returns:
        Success message indicating database initialization status
    """
    try:
        # Use provided config or load default config
        config = request.config if request.config else load_config()
        
        # Initialize databases
        vector_db, metadata_db, image_db = init_databases(config)
        
        # Set databases in the global indexer
        paper_indexer.set_databases(vector_db, metadata_db, image_db)
        
        # Set default search strategy
        #paper_indexer.set_search_strategy([("tf-idf", 0.1)])  # 使用正确的元组列表格式
        
        action = "reinitialized" if recreate_databases else "initialized"
        return {"message": f"Database {action} and indexer creation successful"}
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")

@router.post("/index_papers/")
async def index_papers_route(request: IndexPapersRequest) -> Dict[str, str]:
    """Index a list of papers using AIgnite's parallel storage architecture.
    
    This endpoint stores papers across multiple databases:
    - MetadataDB (PostgreSQL): Paper metadata, PDF data, and text chunks
    - VectorDB (FAISS): Vector embeddings for semantic search
    - MinioImageDB (MinIO): Image data from figures
    
    The indexing process uses parallel storage to maximize performance and
    provides detailed status reporting for each database type.
    
    Args:
        request: IndexPapersRequest containing docsets, store_images, and keep_temp_image parameters
        
    Returns:
        Success message with number of papers indexed
    """
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    
    try:
        docsets = []
        for paper in request.docsets.docsets:
            # 修改figure_chunks的id格式，从title中提取下划线之后的部分
            modified_figure_chunks = []
            figure_counter = 1
            for chunk in paper.figure_chunks:
                # 从title中提取下划线之后的部分作为图片名称
                new_chunk_data = chunk.dict()
                if '_' in chunk.title:
                    # 提取下划线之后的部分，并添加.png扩展名
                    figure_name = chunk.title.split('_', 1)[1] + '.png'
                    new_chunk_data['id'] = figure_name
                else:
                    # 如果没有下划线，使用计数器
                    new_chunk_data['id'] = f"Figure{figure_counter}.png"
                modified_figure_chunks.append(FigureChunk(**new_chunk_data))
                figure_counter += 1
            
            docsets.append(DocSet(
                doc_id=paper.doc_id,
                title=paper.title,
                abstract=paper.abstract,
                authors=paper.authors,
                categories=paper.categories,
                published_date=paper.published_date,
                pdf_path=paper.pdf_path,
                HTML_path=paper.HTML_path,
                text_chunks=[TextChunk(**chunk.dict()) for chunk in paper.text_chunks],
                figure_chunks=modified_figure_chunks,
                table_chunks=[TableChunk(**chunk.dict()) for chunk in paper.table_chunks],
                metadata=paper.metadata or {},
                comments=paper.comments
            ))
        success = index_papers(paper_indexer, docsets, store_images=request.store_images, keep_temp_image=request.keep_temp_image)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to index papers")
        return {"message": f"{len(docsets)} papers indexed successfully"}
    except Exception as e:
        logger.error(f"Error indexing papers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get_metadata/{doc_id}")
async def get_metadata_route(doc_id: str) -> Dict[str, Any]:
    """Get metadata for a specific paper from the MetadataDB.
    
    Args:
        doc_id: The document ID of the paper
        
    Returns:
        Dictionary containing paper metadata including title, abstract, authors, categories, etc.
    """
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    
    try:
        metadata = get_metadata(paper_indexer, doc_id)
        if metadata is None or not metadata:
            raise HTTPException(status_code=404, detail=f"Metadata not found for doc_id: {doc_id}")
        return metadata
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metadata for {doc_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/find_similar/")
async def find_similar_route(query: CustomerQuery):
    """Find papers similar to the query using AIgnite's modular search architecture.
    
    This endpoint leverages AIgnite's advanced search capabilities:
    - Multiple search strategies (vector, tf-idf, hybrid)
    - Advanced filtering with include/exclude structure
    - Text type filtering (abstract, chunk, combined)
    - Result combination with multiple data types
    
    Supports advanced filtering with include/exclude structure:
    - include: Must match conditions
    - exclude: Must not match conditions
    - Supported fields: categories, authors, published_date, doc_ids, title_keywords, abstract_keywords, text_type
    - Supports result_include_types to specify which data types to include in results
    
    Text type filtering allows precise control over search scope:
    - "abstract": Search only in paper abstracts (faster, more focused)
    - "chunk": Search only in text chunks (detailed content matching)
    - "combined": Search in title + categories + abstract combination (comprehensive coverage)
    
    Supports extended retrieve results for reranking debug:
    - When retrieve_k is provided, returns extended format with both top_k and retrieve_k results
    """
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    logger.info(f"Received similarity search query: {query}")
    try:
        # Validate parameters
        if not query.query or not query.query.strip():
            raise HTTPException(status_code=422, detail="Query string cannot be empty")
        
        if query.top_k is not None and query.top_k <= 0:
            raise HTTPException(status_code=422, detail="top_k must be a positive integer")
        
        if query.retrieve_k is not None and query.retrieve_k <= 0:
            raise HTTPException(status_code=422, detail="retrieve_k must be a positive integer")
        
        if query.retrieve_k is not None and query.top_k is not None:
            if query.retrieve_k < query.top_k:
                raise HTTPException(
                    status_code=422, 
                    detail=f"retrieve_k ({query.retrieve_k}) must be >= top_k ({query.top_k})"
                )
            
        if query.similarity_cutoff is not None and not (0 <= query.similarity_cutoff <= 3.0):
            raise HTTPException(status_code=422, detail="similarity_cutoff must be between 0 and 3.0")
    
        # Validate filter structure if provided
        if query.filters:
            if not isinstance(query.filters, dict):
                raise HTTPException(
                    status_code=422, 
                    detail="Filters must be a dictionary"
                )
            
            # Check for new structured format
            if "include" in query.filters or "exclude" in query.filters:
                # Validate include filters
                if "include" in query.filters and not isinstance(query.filters["include"], dict):
                    raise HTTPException(
                        status_code=422,
                        detail="Include filters must be a dictionary"
                    )
                
                # Validate exclude filters
                if "exclude" in query.filters and not isinstance(query.filters["exclude"], dict):
                    raise HTTPException(
                        status_code=422,
                        detail="Exclude filters must be a dictionary"
                    )
                
                # Check for unsupported fields
                supported_fields = {'categories', 'authors', 'published_date', 'doc_ids', 'title_keywords', 'abstract_keywords', 'text_type'}
                
                for filter_type in ["include", "exclude"]:
                    if filter_type in query.filters:
                        for field in query.filters[filter_type]:
                            if field not in supported_fields:
                                raise HTTPException(
                                    status_code=422,
                                    detail=f"Unsupported filter field: {field}. Supported fields: {', '.join(sorted(supported_fields))}"
                                )
        
        
        results = find_similar(
            paper_indexer,
            query=query.query.strip(),
            top_k=query.top_k,
            retrieve_k=query.retrieve_k,
            search_strategies=query.search_strategies,
            filters=query.filters,
            result_include_types=query.result_include_types
        )
        
        # Check for empty results
        if isinstance(results, dict):
            # Extended format
            if not results.get("retrieve_results"):
                logger.warning(f"No results found for query: {query.query}")
        elif not results:
            # Standard format
            logger.warning(f"No results found for query: {query.query}")
            return []  # Return empty list with 200 status for no results
        
        logger.info(f"Search completed successfully")
        return results
    except ValueError as e:
        # Handle validation errors from the service layer
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in similarity search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save_image/")
async def save_image_route(request: SaveImageRequest) -> ImageResponse:
    """Save an image to MinIO storage using AIgnite's image storage architecture.
    
    This endpoint stores images in the MinioImageDB with the specified object name.
    The object name follows the format: {doc_id}_{figure_id} as described in the 
    INDEX_PAPER_STORAGE_LOGIC.md documentation.
    
    The endpoint supports two input methods:
    - image_path: Path to an image file on the server
    - image_data: Raw image bytes (for direct upload)
    
    Args:
        request: SaveImageRequest containing object_name and either image_path or image_data
        
    Returns:
        ImageResponse with success status and message
        
    Raises:
        HTTPException: If indexer not initialized, validation fails, or save operation fails
    """
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    
    try:
        # Validate request parameters
        if not request.object_name or not request.object_name.strip():
            raise HTTPException(status_code=422, detail="Object name cannot be empty")
        
        if not request.image_path and not request.image_data:
            raise HTTPException(
                status_code=422, 
                detail="Either image_path or image_data must be provided"
            )
        
        if request.image_path and request.image_data:
            raise HTTPException(
                status_code=422,
                detail="Only one of image_path or image_data should be provided"
            )
        
        # Call the service function
        success = save_image(
            indexer=paper_indexer,
            object_name=request.object_name.strip(),
            image_path=request.image_path,
            image_data=request.image_data
        )
        
        if success:
            return ImageResponse(
                success=True,
                message=f"Image saved successfully with object_name: {request.object_name}",
                object_name=request.object_name.strip()
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save image with object_name: {request.object_name}"
            )
            
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving image with object_name {request.object_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")

@router.post("/store_images/")
async def store_images_route(request: StoreImagesRequest) -> StoreImagesResponse:
    """Store images from papers to MinIO storage using AIgnite's image storage architecture.
    
    This endpoint stores images from figure_chunks in papers to MinIO storage.
    The object name follows the format: {doc_id}_{figure_id} as described in the 
    INDEX_PAPER_STORAGE_LOGIC.md documentation.
    
    This endpoint supports two storage scenarios:
    1. **Integrated storage**: Images stored during index_papers with store_images=True
    2. **Independent storage**: Images stored separately after metadata storage
    
    Args:
        request: StoreImagesRequest containing docsets, indexing_status, and keep_temp_image parameters
        
    Returns:
        StoreImagesResponse with success status, message, and updated indexing status
        
    Raises:
        HTTPException: If indexer not initialized, validation fails, or storage operation fails
    """
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    
    try:
        # Convert DocSetList to List[DocSet]
        docsets = []
        for paper in request.docsets.docsets:
            # 修改figure_chunks的id格式，从title中提取下划线之后的部分
            modified_figure_chunks = []
            figure_counter = 1
            for chunk in paper.figure_chunks:
                # 从title中提取下划线之后的部分作为图片名称
                new_chunk_data = chunk.dict()
                if '_' in chunk.title:
                    # 提取下划线之后的部分，并添加.png扩展名
                    figure_name = chunk.title.split('_', 1)[1] + '.png'
                    new_chunk_data['id'] = figure_name
                else:
                    # 如果没有下划线，使用计数器
                    new_chunk_data['id'] = f"Figure{figure_counter}.png"
                modified_figure_chunks.append(FigureChunk(**new_chunk_data))
                figure_counter += 1
            
            docsets.append(DocSet(
                doc_id=paper.doc_id,
                title=paper.title,
                abstract=paper.abstract,
                authors=paper.authors,
                categories=paper.categories,
                published_date=paper.published_date,
                pdf_path=paper.pdf_path,
                HTML_path=paper.HTML_path,
                text_chunks=[TextChunk(**chunk.dict()) for chunk in paper.text_chunks],
                figure_chunks=modified_figure_chunks,
                table_chunks=[TableChunk(**chunk.dict()) for chunk in paper.table_chunks],
                metadata=paper.metadata or {},
                comments=paper.comments
            ))
        
        # Call the service function
        updated_indexing_status = store_images(
            indexer=paper_indexer,
            docsets=docsets,
            indexing_status=request.indexing_status,
            keep_temp_image=request.keep_temp_image
        )
        
        return StoreImagesResponse(
            success=True,
            message=f"Images stored successfully for {len(docsets)} papers",
            indexing_status=updated_indexing_status,
            papers_processed=len(docsets)
        )
            
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error storing images: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to store images: {str(e)}")

@router.post("/get_image/")
async def get_image_route(request: GetImageRequest) -> GetImageResponse:
    """Get an image from MinIO storage using AIgnite's image storage architecture.
    
    This endpoint retrieves images from the MinioImageDB with the specified image ID.
    
    Args:
        request: GetImageRequest containing image_id
        
    Returns:
        GetImageResponse with image data if found, otherwise error message
        
    Raises:
        HTTPException: If indexer not initialized or image retrieval fails
    """
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    
    try:
        # Validate request parameters
        if not request.image_id or not request.image_id.strip():
            raise HTTPException(status_code=422, detail="Image ID cannot be empty")
        
        # Call the service function
        image_data = get_image(
            indexer=paper_indexer,
            image_id=request.image_id.strip()
        )
        
        if image_data is not None:
            return GetImageResponse(
                success=True,
                message=f"Image retrieved successfully for image_id: {request.image_id}",
                image_data=image_data,
                image_id=request.image_id.strip()
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Image not found for image_id: {request.image_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image for {request.image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get image: {str(e)}")

@router.post("/get_image_storage_status/")
async def get_image_storage_status_route(request: GetImageStorageStatusRequest) -> GetImageStorageStatusResponse:
    """Get the image storage status for a specific document from the MetadataDB.
    
    This endpoint retrieves the image storage status for a document, showing which
    images have been stored and their current status.
    
    Args:
        request: GetImageStorageStatusRequest containing doc_id
        
    Returns:
        GetImageStorageStatusResponse with storage status information
        
    Raises:
        HTTPException: If indexer not initialized or status retrieval fails
    """
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    
    try:
        # Validate request parameters
        if not request.doc_id or not request.doc_id.strip():
            raise HTTPException(status_code=422, detail="Document ID cannot be empty")
        
        # Call the service function
        storage_status = get_image_storage_status(
            indexer=paper_indexer,
            doc_id=request.doc_id.strip()
        )
        
        if storage_status is not None:
            return GetImageStorageStatusResponse(
                success=True,
                message=f"Image storage status retrieved successfully for doc_id: {request.doc_id}",
                storage_status=storage_status,
                doc_id=request.doc_id.strip()
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Image storage status not found for doc_id: {request.doc_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image storage status for {request.doc_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get image storage status: {str(e)}")

@router.post("/save_vectors/")
async def save_vectors_route(request: SaveVectorsRequest) -> SaveVectorsResponse:
    """Store vectors from papers to FAISS storage using AIgnite's vector storage architecture.
    
    This endpoint stores vectors from papers to FAISS storage.
    The vectors are created from paper title and abstract following the format: {title} . {abstract}
    The vector_db_id follows the format: {doc_id}_abstract as described in the 
    INDEX_PAPER_STORAGE_LOGIC.md documentation.
    
    This endpoint supports two storage scenarios:
    1. **Integrated storage**: Vectors stored during index_papers with vector_db configured
    2. **Independent storage**: Vectors stored separately after metadata storage
    
    Args:
        request: SaveVectorsRequest containing docsets and indexing_status parameters
        
    Returns:
        SaveVectorsResponse with success status, message, and updated indexing status
        
    Raises:
        HTTPException: If indexer not initialized, validation fails, or storage operation fails
    """
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    
    try:
        # Convert DocSetList to List[DocSet]
        docsets = []
        for paper in request.docsets.docsets:
            docsets.append(DocSet(
                doc_id=paper.doc_id,
                title=paper.title,
                abstract=paper.abstract,
                authors=paper.authors,
                categories=paper.categories,
                published_date=paper.published_date,
                pdf_path=paper.pdf_path,
                HTML_path=paper.HTML_path,
                text_chunks=[TextChunk(**chunk.dict()) for chunk in paper.text_chunks],
                figure_chunks=[FigureChunk(**chunk.dict()) for chunk in paper.figure_chunks],
                table_chunks=[TableChunk(**chunk.dict()) for chunk in paper.table_chunks],
                metadata=paper.metadata or {},
                comments=paper.comments
            ))
        
        # Call the service function

        updated_indexing_status = save_vectors(
            indexer=paper_indexer,
            docsets=docsets,
            indexing_status=request.indexing_status
        )
        
        return SaveVectorsResponse(
            success=True,
            message=f"Vectors stored successfully for {len(docsets)} papers",
            indexing_status=updated_indexing_status,
            papers_processed=len(docsets)
        )
            
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error storing vectors: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to store vectors: {str(e)}")

@router.get("/get_all_metadata_doc_ids/")
async def get_all_metadata_doc_ids_route() -> GetAllDocIdsResponse:
    """Get all document IDs from the MetadataDB.
    
    This endpoint retrieves all document IDs stored in the PostgreSQL metadata database.
    Useful for database consistency checks, identifying all indexed papers, and comparing
    with vector database contents.
    
    Returns:
        GetAllDocIdsResponse with list of document IDs and count
        
    Raises:
        HTTPException: If indexer not initialized, metadata database unavailable, or retrieval fails
    """
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    
    try:
        # Call the service function
        doc_ids = get_all_metadata_doc_ids(indexer=paper_indexer)
        
        return GetAllDocIdsResponse(
            success=True,
            message=f"Retrieved {len(doc_ids)} document IDs from metadata database",
            doc_ids=doc_ids,
            count=len(doc_ids),
            database_type="metadata"
        )
            
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting all doc_ids from metadata database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get all doc_ids from metadata database: {str(e)}")

@router.get("/get_all_vector_doc_ids/")
async def get_all_vector_doc_ids_route() -> GetAllDocIdsResponse:
    """Get all unique document IDs from the VectorDB.
    
    This endpoint retrieves all unique document IDs stored in the FAISS vector database.
    Useful for database consistency checks, comparing with metadata database, and
    identifying documents that have vector representations.
    
    Returns:
        GetAllDocIdsResponse with list of unique document IDs and count
        
    Raises:
        HTTPException: If indexer not initialized, vector database unavailable, or retrieval fails
    """
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    
    try:
        # Call the service function
        doc_ids = get_all_vector_doc_ids(indexer=paper_indexer)
        
        return GetAllDocIdsResponse(
            success=True,
            message=f"Retrieved {len(doc_ids)} unique document IDs from vector database",
            doc_ids=doc_ids,
            count=len(doc_ids),
            database_type="vector"
        )
            
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting all doc_ids from vector database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get all doc_ids from vector database: {str(e)}")

@router.post("/delete_vector_document/")
async def delete_vector_document_route(request: DeleteVectorDocumentRequest) -> DeleteVectorDocumentResponse:
    """Delete all vectors for a document from the VectorDB.
    
    This endpoint removes all vector representations associated with a document ID
    from the FAISS vector database. It is useful for:
    - Database maintenance and cleanup
    - Removing outdated or incorrect vector data
    - Testing database synchronization scenarios
    
    The endpoint will:
    1. Delete all vectors associated with the doc_id
    2. Save the vector database to persist changes
    3. Return the operation status
    
    Args:
        request: DeleteVectorDocumentRequest containing doc_id
        
    Returns:
        DeleteVectorDocumentResponse with operation status
        
    Raises:
        HTTPException: If indexer not initialized, vector database unavailable, or deletion fails
    """
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    
    try:
        # Validate request
        if not request.doc_id or not request.doc_id.strip():
            raise HTTPException(status_code=422, detail="Document ID cannot be empty")
        
        doc_id = request.doc_id.strip()
        
        # Call the service function
        success = delete_vector_document(indexer=paper_indexer, doc_id=doc_id)
        
        if success:
            return DeleteVectorDocumentResponse(
                success=True,
                message=f"Successfully deleted vectors for document: {doc_id}",
                doc_id=doc_id,
                vectors_deleted=True
            )
        else:
            return DeleteVectorDocumentResponse(
                success=False,
                message=f"No vectors found for document: {doc_id}",
                doc_id=doc_id,
                vectors_deleted=False
            )
            
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting vectors for document {request.doc_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete vectors: {str(e)}")

@router.put("/update_papers_blog/")
async def update_papers_blog_route(request: Dict[str, Any]) -> Dict[str, Any]:
    """Update blog field in papers table for multiple papers"""
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    
    try:
        from sqlalchemy import text
        
        papers_data = request.get("papers", [])
        if not papers_data:
            return {
                "message": "No papers provided",
                "updated_count": 0,
                "total_requested": 0
            }
        
        updated_count = 0
        
        # Get database connection from indexer
        if paper_indexer.metadata_db is None:
            raise HTTPException(status_code=503, detail="Metadata database not initialized")
        
        # Use the metadata_db connection
        session = paper_indexer.metadata_db.Session()
        try:
            for paper in papers_data:
                paper_id = paper.get("paper_id")
                blog_content = paper.get("blog_content")
                
                if paper_id and blog_content:
                    # Update the blog field in papers table
                    update_query = text("""
                        UPDATE papers 
                        SET blog = :blog_content 
                        WHERE doc_id = :paper_id
                    """)
                    
                    result = session.execute(update_query, {
                        "blog_content": blog_content,
                        "paper_id": paper_id
                    })
                    
                    if result.rowcount > 0:
                        updated_count += 1
                        logger.info(f"Updated blog field for paper {paper_id}")
                    else:
                        logger.warning(f"No paper found with doc_id: {paper_id}")
                else:
                    logger.warning(f"Skipping paper {paper_id} - missing paper_id or blog content")
            
            session.commit()
            logger.info(f"Successfully updated blog fields for {updated_count} papers")
            
            return {
                "message": f"Successfully updated blog fields for {updated_count} papers",
                "updated_count": updated_count,
                "total_requested": len(papers_data)
            }
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Failed to update papers blog field: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update papers blog field: {str(e)}")


