from typing import Tuple, Dict, Any, Optional
from sqlalchemy import create_engine, inspect
from AIgnite.db.metadata_db import MetadataDB, Base
from AIgnite.db.vector_db import VectorDB
from AIgnite.db.image_db import MinioImageDB
from .config import load_config
import logging
import os
import atexit

# Set up logging
logger = logging.getLogger(__name__)

# Global database instances for cleanup
_vector_db_instance: Optional[VectorDB] = None

def cleanup_databases():
    """Cleanup function to properly close database connections."""
    global _vector_db_instance
    if _vector_db_instance:
        try:
            _vector_db_instance.save()  # Save any pending changes
            _vector_db_instance.__del__()  # Cleanup embedding model
        except Exception as e:
            logger.error(f"Error during vector database cleanup: {str(e)}")
    _vector_db_instance = None

# Register cleanup function
atexit.register(cleanup_databases)

def check_tables_exist(engine) -> bool:
    """Check if all required tables exist in the database.
    
    Args:
        engine: SQLAlchemy engine instance
        
    Returns:
        bool: True if all required tables exist, False otherwise
    """
    inspector = inspect(engine)
    required_tables = {table.__tablename__ for table in Base.__subclasses__()}
    existing_tables = set(inspector.get_table_names())
    return required_tables.issubset(existing_tables)

def init_databases(
    config: Dict[str, Any],
    recreate_databases: bool = False,
    vector_dim: int = 768
) -> Tuple[VectorDB, MetadataDB, MinioImageDB]:
    """Initialize all required databases using configuration.
    
    Args:
        config: Configuration dictionary containing database settings
        recreate_databases: If True, will recreate all databases.
                          If False, will use existing databases if they exist, or create new ones if they don't.
        vector_dim: Dimension of the embedding vectors (default: 768 for BGE base model)
        
    Returns:
        Tuple of (VectorDB, MetadataDB, MinioImageDB) instances
        
    Raises:
        RuntimeError: If database initialization fails
        ValueError: If configuration is invalid or missing required fields
    """
    global _vector_db_instance
    logger.debug("Loading configuration and initializing databases...")
    
    try:
        # Load configuration if not provided
        if config is None:
            config = load_config()
        
        # Validate configurations
        if 'db_path' not in config['vector_db']:
            raise ValueError("Vector database path (db_path) must be specified in configuration")
        if 'model_name' not in config['vector_db']:
            raise ValueError("Vector database model name must be specified in configuration")
        if 'db_url' not in config['metadata_db']:
            raise ValueError("Metadata database URL must be specified in configuration")
        required_minio_fields = ['endpoint', 'access_key', 'secret_key', 'bucket_name']
        missing_fields = [f for f in required_minio_fields if f not in config['minio_db']]
        if missing_fields:
            raise ValueError(f"Missing required MinIO configuration fields: {', '.join(missing_fields)}")
            
        # Handle vector database initialization
        vector_db_path = config['vector_db']['db_path']
        if recreate_databases and os.path.exists(f"{vector_db_path}.index"):
            logger.info("Removing existing vector database files...")
            os.remove(f"{vector_db_path}.index")
            os.remove(f"{vector_db_path}.entries")
            
        # Ensure vector database directory exists
        os.makedirs(os.path.dirname(vector_db_path), exist_ok=True)
            
        # Initialize vector database with proper dimension
        _vector_db_instance = VectorDB(
            db_path=vector_db_path,
            model_name=config['vector_db']['model_name'],
            vector_dim=vector_dim
        )
        logger.debug(f"Vector database initialized with model {config['vector_db']['model_name']}")
        
        # Set up metadata database engine
        db_url = config['metadata_db']['db_url']
        engine = create_engine(db_url)
        
        # Handle metadata database initialization
        if recreate_databases:
            logger.info("Recreating all tables in metadata database...")
            Base.metadata.drop_all(engine)
            Base.metadata.create_all(engine)
        else:
            tables_exist = check_tables_exist(engine)
            if tables_exist:
                logger.info("Using existing tables in metadata database...")
            else:
                logger.info("Tables don't exist. Creating new tables in metadata database...")
                Base.metadata.create_all(engine)
        
        # Initialize metadata database
        try:
            metadata_db = MetadataDB(db_path=db_url)
            logger.debug("Metadata database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize metadata database: {str(e)}")
            if "FTS" in str(e):
                logger.warning("Full-text search initialization failed, but database is still usable")
            else:
                raise
        
        # Initialize MinIO image database with proper error handling
        try:
            image_db = MinioImageDB(
                endpoint=config['minio_db']['endpoint'],
                access_key=config['minio_db']['access_key'],
                secret_key=config['minio_db']['secret_key'],
                bucket_name=config['minio_db']['bucket_name'],
                secure=config['minio_db'].get('secure', False)
            )
            logger.debug(f"MinIO image database initialized with endpoint {config['minio_db']['endpoint']}")
        except Exception as e:
            logger.error(f"Failed to initialize MinIO database: {str(e)}")
            raise RuntimeError(f"MinIO initialization failed: {str(e)}")
        
        return _vector_db_instance, metadata_db, image_db
        
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize databases: {str(e)}")
        raise RuntimeError(f"Database initialization failed: {str(e)}") 