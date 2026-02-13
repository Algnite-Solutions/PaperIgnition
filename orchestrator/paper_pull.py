from AIgnite.data.docset import *
from AIgnite.data.htmlparser import ArxivHTMLExtractor
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional, Literal, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from storage_util import LocalStorageManager


class PaperPullService:
    """
    Service for pulling and extracting papers from arXiv

    Supports both HTML and PDF extraction methods (PDF is TODO)
    """

    def __init__(
        self,
        base_dir: Optional[str] = None,
        max_workers: int = 3,
        time_slots_count: int = 3,
        location: str = "Asia/Shanghai",
        count_delay: int = 1,
        max_papers: Optional[int] = None,
        storage_manager: Optional["LocalStorageManager"] = None
    ):
        """
        Initialize PaperPullService

        Args:
            base_dir: Base directory for storing papers (defaults to orchestrator dir)
            max_workers: Number of parallel workers for fetching
            time_slots_count: Number of time slots to divide the day into
            location: Timezone location for time calculations
            count_delay: Days to delay from current date
            max_papers: Maximum number of papers to fetch (None for unlimited)
            storage_manager: Optional LocalStorageManager instance for file operations
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.max_workers = max_workers
        self.time_slots_count = time_slots_count
        self.location = location
        self.count_delay = count_delay
        self.max_papers = max_papers
        self.storage_manager = storage_manager

        # Setup directories
        if base_dir is None:
            base_dir = os.path.dirname(__file__)
        self.base_dir = Path(base_dir)

        # If storage_manager is provided, use its paths; otherwise use defaults
        if storage_manager:
            self.html_text_folder = storage_manager.config.htmls_path
            self.pdf_folder_path = storage_manager.config.pdfs_path
            self.image_folder_path = storage_manager.config.imgs_path
            self.json_output_path = storage_manager.config.jsons_path
        else:
            self.html_text_folder = self.base_dir / "htmls"
            self.pdf_folder_path = self.base_dir / "pdfs"
            self.image_folder_path = self.base_dir / "imgs"
            self.json_output_path = self.base_dir / "jsons"
        
        self.arxiv_pool_path = self.base_dir / "html_url_storage" / "html_urls.txt"

        # Get credentials from environment
        self.volcengine_ak = os.getenv("VOLCENGINE_AK", "")
        self.volcengine_sk = os.getenv("VOLCENGINE_SK", "")

        # Initialize directories
        self._setup_directories()

    def _setup_directories(self):
        """Create necessary directories if they don't exist"""
        self.arxiv_pool_path.parent.mkdir(parents=True, exist_ok=True)
        self.arxiv_pool_path.touch(exist_ok=True)

        for path in [self.html_text_folder, self.pdf_folder_path,
                     self.image_folder_path, self.json_output_path]:
            path.mkdir(parents=True, exist_ok=True)

    def _get_time_str(self) -> str:
        """
        Get UTC time string for the fetch window

        Returns:
            Time string in format YYYYMMDDHHMM
        """
        local_tz = ZoneInfo(self.location)
        local_now = (datetime.now(local_tz) - timedelta(days=self.count_delay)).replace(
            second=0, microsecond=0
        )
        utc_now = local_now.astimezone(ZoneInfo("UTC"))
        return utc_now.strftime("%Y%m%d%H%M")

    def _divide_time_into_slots(self, time: str) -> List[str]:
        """
        Divide a 24-hour period into time slots

        Args:
            time: End time in format YYYYMMDDHHMM

        Returns:
            List of time slot boundaries
        """
        fmt = "%Y%m%d%H%M"
        end_time = datetime.strptime(time, fmt)
        start_time = end_time - timedelta(days=1)
        total_minutes = int((end_time - start_time).total_seconds() // 60)
        step = total_minutes / self.time_slots_count

        result = []
        for i in range(self.time_slots_count + 1):
            t = start_time + timedelta(minutes=round(i * step))
            result.append(t.strftime(fmt))
        return result

    def _run_html_with_pdf_fallback(self, start_str: str, end_str: str, max_papers_per_slot: Optional[int] = None) -> List[str]:
        """
        Run HTML extractor first, then use PDF parser for papers that failed HTML extraction

        This is the default and recommended approach:
        1. Try HTML extraction for all papers
        2. For papers that failed HTML extraction, use PDF parser as fallback

        Args:
            start_str: Start time string
            end_str: End time string
            max_papers_per_slot: Maximum papers to fetch in this time slot

        Returns:
            List of newly fetched paper IDs
        """
        extractor = ArxivHTMLExtractor(
            html_text_folder=str(self.html_text_folder),
            pdf_folder_path=str(self.pdf_folder_path),
            arxiv_pool=str(self.arxiv_pool_path),
            image_folder_path=str(self.image_folder_path),
            json_path=str(self.json_output_path),
            volcengine_ak=self.volcengine_ak,
            volcengine_sk=self.volcengine_sk,
            start_time=start_str,
            end_time=end_str,
            max_results=max_papers_per_slot
        )

        # Step 1: Extract HTML papers
        extractor.extract_all_htmls()

        # Step 2: Use PDF parser for remaining docs (fallback for failed HTML extraction)
        extractor.pdf_parser_helper.docs = extractor.docs
        extractor.pdf_parser_helper.remain_docparser()
        extractor.docs = extractor.pdf_parser_helper.docs

        # Collect newly fetched paper IDs
        newly_fetched_ids = [doc.doc_id for doc in extractor.docs]

        # Serialize all docs to JSON
        extractor.serialize_docs()

        return newly_fetched_ids

    def _run_extractor_for_timeslot(self, start_str: str, end_str: str, max_papers_per_slot: int) -> List[str]:
        """
        Run the appropriate extractor for a time slot

        By default (HTML type), uses HTML extraction with PDF fallback for failed papers

        Args:
            start_str: Start time string
            end_str: End time string

        Returns:
            List of newly fetched paper IDs
        """
        # Default: HTML first, PDF fallback for failures
        return self._run_html_with_pdf_fallback(start_str, end_str, max_papers_per_slot)

    def fetch_daily_papers(self, time: Optional[str] = None) -> List[DocSet]:
        """
        Fetch daily papers from arXiv

        Args:
            time: End time for fetch window (defaults to current time)

        Returns:
            List of newly fetched DocSet objects
        """
        if time is None:
            time = self._get_time_str()

        self.logger.info(f"Fetching papers for {time}")
        if self.max_papers:
            self.logger.info(f"Max papers limit: {self.max_papers}")

        time_slots = self._divide_time_into_slots(time)
        num_slots = len(time_slots) - 1

        # Calculate max papers per slot if max_papers is set
        max_papers_per_slot = None
        if self.max_papers:
            max_papers_per_slot = self.max_papers // num_slots
            if self.max_papers % num_slots != 0:
                max_papers_per_slot += 1  # Round up to cover all papers
            self.logger.info(f"Max papers per time slot: {max_papers_per_slot} (across {num_slots} slots)")

        # Fetch papers in parallel using thread pool
        newly_fetched_ids = set()
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for i in range(num_slots):
                start_str = time_slots[i]
                end_str = time_slots[i + 1]
                futures.append(
                    executor.submit(self._run_extractor_for_timeslot, start_str, end_str, max_papers_per_slot)
                )

            for f in futures:
                result = f.result()
                if result:
                    newly_fetched_ids.update(result)

        self.logger.info(f"📊 Newly fetched paper IDs: {len(newly_fetched_ids)}")

        # Load newly fetched papers from JSON
        new_docs = []
        
        if self.storage_manager:
            # Use storage_manager for loading papers
            for doc_id in newly_fetched_ids:
                docset = self.storage_manager.load_paper_docset(doc_id)
                if docset:
                    new_docs.append(docset)
                    self.logger.info(f"✅ Loaded: {docset.doc_id} - {docset.title}")
        else:
            # Fallback to direct file reading (legacy behavior)
            for json_file in self.json_output_path.glob("*.json"):
                file_name = json_file.stem
                if file_name in newly_fetched_ids:
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            docset = DocSet(**data)
                            new_docs.append(docset)
                            self.logger.info(f"✅ Loaded: {docset.doc_id} - {docset.title}")
                    except Exception as e:
                        self.logger.error(f"Failed to parse {json_file.name}: {e}")

        self.logger.info(f"📊 Total newly fetched papers: {len(new_docs)}")
        return new_docs