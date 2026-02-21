#!/usr/bin/env python3
"""
上传本地imgs文件夹与MinIO bucket并集文件到阿里云OSS

逻辑：
1. 获取MinIO aignite-papers-new bucket中的文件列表
2. 获取本地imgs文件夹中的文件列表
3. 计算并集（两者任一存在的文件都需要上传）
4. 上传策略：
   - 本地存在的文件：从本地上传到OSS
   - MinIO独有的文件：从MinIO流式下载后上传到OSS
5. 跳过已存在于OSS的文件

使用方法:
    python scripts/imgs2aliyun.py
    python scripts/imgs2aliyun.py --config scripts/migration_config.yaml
"""

import argparse
import io
import os
import sys
import time
from pathlib import Path

import oss2
from minio import Minio
from tqdm import tqdm

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from migration_utils import (
    load_migration_config,
    get_aliyun_oss_config,
    get_minio_config,
    get_local_paths_config,
    print_config_summary
)


def get_minio_objects(minio_client: Minio, bucket_name: str) -> set:
    """获取MinIO bucket中所有对象的名称"""
    objects = set()
    try:
        if not minio_client.bucket_exists(bucket_name):
            print(f"错误: Bucket '{bucket_name}' 不存在")
            return objects

        for obj in minio_client.list_objects(bucket_name, recursive=True):
            objects.add(obj.object_name)

    except Exception as e:
        print(f"获取MinIO对象时出错: {e}")

    return objects


def get_local_files(local_dir: str) -> set:
    """获取本地目录中所有文件的名称"""
    files = set()
    try:
        if not os.path.exists(local_dir):
            print(f"错误: 本地目录 '{local_dir}' 不存在")
            return files

        for filename in os.listdir(local_dir):
            filepath = os.path.join(local_dir, filename)
            if os.path.isfile(filepath):
                files.add(filename)

    except Exception as e:
        print(f"获取本地文件时出错: {e}")

    return files


def upload_from_local_with_retry(bucket, oss_path, local_path, max_retries=3):
    """从本地上传到OSS，带重试机制"""
    for attempt in range(max_retries):
        try:
            bucket.put_object_from_file(oss_path, local_path)
            return True
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return False
    return False


def upload_from_minio_with_retry(bucket, oss_path, minio_client, minio_bucket, minio_object_name, max_retries=3):
    """从MinIO流式下载并上传到OSS，带重试机制"""
    for attempt in range(max_retries):
        try:
            # 从MinIO获取对象
            response = minio_client.get_object(minio_bucket, minio_object_name)
            data = response.read()
            response.close()
            response.release_conn()

            # 上传到OSS
            bucket.put_object(oss_path, data)
            return True
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return False
    return False


def main():
    parser = argparse.ArgumentParser(
        description='上传本地imgs文件夹与MinIO bucket并集文件到阿里云OSS',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='配置文件路径 (默认: scripts/migration_config.yaml)'
    )
    args = parser.parse_args()

    # 加载配置
    config = load_migration_config(args.config)

    # 获取各项配置
    oss_config = get_aliyun_oss_config(config)
    minio_config = get_minio_config(config)
    local_paths = get_local_paths_config(config)

    # 打印配置摘要
    print("=" * 60)
    print("上传MinIO与本地并集文件到阿里云OSS")
    print("=" * 60)
    print_config_summary(config)

    # 1. 连接MinIO并获取文件列表
    print("\n[1/4] 连接MinIO并获取文件列表...")
    minio_client = Minio(
        minio_config['endpoint'],
        access_key=minio_config['access_key'],
        secret_key=minio_config['secret_key'],
        secure=minio_config.get('secure', False)
    )
    minio_files = get_minio_objects(minio_client, minio_config['bucket_name'])
    print(f"  MinIO bucket '{minio_config['bucket_name']}' 中共有 {len(minio_files):,} 个文件")

    # 2. 获取本地文件列表
    print("\n[2/4] 获取本地文件列表...")
    local_folder = local_paths.get('imgs_folder', '/data3/guofang/peirongcan/PaperIgnition/orchestrator/imgs')
    local_files = get_local_files(local_folder)
    print(f"  本地目录中共有 {len(local_files):,} 个文件")

    # 3. 计算并集和文件分类
    print("\n[3/4] 计算并集和文件分类...")
    union_files = minio_files | local_files
    only_in_minio = minio_files - local_files  # MinIO独有的文件
    only_in_local = local_files - minio_files  # 本地独有的文件
    in_both = minio_files & local_files        # 两边都有的文件

    print(f"  并集文件数: {len(union_files):,}")
    print(f"  MinIO独有: {len(only_in_minio):,}")
    print(f"  本地独有: {len(only_in_local):,}")
    print(f"  两边都有: {len(in_both):,}")

    if not union_files:
        print("\n没有文件需要上传，程序退出")
        return

    # 4. 连接阿里云OSS并获取已上传文件列表
    print("\n[4/4] 连接阿里云OSS...")
    auth = oss2.Auth(oss_config['access_key_id'], oss_config['access_key_secret'])
    bucket = oss2.Bucket(
        auth,
        oss_config['endpoint'],
        oss_config['bucket_name'],
        connect_timeout=oss_config.get('connect_timeout', 60)
    )

    upload_prefix = oss_config.get('upload_prefix', 'imgs/')
    print(f"  获取OSS上已存在的文件列表 (prefix: {upload_prefix})...")
    existing_files = set()
    for obj in oss2.ObjectIterator(bucket, prefix=upload_prefix):
        existing_files.add(obj.key)
    print(f"  OSS上已有 {len(existing_files):,} 个文件")

    # 5. 筛选出需要上传的文件（区分来源）
    files_from_local = []   # 从本地上传
    files_from_minio = []   # 从MinIO上传

    for filename in union_files:
        oss_path = f'{upload_prefix}{filename}'
        if oss_path not in existing_files:
            if filename in local_files:
                files_from_local.append(filename)
            else:
                files_from_minio.append(filename)

    total_to_upload = len(files_from_local) + len(files_from_minio)
    print(f"  需要上传的文件数: {total_to_upload:,}")
    print(f"    - 从本地上传: {len(files_from_local):,}")
    print(f"    - 从MinIO上传: {len(files_from_minio):,}")

    if total_to_upload == 0:
        print("\n所有文件已存在于OSS，无需上传")
        return

    # 6. 上传文件（带进度条）
    print("\n" + "=" * 60)
    print("开始上传并集文件...")
    print("=" * 60)

    max_retries = oss_config.get('max_retries', 3)
    uploaded_from_local = 0
    uploaded_from_minio = 0
    failed_from_local = []
    failed_from_minio = []
    minio_bucket = minio_config['bucket_name']

    # 先上传本地文件
    if files_from_local:
        print(f"\n[阶段1] 从本地上传 {len(files_from_local):,} 个文件...")
        sorted_local = sorted(files_from_local)
        with tqdm(total=len(sorted_local), desc="本地上传", unit="文件") as pbar:
            for filename in sorted_local:
                local_path = os.path.join(local_folder, filename)
                oss_path = f'{upload_prefix}{filename}'
                pbar.set_postfix_str(f"当前: {filename[:30]}...")

                if upload_from_local_with_retry(bucket, oss_path, local_path, max_retries):
                    uploaded_from_local += 1
                else:
                    failed_from_local.append(filename)
                pbar.update(1)

    # 再上传MinIO独有文件
    if files_from_minio:
        print(f"\n[阶段2] 从MinIO上传 {len(files_from_minio):,} 个文件...")
        sorted_minio = sorted(files_from_minio)
        with tqdm(total=len(sorted_minio), desc="MinIO上传", unit="文件") as pbar:
            for filename in sorted_minio:
                oss_path = f'{upload_prefix}{filename}'
                pbar.set_postfix_str(f"当前: {filename[:30]}...")

                if upload_from_minio_with_retry(bucket, oss_path, minio_client, minio_bucket, filename, max_retries):
                    uploaded_from_minio += 1
                else:
                    failed_from_minio.append(filename)
                pbar.update(1)

    # 7. 输出统计信息
    print("\n" + "=" * 60)
    print("上传完成！统计信息:")
    print("=" * 60)
    print(f"  MinIO 文件数: {len(minio_files):,}")
    print(f"  本地文件数: {len(local_files):,}")
    print(f"  并集文件数: {len(union_files):,}")
    print(f"  OSS已有: {len(existing_files):,}")
    print(f"  ---")
    print(f"  本次需上传: {total_to_upload:,}")
    print(f"    - 从本地需上传: {len(files_from_local):,}")
    print(f"    - 从MinIO需上传: {len(files_from_minio):,}")
    print(f"  ---")
    print(f"  本次上传成功: {uploaded_from_local + uploaded_from_minio:,}")
    print(f"    - 从本地上传成功: {uploaded_from_local:,}")
    print(f"    - 从MinIO上传成功: {uploaded_from_minio:,}")
    print(f"  本次上传失败: {len(failed_from_local) + len(failed_from_minio):,}")

    if failed_from_local:
        print('\n从本地上传失败的文件:')
        for f in failed_from_local[:20]:  # 只显示前20个
            print(f'  - {f}')
        if len(failed_from_local) > 20:
            print(f'  ... 还有 {len(failed_from_local) - 20} 个文件')

    if failed_from_minio:
        print('\n从MinIO上传失败的文件:')
        for f in failed_from_minio[:20]:  # 只显示前20个
            print(f'  - {f}')
        if len(failed_from_minio) > 20:
            print(f'  ... 还有 {len(failed_from_minio) - 20} 个文件')


if __name__ == "__main__":
    main()
