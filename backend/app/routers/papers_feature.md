---
# Feature: Paper Recommendation & Content API

## Description
本模块提供学术论文推荐、内容获取与推荐记录保存的 API。  
- 支持根据用户获取推荐论文基础信息（paper_info）。
- 支持获取指定论文的 markdown 内容、自动生成的 blog 及推荐理由（paper_content, blog, recommendation_reason）。
- 支持保存用户论文推荐记录（包括所有推荐相关字段）到 UserPaperRecommendation 表。

## Entry Point
- `backend/app/routers/papers.py`
  - Function: `get_recommended_papers_info(username: str, db: AsyncSession)`
    - 检索UserPaperRecommendation 表, 返回指定用户的推荐论文基础信息列表（paper_info）
  - Function: `get_paper_markdown_content(paper_id: str)`
    - 检索UserPaperRecommendation 表, 返回指定论文的 markdown blog 及推荐理由 blog, recommendation_reason。
  - Function: `add_paper_recommendation(username: str, rec: PaperRecommendation, db: AsyncSession)`
    - 保存推荐记录到 UserPaperRecommendation 表，字段包括 userid, paperid, title, authors, abstract, url, blog, recommendation_reason。

## Linked Tests
- `tests/test_api_endpoints.py`::`test_get_recommended_papers_info`
- `tests/test_api_endpoints.py`::`test_get_paper_markdown_content`
- `tests/test_api_endpoints.py`::`test_add_paper_recommendation`

## Status
✅ Implemented  
✅ Unit-tested  
⬜ Integration-tested
--- 