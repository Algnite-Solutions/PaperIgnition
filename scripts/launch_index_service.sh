#!/bin/bash
echo "🚀 Starting Index API Server..."
uvicorn backend.index_service.main:app --host 0.0.0.0 --port 8000 --reload
