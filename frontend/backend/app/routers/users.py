from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import or_

from ..db.database import get_db
from ..models.user import User, ResearchDomain, user_domain_association
from ..auth.schemas import UserOut, UserProfileUpdate
from ..auth.utils import get_current_user

# 请求模型
class UserInterestUpdate(BaseModel):
    research_domain_ids: List[int]
    interests_description: Optional[str] = None

# Response model for research domains (assuming a simple list of id and name)
class ResearchDomainOut(BaseModel):
    id: int
    name: str

router = APIRouter(prefix="/api/users", tags=["users"])

# 获取当前用户信息的依赖函数（简化版，实际应使用JWT验证）
async def get_current_user(username: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@router.get("/me", response_model=UserOut)
async def get_current_user_info(username: str, db: AsyncSession = Depends(get_db)):
    """获取当前用户信息（简化版，实际应使用JWT验证）"""
    user = await get_current_user(username, db)
    
    # 获取用户的研究领域ID
    research_domain_ids = []
    for domain in user.research_domains:
        research_domain_ids.append(domain.id)
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "interests_description": user.interests_description,
        "research_domain_ids": research_domain_ids
    }

@router.post("/interests", response_model=UserOut)
async def update_interests(
    interests: UserInterestUpdate, 
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """更新用户研究兴趣"""
    user = await get_current_user(username, db)
    
    # 更新文字描述
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
        "interests_description": user.interests_description,
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
        
        current_user.research_domains = research_domains

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return current_user 