### service.py
from AIgnite.index.paper_indexer import PaperIndexer

indexer = PaperIndexer()

def index_papers(docsets):
    indexer.index_papers(docsets)

def get_metadata(doc_id):
    return indexer.get_paper_metadata(doc_id)

def find_similar(query, top_k, cutoff):
    return indexer.find_similar_papers(query=query, top_k=top_k, similarity_cutoff=cutoff)


