#!/usr/bin/env python3
"""
迁移配置加载工具

提供统一的配置加载功能，供所有迁移脚本使用。
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def get_default_config_path() -> str:
    """获取默认配置文件路径"""
    return str(Path(__file__).parent / "migration_config.yaml")


def load_migration_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载迁移配置文件

    Args:
        config_path: 配置文件路径，如果为 None 则使用默认路径

    Returns:
        配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置文件格式错误
    """
    if config_path is None:
        config_path = get_default_config_path()

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    if not config:
        raise ValueError(f"配置文件为空或格式错误: {config_path}")

    return config


def get_local_paper_db_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取本地 Paper 数据库配置"""
    return config.get('local_database', {}).get('paper_db', {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': '',
        'database': 'paperignition'
    })


def get_local_user_db_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取本地 User 数据库配置"""
    return config.get('local_database', {}).get('user_db', {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': '',
        'database': 'paperignition_user'
    })


def get_aliyun_rds_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取阿里云 RDS 配置"""
    return config.get('aliyun_rds', {})


def build_aliyun_paper_db_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """构建阿里云 Paper 数据库连接配置"""
    rds = get_aliyun_rds_config(config)
    return {
        'host': rds.get('db_host', 'localhost'),
        'port': int(rds.get('db_port', '5432')),
        'user': rds.get('db_user', 'postgres'),
        'password': rds.get('db_password', ''),
        'database': rds.get('db_name_paper', 'paperignition')
    }


def build_aliyun_user_db_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """构建阿里云 User 数据库连接配置"""
    rds = get_aliyun_rds_config(config)
    return {
        'host': rds.get('db_host', 'localhost'),
        'port': int(rds.get('db_port', '5432')),
        'user': rds.get('db_user', 'postgres'),
        'password': rds.get('db_password', ''),
        'database': rds.get('db_name_user', 'paperignition_user')
    }


def get_aliyun_oss_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取阿里云 OSS 配置"""
    return config.get('aliyun_oss', {})


def get_minio_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取 MinIO 配置"""
    return config.get('minio', {})


def get_local_paths_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取本地路径配置"""
    return config.get('local_paths', {})


def get_migration_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取迁移配置"""
    return config.get('migration', {})


def print_config_summary(config: Dict[str, Any], hide_secrets: bool = True) -> None:
    """
    打印配置摘要

    Args:
        config: 配置字典
        hide_secrets: 是否隐藏敏感信息
    """
    print("=" * 60)
    print("配置摘要")
    print("=" * 60)

    # 本地数据库
    local_paper = get_local_paper_db_config(config)
    local_user = get_local_user_db_config(config)
    print(f"\n[本地数据库]")
    print(f"  Paper DB: {local_paper['database']} @ {local_paper['host']}:{local_paper['port']}")
    print(f"  User DB: {local_user['database']} @ {local_user['host']}:{local_user['port']}")

    # 阿里云 RDS
    rds = get_aliyun_rds_config(config)
    if rds.get('enabled', False):
        print(f"\n[阿里云 RDS]")
        print(f"  Host: {rds.get('db_host', 'N/A')}")
        print(f"  Port: {rds.get('db_port', 'N/A')}")
        print(f"  User: {rds.get('db_user', 'N/A')}")
        print(f"  Paper DB: {rds.get('db_name_paper', 'N/A')}")
        print(f"  User DB: {rds.get('db_name_user', 'N/A')}")
        if hide_secrets:
            print(f"  Password: ***")
        else:
            print(f"  Password: {rds.get('db_password', 'N/A')}")

    # 阿里云 OSS
    oss = get_aliyun_oss_config(config)
    if oss:
        print(f"\n[阿里云 OSS]")
        print(f"  Endpoint: {oss.get('endpoint', 'N/A')}")
        print(f"  Bucket: {oss.get('bucket_name', 'N/A')}")
        print(f"  Prefix: {oss.get('upload_prefix', 'N/A')}")

    # MinIO
    minio = get_minio_config(config)
    if minio:
        print(f"\n[MinIO]")
        print(f"  Endpoint: {minio.get('endpoint', 'N/A')}")
        print(f"  Bucket: {minio.get('bucket_name', 'N/A')}")

    # 本地路径
    paths = get_local_paths_config(config)
    if paths:
        print(f"\n[本地路径]")
        print(f"  Imgs Folder: {paths.get('imgs_folder', 'N/A')}")

    print("=" * 60)


if __name__ == "__main__":
    # 测试配置加载
    print("测试配置加载...")
    config = load_migration_config()
    print_config_summary(config)
