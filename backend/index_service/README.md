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

## Advanced Features

### Text Type Filtering
The system supports advanced text type filtering through the `text_type` field, allowing users to precisely control which parts of papers are searched:

- **`abstract`**: Search only in paper abstracts for faster, more focused results
- **`chunk`**: Search in individual text chunks for detailed content matching
- **`combined`**: Search in the combination of title, categories, and abstract for comprehensive coverage

This feature is particularly useful for:
- **Performance optimization**: Limiting search to abstracts can significantly improve search speed
- **Result relevance**: Focusing on specific text types can improve result quality
- **Search strategy**: Different text types may be more appropriate for different use cases

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
- `POST /index_papers/` — Index a list of papers
- `GET /get_metadata/{doc_id}` — Get metadata for a specific paper
- `POST /find_similar/` — Find papers similar to a query
- `GET /health` — Basic service health check

### Advanced Search with Filters

The `/find_similar/` endpoint supports advanced filtering with a structured format:

#### Filter Structure
```json
{
  "query": "machine learning",
  "top_k": 10,
  "similarity_cutoff": 0.7,
  "strategy_type": "hybrid",
  "filters": {
    "include": {
      "categories": ["cs.AI", "cs.LG"],
      "authors": ["John Doe"],
      "published_date": ["2023-01-01", "2023-12-31"],
      "doc_ids": ["doc1", "doc2"],
      "title_keywords": ["neural networks"],
      "abstract_keywords": ["deep learning"],
      "text_type": ["abstract", "chunk", "combined"]
    },
    "exclude": {
      "categories": ["cs.CR"],
      "authors": ["Jane Smith"],
      "text_type": ["chunk"]
    }
  }
}
```

#### Supported Filter Fields
- **categories**: Array of category strings (e.g., ["cs.AI", "cs.LG"])
- **authors**: Array of author names (partial matching supported)
- **published_date**: Date range ["start_date", "end_date"] or exact date
- **doc_ids**: Array of specific document IDs
- **title_keywords**: Keywords to search in paper titles
- **abstract_keywords**: Keywords to search in paper abstracts
- **text_type**: Array of text types to include/exclude in search:
  - `"abstract"`: Search only in paper abstracts
  - `"chunk"`: Search only in text chunks (document sections)
  - `"combined"`: Search in title + categories + abstract combination

#### Backward Compatibility
Simple filter format is still supported:
```json
{
  "query": "machine learning",
  "filters": {"doc_ids": ["doc1", "doc2"]}
}
```

### Example: Find Similar Papers
```bash
curl -X POST http://localhost:8000/find_similar/ \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "machine learning",
    "top_k": 5,
    "similarity_cutoff": 0.8,
    "strategy_type": "hybrid",
    "filters": {
      "include": {
        "categories": ["cs.AI"],
        "published_date": ["2023-01-01", "2023-12-31"]
      }
    }
  }'
```

### Example: Text Type Filtering
```bash
# Search only in paper abstracts (faster, more focused)
curl -X POST http://localhost:8000/find_similar/ \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "neural networks",
    "top_k": 10,
    "filters": {
      "include": {
        "text_type": ["abstract"]
      }
    }
  }'

# Search in both abstracts and combined text, exclude chunks
curl -X POST http://localhost:8000/find_similar/ \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "deep learning",
    "top_k": 15,
    "filters": {
      "include": {
        "text_type": ["abstract", "combined"]
      },
      "exclude": {
        "text_type": ["chunk"]
      }
    }
  }'
```

### Example: Database Health Check
```bash
curl -X POST http://localhost:8000/init_database \
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
- Use `/init_database` to diagnose configuration or connectivity issues.

## Reference
For detailed setup and configuration, see [`index_service_setup.md`](./index_service_setup.md).

- The system supports running with only `metadata_db` configured (minimal configuration, no vector_db or minio_db required). 