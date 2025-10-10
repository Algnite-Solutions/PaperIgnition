from backend.app.db_utils import load_config as load_backend_config
from blog_generation_main import blog_generation_for_storage
from blog_recommendation_main import blog_generation_for_existing_user
from utils import run_batch_generation, run_batch_generation_abs, run_batch_generation_title, fetch_daily_papers
import asyncio
import argparse
from typing import List, Any, Callable, Dict

class GeneratorRegistry:
    """生成器注册表 - 管理不同类型的生成器"""

    def __init__(self):
        self._generators = {
            "blog_full": run_batch_generation,
            "blog_abstract": run_batch_generation_abs,
            "blog_title": run_batch_generation_title,
            "storage_blog": blog_generation_for_storage,
            # 未来功能 定制化生成
            "blog_customization": blog_generation_for_existing_user
        }

    def register(self, name: str, func: Callable):
        """注册新的生成器"""
        self._generators[name] = func

    def get(self, name: str):
        """获取生成器"""
        return self._generators.get(name)

    def list_available(self) -> List[str]:
        """列出可用的生成器"""
        return list(self._generators.keys())

# 全局注册表
generator_registry = GeneratorRegistry()

class PaperOrchestrator:
    """基于现有工作流的编排器"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or "../backend/configs/app_config.yaml"
        self.config = load_backend_config(self.config_path)
        self.registry = generator_registry

    def register_generator(self, name: str, generator_func):
        """注册LLM生成器函数"""
        self.registry.register(name, generator_func)

    async def run_task(self, task_name: str, **kwargs):
        """执行指定任务"""
        if task_name == "daily_blog":
            return await self._run_daily_blog_generation(**kwargs)
        elif task_name == "user_recommendations":
            return await self._run_user_recommendations(**kwargs)
        else:
            # 使用注册表中的生成器
            generator = self.registry.get(task_name)
            if generator:
                if asyncio.iscoroutinefunction(generator):
                    return await generator(**kwargs)
                else:
                    return generator(**kwargs)
            else:
                raise ValueError(f"Unknown task: {task_name}. Available tasks: {self.list_available_tasks()}")

    async def _run_daily_blog_generation(self, generator_type="default"):
        """日常博客生成 - 对应 blog_generation_main.py"""
        papers = fetch_daily_papers(
            self.config['INDEX_SERVICE']["host"],
            self.config
        )

        # 可选择不同的生成器
        if generator_type == "batch":
            await run_batch_generation(papers)
        elif generator_type == "storage":
            await blog_generation_for_storage(
                self.config['INDEX_SERVICE']["host"],
                self.config['APP_SERVICE']["host"],
                papers
            )

        return f"Generated blogs for {len(papers)} papers"

    async def _run_user_recommendations(self, generator_types=["full", "abstract", "title"]):
        """用户推荐生成 - 对应 blog_recommendation_main.py"""
        await blog_generation_for_existing_user(
            self.config['INDEX_SERVICE']["host"],
            self.config['APP_SERVICE']["host"]
        )
        return "User recommendations completed"

    async def run_with_generator(self, generator_name: str, **kwargs):
        """使用指定的生成器执行任务"""
        generator = self.registry.get(generator_name)
        if not generator:
            raise ValueError(f"Generator '{generator_name}' not found. Available: {self.registry.list_available()}")
        
        if asyncio.iscoroutinefunction(generator):
            return await generator(**kwargs)
        else:
            return generator(**kwargs)

    async def run_pipeline(self, tasks: List[tuple]):
        """执行多个任务的管道"""
        results = []
        for task_name, task_kwargs in tasks:
            print(f"🔄 执行任务: {task_name}")
            result = await self.run_task(task_name, **task_kwargs)
            results.append((task_name, result))
            print(f"✅ 任务完成: {task_name}")
        return results

    def list_available_generators(self):
        """列出可用的生成器"""
        return self.registry.list_available()

    def list_available_tasks(self):
        """列出可用的任务"""
        return ["daily_blog", "user_recommendations"] + self.registry.list_available()

async def main():
    """主函数 - 支持命令行参数"""
    parser = argparse.ArgumentParser(description='PaperIgnition 统一编排器')
    parser.add_argument('--task', action='append', help='要执行的任务名称', default=[])
    parser.add_argument('--generator-type', help='生成器类型', default='storage')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--list-tasks', action='store_true', help='列出可用任务')
    parser.add_argument('--list-generators', action='store_true', help='列出可用生成器')
    
    args = parser.parse_args()
    
    orchestrator = PaperOrchestrator(args.config)
    
    if args.list_tasks:
        print("可用任务:")
        for task in orchestrator.list_available_tasks():
            print(f"  - {task}")
        return
    
    if args.list_generators:
        print("可用生成器:")
        for generator in orchestrator.list_available_generators():
            print(f"  - {generator}")
        return
    
    # 如果没有指定任务，使用默认任务
    tasks = args.task if args.task else ["daily_blog", "user_recommendations"]
    
    print(f"🚀 开始执行任务: {tasks}")
    
    for task in tasks:
        try:
            print(f"\n🔄 执行任务: {task}")
            if task == "daily_blog":
                result = await orchestrator.run_task(task, generator_type=args.generator_type)
            else:
                result = await orchestrator.run_task(task)
            print(f"✅ 任务完成: {task} - {result}")
        except Exception as e:
            print(f"❌ 任务失败: {task} - {e}")
            continue
    
    print("\n🎉 所有任务执行完成!")

if __name__ == "__main__":
    asyncio.run(main())