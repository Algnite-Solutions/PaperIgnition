"""
将 Paper Abstract 和 User Interest 的 Embedding 迁移到 pgvector

功能:
1. 从 paperignition 数据库读取论文 Abstract
2. 从 paperignition_user 数据库读取用户 Interest
3. 使用阿里云百炼 Embedding API 生成向量
4. 存储到阿里云 RDS PostgreSQL 的 pgvector 表

运行方式:
    python scripts/migrate_embeddings_to_pgvector.py
    python scripts/migrate_embeddings_to_pgvector.py --config scripts/migration_config.yaml

环境变量:
    DASHSCOPE_API_KEY: 阿里云百炼 API Key (可选，优先使用配置文件)
"""

import os
import sys
import json
import time
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================
# 配置加载
# ============================================

def expand_env_vars(value):
    """展开配置值中的环境变量

    支持格式: ${ENV_VAR} 或 ${ENV_VAR:default_value}
    """
    if not isinstance(value, str):
        return value

    pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

    def replace(match):
        env_var = match.group(1)
        default = match.group(2) if match.group(2) is not None else ""
        return os.getenv(env_var, default)

    return re.sub(pattern, replace, value)


def load_config(config_path: str = None) -> Dict[str, Any]:
    """加载配置文件"""
    if config_path is None:
        # 默认配置文件路径
        config_path = Path(__file__).parent / "migration_config.yaml"

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 递归展开环境变量
    def expand_config(obj):
        if isinstance(obj, dict):
            return {k: expand_config(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [expand_config(item) for item in obj]
        else:
            return expand_env_vars(obj)

    return expand_config(config)


# 全局配置变量（将在 load_all_config() 中初始化）
DASHSCOPE_API_KEY = None
DASHSCOPE_BASE_URL = None
EMBEDDING_MODEL = None
EMBEDDING_DIMENSION = None
BATCH_SIZE = None
PAPER_DB_CONFIG = None
USER_DB_CONFIG = None
PAPER_EMBEDDING_TABLE = None
USER_EMBEDDING_TABLE = None
MAX_PAPERS = None
MAX_USERS = None
DELAY_BETWEEN_BATCHES = None
SKIP_EXISTING = None


def load_all_config(config_path: str = None):
    """加载所有配置到全局变量"""
    global DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, EMBEDDING_MODEL, EMBEDDING_DIMENSION, BATCH_SIZE
    global PAPER_DB_CONFIG, USER_DB_CONFIG
    global PAPER_EMBEDDING_TABLE, USER_EMBEDDING_TABLE
    global MAX_PAPERS, MAX_USERS, DELAY_BETWEEN_BATCHES, SKIP_EXISTING

    config = load_config(config_path)

    # 阿里云百炼 Embedding 配置
    dashscope_cfg = config.get("dashscope", {})
    DASHSCOPE_API_KEY = dashscope_cfg.get("api_key", os.getenv("DASHSCOPE_API_KEY", ""))
    DASHSCOPE_BASE_URL = dashscope_cfg.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    EMBEDDING_MODEL = dashscope_cfg.get("embedding_model", "text-embedding-v4")
    EMBEDDING_DIMENSION = dashscope_cfg.get("embedding_dimension", 2048)
    BATCH_SIZE = dashscope_cfg.get("batch_size", 10)

    # 阿里云 RDS 数据库配置
    aliyun_rds = config.get("aliyun_rds", {})
    db_host = aliyun_rds.get("db_host", "localhost")
    db_port = int(aliyun_rds.get("db_port", 5432))
    db_user = aliyun_rds.get("db_user", "postgres")
    db_password = aliyun_rds.get("db_password", "")

    PAPER_DB_CONFIG = {
        "host": db_host,
        "port": db_port,
        "database": aliyun_rds.get("db_name_paper", "paperignition"),
        "user": db_user,
        "password": db_password
    }

    USER_DB_CONFIG = {
        "host": db_host,
        "port": db_port,
        "database": aliyun_rds.get("db_name_user", "paperignition_user"),
        "user": db_user,
        "password": db_password
    }

    # pgvector 迁移配置
    pgvector_cfg = config.get("pgvector_migration", {})
    PAPER_EMBEDDING_TABLE = pgvector_cfg.get("paper_embedding_table", "paper_embeddings")
    USER_EMBEDDING_TABLE = pgvector_cfg.get("user_embedding_table", "user_interest_embeddings")
    MAX_PAPERS = pgvector_cfg.get("max_papers")
    MAX_USERS = pgvector_cfg.get("max_users")
    DELAY_BETWEEN_BATCHES = pgvector_cfg.get("delay_between_batches", 0.5)
    SKIP_EXISTING = pgvector_cfg.get("skip_existing", True)

    logger.info(f"✅ 配置加载完成:")
    logger.info(f"   Embedding 模型: {EMBEDDING_MODEL} (维度: {EMBEDDING_DIMENSION})")
    logger.info(f"   Paper DB: {PAPER_DB_CONFIG['host']}/{PAPER_DB_CONFIG['database']}")
    logger.info(f"   User DB: {USER_DB_CONFIG['host']}/{USER_DB_CONFIG['database']}")


# ============================================
# 数据库连接
# ============================================

def get_db_connection(config: Dict[str, Any]):
    """创建数据库连接"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            dbname=config["database"],
            user=config["user"],
            password=config["password"]
        )
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        raise


def ensure_pgvector_extension(conn):
    """确保 pgvector 扩展已安装"""
    cur = conn.cursor()
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        logger.info("✅ pgvector 扩展已就绪")
    except Exception as e:
        logger.error(f"安装 pgvector 扩展失败: {e}")
        raise
    finally:
        cur.close()


def create_paper_embedding_table(conn):
    """在 paperignition 数据库创建论文向量表"""
    cur = conn.cursor()
    try:
        # 创建论文 Abstract 向量表
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {PAPER_EMBEDDING_TABLE} (
                id SERIAL PRIMARY KEY,
                doc_id VARCHAR(255) UNIQUE NOT NULL,
                title TEXT,
                abstract TEXT,
                embedding vector({EMBEDDING_DIMENSION}),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        logger.info(f"✅ 创建/确认表: {PAPER_EMBEDDING_TABLE}")

        # 创建向量索引 (HNSW)
        try:
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{PAPER_EMBEDDING_TABLE}_embedding
                ON {PAPER_EMBEDDING_TABLE}
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """)
            logger.info(f"✅ 创建索引: idx_{PAPER_EMBEDDING_TABLE}_embedding")
        except Exception as e:
            logger.warning(f"创建论文向量索引失败 (可能数据量不足): {e}")

    except Exception as e:
        logger.error(f"创建论文向量表失败: {e}")
        raise
    finally:
        cur.close()


def create_user_embedding_table(conn):
    """在 paperignition_user 数据库创建用户向量表"""
    cur = conn.cursor()
    try:
        # 创建用户 Interest 向量表
        # user_id 作为外键关联到同数据库的 users 表
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {USER_EMBEDDING_TABLE} (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                username VARCHAR(255) UNIQUE NOT NULL,
                interest_text TEXT,
                embedding vector({EMBEDDING_DIMENSION}),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        logger.info(f"✅ 创建/确认表: {USER_EMBEDDING_TABLE}")

        # 创建向量索引 (HNSW)
        try:
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{USER_EMBEDDING_TABLE}_embedding
                ON {USER_EMBEDDING_TABLE}
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """)
            logger.info(f"✅ 创建索引: idx_{USER_EMBEDDING_TABLE}_embedding")
        except Exception as e:
            logger.warning(f"创建用户向量索引失败 (可能数据量不足): {e}")

    except Exception as e:
        logger.error(f"创建用户向量表失败: {e}")
        raise
    finally:
        cur.close()


# ============================================
# Embedding API 调用
# ============================================

class EmbeddingClient:
    """阿里云百炼 Embedding 客户端"""

    def __init__(self, api_key: str, base_url: str, model: str, dimension: int):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.dimension = dimension

        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"✅ OpenAI 客户端初始化成功 (base_url: {base_url})")
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")

    def get_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """批量获取文本的 embedding"""
        if not texts:
            return None

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.dimension
            )
            embeddings = [item.embedding for item in response.data]
            return embeddings
        except Exception as e:
            logger.error(f"Embedding API 调用失败: {e}")
            return None

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取单个文本的 embedding"""
        embeddings = self.get_embeddings([text])
        return embeddings[0] if embeddings else None


def batch_process_embeddings(
    embedding_client: EmbeddingClient,
    texts: List[str],
    batch_size: int = BATCH_SIZE,
    delay: float = DELAY_BETWEEN_BATCHES
) -> List[Optional[List[float]]]:
    """批量处理文本的 embedding，处理 API 限制"""
    all_embeddings = []

    total_batches = (len(texts) + batch_size - 1) // batch_size
    logger.info(f"开始处理 {len(texts)} 条文本，共 {total_batches} 批次")

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_num = i // batch_size + 1

        logger.info(f"处理批次 {batch_num}/{total_batches} ({len(batch)} 条文本)")

        embeddings = embedding_client.get_embeddings(batch)

        if embeddings:
            all_embeddings.extend(embeddings)
        else:
            # 如果失败，填充 None
            all_embeddings.extend([None] * len(batch))
            logger.warning(f"批次 {batch_num} 处理失败")

        # 批次间延迟，避免 API 限流
        if i + batch_size < len(texts):
            time.sleep(delay)

    return all_embeddings


# ============================================
# 数据读取
# ============================================

def fetch_paper_abstracts(conn, target_conn=None, limit: Optional[int] = None, skip_existing: bool = True) -> List[Dict[str, Any]]:
    """从数据库读取论文 Abstract

    Args:
        conn: 源数据库连接 (paperignition)
        target_conn: 目标数据库连接 (用于检查已存在的记录)
        limit: 限制读取数量
        skip_existing: 是否跳过已存在的记录
    """
    cur = conn.cursor()
    try:
        # 获取已存在的 doc_id 列表（去重）
        existing_doc_ids = set()
        if skip_existing and target_conn:
            target_cur = target_conn.cursor()
            target_cur.execute(f"SELECT doc_id FROM {PAPER_EMBEDDING_TABLE}")
            existing_doc_ids = {row[0] for row in target_cur.fetchall()}
            target_cur.close()
            logger.info(f"📋 已存在 {len(existing_doc_ids)} 条论文 embedding 记录")

        limit_clause = f"LIMIT {limit * 3 if limit else ''}" if limit else ""  # 多取一些，因为会过滤掉已存在的

        # 查询 papers 表
        cur.execute(f"""
            SELECT doc_id, title, abstract
            FROM papers
            WHERE abstract IS NOT NULL AND abstract != ''
            {limit_clause}
        """)

        papers = []
        for row in cur.fetchall():
            doc_id, title, abstract = row

            # 去重：跳过已存在的
            if skip_existing and doc_id in existing_doc_ids:
                continue

            if abstract and abstract.strip():
                papers.append({
                    "doc_id": doc_id,
                    "title": title or "",
                    "abstract": abstract.strip()
                })

            # 达到限制数量就停止
            if limit and len(papers) >= limit:
                break

        logger.info(f"📚 读取到 {len(papers)} 篇新论文 (待处理)")
        return papers

    except Exception as e:
        logger.error(f"读取论文数据失败: {e}")
        return []
    finally:
        cur.close()


def fetch_user_interests(conn, skip_existing: bool = True) -> List[Dict[str, Any]]:
    """从数据库读取用户 Interest

    Args:
        conn: 数据库连接 (paperignition_user，同时用于读取和去重检查)
        skip_existing: 是否跳过已存在的记录
    """
    cur = conn.cursor()
    try:
        # 获取已存在的 username 列表（去重）- 现在在同一个数据库
        existing_usernames = set()
        if skip_existing:
            cur.execute(f"SELECT username FROM {USER_EMBEDDING_TABLE}")
            existing_usernames = {row[0] for row in cur.fetchall()}
            logger.info(f"📋 已存在 {len(existing_usernames)} 条用户 embedding 记录")

        # 查询 users 表的 interests_description
        # interests_description 是一个数组，需要展开处理
        cur.execute(f"""
            SELECT id, username, interests_description, rewrite_interest
            FROM users
            WHERE interests_description IS NOT NULL
            AND array_length(interests_description, 1) > 0
        """)

        users = []
        for row in cur.fetchall():
            user_id, username, interests_description, rewrite_interest = row

            # 去重：跳过已存在的
            if skip_existing and username in existing_usernames:
                continue

            # 优先使用 rewrite_interest (翻译后的英文版本)
            if rewrite_interest and rewrite_interest.strip():
                interest_text = rewrite_interest.strip()
            elif interests_description:
                # interests_description 是数组，合并为字符串
                interest_text = " ".join([i for i in interests_description if i])
            else:
                continue

            if interest_text.strip():
                users.append({
                    "user_id": user_id,
                    "username": username,
                    "interest_text": interest_text.strip()
                })

        logger.info(f"👥 读取到 {len(users)} 个新用户 (待处理)")
        return users

    except Exception as e:
        logger.error(f"读取用户数据失败: {e}")
        return []
    finally:
        cur.close()


# ============================================
# 数据存储
# ============================================

def insert_paper_embeddings(conn, papers: List[Dict[str, Any]], embeddings: List[Optional[List[float]]]):
    """将论文 embedding 插入数据库"""
    cur = conn.cursor()
    success_count = 0
    error_count = 0

    try:
        for paper, embedding in zip(papers, embeddings):
            if embedding is None:
                logger.warning(f"跳过论文 {paper['doc_id']} (embedding 为空)")
                error_count += 1
                continue

            try:
                # 转换为 JSON 字符串
                emb_str = json.dumps(embedding)

                # 使用 UPSERT (INSERT ... ON CONFLICT)
                cur.execute(f"""
                    INSERT INTO {PAPER_EMBEDDING_TABLE} (doc_id, title, abstract, embedding, updated_at)
                    VALUES (%s, %s, %s, %s::vector, CURRENT_TIMESTAMP)
                    ON CONFLICT (doc_id)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        abstract = EXCLUDED.abstract,
                        embedding = EXCLUDED.embedding,
                        updated_at = CURRENT_TIMESTAMP
                """, (paper["doc_id"], paper["title"], paper["abstract"], emb_str))

                success_count += 1

            except Exception as e:
                logger.error(f"插入论文 {paper['doc_id']} 失败: {e}")
                error_count += 1

        logger.info(f"📄 论文 embedding 插入完成: 成功 {success_count}, 失败 {error_count}")

    finally:
        cur.close()

    return success_count, error_count


def insert_user_embeddings(conn, users: List[Dict[str, Any]], embeddings: List[Optional[List[float]]]):
    """将用户 embedding 插入数据库"""
    cur = conn.cursor()
    success_count = 0
    error_count = 0

    try:
        for user, embedding in zip(users, embeddings):
            if embedding is None:
                logger.warning(f"跳过用户 {user['username']} (embedding 为空)")
                error_count += 1
                continue

            try:
                # 转换为 JSON 字符串
                emb_str = json.dumps(embedding)

                # 使用 UPSERT (INSERT ... ON CONFLICT)
                cur.execute(f"""
                    INSERT INTO {USER_EMBEDDING_TABLE} (user_id, username, interest_text, embedding, updated_at)
                    VALUES (%s, %s, %s, %s::vector, CURRENT_TIMESTAMP)
                    ON CONFLICT (username)
                    DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        interest_text = EXCLUDED.interest_text,
                        embedding = EXCLUDED.embedding,
                        updated_at = CURRENT_TIMESTAMP
                """, (user["user_id"], user["username"], user["interest_text"], emb_str))

                success_count += 1

            except Exception as e:
                logger.error(f"插入用户 {user['username']} 失败: {e}")
                error_count += 1

        logger.info(f"👥 用户 embedding 插入完成: 成功 {success_count}, 失败 {error_count}")

    finally:
        cur.close()

    return success_count, error_count


# ============================================
# 相似度检索函数
# ============================================

def search_similar_papers(conn, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """搜索相似的论文"""
    cur = conn.cursor()
    try:
        emb_str = json.dumps(query_embedding)

        cur.execute(f"""
            SELECT doc_id, title, abstract,
                   1 - (embedding <=> %s::vector) as similarity
            FROM {PAPER_EMBEDDING_TABLE}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (emb_str, emb_str, top_k))

        results = []
        for row in cur.fetchall():
            results.append({
                "doc_id": row[0],
                "title": row[1],
                "abstract": row[2],
                "similarity": float(row[3])
            })

        return results

    finally:
        cur.close()


def search_similar_users(conn, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """搜索兴趣相似的用户"""
    cur = conn.cursor()
    try:
        emb_str = json.dumps(query_embedding)

        cur.execute(f"""
            SELECT user_id, username, interest_text,
                   1 - (embedding <=> %s::vector) as similarity
            FROM {USER_EMBEDDING_TABLE}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (emb_str, emb_str, top_k))

        results = []
        for row in cur.fetchall():
            results.append({
                "user_id": row[0],
                "username": row[1],
                "interest_text": row[2],
                "similarity": float(row[3])
            })

        return results

    finally:
        cur.close()


# ============================================
# 主流程
# ============================================

def main(config_path: str = None):
    """主迁移流程"""
    # 加载配置
    load_all_config(config_path)

    logger.info("=" * 60)
    logger.info("开始 Embedding 迁移到 pgvector")
    logger.info("=" * 60)

    start_time = datetime.now()

    # 1. 初始化 Embedding 客户端
    logger.info("\n📌 步骤 1: 初始化 Embedding 客户端")
    embedding_client = EmbeddingClient(
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_BASE_URL,
        model=EMBEDDING_MODEL,
        dimension=EMBEDDING_DIMENSION
    )

    # 2. 连接数据库并创建表
    logger.info("\n📌 步骤 2: 连接数据库并创建表")

    # 连接到 Paper 数据库 (阿里云 RDS)
    paper_conn = get_db_connection(PAPER_DB_CONFIG)
    logger.info(f"✅ 连接到 Paper 数据库: {PAPER_DB_CONFIG['database']} ({PAPER_DB_CONFIG['host']})")
    ensure_pgvector_extension(paper_conn)
    create_paper_embedding_table(paper_conn)

    # 连接到 User 数据库 (本地)
    user_conn = get_db_connection(USER_DB_CONFIG)
    logger.info(f"✅ 连接到 User 数据库: {USER_DB_CONFIG['database']} ({USER_DB_CONFIG['host']})")
    ensure_pgvector_extension(user_conn)
    create_user_embedding_table(user_conn)

    # 3. 处理论文 Abstract
    logger.info("\n📌 步骤 3: 处理论文 Abstract Embedding")
    papers = fetch_paper_abstracts(
        paper_conn,
        target_conn=paper_conn,
        limit=MAX_PAPERS,
        skip_existing=SKIP_EXISTING
    )

    if papers:
        # 准备 embedding 文本 (title + abstract)
        paper_texts = []
        for paper in papers:
            # 组合 title 和 abstract 进行 embedding
            text = f"{paper['title']}. {paper['abstract']}" if paper['title'] else paper['abstract']
            paper_texts.append(text)

        # 批量获取 embedding
        paper_embeddings = batch_process_embeddings(embedding_client, paper_texts)

        # 插入到 Paper 数据库
        insert_paper_embeddings(paper_conn, papers, paper_embeddings)
    else:
        logger.warning("没有找到论文数据")

    # 4. 处理用户 Interest
    logger.info("\n📌 步骤 4: 处理用户 Interest Embedding")
    users = fetch_user_interests(user_conn, skip_existing=SKIP_EXISTING)

    if users:
        # 准备 embedding 文本
        user_texts = [user["interest_text"] for user in users]

        # 批量获取 embedding
        user_embeddings = batch_process_embeddings(embedding_client, user_texts)

        # 插入到 User 数据库 (paperignition_user)
        insert_user_embeddings(user_conn, users, user_embeddings)
    else:
        logger.warning("没有找到用户数据")

    # 5. 验证结果
    logger.info("\n📌 步骤 5: 验证迁移结果")

    # 检查论文 embedding 数量
    cur = paper_conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {PAPER_EMBEDDING_TABLE}")
    paper_count = cur.fetchone()[0]
    cur.close()
    logger.info(f"📊 Paper Embedding 记录数 (paperignition): {paper_count}")

    # 检查用户 embedding 数量
    cur = user_conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {USER_EMBEDDING_TABLE}")
    user_count = cur.fetchone()[0]
    cur.close()
    logger.info(f"📊 User Embedding 记录数 (paperignition_user): {user_count}")

    # 6. 测试相似度搜索
    logger.info("\n📌 步骤 6: 测试相似度搜索")

    # 测试搜索：用第一个用户的兴趣搜索相似论文
    if users and papers:
        test_user = users[0]
        logger.info(f"🔍 使用用户 '{test_user['username']}' 的兴趣测试搜索")

        # 获取该用户的 embedding (从 user_conn / paperignition_user 数据库)
        cur = user_conn.cursor()
        cur.execute(f"""
            SELECT embedding FROM {USER_EMBEDDING_TABLE}
            WHERE username = %s
        """, (test_user['username'],))
        result = cur.fetchone()
        cur.close()

        if result:
            user_emb = json.loads(result[0])
            # 搜索相似论文 (在 paper_conn / paperignition 数据库中)
            similar_papers = search_similar_papers(paper_conn, user_emb, top_k=3)

            logger.info(f"   用户兴趣: {test_user['interest_text'][:100]}...")
            logger.info("   相似论文:")
            for i, paper in enumerate(similar_papers, 1):
                logger.info(f"   {i}. [{paper['similarity']:.4f}] {paper['title'][:60]}...")

    # 清理连接
    paper_conn.close()
    user_conn.close()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info("\n" + "=" * 60)
    logger.info(f"✅ 迁移完成!")
    logger.info(f"   总耗时: {duration:.2f} 秒")
    logger.info(f"   论文 Embedding (paperignition): {paper_count} 条")
    logger.info(f"   用户 Embedding (paperignition_user): {user_count} 条")
    logger.info("=" * 60)


def test_search(config_path: str = None):
    """测试向量搜索功能"""
    # 加载配置
    load_all_config(config_path)

    logger.info("\n" + "=" * 60)
    logger.info("测试向量搜索功能")
    logger.info("=" * 60)

    # 初始化
    embedding_client = EmbeddingClient(
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_BASE_URL,
        model=EMBEDDING_MODEL,
        dimension=EMBEDDING_DIMENSION
    )

    paper_conn = get_db_connection(PAPER_DB_CONFIG)

    # 测试查询
    test_queries = [
        "机器学习",
        "自然语言处理",
        "计算机视觉"
    ]

    for query in test_queries:
        logger.info(f"\n🔍 查询: {query}")

        # 获取查询的 embedding
        query_embedding = embedding_client.get_embedding(query)

        if query_embedding:
            # 搜索相似论文
            similar_papers = search_similar_papers(paper_conn, query_embedding, top_k=3)

            logger.info("   相似论文:")
            for i, paper in enumerate(similar_papers, 1):
                logger.info(f"   {i}. [{paper['similarity']:.4f}] {paper['title'][:60]}...")

    paper_conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="迁移 Embedding 到 pgvector")
    parser.add_argument("--config", type=str, default=None,
                        help="配置文件路径 (默认: scripts/migration_config.yaml)")
    parser.add_argument("--test", action="store_true", help="只运行搜索测试")
    parser.add_argument("--max-papers", type=int, default=None, help="最大处理论文数量")
    parser.add_argument("--max-users", type=int, default=None, help="最大处理用户数量")

    args = parser.parse_args()

    # 命令行参数覆盖配置文件
    if args.max_papers is not None:
        MAX_PAPERS = args.max_papers
    if args.max_users is not None:
        MAX_USERS = args.max_users

    if args.test:
        test_search(args.config)
    else:
        main(args.config)
