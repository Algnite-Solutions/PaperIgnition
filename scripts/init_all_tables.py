#!/usr/bin/env python3
"""
PaperIgnition 数据库初始化脚本
创建所有业务数据库表结构

支持两套业务数据库：
1. 用户业务数据库 (USER_DB) - paperignition_user
2. 索引服务元数据数据库 (INDEX_SERVICE.metadata_db)
"""

import os
import sys
import asyncio
import yaml
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ProgrammingError, OperationalError

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from backend.app.db_utils import Base as UserBase, load_config as load_user_config
    from backend.app.models.users import (
        User, ResearchDomain, FavoritePaper, 
        UserPaperRecommendation, UserRetrieveResult, JobLog,
        user_domain_association
    )
except ImportError:
    # 如果直接导入失败，尝试添加路径
    import sys
    sys.path.insert(0, str(project_root))
    from backend.app.db_utils import Base as UserBase, load_config as load_user_config
    from backend.app.models.users import (
        User, ResearchDomain, FavoritePaper, 
        UserPaperRecommendation, UserRetrieveResult, JobLog,
        user_domain_association
    )

try:
    from AIgnite.db.metadata_db import Base as MetadataBase, TableSchema, TextChunkRecord
except ImportError:
    # AIgnite 可能不在当前路径，尝试从系统路径导入
    import sys
    ai_path = project_root.parent / "AIgnite" / "src"
    if ai_path.exists():
        sys.path.insert(0, str(ai_path))
    from AIgnite.db.metadata_db import Base as MetadataBase, TableSchema, TextChunkRecord


# AI领域初始数据
AI_DOMAINS = [
    {"name": "自然语言处理", "code": "NLP", "description": "自然语言处理技术，包括文本分析、生成、翻译等"},
    {"name": "计算机视觉", "code": "CV", "description": "计算机视觉技术，包括图像识别、目标检测等"},
    {"name": "大型语言模型", "code": "LLM", "description": "大型语言模型和相关研究"},
    {"name": "机器学习", "code": "ML", "description": "通用机器学习方法和技术"},
    {"name": "深度学习", "code": "DL", "description": "深度神经网络和相关技术"},
    {"name": "强化学习", "code": "RL", "description": "强化学习算法和应用"},
    {"name": "生成式AI", "code": "GAI", "description": "生成式AI技术，如GAN、扩散模型等"},
    {"name": "多模态学习", "code": "MM", "description": "多模态学习，结合不同类型的数据"},
    {"name": "语音识别", "code": "ASR", "description": "语音识别和语音处理技术"},
    {"name": "推荐系统", "code": "REC", "description": "推荐系统和个性化技术"},
    {"name": "图神经网络", "code": "GNN", "description": "图神经网络和图数据分析"},
    {"name": "联邦学习", "code": "FL", "description": "联邦学习和分布式AI技术"},
    {"name": "知识图谱", "code": "KG", "description": "知识图谱和知识表示学习"}
]


def ensure_database_exists(database_url: str, default_database: str = "postgres"):
    """Ensure target database exists, create it if missing."""
    url = make_url(database_url)
    target_database = url.database


    print(f"url: {url}")
    if not target_database:
        raise ValueError(f"Invalid database URL, missing database name: {database_url}")

    admin_url = url.set(database=default_database)
    # Use AUTOCOMMIT to allow CREATE DATABASE
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    try:
        with admin_engine.connect() as connection:
            try:
                connection.execute(text(f'CREATE DATABASE "{target_database}"'))
                print(f"✅ 数据库不存在，已创建: {target_database}")
            except ProgrammingError as exc:
                # PostgreSQL error code 42P04 indicates database already exists
                if getattr(exc.orig, "pgcode", None) == "42P04" or "already exists" in str(exc).lower():
                    print(f"ℹ️  数据库已存在: {target_database}")
                else:
                    raise
    except OperationalError as exc:
        print(f"❌ 创建数据库失败（可能权限不足或无法连接）: {target_database}")
        raise
    finally:
        admin_engine.dispose()


def create_fts_function(engine):
    """创建全文搜索排名函数"""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION fts_rank(
                    title text,
                    abstract text,
                    q tsquery,
                    title_weight float DEFAULT 0.7,
                    abstract_weight float DEFAULT 0.3
                ) RETURNS float AS $$
                BEGIN
                    RETURN (
                        title_weight * ts_rank_cd(
                            setweight(to_tsvector('english', coalesce(title, '')), 'A'),
                            q
                        ) +
                        abstract_weight * ts_rank_cd(
                            setweight(to_tsvector('english', coalesce(abstract, '')), 'B'),
                            q
                        )
                    );
                END;
                $$ LANGUAGE plpgsql;
            """))
            conn.commit()
            print("✅ 已创建全文搜索排名函数 fts_rank")
        except Exception as e:
            print(f"⚠️  创建全文搜索函数时出现警告: {str(e)}")


def init_user_database(config_path: str = None, drop_existing: bool = False):
    """
    初始化用户业务数据库
    
    Args:
        config_path: 配置文件路径
        drop_existing: 是否删除已存在的表
    """
    print("\n" + "="*80)
    print("📊 初始化用户业务数据库 (USER_DB)")
    print("="*80)
    
    # 加载配置
    config = load_user_config(config_path)
    db_config = config.get("USER_DB", {})
    
    # 构建数据库URL
    print(f"db_config: {db_config}")
    db_user = db_config.get("db_user", "postgres")
    db_password = db_config.get("db_password", "11111")
    db_host = db_config.get("db_host", "localhost")
    db_port = db_config.get("db_port", "5432")
    db_name = db_config.get("db_name", "paperignition_user")
    
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    print(f"🔗 连接数据库: {database_url}")

    # 确保数据库存在
    user_db_url = make_url(database_url).set(drivername="postgresql+psycopg2")

    user_db_url=user_db_url.render_as_string(hide_password=False)
    ensure_database_exists(str(user_db_url))
    
    # 创建同步引擎（用于表创建）
    engine = create_engine(user_db_url)
    
    try:
        # 检查表是否存在
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if drop_existing and existing_tables:
            print(f"🗑️  删除已存在的表: {', '.join(existing_tables)}")
            UserBase.metadata.drop_all(engine)
        
        # 创建所有表
        print("📝 创建用户业务数据库表...")
        UserBase.metadata.create_all(engine)
        
        # 检查创建的表
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()
        print(f"✅ 已创建以下表: {', '.join(created_tables)}")
        
        # 创建索引（如果通过SQLAlchemy没有自动创建）
        with engine.connect() as conn:
            # user_retrieve_results 表的复合索引
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_username_date 
                    ON user_retrieve_results(username, recommendation_date)
                """))
                print("✅ 已创建 user_retrieve_results 复合索引")
            except Exception as e:
                print(f"⚠️  创建索引时出现警告: {str(e)}")
        
        # 插入初始数据
        print("\n📦 插入初始数据...")
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # 检查是否已存在研究领域数据
            existing_domains = session.query(ResearchDomain).count()
            
            if existing_domains == 0:
                print("  添加研究领域数据...")
                for domain_data in AI_DOMAINS:
                    domain = ResearchDomain(**domain_data)
                    session.add(domain)
                session.commit()
                print(f"  ✅ 已添加 {len(AI_DOMAINS)} 个研究领域")
            else:
                print(f"  ℹ️  研究领域数据已存在 ({existing_domains} 条)")
            
        except Exception as e:
            session.rollback()
            print(f"  ❌ 插入初始数据失败: {str(e)}")
        finally:
            session.close()
        
        print("✅ 用户业务数据库初始化完成")
        
    except Exception as e:
        print(f"❌ 初始化用户业务数据库失败: {str(e)}")
        raise
    finally:
        engine.dispose()


def init_metadata_database(config_path: str = None, drop_existing: bool = False):
    """
    初始化索引服务元数据数据库
    
    Args:
        config_path: 配置文件路径
        drop_existing: 是否删除已存在的表
    """
    print("\n" + "="*80)
    print("📊 初始化索引服务元数据数据库 (INDEX_SERVICE.metadata_db)")
    print("="*80)
    
    # 加载配置
    try:
        from backend.index_service.db_utils import load_config
    except ImportError:
        # 如果导入失败，尝试添加路径
        import sys
        sys.path.insert(0, str(project_root))
        from backend.index_service.db_utils import load_config
    config = load_config(config_path)
    
    db_url = config['metadata_db']['db_url']
    print(f"🔗 连接数据库: {db_url}")

    metadata_url = make_url(db_url)
    if not metadata_url.drivername.startswith("postgresql"):
        raise ValueError(f"Unsupported driver for metadata database: {metadata_url.drivername}")
    metadata_db_url = metadata_url
    if "+" not in metadata_url.drivername:
        metadata_db_url = metadata_url.set(drivername="postgresql+psycopg2")

    metadata_db_url=metadata_db_url.render_as_string(hide_password=False)
    ensure_database_exists(str(metadata_db_url))
    
    # 创建引擎
    engine = create_engine(metadata_db_url)
    
    try:
        # 检查表是否存在
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if drop_existing and existing_tables:
            print(f"🗑️  删除已存在的表: {', '.join(existing_tables)}")
            MetadataBase.metadata.drop_all(engine)
        
        # 创建所有表
        print("📝 创建索引服务元数据数据库表...")
        MetadataBase.metadata.create_all(engine)
        
        # 检查创建的表
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()
        print(f"✅ 已创建以下表: {', '.join(created_tables)}")
        
        # 创建全文搜索函数
        print("\n🔍 创建全文搜索函数...")
        create_fts_function(engine)
        
        print("✅ 索引服务元数据数据库初始化完成")
        
    except Exception as e:
        print(f"❌ 初始化索引服务元数据数据库失败: {str(e)}")
        raise
    finally:
        engine.dispose()


def print_database_schema():
    """打印数据库架构信息"""
    print("\n" + "="*80)
    print("📋 PaperIgnition 数据库架构总览")
    print("="*80)
    
    print("\n【用户业务数据库】paperignition_user")
    print("-" * 80)
    print("1. users - 用户主表")
    print("   字段: id, username, email, hashed_password, wx_openid, wx_nickname,")
    print("         wx_avatar_url, wx_phone, push_frequency, is_active, is_verified,")
    print("         interests_description (ARRAY), research_interests_text, rewrite_interest,")
    print("         created_at, updated_at")
    print("   索引: username (unique), email (unique), wx_openid (unique)")
    
    print("\n2. research_domains - 研究领域字典表")
    print("   字段: id, name, code, description")
    print("   索引: name (unique), code (unique)")
    
    print("\n3. user_domain_association - 用户-研究领域多对多关联表")
    print("   字段: user_id (FK -> users.id), domain_id (FK -> research_domains.id)")
    print("   主键: (user_id, domain_id)")
    
    print("\n4. favorite_papers - 用户收藏论文表")
    print("   字段: id, user_id (FK -> users.id), paper_id, title, authors,")
    print("         abstract, url, created_at")
    print("   索引: paper_id")
    
    print("\n5. paper_recommendations - 用户论文推荐关系表")
    print("   字段: id, username (FK -> users.username), paper_id, title, authors,")
    print("         abstract, url, blog, blog_title, blog_abs, recommendation_date,")
    print("         viewed, relevance_score, recommendation_reason, submitted, comment,")
    print("         blog_liked, blog_feedback_date")
    print("   索引: username, paper_id")
    
    print("\n6. user_retrieve_results - 用户检索结果记录表")
    print("   字段: id, username (FK -> users.username), query, search_strategy,")
    print("         recommendation_date, retrieve_ids (JSON), top_k_ids (JSON)")
    print("   索引: username, (username, recommendation_date)")
    
    print("\n7. job_logs - 作业执行日志表")
    print("   字段: id, job_type, job_id, status, username, start_time, end_time,")
    print("         duration_seconds, error_message, details, created_at, updated_at")
    print("   索引: job_type, job_id, status, username")
    
    print("\n【索引服务元数据数据库】paperignition")
    print("-" * 80)
    print("1. papers - 论文主表")
    print("   字段: id, doc_id (unique), title, abstract, authors (JSON),")
    print("         categories (JSON), published_date, pdf_data (BYTEA),")
    print("         chunk_ids (JSON), figure_ids (JSON), image_storage (JSON),")
    print("         table_ids (JSON), extra_metadata (JSON), pdf_path, HTML_path,")
    print("         blog, comments")
    print("   索引: doc_id (unique), GIN全文索引 (title + abstract)")
    
    print("\n2. text_chunks - 文本分块表")
    print("   字段: id (PK: doc_id_chunkId), doc_id, chunk_id, text_content,")
    print("         chunk_order, created_at")
    print("   索引: doc_id, (doc_id, chunk_order), GIN全文索引 (text_content),")
    print("         (doc_id, chunk_id) unique")
    
    print("\n3. 数据库函数")
    print("   fts_rank() - 全文搜索排名函数")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PaperIgnition 数据库初始化脚本")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="配置文件路径 (默认: backend/configs/app_config.yaml)"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="删除已存在的表后重新创建"
    )
    parser.add_argument(
        "--user-db-only",
        action="store_true",
        help="仅初始化用户业务数据库"
    )
    parser.add_argument(
        "--metadata-db-only",
        action="store_true",
        help="仅初始化索引服务元数据数据库"
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="仅打印数据库架构信息，不执行初始化"
    )
    
    args = parser.parse_args()
    
    # 如果只是打印架构信息
    if args.schema_only:
        print_database_schema()
        return
    
    # 确定配置文件路径
    if args.config is None:
        local_mode = os.getenv("PAPERIGNITION_LOCAL_MODE", "false").lower() == "true"
        config_file = "test_config.yaml" if local_mode else "app_config.yaml"
        config_path = project_root / "backend" / "configs" / config_file
    else:
        config_path = args.config
    
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        sys.exit(1)
    
    print(f"📄 使用配置文件: {config_path}")
    
    try:
        # 初始化用户业务数据库
        if not args.metadata_db_only:
            init_user_database(config_path, drop_existing=args.drop)
        
        # 初始化索引服务元数据数据库
        if not args.user_db_only:
            init_metadata_database(config_path, drop_existing=args.drop)
        
        print("\n" + "="*80)
        print("✅ 所有数据库初始化完成！")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

