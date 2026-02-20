# Application Environment (Production)
# Source this file before running the application

# Environment
export ENVIRONMENT="production"

# Database - Aliyun RDS
export METADATA_DB_URL="postgresql://paperignition:Paperignition111@pgm-bp17do9bav7s2yv3mo.pg.rds.aliyuncs.com:5432/paperignition"
export USER_DB_USER="paperignition"
export USER_DB_PASSWORD="Paperignition111"
export USER_DB_HOST="pgm-bp17do9bav7s2yv3mo.pg.rds.aliyuncs.com"
export USER_DB_PORT="5432"
export USER_DB_NAME="paperignition_user"

# Services
export INDEX_SERVICE_HOST="http://localhost:8002"
export APP_SERVICE_HOST="http://localhost:8080"

# OpenAI/LLM Service
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_API_KEY="sk-7d1b4bfa589c45f9a352d3e22623eec1"
