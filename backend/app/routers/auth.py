from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.users import User
from ..db_utils import get_db

from ..auth import schemas as auth_schemas # aliased for clarity
from ..auth.utils import verify_password, create_access_token # get_password_hash is used in crud
from ..crud import user as crud_user # aliased for clarity

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register-email", response_model=auth_schemas.EmailLoginResponse)
async def register_email(user_in: auth_schemas.UserCreateEmail, db: AsyncSession = Depends(get_db)):
    """用户通过邮箱密码注册"""
    db_user = await crud_user.get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此邮箱已被注册"
        )
    created_user = await crud_user.create_user_email(db=db, user_in=user_in)

    # Create access token for auto-login
    access_token = create_access_token(data={"sub": created_user.email})

    # Check if user needs interest setup (new users always do)
    needs_interest_setup = not created_user.interests_description or len(created_user.interests_description) == 0

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "needs_interest_setup": needs_interest_setup,
        "user_info": {
            "email": created_user.email,
            "username": created_user.username
        }
    }

@router.post("/login-email", response_model=auth_schemas.EmailLoginResponse)
async def login_email(user_in: auth_schemas.UserLoginEmail, db: AsyncSession = Depends(get_db)):
    """用户通过邮箱密码登录"""
    user = await crud_user.get_user_by_email(db, email=user_in.email)
    if not user or not user.hashed_password or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email}) # Use email as subject
    
    # 检查用户是否设置了研究兴趣
    # 恢复到原始逻辑，移除所有DEBUG打印
    needs_interest_setup = not user.interests_description or len(user.interests_description) == 0
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "needs_interest_setup": needs_interest_setup,
        "user_info": {
            "email": user.email,
            "username": user.username
        }
    }


# Existing username/password login (can be kept or deprecated based on strategy)
@router.post("/login", response_model=auth_schemas.Token)
async def login_username_password(user_data: auth_schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    """用户通过用户名密码登录"""
    user = await crud_user.get_user_by_username(db, username=user_data.username)
    if not user or not user.hashed_password or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/wechat_login", response_model=auth_schemas.WechatLoginResponse)
async def wechat_login(wechat_data: auth_schemas.WechatLogin, db: AsyncSession = Depends(get_db)):
    """微信小程序登录"""
    # This is a simplified placeholder for WeChat OAuth flow.
    # In a real application, you would exchange wechat_data.code for openid and session_key with WeChat servers.
    # openid = await call_wechat_api(wechat_data.code) # Placeholder for actual API call
    
    # For demonstration, using a mock openid. Replace with actual openid retrieval.
    mock_openid = f"mock_openid_for_code_{wechat_data.code}" 
    
    user = await crud_user.get_user_by_username(db, username=mock_openid) # Assuming wx_openid is stored as username for wechat users
    # Or if wx_openid field is primary lookup for wechat:
    # result = await db.execute(select(User).where(User.wx_openid == mock_openid))
    # user = result.scalars().first()

    needs_interest_setup = True
    if not user:
        # Assuming a new WeChat user always needs profile completion for now.
        # You might get nickname/avatar if WeChat API provides it with code exchange.
        user = await crud_user.create_user_wechat(db=db, openid=mock_openid, nickname="微信用户", avatar_url=None)
    else:
        # 检查用户是否设置了研究兴趣
        needs_interest_setup = not user.interests_description or len(user.interests_description) == 0

    access_token = create_access_token(data={"sub": user.username}) # or user.wx_openid
    return auth_schemas.WechatLoginResponse(
        access_token=access_token, 
        token_type="bearer", 
        needs_interest_setup=needs_interest_setup,
        user_info={
            "email": user.email if user.email else "wx_user@example.com",
            "username": user.username
        }
    ) 