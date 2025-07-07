from typing import List
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.users import User, UserPaperRecommendation
from ..models.papers import PaperBase, PaperRecommendation, MOCK_PAPERS
from ..db_utils import get_db


router = APIRouter(prefix="/papers", tags=["papers"])

@router.get("/recommendations/{username}", response_model=List[PaperBase])
async def get_recommended_papers_info(username: str, db: AsyncSession = Depends(get_db)):
    """根据username查询UserPaperRecommendation表中对应的paper基础信息列表"""
    result = await db.execute(select(UserPaperRecommendation.paper_id).where(UserPaperRecommendation.username == username))
    paper_ids = [row[0] for row in result.all()]
    papers=get_papers_by_ids(paper_ids)
    print("========================")
    print(papers)
    print("========================")
    return papers

# TODO(@Fang Guo): 输入为paper_id列表，返回为以下json格式的内容,实际上我觉得可以在其他地方实现，import进来就行
"""
    {
        "id": "2023.24680",
        "title": "多模态大语言模型研究进展",
        "authors": "孙八, 周九, 吴十",
        "abstract": "多模态大语言模型将文本、图像等多种模态信息融合处理...",
        "url": "https://example.com/papers/2023.24680"
    }
"""
def get_papers_by_ids(paper_ids: List[str]):
    """根据paper_id列表返回论文详情（mock数据）"""
    # 用mock数据模拟数据库查询
    papers = []
    for pid in paper_ids:
        paper = next((p for p in MOCK_PAPERS if p["id"] == pid), None)
        if paper:
            papers.append(PaperBase(**paper))
    return papers

@router.get("/paper_content/{paper_id}")
async def get_paper_markdown_content(paper_id: str):
    """根据paper_id返回论文的markdown内容（mock数据）"""
    paper = get_content_by_ids(paper_id)
    print("========================")
    print(paper)
    print("========================")
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper content not found")
    return paper

# TODO(@Fang Guo): 输入为paper_id，返回为str格式的markdown内容,暂时不考虑图片
def get_content_by_ids(paper_id: str):
    """根据paper_id返回论文详情（mock数据）"""
    content = next((p["content"] for p in MOCK_PAPERS if p["id"] == paper_id), None)
    return content

# 这个接口应该为后端使用，插入对任意用户的推荐，应当受到保护
# 接口为{backend_url}/api/papers/recommend
# TODO(@Hui Chen): 需要添加安全验证
@router.post("/recommend", status_code=status.HTTP_201_CREATED)
async def add_paper_recommendation(username:str, rec: PaperRecommendation, db: AsyncSession = Depends(get_db)):
    """根据username和paper_id插入推荐记录"""
    try:
        # 验证用户是否存在
        user_result = await db.execute(
            select(User).where(User.username == username)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {username} 不存在")

        # 验证论文是否存在（这里假设论文ID是有效的）
        # TODO: 添加实际的论文验证逻辑
        # paper_result = await db.execute(
        #     select(Paper).where(Paper.id == rec.paper_id)
        # )
        # paper = paper_result.scalar_one_or_none()
        # if not paper:
        #     raise HTTPException(status_code=404, detail=f"论文 {rec.paper_id} 不存在")

        # 创建推荐记录
        new_rec = UserPaperRecommendation(
            username=username,
            paper_id=rec.paper_id,
            recommendation_reason=rec.recommendation_reason,
            relevance_score=rec.relevance_score
        )
        
        # 添加到数据库
        db.add(new_rec)
        await db.commit()
        await db.refresh(new_rec)
        
        return {"message": "推荐记录添加成功", "id": new_rec.id}
        
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="该推荐记录已存在或数据不合法")
    except Exception as e:
        await db.rollback()
        print(f"添加推荐记录时发生错误: {str(e)}")  # 添加日志
        raise HTTPException(status_code=500, detail="添加推荐记录失败")