from AIgnite.data.docset import *
from AIgnite.data.htmlparser import *
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional, Literal
from enum import Enum


class ExtractorType(Enum):
    """Enum for extractor types"""
    HTML = "html"
    PDF = "pdf"


class PaperPullService:
    """
    Service for pulling and extracting papers from arXiv

    Supports both HTML and PDF extraction methods (PDF is TODO)
    """

    def __init__(
        self,
        base_dir: Optional[str] = None,
        extractor_type: ExtractorType = ExtractorType.HTML,
        max_workers: int = 3,
        time_slots_count: int = 3,
        location: str = "Asia/Shanghai",
        count_delay: int = 1
    ):
        """
        Initialize PaperPullService

        Args:
            base_dir: Base directory for storing papers (defaults to orchestrator dir)
            extractor_type: Type of extractor to use (HTML or PDF)
            max_workers: Number of parallel workers for fetching
            time_slots_count: Number of time slots to divide the day into
            location: Timezone location for time calculations
            count_delay: Days to delay from current date
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.extractor_type = extractor_type
        self.max_workers = max_workers
        self.time_slots_count = time_slots_count
        self.location = location
        self.count_delay = count_delay

        # Setup directories
        if base_dir is None:
            base_dir = os.path.dirname(__file__)
        self.base_dir = Path(base_dir)

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

    def _run_html_extractor(self, start_str: str, end_str: str) -> List[str]:
        """
        Run HTML extractor for a time slot

        Args:
            start_str: Start time string
            end_str: End time string

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
            end_time=end_str
        )

        extractor.extract_all_htmls()
        newly_fetched_ids = [doc.doc_id for doc in extractor.docs]
        extractor.serialize_docs()

        return newly_fetched_ids

    def _run_pdf_extractor(self, start_str: str, end_str: str) -> List[str]:
        """
        Run PDF extractor for a time slot

        TODO: Implement PDF extraction as a separate extractor

        Args:
            start_str: Start time string
            end_str: End time string

        Returns:
            List of newly fetched paper IDs
        """
        # TODO: Implement PDF extractor
        # For now, fall back to HTML extractor
        self.logger.warning("PDF extractor not yet implemented, using HTML extractor")
        return self._run_html_extractor(start_str, end_str)

    def _run_extractor_for_timeslot(self, start_str: str, end_str: str) -> List[str]:
        """
        Run the appropriate extractor for a time slot

        Args:
            start_str: Start time string
            end_str: End time string

        Returns:
            List of newly fetched paper IDs
        """
        if self.extractor_type == ExtractorType.HTML:
            return self._run_html_extractor(start_str, end_str)
        elif self.extractor_type == ExtractorType.PDF:
            return self._run_pdf_extractor(start_str, end_str)
        else:
            raise ValueError(f"Unknown extractor type: {self.extractor_type}")

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

        self.logger.info(f"Fetching papers for {time} using {self.extractor_type.value} extractor")

        time_slots = self._divide_time_into_slots(time)

        # Fetch papers in parallel using thread pool
        newly_fetched_ids = set()
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for i in range(len(time_slots) - 1):
                start_str = time_slots[i]
                end_str = time_slots[i + 1]
                futures.append(
                    executor.submit(self._run_extractor_for_timeslot, start_str, end_str)
                )

            for f in futures:
                result = f.result()
                if result:
                    newly_fetched_ids.update(result)

        self.logger.info(f"📊 Newly fetched paper IDs: {len(newly_fetched_ids)}")

        # Load newly fetched papers from JSON
        new_docs = []
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