#!/usr/bin/env python3
"""
Migrate PaperIgnition Data to Aliyun RDS PostgreSQL

This script migrates data from local PostgreSQL to Aliyun RDS.

Usage:
    python scripts/migrate_to_aliyun_rds.py
    python scripts/migrate_to_aliyun_rds.py --batch-size 1000
    python scripts/migrate_to_aliyun_rds.py --skip-papers  # Skip papers table
    python scripts/migrate_to_aliyun_rds.py --skip-chunks  # Skip text_chunks table
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import Generator, Tuple
import time
import json

import yaml
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import execute_batch, Json


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Local database configuration
LOCAL_DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "11111",
    "database": "paperignition"
}


def load_aliyun_config(config_path: str = None) -> dict:
    """Load Aliyun RDS configuration from config file."""
    if config_path is None:
        possible_paths = [
            "orchestrator/production_config.yaml",
            "orchestrator/development_config.yaml",
            "../orchestrator/production_config.yaml",
            "../orchestrator/development_config.yaml",
        ]
        for path in possible_paths:
            full_path = Path(__file__).parent.parent / path
            if full_path.exists():
                config_path = str(full_path)
                break

        if config_path is None:
            raise FileNotFoundError("Config file not found")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    if 'aliyun_rds' not in config:
        raise ValueError("'aliyun_rds' section not found in config")

    return config['aliyun_rds']


def build_aliyun_db_config(aliyun_config: dict) -> dict:
    """Build PostgreSQL connection config for Aliyun RDS."""
    return {
        "host": aliyun_config.get('db_host', 'localhost'),
        "port": int(aliyun_config.get('db_port', '5432')),
        "user": aliyun_config.get('db_user', 'postgres'),
        "password": aliyun_config.get('db_password', ''),
        "database": aliyun_config.get('db_name_paper', 'paperignition')
    }


def connect_to_db(db_config: dict) -> psycopg2.extensions.connection:
    """Connect to PostgreSQL database."""
    return psycopg2.connect(**db_config)


def get_row_count(conn, table_name: str) -> int:
    """Get row count of a table."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    cursor.close()
    return count


def fetch_papers_data(conn, batch_size: int = 1000) -> Generator[list, None, None]:
    """Fetch papers data in batches (excluding pdf_data to reduce transfer size)."""
    cursor = conn.cursor(name="papers_cursor")  # Named cursor for server-side cursor
    cursor.itersize = batch_size

    cursor.execute("""
        SELECT id, doc_id, title, abstract, authors, categories, published_date,
               chunk_ids, figure_ids, image_storage, table_ids,
               extra_metadata, pdf_path, "HTML_path", blog, comments
        FROM papers
        ORDER BY id
    """)

    while True:
        batch = cursor.fetchmany(batch_size)
        if not batch:
            break
        yield batch

    cursor.close()


def fetch_text_chunks_data(conn, batch_size: int = 1000) -> Generator[list, None, None]:
    """Fetch text_chunks data in batches."""
    cursor = conn.cursor(name="chunks_cursor")  # Named cursor for server-side cursor
    cursor.itersize = batch_size

    cursor.execute("""
        SELECT id, doc_id, chunk_id, text_content, chunk_order, created_at
        FROM text_chunks
        ORDER BY doc_id, chunk_order
    """)

    while True:
        batch = cursor.fetchmany(batch_size)
        if not batch:
            break
        yield batch

    cursor.close()


def migrate_papers(local_conn, remote_conn, batch_size: int = 1000) -> int:
    """Migrate papers table from local to remote (excluding pdf_data field)."""
    logger.info("="*60)
    logger.info("Starting papers table migration...")
    logger.info("Note: pdf_data field is excluded to reduce transfer size")
    logger.info("="*60)

    # Get row counts
    local_count = get_row_count(local_conn, "papers")
    remote_count_before = get_row_count(remote_conn, "papers")

    logger.info(f"Local papers count: {local_count}")
    logger.info(f"Remote papers count (before): {remote_count_before}")

    if remote_count_before > 0:
        logger.warning(f"Remote table already has {remote_count_before} rows!")
        response = input("Do you want to continue? (y/N): ")
        if response.lower() != 'y':
            logger.info("Migration cancelled.")
            return 0

    cursor = remote_conn.cursor()

    # Prepare insert statement (excluding pdf_data to reduce transfer size)
    insert_sql = """
        INSERT INTO papers (id, doc_id, title, abstract, authors, categories, published_date,
                           chunk_ids, figure_ids, image_storage, table_ids,
                           extra_metadata, pdf_path, "HTML_path", blog, comments)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (doc_id) DO UPDATE SET
            title = EXCLUDED.title,
            abstract = EXCLUDED.abstract,
            authors = EXCLUDED.authors,
            categories = EXCLUDED.categories,
            published_date = EXCLUDED.published_date,
            chunk_ids = EXCLUDED.chunk_ids,
            figure_ids = EXCLUDED.figure_ids,
            image_storage = EXCLUDED.image_storage,
            table_ids = EXCLUDED.table_ids,
            extra_metadata = EXCLUDED.extra_metadata,
            pdf_path = EXCLUDED.pdf_path,
            "HTML_path" = EXCLUDED."HTML_path",
            blog = EXCLUDED.blog,
            comments = EXCLUDED.comments
    """

    start_time = time.time()
    total_migrated = 0

    try:
        for batch in fetch_papers_data(local_conn, batch_size):
            # Convert dict fields to Json for psycopg2
            processed_batch = []
            for row in batch:
                processed_row = list(row)
                # JSON field indices (based on SELECT order):
                # 0:id, 1:doc_id, 2:title, 3:abstract
                # 4:authors, 5:categories, 6:published_date, 7:chunk_ids,
                # 8:figure_ids, 9:image_storage, 10:table_ids, 11:extra_metadata
                # 12:pdf_path, 13:HTML_path, 14:blog, 15:comments
                json_indices = [4, 5, 7, 8, 9, 10, 11]
                for idx in json_indices:
                    if processed_row[idx] is not None:
                        processed_row[idx] = Json(processed_row[idx])
                processed_batch.append(processed_row)

            execute_batch(cursor, insert_sql, processed_batch, page_size=100)
            remote_conn.commit()
            total_migrated += len(batch)

            progress = (total_migrated / local_count) * 100
            elapsed = time.time() - start_time
            speed = total_migrated / elapsed if elapsed > 0 else 0

            logger.info(f"Progress: {total_migrated}/{local_count} ({progress:.1f}%) - Speed: {speed:.1f} rows/sec")

        # Sync sequence
        logger.info("Syncing sequence...")
        cursor.execute("SELECT MAX(id) FROM papers")
        max_id = cursor.fetchone()[0]
        if max_id:
            cursor.execute(f"SELECT setval('papers_id_seq', {max_id}, true)")
            remote_conn.commit()
            logger.info(f"Sequence set to: {max_id}")

        remote_count_after = get_row_count(remote_conn, "papers")
        elapsed = time.time() - start_time

        logger.info("="*60)
        logger.info("Papers migration completed!")
        logger.info(f"  Rows migrated: {total_migrated}")
        logger.info(f"  Remote count (after): {remote_count_after}")
        logger.info(f"  Time elapsed: {elapsed:.2f} seconds")
        logger.info("="*60)

        return total_migrated

    except Exception as e:
        remote_conn.rollback()
        logger.error(f"Error during papers migration: {e}")
        raise
    finally:
        cursor.close()


def migrate_text_chunks(local_conn, remote_conn, batch_size: int = 1000) -> int:
    """Migrate text_chunks table from local to remote."""
    logger.info("="*60)
    logger.info("Starting text_chunks table migration...")
    logger.info("="*60)

    # Get row counts
    local_count = get_row_count(local_conn, "text_chunks")
    remote_count_before = get_row_count(remote_conn, "text_chunks")

    logger.info(f"Local text_chunks count: {local_count}")
    logger.info(f"Remote text_chunks count (before): {remote_count_before}")

    if remote_count_before > 0:
        logger.warning(f"Remote table already has {remote_count_before} rows!")
        response = input("Do you want to continue? (y/N): ")
        if response.lower() != 'y':
            logger.info("Migration cancelled.")
            return 0

    cursor = remote_conn.cursor()

    # Prepare insert statement
    insert_sql = """
        INSERT INTO text_chunks (id, doc_id, chunk_id, text_content, chunk_order, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            doc_id = EXCLUDED.doc_id,
            chunk_id = EXCLUDED.chunk_id,
            text_content = EXCLUDED.text_content,
            chunk_order = EXCLUDED.chunk_order,
            created_at = EXCLUDED.created_at
    """

    start_time = time.time()
    total_migrated = 0

    try:
        for batch in fetch_text_chunks_data(local_conn, batch_size):
            execute_batch(cursor, insert_sql, batch, page_size=100)
            remote_conn.commit()
            total_migrated += len(batch)

            progress = (total_migrated / local_count) * 100
            elapsed = time.time() - start_time
            speed = total_migrated / elapsed if elapsed > 0 else 0

            logger.info(f"Progress: {total_migrated}/{local_count} ({progress:.1f}%) - Speed: {speed:.1f} rows/sec")

        remote_count_after = get_row_count(remote_conn, "text_chunks")
        elapsed = time.time() - start_time

        logger.info("="*60)
        logger.info("Text chunks migration completed!")
        logger.info(f"  Rows migrated: {total_migrated}")
        logger.info(f"  Remote count (after): {remote_count_after}")
        logger.info(f"  Time elapsed: {elapsed:.2f} seconds")
        logger.info("="*60)

        return total_migrated

    except Exception as e:
        remote_conn.rollback()
        logger.error(f"Error during text_chunks migration: {e}")
        raise
    finally:
        cursor.close()


def main():
    parser = argparse.ArgumentParser(
        description="Migrate PaperIgnition data to Aliyun RDS",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to config file (default: auto-detect)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for data migration (default: 1000)'
    )
    parser.add_argument(
        '--skip-papers',
        action='store_true',
        help='Skip papers table migration'
    )
    parser.add_argument(
        '--skip-chunks',
        action='store_true',
        help='Skip text_chunks table migration'
    )

    args = parser.parse_args()

    local_conn = None
    remote_conn = None

    try:
        # Load Aliyun config
        logger.info("Loading Aliyun RDS configuration...")
        aliyun_config = load_aliyun_config(args.config)
        remote_db_config = build_aliyun_db_config(aliyun_config)

        logger.info(f"Local DB: {LOCAL_DB_CONFIG['database']} at {LOCAL_DB_CONFIG['host']}")
        logger.info(f"Remote DB: {remote_db_config['database']} at {remote_db_config['host']}")

        # Connect to databases
        logger.info("Connecting to local database...")
        local_conn = connect_to_db(LOCAL_DB_CONFIG)
        logger.info("✓ Connected to local database")

        logger.info("Connecting to Aliyun RDS...")
        remote_conn = connect_to_db(remote_db_config)
        logger.info("✓ Connected to Aliyun RDS")

        # Migrate papers table
        if not args.skip_papers:
            migrate_papers(local_conn, remote_conn, args.batch_size)
        else:
            logger.info("Skipping papers table migration (--skip-papers)")

        # Migrate text_chunks table
        if not args.skip_chunks:
            migrate_text_chunks(local_conn, remote_conn, args.batch_size)
        else:
            logger.info("Skipping text_chunks table migration (--skip-chunks)")

        logger.info("\n" + "="*60)
        logger.info("SUCCESS! Data migration completed!")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"\nMigration failed: {e}")
        sys.exit(1)
    finally:
        if local_conn:
            local_conn.close()
            logger.info("Local connection closed")
        if remote_conn:
            remote_conn.close()
            logger.info("Remote connection closed")


if __name__ == "__main__":
    main()
