from fastapi import APIRouter, HTTPException
from .models import CustomerQuery
from AIgnite.data.docset import DocSet, TextChunk, FigureChunk, TableChunk, ChunkType,DocSetList


from .service import index_papers, get_metadata, find_similar

router = APIRouter()

@router.post("/index_papers/")
async def index_papers_route(docset_list: DocSetList):
    try:
        docsets = []
        for paper in docset_list.docsets:
            docsets.append(DocSet(
                doc_id=paper.doc_id,
                title=paper.title,
                abstract=paper.abstract,
                authors=paper.authors,
                categories=paper.categories,
                published_date=paper.published_date,
                pdf_path=paper.pdf_path,
                text_chunks=[TextChunk(**chunk.dict()) for chunk in paper.text_chunks],
                figure_chunks=[FigureChunk(**chunk.dict()) for chunk in paper.figure_chunks],
                table_chunks=[TableChunk(**chunk.dict()) for chunk in paper.table_chunks],
                metadata=paper.metadata or {}
            ))
        index_papers(docsets)
        return {"message": f"{len(docsets)} papers indexed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get_metadata/{doc_id}")
async def get_metadata_route(doc_id: str):
    metadata = get_metadata(doc_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return metadata

@router.post("/find_similar/")
async def find_similar_route(query: CustomerQuery):
    try:
        return find_similar(query.query, query.top_k, query.similarity_cutoff)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
