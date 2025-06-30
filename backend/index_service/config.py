import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent / "configs/index_config.yaml"

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to config.yaml file. Must be provided.
        
    Returns:
        Dictionary containing configuration parameters
        
    Raises:
        FileNotFoundError: If config file not found
        ValueError: If required configuration sections are missing or if loading fails
    """
    if not config_path:
        config_path = os.environ.get("INDEX_SERVICE_CONFIG", str(DEFAULT_CONFIG_PATH))
        
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
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
        
        logger.debug(f"Successfully loaded configuration from {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise ValueError(f"Error loading config: {str(e)}")
