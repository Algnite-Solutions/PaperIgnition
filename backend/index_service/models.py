### models.py
from pydantic import BaseModel, RootModel
from typing import List, Dict, Any, Optional
from AIgnite.data.docset import DocSet, TextChunk, FigureChunk, TableChunk, ChunkType,DocSetList



# --- Request Models ---

class CustomerQuery(BaseModel):
    query: str
    top_k: int = 5
    similarity_cutoff: float = 0.8