from typing import List
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..models.users import User, FavoritePaper
from ..models.papers import PaperBase
from ..db_utils import get_db
from ..auth.utils import get_current_user

router = APIRouter(prefix="/favorites", tags=["favorites"])

# Pydantic 模型
class FavoriteRequest(BaseModel):
    paper_id: str
    title: str
    authors: str
    abstract: str
    url: str = None

class FavoriteResponse(BaseModel):
    id: int
    paper_id: str
    title: str
    authors: str
    abstract: str
    url: str = None

@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_to_favorites(
    favorite_data: FavoriteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """添加论文到收藏"""
    try:
        # 检查是否已经收藏
        result = await db.execute(
            select(FavoritePaper).where(
                FavoritePaper.user_id == current_user.id,
                FavoritePaper.paper_id == favorite_data.paper_id
            )
        )
        existing_favorite = result.scalar_one_or_none()
        
        if existing_favorite:
            raise HTTPException(
                status_code=400, 
                detail="论文已在收藏列表中"
            )
        
        # 创建收藏记录
        new_favorite = FavoritePaper(
            user_id=current_user.id,
            paper_id=favorite_data.paper_id,
            title=favorite_data.title,
            authors=favorite_data.authors,
            abstract=favorite_data.abstract,
            url=favorite_data.url
        )
        
        db.add(new_favorite)
        await db.commit()
        await db.refresh(new_favorite)
        
        return {
            "message": "论文已添加到收藏",
            "favorite_id": new_favorite.id
        }
        
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="论文已在收藏列表中"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="添加收藏失败"
        )

@router.delete("/remove/{paper_id}")
async def remove_from_favorites(
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """从收藏中移除论文"""
    try:
        # 查找收藏记录
        result = await db.execute(
            select(FavoritePaper).where(
                FavoritePaper.user_id == current_user.id,
                FavoritePaper.paper_id == paper_id
            )
        )
        favorite = result.scalar_one_or_none()
        
        if not favorite:
            raise HTTPException(
                status_code=404,
                detail="收藏记录不存在"
            )
        
        # 删除收藏记录
        await db.delete(favorite)
        await db.commit()
        
        return {"message": "论文已从收藏中移除"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="移除收藏失败"
        )

@router.get("/list", response_model=List[FavoriteResponse])
async def get_user_favorites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户的收藏列表"""
    try:
        result = await db.execute(
            select(FavoritePaper).where(
                FavoritePaper.user_id == current_user.id
            ).order_by(FavoritePaper.id.desc())  # 按收藏时间倒序
        )
        favorites = result.scalars().all()
        
        return [
            FavoriteResponse(
                id=fav.id,
                paper_id=fav.paper_id,
                title=fav.title,
                authors=fav.authors,
                abstract=fav.abstract,
                url=fav.url
            )
            for fav in favorites
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="获取收藏列表失败"
        )

@router.get("/check/{paper_id}")
async def check_if_favorited(
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """检查论文是否已收藏"""
    try:
        result = await db.execute(
            select(FavoritePaper).where(
                FavoritePaper.user_id == current_user.id,
                FavoritePaper.paper_id == paper_id
            )
        )
        favorite = result.scalar_one_or_none()
        
        return {"is_favorited": favorite is not None}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="检查收藏状态失败"
        ) 