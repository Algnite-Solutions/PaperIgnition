# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PaperIgnition is an AI-powered academic paper recommendation system that fetches papers from arXiv, indexes them for semantic search, and generates blog summaries using LLMs. The system supports a WeChat mini-program frontend and an H5 web interface.

### Architecture

The system consists of three main layers:

1. **AIgnite Package** (`../AIgnite/src/`) - Core library for paper indexing and recommendation
   - `AIgnite.index.PaperIndexer` - Main indexer orchestrating vector search, metadata retrieval, and filtering
   - `AIgnite.db.VectorDB` - FAISS-based vector storage (LangChain integration)
   - `AIgnite.db.MetadataDB` - PostgreSQL metadata storage with full-text search
   - `AIgnite.db.MinioImageDB` - MinIO image storage for figures
   - `AIgnite.recommendation` - Recommendation and reranking modules

2. **Backend Services** (FastAPI)
   - **Backend Service** (`backend/app/`, port 8000) - User auth, paper recommendations, favorites
   - **Index Service** (`backend/index_service/`, port 8002) - Paper indexing, similarity search, content retrieval
   - **Shared Utilities** (`backend/shared/`) - Common configuration loading and database utilities

3. **Orchestrator** (`orchestrator/`) - Daily task automation
   - Fetches papers from arXiv
   - Indexes papers into vector and metadata databases
   - Generates blog summaries using Gemini/vLLM
   - Creates personalized recommendations per user

4. **Frontend** - H5 web interface (`beta_frontend/`) - Taro-based web interface

### Database Architecture

The system uses **two PostgreSQL databases**:

- **paperignition_user** (User DB) - User accounts, recommendations, favorites
  - Tables: `users`, `research_domains`, `paper_recommendations`, `favorite_papers`, `user_retrieve_results`, `job_logs`

- **paperignition** (Metadata DB) - Paper metadata, text chunks
  - Tables: `papers`, `text_chunks` (with GIN index for full-text search)

Additionally:
- **FAISS** - Local vector storage (path: `/data3/guofang/AIgnite-Solutions/PaperIgnition/vector_db/paperignition_db`)
- **MinIO** - Object storage for PDFs and images (endpoint: `10.0.1.226:9081`)

### Configuration System

Configuration is centralized in YAML files with environment variable overrides:

- `backend/configs/app_config.yaml` - Production config
- `backend/configs/test_config.yaml` - Local dev config (uses `test_user_db`)
- `orchestrator/development_config.yaml` - Orchestrator local config
- `orchestrator/production_config.yaml` - Orchestrator production config

Environment variables:
- `PAPERIGNITION_CONFIG` - Override config path
- `PAPERIGNITION_LOCAL_MODE` - Enable local mode (`true`/`false`)
- `PAPERIGNITION_INDEX_SERVICE_HOST` - Override index service URL

The system automatically sets environment variables from config files using `load_config()` in both backend services.

### Shared Configuration Loading (Updated 2025-02-12)

Configuration loading has been consolidated to eliminate duplicate code:

- **`backend/shared/config_utils.py`** - Unified configuration loader
  - Supports both backend service (USER_DB, INDEX_SERVICE, APP_SERVICE) and index service (vector_db, metadata_db, minio_db)
  - Environment variable support with `set_env` parameter
  - Storage info display with `display_storage_info` parameter
  - Single source of truth for all configuration

- **Deprecated configurations removed:**
  - `config.yaml` (root) - Empty file, deleted
  - `backend/index_service/index_service_setup_deprecated.md` - Old docs, deleted
  - `orchestrator/NEW/` - Experimental code with old paths, deleted
  - `scripts/export_data_from_db/app_config.yaml` - Duplicate config, deleted

- **Deprecated scripts (marked but not removed):**
  - `scripts/user_db_init.py` - Use `scripts/init_all_tables.py --init-user-db` instead
  - `scripts/paper_db_init.py` - Use `scripts/init_all_tables.py --init-metadata-db` instead

Both deprecated scripts remain functional for backward compatibility but clearly marked as deprecated.

## Development Commands

### Environment Setup

```bash
# Set PYTHONPATH (required for AIgnite package import)
export PYTHONPATH=/Users/bran/Desktop/AIgnite-Solutions/AIgnite/src:/Users/bran/Desktop/AIgnite-Solutions/PaperIgnition

# Windows PowerShell equivalent
$env:PYTHONPATH = "D:\PaperIgnition\PaperIgnition"
```

### Database Initialization

```bash
# Initialize both User DB and Metadata DB (recommended)
python scripts/init_all_tables.py

# Initialize only User DB
python scripts/init_all_tables.py --init-user-db

# Initialize only Metadata DB
python scripts/init_all_tables.py --init-metadata-db

# Legacy methods (deprecated but still functional):
python scripts/user_db_init.py  # Use init_all_tables.py instead
python scripts/paper_db_init.py  # Use init_all_tables.py instead
```

### Starting Services

```bash
# Backend Service (port 8000)
cd backend
uvicorn app.main:app --reload --port 8000

# Index Service (port 8002)
uvicorn index_service.main:app --reload --port 8002

# Frontend (H5 with Nginx)
cd beta_frontend
nginx -c nginx_mac.conf  # Serves on port 8080
```

### Running Tests

```bash
# Test API connections
python tests/test_api_connections.py

# Test specific services
python tests/test_index_service.py
python tests/test_user_db_endpoints.py
```

### Running Orchestrator

```bash
cd orchestrator

# Development mode (uses development_config.yaml)
python orchestrator.py

# Production mode
python orchestrator.py production_config.yaml
```

The orchestrator runs configurable stages:
- `fetch_daily_papers` - Fetch from arXiv
- `generate_all_papers_blog` - Generate blogs for all papers
- `generate_per_user_blogs` - Generate personalized recommendations

## Code Architecture

### Backend Service (`backend/app/`)

- **main.py** - FastAPI app with lifespan management, initializes `DatabaseManager`
- **db_utils.py** - `DatabaseManager` class for async PostgreSQL connections using SQLAlchemy + asyncpg
- **models/users.py** - SQLAlchemy models for user domain (User, FavoritePaper, UserPaperRecommendation, etc.)
- **routers/** - API route handlers:
  - `auth.py` - WeChat OAuth login
  - `users.py` - User profile and preferences
  - `papers.py` - Paper recommendations and retrieve results
  - `favorites.py` - Favorite paper management
  - `static.py` - Static file serving

### Index Service (`backend/index_service/`)

- **main.py** - FastAPI app, initializes `PaperIndexer` with VectorDB, MetadataDB, and MinioImageDB
- **db_utils.py** - `init_databases()` loads config and initializes all three databases
- **service.py** - Wrapper functions for `PaperIndexer` methods:
  - `index_papers()` - Store papers across all databases
  - `find_similar()` - Semantic search with filtering
  - `get_metadata()` - Retrieve paper metadata
  - `get_image()` - Retrieve images from MinIO
- **routes.py** - API endpoints mapping to service functions

### PaperIndexer (AIgnite Package)

The `PaperIndexer` class orchestrates three database types:

1. **Vector Search** - FAISS-based semantic search with embedding models (BGE/GritLM)
2. **Metadata Retrieval** - PostgreSQL for paper metadata and text chunks
3. **Image Storage** - MinIO for figure storage and retrieval

Key methods:
- `index_papers()` - Parallel storage: metadata → vectors → images
- `find_similar_papers()` - Hybrid search combining vector similarity, TF-IDF, and filters
- `set_search_strategy()` - Configure search strategies: `['vector', 'tf-idf']` with thresholds
- `get_paper_metadata()` - Retrieve metadata by doc_id
- `store_images()` - Batch image storage to MinIO

### Search and Filtering

The system supports advanced search with:
- **Search Strategies**: Vector (semantic), TF-IDF (keyword), BM25
- **Filters**: Categories, authors, date ranges, doc_ids, text_type (abstract/chunk/combined)
- **Result Types**: metadata, text_chunks, search_parameters, full_text, images

Filters support structured `include`/`exclude` format:
```python
filters = {
    "include": {"categories": ["cs.AI", "cs.LG"], "published_date": ["2023-01-01", "2023-12-31"]},
    "exclude": {"categories": ["cs.CR"]}
}
```

### API Communication

Services communicate via HTTP:
- **Orchestrator → Index Service**: `POST /index_papers`, `POST /find_similar`
- **Orchestrator → Backend Service**: `POST /users/{username}/recommendations`
- **Frontend → Backend**: `/api/auth/*`, `/api/papers/*`, `/api/favorites/*`
- **Frontend → Index**: `/find_similar`, `/paper_content`, `/get_metadata`

### Data Flow

1. **Paper Fetching**: `orchestrator/paper_pull.py` → arXiv API → DocSet objects
2. **Indexing**: Index Service → MetadataDB (PostgreSQL) + VectorDB (FAISS) + MinioImageDB
3. **Search**: Frontend query → Index Service → Vector search + Metadata retrieval → Results
4. **Recommendation**: Orchestrator → Search per user → Backend API → Generate blogs → Store recommendations

## Important Implementation Details

### Async Database Access

The backend uses SQLAlchemy async engine with `asyncpg`:
```python
# DatabaseManager pattern (backend/app/db_utils.py)
db_manager = DatabaseManager(db_config)
await db_manager.initialize()
async with db_manager.get_session() as db:
    # Query operations
```

### Configuration Loading

Always use the centralized `load_config()` function:
```python
from backend.index_service.db_utils import load_config
config = load_config(config_path, set_env=True, display_storage_info=True)
```

This function:
- Loads YAML config
- Sets environment variables automatically
- Displays storage statistics (optional)
- Caches config for subsequent calls

### DocSet Model

Papers are represented as `AIgnite.data.docset.DocSet` objects containing:
- `text_chunks` - List of TextChunk (main content)
- `figure_chunks` - List of FigureChunk (images)
- `table_chunks` - List of TableChunk (tables)
- Metadata fields: `doc_id`, `title`, `authors`, `abstract`, `categories`, `published_date`

### Embedding Models

VectorDB supports multiple embedding models:
- **BGE**: `BAAI/bge-base-en-v1.5` (768 dimensions)
- **GritLM**: `GritLM/GritLM-7B` (4096 dimensions, used in production)

The model is specified in config: `vector_db.model_name`

### Logging

Orchestrator uses `JobLogger` class to track job execution:
```python
job_id = await job_logger.start_job_log(job_type="blog_generation", username="user")
await job_logger.complete_job_log(job_id, status="success", details={...})
```

Logs are stored in:
- `orchestrator/logs/paperignition_execution.log`
- Database: `job_logs` table

## Common Issues

### Missing AIgnite Package

If you get `ModuleNotFoundError: No module named 'AIgnite'`:
```bash
export PYTHONPATH=/Users/bran/Desktop/AIgnite-Solutions/AIgnite/src:/Users/bran/Desktop/AIgnite-Solutions/PaperIgnition
```

### Database Connection Errors

Check config files and ensure PostgreSQL is running:
```bash
# Check if PostgreSQL is running
psql -U postgres -c "SELECT version();"

# Test connection to user database
psql -U test_user -d test_user_db
```

### Index Service Not Responding

The Index Service requires all three databases to be initialized. Check startup logs for:
- "Vector database initialized"
- "Metadata database initialized"
- "MinIO image database initialized"

If MinIO fails, the service will still start but image operations will fail.

### Vector Search Returns No Results

Common causes:
1. FAISS index file missing or corrupted
2. Embedding model dimension mismatch
3. Search strategy threshold too high

Check vector storage info:
```python
from backend.index_service.db_utils import load_config, init_databases
config = load_config(path, display_storage_info=True)
```

## Deployment Considerations

### Production vs Development Configs

- **Development**: Uses `test_user_db`, `localhost:5432`, local vector storage
- **Production**: Uses `paperignition_user`, remote PostgreSQL, shared MinIO

### Migration to Cloud

When migrating to Alibaba Cloud RDS:
1. Update `db_url` in config files to RDS endpoint
2. Enable pgvector extension for future vector migration
3. Consider migrating MinIO to OSS
4. Update security group whitelist to allow local Mac access

### Service Dependencies

Startup order matters:
1. PostgreSQL must be running
2. MinIO must be accessible (for Index Service)
3. Backend Service (port 8000)
4. Index Service (port 8002)
5. Frontend/Nginx (port 8080)

## File Structure Notes

- `backend/configs/` - Service configuration files
- `orchestrator/blogsByGemini/` - Generated blog storage (development)
- `orchestrator/{htmls,jsons,imgs}` - Scraped paper data
- `scripts/` - Database initialization and utility scripts
- `tests/` - API and integration tests
