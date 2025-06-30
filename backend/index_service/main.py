from fastapi import FastAPI

from .db_utils import init_databases, load_config
from .routes import router
from .service import paper_indexer

app = FastAPI()
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    # Setup databases and inject into indexer
    config = load_config()
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