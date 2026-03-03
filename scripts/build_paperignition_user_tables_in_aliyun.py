#!/usr/bin/env python3
"""
Build PaperIgnition User Tables in Aliyun RDS PostgreSQL

This script creates all tables in the `paperignition_user` database in Aliyun RDS PostgreSQL,
including: users, favorite_papers, paper_recommendations, job_logs, research_domains,
user_domain_association, and user_retrieve_results.

Usage:
    python scripts/build_paperignition_user_tables_in_aliyun.py
    python scripts/build_paperignition_user_tables_in_aliyun.py --config scripts/migration_config.yaml
    python scripts/build_paperignition_user_tables_in_aliyun.py --drop-existing  # WARNING: deletes all data!
    python scripts/build_paperignition_user_tables_in_aliyun.py --skip-db-create  # skip DB creation
"""

import sys
import logging
import argparse
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from migration_utils import (
    load_migration_config,
    get_aliyun_rds_config,
    print_config_summary
)


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def build_db_config(aliyun_config: dict) -> dict:
    """Build PostgreSQL connection config dict from Aliyun config."""
    return {
        "host": aliyun_config.get('db_host', 'localhost'),
        "port": int(aliyun_config.get('db_port', '5432')),
        "user": aliyun_config.get('db_user', 'postgres'),
        "password": aliyun_config.get('db_password', ''),
        "database": aliyun_config.get('db_name_user', 'paperignition_user')
    }


def connect_to_db(db_config: dict, dbname: str = None) -> psycopg2.extensions.connection:
    """Connect to PostgreSQL database."""
    config = db_config.copy()
    if dbname is not None:
        config['database'] = dbname
    return psycopg2.connect(**config)


def create_database_if_not_exists(db_config: dict, db_name: str) -> None:
    """Create the database if it doesn't exist."""
    print("\n" + "="*50)
    print("正在连接到阿里云RDS PostgreSQL...")
    print(f"Host: {db_config['host']}")
    print(f"Port: {db_config['port']}")
    print("="*50)

    logger.info(f"Checking if database '{db_name}' exists...")

    conn = connect_to_db(db_config, dbname='postgres')
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        exists = cursor.fetchone()

        if not exists:
            logger.info(f"Creating database '{db_name}'...")
            cursor.execute(f"CREATE DATABASE {db_name} ENCODING 'UTF8'")
            logger.info(f"Database '{db_name}' created successfully.")
        else:
            logger.info(f"Database '{db_name}' already exists.")
    finally:
        cursor.close()
        conn.close()


def create_tables(db_config: dict, drop_existing: bool = False) -> None:
    """Create all tables for paperignition_user database with all indexes."""
    logger.info("Connecting to database for table creation...")
    logger.info(f"Database: {db_config['database']}")

    conn = connect_to_db(db_config)
    cursor = conn.cursor()

    try:
        if drop_existing:
            logger.warning("Dropping existing tables...")
            cursor.execute("DROP TABLE IF EXISTS user_retrieve_results CASCADE")
            cursor.execute("DROP TABLE IF EXISTS user_domain_association CASCADE")
            cursor.execute("DROP TABLE IF EXISTS paper_recommendations CASCADE")
            cursor.execute("DROP TABLE IF EXISTS job_logs CASCADE")
            cursor.execute("DROP TABLE IF EXISTS favorite_papers CASCADE")
            cursor.execute("DROP TABLE IF EXISTS research_domains CASCADE")
            cursor.execute("DROP TABLE IF EXISTS users CASCADE")
            cursor.execute("DROP SEQUENCE IF EXISTS users_id_seq CASCADE")
            cursor.execute("DROP SEQUENCE IF EXISTS favorite_papers_id_seq CASCADE")
            cursor.execute("DROP SEQUENCE IF EXISTS job_logs_id_seq CASCADE")
            cursor.execute("DROP SEQUENCE IF EXISTS paper_recommendations_id_seq CASCADE")
            cursor.execute("DROP SEQUENCE IF EXISTS research_domains_id_seq CASCADE")
            cursor.execute("DROP SEQUENCE IF EXISTS user_retrieve_results_id_seq CASCADE")
            conn.commit()

        # 1. Create users table
        logger.info("Creating users table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50),
                email VARCHAR(100),
                hashed_password VARCHAR(100),
                wx_openid VARCHAR(50),
                wx_nickname VARCHAR(50),
                wx_avatar_url VARCHAR(255),
                wx_phone VARCHAR(20),
                push_frequency VARCHAR(20),
                is_active BOOLEAN,
                is_verified BOOLEAN,
                created_at TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE,
                interests_description TEXT[],
                research_interests_text TEXT,
                rewrite_interest TEXT
            )
        """)

        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_wx_openid ON users (wx_openid)")

        # 2. Create research_domains table
        logger.info("Creating research_domains table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_domains (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                code VARCHAR(20),
                description TEXT
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS ix_research_domains_id ON research_domains (id)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_research_domains_name ON research_domains (name)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS research_domains_code_key ON research_domains (code)")

        # 3. Create favorite_papers table
        logger.info("Creating favorite_papers table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorite_papers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                paper_id VARCHAR(50),
                title VARCHAR(255),
                authors VARCHAR(255),
                abstract TEXT,
                url VARCHAR(255),
                created_at TIMESTAMP WITH TIME ZONE
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS ix_favorite_papers_id ON favorite_papers (id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_favorite_papers_paper_id ON favorite_papers (paper_id)")

        cursor.execute("""
            ALTER TABLE favorite_papers
            DROP CONSTRAINT IF EXISTS favorite_papers_user_id_fkey
        """)
        cursor.execute("""
            ALTER TABLE favorite_papers
            ADD CONSTRAINT favorite_papers_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id)
        """)

        # 4. Create paper_recommendations table
        logger.info("Creating paper_recommendations table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_recommendations (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50),
                paper_id VARCHAR(50),
                title VARCHAR(255),
                authors VARCHAR(255),
                abstract TEXT,
                url VARCHAR(255),
                blog TEXT,
                blog_title TEXT,
                blog_abs TEXT,
                recommendation_date TIMESTAMP WITH TIME ZONE,
                viewed BOOLEAN,
                relevance_score DOUBLE PRECISION,
                recommendation_reason TEXT,
                submitted VARCHAR(255),
                comment TEXT,
                blog_liked BOOLEAN,
                blog_feedback_date TIMESTAMP WITH TIME ZONE
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS ix_paper_recommendations_id ON paper_recommendations (id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_paper_recommendations_paper_id ON paper_recommendations (paper_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_paper_recommendations_username ON paper_recommendations (username)")

        cursor.execute("""
            ALTER TABLE paper_recommendations
            DROP CONSTRAINT IF EXISTS paper_recommendations_username_fkey
        """)
        cursor.execute("""
            ALTER TABLE paper_recommendations
            ADD CONSTRAINT paper_recommendations_username_fkey
            FOREIGN KEY (username) REFERENCES users(username)
        """)

        # 5. Create job_logs table
        logger.info("Creating job_logs table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_logs (
                id SERIAL PRIMARY KEY,
                job_type VARCHAR(100) NOT NULL,
                job_id VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL,
                username VARCHAR(50),
                start_time TIMESTAMP WITH TIME ZONE,
                end_time TIMESTAMP WITH TIME ZONE,
                duration_seconds DOUBLE PRECISION,
                error_message TEXT,
                details TEXT,
                created_at TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS ix_job_logs_id ON job_logs (id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_job_logs_job_id ON job_logs (job_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_job_logs_job_type ON job_logs (job_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_job_logs_status ON job_logs (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_job_logs_username ON job_logs (username)")

        # 6. Create user_domain_association table
        logger.info("Creating user_domain_association table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_domain_association (
                user_id INTEGER NOT NULL,
                domain_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, domain_id)
            )
        """)

        cursor.execute("""
            ALTER TABLE user_domain_association
            DROP CONSTRAINT IF EXISTS user_domain_association_user_id_fkey
        """)
        cursor.execute("""
            ALTER TABLE user_domain_association
            ADD CONSTRAINT user_domain_association_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id)
        """)
        cursor.execute("""
            ALTER TABLE user_domain_association
            DROP CONSTRAINT IF EXISTS user_domain_association_domain_id_fkey
        """)
        cursor.execute("""
            ALTER TABLE user_domain_association
            ADD CONSTRAINT user_domain_association_domain_id_fkey
            FOREIGN KEY (domain_id) REFERENCES research_domains(id)
        """)

        # 7. Create user_retrieve_results table
        logger.info("Creating user_retrieve_results table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_retrieve_results (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50),
                query TEXT NOT NULL,
                search_strategy VARCHAR(50) NOT NULL,
                recommendation_date TIMESTAMP WITH TIME ZONE,
                retrieve_ids JSON NOT NULL,
                top_k_ids JSON NOT NULL
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_retrieve_results_id ON user_retrieve_results (id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_retrieve_results_username ON user_retrieve_results (username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_username_date ON user_retrieve_results (username, recommendation_date)")

        cursor.execute("""
            ALTER TABLE user_retrieve_results
            DROP CONSTRAINT IF EXISTS user_retrieve_results_username_fkey
        """)
        cursor.execute("""
            ALTER TABLE user_retrieve_results
            ADD CONSTRAINT user_retrieve_results_username_fkey
            FOREIGN KEY (username) REFERENCES users(username)
        """)

        conn.commit()
        logger.info("All tables and indexes created successfully!")

    finally:
        cursor.close()
        conn.close()


def verify_tables(db_config: dict) -> None:
    """Verify that all tables were created correctly."""
    logger.info("Verifying tables...")

    conn = connect_to_db(db_config)
    cursor = conn.cursor()

    expected_tables = [
        'users',
        'favorite_papers',
        'paper_recommendations',
        'job_logs',
        'research_domains',
        'user_domain_association',
        'user_retrieve_results'
    ]

    try:
        results = {}
        for table_name in expected_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                );
            """, (table_name,))
            table_exists = cursor.fetchone()[0]

            cursor.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = %s;
            """, (table_name,))
            indexes = [row[0] for row in cursor.fetchall()]

            results[table_name] = {
                'exists': table_exists,
                'indexes': indexes
            }

    finally:
        cursor.close()
        conn.close()

    logger.info("\n" + "="*60)
    logger.info("Table Verification Results:")
    logger.info("="*60)

    all_exist = True
    for table_name, info in results.items():
        status = 'EXISTS' if info['exists'] else 'MISSING'
        logger.info(f"\n{'✓' if info['exists'] else '✗'} {table_name} table: {status}")
        if info['exists'] and info['indexes']:
            logger.info(f"  Indexes: {', '.join(info['indexes'])}")
        if not info['exists']:
            all_exist = False

    logger.info("\n" + "="*60)

    if not all_exist:
        raise RuntimeError("Table verification failed! Some tables are missing.")


def main():
    parser = argparse.ArgumentParser(
        description="Build PaperIgnition User tables in Aliyun RDS PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Use default config
  %(prog)s --config scripts/migration_config.yaml
  %(prog)s --drop-existing              # Drop existing tables first (WARNING!)
  %(prog)s --skip-db-create             # Skip database creation step
        """
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='配置文件路径 (默认: scripts/migration_config.yaml)'
    )
    parser.add_argument(
        '--drop-existing',
        action='store_true',
        help='Drop existing tables before creating new ones (WARNING: this will delete all data!)'
    )
    parser.add_argument(
        '--skip-db-create',
        action='store_true',
        help='Skip database creation step (use if database already exists)'
    )

    args = parser.parse_args()

    try:
        # 加载配置
        logger.info("Loading Aliyun RDS configuration...")
        config = load_migration_config(args.config)
        aliyun_config = get_aliyun_rds_config(config)

        # 打印配置摘要
        print_config_summary(config)

        # 构建数据库配置
        db_config = build_db_config(aliyun_config)
        db_name = aliyun_config.get('db_name_user', 'paperignition_user')

        # 创建数据库
        if not args.skip_db_create:
            create_database_if_not_exists(db_config, db_name)
        else:
            logger.info("Skipping database creation step (--skip-db-create flag set)")

        # 创建表
        create_tables(db_config, drop_existing=args.drop_existing)

        # 验证表
        verify_tables(db_config)

        logger.info("\n" + "="*60)
        logger.info("SUCCESS! PaperIgnition User tables built in Aliyun RDS!")
        logger.info("="*60)
        logger.info(f"\nYou can now connect to Aliyun RDS at:")
        logger.info(f"  Host: {aliyun_config['db_host']}")
        logger.info(f"  Port: {aliyun_config['db_port']}")
        logger.info(f"  Database: {db_name}")
        logger.info(f"  User: {aliyun_config['db_user']}")

    except Exception as e:
        logger.error(f"\n{'='*60}")
        logger.error(f"ERROR: Failed to build tables in Aliyun RDS!")
        logger.error(f"{'='*60}")
        logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
