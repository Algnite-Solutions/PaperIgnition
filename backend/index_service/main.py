from fastapi import FastAPI, HTTPException
import os

from backend.index_service.db_utils import init_databases, load_config
from backend.index_service.routes import router
from backend.index_service.service import paper_indexer

app = FastAPI()
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    # Setup databases and inject into indexer
    print("🚀 Starting INDEX_SERVICE with enhanced configuration management...")
    
    # Load configuration using enhanced load_config function
    # This will automatically set environment variables and cache the config
    config_path=os.environ.get('PAPERIGNITION_CONFIG')
    config = load_config(config_path,set_env=True)
    
    print(f"📁 Configuration loaded from: {os.environ.get('PAPERIGNITION_CONFIG', 'default path')}")
    print(f"🌍 Environment variables set: {len([k for k in os.environ.keys() if k.startswith('PAPERIGNITION_')])} config variables")
    

    print(config)
    vector_db, metadata_db, image_db = init_databases(config)
    try:
        paper_indexer.set_databases(vector_db, metadata_db, image_db)
        
    except ValueError as e:  # Handle validation errors from init_db
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # Handle other errors
        raise HTTPException(status_code=500, detail=f"Failed to initialize database: {str(e)}")

    paper_indexer.set_databases(vector_db, metadata_db, image_db)
    paper_indexer.set_search_strategy("tf-idf")  # or "vector", "tf-idf"
    print("✅ PaperIndexer initialized at startup.")