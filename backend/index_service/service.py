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

def index_papers(indexer: PaperIndexer, docsets: List[DocSet], store_images: bool = False, keep_temp_image: bool = False) -> bool:
    """Index a list of papers into the database using AIgnite's parallel storage architecture.
    
    This function stores papers across multiple databases:
    - MetadataDB (PostgreSQL): Paper metadata, PDF data, and text chunks
    - VectorDB (FAISS): Vector embeddings for semantic search
    - MinioImageDB (MinIO): Image data from figures
    
    Args:
        indexer: PaperIndexer instance with configured databases
        docsets: List of DocSet objects containing paper information
        store_images: Whether to store images to MinIO (default: False)
        keep_temp_image: If False, delete temporary image files after successful storage (default: False)
        
    Returns:
        bool: True if indexing completed successfully, False otherwise
    """
    try:
        indexing_status = indexer.index_papers(docsets, store_images=store_images, keep_temp_image=keep_temp_image)
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


def get_image(indexer: PaperIndexer, image_id: str) -> Optional[str]:
    """Get an image from MinIO storage using AIgnite's image storage architecture.
    
    This function retrieves images from the MinioImageDB with the specified image ID.
    
    Args:
        indexer: PaperIndexer instance with configured databases
        image_id: Image ID to retrieve
        
    Returns:
        Base64 encoded image data if found, otherwise None
    """
    try:
        import base64
        image_bytes = indexer._get_image(image_id)
        if image_bytes is not None:
            return base64.b64encode(image_bytes).decode('utf-8')
        return None
    except Exception as e:
        logger.error(f"Failed to get image for {image_id}: {str(e)}")
        return None


def get_image_storage_status(indexer: PaperIndexer, doc_id: str) -> Optional[Dict[str, Any]]:
    """Get the image storage status for a specific document from the MetadataDB.
    
    Args:
        indexer: PaperIndexer instance with configured databases
        doc_id: Document ID to retrieve
        
    Returns:
        Dictionary with storage status if found, None if document not found
    """
    try:
        status = indexer.get_image_storage_status_for_doc(doc_id)
        # If the status is empty (document not found), return None to trigger 404
        if not status:
            return None
        return status
    except Exception as e:
        logger.error(f"Failed to get image storage status for {doc_id}: {str(e)}")
        return None

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

def save_image(indexer: PaperIndexer, object_name: str, image_path: str = None, image_data: str = None) -> bool:
    """Save an image to MinIO storage using AIgnite's image storage architecture.
    
    This function stores images in the MinioImageDB with the specified object name.
    The object name follows the format: {doc_id}_{figure_id} as described in the 
    INDEX_PAPER_STORAGE_LOGIC.md documentation.
    
    Args:
        indexer: PaperIndexer instance with configured databases
        object_name: Object name to use for storage in MinIO (format: {doc_id}_{figure_id})
        image_path: Path to image file (mutually exclusive with image_data)
        image_data: Base64 encoded image data (mutually exclusive with image_path)
        
    Returns:
        bool: True if image was saved successfully, False otherwise
        
    Raises:
        ValueError: If input parameters are invalid
        RuntimeError: If image saving fails
    """
    try:
        # Validate input parameters
        if not object_name or not object_name.strip():
            raise ValueError("Object name cannot be empty")
        
        if not image_path and not image_data:
            raise ValueError("Either image_path or image_data must be provided")
        
        if image_path and image_data:
            raise ValueError("Only one of image_path or image_data should be provided")
        
        # Check if image_db is available
        if indexer.image_db is None:
            raise RuntimeError("Image database is not initialized")
        
        # Decode base64 image data if provided
        decoded_image_data = None
        if image_data:
            try:
                import base64
                decoded_image_data = base64.b64decode(image_data)
            except Exception as e:
                raise ValueError(f"Invalid base64 image data: {str(e)}")
        
        # Call the image_db save_image method directly
        success = indexer.image_db.save_image(
            object_name=object_name.strip(),
            image_path=image_path,
            image_data=decoded_image_data
        )
        
        if not success:
            raise RuntimeError(f"Failed to save image with object_name: {object_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to save image with object_name {object_name}: {str(e)}")
        raise

def store_images(indexer: PaperIndexer, docsets: List[DocSet], indexing_status: Dict[str, Dict[str, bool]] = None, keep_temp_image: bool = False) -> Dict[str, Dict[str, bool]]:
    """Store images from papers to MinIO storage using AIgnite's image storage architecture.
    
    This function stores images from figure_chunks in papers to MinIO storage.
    The object name follows the format: {doc_id}_{figure_id} as described in the 
    INDEX_PAPER_STORAGE_LOGIC.md documentation.
    
    Args:
        indexer: PaperIndexer instance with configured databases
        docsets: List of DocSet objects containing papers with figure_chunks
        indexing_status: Optional dictionary to track indexing status for each paper
        keep_temp_image: If False, delete temporary image files after successful storage (default: False)
        
    Returns:
        Dictionary mapping doc_ids to their indexing status for each database type
        
    Raises:
        RuntimeError: If indexer is not initialized or image storage fails
    """
    try:
        # Check if indexer is initialized
        if indexer is None:
            raise RuntimeError("Indexer not initialized")
        
        # Check if image_db is available
        if indexer.image_db is None:
            raise RuntimeError("Image database is not initialized")
        
        # Call the indexer's store_images method
        updated_indexing_status = indexer.store_images(
            papers=docsets,
            indexing_status=indexing_status,
            keep_temp_image=keep_temp_image
        )
        
        return updated_indexing_status
        
    except Exception as e:
        logger.error(f"Failed to store images: {str(e)}")
        raise RuntimeError(f"Failed to store images: {str(e)}")




