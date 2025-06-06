### service.py
from typing import List, Dict, Any, Tuple, Optional
from .db_init import init_databases
from AIgnite.index.paper_indexer import PaperIndexer
from AIgnite.data.docset import DocSet
import logging

# Set up logging
logger = logging.getLogger(__name__)

def init_db(config: Dict[str, Any], recreate_databases: bool = True) -> Tuple[Any, Any, Any]:
    """Initialize the databases.
    
    Args:
        config: Configuration dictionary containing database settings
        recreate_databases: If True, will drop and recreate metadata tables. Defaults to True.
    
    Returns:
        Tuple of (vector_db, metadata_db, image_db)
        
    Raises:
        ValueError: If configuration is invalid
        RuntimeError: If database initialization fails for other reasons
    """
    try:
        dbs = init_databases(config=config, recreate_databases=recreate_databases)
        logger.info("Databases initialized successfully")
        return dbs
    except ValueError as e:
        logger.error(f"Invalid configuration: {str(e)}")
        raise  # Re-raise ValueError as is
    except Exception as e:
        error_msg = f"Failed to initialize databases: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

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
    """Index a list of papers into the database."""
    try:
        indexer.index_papers(docsets)
        return True
    except Exception as e:
        logger.error(f"Failed to index papers: {str(e)}")
        return False

def get_metadata(indexer: PaperIndexer, doc_id: str) -> Dict[str, Any]:
    """Get metadata for a specific paper."""
    try:
        return indexer.get_paper_metadata(doc_id)
    except Exception as e:
        logger.error(f"Failed to get metadata for {doc_id}: {str(e)}")
        return {}

def find_similar(
    indexer: PaperIndexer,
    query: str,
    top_k: int = 5,
    cutoff: float = 0.5,
    strategy_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Find papers similar to the query.
    
    Args:
        indexer: PaperIndexer instance
        query: Search query string
        top_k: Number of results to return
        cutoff: Minimum similarity score to include in results
        strategy_type: Optional search strategy to use ('vector', 'tf-idf', 'hybrid')
        
    Returns:
        List of dictionaries containing paper information and similarity scores
    """
    try:
        return indexer.find_similar_papers(
            query=query,
            top_k=top_k,
            similarity_cutoff=cutoff,
            strategy_type=strategy_type
        )
    except Exception as e:
        logger.error(f"Failed to find similar papers: {str(e)}")
        return []


