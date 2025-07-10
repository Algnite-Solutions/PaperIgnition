import asyncio
import argparse
import sys
import os
import importlib.util
from typing import Optional
from pathlib import Path

def check_config_files():
    """检查配置文件是否存在"""
    index_config_path = Path("backend/configs/index_config.yaml")
    backend_config_path = Path("backend/configs/backend_config.yaml")
    config_module_path = Path("backend/configs/config.py")
    
    missing_files = []
    if not index_config_path.exists():
        missing_files.append(str(index_config_path))
    if not backend_config_path.exists():
        missing_files.append(str(backend_config_path))
    if not config_module_path.exists():
        missing_files.append(str(config_module_path))
        
    if missing_files:
        print(f"❌ 缺少以下配置文件:")
        for file in missing_files:
            print(f"  - {file}")
        print("请确保这些配置文件存在并包含必要的配置项")
        return False
    return True

def import_module(module_path: str) -> Optional[object]:
    """动态导入模块"""
    try:
        spec = importlib.util.spec_from_file_location(module_path, module_path)
        if spec is None:
            print(f"❌ 无法找到模块: {module_path}")
            return None
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except (ImportError, AttributeError) as e:
        print(f"❌ 导入模块 {module_path} 失败: {str(e)}")
        return None

async def run_backend_tests():
    """运行后端API测试"""
    print("\n===== 运行后端API测试 =====")
    module = import_module("tests/test_backend_api.py")
    if module and hasattr(module, "run_tests"):
        await module.run_tests()
    else:
        print("❌ 无法运行后端API测试")

async def run_index_tests():
    """运行索引服务API测试"""
    print("\n===== 运行索引服务API测试 =====")
    module = import_module("tests/test_api_endpoints.py")
    if module and hasattr(module, "run_tests"):
        await module.run_tests()
    else:
        print("❌ 无法运行索引服务API测试")

async def run_db_tests():
    """运行数据库测试"""
    print("\n===== 运行数据库测试 =====")
    module = import_module("tests/test_db.py")
    if module and hasattr(module, "run_tests"):
        await module.run_tests()
    else:
        print("❌ 无法运行数据库测试")

def run_frontend_tests():
    """运行前端测试"""
    print("\n===== 运行前端测试 =====")
    module = import_module("tests/test_frontend.py")
    if module and hasattr(module, "run_tests"):
        module.run_tests()
    else:
        print("❌ 无法运行前端测试")

async def run_all_tests():
    """运行所有测试"""
    await run_backend_tests()
    await run_index_tests()
    await run_db_tests()
    run_frontend_tests()

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="运行PaperIgnition项目的测试")
    parser.add_argument(
        "--test-type", 
        choices=["backend", "index", "db", "frontend", "all"], 
        default="all",
        help="指定要运行的测试类型: backend(后端API测试), index(索引服务API测试), db(数据库测试), frontend(前端测试), all(所有测试)"
    )
    return parser.parse_args()

if __name__ == "__main__":
    # 首先检查配置文件
    if not check_config_files():
        sys.exit(1)
        
    args = parse_args()
    
    if args.test_type == "backend":
        asyncio.run(run_backend_tests())
    elif args.test_type == "index":
        asyncio.run(run_index_tests())
    elif args.test_type == "db":
        asyncio.run(run_db_tests())
    elif args.test_type == "frontend":
        run_frontend_tests()
    else:  # all
        asyncio.run(run_all_tests())
    
    print("\n===== 所有测试完成 =====") 