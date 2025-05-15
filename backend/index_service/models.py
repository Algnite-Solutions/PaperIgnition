### models.py
from pydantic import BaseModel, RootModel
from typing import List, Dict, Any, Optional
from AIgnite.data.docset import DocSet, TextChunk, FigureChunk, TableChunk, ChunkType,DocSetList



# --- Request Models ---
class ChunkInput(BaseModel):
    type: str
    text: str

class DocSetInput(BaseModel):
    doc_id: str
    title: str
    abstract: str
    authors: List[str]
    categories: List[str]
    published_date: str
    pdf_path: str
    text_chunks: List[TextChunk]
    figure_chunks: List[FigureChunk]
    table_chunks: List[TableChunk]
    metadata: Optional[Dict[str, Any]] = {}

#class DocSetList(RootModel):
#    root: List[DocSetInput]

class SimilarQuery(BaseModel):
    query: str
    top_k: int = 5
    similarity_cutoff: float = 0.8