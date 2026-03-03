### models.py
from pydantic import BaseModel, RootModel, Field, validator
from typing import List, Dict, Any, Optional, Tuple
from AIgnite.data.docset import DocSet, TextChunk, FigureChunk, TableChunk, ChunkType, DocSetList



# --- Request Models ---

class IndexPapersRequest(BaseModel):
    docsets: DocSetList = Field(..., description="List of DocSet objects containing paper information")
    store_images: bool = Field(default=False, description="Whether to store images to MinIO (default: False)")
    keep_temp_image: bool = Field(default=True, description="If False, delete temporary image files after successful storage (default: False)")

class CustomerQuery(BaseModel):
    query: str = Field(..., description="Search query string")
    top_k: Optional[int] = Field(default=5, description="Number of results to return", ge=1)
    retrieve_k: Optional[int] = Field(
        default=None,
        description="Optional number of results for retrieval (for reranking debug). If provided, returns extended format.",
        ge=1
    )
    retrieve_result: Optional[bool] = Field(
        default=False,
        description="Whether to save retrieve results to database for reranking debug"
    )
    similarity_cutoff: Optional[float] = Field(
        default=0.8,
        description="Minimum similarity score (0.0 to 1.0)",
        ge=0.0,
        le=3.0
    )
    search_strategies: Optional[List[Tuple[str, float]]] = Field(
        default=None,
        description="List of search strategies and their thresholds. Format: [('vector', 0.5), ('tf-idf', 0.1)]"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="""Optional filters to apply to the search. Supports structured include/exclude format:
        {
            "include": {
                "categories": ["cs.AI", "cs.LG"],           # 分类过滤，支持多个分类
                "authors": ["John Doe"],                     # 作者过滤，支持部分匹配
                "published_date": ["2023-01-01", "2023-12-31"], # 日期范围过滤
                "doc_ids": ["doc1", "doc2"],                 # 特定文档ID过滤
                "title_keywords": ["machine learning"],      # 标题关键词过滤
                "abstract_keywords": ["neural networks"],    # 摘要关键词过滤
                "text_type": ["abstract", "chunk", "combined"] # 文本类型过滤
            },
            "exclude": {
                "categories": ["cs.CR"],                     # 排除特定分类
                "authors": ["Jane Smith"],                   # 排除特定作者
                "text_type": ["chunk"]                       # 排除特定文本类型
            }
        }
        
        text_type filter supports three values:
        - "abstract": Search only in paper abstracts (faster, more focused)
        - "chunk": Search only in text chunks (detailed content matching)
        - "combined": Search in title + categories + abstract combination (comprehensive coverage)
        
        Also supports backward compatibility with simple format:
        {"doc_ids": ["doc1", "doc2"]}
        """
    )
    result_include_types: Optional[List[str]] = Field(
        default=None,
        description="""List of data types to include in results. Supported types:
        - 'metadata': Paper metadata (title, abstract, authors, categories, published_date)
        - 'text_chunks': Text chunk content from the paper
        - 'search_parameters': Search parameters and similarity scores
        - 'full_text': Complete text content of the paper
        - 'images': Image data from the paper
        
        Default: ['metadata', 'search_parameters']"""
    )

    @validator('query')
    def query_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Query string cannot be empty')
        return v.strip()

    @validator('retrieve_k')
    def validate_retrieve_k(cls, v, values):
        """Validate retrieve_k is greater than or equal to top_k if provided"""
        if v is not None and 'top_k' in values:
            top_k = values['top_k']
            if top_k and v < top_k:
                raise ValueError(f'retrieve_k ({v}) must be >= top_k ({top_k})')
        return v

    @validator('search_strategies')
    def validate_search_strategies(cls, v):
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("search_strategies must be a list")
            for strategy_tuple in v:
                if not isinstance(strategy_tuple, tuple) or len(strategy_tuple) != 2:
                    raise ValueError("Each search strategy must be a tuple of (strategy_type, threshold)")
                strategy_type, threshold = strategy_tuple
                if strategy_type not in ['vector', 'tf-idf']:
                    raise ValueError("Strategy type must be 'vector' or 'tf-idf'")
                if not isinstance(threshold, (int, float)) or not (0.0 <= threshold <= 2.0):
                    raise ValueError("Threshold must be a number between 0.0 and 2.0")
        return v

    @validator('result_include_types')
    def validate_result_include_types(cls, v):
        if v is not None:
            supported_types = {'metadata', 'text_chunks', 'search_parameters', 'full_text', 'images'}
            for data_type in v:
                if data_type not in supported_types:
                    raise ValueError(f"Unsupported result_include_type: {data_type}. Supported types: {', '.join(sorted(supported_types))}")
        return v

    @validator('filters')
    def validate_filters(cls, v):
        """Validate filter structure and supported fields."""
        if v is not None:
            # Check for new structured format
            if "include" in v or "exclude" in v:
                supported_fields = {'categories', 'authors', 'published_date', 'doc_ids', 'title_keywords', 'abstract_keywords', 'text_type'}
                
                for filter_type in ["include", "exclude"]:
                    if filter_type in v:
                        if not isinstance(v[filter_type], dict):
                            raise ValueError(f"{filter_type} filters must be a dictionary")
                        
                        for field in v[filter_type]:
                            if field not in supported_fields:
                                raise ValueError(f"Unsupported filter field: {field}. Supported fields: {', '.join(sorted(supported_fields))}")
                            
                            # Validate text_type values
                            if field == "text_type":
                                valid_types = {'abstract', 'chunk', 'combined'}
                                value = v[filter_type][field]
                                if isinstance(value, str):
                                    if value not in valid_types:
                                        raise ValueError(f"Invalid text_type value: {value}. Valid values: {', '.join(sorted(valid_types))}")
                                elif isinstance(value, list):
                                    for t in value:
                                        if t not in valid_types:
                                            raise ValueError(f"Invalid text_type value: {t}. Valid values: {', '.join(sorted(valid_types))}")
                                else:
                                    raise ValueError(f"text_type must be a string or list of strings")
        return v


# --- Image-related Models ---

class SaveImageRequest(BaseModel):
    object_name: str = Field(..., description="Object name to use for storage in MinIO")
    image_path: Optional[str] = Field(default=None, description="Path to image file (mutually exclusive with image_data)")
    image_data: Optional[str] = Field(default=None, description="Base64 encoded image data (mutually exclusive with image_path)")
    
    @validator('image_path', 'image_data')
    def validate_image_input(cls, v, values):
        """Validate that exactly one of image_path or image_data is provided."""
        if 'image_path' in values and 'image_data' in values:
            if values['image_path'] is not None and values['image_data'] is not None:
                raise ValueError("Only one of image_path or image_data should be provided")
        return v

class GetImageRequest(BaseModel):
    object_name: str = Field(..., description="Object name in MinIO storage")
    save_path: Optional[str] = Field(default=None, description="Optional path to save the image file")

class StoreImagesRequest(BaseModel):
    docsets: DocSetList = Field(..., description="List of DocSet objects containing papers with figure_chunks")
    indexing_status: Optional[Dict[str, Dict[str, bool]]] = Field(
        default=None, 
        description="Optional dictionary to track indexing status for each paper"
    )
    keep_temp_image: bool = Field(default=False, description="If False, delete temporary image files after successful storage (default: False)")

class StoreImagesResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    indexing_status: Optional[Dict[str, Dict[str, bool]]] = Field(
        default=None, 
        description="Updated indexing status for each paper"
    )
    papers_processed: int = Field(..., description="Number of papers processed")

class ImageResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    object_name: Optional[str] = Field(default=None, description="Object name used for storage/retrieval")
    image_data: Optional[bytes] = Field(default=None, description="Image data (only for get operations)")
    file_size: Optional[int] = Field(default=None, description="File size in bytes (only for get operations)")

class GetImageRequest(BaseModel):
    image_id: str = Field(..., description="Image ID to retrieve from MinIO storage")

class GetImageResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    image_data: Optional[str] = Field(default=None, description="Base64 encoded image data if found")
    image_id: Optional[str] = Field(default=None, description="Image ID that was requested")

class GetImageStorageStatusRequest(BaseModel):
    doc_id: str = Field(..., description="Document ID to get image storage status for")

class GetImageStorageStatusResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    storage_status: Optional[Dict[str, Any]] = Field(default=None, description="Image storage status for the document")
    doc_id: Optional[str] = Field(default=None, description="Document ID that was requested")


# --- Vector-related Models ---

class SaveVectorsRequest(BaseModel):
    docsets: DocSetList = Field(..., description="List of DocSet objects containing papers")
    indexing_status: Optional[Dict[str, Dict[str, bool]]] = Field(
        default=None, 
        description="Optional dictionary to track indexing status for each paper"
    )

class SaveVectorsResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    indexing_status: Optional[Dict[str, Dict[str, bool]]] = Field(
        default=None, 
        description="Updated indexing status for each paper"
    )
    papers_processed: int = Field(..., description="Number of papers processed")


# --- Document ID retrieval Models ---

class GetAllDocIdsResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    doc_ids: List[str] = Field(..., description="List of all document IDs")
    count: int = Field(..., description="Total number of document IDs")
    database_type: str = Field(..., description="Database type: 'metadata' or 'vector'")


# --- Vector Document Deletion Models ---

class DeleteVectorDocumentRequest(BaseModel):
    doc_id: str = Field(..., description="Document ID to delete from vector database")
    
    @validator('doc_id')
    def doc_id_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Document ID cannot be empty')
        return v.strip()

class DeleteVectorDocumentResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    doc_id: str = Field(..., description="Document ID that was deleted")
    vectors_deleted: bool = Field(..., description="Whether vectors were actually deleted")


# --- Blog Content Models ---

class GetPaperContentRequest(BaseModel):
    paper_id: str = Field(..., description="Paper ID (doc_id) to get blog content for")
    
    @validator('paper_id')
    def paper_id_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Paper ID cannot be empty')
        return v.strip()

class GetPaperContentResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    content: Optional[str] = Field(default=None, description="Processed blog content with fixed image URLs")
    paper_id: str = Field(..., description="Paper ID that was requested")