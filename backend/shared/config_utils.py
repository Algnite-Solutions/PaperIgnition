"""
Unified Configuration Loading Utility for PaperIgnition

This module provides a centralized configuration loading mechanism
that supports both YAML files and environment variables.

Shared between:
- Backend Service (backend/app/)

Last updated: 2026-03-05
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
    - Backend Service (loads USER_DB, APP_SERVICE, etc. sections)

    Args:
        config_path: Path to config.yaml file. If None, uses environment variable or default path.
        service: Which service config to load (Default: 'backend')
        set_env: Whether to set configuration values as environment variables.

    Returns:
        Dictionary containing configuration parameters for the requested service

    Raises:
        FileNotFoundError: If config file path provided but file doesn't exist
        ValueError: If required configuration sections are missing or loading fails
    """
    # Get config path from parameter, environment variable, or default
    if not config_path:
        config_path = os.environ.get("PAPERIGNITION_CONFIG")

        # Use default paths based on service
        if not config_path:
            LOCAL_MODE = os.getenv("PAPERIGNITION_LOCAL_MODE", "false").lower() == "true"
            config_file = "configs/test_config.yaml" if LOCAL_MODE else "configs/app_config.yaml"
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
        else:
            raise ValueError(f"Unknown service type: {service}")

        logger.info(f"Successfully loaded {service} configuration from: {config_path}")

        return config

    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise ValueError(f"Error loading config from {config_path}: {str(e)}")


def _load_backend_config(full_config: Dict[str, Any], config_path: str) -> Dict[str, Any]:
    """Load backend service configuration."""
    required_sections = {
        "USER_DB": "User database configuration",
        "APP_SERVICE": "Application service configuration"
    }

    for section, description in required_sections.items():
        if section not in full_config:
            raise ValueError(f"Missing required section '{section}' in {config_path}")

    config = {
        "USER_DB": full_config["USER_DB"],
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
