from fastapi import APIRouter, HTTPException, Query, Body
from .models import CustomerQuery
from AIgnite.data.docset import DocSet, TextChunk, FigureChunk, TableChunk, ChunkType, DocSetList
from typing import Dict, Any, List, Optional
from .service import paper_indexer, index_papers, get_metadata, find_similar, create_indexer
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
async def index_papers_route(docset_list: DocSetList) -> Dict[str, str]:
    """Index a list of papers using AIgnite's parallel storage architecture.
    
    This endpoint stores papers across multiple databases:
    - MetadataDB (PostgreSQL): Paper metadata, PDF data, and text chunks
    - VectorDB (FAISS): Vector embeddings for semantic search
    - MinioImageDB (MinIO): Image data from figures
    
    The indexing process uses parallel storage to maximize performance and
    provides detailed status reporting for each database type.
    """
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    
    try:
        docsets = []
        for paper in docset_list.docsets:
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
        success = index_papers(paper_indexer, docsets)
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
async def find_similar_route(query: CustomerQuery) -> List[Dict[str, Any]]:
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
    """
    if paper_indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    
    try:
        # Validate parameters
        if not query.query or not query.query.strip():
            raise HTTPException(status_code=422, detail="Query string cannot be empty")
        
        if query.top_k is not None and query.top_k <= 0:
            raise HTTPException(status_code=422, detail="top_k must be a positive integer")
            
        if query.similarity_cutoff is not None and not (0 <= query.similarity_cutoff <= 1):
            raise HTTPException(status_code=422, detail="similarity_cutoff must be between 0 and 1")
    
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
            search_strategies=query.search_strategies,
            filters=query.filters,
            result_include_types=query.result_include_types
        )
        if not results:
            logger.warning(f"No results found for query: {query.query}")
            return []  # Return empty list with 200 status for no results
        return results
    except ValueError as e:
        # Handle validation errors from the service layer
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in similarity search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
