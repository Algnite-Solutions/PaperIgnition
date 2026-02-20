# PaperIgnition Backend

## Environment Configuration

This backend uses environment variables for all configuration. See [Configuration](#configuration) below.

## Quick Start

### 1. Set Environment Variables

```bash
# For production/app environment
source .env.app

# For test environment
source .env.test
```

### 2. Start Services

```bash
# Backend Service (port 8000)
cd backend
uvicorn app.main:app --reload --port 8000

# Index Service (port 8002)
uvicorn index_service.main:app --reload --port 8002
```

### 3. Test Services

```bash
# Test health endpoints
curl http://localhost:8000/api/health
curl http://localhost:8002/health
```

## Configuration

### Environment Variables

The following environment variables are used in the configuration files:

#### Database Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `METADATA_DB_URL` | PostgreSQL connection string for paper metadata | `postgresql://user:pass@host:5432/db` |
| `USER_DB_USER` | Database username for user database | `paperignition` |
| `USER_DB_PASSWORD` | Database password for user database | `your_password` |
| `USER_DB_HOST` | Database host for user database | `pgm-xxxxx.pg.rds.aliyuncs.com` |
| `USER_DB_PORT` | Database port | `5432` |
| `USER_DB_NAME` | Database name for user database | `paperignition_user` |

#### Service URLs

| Variable | Description | Default |
|----------|-------------|---------|
| `INDEX_SERVICE_HOST` | Index service URL | `http://localhost:8002` |
| `APP_SERVICE_HOST` | Backend service URL | `http://localhost:8080` |

#### OpenAI/LLM Service

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_BASE_URL` | Base URL for LLM API | `https://api.deepseek.com` |
| `OPENAI_API_KEY` | API key for LLM service | `sk-xxxxx` |

### How It Works

1. **YAML files use `${VARIABLE}` syntax** to reference environment variables
2. **Config loader** automatically substitutes these with actual values from environment
3. **Source the `.env` file** before starting services to load variables

Example from `configs/app_config.yaml`:

```yaml
USER_DB:
  db_user: "${USER_DB_USER}"
  db_password: "${USER_DB_PASSWORD}"
  db_host: "${USER_DB_HOST}"
```

### Configuration Files

| File | Purpose | Environment |
|------|---------|-------------|
| `configs/app_config.yaml` | Production configuration | Uses `.env.app` |
| `configs/test_config.yaml` | Test configuration | Uses `.env.test` |

## Project Structure

```
backend/
├── app/                    # Backend service (FastAPI)
│   ├── main.py            # Application entry point
│   ├── routers/           # API route handlers
│   │   ├── auth.py        # Authentication endpoints
│   │   ├── papers.py      # Paper recommendations
│   │   ├── favorites.py   # Favorite paper management
│   │   ├── users.py       # User profile management
│   │   └── static.py      # Static file serving
│   ├── crud/              # Database CRUD operations
│   ├── models/            # SQLAlchemy database models
│   ├── auth/              # Authentication utilities
│   └── db_utils.py        # Database connection management
├── index_service/         # Index service (FastAPI)
│   ├── main.py            # Index service entry point
│   ├── routes.py          # Index API endpoints
│   └── service.py         # Paper indexing logic
├── shared/                # Shared utilities
│   └── config_utils.py    # Configuration loader with env var support
├── configs/               # Configuration files
│   ├── app_config.yaml    # Production config (uses ${VAR} syntax)
│   └── test_config.yaml   # Test config (uses ${VAR} syntax)
└── tests/                 # Integration tests
    └── integration/
        └── test_backend_endpoints.py
```

## API Endpoints

### Backend Service (port 8000)

#### Authentication
- `POST /api/auth/register-email` - User registration
- `POST /api/auth/login-email` - User login
- `DELETE /api/auth/users/{email}` - Delete user (test mode only)

#### Papers
- `GET /api/digests/recommendations/{username}` - Get user recommendations
- `POST /api/digests/recommendations/{paper_id}/feedback` - Submit feedback
- `POST /api/digests/{paper_id}/mark-viewed` - Mark paper as viewed
- `GET /api/digests/blog_content/{paper_id}/{username}` - Get blog content

#### Favorites
- `POST /api/favorites/add` - Add to favorites
- `DELETE /api/favorites/remove/{paper_id}` - Remove from favorites
- `GET /api/favorites/list` - List user favorites
- `GET /api/favorites/check/{paper_id}` - Check if paper is favorited

#### Users
- `GET /api/users/me` - Get current user info
- `PUT /api/users/interests` - Update user research interests
- `GET /api/users/recommendation-history` - Get recommendation history

#### Health
- `GET /api/health` - Health check
- `GET /api/domains` - Get research domains

### Index Service (port 8002)

#### Paper Indexing
- `POST /index_papers` - Index papers
- `POST /find_similar` - Find similar papers

#### Content Retrieval
- `GET /get_metadata/{doc_id}` - Get paper metadata
- `GET /paper_content/{doc_id}` - Get paper content

## Development

### Running Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test class
pytest tests/integration/test_backend_endpoints.py::TestAuthEndpoints -v

# Run specific test
pytest tests/integration/test_backend_endpoints.py::TestAuthEndpoints::test_email_login_success -v
```

### Database Initialization

```bash
# Initialize both databases
python scripts/init_all_tables.py

# Initialize only user database
python scripts/init_all_tables.py --init-user-db

# Initialize only metadata database
python scripts/init_all_tables.py --init-metadata-db
```

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/list_users.py` | List all users in database |
| `scripts/reset_password.py` | Reset user password |
| `scripts/test_login.py` | Test login endpoint |

## Best Practices

1. **Source environment before starting services**
   ```bash
   source .env.app
   uvicorn app.main:app --reload --port 8000
   ```

2. **Never commit `.env.app` to version control** - it contains sensitive credentials

3. **Check logs** for errors if services fail to start
   - Backend logs: Console output
   - Index service logs: Console output

4. **Test environment variables** are set
   ```bash
   echo $USER_DB_HOST
   echo $USER_DB_PASSWORD
   ```

## Troubleshooting

### "Environment variable not found"

**Solution:** Make sure you've sourced the environment file
```bash
source .env.app  # or .env.test
```

### Database connection errors

**Solution:** Verify environment variables are set correctly
```bash
echo $USER_DB_HOST
echo $USER_DB_PASSWORD
psql -h $USER_DB_HOST -U $USER_DB_USER -d $USER_DB_NAME
```

### Services can't connect to each other

**Solution:** Check service host variables
```bash
echo $INDEX_SERVICE_HOST
echo $APP_SERVICE_HOST
```

### ModuleNotFoundError: No module named 'AIgnite'

**Solution:** Set PYTHONPATH to include AIgnite package
```bash
export PYTHONPATH=/path/to/AIgnite/src:/path/to/PaperIgnition
```

## Security Notes

- `.env.app` contains production credentials - **NEVER commit to git**
- API keys and passwords are externalized from code
- Rotate credentials regularly
- Use different databases for app and test when possible

## Additional Documentation

- `API_Documentation.md` - Detailed API endpoint documentation
- `app/README.md` - Backend service documentation
- `index_service/README.md` - Index service documentation
