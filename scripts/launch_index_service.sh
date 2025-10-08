#!/bin/bash
cd "$(dirname "$0")/.."

# Set default configuration path for development environment
export PAPERIGNITION_CONFIG="backend/configs/app_config.yaml"
export PAPERIGNITION_ENV="development"

echo "🚀 Starting Index API Server in DEVELOPMENT mode..."
echo "📁 Using config: $PAPERIGNITION_CONFIG"
echo "🌍 Environment: $PAPERIGNITION_ENV"

# Start the server with enhanced configuration management
#uvicorn backend.index_service.main:app --host 0.0.0.0 --port 8002 --reload
uvicorn backend.index_service.main:app --host 0.0.0.0 --port 8002 