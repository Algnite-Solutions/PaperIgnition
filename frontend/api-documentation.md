# PaperIgnition API 文档

本文档介绍了PaperIgnition项目已实现的API接口、功能以及工作流程，方便团队成员理解和使用系统。

## 项目概述

PaperIgnition是一个学术论文推荐系统，前端为微信小程序，后端使用FastAPI框架开发。该系统旨在帮助用户发现和推荐与其研究兴趣相关的学术论文。

## 系统架构

- **前端**：微信小程序
- **后端**：FastAPI (Python)
- **数据库**：PostgreSQL（使用异步连接）

## 数据库模型

### 用户 (User)

```
- id: 主键
- username: 用户名
- email: 邮箱（可为空）
- hashed_password: 哈希密码（可为空，支持微信登录）
- wx_openid: 微信OpenID
- wx_nickname: 微信昵称
- wx_avatar_url: 微信头像URL
- wx_phone: 微信手机号
- push_frequency: 推送频率（每日/每周）
- is_active: 是否活跃
- is_verified: 是否已验证
- created_at: 创建时间
- updated_at: 更新时间
- interests_description: 用户研究兴趣关键词数组
```

### 研究领域 (ResearchDomain)

```
- id: 主键
- name: 名称
- code: 简短代码（如'NLP', 'CV'等）
- description: 描述
```

### 收藏论文 (FavoritePaper)

```
- id: 主键
- user_id: 用户ID
- paper_id: 论文ID（外部ID，如arXiv ID）
- title: 标题
- authors: 作者
- abstract: 摘要
- url: URL
- created_at: 创建时间
```

## API接口

### 1. 认证接口

#### 1.1 邮箱注册
- **URL**: `/api/auth/register-email`
- **方法**: POST
- **功能**: 用户通过邮箱密码注册
- **请求体**:
  ```json
  {
    "email": "user@example.com",
    "password": "password123",
    "username": "username"
  }
  ```
- **响应**:
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "username": "username"
  }
  ```

#### 1.2 邮箱登录
- **URL**: `/api/auth/login-email`
- **方法**: POST
- **功能**: 用户通过邮箱密码登录
- **请求体**:
  ```json
  {
    "email": "user@example.com",
    "password": "password123"
  }
  ```
- **响应**:
  ```json
  {
    "access_token": "token...",
    "token_type": "bearer",
    "needs_interest_setup": true,
    "user_info": {
      "email": "user@example.com",
      "username": "username"
    }
  }
  ```

#### 1.3 用户名登录
- **URL**: `/api/auth/login`
- **方法**: POST
- **功能**: 用户通过用户名密码登录
- **请求体**:
  ```json
  {
    "username": "username",
    "password": "password123"
  }
  ```
- **响应**:
  ```json
  {
    "access_token": "token...",
    "token_type": "bearer"
  }
  ```

#### 1.4 微信登录
- **URL**: `/api/auth/wechat_login`
- **方法**: POST
- **功能**: 微信小程序登录
- **请求体**:
  ```json
  {
    "code": "wx_code"
  }
  ```
- **响应**:
  ```json
  {
    "access_token": "token...",
    "token_type": "bearer",
    "needs_interest_setup": true,
    "user_info": {
      "email": "wx_user@example.com",
      "username": "wx_username"
    }
  }
  ```

### 2. 用户接口

#### 2.1 获取当前用户信息
- **URL**: `/api/users/me`
- **方法**: GET
- **功能**: 获取当前用户信息
- **参数**: username (Query)
- **响应**:
  ```json
  {
    "id": 1,
    "username": "username",
    "email": "user@example.com",
    "is_active": true,
    "interests_description": ["AI", "机器学习"],
    "research_domain_ids": [1, 2]
  }
  ```

#### 2.2 更新用户研究兴趣
- **URL**: `/api/users/interests`
- **方法**: POST
- **功能**: 更新用户研究兴趣
- **参数**: username (Query)
- **请求体**:
  ```json
  {
    "research_domain_ids": [1, 2, 3],
    "interests_description": ["AI", "机器学习", "深度学习"]
  }
  ```
- **响应**:
  ```json
  {
    "id": 1,
    "username": "username",
    "email": "user@example.com",
    "is_active": true,
    "interests_description": ["AI", "机器学习", "深度学习"],
    "research_domain_ids": [1, 2, 3]
  }
  ```

#### 2.3 获取研究领域列表
- **URL**: `/api/users/research_domains`
- **方法**: GET
- **功能**: 获取所有研究领域列表
- **响应**:
  ```json
  [
    {
      "id": 1,
      "name": "自然语言处理"
    },
    {
      "id": 2,
      "name": "计算机视觉"
    },
    ...
  ]
  ```

#### 2.4 更新用户个人资料
- **URL**: `/api/users/me/profile`
- **方法**: PUT
- **功能**: 更新当前用户的个人资料
- **请求体**:
  ```json
  {
    "email": "new_email@example.com",
    "push_frequency": "weekly",
    "interests_description": ["AI", "NLP"],
    "research_domain_ids": [1, 4]
  }
  ```
- **响应**: 更新后的用户信息



## 数据库相关文件

### 1. database.py

数据库连接配置文件，负责创建与PostgreSQL数据库的异步连接。

### 2. init_db.py

数据库初始化文件，负责创建数据表并添加初始数据。

### 3. run_init_db.py

独立脚本，用于手动触发数据库初始化过程。

**使用方法:**

```bash
python -m backend.run_init_db
```







## 完整使用流程

### 1. 环境配置

#### 1.1 后端环境

1. 安装Python 3.8+

2. 安装PostgreSQL 12+

3. 创建虚拟环境并安装依赖:

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

#### 1.2 前端环境

1. 安装Node.js和pnpm

### 2. 数据库初始化

1. 创建PostgreSQL数据库:

   ```bash
   createdb AIgnite
   ```

2. 初始化数据库表和预填充数据:

   ```bash
   cd backend
   python run_init_db.py
   ```

### 3. 启动后端服务

1. 在虚拟环境中启动FastAPI服务:

   ```bash
   cd backend
   # 开发环境
   uvicorn app.main:app --reload --port 8000
   # 生产环境
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

### 4. 运行前端

```
cd frontend
pnpm run dev:h5
```

### 5. 用户注册与登录

#### 5.1 邮箱注册

1. 前端访问 `/api/auth/register-email` 接口
2. 提交用户信息（邮箱、密码、用户名）
3. 获取注册成功响应
4. 使用注册的邮箱和密码登录

#### 5.2 邮箱登录

1. 前端访问 `/api/auth/login-email` 接口
2. 提交邮箱和密码
3. 获取访问令牌（token）
4. 检查是否需要设置研究兴趣（`needs_interest_setup`）
5. 如需设置，跳转到兴趣设置页面

#### 5.4 设置研究兴趣

1. 获取研究领域列表（`/api/users/research_domains`）
2. 用户选择感兴趣的领域和关键词
3. 提交到 `/api/users/interests` 接口
4. 完成初始设置，进入主界面

### 6. 论文浏览流程

1. 主界面加载论文列表（`/api/papers`）
2. 用户可以根据研究领域筛选论文
3. 点击论文查看详情（`/api/papers/{paper_id}`）
4. 用户可以保存/收藏感兴趣的论文
