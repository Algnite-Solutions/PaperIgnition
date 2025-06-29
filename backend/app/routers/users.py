from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from backend.models.user import User, ResearchDomain, user_domain_association
from backend.db.user_db import get_db

from ..auth.schemas import UserOut, UserProfileUpdate
from ..auth.utils import get_current_user

# 请求模型
class UserInterestUpdate(BaseModel):
    research_domain_ids: List[int]
    interests_description: Optional[List[str]] = None

# Response model for research domains (assuming a simple list of id and name)
class ResearchDomainOut(BaseModel):
    id: int
    name: str

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserOut)
async def get_current_user_info(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取当前用户信息（现在使用JWT验证）"""
    # 获取用户的研究领域ID
    research_domain_ids = []
    if current_user.research_domains:
        for domain in current_user.research_domains:
            research_domain_ids.append(domain.id)
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "interests_description": current_user.interests_description or [],
        "research_domain_ids": research_domain_ids
    }

@router.post("/interests", response_model=UserOut)
async def update_interests(
    interests: UserInterestUpdate, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新用户研究兴趣"""
    user = current_user
    
    # 更新兴趣关键词数组
    if interests.interests_description is not None:
        user.interests_description = interests.interests_description
    
    # 获取研究领域对象
    result = await db.execute(
        select(ResearchDomain).where(ResearchDomain.id.in_(interests.research_domain_ids))
    )
    domains = result.scalars().all()
    
    # 检查所有ID是否有效
    if len(domains) != len(interests.research_domain_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="一个或多个研究领域ID无效"
        )
    
    # 更新用户的研究领域
    user.research_domains = domains
    
    await db.commit()
    await db.refresh(user)
    
    # 获取更新后的用户研究领域ID
    updated_domain_ids = [domain.id for domain in user.research_domains]
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "interests_description": user.interests_description or [],
        "research_domain_ids": updated_domain_ids
    }

@router.get("/research_domains", response_model=List[ResearchDomainOut])
async def get_research_domains(db: AsyncSession = Depends(get_db)):
    """获取所有研究领域列表"""
    result = await db.execute(select(ResearchDomain))
    research_domains = result.scalars().all()
    return research_domains

@router.put("/me/profile", response_model=UserOut)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新当前用户的个人资料"""
    if profile_data.email is not None:
        current_user.email = profile_data.email
    if profile_data.push_frequency is not None:
        current_user.push_frequency = profile_data.push_frequency
    if profile_data.interests_description is not None:
        current_user.interests_description = profile_data.interests_description
        
    if profile_data.research_domain_ids is not None:
        result = await db.execute(select(ResearchDomain).where(ResearchDomain.id.in_(profile_data.research_domain_ids)))
        research_domains = result.scalars().all()
        if len(research_domains) != len(profile_data.research_domain_ids):
             raise HTTPException(status_code=400, detail="一个或多个提供的研究领域ID无效。")
        current_user.research_domains = research_domains

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return current_user 

@router.get("/all", response_model=List[UserOut])
async def get_all_users_info(db: AsyncSession = Depends(get_db)):
    """获取所有用户信息（username 和 interests_description）"""
    result = await db.execute(select(User))
    users = result.scalars().all()
    
    response_users = []
    for user in users:
        research_domain_ids = []
        # if user.research_domains:
        #     for domain in user.research_domains:
        #         research_domain_ids.append(domain.id)
        
        response_users.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "interests_description": user.interests_description or [],
            "research_domain_ids": research_domain_ids
        })
    return response_users 

@router.get("/by_email/{username}", response_model=UserOut)
async def get_user_by_email(
    username: str, 
    db: AsyncSession = Depends(get_db)
):
    """获取指定邮箱用户的详细信息"""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {username} not found"
        )
    
    # 获取用户的研究领域ID (与 /me 和 /all 接口保持一致的返回结构)
    research_domain_ids = []
    # if user.research_domains:
    #     for domain in user.research_domains:
    #         research_domain_ids.append(domain.id)
            
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "interests_description": user.interests_description or [],
        "research_domain_ids": research_domain_ids
    } 