"""
Unified Configuration Loading Utility for PaperIgnition

This module provides a centralized configuration loading mechanism
that supports both YAML files and environment variables.

Shared between:
- Backend Service (backend/app/)
- Index Service (backend/index_service/)

Last updated: 2025-02-12
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging
import os
import yaml
import re


# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def _substitute_env_vars(value: Any) -> Any:
    """
    Recursively substitute environment variables in configuration values.

    Supports ${VAR_NAME} syntax in YAML values.

    Args:
        value: Configuration value (string, dict, list, or other type)

    Returns:
        Value with environment variables substituted
    """
    if isinstance(value, str):
        # Replace ${VAR_NAME} with environment variable value
        def replace_env_var(match):
            env_var = match.group(1)
            env_value = os.environ.get(env_var)
            if env_value is None:
                logger.warning(f"Environment variable '{env_var}' not found, keeping placeholder")
                return match.group(0)  # Keep the ${VAR_NAME} if not found
            return env_value

        # Use regex to find and replace ${VAR_NAME} patterns
        return re.sub(r'\$\{([^}]+)\}', replace_env_var, value)

    elif isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]
    else:
        return value


def load_config(
    config_path: Optional[str] = None,
    service: str = "backend",
    set_env: bool = True,
    display_storage_info: bool = False
) -> Dict[str, Any]:
    """
    Load configuration from YAML file or environment variables.

    This is a unified configuration loader that supports:
    - Backend Service (loads USER_DB, INDEX_SERVICE, APP_SERVICE sections)
    - Index Service (loads INDEX_SERVICE section with vector_db, metadata_db, minio_db)

    Args:
        config_path: Path to config.yaml file. If None, uses environment variable or default path.
        service: Which service config to load ('backend' or 'index')
        set_env: Whether to set configuration values as environment variables.
        display_storage_info: Whether to display storage statistics (index service only)

    Returns:
        Dictionary containing configuration parameters for the requested service

    Raises:
        FileNotFoundError: If config file path provided but file doesn't exist
        ValueError: If required configuration sections are missing or loading fails
    """
    # Get config path from parameter, environment variable, or default
    if not config_path:
        config_path = os.environ.get("PAPERIGNITION_CONFIG")

        # Check for host override (used in index service)
        host = os.environ.get('PAPERIGNITION_INDEX_SERVICE_HOST')
        if host:
            logger.debug(f"Using config from environment variable (host override: {host})")
            return _load_config_from_environment(set_env, display_storage_info)

        # Use default paths based on service
        if not config_path:
            LOCAL_MODE = os.getenv("PAPERIGNITION_LOCAL_MODE", "false").lower() == "true"
            if service == "backend":
                config_file = "configs/test_config.yaml" if LOCAL_MODE else "configs/app_config.yaml"
            else:  # index service
                config_file = "configs/app_config.yaml"  # Index service uses production config
            config_path = str(Path(__file__).resolve().parent.parent / config_file)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at: {config_path}")

    try:
        with open(config_path, 'r') as f:
            full_config = yaml.safe_load(f)

        # Substitute environment variables in the entire config
        full_config = _substitute_env_vars(full_config)

        # Load based on service type
        if service == "backend":
            config = _load_backend_config(full_config, config_path)
        elif service == "index":
            config = _load_index_config(full_config, config_path)
        else:
            raise ValueError(f"Unknown service type: {service}")

        # Set environment variables if requested
        if set_env:
            logger.debug('Setting environment variables from loaded configuration')
            _set_config_environment_variables(config, service)

        logger.info(f"Successfully loaded {service} configuration from: {config_path}")

        # Display storage info for index service
        if display_storage_info and service == "index":
            _display_storage_info(config)

        return config

    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise ValueError(f"Error loading config from {config_path}: {str(e)}")


def _load_backend_config(full_config: Dict[str, Any], config_path: str) -> Dict[str, Any]:
    """Load backend service configuration (USER_DB, INDEX_SERVICE, APP_SERVICE)."""
    required_sections = {
        "USER_DB": "User database configuration",
        "INDEX_SERVICE": "Index service configuration",
        "APP_SERVICE": "Application service configuration"
    }

    for section, description in required_sections.items():
        if section not in full_config:
            raise ValueError(f"Missing required section '{section}' in {config_path}")

    config = {
        "USER_DB": full_config["USER_DB"],
        "INDEX_SERVICE": full_config["INDEX_SERVICE"],
        "APP_SERVICE": full_config["APP_SERVICE"],
        "OPENAI_SERVICE": full_config.get("OPENAI_SERVICE", {}),
        # New sections for RDS decoupling
        "dashscope": full_config.get("dashscope", {}),
        "aliyun_rds": full_config.get("aliyun_rds", {}),
        "aliyun_oss": full_config.get("aliyun_oss", {}),
    }

    # Set dashscope environment variables if available
    dashscope_config = config.get("dashscope", {})
    if dashscope_config:
        if "api_key" in dashscope_config:
            os.environ["DASHSCOPE_API_KEY"] = str(dashscope_config["api_key"])
        if "base_url" in dashscope_config:
            os.environ["DASHSCOPE_BASE_URL"] = str(dashscope_config["base_url"])
        if "embedding_model" in dashscope_config:
            os.environ["DASHSCOPE_EMBEDDING_MODEL"] = str(dashscope_config["embedding_model"])
        if "embedding_dimension" in dashscope_config:
            os.environ["DASHSCOPE_EMBEDDING_DIMENSION"] = str(dashscope_config["embedding_dimension"])

    return config


def _load_index_config(full_config: Dict[str, Any], config_path: str) -> Dict[str, Any]:
    """Load index service configuration (INDEX_SERVICE with vector_db, metadata_db, minio_db)."""
    if "INDEX_SERVICE" not in full_config:
        raise ValueError(f"Missing 'INDEX_SERVICE' section in {config_path}")

    config = full_config["INDEX_SERVICE"]

    # Validate vector database configuration (optional)
    if 'vector_db' in config:
        if 'model_name' not in config['vector_db']:
            raise ValueError("Missing 'model_name' in vector_db configuration")

    # Validate metadata database configuration (required)
    if 'metadata_db' not in config:
        raise ValueError("Missing 'metadata_db' section in INDEX_SERVICE configuration")
    if 'db_url' not in config['metadata_db']:
        raise ValueError("Missing 'db_url' in metadata_db configuration")

    # Validate MinIO configuration (optional)
    if 'minio_db' in config:
        minio_required = ['endpoint', 'access_key', 'secret_key', 'bucket_name']
        for param in minio_required:
            if param not in config['minio_db']:
                raise ValueError(f"Missing required MinIO parameter '{param}' in config.yaml")

    return config


def _load_config_from_environment(
    set_env: bool = True,
    display_storage_info: bool = False
) -> Dict[str, Any]:
    """
    Load configuration from environment variables (index service only).

    Args:
        set_env: Whether to set configuration values as environment variables.
        display_storage_info: Whether to display storage statistics

    Returns:
        Dictionary containing configuration parameters from environment variables

    Raises:
        ValueError: If required configuration sections are missing
    """
    logger.info("Loading index service configuration from environment variables")

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

    # Set environment variables if requested
    if set_env:
        _set_config_environment_variables(config, "index")

    # Display storage information
    if display_storage_info:
        _display_storage_info(config)

    return config


def _set_config_environment_variables(config: Dict[str, Any], service: str) -> None:
    """Set configuration values as environment variables for other modules to access."""
    try:
        if service == "index":
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


def _display_storage_info(config: Dict[str, Any]) -> None:
    """Display current storage information for metadata_db and vector_db.

    Args:
        config: Configuration dictionary containing database settings
    """
    try:
        logger.info("=" * 60)
        logger.info("STORAGE INFORMATION")
        logger.info("=" * 60)

        # Vector DB Storage Information
        if 'vector_db' in config:
            vector_db_path = config['vector_db']['db_path']
            logger.info(f"Vector Database Path: {vector_db_path}")

            # Check if vector database exists and get info
            if os.path.exists(vector_db_path):
                index_file = os.path.join(vector_db_path, "index.pkl")
                faiss_file = os.path.join(vector_db_path, "index.faiss")

                if os.path.exists(index_file) and os.path.exists(faiss_file):
                    # Get file sizes
                    index_size = os.path.getsize(index_file)
                    faiss_size = os.path.getsize(faiss_file)
                    total_size = index_size + faiss_size

                    logger.info(f"   Vector DB exists")
                    logger.info(f"   Index file size: {_format_bytes(index_size)}")
                    logger.info(f"   FAISS file size: {_format_bytes(faiss_size)}")
                    logger.info(f"   Total size: {_format_bytes(total_size)}")

                    # Try to get vector count from FAISS index
                    try:
                        import faiss
                        faiss_index = faiss.read_index(faiss_file)
                        vector_count = faiss_index.ntotal
                        logger.info(f"   Vector count: {vector_count}")
                    except Exception as e:
                        logger.debug(f"Failed to read FAISS index for vector count: {str(e)}")
                        logger.info(f"   Vector count: Unable to determine")
                else:
                    logger.info(f"   Vector DB files incomplete or missing")
            else:
                logger.info(f"   Vector DB directory does not exist")

            logger.info("")

        # Metadata DB Storage Information
        if 'metadata_db' in config:
            db_url = config['metadata_db']['db_url']
            logger.info(f"Metadata Database URL: {db_url}")

            # Try to connect and get metadata info
            try:
                from sqlalchemy import create_engine, inspect, text
                engine = create_engine(db_url)
                with engine.connect() as conn:
                    # Check if tables exist
                    inspector = inspect(engine)
                    tables = inspector.get_table_names()

                    if 'papers' in tables:
                        # Get paper count
                        result = conn.execute(text("SELECT COUNT(*) FROM papers"))
                        paper_count = result.scalar()
                        logger.info(f"   Metadata DB connected")
                        logger.info(f"   Papers table exists")
                        logger.info(f"   Paper count: {paper_count}")

                        # Get text chunks count if table exists
                        if 'text_chunks' in tables:
                            result = conn.execute(text("SELECT COUNT(*) FROM text_chunks"))
                            chunk_count = result.scalar()
                            logger.info(f"   Text chunks count: {chunk_count}")

                        # Get database size (PostgreSQL specific)
                        if 'postgresql' in db_url:
                            try:
                                result = conn.execute(text("""
                                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
                                """))
                                db_size = result.scalar()
                                logger.info(f"   Database size: {db_size}")
                            except Exception:
                                logger.info(f"   Database size: Unable to determine")
                    else:
                        logger.info(f"   Papers table does not exist")
                        logger.info(f"   Available tables: {', '.join(tables) if tables else 'None'}")

            except Exception as e:
                logger.info(f"   Cannot connect to metadata DB: {str(e)}")

            logger.info("")

        # MinIO DB Storage Information
        if 'minio_db' in config:
            minio_config = config['minio_db']
            logger.info(f"MinIO Image Storage: {minio_config['endpoint']}")
            logger.info(f"   Bucket: {minio_config['bucket_name']}")

            # Try to connect and get MinIO storage info
            try:
                from minio import Minio
                from minio.error import S3Error

                # Create MinIO client
                minio_client = Minio(
                    endpoint=minio_config['endpoint'],
                    access_key=minio_config['access_key'],
                    secret_key=minio_config['secret_key'],
                    secure=minio_config.get('secure', False)
                )

                bucket_name = minio_config['bucket_name']

                # Check if bucket exists
                if minio_client.bucket_exists(bucket_name):
                    logger.info(f"   MinIO bucket exists")

                    # List all objects and calculate statistics
                    try:
                        objects = minio_client.list_objects(bucket_name, recursive=True)

                        object_count = 0
                        total_size = 0

                        for obj in objects:
                            object_count += 1
                            total_size += obj.size

                        logger.info(f"   Image object count: {object_count}")
                        logger.info(f"   Total storage size: {_format_bytes(total_size)}")

                    except Exception as e:
                        logger.info(f"   Could not retrieve object statistics: {str(e)}")

                else:
                    logger.info(f"   MinIO bucket does not exist")

            except S3Error as e:
                logger.warning(f"   MinIO S3 Error: {str(e)}")
            except Exception as e:
                logger.warning(f"   Cannot connect to MinIO: {str(e)}")
        else:
            logger.info("")
            logger.info("MinIO Image Storage: Not configured")

        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Failed to display storage information: {str(e)}")


def _format_bytes(bytes_size: int) -> str:
    """Format bytes into human readable format.

    Args:
        bytes_size: Size in bytes

    Returns:
        Formatted string with appropriate unit
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


# Alias for backward compatibility
load_config_from_environment = _load_config_from_environment
