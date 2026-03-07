#!/usr/bin/env python3
"""
修复paper_recommendations表中空的URL字段
将空的URL字段更新为对应的arXiv链接
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.db_utils import get_db, load_config
from backend.app.models.users import UserPaperRecommendation
from sqlalchemy import select, update

async def fix_empty_urls():
    """修复空的URL字段"""
    print("🔧 开始修复空的URL字段...")
    
    # 加载配置
    config_path = project_root / "backend/configs/app_config.yaml"
    config = load_config(config_path)
    
    # 获取数据库连接
    async for db in get_db():
        try:
            # 查询所有记录（不管URL是否为空）
            result = await db.execute(
                select(UserPaperRecommendation)
            )
            all_records = result.scalars().all()
            
            print(f"📊 找到 {len(all_records)} 条记录需要检查")
            
            if not all_records:
                print("✅ 没有记录需要处理")
                return
            
            # 更新每条记录
            updated_count = 0
            for record in all_records:
                if record.paper_id:
                    # 生成arXiv链接
                    new_url = f"https://arxiv.org/abs/{record.paper_id}"
                    
                    # 更新记录
                    await db.execute(
                        update(UserPaperRecommendation)
                        .where(UserPaperRecommendation.id == record.id)
                        .values(url=new_url)
                    )
                    updated_count += 1
                    print(f"✅ 更新记录 {record.id}: {record.paper_id} -> {new_url}")
            
            # 提交更改
            await db.commit()
            print(f"🎉 成功更新 {updated_count} 条记录的URL字段")
            
        except Exception as e:
            print(f"❌ 修复过程中发生错误: {e}")
            await db.rollback()
            raise
        finally:
            await db.close()

async def main():
    """主函数"""
    try:
        await fix_empty_urls()
        print("✅ URL修复完成")
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
