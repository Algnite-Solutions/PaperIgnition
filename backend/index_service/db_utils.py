from typing import Tuple, Dict, Any, Optional
from pathlib import Path
from sqlalchemy import create_engine, inspect
import logging
import os
import yaml

from AIgnite.db.metadata_db import MetadataDB, Base
from AIgnite.db.vector_db import VectorDB
from AIgnite.db.image_db import MinioImageDB


# Set up logging
logger = logging.getLogger(__name__)

# Global database instances for cleanup
_vector_db_instance: Optional[VectorDB] = None

#DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "configs/app_config.yaml"

def load_config(config_path: Optional[str] = None, set_env: bool = True) -> Dict[str, Any]:
    """Enhanced configuration loading function with environment variable support.
    
    Args:
        config_path: Path to config.yaml file. If None, uses environment variable or default path.
        set_env: Whether to set configuration values as environment variables.
        
    Returns:
        Dictionary containing configuration parameters
        
    Raises:
        FileNotFoundError: If given config path but config file not found
        ValueError: If required configuration sections are missing or if loading fails
    """
    # Get config path from parameter, environment variable, or default
    if not config_path:
        config_path = os.environ.get("PAPERIGNITION_CONFIG")
        host = os.environ.get('PAPERIGNITION_INDEX_SERVICE_HOST')
        if host:
            logger.debug(f"Using config path from environment variable: {config_path}")
            return _load_config_from_environment()
        else:
            logger.warning("No config path provided and PAPERIGNITION_CONFIG environment variable not set")
            raise ValueError("No config path provided and PAPERIGNITION_CONFIG environment variable not set")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            full_config = yaml.safe_load(f)
            config = full_config["INDEX_SERVICE"]
        
        # Validate required sections for index service
        required_sections = ['vector_db', 'metadata_db', 'minio_db']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required section '{section}' in config.yaml")
        
        # Validate database configurations
        if 'model_name' not in config['vector_db']:
            raise ValueError("Missing 'model_name' in vector_db configuration")
            
        if 'db_url' not in config['metadata_db']:
            raise ValueError("Missing 'db_url' in metadata_db configuration")
        
        # Validate MinIO configuration
        minio_required = ['endpoint', 'access_key', 'secret_key', 'bucket_name']
        for param in minio_required:
            if param not in config['minio_db']:
                raise ValueError(f"Missing required MinIO parameter '{param}' in config.yaml")
        
        # Set environment variables if requested
        if set_env:
            logger.debug('Setting environment variables from loaded configuration')
            set_config_environment_variables(config)
        
        logger.info(f"Successfully loaded configuration from file: {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise ValueError(f"Error loading config: {str(e)}")

def _load_config_from_environment(set_env: bool = True) -> Dict[str, Any]:
    """Load configuration from environment variables.
    
    Args:
        set_env: Whether to set configuration values as environment variables.
        
    Returns:
        Dictionary containing configuration parameters from environment variables
        
    Raises:
        ValueError: If required configuration sections are missing
    """
    logger.info("Loading configuration from environment variables")
    
    # Initialize config structure
    config = {
        'vector_db': {},
        'metadata_db': {},
        'minio_db': {}
    }
    
    # Load INDEX_SERVICE host
    host = os.environ.get('PAPERIGNITION_INDEX_SERVICE_HOST')
    if host:
        config['host'] = host
    
    # Load vector database configuration
    vector_db = config['vector_db']
    vector_db['model_name'] = os.environ.get('PAPERIGNITION_VECTOR_DB_MODEL')
    vector_db['vector_dim'] = int(os.environ.get('PAPERIGNITION_VECTOR_DB_DIM', '768'))
    vector_db['db_path'] = os.environ.get('PAPERIGNITION_VECTOR_DB_PATH')
    
    # Load metadata database configuration
    metadata_db = config['metadata_db']
    metadata_db['db_url'] = os.environ.get('PAPERIGNITION_METADATA_DB_URL')
    
    # Load MinIO configuration
    minio_db = config['minio_db']
    minio_db['endpoint'] = os.environ.get('PAPERIGNITION_MINIO_ENDPOINT')
    minio_db['access_key'] = os.environ.get('PAPERIGNITION_MINIO_ACCESS_KEY')
    minio_db['secret_key'] = os.environ.get('PAPERIGNITION_MINIO_SECRET_KEY')
    minio_db['bucket_name'] = os.environ.get('PAPERIGNITION_MINIO_BUCKET')
    secure_str = os.environ.get('PAPERIGNITION_MINIO_SECURE', 'false')
    minio_db['secure'] = secure_str.lower() in ('true', '1', 'yes')
    
    # Validate required sections for index service
    required_sections = ['vector_db', 'metadata_db', 'minio_db']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required section '{section}' in environment configuration")
    
    # Validate database configurations
    if not vector_db.get('model_name'):
        raise ValueError("Missing 'PAPERIGNITION_VECTOR_DB_MODEL' environment variable")
        
    if not metadata_db.get('db_url'):
        raise ValueError("Missing 'PAPERIGNITION_METADATA_DB_URL' environment variable")
    
    # Validate MinIO configuration
    minio_required = ['endpoint', 'access_key', 'secret_key', 'bucket_name']
    for param in minio_required:
        if not minio_db.get(param):
            raise ValueError(f"Missing required MinIO environment variable 'PAPERIGNITION_MINIO_{param.upper()}'")
    
    logger.info("Successfully loaded configuration from environment variables")
    return config

def set_config_environment_variables(config: Dict[str, Any]) -> None:
    """Set configuration values as environment variables for other modules to access.
    
    Args:
        config: Configuration dictionary to set as environment variables
    """
    try:
        # Set INDEX_SERVICE host
        if 'host' in config:
            os.environ['PAPERIGNITION_INDEX_SERVICE_HOST'] = str(config['host'])
        
        # Set vector database configuration
        if 'vector_db' in config:
            vector_db = config['vector_db']
            if 'model_name' in vector_db:
                os.environ['PAPERIGNITION_VECTOR_DB_MODEL'] = str(vector_db['model_name'])
            if 'vector_dim' in vector_db:
                os.environ['PAPERIGNITION_VECTOR_DB_DIM'] = str(vector_db['vector_dim'])
            if 'db_path' in vector_db:
                os.environ['PAPERIGNITION_VECTOR_DB_PATH'] = str(vector_db['db_path'])
        
        # Set metadata database configuration
        if 'metadata_db' in config:
            metadata_db = config['metadata_db']
            if 'db_url' in metadata_db:
                os.environ['PAPERIGNITION_METADATA_DB_URL'] = str(metadata_db['db_url'])
        
        # Set MinIO configuration
        if 'minio_db' in config:
            minio_db = config['minio_db']
            if 'endpoint' in minio_db:
                os.environ['PAPERIGNITION_MINIO_ENDPOINT'] = str(minio_db['endpoint'])
            if 'access_key' in minio_db:
                os.environ['PAPERIGNITION_MINIO_ACCESS_KEY'] = str(minio_db['access_key'])
            if 'secret_key' in minio_db:
                os.environ['PAPERIGNITION_MINIO_SECRET_KEY'] = str(minio_db['secret_key'])
            if 'bucket_name' in minio_db:
                os.environ['PAPERIGNITION_MINIO_BUCKET'] = str(minio_db['bucket_name'])
            if 'secure' in minio_db:
                os.environ['PAPERIGNITION_MINIO_SECURE'] = str(minio_db['secure'])
        
        logger.debug("Configuration environment variables set successfully")
        
    except Exception as e:
        logger.warning(f"Failed to set some environment variables: {str(e)}")



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
    
    # Initialize MinIO image database with proper error handling
    image_db = None
    
    return _vector_db_instance, metadata_db, image_db
