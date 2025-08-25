#!/usr/bin/env python3
"""
测试推荐逻辑的脚本
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.app.db_utils import AsyncSessionLocal
from backend.app.models.users import User, UserPaperRecommendation
from sqlalchemy.future import select
from sqlalchemy import and_

async def test_recommendation_logic():
    """测试推荐逻辑"""
    async with AsyncSessionLocal() as db:
        # 1. 检查BlogBot用户是否存在
        blogbot_user = await db.execute(
            select(User).where(User.username == "BlogBot@gmail.com")
        )
        blogbot_user = blogbot_user.scalar_one_or_none()
        
        if not blogbot_user:
            print("❌ BlogBot@gmail.com 用户不存在")
            return
        
        print(f"✅ 找到BlogBot用户: {blogbot_user.username}")
        
        # 2. 检查BlogBot用户的推荐论文
        blogbot_recommendations = await db.execute(
            select(UserPaperRecommendation).where(
                UserPaperRecommendation.username == "BlogBot@gmail.com"
            )
        )
        blogbot_recommendations = blogbot_recommendations.scalars().all()
        
        print(f"📊 BlogBot用户推荐论文数量: {len(blogbot_recommendations)}")
        
        if blogbot_recommendations:
            print("📝 BlogBot推荐论文列表:")
            for i, rec in enumerate(blogbot_recommendations[:5]):  # 只显示前5个
                print(f"  {i+1}. Paper ID: {rec.paper_id}")
                print(f"     Title: {rec.title}")
                print(f"     Blog长度: {len(rec.blog) if rec.blog else 0} 字符")
                print(f"     Recommendation Reason: {rec.recommendation_reason}")
                print()
        
        # 3. 检查其他用户的推荐论文
        other_users = await db.execute(
            select(User).where(User.username != "BlogBot@gmail.com")
        )
        other_users = other_users.scalars().all()
        
        print(f"👥 其他用户数量: {len(other_users)}")
        
        for user in other_users[:3]:  # 只检查前3个用户
            user_recommendations = await db.execute(
                select(UserPaperRecommendation).where(
                    UserPaperRecommendation.username == user.username
                )
            )
            user_recommendations = user_recommendations.scalars().all()
            print(f"  {user.username}: {len(user_recommendations)} 篇推荐论文")

if __name__ == "__main__":
    print("🧪 开始测试推荐逻辑...")
    asyncio.run(test_recommendation_logic())
    print("✅ 测试完成")



