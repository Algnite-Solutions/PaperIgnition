#!/usr/bin/env python3
"""
Build PaperIgnition Tables in Aliyun RDS PostgreSQL

This script creates the `papers` and `text_chunks` tables in Aliyun RDS PostgreSQL,
matching the local database schema.

Usage:
    python scripts/build_paperignition_tables_in_aliyun.py
    python scripts/build_paperignition_tables_in_aliyun.py --config orchestrator/production_config.yaml
    python scripts/build_paperignition_tables_in_aliyun.py --drop-existing  # WARNING: deletes all data!
    python scripts/build_paperignition_tables_in_aliyun.py --skip-db-create  # skip DB creation
"""

import sys
import logging
import argparse
from pathlib import Path

import yaml
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_aliyun_config(config_path: str = None) -> dict:
    """
    Load Aliyun RDS configuration from config file.

    Args:
        config_path: Path to the config file (yaml)

    Returns:
        Dictionary containing Aliyun RDS configuration
    """
    # Determine config path
    if config_path is None:
        # Try to find config in common locations
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
                logger.info(f"Using config file: {config_path}")
                break

        if config_path is None:
            raise FileNotFoundError(
                "Config file not found. Please specify --config or ensure "
                "orchestrator/production_config.yaml exists."
            )

    # Load config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    if 'aliyun_rds' not in config:
        raise ValueError(f"'aliyun_rds' section not found in {config_path}")

    aliyun_rds_config = config['aliyun_rds']

    # Check if enabled
    if not aliyun_rds_config.get('enabled', False):
        logger.warning("Aliyun RDS is not enabled in the config. Proceeding anyway...")

    return aliyun_rds_config


def build_db_config(aliyun_config: dict) -> dict:
    """
    Build PostgreSQL connection config dict from Aliyun config.

    Args:
        aliyun_config: Aliyun RDS configuration dict

    Returns:
        Dictionary with connection parameters for psycopg2
    """
    return {
        "host": aliyun_config.get('db_host', 'localhost'),
        "port": int(aliyun_config.get('db_port', '5432')),
        "user": aliyun_config.get('db_user', 'postgres'),
        "password": aliyun_config.get('db_password', ''),
        "database": aliyun_config.get('db_name_paper', 'test')
    }


def connect_to_db(db_config: dict, dbname: str = None) -> psycopg2.extensions.connection:
    """
    Connect to PostgreSQL database.

    Args:
        db_config: Database configuration dict
        dbname: Database name (overrides config if provided)

    Returns:
        psycopg2 connection object
    """
    config = db_config.copy()
    if dbname is not None:
        config['database'] = dbname

    return psycopg2.connect(**config)


def create_database_if_not_exists(db_config: dict, db_name: str) -> None:
    """
    Create the database if it doesn't exist.

    Args:
        db_config: Database configuration dict
        db_name: Name of the database to create
    """
    print("\n" + "="*50)
    print("正在连接到阿里云RDS PostgreSQL...")
    print(f"Host: {db_config['host']}")
    print(f"Port: {db_config['port']}")
    print("="*50)

    logger.info(f"Checking if database '{db_name}' exists...")

    # Connect to 'postgres' database to create a new database
    conn = connect_to_db(db_config, dbname='postgres')
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        # Check if database exists
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
    """
    Create the papers and text_chunks tables with all indexes.

    Args:
        db_config: Database configuration dict
        drop_existing: If True, drop existing tables before creating new ones
    """
    logger.info("Connecting to database for table creation...")
    logger.info(f"Database: {db_config['database']}")

    conn = connect_to_db(db_config)
    cursor = conn.cursor()

    try:
        # Drop existing tables if requested
        if drop_existing:
            logger.warning("Dropping existing tables...")
            cursor.execute("DROP TABLE IF EXISTS text_chunks CASCADE")
            cursor.execute("DROP TABLE IF EXISTS papers CASCADE")
            cursor.execute("DROP SEQUENCE IF EXISTS papers_id_seq CASCADE")
            conn.commit()

        # Create papers table
        logger.info("Creating papers table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY,
                doc_id VARCHAR NOT NULL UNIQUE,
                title VARCHAR NOT NULL,
                abstract TEXT,
                authors JSON,
                categories JSON,
                published_date VARCHAR,
                pdf_data BYTEA,
                chunk_ids JSON,
                figure_ids JSON,
                image_storage JSON,
                table_ids JSON,
                extra_metadata JSON,
                pdf_path VARCHAR,
                "HTML_path" VARCHAR,
                blog TEXT,
                comments TEXT
            )
        """)

        # Create sequence for auto-incrementing id
        cursor.execute("CREATE SEQUENCE IF NOT EXISTS papers_id_seq")
        cursor.execute("ALTER TABLE papers ALTER COLUMN id SET DEFAULT nextval('papers_id_seq')")

        # Create full-text search index on title and abstract
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fts ON papers
            USING gin (to_tsvector('english', COALESCE(title, '')::text || ' ' || COALESCE(abstract, ''::text)))
        """)

        # Create text_chunks table
        logger.info("Creating text_chunks table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS text_chunks (
                id VARCHAR PRIMARY KEY,
                doc_id VARCHAR NOT NULL,
                chunk_id VARCHAR NOT NULL,
                text_content TEXT NOT NULL,
                chunk_order INTEGER NOT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE
            )
        """)

        # Create unique constraint on doc_id and chunk_id
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_chunk_doc_chunk ON text_chunks (doc_id, chunk_id)
        """)

        # Create index on doc_id for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_doc_id ON text_chunks (doc_id)
        """)

        # Create index on doc_id and chunk_order for ordered retrieval
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_order ON text_chunks (doc_id, chunk_order)
        """)

        # Create full-text search index on text_content
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_text_fts ON text_chunks
            USING gin (to_tsvector('english', text_content))
        """)

        conn.commit()
        logger.info("All tables and indexes created successfully!")

    finally:
        cursor.close()
        conn.close()


def verify_tables(db_config: dict) -> None:
    """
    Verify that tables were created correctly.

    Args:
        db_config: Database configuration dict
    """
    logger.info("Verifying tables...")

    conn = connect_to_db(db_config)
    cursor = conn.cursor()

    try:
        # Check if papers table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'papers'
            );
        """)
        papers_exists = cursor.fetchone()[0]

        # Check if text_chunks table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'text_chunks'
            );
        """)
        text_chunks_exists = cursor.fetchone()[0]

        # List all indexes for papers table
        cursor.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'papers';
        """)
        papers_indexes = [row[0] for row in cursor.fetchall()]

        # List all indexes for text_chunks table
        cursor.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'text_chunks';
        """)
        text_chunks_indexes = [row[0] for row in cursor.fetchall()]

    finally:
        cursor.close()
        conn.close()

    logger.info("\n" + "="*60)
    logger.info("Table Verification Results:")
    logger.info("="*60)

    logger.info(f"\n✓ papers table: {'EXISTS' if papers_exists else 'MISSING'}")
    if papers_exists:
        logger.info(f"  Indexes: {', '.join(papers_indexes)}")

    logger.info(f"\n✓ text_chunks table: {'EXISTS' if text_chunks_exists else 'MISSING'}")
    if text_chunks_exists:
        logger.info(f"  Indexes: {', '.join(text_chunks_indexes)}")

    logger.info("\n" + "="*60)

    if not (papers_exists and text_chunks_exists):
        raise RuntimeError("Table verification failed! Some tables are missing.")


def main():
    parser = argparse.ArgumentParser(
        description="Build PaperIgnition tables in Aliyun RDS PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Use default config
  %(prog)s --config path/to/config.yaml # Use specific config
  %(prog)s --drop-existing              # Drop existing tables first (WARNING!)
  %(prog)s --skip-db-create             # Skip database creation step
        """
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to config file (default: auto-detect orchestrator/production_config.yaml)'
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
        # Load configuration
        logger.info("Loading Aliyun RDS configuration...")
        aliyun_config = load_aliyun_config(args.config)

        # Print connection info (hide password)
        safe_config = aliyun_config.copy()
        safe_config['db_password'] = '***'
        logger.info(f"Aliyun RDS config: {safe_config}")

        # Build db config
        db_config = build_db_config(aliyun_config)
        db_name = aliyun_config.get('db_name_paper', 'paperignition')

        # Create database if needed
        if not args.skip_db_create:
            create_database_if_not_exists(db_config, db_name)
        else:
            logger.info("Skipping database creation step (--skip-db-create flag set)")

        # Create tables
        create_tables(db_config, drop_existing=args.drop_existing)

        # Verify tables
        verify_tables(db_config)

        logger.info("\n" + "="*60)
        logger.info("SUCCESS! PaperIgnition tables built in Aliyun RDS!")
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
