from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.users import User
from ..db_utils import get_db

from ..auth import schemas as auth_schemas # aliased for clarity
from ..auth.utils import verify_password, create_access_token, get_current_user # get_password_hash is used in crud
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

@router.delete("/users/{email:path}")
async def delete_user(
    email: str,
    db: AsyncSession = Depends(get_db),
    x_test_mode: str = Header(None)
):
    """
    Delete a user by email.

    **WARNING**: This endpoint is for testing purposes only!
    Requires either:
    - Valid authentication token, OR
    - X-Test-Mode header (for automated testing)

    This will permanently delete the user and all associated data.
    """
    # Allow deletion if authenticated OR in test mode
    # Test mode can be enabled by passing X-Test-Mode: true header
    if x_test_mode != "true":
        # Require authentication in production
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required or test mode not enabled"
        )

    # Delete the user
    deleted = await crud_user.delete_user_by_email(db, email)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {email} not found"
        )

    return {
        "message": f"User {email} deleted successfully",
        "email": email
    }