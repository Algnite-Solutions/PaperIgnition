#!/usr/bin/env python3
"""
Export database schema from PostgreSQL to Markdown

Usage:
    python scripts/db_schema.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.shared.config_utils import load_config
from backend.app.db_utils import DatabaseManager
from sqlalchemy import text


async def export_schema():
    """Export database schema from PostgreSQL"""
    print("🔍 Connecting to database...")
    print()

    # Load configuration
    config = load_config('backend/configs/app_config.yaml', service='backend')

    # Initialize database manager
    print("🔗 Connecting to User DB...")
    db_manager = DatabaseManager(config['USER_DB'])
    await db_manager.initialize()

    try:
        async with db_manager.get_session() as db:
            # Get all tables
            result = await db.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]

            print(f"✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table}")
            print()

            # Export schema for each table
            markdown = []
            markdown.append("# Database Schema\n")
            markdown.append("## Tables\n")

            for table in tables:
                print(f"📄 Exporting schema for: {table}")

                # Get table columns
                result = await db.execute(text(f"""
                    SELECT
                        column_name,
                        data_type,
                        character_maximum_length,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """))

                markdown.append(f"### {table}\n")
                markdown.append("| Column | Type | Nullable | Default |\n")
                markdown.append("|--------|------|----------|----------|\n")

                for row in result:
                    column_name, data_type, max_length, is_nullable, default_val = row

                    # Format data type
                    if max_length:
                        type_str = f"{data_type}({max_length})"
                    else:
                        type_str = data_type

                    # Format nullable
                    nullable = "YES" if is_nullable == "YES" else "NO"

                    # Format default
                    default_val = str(default_val) if default_val else ""

                    markdown.append(f"| {column_name} | {type_str} | {nullable} | {default_val} |\n")

                markdown.append("\n")

                # Get constraints
                result = await db.execute(text(f"""
                    SELECT
                        constraint_name,
                        constraint_type
                    FROM information_schema.table_constraints
                    WHERE table_name = '{table}'
                    ORDER BY constraint_type, constraint_name
                """))

                constraints = list(result)
                if constraints:
                    markdown.append("**Constraints:**\n")
                    for constraint_name, constraint_type in constraints:
                        markdown.append(f"- {constraint_type}: {constraint_name}\n")
                    markdown.append("\n")

            # Write to file
            output_file = project_root / "DATABASE_SCHEMA.md"
            with open(output_file, 'w') as f:
                f.writelines(markdown)

            print()
            print(f"✅ Schema exported to: {output_file}")
            print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(export_schema())
