# AIgnite 后端API文档

## 数据库结构

### 1. 用户表 (users)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | 整数 | 主键 |
| username | 字符串(50) | 用户名(唯一) |
| email | 字符串(100) | 电子邮件(唯一，可选) |
| hashed_password | 字符串(100) | 哈希密码(用于传统登录，可选) |
| wx_openid | 字符串(50) | 微信OpenID(唯一，可选) |
| wx_nickname | 字符串(50) | 微信昵称 |
| wx_avatar_url | 字符串(255) | 微信头像URL |
| wx_phone | 字符串(20) | 微信绑定手机号 |
| push_frequency | 字符串(20) | 推送频率(默认"daily") |
| is_active | 布尔值 | 账户是否激活 |
| is_verified | 布尔值 | 账户是否已验证 |
| created_at | 日期时间 | 创建时间 |
| updated_at | 日期时间 | 更新时间 |
| interests_description | 字符串数组 | 用户研究兴趣关键词数组 |

### 2. 研究领域表 (research_domains)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | 整数 | 主键 |
| name | 字符串(100) | 领域名称(唯一) |
| code | 字符串(20) | 领域代码(唯一，如'NLP','CV') |
| description | 文本 | 领域描述 |

### 3. 用户-研究领域关联表 (user_domain_association)

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | 整数 | 用户ID，外键 |
| domain_id | 整数 | 研究领域ID，外键 |

**作用**: 实现用户与研究领域的多对多关系

### 4. 收藏论文表 (favorite_papers) 

1. 目前可能用不上
2. 应该和郭老师的论文数据表关联，这样我这边就不需要建表了，以下仅供参考

| 字段 | 类型 | 说明 |
|------|------|------|
| id | 整数 | 主键 |
| user_id | 整数 | 用户ID，外键 |
| paper_id | 字符串(50) | 论文外部ID(如arXiv ID) |
| title | 字符串(255) | 论文标题 |
| authors | 字符串(255) | 论文作者 |
| abstract | 文本 | 论文摘要 |
| url | 字符串(255) | 论文URL |
| created_at | 日期时间 | 创建时间 |

## 数据结构变更

### interests_description 字段从文本到数组的迁移

在v1.1版本中，我们将用户的兴趣描述字段从单一文本改为字符串数组，以便更好地存储和查询多个关键词。
若要运行此迁移，请执行以下命令：

```bash
python run_migrations.py
```

迁移过程会：
1. 创建临时列保存原始文本数据
2. 将原字段类型更改为字符串数组
3. 使用逗号分隔符拆分原始文本数据并转换为数组
4. 删除临时列

## API端点

目前前后端需要以下这些api接口，但是我没有完全实现

1. user表

   用户注册

   用户登录

   获取当前用户信息

   获取所有研究领域

   更新用户研究兴趣

2. paper表

   获取论文详情

   获取论文列表

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/auth/register` | POST | 用户注册 |
| `/api/auth/login` | POST | 用户登录 |
| `/api/domains` | GET | 获取所有研究领域 |
| `/api/users/me` | GET | 获取当前用户信息 |
| `/api/users/interests` | POST | 更新用户研究兴趣 |
| `/api/papers` | GET | 获取论文列表 |
| `/api/papers/{paper_id}` | GET | 获取论文详情 |

## 数据格式示例

### 用户兴趣更新

请求:
```json
{
  "research_domain_ids": [1, 3, 5],
  "interests_description": ["机器学习", "深度学习", "自然语言处理", "计算机视觉"]
}
```

响应:
```json
{
  "id": 1,
  "username": "user123",
  "email": "user@example.com",
  "is_active": true,
  "interests_description": ["机器学习", "深度学习", "自然语言处理", "计算机视觉"],
  "research_domain_ids": [1, 3, 5]
}
```