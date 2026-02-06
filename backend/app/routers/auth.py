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