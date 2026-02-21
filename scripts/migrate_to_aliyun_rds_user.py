#!/usr/bin/env python3
"""
Migrate PaperIgnition User Data to Aliyun RDS PostgreSQL

This script migrates user data from local PostgreSQL to Aliyun RDS.
Tables: users, research_domains, favorite_papers, paper_recommendations,
        job_logs, user_domain_association, user_retrieve_results

Usage:
    python scripts/migrate_to_aliyun_rds_user.py
    python scripts/migrate_to_aliyun_rds_user.py --config scripts/migration_config.yaml
    python scripts/migrate_to_aliyun_rds_user.py --batch-size 500
    python scripts/migrate_to_aliyun_rds_user.py --skip-users  # Skip users table
    python scripts/migrate_to_aliyun_rds_user.py --tables users,favorite_papers  # Migrate specific tables
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import Generator, List
import time

import psycopg2
from psycopg2.extras import execute_batch, Json

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from migration_utils import (
    load_migration_config,
    get_local_user_db_config,
    build_aliyun_user_db_config,
    print_config_summary
)


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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


def fetch_data(conn, table_name: str, columns: List[str], batch_size: int = 500, order_by: str = None) -> Generator[list, None, None]:
    """Fetch data in batches using server-side cursor."""
    cursor_name = f"{table_name}_cursor"
    cursor = conn.cursor(name=cursor_name)
    cursor.itersize = batch_size

    order_clause = f"ORDER BY {order_by}" if order_by else ""
    columns_str = ", ".join(columns)

    cursor.execute(f"SELECT {columns_str} FROM {table_name} {order_clause}")

    while True:
        batch = cursor.fetchmany(batch_size)
        if not batch:
            break
        yield batch

    cursor.close()


def confirm_migration(remote_count: int, table_name: str) -> bool:
    """Ask user to confirm migration if remote table has data."""
    if remote_count > 0:
        logger.warning(f"Remote table '{table_name}' already has {remote_count} rows!")
        try:
            response = input("Do you want to continue? (y/N): ")
            return response.lower() == 'y'
        except EOFError:
            logger.info("Non-interactive mode, continuing...")
            return True
    return True


def migrate_users(local_conn, remote_conn, batch_size: int = 500) -> int:
    """Migrate users table."""
    logger.info("="*60)
    logger.info("Starting users table migration...")
    logger.info("="*60)

    local_count = get_row_count(local_conn, "users")
    remote_count_before = get_row_count(remote_conn, "users")

    logger.info(f"Local users count: {local_count}")
    logger.info(f"Remote users count (before): {remote_count_before}")

    if not confirm_migration(remote_count_before, "users"):
        logger.info("Migration cancelled.")
        return 0

    cursor = remote_conn.cursor()

    columns = [
        "id", "username", "email", "hashed_password", "wx_openid", "wx_nickname",
        "wx_avatar_url", "wx_phone", "push_frequency", "is_active", "is_verified",
        "created_at", "updated_at", "interests_description", "research_interests_text", "rewrite_interest"
    ]

    insert_sql = f"""
        INSERT INTO users ({', '.join(columns)})
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            username = EXCLUDED.username,
            email = EXCLUDED.email,
            hashed_password = EXCLUDED.hashed_password,
            wx_openid = EXCLUDED.wx_openid,
            wx_nickname = EXCLUDED.wx_nickname,
            wx_avatar_url = EXCLUDED.wx_avatar_url,
            wx_phone = EXCLUDED.wx_phone,
            push_frequency = EXCLUDED.push_frequency,
            is_active = EXCLUDED.is_active,
            is_verified = EXCLUDED.is_verified,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at,
            interests_description = EXCLUDED.interests_description,
            research_interests_text = EXCLUDED.research_interests_text,
            rewrite_interest = EXCLUDED.rewrite_interest
    """

    start_time = time.time()
    total_migrated = 0

    try:
        for batch in fetch_data(local_conn, "users", columns, batch_size, "id"):
            execute_batch(cursor, insert_sql, batch, page_size=100)
            remote_conn.commit()
            total_migrated += len(batch)

            progress = (total_migrated / local_count) * 100 if local_count > 0 else 100
            elapsed = time.time() - start_time
            speed = total_migrated / elapsed if elapsed > 0 else 0

            logger.info(f"Progress: {total_migrated}/{local_count} ({progress:.1f}%) - Speed: {speed:.1f} rows/sec")

        logger.info("Syncing sequence...")
        cursor.execute("SELECT MAX(id) FROM users")
        max_id = cursor.fetchone()[0]
        if max_id:
            cursor.execute(f"SELECT setval('users_id_seq', {max_id}, true)")
            remote_conn.commit()
            logger.info(f"Sequence set to: {max_id}")

        remote_count_after = get_row_count(remote_conn, "users")
        elapsed = time.time() - start_time

        logger.info("="*60)
        logger.info("Users migration completed!")
        logger.info(f"  Rows migrated: {total_migrated}")
        logger.info(f"  Remote count (after): {remote_count_after}")
        logger.info(f"  Time elapsed: {elapsed:.2f} seconds")
        logger.info("="*60)

        return total_migrated

    except Exception as e:
        remote_conn.rollback()
        logger.error(f"Error during users migration: {e}")
        raise
    finally:
        cursor.close()


def migrate_research_domains(local_conn, remote_conn, batch_size: int = 500) -> int:
    """Migrate research_domains table."""
    logger.info("="*60)
    logger.info("Starting research_domains table migration...")
    logger.info("="*60)

    local_count = get_row_count(local_conn, "research_domains")
    remote_count_before = get_row_count(remote_conn, "research_domains")

    logger.info(f"Local research_domains count: {local_count}")
    logger.info(f"Remote research_domains count (before): {remote_count_before}")

    if not confirm_migration(remote_count_before, "research_domains"):
        logger.info("Migration cancelled.")
        return 0

    cursor = remote_conn.cursor()

    columns = ["id", "name", "code", "description"]

    insert_sql = f"""
        INSERT INTO research_domains ({', '.join(columns)})
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            code = EXCLUDED.code,
            description = EXCLUDED.description
    """

    start_time = time.time()
    total_migrated = 0

    try:
        for batch in fetch_data(local_conn, "research_domains", columns, batch_size, "id"):
            execute_batch(cursor, insert_sql, batch, page_size=100)
            remote_conn.commit()
            total_migrated += len(batch)

            progress = (total_migrated / local_count) * 100 if local_count > 0 else 100
            elapsed = time.time() - start_time
            speed = total_migrated / elapsed if elapsed > 0 else 0

            logger.info(f"Progress: {total_migrated}/{local_count} ({progress:.1f}%) - Speed: {speed:.1f} rows/sec")

        logger.info("Syncing sequence...")
        cursor.execute("SELECT MAX(id) FROM research_domains")
        max_id = cursor.fetchone()[0]
        if max_id:
            cursor.execute(f"SELECT setval('research_domains_id_seq', {max_id}, true)")
            remote_conn.commit()
            logger.info(f"Sequence set to: {max_id}")

        remote_count_after = get_row_count(remote_conn, "research_domains")
        elapsed = time.time() - start_time

        logger.info("="*60)
        logger.info("Research domains migration completed!")
        logger.info(f"  Rows migrated: {total_migrated}")
        logger.info(f"  Remote count (after): {remote_count_after}")
        logger.info(f"  Time elapsed: {elapsed:.2f} seconds")
        logger.info("="*60)

        return total_migrated

    except Exception as e:
        remote_conn.rollback()
        logger.error(f"Error during research_domains migration: {e}")
        raise
    finally:
        cursor.close()


def migrate_favorite_papers(local_conn, remote_conn, batch_size: int = 500) -> int:
    """Migrate favorite_papers table."""
    logger.info("="*60)
    logger.info("Starting favorite_papers table migration...")
    logger.info("="*60)

    local_count = get_row_count(local_conn, "favorite_papers")
    remote_count_before = get_row_count(remote_conn, "favorite_papers")

    logger.info(f"Local favorite_papers count: {local_count}")
    logger.info(f"Remote favorite_papers count (before): {remote_count_before}")

    if not confirm_migration(remote_count_before, "favorite_papers"):
        logger.info("Migration cancelled.")
        return 0

    cursor = remote_conn.cursor()

    columns = ["id", "user_id", "paper_id", "title", "authors", "abstract", "url", "created_at"]

    insert_sql = f"""
        INSERT INTO favorite_papers ({', '.join(columns)})
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            paper_id = EXCLUDED.paper_id,
            title = EXCLUDED.title,
            authors = EXCLUDED.authors,
            abstract = EXCLUDED.abstract,
            url = EXCLUDED.url,
            created_at = EXCLUDED.created_at
    """

    start_time = time.time()
    total_migrated = 0

    try:
        for batch in fetch_data(local_conn, "favorite_papers", columns, batch_size, "id"):
            execute_batch(cursor, insert_sql, batch, page_size=100)
            remote_conn.commit()
            total_migrated += len(batch)

            progress = (total_migrated / local_count) * 100 if local_count > 0 else 100
            elapsed = time.time() - start_time
            speed = total_migrated / elapsed if elapsed > 0 else 0

            logger.info(f"Progress: {total_migrated}/{local_count} ({progress:.1f}%) - Speed: {speed:.1f} rows/sec")

        logger.info("Syncing sequence...")
        cursor.execute("SELECT MAX(id) FROM favorite_papers")
        max_id = cursor.fetchone()[0]
        if max_id:
            cursor.execute(f"SELECT setval('favorite_papers_id_seq', {max_id}, true)")
            remote_conn.commit()
            logger.info(f"Sequence set to: {max_id}")

        remote_count_after = get_row_count(remote_conn, "favorite_papers")
        elapsed = time.time() - start_time

        logger.info("="*60)
        logger.info("Favorite papers migration completed!")
        logger.info(f"  Rows migrated: {total_migrated}")
        logger.info(f"  Remote count (after): {remote_count_after}")
        logger.info(f"  Time elapsed: {elapsed:.2f} seconds")
        logger.info("="*60)

        return total_migrated

    except Exception as e:
        remote_conn.rollback()
        logger.error(f"Error during favorite_papers migration: {e}")
        raise
    finally:
        cursor.close()


def migrate_paper_recommendations(local_conn, remote_conn, batch_size: int = 500) -> int:
    """Migrate paper_recommendations table."""
    logger.info("="*60)
    logger.info("Starting paper_recommendations table migration...")
    logger.info("="*60)

    local_count = get_row_count(local_conn, "paper_recommendations")
    remote_count_before = get_row_count(remote_conn, "paper_recommendations")

    logger.info(f"Local paper_recommendations count: {local_count}")
    logger.info(f"Remote paper_recommendations count (before): {remote_count_before}")

    if not confirm_migration(remote_count_before, "paper_recommendations"):
        logger.info("Migration cancelled.")
        return 0

    cursor = remote_conn.cursor()

    columns = [
        "id", "username", "paper_id", "title", "authors", "abstract", "url",
        "blog", "blog_title", "blog_abs", "recommendation_date", "viewed",
        "relevance_score", "recommendation_reason", "submitted", "comment",
        "blog_liked", "blog_feedback_date"
    ]

    insert_sql = f"""
        INSERT INTO paper_recommendations ({', '.join(columns)})
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            username = EXCLUDED.username,
            paper_id = EXCLUDED.paper_id,
            title = EXCLUDED.title,
            authors = EXCLUDED.authors,
            abstract = EXCLUDED.abstract,
            url = EXCLUDED.url,
            blog = EXCLUDED.blog,
            blog_title = EXCLUDED.blog_title,
            blog_abs = EXCLUDED.blog_abs,
            recommendation_date = EXCLUDED.recommendation_date,
            viewed = EXCLUDED.viewed,
            relevance_score = EXCLUDED.relevance_score,
            recommendation_reason = EXCLUDED.recommendation_reason,
            submitted = EXCLUDED.submitted,
            comment = EXCLUDED.comment,
            blog_liked = EXCLUDED.blog_liked,
            blog_feedback_date = EXCLUDED.blog_feedback_date
    """

    start_time = time.time()
    total_migrated = 0

    try:
        for batch in fetch_data(local_conn, "paper_recommendations", columns, batch_size, "id"):
            execute_batch(cursor, insert_sql, batch, page_size=100)
            remote_conn.commit()
            total_migrated += len(batch)

            progress = (total_migrated / local_count) * 100 if local_count > 0 else 100
            elapsed = time.time() - start_time
            speed = total_migrated / elapsed if elapsed > 0 else 0

            logger.info(f"Progress: {total_migrated}/{local_count} ({progress:.1f}%) - Speed: {speed:.1f} rows/sec")

        logger.info("Syncing sequence...")
        cursor.execute("SELECT MAX(id) FROM paper_recommendations")
        max_id = cursor.fetchone()[0]
        if max_id:
            cursor.execute(f"SELECT setval('paper_recommendations_id_seq', {max_id}, true)")
            remote_conn.commit()
            logger.info(f"Sequence set to: {max_id}")

        remote_count_after = get_row_count(remote_conn, "paper_recommendations")
        elapsed = time.time() - start_time

        logger.info("="*60)
        logger.info("Paper recommendations migration completed!")
        logger.info(f"  Rows migrated: {total_migrated}")
        logger.info(f"  Remote count (after): {remote_count_after}")
        logger.info(f"  Time elapsed: {elapsed:.2f} seconds")
        logger.info("="*60)

        return total_migrated

    except Exception as e:
        remote_conn.rollback()
        logger.error(f"Error during paper_recommendations migration: {e}")
        raise
    finally:
        cursor.close()


def migrate_job_logs(local_conn, remote_conn, batch_size: int = 500) -> int:
    """Migrate job_logs table."""
    logger.info("="*60)
    logger.info("Starting job_logs table migration...")
    logger.info("="*60)

    local_count = get_row_count(local_conn, "job_logs")
    remote_count_before = get_row_count(remote_conn, "job_logs")

    logger.info(f"Local job_logs count: {local_count}")
    logger.info(f"Remote job_logs count (before): {remote_count_before}")

    if not confirm_migration(remote_count_before, "job_logs"):
        logger.info("Migration cancelled.")
        return 0

    cursor = remote_conn.cursor()

    columns = [
        "id", "job_type", "job_id", "status", "username",
        "start_time", "end_time", "duration_seconds", "error_message",
        "details", "created_at", "updated_at"
    ]

    insert_sql = f"""
        INSERT INTO job_logs ({', '.join(columns)})
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            job_type = EXCLUDED.job_type,
            job_id = EXCLUDED.job_id,
            status = EXCLUDED.status,
            username = EXCLUDED.username,
            start_time = EXCLUDED.start_time,
            end_time = EXCLUDED.end_time,
            duration_seconds = EXCLUDED.duration_seconds,
            error_message = EXCLUDED.error_message,
            details = EXCLUDED.details,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at
    """

    start_time = time.time()
    total_migrated = 0

    try:
        for batch in fetch_data(local_conn, "job_logs", columns, batch_size, "id"):
            execute_batch(cursor, insert_sql, batch, page_size=100)
            remote_conn.commit()
            total_migrated += len(batch)

            progress = (total_migrated / local_count) * 100 if local_count > 0 else 100
            elapsed = time.time() - start_time
            speed = total_migrated / elapsed if elapsed > 0 else 0

            logger.info(f"Progress: {total_migrated}/{local_count} ({progress:.1f}%) - Speed: {speed:.1f} rows/sec")

        logger.info("Syncing sequence...")
        cursor.execute("SELECT MAX(id) FROM job_logs")
        max_id = cursor.fetchone()[0]
        if max_id:
            cursor.execute(f"SELECT setval('job_logs_id_seq', {max_id}, true)")
            remote_conn.commit()
            logger.info(f"Sequence set to: {max_id}")

        remote_count_after = get_row_count(remote_conn, "job_logs")
        elapsed = time.time() - start_time

        logger.info("="*60)
        logger.info("Job logs migration completed!")
        logger.info(f"  Rows migrated: {total_migrated}")
        logger.info(f"  Remote count (after): {remote_count_after}")
        logger.info(f"  Time elapsed: {elapsed:.2f} seconds")
        logger.info("="*60)

        return total_migrated

    except Exception as e:
        remote_conn.rollback()
        logger.error(f"Error during job_logs migration: {e}")
        raise
    finally:
        cursor.close()


def migrate_user_domain_association(local_conn, remote_conn, batch_size: int = 500) -> int:
    """Migrate user_domain_association table."""
    logger.info("="*60)
    logger.info("Starting user_domain_association table migration...")
    logger.info("="*60)

    local_count = get_row_count(local_conn, "user_domain_association")
    remote_count_before = get_row_count(remote_conn, "user_domain_association")

    logger.info(f"Local user_domain_association count: {local_count}")
    logger.info(f"Remote user_domain_association count (before): {remote_count_before}")

    if not confirm_migration(remote_count_before, "user_domain_association"):
        logger.info("Migration cancelled.")
        return 0

    cursor = remote_conn.cursor()

    columns = ["user_id", "domain_id"]

    insert_sql = f"""
        INSERT INTO user_domain_association ({', '.join(columns)})
        VALUES (%s, %s)
        ON CONFLICT (user_id, domain_id) DO NOTHING
    """

    start_time = time.time()
    total_migrated = 0

    try:
        for batch in fetch_data(local_conn, "user_domain_association", columns, batch_size, "user_id"):
            execute_batch(cursor, insert_sql, batch, page_size=100)
            remote_conn.commit()
            total_migrated += len(batch)

            progress = (total_migrated / local_count) * 100 if local_count > 0 else 100
            elapsed = time.time() - start_time
            speed = total_migrated / elapsed if elapsed > 0 else 0

            logger.info(f"Progress: {total_migrated}/{local_count} ({progress:.1f}%) - Speed: {speed:.1f} rows/sec")

        remote_count_after = get_row_count(remote_conn, "user_domain_association")
        elapsed = time.time() - start_time

        logger.info("="*60)
        logger.info("User domain association migration completed!")
        logger.info(f"  Rows migrated: {total_migrated}")
        logger.info(f"  Remote count (after): {remote_count_after}")
        logger.info(f"  Time elapsed: {elapsed:.2f} seconds")
        logger.info("="*60)

        return total_migrated

    except Exception as e:
        remote_conn.rollback()
        logger.error(f"Error during user_domain_association migration: {e}")
        raise
    finally:
        cursor.close()


def migrate_user_retrieve_results(local_conn, remote_conn, batch_size: int = 500) -> int:
    """Migrate user_retrieve_results table."""
    logger.info("="*60)
    logger.info("Starting user_retrieve_results table migration...")
    logger.info("="*60)

    local_count = get_row_count(local_conn, "user_retrieve_results")
    remote_count_before = get_row_count(remote_conn, "user_retrieve_results")

    logger.info(f"Local user_retrieve_results count: {local_count}")
    logger.info(f"Remote user_retrieve_results count (before): {remote_count_before}")

    if not confirm_migration(remote_count_before, "user_retrieve_results"):
        logger.info("Migration cancelled.")
        return 0

    cursor = remote_conn.cursor()

    columns = [
        "id", "username", "query", "search_strategy",
        "recommendation_date", "retrieve_ids", "top_k_ids"
    ]

    insert_sql = f"""
        INSERT INTO user_retrieve_results ({', '.join(columns)})
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            username = EXCLUDED.username,
            query = EXCLUDED.query,
            search_strategy = EXCLUDED.search_strategy,
            recommendation_date = EXCLUDED.recommendation_date,
            retrieve_ids = EXCLUDED.retrieve_ids,
            top_k_ids = EXCLUDED.top_k_ids
    """

    start_time = time.time()
    total_migrated = 0

    try:
        for batch in fetch_data(local_conn, "user_retrieve_results", columns, batch_size, "id"):
            processed_batch = []
            for row in batch:
                processed_row = list(row)
                for idx in [5, 6]:
                    if processed_row[idx] is not None:
                        processed_row[idx] = Json(processed_row[idx])
                processed_batch.append(processed_row)

            execute_batch(cursor, insert_sql, processed_batch, page_size=100)
            remote_conn.commit()
            total_migrated += len(batch)

            progress = (total_migrated / local_count) * 100 if local_count > 0 else 100
            elapsed = time.time() - start_time
            speed = total_migrated / elapsed if elapsed > 0 else 0

            logger.info(f"Progress: {total_migrated}/{local_count} ({progress:.1f}%) - Speed: {speed:.1f} rows/sec")

        logger.info("Syncing sequence...")
        cursor.execute("SELECT MAX(id) FROM user_retrieve_results")
        max_id = cursor.fetchone()[0]
        if max_id:
            cursor.execute(f"SELECT setval('user_retrieve_results_id_seq', {max_id}, true)")
            remote_conn.commit()
            logger.info(f"Sequence set to: {max_id}")

        remote_count_after = get_row_count(remote_conn, "user_retrieve_results")
        elapsed = time.time() - start_time

        logger.info("="*60)
        logger.info("User retrieve results migration completed!")
        logger.info(f"  Rows migrated: {total_migrated}")
        logger.info(f"  Remote count (after): {remote_count_after}")
        logger.info(f"  Time elapsed: {elapsed:.2f} seconds")
        logger.info("="*60)

        return total_migrated

    except Exception as e:
        remote_conn.rollback()
        logger.error(f"Error during user_retrieve_results migration: {e}")
        raise
    finally:
        cursor.close()


# Migration order (based on foreign key dependencies)
MIGRATION_TABLES = [
    ("users", migrate_users),
    ("research_domains", migrate_research_domains),
    ("favorite_papers", migrate_favorite_papers),
    ("paper_recommendations", migrate_paper_recommendations),
    ("job_logs", migrate_job_logs),
    ("user_domain_association", migrate_user_domain_association),
    ("user_retrieve_results", migrate_user_retrieve_results),
]


def main():
    parser = argparse.ArgumentParser(
        description="Migrate PaperIgnition User data to Aliyun RDS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Migrate all tables
  %(prog)s --config scripts/migration_config.yaml
  %(prog)s --batch-size 500                   # Use batch size of 500
  %(prog)s --tables users,favorite_papers     # Migrate specific tables
  %(prog)s --skip-tables job_logs             # Skip specific tables
        """
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='配置文件路径 (默认: scripts/migration_config.yaml)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=500,
        help='Batch size for data migration (default: 500)'
    )
    parser.add_argument(
        '--tables',
        type=str,
        default=None,
        help='Comma-separated list of tables to migrate (default: all)'
    )
    parser.add_argument(
        '--skip-tables',
        type=str,
        default=None,
        help='Comma-separated list of tables to skip'
    )

    args = parser.parse_args()

    local_conn = None
    remote_conn = None

    try:
        # 加载配置
        logger.info("Loading configuration...")
        config = load_migration_config(args.config)

        # 获取数据库配置
        local_db_config = get_local_user_db_config(config)
        remote_db_config = build_aliyun_user_db_config(config)

        # 打印配置摘要
        print_config_summary(config)

        logger.info(f"Local DB: {local_db_config['database']} at {local_db_config['host']}")
        logger.info(f"Remote DB: {remote_db_config['database']} at {remote_db_config['host']}")

        # 连接数据库
        logger.info("Connecting to local database...")
        local_conn = connect_to_db(local_db_config)
        logger.info("Connected to local database")

        logger.info("Connecting to Aliyun RDS...")
        remote_conn = connect_to_db(remote_db_config)
        logger.info("Connected to Aliyun RDS")

        # 确定要迁移的表
        tables_to_migrate = []
        skip_tables = set(args.skip_tables.split(',')) if args.skip_tables else set()

        if args.tables:
            requested_tables = set(args.tables.split(','))
            for table_name, migrate_func in MIGRATION_TABLES:
                if table_name in requested_tables and table_name not in skip_tables:
                    tables_to_migrate.append((table_name, migrate_func))
        else:
            for table_name, migrate_func in MIGRATION_TABLES:
                if table_name not in skip_tables:
                    tables_to_migrate.append((table_name, migrate_func))

        if not tables_to_migrate:
            logger.warning("No tables to migrate!")
            return

        logger.info(f"Tables to migrate: {[t[0] for t in tables_to_migrate]}")

        # 执行迁移
        total_migrated = 0
        for table_name, migrate_func in tables_to_migrate:
            try:
                count = migrate_func(local_conn, remote_conn, args.batch_size)
                total_migrated += count
            except Exception as e:
                logger.error(f"Failed to migrate {table_name}: {e}")
                raise

        logger.info("\n" + "="*60)
        logger.info("SUCCESS! Data migration completed!")
        logger.info(f"Total rows migrated: {total_migrated}")
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
