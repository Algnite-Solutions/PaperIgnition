### models.py
from pydantic import BaseModel, RootModel, Field, validator
from typing import List, Dict, Any, Optional
from AIgnite.data.docset import DocSet, TextChunk, FigureChunk, TableChunk, ChunkType, DocSetList



# --- Request Models ---

class CustomerQuery(BaseModel):
    query: str = Field(..., description="Search query string")
    top_k: Optional[int] = Field(default=5, description="Number of results to return", ge=1)
    similarity_cutoff: Optional[float] = Field(
        default=0.8,
        description="Minimum similarity score (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    strategy_type: Optional[str] = Field(
        default=None,
        description="Search strategy to use ('vector', 'tf-idf', or 'hybrid')"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="""Optional filters to apply to the search. Supports new structured format:
        {
            "include": {
                "categories": ["cs.AI", "cs.LG"],
                "authors": ["John Doe"],
                "published_date": ["2023-01-01", "2023-12-31"],
                "doc_ids": ["doc1", "doc2"],
                "title_keywords": ["machine learning"],
                "abstract_keywords": ["neural networks"]
            },
            "exclude": {
                "categories": ["cs.CR"],
                "authors": ["Jane Smith"]
            }
        }
        
        Also supports backward compatibility with simple format:
        {"doc_ids": ["doc1", "doc2"]}
        """
    )

    @validator('query')
    def query_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Query string cannot be empty')
        return v.strip()

    @validator('strategy_type')
    def validate_strategy_type(cls, v):
        if v is not None and v not in ['vector', 'tf-idf', 'hybrid']:
            raise ValueError("strategy_type must be one of: 'vector', 'tf-idf', 'hybrid'")
        return v