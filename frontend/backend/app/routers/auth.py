from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_

from ..db.database import get_db
from ..models.user import User
from ..auth.schemas import UserLogin, Token, UserOut, WechatLogin, WechatLoginResponse
from ..auth.utils import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    # 查找用户
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalars().first()
    
    # 验证用户和密码
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 生成访问令牌
    access_token = create_access_token(data={"sub": user.username})
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/wechat_login", response_model=WechatLoginResponse)
async def wechat_login(wechat_data: WechatLogin, db: AsyncSession = Depends(get_db)):
    """微信小程序登录"""
    # TODO: Implement WeChat authentication logic using wechat_data.code
    # This involves calling WeChat's API to exchange code for session_key and openid
    
    # Example placeholder logic:
    # 1. Call WeChat API with code to get openid
    # wechat_info = await get_wechat_openid(wechat_data.code) # Hypothetical function
    # openid = wechat_info.openid # Assuming you get openid here
    openid = "placeholder_openid" # Placeholder
    
    # 2. Find user by openid
    result = await db.execute(select(User).where(User.wx_openid == openid))
    user = result.scalars().first()
    
    # 3. If user doesn't exist, create a new user (minimal info first)
    if not user:
        # TODO: Get nickname and avatar from WeChat API if possible
        new_user = User(wx_openid=openid)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        user = new_user
        
    # 4. Generate access token
    # Using openid as sub for now, you might want to use user.id or username if available
    access_token = create_access_token(data={"sub": user.wx_openid})
    
    # 5. Check if user needs to complete profile (e.g., email is None)
    needs_profile_completion = user.email is None # Or check other fields like interests_description
    
    # Return Token and needs_profile_completion flag
    return WechatLoginResponse(access_token=access_token, token_type="bearer", needs_profile_completion=needs_profile_completion) 