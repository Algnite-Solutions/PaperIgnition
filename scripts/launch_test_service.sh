#!/bin/bash
cd "$(dirname "$0")/.."

# Set test environment configuration
export PAPERIGNITION_CONFIG="backend/configs/test_config.yaml"
export PAPERIGNITION_ENV="testing"
export PAPERIGNITION_LOCAL_MODE="true"

echo "🧪 Starting Index API Server in TEST mode..."
echo "📁 Using config: $PAPERIGNITION_CONFIG"
echo "🌍 Environment: $PAPERIGNITION_ENV"

# Start the server with enhanced configuration management
uvicorn backend.index_service.main:app --host 0.0.0.0 --port 8002 --reload &
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload &
wait
