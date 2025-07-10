import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import os
import logging

logger = logging.getLogger(__name__)

# 默认配置文件路径
DEFAULT_INDEX_CONFIG_PATH = Path(__file__).parent / "index_config.yaml"
DEFAULT_BACKEND_CONFIG_PATH = Path(__file__).parent / "backend_config.yaml"

def load_index_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载索引服务配置
    
    Args:
        config_path: 配置文件路径。如果未提供，使用默认路径。
        
    Returns:
        包含配置参数的字典
        
    Raises:
        FileNotFoundError: 如果配置文件不存在
        ValueError: 如果缺少必要的配置项或加载失败
    """
    if not config_path:
        config_path = os.environ.get("INDEX_SERVICE_CONFIG", str(DEFAULT_INDEX_CONFIG_PATH))
        
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件未找到: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # 验证必要的配置项
        required_sections = ['vector_db', 'metadata_db', 'minio_db']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"配置文件缺少必要的部分 '{section}'")
        
        # 验证数据库配置
        if 'model_name' not in config['vector_db']:
            raise ValueError("vector_db 配置中缺少 'model_name'")
            
        if 'db_url' not in config['metadata_db']:
            raise ValueError("metadata_db 配置中缺少 'db_url'")
        
        # 验证 MinIO 配置
        minio_required = ['endpoint', 'access_key', 'secret_key', 'bucket_name']
        for param in minio_required:
            if param not in config['minio_db']:
                raise ValueError(f"配置文件中缺少必要的 MinIO 参数 '{param}'")
        
        logger.debug(f"成功加载配置文件: {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        raise ValueError(f"配置加载错误: {str(e)}")

def load_backend_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载后端配置
    
    Args:
        config_path: 配置文件路径。如果未提供，使用默认路径。
        
    Returns:
        包含配置参数的字典
        
    Raises:
        FileNotFoundError: 如果配置文件不存在
        ValueError: 如果加载失败
    """
    if not config_path:
        config_path = os.environ.get("BACKEND_CONFIG", str(DEFAULT_BACKEND_CONFIG_PATH))
        
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"后端配置文件未找到: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # 验证必要的字段
        if 'api_url' not in config:
            raise ValueError("后端配置中缺少 'api_url'")
        
        # 从环境变量覆盖数据库配置
        _override_db_config_from_env(config)
        
        logger.debug(f"成功加载后端配置文件: {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"加载后端配置失败: {str(e)}")
        raise ValueError(f"后端配置加载错误: {str(e)}")

def _override_db_config_from_env(config: Dict[str, Any]) -> None:
    """从环境变量中覆盖数据库配置
    
    环境变量命名规则：
    - 主数据库: DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
    - 测试数据库: TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME
    
    Args:
        config: 配置字典
    """
    # 确保数据库配置部分存在
    if 'database' not in config:
        config['database'] = {'main': {}, 'test': {}}
    if 'main' not in config['database']:
        config['database']['main'] = {}
    if 'test' not in config['database']:
        config['database']['test'] = {}
    
    # 主数据库配置覆盖
    main_db = config['database']['main']
    main_db['user'] = os.environ.get('DB_USER', main_db.get('user', 'postgres'))
    main_db['password'] = os.environ.get('DB_PASSWORD', main_db.get('password', ''))
    main_db['host'] = os.environ.get('DB_HOST', main_db.get('host', 'localhost'))
    main_db['port'] = os.environ.get('DB_PORT', main_db.get('port', '5432'))
    main_db['name'] = os.environ.get('DB_NAME', main_db.get('name', 'paperignition_user'))
    
    # 测试数据库配置覆盖
    test_db = config['database']['test']
    test_db['user'] = os.environ.get('TEST_DB_USER', test_db.get('user', main_db['user']))
    test_db['password'] = os.environ.get('TEST_DB_PASSWORD', test_db.get('password', main_db['password']))
    test_db['host'] = os.environ.get('TEST_DB_HOST', test_db.get('host', main_db['host']))
    test_db['port'] = os.environ.get('TEST_DB_PORT', test_db.get('port', main_db['port']))
    test_db['name'] = os.environ.get('TEST_DB_NAME', test_db.get('name', 'paperignition_test'))

def load_config(config_type: str = "backend", config_path: Optional[str] = None) -> Dict[str, Any]:
    """通用配置加载函数
    
    Args:
        config_type: 配置类型，可以是 "backend" 或 "index"
        config_path: 配置文件路径。如果未提供，使用默认路径。
        
    Returns:
        包含配置参数的字典
        
    Raises:
        ValueError: 如果配置类型无效或加载失败
    """
    if config_type == "backend":
        return load_backend_config(config_path)
    elif config_type == "index":
        return load_index_config(config_path)
    else:
        raise ValueError(f"无效的配置类型: {config_type}。有效类型为 'backend' 或 'index'。") 