### service.py
from typing import List, Dict, Any, Tuple, Optional
from AIgnite.index.paper_indexer import PaperIndexer
from AIgnite.data.docset import DocSet
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Global indexer instance
paper_indexer = PaperIndexer()

def create_indexer(vector_db, metadata_db, image_db) -> PaperIndexer:
    """Create a PaperIndexer instance with the given databases."""
    try:
        return PaperIndexer(
            vector_db=vector_db,
            metadata_db=metadata_db,
            image_db=image_db
        )
    except Exception as e:
        error_msg = f"Failed to create indexer: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

def index_papers(indexer: PaperIndexer, docsets: List[DocSet]) -> bool:
    """Index a list of papers into the database using AIgnite's parallel storage architecture.
    
    This function stores papers across multiple databases:
    - MetadataDB (PostgreSQL): Paper metadata, PDF data, and text chunks
    - VectorDB (FAISS): Vector embeddings for semantic search
    - MinioImageDB (MinIO): Image data from figures
    
    Args:
        indexer: PaperIndexer instance with configured databases
        docsets: List of DocSet objects containing paper information
        
    Returns:
        bool: True if indexing completed successfully, False otherwise
    """
    try:
        indexing_status = indexer.index_papers(docsets)
        # Check if all papers were indexed successfully
        all_successful = all(
            status.get("metadata", False) or status.get("vectors", False) or status.get("images", False)
            for status in indexing_status.values()
        )
        return all_successful
    except Exception as e:
        logger.error(f"Failed to index papers: {str(e)}")
        return False

def get_metadata(indexer: PaperIndexer, doc_id: str) -> Dict[str, Any]:
    """Get metadata for a specific paper from the MetadataDB.
    
    Args:
        indexer: PaperIndexer instance with configured databases
        doc_id: The document ID of the paper
        
    Returns:
        Dictionary containing paper metadata or empty dict if not found
    """
    try:
        return indexer.get_paper_metadata(doc_id)
    except Exception as e:
        logger.error(f"Failed to get metadata for {doc_id}: {str(e)}")
        return {}

def find_similar(
    indexer: PaperIndexer,
    query: str,
    top_k: int = 5,
    search_strategies: Optional[List[Tuple[str, float]]] = None,
    filters: Optional[Dict[str, Any]] = None,
    result_include_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Find papers similar to the query using AIgnite's modular search architecture.
    
    This function leverages AIgnite's advanced search capabilities including:
    - Multiple search strategies (vector, tf-idf, hybrid)
    - Advanced filtering with include/exclude structure
    - Text type filtering (abstract, chunk, combined)
    - Result combination with multiple data types
    
    Args:
        indexer: PaperIndexer instance with configured databases
        query: Search query string
        top_k: Number of results to return
        search_strategies: Optional list of search strategies and thresholds:
            - Format: [('vector', 0.5), ('tf-idf', 0.1)]
            - 'vector': Semantic search using embeddings
            - 'tf-idf': Keyword-based search using PostgreSQL FTS
        filters: Optional filters with include/exclude structure:
            - include: Must match conditions
            - exclude: Must not match conditions
            - Supported fields: categories, authors, published_date, doc_ids, 
              title_keywords, abstract_keywords, text_type
        result_include_types: Optional list of data types to include:
            - 'metadata': Paper metadata (title, abstract, authors, etc.)
            - 'text_chunks': Text chunk content
            - 'search_parameters': Search parameters and scores
            - 'full_text': Complete text content
            - 'images': Image data
        
    Returns:
        List of dictionaries containing paper information, similarity scores, and requested data types
        
    Raises:
        ValueError: If input parameters are invalid or search fails
    """
    try:
        # Convert string-based search strategies to SearchStrategy objects
        if search_strategies:
            # Set the search strategy using the provided strategies
            indexer.set_search_strategy(search_strategies)
        
        return indexer.find_similar_papers(
            query=query,
            top_k=top_k,
            filters=filters,
            search_strategies=search_strategies,
            result_include_types=result_include_types
        )
    except Exception as e:
        #logger.error(f"Failed to find similar papers: {str(e)}")
        raise ValueError(f"Failed to find similar papers, please verify the input parameters: {str(e)}")
        #return []


