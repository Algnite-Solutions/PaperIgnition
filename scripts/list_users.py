#!/usr/bin/env python3
"""
List all users in the database

Usage:
    python scripts/list_users.py
"""

import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.config_utils import load_config
from backend.app.db_utils import DatabaseManager
from sqlalchemy import select
from backend.app.models.users import User


async def list_all_users():
    """List all users in database"""
    print("🔍 Listing all users in database...")
    print()

    # Load configuration
    print("⚙️  Loading configuration...")
    config = load_config('backend/configs/test_config.yaml', service='backend')

    # Initialize database manager
    print("🔗 Connecting to database...")
    db_manager = DatabaseManager(config['USER_DB'])
    await db_manager.initialize()

    try:
        async with db_manager.get_session() as db:
            # Get all users
            result = await db.execute(select(User))
            users = result.scalars().all()

            if not users:
                print("❌ No users found in database!")
                return

            print(f"✅ Found {len(users)} user(s):")
            print()
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"{'ID':<6} {'Username':<20} {'Email':<35} {'Created':<20}")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            for user in users:
                created_str = user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "N/A"
                print(f"{user.id:<6} {user.username:<20} {user.email:<35} {created_str:<20}")

            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await db_manager.close()
        print("🔌 Database connection closed")


if __name__ == "__main__":
    asyncio.run(list_all_users())
