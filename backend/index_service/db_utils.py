from typing import Tuple, Dict, Any, Optional
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
import logging
import os

from AIgnite.db.metadata_db import MetadataDB, Base
from AIgnite.db.vector_db import VectorDB
from AIgnite.db.image_db import MinioImageDB
from minio import Minio
from minio.error import S3Error

# Import shared configuration loader
from backend.shared.config_utils import load_config as shared_load_config

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

# Global database instances for cleanup
_vector_db_instance: Optional[VectorDB] = None

#DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "configs/app_config.yaml"

# Keep backward compatibility alias - use shared load_config with service="index"
def load_config(config_path: Optional[str] = None, set_env: bool = True, display_storage_info: bool = False) -> Dict[str, Any]:
    """
    Load index service configuration.

    This is a wrapper around the shared config loader for backward compatibility.
    For new code, consider using backend.shared.config_utils.load_config directly.
    """
    return shared_load_config(config_path, service="index", set_env=set_env, display_storage_info=display_storage_info)


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
    vector_dim: int = 768
) -> Tuple[VectorDB, MetadataDB, MinioImageDB]:
    """Initialize all required databases using configuration.
    
    Args:
        config: Configuration dictionary containing database settings
        vector_dim: Dimension of the embedding vectors (default: 768 for BGE base model)
        
    Returns:
        Tuple of (VectorDB, MetadataDB, MinioImageDB) instances
        
    Raises:
        RuntimeError: If database initialization fails
        ValueError: If configuration is invalid or missing required fields
    """
    global _vector_db_instance
    logger.debug("Loading configuration and initializing databases...")
    
    # Load configuration if not provided
    if config is None:
        raise ValueError("No configuration provided")
    
    # Handle vector database initialization
    if 'vector_db' in config:
        vector_db_path = config['vector_db']['db_path']
        if 'db_path' not in config['vector_db']:
            raise ValueError("Vector database path (db_path) must be specified in configuration")
        if 'model_name' not in config['vector_db']:
            raise ValueError("Vector database model name must be specified in configuration")
        # Ensure vector database directory exists
        os.makedirs(os.path.dirname(vector_db_path), exist_ok=True)
        
        # Initialize vector database with proper dimension
        _vector_db_instance = VectorDB(
            db_path=vector_db_path,
            model_name=config['vector_db']['model_name'],
            vector_dim=vector_dim
        )
        logger.debug(f"Vector database initialized with model {config['vector_db']['model_name']}")
    else:
        _vector_db_instance = None
    
    # Handle vector database initialization
    if 'db_url' not in config['metadata_db']:
        raise ValueError("Metadata database URL must be specified in configuration")
    # Set up metadata database engine
    db_url = config['metadata_db']['db_url']
    engine = create_engine(db_url)
    
    # Handle metadata database initialization
    tables_exist = check_tables_exist(engine)
    if tables_exist:
        logger.info("Using existing tables in metadata database...")
    else:
        logger.info("Tables don't exist. Creating new tables in metadata database...")
        Base.metadata.create_all(engine)
    logger.info("database tables checked/created successfully")
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

    if 'minio_db' in config:
        required_minio_fields = ['endpoint', 'access_key', 'secret_key', 'bucket_name']
        missing_fields = [f for f in required_minio_fields if f not in config['minio_db']]
        if missing_fields:
            raise ValueError(f"Missing required MinIO configuration fields: {', '.join(missing_fields)}")
        # Initialize MinIO image database with proper error handling
        try:
            minio_config = config['minio_db']
            image_db = MinioImageDB(
                endpoint=minio_config['endpoint'],
                access_key=minio_config['access_key'],
                secret_key=minio_config['secret_key'],
                bucket_name=minio_config['bucket_name'],
                secure=minio_config.get('secure', False)
            )
            logger.debug("MinIO image database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MinIO image database: {str(e)}")
    else:
        image_db = None
    
    return _vector_db_instance, metadata_db, image_db
