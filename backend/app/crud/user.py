from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from typing import Optional

from ..models.users import User
from ..auth import schemas as auth_schemas
from ..auth.utils import get_password_hash

async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """
    通过ID获取用户
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()

async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """
    通过用户名获取用户
    """
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """
    通过邮箱获取用户
    """
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()

async def create_user_email(db: AsyncSession, user_in: auth_schemas.UserCreateEmail) -> User:
    """
    通过邮箱和密码创建新用户
    """
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        username=user_in.username  # Use the provided username
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def create_user_wechat(db: AsyncSession, openid: str, nickname: Optional[str] = None, avatar_url: Optional[str] = None) -> User:
    """
    创建微信用户 (如果不存在)
    """
    # For WeChat users, username might be initially set to openid or a generated unique value
    # Or, it could be prompted for after first login.
    # For simplicity here, if wx_openid is unique, username can be derived or also set to wx_openid initially.
    # The current User model has username as unique and not nullable if email/password is not used.
    # Let's assume wx_openid can serve as a unique username if a dedicated one isn't provided.
    db_user = User(
        wx_openid=openid,
        username=openid, # Using openid as username for WeChat users if no other username is provided
        wx_nickname=nickname,
        wx_avatar_url=avatar_url,
        is_verified=True # WeChat users are implicitly verified by WeChat
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user 