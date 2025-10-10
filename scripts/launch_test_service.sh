#!/bin/bash
cd "$(dirname "$0")/.."

# Set test environment configuration
export PAPERIGNITION_CONFIG="backend/configs/test_config_gf.yaml"
export PAPERIGNITION_ENV="testing"
export PAPERIGNITION_LOCAL_MODE="true"
export PYTHONPATH="/Users/bran/Desktop/AIgnite-Solutions/AIgnite/src"

echo "🧪 Starting Index API Server in TEST mode..."
echo "📁 Using config: $PAPERIGNITION_CONFIG"
echo "🌍 Environment: $PAPERIGNITION_ENV"

# Start the server with enhanced configuration management
uvicorn backend.index_service.main:app --host 0.0.0.0 --port 8008 --reload &
uvicorn backend.app.main:app --host 0.0.0.0 --port 8007 --reload &
wait
