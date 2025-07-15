# Index Service Module

## Overview
This module provides initialization, health checking, and API routing for the three core databases used by the Index Service:
- **MetadataDB** (PostgreSQL)
- **VectorDB** (Faiss)
- **MinioImageDB** (MinIO)

It exposes service functions and FastAPI endpoints for initializing databases, checking their health, and managing document indexing and search.

## Main Components

- `db_init.py`: Handles creation, recreation, and health checking of all three database types.
- `service.py`: Business logic for database operations, indexer creation, document indexing, search, and health status aggregation.
- `routes.py`: FastAPI endpoints for all service functions, including database health check.
- `config.py`: Loads and validates YAML-based configuration for all database backends.
- `index_service_setup.md`: Detailed setup guide for configuring and running the Index Service.

## Setup & Usage

1. **Install dependencies** (see project root requirements).
2. **Configure databases** using a YAML config file (see `index_service_setup.md` and example in `tests/config.yaml`).
3. **Start the service**:
   ```bash
   bash scripts/launch_index_service.sh
   ```
4. **API available** at the configured host/port (default: `http://localhost:8000`).

## API Endpoints

- `POST /init_database` — Initialize all databases and create the indexer
- `POST /index_documents/` — Index a list of documents
- `GET /get_document/{doc_id}` — Get metadata for a specific document
- `POST /find_similar_documents/` — Find documents similar to a query
- `POST /databases_health` — Check health of all databases (independent of indexer, covered by automated test: `test_databases_health` in `tests/test_api_endpoints.py`)
- `GET /health` — Basic service health check (function: `server_health_check`)

### Example: Database Health Check
```bash
curl -X POST http://localhost:8000/databases_health \
  -H 'Content-Type: application/json' \
  -d '{"config": { ... }}'
```
Returns:
```json
{
  "metadata_db": "healthy",
  "vector_db": "healthy",
  "image_db": "unavailable"
}
```

## Troubleshooting
- Ensure all database services are running and accessible.
- Check logs for detailed error messages.
- Use `/databases_health` to diagnose configuration or connectivity issues. (This endpoint is covered by automated tests; see `tests/test_api_endpoints.py`)

## Reference
For detailed setup and configuration, see [`index_service_setup.md`](./index_service_setup.md).

- The system supports running with only `metadata_db` configured (minimal configuration, no vector_db or minio_db required). This scenario is covered by automated tests (see `run_minimal_metadata_db_tests` in `tests/test_api_endpoints.py`). 