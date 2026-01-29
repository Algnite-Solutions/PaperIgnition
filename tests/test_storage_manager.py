"""
测试 StorageManager 的路径处理和存储功能

主要测试点：
1. 绝对路径和相对路径的正确拼接
2. 在不同工作目录下运行时路径是否一致
3. 各种存储操作的基本功能
4. 模拟 run_orchestrator.sh 执行时的场景
"""

import os
import sys
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch

# 添加项目路径到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "orchestrator"))

from storage_util import StorageConfig, LocalStorageManager, create_local_storage_manager


class TestStorageConfigPathResolution:
    """测试 StorageConfig 的路径解析逻辑"""

    def test_relative_paths_resolved_correctly(self):
        """测试相对路径是否正确解析为绝对路径"""
        base_dir = "/data3/guofang/peirongcan/PaperIgnition/orchestrator"
        config = StorageConfig(
            base_dir=base_dir,
            blogs_dir="blogs",
            jsons_dir="jsons",
            htmls_dir="htmls",
            pdfs_dir="pdfs",
            imgs_dir="imgs"
        )
        
        # 验证路径是否正确拼接
        assert config.blogs_path == Path(base_dir) / "blogs"
        assert config.jsons_path == Path(base_dir) / "jsons"
        assert config.htmls_path == Path(base_dir) / "htmls"
        assert config.pdfs_path == Path(base_dir) / "pdfs"
        assert config.imgs_path == Path(base_dir) / "imgs"
        
    def test_absolute_paths_preserved(self):
        """测试绝对路径是否被正确保留"""
        base_dir = "/data3/guofang/peirongcan/PaperIgnition/orchestrator"
        absolute_blog_path = "/data3/guofang/peirongcan/PaperIgnition/orchestrator/blogs"
        
        config = StorageConfig(
            base_dir=base_dir,
            blogs_dir=absolute_blog_path,  # 绝对路径
            jsons_dir="jsons",  # 相对路径
        )
        
        # 绝对路径应该被直接使用，不进行拼接
        assert config.blogs_path == Path(absolute_blog_path)
        # 相对路径应该基于 base_dir 拼接
        assert config.jsons_path == Path(base_dir) / "jsons"
        
    def test_mixed_paths_from_orchestrator_config(self):
        """模拟 orchestrator.py 中的配置场景 - 混合绝对路径和相对路径"""
        # 这是 orchestrator.py 中实际使用的配置方式
        project_root = "/data3/guofang/peirongcan/PaperIgnition"
        base_dir = os.path.join(project_root, "orchestrator")
        
        # blog_output_path 在 production_config.yaml 中是绝对路径
        blog_output_path = "/data3/guofang/peirongcan/PaperIgnition/orchestrator/blogs"
        
        config = StorageConfig(
            base_dir=base_dir,
            blogs_dir=blog_output_path,  # 绝对路径 (来自配置文件)
            jsons_dir="jsons",
            htmls_dir="htmls",
            pdfs_dir="pdfs",
            imgs_dir="imgs",
        )
        
        # 验证绝对路径保持不变
        assert str(config.blogs_path) == blog_output_path
        assert config.blogs_path.is_absolute()
        
        # 验证相对路径正确拼接
        expected_jsons = Path(base_dir) / "jsons"
        expected_htmls = Path(base_dir) / "htmls"
        expected_pdfs = Path(base_dir) / "pdfs"
        expected_imgs = Path(base_dir) / "imgs"
        
        assert config.jsons_path == expected_jsons
        assert config.htmls_path == expected_htmls
        assert config.pdfs_path == expected_pdfs
        assert config.imgs_path == expected_imgs
        
        # 确保所有路径都是绝对路径
        assert config.jsons_path.is_absolute()
        assert config.htmls_path.is_absolute()
        assert config.pdfs_path.is_absolute()
        assert config.imgs_path.is_absolute()


class TestLocalStorageManagerPathConsistency:
    """测试 LocalStorageManager 在不同工作目录下的路径一致性"""
    
    @pytest.fixture
    def temp_storage_dir(self):
        """创建临时存储目录"""
        temp_dir = tempfile.mkdtemp(prefix="test_storage_")
        yield temp_dir
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_path_consistency_different_cwd(self, temp_storage_dir):
        """测试在不同工作目录下创建的 StorageManager 路径是否一致"""
        original_cwd = os.getcwd()
        base_dir = temp_storage_dir
        
        try:
            # 在项目根目录创建 StorageManager
            os.chdir("/")
            config1 = StorageConfig(base_dir=base_dir)
            manager1 = LocalStorageManager(config1)
            paths1 = {
                'blogs': str(manager1.config.blogs_path),
                'jsons': str(manager1.config.jsons_path),
                'pdfs': str(manager1.config.pdfs_path),
            }
            
            # 在另一个目录创建 StorageManager
            os.chdir("/tmp")
            config2 = StorageConfig(base_dir=base_dir)
            manager2 = LocalStorageManager(config2)
            paths2 = {
                'blogs': str(manager2.config.blogs_path),
                'jsons': str(manager2.config.jsons_path),
                'pdfs': str(manager2.config.pdfs_path),
            }
            
            # 路径应该完全一致
            assert paths1 == paths2, "路径在不同工作目录下应该保持一致"
            
        finally:
            os.chdir(original_cwd)
            
    def test_storage_operations_with_absolute_paths(self, temp_storage_dir):
        """测试使用绝对路径时的存储操作"""
        original_cwd = os.getcwd()
        base_dir = temp_storage_dir
        
        try:
            # 模拟 run_orchestrator.sh 的场景：从任意目录运行
            os.chdir("/tmp")
            
            config = StorageConfig(base_dir=base_dir)
            manager = LocalStorageManager(config)
            
            # 测试 blog 操作
            doc_id = "test_paper_123"
            blog_content = "# Test Blog\n\nThis is a test blog content."
            
            assert manager.save_blog(doc_id, blog_content) == True
            assert manager.blog_exists(doc_id) == True
            assert manager.read_blog(doc_id) == blog_content
            
            # 验证文件确实存在于预期路径
            expected_blog_path = Path(base_dir) / "blogs" / f"{doc_id}.md"
            assert expected_blog_path.exists(), f"Blog 文件应该存在于 {expected_blog_path}"
            
            # 清理
            assert manager.delete_blog(doc_id) == True
            assert manager.blog_exists(doc_id) == False
            
        finally:
            os.chdir(original_cwd)


class TestStorageManagerCRUDOperations:
    """测试 LocalStorageManager 的 CRUD 操作"""
    
    @pytest.fixture
    def manager(self):
        """创建带有临时目录的 StorageManager"""
        temp_dir = tempfile.mkdtemp(prefix="test_storage_crud_")
        config = StorageConfig(base_dir=temp_dir)
        manager = LocalStorageManager(config)
        yield manager
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_blog_crud(self, manager):
        """测试 Blog 的 CRUD 操作"""
        doc_id = "paper_001"
        content = "# My Paper Blog\n\n## Abstract\n\nThis is the abstract."
        
        # Create
        assert manager.save_blog(doc_id, content) == True
        
        # Read
        assert manager.read_blog(doc_id) == content
        
        # Exists
        assert manager.blog_exists(doc_id) == True
        
        # List
        assert doc_id in manager.list_blogs()
        
        # Delete
        assert manager.delete_blog(doc_id) == True
        assert manager.blog_exists(doc_id) == False
        
    def test_paper_json_crud(self, manager):
        """测试 Paper JSON 的 CRUD 操作"""
        doc_id = "paper_002"
        data = {
            "title": "Test Paper",
            "authors": ["Author A", "Author B"],
            "abstract": "This is a test abstract.",
            "doc_id": doc_id
        }
        
        # Create
        assert manager.save_paper_json(doc_id, data) == True
        
        # Read
        loaded_data = manager.read_paper_json(doc_id)
        assert loaded_data == data
        
        # Exists
        assert manager.paper_json_exists(doc_id) == True
        
        # List
        assert doc_id in manager.list_paper_jsons()
        
        # Delete
        assert manager.delete_paper_json(doc_id) == True
        assert manager.paper_json_exists(doc_id) == False
        
    def test_html_crud(self, manager):
        """测试 HTML 的 CRUD 操作"""
        doc_id = "paper_003"
        content = "<html><body><h1>Test Paper</h1></body></html>"
        
        # Create
        assert manager.save_html(doc_id, content) == True
        
        # Read
        assert manager.read_html(doc_id) == content
        
        # Exists
        assert manager.html_exists(doc_id) == True
        
        # Delete
        assert manager.delete_html(doc_id) == True
        assert manager.html_exists(doc_id) == False
        
    def test_pdf_crud(self, manager):
        """测试 PDF 的 CRUD 操作"""
        doc_id = "paper_004"
        content = b"%PDF-1.4 fake pdf content for testing"
        
        # Create
        assert manager.save_pdf(doc_id, content) == True
        
        # Read
        assert manager.read_pdf(doc_id) == content
        
        # Exists
        assert manager.pdf_exists(doc_id) == True
        
        # Get path
        pdf_path = manager.get_pdf_path(doc_id)
        assert pdf_path is not None
        assert Path(pdf_path).exists()
        
        # Delete
        assert manager.delete_pdf(doc_id) == True
        assert manager.pdf_exists(doc_id) == False
        
    def test_image_crud(self, manager):
        """测试 Image 的 CRUD 操作"""
        doc_id = "paper_005"
        image_id = "figure_1.png"
        content = b"\x89PNG\r\n\x1a\n fake image content"
        
        # Create
        assert manager.save_image(doc_id, image_id, content) == True
        
        # Read
        assert manager.read_image(doc_id, image_id) == content
        
        # Exists
        assert manager.image_exists(doc_id, image_id) == True
        
        # List
        assert image_id in manager.list_images(doc_id)
        
        # Get path
        img_path = manager.get_image_path(doc_id, image_id)
        assert img_path is not None
        assert Path(img_path).exists()
        
        # Delete
        assert manager.delete_image(doc_id, image_id) == True
        assert manager.image_exists(doc_id, image_id) == False


class TestOrchestratorIntegrationScenario:
    """模拟 orchestrator.py 运行时的场景进行测试"""
    
    @pytest.fixture
    def orchestrator_like_setup(self):
        """模拟 orchestrator 的设置方式"""
        temp_dir = tempfile.mkdtemp(prefix="test_orchestrator_")
        
        # 模拟项目结构
        project_root = temp_dir
        orchestrator_dir = os.path.join(project_root, "orchestrator")
        os.makedirs(orchestrator_dir, exist_ok=True)
        
        yield {
            'project_root': project_root,
            'orchestrator_dir': orchestrator_dir,
            'temp_dir': temp_dir
        }
        
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_simulate_orchestrator_storage_setup(self, orchestrator_like_setup):
        """模拟 orchestrator.py 中的存储设置"""
        project_root = orchestrator_like_setup['project_root']
        base_dir = os.path.join(project_root, "orchestrator")
        
        # 模拟配置文件中的 blog_output_path (绝对路径)
        blog_output_path = os.path.join(project_root, "orchestrator", "blogs")
        
        # 这是 orchestrator.py 实际创建 StorageConfig 的方式
        storage_config = StorageConfig(
            base_dir=base_dir,
            blogs_dir=blog_output_path,
            jsons_dir="jsons",
            htmls_dir="htmls",
            pdfs_dir="pdfs",
            imgs_dir="imgs",
        )
        
        manager = LocalStorageManager(storage_config)
        
        # 验证所有路径都是绝对路径
        assert storage_config.blogs_path.is_absolute()
        assert storage_config.jsons_path.is_absolute()
        assert storage_config.htmls_path.is_absolute()
        assert storage_config.pdfs_path.is_absolute()
        assert storage_config.imgs_path.is_absolute()
        
        # 验证路径正确指向 orchestrator 目录下
        assert str(storage_config.blogs_path).startswith(base_dir)
        assert str(storage_config.jsons_path).startswith(base_dir)
        assert str(storage_config.htmls_path).startswith(base_dir)
        assert str(storage_config.pdfs_path).startswith(base_dir)
        assert str(storage_config.imgs_path).startswith(base_dir)
        
    def test_run_from_different_cwd_simulating_shell_script(self, orchestrator_like_setup):
        """
        模拟 run_orchestrator.sh 的执行场景：
        脚本可能从任意目录执行，但使用绝对路径调用 orchestrator.py
        """
        original_cwd = os.getcwd()
        project_root = orchestrator_like_setup['project_root']
        base_dir = os.path.join(project_root, "orchestrator")
        blog_output_path = os.path.join(project_root, "orchestrator", "blogs")
        
        try:
            # 场景1: 从项目根目录运行
            os.chdir(project_root)
            config1 = StorageConfig(
                base_dir=base_dir,
                blogs_dir=blog_output_path,
                jsons_dir="jsons",
            )
            manager1 = LocalStorageManager(config1)
            
            # 场景2: 从 /tmp 目录运行 (模拟用户可能在任意目录执行脚本)
            os.chdir("/tmp")
            config2 = StorageConfig(
                base_dir=base_dir,
                blogs_dir=blog_output_path,
                jsons_dir="jsons",
            )
            manager2 = LocalStorageManager(config2)
            
            # 场景3: 从 home 目录运行
            os.chdir(os.path.expanduser("~"))
            config3 = StorageConfig(
                base_dir=base_dir,
                blogs_dir=blog_output_path,
                jsons_dir="jsons",
            )
            manager3 = LocalStorageManager(config3)
            
            # 所有场景的路径应该完全一致
            assert str(config1.blogs_path) == str(config2.blogs_path) == str(config3.blogs_path)
            assert str(config1.jsons_path) == str(config2.jsons_path) == str(config3.jsons_path)
            
            # 写入测试数据 (从 /tmp 目录)
            os.chdir("/tmp")
            doc_id = "test_doc_001"
            blog_content = "Test blog content"
            
            assert manager2.save_blog(doc_id, blog_content) == True
            
            # 验证数据存在于正确的路径
            expected_path = Path(blog_output_path) / f"{doc_id}.md"
            assert expected_path.exists(), f"文件应该存在于 {expected_path}"
            
            # 从另一个目录也能正确读取
            os.chdir(project_root)
            assert manager1.read_blog(doc_id) == blog_content
            
        finally:
            os.chdir(original_cwd)
            

class TestBulkOperations:
    """测试批量操作功能"""
    
    @pytest.fixture
    def manager_with_data(self):
        """创建带有测试数据的 StorageManager"""
        temp_dir = tempfile.mkdtemp(prefix="test_bulk_")
        config = StorageConfig(base_dir=temp_dir)
        manager = LocalStorageManager(config)
        
        # 添加测试数据
        for i in range(5):
            doc_id = f"paper_{i:03d}"
            manager.save_blog(doc_id, f"Blog content {i}")
            manager.save_paper_json(doc_id, {"title": f"Paper {i}", "doc_id": doc_id})
            manager.save_html(doc_id, f"<html>{i}</html>")
            manager.save_pdf(doc_id, f"PDF content {i}".encode())
            manager.save_image(doc_id, f"fig_{i}.png", f"Image {i}".encode())
            
        yield manager
        
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    def test_cleanup_paper_files(self, manager_with_data):
        """测试清理单个论文的文件"""
        doc_id = "paper_000"
        
        # 确认文件存在
        assert manager_with_data.blog_exists(doc_id)
        assert manager_with_data.paper_json_exists(doc_id)
        assert manager_with_data.html_exists(doc_id)
        assert manager_with_data.pdf_exists(doc_id)
        
        # 只删除 blog 和 json
        results = manager_with_data.cleanup_paper_files(
            doc_id,
            delete_blog=True,
            delete_json=True,
            delete_html=False,
            delete_pdf=False,
            delete_images=False
        )
        
        # 验证结果
        assert results['blog'] == True
        assert results['json'] == True
        
        # blog 和 json 应该被删除
        assert not manager_with_data.blog_exists(doc_id)
        assert not manager_with_data.paper_json_exists(doc_id)
        
        # html 和 pdf 应该保留
        assert manager_with_data.html_exists(doc_id)
        assert manager_with_data.pdf_exists(doc_id)
        
    def test_cleanup_all(self, manager_with_data):
        """测试批量清理所有文件"""
        # 确认有文件存在
        assert len(manager_with_data.list_blogs()) == 5
        assert len(manager_with_data.list_paper_jsons()) == 5
        
        # 只删除 blogs
        results = manager_with_data.cleanup_all(
            delete_blogs=True,
            delete_jsons=False,
            delete_htmls=False,
            delete_pdfs=False,
            delete_images=False
        )
        
        assert results['blogs'] == 5
        assert len(manager_with_data.list_blogs()) == 0
        assert len(manager_with_data.list_paper_jsons()) == 5  # JSON 保留
        
    def test_get_storage_stats(self, manager_with_data):
        """测试获取存储统计信息"""
        stats = manager_with_data.get_storage_stats()
        
        assert stats['blogs']['count'] == 5
        assert stats['jsons']['count'] == 5
        assert stats['htmls']['count'] == 5
        assert stats['pdfs']['count'] == 5
        assert stats['images']['count'] == 5
        
        # 验证总大小大于 0
        assert stats['blogs']['total_size'] > 0
        assert stats['jsons']['total_size'] > 0


class TestEdgeCases:
    """测试边界情况"""
    
    @pytest.fixture
    def manager(self):
        """创建 StorageManager"""
        temp_dir = tempfile.mkdtemp(prefix="test_edge_")
        config = StorageConfig(base_dir=temp_dir)
        manager = LocalStorageManager(config)
        yield manager
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    def test_read_nonexistent_files(self, manager):
        """测试读取不存在的文件"""
        doc_id = "nonexistent_paper"
        
        assert manager.read_blog(doc_id) is None
        assert manager.read_paper_json(doc_id) is None
        assert manager.read_html(doc_id) is None
        assert manager.read_pdf(doc_id) is None
        assert manager.read_image(doc_id, "image.png") is None
        
    def test_delete_nonexistent_files(self, manager):
        """测试删除不存在的文件"""
        doc_id = "nonexistent_paper"
        
        assert manager.delete_blog(doc_id) == False
        assert manager.delete_paper_json(doc_id) == False
        assert manager.delete_html(doc_id) == False
        assert manager.delete_pdf(doc_id) == False
        assert manager.delete_image(doc_id, "image.png") == False
        
    def test_special_characters_in_doc_id(self, manager):
        """测试 doc_id 包含特殊字符的情况"""
        # arXiv 论文 ID 可能包含点号
        doc_id = "2401.12345"
        content = "Blog content for paper with special ID"
        
        assert manager.save_blog(doc_id, content) == True
        assert manager.read_blog(doc_id) == content
        assert manager.delete_blog(doc_id) == True
        
    def test_unicode_content(self, manager):
        """测试包含 Unicode 字符的内容"""
        doc_id = "unicode_paper"
        content = """# 论文标题
        
## 摘要

这是一篇关于深度学习的论文。包含中文、日本語、한국어等多种语言。

数学公式: α + β = γ
"""
        
        assert manager.save_blog(doc_id, content) == True
        loaded_content = manager.read_blog(doc_id)
        assert loaded_content == content
        assert "深度学习" in loaded_content
        assert "日本語" in loaded_content
        
    def test_empty_content(self, manager):
        """测试空内容"""
        doc_id = "empty_paper"
        
        # 空 blog
        assert manager.save_blog(doc_id, "") == True
        assert manager.read_blog(doc_id) == ""
        
        # 空 JSON
        assert manager.save_paper_json(doc_id, {}) == True
        assert manager.read_paper_json(doc_id) == {}
        

class TestFactoryFunction:
    """测试工厂函数"""
    
    def test_create_local_storage_manager(self):
        """测试 create_local_storage_manager 工厂函数"""
        temp_dir = tempfile.mkdtemp(prefix="test_factory_")
        
        try:
            manager = create_local_storage_manager(
                base_dir=temp_dir,
                blogs_dir="custom_blogs",
                jsons_dir="custom_jsons"
            )
            
            assert isinstance(manager, LocalStorageManager)
            assert str(manager.config.blogs_path) == os.path.join(temp_dir, "custom_blogs")
            assert str(manager.config.jsons_path) == os.path.join(temp_dir, "custom_jsons")
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestPathConsistencyWithOriginalCode:
    """
    验证 StorageManager 的路径与原代码的路径是否一致
    
    这些测试确保重构后的代码行为与原代码完全一致
    """
    
    @pytest.fixture
    def simulated_project_structure(self):
        """模拟真实的项目目录结构"""
        temp_dir = tempfile.mkdtemp(prefix="test_consistency_")
        
        # 模拟真实的项目结构
        project_root = temp_dir
        orchestrator_dir = os.path.join(project_root, "orchestrator")
        blogs_dir = os.path.join(orchestrator_dir, "blogs")
        jsons_dir = os.path.join(orchestrator_dir, "jsons")
        htmls_dir = os.path.join(orchestrator_dir, "htmls")
        pdfs_dir = os.path.join(orchestrator_dir, "pdfs")
        imgs_dir = os.path.join(orchestrator_dir, "imgs")
        
        # 创建目录
        for d in [orchestrator_dir, blogs_dir, jsons_dir, htmls_dir, pdfs_dir, imgs_dir]:
            os.makedirs(d, exist_ok=True)
        
        yield {
            'project_root': project_root,
            'orchestrator_dir': orchestrator_dir,
            'blogs_dir': blogs_dir,
            'jsons_dir': jsons_dir,
            'htmls_dir': htmls_dir,
            'pdfs_dir': pdfs_dir,
            'imgs_dir': imgs_dir,
        }
        
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_orchestrator_blog_path_consistency(self, simulated_project_structure):
        """
        验证 orchestrator.py 中的博客路径一致性
        
        原代码 (orchestrator.py 第 214-216 行):
            blog_path = os.path.join(output_path, f"{paper.doc_id}.md")
            with open(blog_path, encoding="utf-8") as file:
                blog = file.read()
        
        新代码:
            blog = self.storage_manager.read_blog(paper.doc_id)
        """
        project_root = simulated_project_structure['project_root']
        base_dir = simulated_project_structure['orchestrator_dir']
        
        # 模拟 production_config.yaml 中的配置 (绝对路径)
        blog_output_path = os.path.join(project_root, "orchestrator", "blogs")
        
        # === 原代码的路径计算方式 ===
        doc_id = "2401.12345"
        original_blog_path = os.path.join(blog_output_path, f"{doc_id}.md")
        
        # === 新代码使用 StorageManager ===
        # 模拟 orchestrator.py 第 88-102 行的配置方式
        storage_config = StorageConfig(
            base_dir=base_dir,
            blogs_dir=blog_output_path,                    # 绝对路径
            jsons_dir=os.path.join(base_dir, "jsons"),     # 绝对路径
            htmls_dir=os.path.join(base_dir, "htmls"),     # 绝对路径
            pdfs_dir=os.path.join(base_dir, "pdfs"),       # 绝对路径
            imgs_dir=os.path.join(base_dir, "imgs"),       # 绝对路径
        )
        manager = LocalStorageManager(storage_config)
        
        # 计算 StorageManager 的博客路径
        new_blog_path = str(manager.config.blogs_path / f"{doc_id}.md")
        
        # 验证路径一致
        assert original_blog_path == new_blog_path, \
            f"路径不一致!\n原代码: {original_blog_path}\n新代码: {new_blog_path}"
        
        # 验证读写操作
        blog_content = "# Test Blog\n\nThis is test content for paper 2401.12345"
        
        # 用原方式写入
        with open(original_blog_path, 'w', encoding='utf-8') as f:
            f.write(blog_content)
        
        # 用新方式读取
        read_content = manager.read_blog(doc_id)
        assert read_content == blog_content, "StorageManager 读取的内容与原代码写入的不一致"
        
        # 用新方式写入
        new_content = "# Updated Blog\n\nNew content"
        manager.save_blog(doc_id, new_content)
        
        # 用原方式读取
        with open(original_blog_path, 'r', encoding='utf-8') as f:
            original_read = f.read()
        assert original_read == new_content, "原代码读取的内容与 StorageManager 写入的不一致"
    
    def test_paper_pull_paths_consistency(self, simulated_project_structure):
        """
        验证 paper_pull.py 中的路径一致性
        
        原代码 (paper_pull.py 第 54-57 行):
            self.html_text_folder = self.base_dir / "htmls"
            self.pdf_folder_path = self.base_dir / "pdfs"
            self.image_folder_path = self.base_dir / "imgs"
            self.json_output_path = self.base_dir / "jsons"
        
        新代码使用 storage_manager.config 的路径
        """
        base_dir = Path(simulated_project_structure['orchestrator_dir'])
        
        # === 原代码的路径计算方式 ===
        original_html_folder = base_dir / "htmls"
        original_pdf_folder = base_dir / "pdfs"
        original_img_folder = base_dir / "imgs"
        original_json_folder = base_dir / "jsons"
        
        # === 新代码使用 StorageManager ===
        storage_config = StorageConfig(
            base_dir=str(base_dir),
            blogs_dir=os.path.join(str(base_dir), "blogs"),
            jsons_dir=os.path.join(str(base_dir), "jsons"),
            htmls_dir=os.path.join(str(base_dir), "htmls"),
            pdfs_dir=os.path.join(str(base_dir), "pdfs"),
            imgs_dir=os.path.join(str(base_dir), "imgs"),
        )
        manager = LocalStorageManager(storage_config)
        
        # 验证路径一致
        assert str(original_html_folder) == str(manager.config.htmls_path), \
            f"HTML 路径不一致!\n原: {original_html_folder}\n新: {manager.config.htmls_path}"
        assert str(original_pdf_folder) == str(manager.config.pdfs_path), \
            f"PDF 路径不一致!\n原: {original_pdf_folder}\n新: {manager.config.pdfs_path}"
        assert str(original_img_folder) == str(manager.config.imgs_path), \
            f"IMG 路径不一致!\n原: {original_img_folder}\n新: {manager.config.imgs_path}"
        assert str(original_json_folder) == str(manager.config.jsons_path), \
            f"JSON 路径不一致!\n原: {original_json_folder}\n新: {manager.config.jsons_path}"
    
    def test_paper_pull_json_loading_consistency(self, simulated_project_structure):
        """
        验证 paper_pull.py 中 JSON 加载的一致性
        
        原代码 (paper_pull.py 第 225-227 行):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                docset = DocSet(**data)
        
        新代码:
            docset = self.storage_manager.load_paper_docset(doc_id)
        """
        jsons_dir = simulated_project_structure['jsons_dir']
        base_dir = simulated_project_structure['orchestrator_dir']
        
        # 创建测试数据
        doc_id = "2401.98765"
        paper_data = {
            "doc_id": doc_id,
            "title": "Test Paper Title",
            "authors": ["Author A", "Author B"],
            "abstract": "This is the abstract of the test paper.",
            "categories": ["cs.AI", "cs.LG"],
            "published_date": "2024-01-15",
            "pdf_path": "",
            "HTML_path": "",
            "text_chunks": [],
            "figure_chunks": [],
            "table_chunks": [],
            "metadata": {},
            "comments": ""
        }
        
        # === 原方式：直接写入 JSON 文件 ===
        original_json_path = os.path.join(jsons_dir, f"{doc_id}.json")
        with open(original_json_path, 'w', encoding='utf-8') as f:
            json.dump(paper_data, f, ensure_ascii=False, indent=2)
        
        # === 新方式：使用 StorageManager 读取 ===
        storage_config = StorageConfig(
            base_dir=base_dir,
            jsons_dir=os.path.join(base_dir, "jsons"),
        )
        manager = LocalStorageManager(storage_config)
        
        # 验证 StorageManager 的 JSON 路径
        new_json_path = str(manager.config.jsons_path / f"{doc_id}.json")
        assert original_json_path == new_json_path, \
            f"JSON 路径不一致!\n原: {original_json_path}\n新: {new_json_path}"
        
        # 验证读取的数据一致
        loaded_data = manager.read_paper_json(doc_id)
        assert loaded_data == paper_data, "StorageManager 读取的 JSON 数据与原数据不一致"
        
        # 验证 load_paper_docset 能正确加载
        docset = manager.load_paper_docset(doc_id)
        assert docset is not None, "load_paper_docset 返回 None"
        assert docset.doc_id == doc_id
        assert docset.title == paper_data["title"]
        assert docset.authors == paper_data["authors"]
    
    def test_generate_blog_path_consistency(self, simulated_project_structure):
        """
        验证 generate_blog.py 中的路径一致性
        
        原代码 (generate_blog.py 第 115 行):
            with open(f"./orchestrator/blogs/{paper.doc_id}.md", encoding="utf-8") as file:
                blog_content = file.read()
        
        新代码:
            blog_content = storage_manager.read_blog(paper.doc_id)
        
        注意: 原代码使用相对路径 "./orchestrator/blogs/"，这在不同工作目录下会有问题
        新代码使用绝对路径，更加可靠
        """
        project_root = simulated_project_structure['project_root']
        orchestrator_dir = simulated_project_structure['orchestrator_dir']
        blogs_dir = simulated_project_structure['blogs_dir']
        
        doc_id = "2401.54321"
        blog_content = "# 论文解读\n\n这是一篇关于深度学习的论文解读。"
        
        # === 原代码的路径 (相对路径，依赖当前工作目录) ===
        # 原代码: f"./orchestrator/blogs/{paper.doc_id}.md"
        # 如果从项目根目录运行，路径是: {project_root}/orchestrator/blogs/{doc_id}.md
        original_cwd = os.getcwd()
        
        try:
            # 模拟从项目根目录运行
            os.chdir(project_root)
            original_relative_path = f"./orchestrator/blogs/{doc_id}.md"
            original_absolute_path = os.path.abspath(original_relative_path)
            
            # === 新代码使用 StorageManager (使用绝对路径) ===
            storage_config = StorageConfig(
                base_dir=orchestrator_dir,
                blogs_dir=blogs_dir,  # 绝对路径
            )
            manager = LocalStorageManager(storage_config)
            new_path = str(manager.config.blogs_path / f"{doc_id}.md")
            
            # 验证路径一致 (在项目根目录下)
            assert original_absolute_path == new_path, \
                f"路径不一致!\n原: {original_absolute_path}\n新: {new_path}"
            
            # 写入测试数据
            manager.save_blog(doc_id, blog_content)
            
            # 用原方式读取 (从项目根目录)
            with open(original_relative_path, 'r', encoding='utf-8') as f:
                original_read = f.read()
            assert original_read == blog_content, "原方式读取失败"
            
            # 验证从不同目录读取时，StorageManager 仍然有效
            os.chdir("/tmp")
            read_from_tmp = manager.read_blog(doc_id)
            assert read_from_tmp == blog_content, \
                "从 /tmp 目录使用 StorageManager 读取失败，说明绝对路径有问题"
            
        finally:
            os.chdir(original_cwd)
    
    def test_all_paths_match_production_config(self, simulated_project_structure):
        """
        验证使用 production_config.yaml 配置时的路径一致性
        
        production_config.yaml 中:
            blog_generation:
              output_path: "/data3/guofang/peirongcan/PaperIgnition/orchestrator/blogs"
        
        这个测试模拟完整的 orchestrator.py 初始化过程
        """
        project_root = simulated_project_structure['project_root']
        orchestrator_dir = simulated_project_structure['orchestrator_dir']
        
        # 模拟 production_config.yaml 的配置
        mock_orch_config = {
            "blog_generation": {
                "output_path": os.path.join(project_root, "orchestrator", "blogs")
            },
            "storage": {
                "keep_blogs": True,
                "keep_jsons": True,
                "keep_htmls": True,
                "keep_pdfs": True,
                "keep_imgs": True,
            }
        }
        
        # === 模拟 orchestrator.py 第 81-102 行的逻辑 ===
        base_dir = orchestrator_dir
        blog_output_path = mock_orch_config["blog_generation"]["output_path"]
        
        # 如果 blog_output_path 不是绝对路径，转换为绝对路径
        if not os.path.isabs(blog_output_path):
            blog_output_path = os.path.join(project_root, blog_output_path)
        
        storage_config = StorageConfig(
            base_dir=base_dir,
            blogs_dir=blog_output_path,                    # 绝对路径
            jsons_dir=os.path.join(base_dir, "jsons"),     # 绝对路径
            htmls_dir=os.path.join(base_dir, "htmls"),     # 绝对路径
            pdfs_dir=os.path.join(base_dir, "pdfs"),       # 绝对路径
            imgs_dir=os.path.join(base_dir, "imgs"),       # 绝对路径
            keep_blogs=mock_orch_config.get("storage", {}).get("keep_blogs", True),
            keep_jsons=mock_orch_config.get("storage", {}).get("keep_jsons", True),
            keep_htmls=mock_orch_config.get("storage", {}).get("keep_htmls", True),
            keep_pdfs=mock_orch_config.get("storage", {}).get("keep_pdfs", True),
            keep_imgs=mock_orch_config.get("storage", {}).get("keep_imgs", True),
        )
        manager = LocalStorageManager(storage_config)
        
        # 验证所有路径都指向正确的位置
        expected_paths = {
            'blogs': os.path.join(project_root, "orchestrator", "blogs"),
            'jsons': os.path.join(project_root, "orchestrator", "jsons"),
            'htmls': os.path.join(project_root, "orchestrator", "htmls"),
            'pdfs': os.path.join(project_root, "orchestrator", "pdfs"),
            'imgs': os.path.join(project_root, "orchestrator", "imgs"),
        }
        
        assert str(manager.config.blogs_path) == expected_paths['blogs'], \
            f"blogs 路径不匹配: {manager.config.blogs_path} != {expected_paths['blogs']}"
        assert str(manager.config.jsons_path) == expected_paths['jsons'], \
            f"jsons 路径不匹配: {manager.config.jsons_path} != {expected_paths['jsons']}"
        assert str(manager.config.htmls_path) == expected_paths['htmls'], \
            f"htmls 路径不匹配: {manager.config.htmls_path} != {expected_paths['htmls']}"
        assert str(manager.config.pdfs_path) == expected_paths['pdfs'], \
            f"pdfs 路径不匹配: {manager.config.pdfs_path} != {expected_paths['pdfs']}"
        assert str(manager.config.imgs_path) == expected_paths['imgs'], \
            f"imgs 路径不匹配: {manager.config.imgs_path} != {expected_paths['imgs']}"
    
    def test_cross_file_data_sharing(self, simulated_project_structure):
        """
        测试跨文件的数据共享场景
        
        场景: paper_pull.py 保存 JSON，orchestrator.py 读取并处理，generate_blog.py 生成博客
        验证整个流程中的数据一致性
        """
        project_root = simulated_project_structure['project_root']
        orchestrator_dir = simulated_project_structure['orchestrator_dir']
        
        # 创建共享的 StorageManager (模拟 orchestrator.py 中创建并传递给其他模块)
        blog_output_path = os.path.join(project_root, "orchestrator", "blogs")
        storage_config = StorageConfig(
            base_dir=orchestrator_dir,
            blogs_dir=blog_output_path,
            jsons_dir=os.path.join(orchestrator_dir, "jsons"),
            htmls_dir=os.path.join(orchestrator_dir, "htmls"),
            pdfs_dir=os.path.join(orchestrator_dir, "pdfs"),
            imgs_dir=os.path.join(orchestrator_dir, "imgs"),
        )
        manager = LocalStorageManager(storage_config)
        
        # === Step 1: 模拟 paper_pull.py 保存论文数据 ===
        doc_id = "2401.cross_test"
        paper_data = {
            "doc_id": doc_id,
            "title": "Cross-file Test Paper",
            "authors": ["Tester"],
            "abstract": "Testing cross-file data consistency.",
            "categories": ["cs.SE"],
            "published_date": "2024-01-20",
            "pdf_path": "",
            "HTML_path": "",
            "text_chunks": [],
            "figure_chunks": [],
            "table_chunks": [],
            "metadata": {},
            "comments": ""
        }
        
        # paper_pull.py 原方式保存 (serialize_docs)
        original_json_path = os.path.join(orchestrator_dir, "jsons", f"{doc_id}.json")
        with open(original_json_path, 'w', encoding='utf-8') as f:
            json.dump(paper_data, f, ensure_ascii=False, indent=2)
        
        # === Step 2: 模拟 orchestrator.py 读取论文数据 ===
        # 使用 StorageManager 读取
        loaded_docset = manager.load_paper_docset(doc_id)
        assert loaded_docset is not None, "orchestrator 无法读取 paper_pull 保存的数据"
        assert loaded_docset.title == paper_data["title"]
        
        # === Step 3: 模拟 generate_blog.py 保存博客 ===
        blog_content = f"# {loaded_docset.title}\n\n## 摘要\n\n{loaded_docset.abstract}"
        manager.save_blog(doc_id, blog_content)
        
        # === Step 4: 模拟 orchestrator.py 读取博客用于上传数据库 ===
        read_blog = manager.read_blog(doc_id)
        assert read_blog == blog_content, "orchestrator 无法读取 generate_blog 保存的博客"
        
        # === 验证原方式也能读取 ===
        original_blog_path = os.path.join(blog_output_path, f"{doc_id}.md")
        with open(original_blog_path, 'r', encoding='utf-8') as f:
            original_read = f.read()
        assert original_read == blog_content, "原方式无法读取 StorageManager 保存的博客"


if __name__ == "__main__":
    # 可以直接运行此文件进行测试
    pytest.main([__file__, "-v", "--tb=short"])

