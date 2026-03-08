#!/usr/bin/env python3
"""
Reset password for a user via direct database access

Usage:
    python scripts/reset_password.py <email> [new_password]

Example:
    python scripts/reset_password.py qi.zhu.ckc@gmail.com newpass123
"""

import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.config_utils import load_config
from backend.app.db_utils import DatabaseManager
from backend.app.crud import user as crud_user
from backend.app.auth.utils import get_password_hash
from sqlalchemy import update
from backend.app.models.users import User


async def reset_password(email: str, new_password: str = "newpass123"):
    """Reset user password in database"""
    print(f"🔐 Resetting password for: {email}")
    print(f"📧 New password will be: {new_password}")
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
            # Check if user exists
            print(f"🔍 Looking up user: {email}")
            user = await crud_user.get_user_by_email(db, email)

            if not user:
                print(f"❌ User not found: {email}")
                return False

            print(f"✅ Found user: {user.username} (ID: {user.id})")

            # Hash new password
            print(f"🔒 Hashing new password...")
            new_hash = get_password_hash(new_password)

            # Update password
            print(f"💾 Updating password in database...")
            await db.execute(
                update(User).where(User.email == email).values(hashed_password=new_hash)
            )
            await db.commit()

            print()
            print("✅ Password reset successful!")
            print()
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"📧 Email:    {email}")
            print(f"🔑 Password: {new_password}")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print()
            print("You can now login at: http://localhost:8080/login.html")
            print()

            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await db_manager.close()
        print("🔌 Database connection closed")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/reset_password.py <email> [new_password]")
        print("Example: python scripts/reset_password.py qi.zhu.ckc@gmail.com newpass123")
        sys.exit(1)

    email = sys.argv[1]
    new_password = sys.argv[2] if len(sys.argv) > 2 else "newpass123"

    asyncio.run(reset_password(email, new_password))
