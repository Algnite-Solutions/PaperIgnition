"""
Storage Manager Module for PaperIgnition

Provides abstract base class and implementations for managing storage of:
- Blog files (.md)
- Paper JSON files (.json)
- HTML files
- PDF files
- Image files

This module allows flexible storage backends (local, cloud, etc.)
"""

import os
import json
import shutil
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field

# Avoid circular imports by importing DocSet only when needed
# from AIgnite.data.docset import DocSet


@dataclass
class StorageConfig:
    """Configuration for storage paths"""
    base_dir: str
    blogs_dir: str = "blogs"
    jsons_dir: str = "jsons"
    htmls_dir: str = "htmls"
    pdfs_dir: str = "pdfs"
    imgs_dir: str = "imgs"
    
    # Cleanup options
    keep_blogs: bool = True
    keep_jsons: bool = True
    keep_htmls: bool = True
    keep_pdfs: bool = True
    keep_imgs: bool = True
    
    def __post_init__(self):
        """Convert relative paths to absolute paths based on base_dir"""
        self.blogs_path = self._resolve_path(self.blogs_dir)
        self.jsons_path = self._resolve_path(self.jsons_dir)
        self.htmls_path = self._resolve_path(self.htmls_dir)
        self.pdfs_path = self._resolve_path(self.pdfs_dir)
        self.imgs_path = self._resolve_path(self.imgs_dir)
    
    def _resolve_path(self, dir_name: str) -> Path:
        """Resolve directory path"""
        if os.path.isabs(dir_name):
            return Path(dir_name)
        return Path(self.base_dir) / dir_name


class StorageManager(ABC):
    """
    Abstract base class for storage management.
    
    Defines the interface for CRUD operations on different data types:
    - Blogs
    - Papers (JSON)
    - HTML files
    - PDF files
    - Images
    """
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    # ==================== Blog Operations ====================
    
    @abstractmethod
    def save_blog(self, doc_id: str, content: str) -> bool:
        """Save blog content for a paper"""
        pass
    
    @abstractmethod
    def read_blog(self, doc_id: str) -> Optional[str]:
        """Read blog content for a paper"""
        pass
    
    @abstractmethod
    def delete_blog(self, doc_id: str) -> bool:
        """Delete blog file for a paper"""
        pass
    
    @abstractmethod
    def blog_exists(self, doc_id: str) -> bool:
        """Check if blog exists for a paper"""
        pass
    
    @abstractmethod
    def list_blogs(self) -> List[str]:
        """List all blog doc_ids"""
        pass
    
    # ==================== Paper JSON Operations ====================
    
    @abstractmethod
    def save_paper_json(self, doc_id: str, data: Dict[str, Any]) -> bool:
        """Save paper data as JSON"""
        pass
    
    @abstractmethod
    def read_paper_json(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Read paper data from JSON"""
        pass
    
    @abstractmethod
    def delete_paper_json(self, doc_id: str) -> bool:
        """Delete paper JSON file"""
        pass
    
    @abstractmethod
    def paper_json_exists(self, doc_id: str) -> bool:
        """Check if paper JSON exists"""
        pass
    
    @abstractmethod
    def list_paper_jsons(self) -> List[str]:
        """List all paper JSON doc_ids"""
        pass
    
    # ==================== HTML Operations ====================
    
    @abstractmethod
    def save_html(self, doc_id: str, content: str) -> bool:
        """Save HTML content for a paper"""
        pass
    
    @abstractmethod
    def read_html(self, doc_id: str) -> Optional[str]:
        """Read HTML content for a paper"""
        pass
    
    @abstractmethod
    def delete_html(self, doc_id: str) -> bool:
        """Delete HTML file for a paper"""
        pass
    
    @abstractmethod
    def html_exists(self, doc_id: str) -> bool:
        """Check if HTML exists for a paper"""
        pass
    
    # ==================== PDF Operations ====================
    
    @abstractmethod
    def save_pdf(self, doc_id: str, content: bytes) -> bool:
        """Save PDF content for a paper"""
        pass
    
    @abstractmethod
    def read_pdf(self, doc_id: str) -> Optional[bytes]:
        """Read PDF content for a paper"""
        pass
    
    @abstractmethod
    def delete_pdf(self, doc_id: str) -> bool:
        """Delete PDF file for a paper"""
        pass
    
    @abstractmethod
    def pdf_exists(self, doc_id: str) -> bool:
        """Check if PDF exists for a paper"""
        pass
    
    @abstractmethod
    def get_pdf_path(self, doc_id: str) -> Optional[str]:
        """Get the path to PDF file (for external tools that need file path)"""
        pass
    
    # ==================== Image Operations ====================
    
    @abstractmethod
    def save_image(self, doc_id: str, image_id: str, content: bytes) -> bool:
        """Save image content"""
        pass
    
    @abstractmethod
    def read_image(self, doc_id: str, image_id: str) -> Optional[bytes]:
        """Read image content"""
        pass
    
    @abstractmethod
    def delete_image(self, doc_id: str, image_id: str) -> bool:
        """Delete image file"""
        pass
    
    @abstractmethod
    def image_exists(self, doc_id: str, image_id: str) -> bool:
        """Check if image exists"""
        pass
    
    @abstractmethod
    def list_images(self, doc_id: str) -> List[str]:
        """List all image IDs for a paper"""
        pass
    
    @abstractmethod
    def get_image_path(self, doc_id: str, image_id: str) -> Optional[str]:
        """Get the path to image file"""
        pass
    
    # ==================== Bulk Operations ====================
    
    @abstractmethod
    def cleanup_paper_files(self, doc_id: str, 
                           delete_blog: bool = False,
                           delete_json: bool = False,
                           delete_html: bool = False,
                           delete_pdf: bool = False,
                           delete_images: bool = False) -> Dict[str, bool]:
        """
        Clean up files for a specific paper based on flags.
        
        Returns:
            Dict with status for each file type
        """
        pass
    
    @abstractmethod
    def cleanup_all(self,
                   delete_blogs: bool = False,
                   delete_jsons: bool = False,
                   delete_htmls: bool = False,
                   delete_pdfs: bool = False,
                   delete_images: bool = False) -> Dict[str, int]:
        """
        Clean up all files based on flags.
        
        Returns:
            Dict with count of deleted files for each type
        """
        pass


class LocalStorageManager(StorageManager):
    """
    Local filesystem implementation of StorageManager.
    
    Stores files in local directories:
    - blogs/: .md files
    - jsons/: .json files
    - htmls/: .html files
    - pdfs/: .pdf files
    - imgs/: image files (organized by doc_id)
    """
    
    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        for path in [self.config.blogs_path, self.config.jsons_path,
                     self.config.htmls_path, self.config.pdfs_path,
                     self.config.imgs_path]:
            path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {path}")
    
    # ==================== Blog Operations ====================
    
    def save_blog(self, doc_id: str, content: str) -> bool:
        """Save blog content as .md file"""
        try:
            file_path = self.config.blogs_path / f"{doc_id}.md"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.debug(f"Saved blog: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save blog {doc_id}: {e}")
            return False
    
    def read_blog(self, doc_id: str) -> Optional[str]:
        """Read blog content from .md file"""
        try:
            file_path = self.config.blogs_path / f"{doc_id}.md"
            if not file_path.exists():
                self.logger.debug(f"Blog not found: {file_path}")
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to read blog {doc_id}: {e}")
            return None
    
    def delete_blog(self, doc_id: str) -> bool:
        """Delete blog .md file"""
        try:
            file_path = self.config.blogs_path / f"{doc_id}.md"
            if file_path.exists():
                file_path.unlink()
                self.logger.debug(f"Deleted blog: {file_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete blog {doc_id}: {e}")
            return False
    
    def blog_exists(self, doc_id: str) -> bool:
        """Check if blog .md file exists"""
        return (self.config.blogs_path / f"{doc_id}.md").exists()
    
    def list_blogs(self) -> List[str]:
        """List all blog doc_ids"""
        return [f.stem for f in self.config.blogs_path.glob("*.md")]
    
    # ==================== Paper JSON Operations ====================
    
    def save_paper_json(self, doc_id: str, data: Dict[str, Any]) -> bool:
        """Save paper data as JSON file"""
        try:
            file_path = self.config.jsons_path / f"{doc_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"Saved paper JSON: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save paper JSON {doc_id}: {e}")
            return False
    
    def read_paper_json(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Read paper data from JSON file"""
        try:
            file_path = self.config.jsons_path / f"{doc_id}.json"
            if not file_path.exists():
                self.logger.debug(f"Paper JSON not found: {file_path}")
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read paper JSON {doc_id}: {e}")
            return None
    
    def delete_paper_json(self, doc_id: str) -> bool:
        """Delete paper JSON file"""
        try:
            file_path = self.config.jsons_path / f"{doc_id}.json"
            if file_path.exists():
                file_path.unlink()
                self.logger.debug(f"Deleted paper JSON: {file_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete paper JSON {doc_id}: {e}")
            return False
    
    def paper_json_exists(self, doc_id: str) -> bool:
        """Check if paper JSON file exists"""
        return (self.config.jsons_path / f"{doc_id}.json").exists()
    
    def list_paper_jsons(self) -> List[str]:
        """List all paper JSON doc_ids"""
        return [f.stem for f in self.config.jsons_path.glob("*.json")]
    
    def load_paper_docset(self, doc_id: str):
        """
        Load paper JSON and convert to DocSet object.
        
        Returns:
            DocSet object or None if not found/error
        """
        from AIgnite.data.docset import DocSet
        
        data = self.read_paper_json(doc_id)
        if data is None:
            return None
        try:
            return DocSet(**data)
        except Exception as e:
            self.logger.error(f"Failed to create DocSet from {doc_id}: {e}")
            return None
    
    def load_all_paper_docsets(self, doc_ids: Optional[List[str]] = None) -> List:
        """
        Load multiple papers as DocSet objects.
        
        Args:
            doc_ids: Optional list of doc_ids to load. If None, loads all.
            
        Returns:
            List of DocSet objects
        """
        from AIgnite.data.docset import DocSet
        
        if doc_ids is None:
            doc_ids = self.list_paper_jsons()
        
        docsets = []
        for doc_id in doc_ids:
            docset = self.load_paper_docset(doc_id)
            if docset is not None:
                docsets.append(docset)
        
        return docsets
    
    # ==================== HTML Operations ====================
    
    def save_html(self, doc_id: str, content: str) -> bool:
        """Save HTML content"""
        try:
            file_path = self.config.htmls_path / f"{doc_id}.html"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.debug(f"Saved HTML: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save HTML {doc_id}: {e}")
            return False
    
    def read_html(self, doc_id: str) -> Optional[str]:
        """Read HTML content"""
        try:
            file_path = self.config.htmls_path / f"{doc_id}.html"
            if not file_path.exists():
                self.logger.debug(f"HTML not found: {file_path}")
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to read HTML {doc_id}: {e}")
            return None
    
    def delete_html(self, doc_id: str) -> bool:
        """Delete HTML file"""
        try:
            file_path = self.config.htmls_path / f"{doc_id}.html"
            if file_path.exists():
                file_path.unlink()
                self.logger.debug(f"Deleted HTML: {file_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete HTML {doc_id}: {e}")
            return False
    
    def html_exists(self, doc_id: str) -> bool:
        """Check if HTML file exists"""
        return (self.config.htmls_path / f"{doc_id}.html").exists()
    
    # ==================== PDF Operations ====================
    
    def save_pdf(self, doc_id: str, content: bytes) -> bool:
        """Save PDF content"""
        try:
            file_path = self.config.pdfs_path / f"{doc_id}.pdf"
            with open(file_path, 'wb') as f:
                f.write(content)
            self.logger.debug(f"Saved PDF: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save PDF {doc_id}: {e}")
            return False
    
    def read_pdf(self, doc_id: str) -> Optional[bytes]:
        """Read PDF content"""
        try:
            file_path = self.config.pdfs_path / f"{doc_id}.pdf"
            if not file_path.exists():
                self.logger.debug(f"PDF not found: {file_path}")
                return None
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to read PDF {doc_id}: {e}")
            return None
    
    def delete_pdf(self, doc_id: str) -> bool:
        """Delete PDF file"""
        try:
            file_path = self.config.pdfs_path / f"{doc_id}.pdf"
            if file_path.exists():
                file_path.unlink()
                self.logger.debug(f"Deleted PDF: {file_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete PDF {doc_id}: {e}")
            return False
    
    def pdf_exists(self, doc_id: str) -> bool:
        """Check if PDF file exists"""
        return (self.config.pdfs_path / f"{doc_id}.pdf").exists()
    
    def get_pdf_path(self, doc_id: str) -> Optional[str]:
        """Get the absolute path to PDF file"""
        file_path = self.config.pdfs_path / f"{doc_id}.pdf"
        if file_path.exists():
            return str(file_path.absolute())
        return None
    
    # ==================== Image Operations ====================
    
    def _get_image_dir(self, doc_id: str) -> Path:
        """Get the image directory for a paper (organized by doc_id)"""
        return self.config.imgs_path / doc_id
    
    def save_image(self, doc_id: str, image_id: str, content: bytes) -> bool:
        """Save image content"""
        try:
            img_dir = self._get_image_dir(doc_id)
            img_dir.mkdir(parents=True, exist_ok=True)
            file_path = img_dir / image_id
            with open(file_path, 'wb') as f:
                f.write(content)
            self.logger.debug(f"Saved image: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save image {doc_id}/{image_id}: {e}")
            return False
    
    def read_image(self, doc_id: str, image_id: str) -> Optional[bytes]:
        """Read image content"""
        try:
            file_path = self._get_image_dir(doc_id) / image_id
            if not file_path.exists():
                # Also check flat structure (legacy)
                file_path = self.config.imgs_path / image_id
                if not file_path.exists():
                    self.logger.debug(f"Image not found: {doc_id}/{image_id}")
                    return None
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to read image {doc_id}/{image_id}: {e}")
            return None
    
    def delete_image(self, doc_id: str, image_id: str) -> bool:
        """Delete image file"""
        try:
            file_path = self._get_image_dir(doc_id) / image_id
            if file_path.exists():
                file_path.unlink()
                self.logger.debug(f"Deleted image: {file_path}")
                return True
            # Also check flat structure (legacy)
            file_path = self.config.imgs_path / image_id
            if file_path.exists():
                file_path.unlink()
                self.logger.debug(f"Deleted image (flat): {file_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete image {doc_id}/{image_id}: {e}")
            return False
    
    def image_exists(self, doc_id: str, image_id: str) -> bool:
        """Check if image file exists"""
        # Check hierarchical structure first
        if (self._get_image_dir(doc_id) / image_id).exists():
            return True
        # Also check flat structure (legacy)
        return (self.config.imgs_path / image_id).exists()
    
    def list_images(self, doc_id: str) -> List[str]:
        """List all image IDs for a paper"""
        img_dir = self._get_image_dir(doc_id)
        if img_dir.exists():
            return [f.name for f in img_dir.iterdir() if f.is_file()]
        return []
    
    def get_image_path(self, doc_id: str, image_id: str) -> Optional[str]:
        """Get the absolute path to image file"""
        # Check hierarchical structure first
        file_path = self._get_image_dir(doc_id) / image_id
        if file_path.exists():
            return str(file_path.absolute())
        # Also check flat structure (legacy)
        file_path = self.config.imgs_path / image_id
        if file_path.exists():
            return str(file_path.absolute())
        return None
    
    def delete_all_images(self, doc_id: str) -> int:
        """Delete all images for a paper"""
        count = 0
        img_dir = self._get_image_dir(doc_id)
        if img_dir.exists():
            for f in img_dir.iterdir():
                if f.is_file():
                    f.unlink()
                    count += 1
            # Remove empty directory
            try:
                img_dir.rmdir()
            except OSError:
                pass
        return count
    
    # ==================== Bulk Operations ====================
    
    def cleanup_paper_files(self, doc_id: str,
                           delete_blog: bool = False,
                           delete_json: bool = False,
                           delete_html: bool = False,
                           delete_pdf: bool = False,
                           delete_images: bool = False) -> Dict[str, bool]:
        """
        Clean up files for a specific paper based on flags.
        
        Args:
            doc_id: Paper document ID
            delete_blog: Whether to delete blog file
            delete_json: Whether to delete JSON file
            delete_html: Whether to delete HTML file
            delete_pdf: Whether to delete PDF file
            delete_images: Whether to delete image files
            
        Returns:
            Dict with deletion status for each file type
        """
        results = {}
        
        if delete_blog:
            results['blog'] = self.delete_blog(doc_id)
        if delete_json:
            results['json'] = self.delete_paper_json(doc_id)
        if delete_html:
            results['html'] = self.delete_html(doc_id)
        if delete_pdf:
            results['pdf'] = self.delete_pdf(doc_id)
        if delete_images:
            count = self.delete_all_images(doc_id)
            results['images'] = count > 0
            results['images_count'] = count
        
        self.logger.info(f"Cleaned up files for {doc_id}: {results}")
        return results
    
    def cleanup_all(self,
                   delete_blogs: bool = False,
                   delete_jsons: bool = False,
                   delete_htmls: bool = False,
                   delete_pdfs: bool = False,
                   delete_images: bool = False) -> Dict[str, int]:
        """
        Clean up all files based on flags.
        
        Args:
            delete_blogs: Whether to delete all blog files
            delete_jsons: Whether to delete all JSON files
            delete_htmls: Whether to delete all HTML files
            delete_pdfs: Whether to delete all PDF files
            delete_images: Whether to delete all image files
            
        Returns:
            Dict with count of deleted files for each type
        """
        results = {
            'blogs': 0,
            'jsons': 0,
            'htmls': 0,
            'pdfs': 0,
            'images': 0
        }
        
        if delete_blogs:
            for f in self.config.blogs_path.glob("*.md"):
                f.unlink()
                results['blogs'] += 1
        
        if delete_jsons:
            for f in self.config.jsons_path.glob("*.json"):
                f.unlink()
                results['jsons'] += 1
        
        if delete_htmls:
            for f in self.config.htmls_path.glob("*.html"):
                f.unlink()
                results['htmls'] += 1
        
        if delete_pdfs:
            for f in self.config.pdfs_path.glob("*.pdf"):
                f.unlink()
                results['pdfs'] += 1
        
        if delete_images:
            # Delete all files in imgs directory (including subdirectories)
            for item in self.config.imgs_path.iterdir():
                if item.is_file():
                    item.unlink()
                    results['images'] += 1
                elif item.is_dir():
                    for f in item.iterdir():
                        if f.is_file():
                            f.unlink()
                            results['images'] += 1
                    try:
                        item.rmdir()
                    except OSError:
                        pass
        
        self.logger.info(f"Cleaned up all files: {results}")
        return results
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored files.
        
        Returns:
            Dict with counts and sizes for each file type
        """
        stats = {}
        
        # Count blogs
        blogs = list(self.config.blogs_path.glob("*.md"))
        stats['blogs'] = {
            'count': len(blogs),
            'total_size': sum(f.stat().st_size for f in blogs)
        }
        
        # Count JSONs
        jsons = list(self.config.jsons_path.glob("*.json"))
        stats['jsons'] = {
            'count': len(jsons),
            'total_size': sum(f.stat().st_size for f in jsons)
        }
        
        # Count HTMLs
        htmls = list(self.config.htmls_path.glob("*.html"))
        stats['htmls'] = {
            'count': len(htmls),
            'total_size': sum(f.stat().st_size for f in htmls)
        }
        
        # Count PDFs
        pdfs = list(self.config.pdfs_path.glob("*.pdf"))
        stats['pdfs'] = {
            'count': len(pdfs),
            'total_size': sum(f.stat().st_size for f in pdfs)
        }
        
        # Count images (recursively)
        img_count = 0
        img_size = 0
        for item in self.config.imgs_path.rglob("*"):
            if item.is_file():
                img_count += 1
                img_size += item.stat().st_size
        stats['images'] = {
            'count': img_count,
            'total_size': img_size
        }
        
        return stats


def create_local_storage_manager(base_dir: str, **kwargs) -> LocalStorageManager:
    """
    Factory function to create a LocalStorageManager with default or custom paths.
    
    Args:
        base_dir: Base directory for storage
        **kwargs: Optional overrides for directory names and cleanup flags
        
    Returns:
        Configured LocalStorageManager instance
    """
    config = StorageConfig(base_dir=base_dir, **kwargs)
    return LocalStorageManager(config)


# ==================== Aliyun OSS Storage ====================

@dataclass
class AliyunOSSConfig:
    """
    阿里云OSS配置类
    
    Attributes:
        access_key_id: 阿里云AccessKey ID
        access_key_secret: 阿里云AccessKey Secret
        endpoint: OSS endpoint (如 'oss-cn-beijing.aliyuncs.com')
        bucket_name: OSS bucket名称
        blogs_prefix: 博客存储前缀 (如 'blogs/')
        jsons_prefix: JSON存储前缀
        htmls_prefix: HTML存储前缀
        pdfs_prefix: PDF存储前缀
        imgs_prefix: 图片存储前缀
    """
    access_key_id: str
    access_key_secret: str
    endpoint: str
    bucket_name: str
    blogs_prefix: str = "blogs/"
    jsons_prefix: str = "jsons/"
    htmls_prefix: str = "htmls/"
    pdfs_prefix: str = "pdfs/"
    imgs_prefix: str = "imgs/"
    
    @classmethod
    def from_env(cls, prefix: str = "ALIYUN_") -> "AliyunOSSConfig":
        """
        从环境变量创建配置
        
        环境变量:
            ALIYUN_ACCESS_KEY_ID
            ALIYUN_ACCESS_KEY_SECRET
            ALIYUN_OSS_ENDPOINT
            ALIYUN_OSS_BUCKET
        """
        return cls(
            access_key_id=os.getenv(f"{prefix}ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv(f"{prefix}ACCESS_KEY_SECRET", ""),
            endpoint=os.getenv(f"{prefix}OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com"),
            bucket_name=os.getenv(f"{prefix}OSS_BUCKET", "paperignition"),
        )


class AliyunStorageManager(StorageManager):
    """
    阿里云OSS存储实现
    
    目前只实现博客存储功能，其他存储类型（JSON、HTML、PDF、图片）为占位符。
    
    使用方式:
        oss_config = AliyunOSSConfig(
            access_key_id="your_ak",
            access_key_secret="your_sk",
            endpoint="oss-cn-beijing.aliyuncs.com",
            bucket_name="paperignition"
        )
        storage_config = StorageConfig(base_dir="/tmp")  # 本地配置仍需提供
        manager = AliyunStorageManager(storage_config, oss_config)
    """
    
    def __init__(self, config: StorageConfig, oss_config: AliyunOSSConfig):
        super().__init__(config)
        self.oss_config = oss_config
        self._bucket = None
        self._init_oss_client()
    
    def _init_oss_client(self):
        """初始化OSS客户端"""
        try:
            import oss2
            auth = oss2.Auth(
                self.oss_config.access_key_id,
                self.oss_config.access_key_secret
            )
            self._bucket = oss2.Bucket(
                auth,
                self.oss_config.endpoint,
                self.oss_config.bucket_name
            )
            self.logger.info(
                f"Initialized Aliyun OSS client: "
                f"endpoint={self.oss_config.endpoint}, bucket={self.oss_config.bucket_name}"
            )
        except ImportError:
            self.logger.error("oss2 library not installed. Run: pip install oss2")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize OSS client: {e}")
            raise
    
    def _get_blog_key(self, doc_id: str) -> str:
        """获取博客在OSS中的key"""
        # OSS key不能以/开头
        prefix = self.oss_config.blogs_prefix.lstrip('/')
        return f"{prefix}{doc_id}.md"
    
    def _validate_oss_key(self, oss_key: str) -> bool:
        """验证OSS对象key是否有效"""
        if oss_key.startswith('/'):
            self.logger.error(f"OSS对象key不能以'/'开头: {oss_key}")
            return False
        if len(oss_key.encode('utf-8')) > 1024:
            self.logger.error(f"OSS对象key过长（超过1024字节）: {oss_key}")
            return False
        return True
    
    # ==================== Blog Operations (已实现) ====================
    
    def save_blog(self, doc_id: str, content: str) -> bool:
        """保存博客内容到OSS"""
        try:
            oss_key = self._get_blog_key(doc_id)
            if not self._validate_oss_key(oss_key):
                return False
            
            # 上传内容到OSS
            result = self._bucket.put_object(oss_key, content.encode('utf-8'))
            self.logger.debug(f"Saved blog to OSS: {oss_key}, ETag: {result.etag}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save blog {doc_id} to OSS: {e}")
            return False
    
    def read_blog(self, doc_id: str) -> Optional[str]:
        """从OSS读取博客内容"""
        try:
            oss_key = self._get_blog_key(doc_id)
            
            # 先检查是否存在
            if not self._bucket.object_exists(oss_key):
                self.logger.debug(f"Blog not found in OSS: {oss_key}")
                return None
            
            # 读取内容
            result = self._bucket.get_object(oss_key)
            content = result.read().decode('utf-8')
            return content
        except Exception as e:
            self.logger.error(f"Failed to read blog {doc_id} from OSS: {e}")
            return None
    
    def delete_blog(self, doc_id: str) -> bool:
        """从OSS删除博客"""
        try:
            oss_key = self._get_blog_key(doc_id)
            
            # 检查是否存在
            if not self._bucket.object_exists(oss_key):
                self.logger.debug(f"Blog not found in OSS (cannot delete): {oss_key}")
                return False
            
            # 删除对象
            self._bucket.delete_object(oss_key)
            self.logger.debug(f"Deleted blog from OSS: {oss_key}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete blog {doc_id} from OSS: {e}")
            return False
    
    def blog_exists(self, doc_id: str) -> bool:
        """检查博客是否存在于OSS"""
        try:
            oss_key = self._get_blog_key(doc_id)
            return self._bucket.object_exists(oss_key)
        except Exception as e:
            self.logger.error(f"Failed to check blog existence {doc_id} in OSS: {e}")
            return False
    
    def list_blogs(self) -> List[str]:
        """列出OSS中所有博客的doc_ids"""
        try:
            import oss2
            prefix = self.oss_config.blogs_prefix.lstrip('/')
            doc_ids = []
            
            for obj in oss2.ObjectIterator(self._bucket, prefix=prefix):
                # 从key中提取doc_id
                # key格式: blogs/doc_id.md
                key = obj.key
                if key.endswith('.md'):
                    # 移除前缀和.md后缀
                    doc_id = key[len(prefix):].rsplit('.md', 1)[0]
                    if doc_id:
                        doc_ids.append(doc_id)
            
            return doc_ids
        except Exception as e:
            self.logger.error(f"Failed to list blogs from OSS: {e}")
            return []
    
    def get_blog_url(self, doc_id: str, expires: int = 3600) -> Optional[str]:
        """
        生成博客的预签名URL
        
        Args:
            doc_id: 文档ID
            expires: URL过期时间（秒），默认1小时
            
        Returns:
            预签名URL，如果生成失败返回None
        """
        try:
            oss_key = self._get_blog_key(doc_id)
            if not self._bucket.object_exists(oss_key):
                return None
            
            url = self._bucket.sign_url('GET', oss_key, expires)
            return url
        except Exception as e:
            self.logger.error(f"Failed to generate presigned URL for blog {doc_id}: {e}")
            return None
    
    # ==================== Paper JSON Operations (占位符) ====================
    
    def save_paper_json(self, doc_id: str, data: Dict[str, Any]) -> bool:
        """保存论文JSON到OSS - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: save_paper_json not implemented yet")
    
    def read_paper_json(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """从OSS读取论文JSON - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: read_paper_json not implemented yet")
    
    def delete_paper_json(self, doc_id: str) -> bool:
        """从OSS删除论文JSON - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: delete_paper_json not implemented yet")
    
    def paper_json_exists(self, doc_id: str) -> bool:
        """检查论文JSON是否存在于OSS - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: paper_json_exists not implemented yet")
    
    def list_paper_jsons(self) -> List[str]:
        """列出OSS中所有论文JSON的doc_ids - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: list_paper_jsons not implemented yet")
    
    # ==================== HTML Operations (占位符) ====================
    
    def save_html(self, doc_id: str, content: str) -> bool:
        """保存HTML到OSS - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: save_html not implemented yet")
    
    def read_html(self, doc_id: str) -> Optional[str]:
        """从OSS读取HTML - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: read_html not implemented yet")
    
    def delete_html(self, doc_id: str) -> bool:
        """从OSS删除HTML - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: delete_html not implemented yet")
    
    def html_exists(self, doc_id: str) -> bool:
        """检查HTML是否存在于OSS - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: html_exists not implemented yet")
    
    # ==================== PDF Operations (占位符) ====================
    
    def save_pdf(self, doc_id: str, content: bytes) -> bool:
        """保存PDF到OSS - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: save_pdf not implemented yet")
    
    def read_pdf(self, doc_id: str) -> Optional[bytes]:
        """从OSS读取PDF - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: read_pdf not implemented yet")
    
    def delete_pdf(self, doc_id: str) -> bool:
        """从OSS删除PDF - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: delete_pdf not implemented yet")
    
    def pdf_exists(self, doc_id: str) -> bool:
        """检查PDF是否存在于OSS - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: pdf_exists not implemented yet")
    
    def get_pdf_path(self, doc_id: str) -> Optional[str]:
        """获取PDF路径 - 云存储不支持本地路径"""
        raise NotImplementedError("AliyunStorageManager: get_pdf_path not applicable for cloud storage")
    
    # ==================== Image Operations (占位符) ====================
    
    def save_image(self, doc_id: str, image_id: str, content: bytes) -> bool:
        """保存图片到OSS - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: save_image not implemented yet")
    
    def read_image(self, doc_id: str, image_id: str) -> Optional[bytes]:
        """从OSS读取图片 - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: read_image not implemented yet")
    
    def delete_image(self, doc_id: str, image_id: str) -> bool:
        """从OSS删除图片 - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: delete_image not implemented yet")
    
    def image_exists(self, doc_id: str, image_id: str) -> bool:
        """检查图片是否存在于OSS - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: image_exists not implemented yet")
    
    def list_images(self, doc_id: str) -> List[str]:
        """列出OSS中某论文的所有图片 - 暂未实现"""
        raise NotImplementedError("AliyunStorageManager: list_images not implemented yet")
    
    def get_image_path(self, doc_id: str, image_id: str) -> Optional[str]:
        """获取图片路径 - 云存储不支持本地路径"""
        raise NotImplementedError("AliyunStorageManager: get_image_path not applicable for cloud storage")
    
    # ==================== Bulk Operations (占位符) ====================
    
    def cleanup_paper_files(self, doc_id: str,
                           delete_blog: bool = False,
                           delete_json: bool = False,
                           delete_html: bool = False,
                           delete_pdf: bool = False,
                           delete_images: bool = False) -> Dict[str, bool]:
        """
        清理某论文的文件 - 目前只支持博客
        """
        results = {}
        
        if delete_blog:
            results['blog'] = self.delete_blog(doc_id)
        
        # 其他类型暂不支持
        if delete_json or delete_html or delete_pdf or delete_images:
            self.logger.warning("AliyunStorageManager: only blog cleanup is supported currently")
        
        return results
    
    def cleanup_all(self,
                   delete_blogs: bool = False,
                   delete_jsons: bool = False,
                   delete_htmls: bool = False,
                   delete_pdfs: bool = False,
                   delete_images: bool = False) -> Dict[str, int]:
        """
        清理所有文件 - 目前只支持博客
        """
        results = {
            'blogs': 0,
            'jsons': 0,
            'htmls': 0,
            'pdfs': 0,
            'images': 0
        }
        
        if delete_blogs:
            doc_ids = self.list_blogs()
            for doc_id in doc_ids:
                if self.delete_blog(doc_id):
                    results['blogs'] += 1
        
        # 其他类型暂不支持
        if delete_jsons or delete_htmls or delete_pdfs or delete_images:
            self.logger.warning("AliyunStorageManager: only blog cleanup is supported currently")
        
        return results
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        获取OSS存储统计 - 目前只统计博客
        """
        stats = {
            'blogs': {'count': 0, 'total_size': 0},
            'jsons': {'count': 0, 'total_size': 0},
            'htmls': {'count': 0, 'total_size': 0},
            'pdfs': {'count': 0, 'total_size': 0},
            'images': {'count': 0, 'total_size': 0}
        }
        
        try:
            import oss2
            prefix = self.oss_config.blogs_prefix.lstrip('/')
            
            for obj in oss2.ObjectIterator(self._bucket, prefix=prefix):
                if obj.key.endswith('.md'):
                    stats['blogs']['count'] += 1
                    stats['blogs']['total_size'] += obj.size
        except Exception as e:
            self.logger.error(f"Failed to get storage stats from OSS: {e}")
        
        return stats
    
    def test_connection(self) -> bool:
        """
        测试OSS连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            bucket_info = self._bucket.get_bucket_info()
            self.logger.info(
                f"OSS connection successful: bucket={bucket_info.name}, "
                f"storage_class={bucket_info.storage_class}"
            )
            return True
        except Exception as e:
            self.logger.error(f"OSS connection failed: {e}")
            return False


def create_aliyun_storage_manager(
    base_dir: str,
    oss_config: Optional[AliyunOSSConfig] = None,
    **kwargs
) -> AliyunStorageManager:
    """
    工厂函数：创建阿里云存储管理器
    
    Args:
        base_dir: 本地基础目录（用于StorageConfig）
        oss_config: OSS配置，如果为None则从环境变量读取
        **kwargs: StorageConfig的额外参数
        
    Returns:
        配置好的AliyunStorageManager实例
    """
    storage_config = StorageConfig(base_dir=base_dir, **kwargs)
    
    if oss_config is None:
        oss_config = AliyunOSSConfig.from_env()
    
    return AliyunStorageManager(storage_config, oss_config)

