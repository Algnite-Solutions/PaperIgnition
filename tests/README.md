# PaperIgnition 测试文档

本目录包含针对 PaperIgnition 项目的测试代码。测试涵盖了后端API、索引服务和前端功能。

## 测试结构

- `test_api_endpoints.py` - 测试原有API端点
- `test_user_endpoints.py` - 测试用户相关API端点
- `test_paper_endpoints.py` - 测试论文相关API端点
- `test_index_service.py` - 测试论文索引服务
- `test_frontend.py` - 测试前端功能（使用Selenium）
- `run_tests.py` - 运行所有测试的主脚本

## 运行测试

### 安装依赖

```bash
pip install pytest httpx pytest-asyncio selenium
```

### 运行所有测试

```bash
python tests/run_tests.py
```

### 运行特定类型的测试

```bash
# 运行API测试
python tests/run_tests.py --test-type api

# 运行索引服务测试
python tests/run_tests.py --test-type index

# 运行前端测试
python tests/run_tests.py --test-type frontend
```

## 测试配置

在运行测试前，请确保：

1. 后端API服务运行在 `http://localhost:8000`
2. 索引服务运行在 `http://localhost:8001`
3. 前端Web版（如果有）运行在 `http://localhost:3000`

如需修改测试配置，请编辑相应测试文件中的 `BASE_URL`、`INDEX_API_URL` 或 `FRONTEND_URL` 常量。

## 测试数据

测试使用以下测试账户：

- 邮箱：`test_user@example.com`
- 密码：`TestPassword123`
- 用户名：`test_user`

## 注意事项

1. 前端测试基于Selenium，需要安装相应的WebDriver
2. 微信小程序前端测试需要在特定测试环境中运行，当前的前端测试主要针对Web版本
3. 部分测试可能会创建临时文件，测试完成后会自动清理
4. 索引服务测试可能需要较长时间，特别是在首次索引论文时 