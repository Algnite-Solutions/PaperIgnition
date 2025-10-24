"""
API Client Layer for PaperIgnition Orchestrator

Provides robust HTTP clients with retry logic, timeout handling, and consistent error handling.
"""

import httpx
import logging
from typing import Dict, Any, List, Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from AIgnite.data.docset import DocSetList, DocSet


class APIClientError(Exception):
    """Base exception for API client errors"""
    pass


class APIConnectionError(APIClientError):
    """Raised when unable to connect to API"""
    pass


class APIResponseError(APIClientError):
    """Raised when API returns an error response"""
    pass


class BaseAPIClient:
    """Base API client with common functionality"""

    def __init__(self, base_url: str, timeout: float = 30.0, max_retries: int = 3):
        """
        Initialize base API client

        Args:
            base_url: Base URL for the API
            timeout: Default timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(self.__class__.__name__)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True
    )
    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: Optional[float] = None
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            json_data: JSON data for request body
            params: Query parameters
            timeout: Request timeout (uses default if None)

        Returns:
            httpx.Response object

        Raises:
            APIConnectionError: If connection fails after retries
            APIResponseError: If API returns error status
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        timeout_value = timeout or self.timeout

        try:
            self.logger.debug(f"Making {method} request to {url}")
            response = httpx.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                timeout=timeout_value
            )
            response.raise_for_status()
            return response

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            self.logger.error(f"Connection error to {url}: {e}")
            raise APIConnectionError(f"Failed to connect to {url}: {str(e)}") from e

        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error from {url}: {e.response.status_code} - {e.response.text}")
            raise APIResponseError(
                f"API error ({e.response.status_code}): {e.response.text}"
            ) from e

        except Exception as e:
            self.logger.error(f"Unexpected error calling {url}: {e}")
            raise APIClientError(f"Unexpected error: {str(e)}") from e

    def get(self, endpoint: str, params: Optional[Dict] = None, timeout: Optional[float] = None) -> Dict:
        """Make GET request and return JSON response"""
        response = self._make_request("GET", endpoint, params=params, timeout=timeout)
        return response.json()

    def post(self, endpoint: str, json_data: Dict, params: Optional[Dict] = None, timeout: Optional[float] = None) -> Dict:
        """Make POST request and return JSON response"""
        response = self._make_request("POST", endpoint, json_data=json_data, params=params, timeout=timeout)
        return response.json()


class IndexAPIClient(BaseAPIClient):
    """Client for Index Service API"""

    def __init__(self, base_url: str, timeout: float = 30.0):
        super().__init__(base_url, timeout)

    def health_check(self) -> Dict[str, Any]:
        """
        Check health status of index service

        Returns:
            Dict with health status information

        Raises:
            APIClientError: If health check fails
        """
        try:
            response = self.get("/health", timeout=5.0)
            self.logger.info(f"Health check: {response}")
            return response
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            raise

    def is_healthy(self) -> bool:
        """
        Check if service is healthy and ready

        Returns:
            True if service is healthy and indexer is ready
        """
        try:
            health = self.health_check()
            return health.get("status") == "healthy" and health.get("indexer_ready", False)
        except Exception:
            return False

    def index_papers(self, papers: List[DocSet], store_images: bool = False, timeout: float = 3000.0) -> Dict:
        """
        Index papers in the index service

        Args:
            papers: List of DocSet objects to index
            store_images: Whether to store images
            timeout: Request timeout in seconds

        Returns:
            Response from index service

        Raises:
            APIClientError: If indexing fails
        """
        if not papers:
            self.logger.warning("No papers to index")
            return {"status": "skipped", "count": 0}

        docset_list = DocSetList(docsets=papers)
        data = {
            "docsets": docset_list.model_dump(),
            "store_images": store_images
        }

        self.logger.info(f"📤 Indexing {len(papers)} papers...")
        if papers:
            self.logger.info(f"📋 First paper: {papers[0].doc_id} - {papers[0].title[:50]}...")

        try:
            response = self.post("/index_papers/", json_data=data, timeout=timeout)
            self.logger.info(f"✅ Indexing complete: {response}")
            return response
        except Exception as e:
            self.logger.error(f"❌ Failed to index papers: {e}")
            raise

    def find_similar(
        self,
        query: str,
        top_k: int = 10,
        similarity_cutoff: float = 0.1,
        search_strategy: str = 'vector',
        filters: Optional[Dict] = None,
        result_types: Optional[List[str]] = None,
        timeout: float = 10.0
    ) -> List[DocSet]:
        """
        Find similar papers using the index service

        Args:
            query: Search query
            top_k: Number of results to return
            similarity_cutoff: Minimum similarity score threshold
            search_strategy: Search strategy ('vector', 'tf-idf', 'bm25')
            filters: Optional filters (e.g., exclude doc_ids)
            result_types: Types of data to include in results
            timeout: Request timeout in seconds

        Returns:
            List of DocSet objects matching the query

        Raises:
            APIClientError: If search fails
        """
        if result_types is None:
            result_types = ["metadata"]

        payload = {
            "query": query,
            "top_k": top_k,
            "similarity_cutoff": similarity_cutoff,
            "search_strategies": [(search_strategy, 1.5)],
            "filters": filters,
            "result_include_types": result_types
        }

        try:
            self.logger.info(f"🔍 Searching for: '{query}' (strategy: {search_strategy}, cutoff: {similarity_cutoff})")
            results = self.post("/find_similar/", json_data=payload, timeout=timeout)

            docsets = []
            for r in results:
                try:
                    metadata = r.get('metadata', {})

                    # 处理chunks数据，确保符合DocSet定义
                    def process_text_chunks(chunks_data):
                        """处理text_chunks数据，转换为符合DocSet定义的格式"""
                        if not chunks_data:
                            return []
                        
                        processed_chunks = []
                        for chunk in chunks_data:
                            if isinstance(chunk, dict):
                                # 检查是否已经是正确的格式
                                if 'id' in chunk and 'type' in chunk and 'text' in chunk:
                                    processed_chunks.append(chunk)
                                elif 'chunk_id' in chunk and 'text_content' in chunk:
                                    # 转换API格式到DocSet格式
                                    converted_chunk = {
                                        'id': chunk['chunk_id'],
                                        'type': 'text',
                                        'text': chunk['text_content']
                                    }
                                    processed_chunks.append(converted_chunk)
                                else:
                                    # 跳过无效的chunk
                                    print(f"Warning: Skipping invalid text chunk: {chunk}")
                            else:
                                print(f"Warning: Skipping non-dict text chunk: {chunk}")
                        return processed_chunks
                
                    docset_data = {
                        'doc_id': metadata.get('doc_id'),
                        'title': metadata.get('title', 'Unknown Title'),
                        'authors': metadata.get('authors', []),
                        'categories': metadata.get('categories', []),
                        'published_date': metadata.get('published_date', ''),
                        'abstract': metadata.get('abstract', ''),
                        'pdf_path': metadata.get('pdf_path', ''),
                        'HTML_path': metadata.get('HTML_path'),
                        'text_chunks': process_text_chunks(r.get('text_chunks', [])),
                        'figure_chunks': [],
                        'table_chunks': [],
                        'metadata': metadata,
                        'comments': metadata.get('comments', '')
                    }
                    docsets.append(DocSet(**docset_data))
                except Exception as e:
                    self.logger.warning(f"Failed to create DocSet for {r.get('doc_id')}: {e}")
                    continue

            self.logger.info(f"✅ Found {len(docsets)} papers")
            return docsets

        except Exception as e:
            self.logger.error(f"❌ Search failed for query '{query}': {e}")
            raise

    def update_papers_blog(
        self,
        papers_data: List[Dict[str, str]],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Update blog field in papers table for multiple papers

        Args:
            papers_data: List of dicts with 'paper_id' and 'blog_content' keys
            timeout: Request timeout in seconds

        Returns:
            Response from index service

        Raises:
            APIClientError: If update fails
        """
        if not papers_data:
            self.logger.warning("No papers to update")
            return {"status": "skipped", "updated": 0}

        request_data = {"papers": papers_data}

        self.logger.info(f"📤 Updating blog field for {len(papers_data)} papers...")

        try:
            response = self._make_request(
                method="PUT",
                endpoint="/update_papers_blog/",
                json_data=request_data,
                timeout=timeout
            )
            result = response.json()
            self.logger.info(f"✅ Blog update complete: {result}")
            return result
        except Exception as e:
            self.logger.error(f"❌ Failed to update papers blog: {e}")
            raise


class BackendAPIClient(BaseAPIClient):
    """Client for Backend App Service API"""

    def __init__(self, base_url: str, timeout: float = 30.0):
        super().__init__(base_url, timeout)

    def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Get all users from backend

        Returns:
            List of user dictionaries with username and interests

        Raises:
            APIClientError: If request fails
        """
        try:
            self.logger.info("Fetching all users...")
            users = self.get("/api/users/all", timeout=100.0)
            self.logger.info(f"✅ Retrieved {len(users)} users")
            return users
        except Exception as e:
            self.logger.error(f"❌ Failed to fetch users: {e}")
            raise

    def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """
        Get user information by email

        Args:
            email: User email address

        Returns:
            User information dictionary

        Raises:
            APIClientError: If user not found or request fails
        """
        try:
            self.logger.debug(f"Fetching user: {email}")
            user = self.get(f"/api/users/by_email/{email}")
            return user
        except Exception as e:
            self.logger.error(f"❌ Failed to fetch user {email}: {e}")
            raise

    def get_user_interests(self, email: str) -> List[str]:
        """
        Get user's research interests

        Args:
            email: User email address

        Returns:
            List of interest keywords
        """
        try:
            user = self.get_user_by_email(email)
            interests = user.get("interests_description", [])
            self.logger.debug(f"User {email} interests: {interests}")
            return interests
        except Exception as e:
            self.logger.warning(f"Failed to get interests for {email}: {e}")
            return []

    def get_user_papers(self, username: str) -> List[Dict[str, Any]]:
        """
        Get papers recommended to a user

        Args:
            username: User's username/email

        Returns:
            List of paper dictionaries
        """
        try:
            self.logger.debug(f"Fetching papers for user: {username}")
            papers = self.get(f"/api/papers/recommendations/{username}")
            self.logger.info(f"✅ User {username} has {len(papers)} papers")
            return papers
        except APIResponseError as e:
            if "404" in str(e):
                self.logger.debug(f"No papers found for {username}")
                return []
            raise
        except Exception as e:
            self.logger.error(f"❌ Failed to fetch papers for {username}: {e}")
            return []

    def get_existing_paper_ids(self, username: str) -> List[str]:
        """
        Get list of paper IDs already recommended to user

        Args:
            username: User's username/email

        Returns:
            List of paper IDs
        """
        papers = self.get_user_papers(username)
        paper_ids = [p["id"] for p in papers if p.get("id")]
        self.logger.debug(f"User {username} has {len(paper_ids)} existing papers")
        return paper_ids

    def recommend_paper(
        self,
        username: str,
        paper_id: str,
        title: str,
        authors: str = "",
        abstract: str = "",
        url: str = "",
        content: str = "",
        blog: Optional[str] = None,
        blog_abs: Optional[str] = None,
        blog_title: Optional[str] = None,
        recommendation_reason: str = "",
        relevance_score: Optional[float] = None,
        submitted: Optional[str] = None,
        timeout: float = 100.0
    ) -> bool:
        """
        Recommend a paper to a user

        Args:
            username: User's username/email
            paper_id: Paper identifier
            title: Paper title
            authors: Paper authors (comma-separated)
            abstract: Paper abstract
            url: Paper URL
            content: Paper content
            blog: Generated blog digest
            blog_abs: Blog abstract
            blog_title: Blog title
            recommendation_reason: Reason for recommendation
            relevance_score: Relevance score
            timeout: Request timeout

        Returns:
            True if successful, False otherwise
        """
        # Truncate fields to fit database constraints (VARCHAR(255))
        def truncate(s, max_len=255):
            return s[:max_len] if s else ""

        data = {
            "username": username,
            "paper_id": paper_id,
            "title": truncate(title, 255),
            "authors": truncate(authors, 255),
            "abstract": abstract,  # Text field, no limit
            "url": truncate(url, 255),
            "content": content,  # Text field, no limit
            "blog": blog or "",  # Text field, no limit
            "blog_abs": blog_abs or "",  # Text field, no limit
            "blog_title": blog_title or "",  # Text field, no limit
            "recommendation_reason": recommendation_reason,  # Text field, no limit
            "relevance_score": relevance_score,
            "submitted": submitted or ""
        }

        try:
            self.logger.debug(f"Recommending paper {paper_id} to {username}")
            response = self.post(
                "/api/papers/recommend",
                params={"username": username},
                json_data=data,
                timeout=timeout
            )
            self.logger.info(f"✅ Paper {paper_id} recommended to {username} ")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to recommend paper {paper_id} to {username}: {e}")
            return False

    def recommend_papers_batch(self, username: str, papers: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Recommend multiple papers to a user

        Args:
            username: User's username/email
            papers: List of paper dictionaries

        Returns:
            Tuple of (successful_count, failed_count)
        """
        success_count = 0
        failed_count = 0

        self.logger.info(f"Recommending {len(papers)} papers to {username}...")

        for paper in papers:
            success = self.recommend_paper(
                username=username,
                paper_id=paper.get("paper_id"),
                title=paper.get("title", ""),
                authors=paper.get("authors", ""),
                abstract=paper.get("abstract", ""),
                url=paper.get("url", ""),
                content=paper.get("content", ""),
                blog=paper.get("blog"),
                blog_abs=paper.get("blog_abs"),
                blog_title=paper.get("blog_title"),
                recommendation_reason=paper.get("recommendation_reason", ""),
                relevance_score=paper.get("relevance_score"),
                submitted=paper.get("submitted", ""),
            )

            if success:
                success_count += 1
            else:
                failed_count += 1

        self.logger.info(f"📊 Batch complete: {success_count} succeeded, {failed_count} failed")
        return success_count, failed_count
