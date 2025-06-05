from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional

from ..db.database import get_db

router = APIRouter(prefix="/papers", tags=["papers"])

# 论文模型
class PaperBase(BaseModel):
    id: str
    title: str
    authors: str
    abstract: str
    url: Optional[str] = None

class PaperDetail(PaperBase):
    markdownContent: str

# 模拟论文数据
MOCK_PAPERS = [
    {
        "id": "2023.12345",
        "title": "深度学习在自然语言处理中的应用",
        "authors": "张三, 李四, 王五",
        "abstract": "本文探讨了深度学习技术在自然语言处理领域的最新进展...",
        "url": "https://example.com/papers/2023.12345"
    },
    {
        "id": "2023.67890",
        "title": "计算机视觉中的注意力机制",
        "authors": "赵六, 钱七",
        "abstract": "注意力机制极大地提高了计算机视觉模型的性能...",
        "url": "https://example.com/papers/2023.67890"
    },
    {
        "id": "2023.24680",
        "title": "多模态大语言模型研究进展",
        "authors": "孙八, 周九, 吴十",
        "abstract": "多模态大语言模型将文本、图像等多种模态信息融合处理...",
        "url": "https://example.com/papers/2023.24680"
    }
]

# 论文详情Markdown内容
PAPER_CONTENT = {
    "2023.12345": """# 深度学习在自然语言处理中的应用

## 简介
深度学习技术已经彻底改变了自然语言处理领域。本文将探讨最新的研究进展以及未来发展方向。

## 主要内容
1. Transformer架构及其变体
2. 预训练语言模型（如BERT、GPT系列）
3. 多模态学习在NLP中的应用
4. 低资源语言的NLP技术

## 研究方法
本研究采用了对比实验的方法，在多个基准测试集上评估了不同模型的性能。

## 结论
研究表明，大规模预训练模型在多种NLP任务上表现出色，但在特定领域仍然需要针对性的优化。""",

    "2023.67890": """# 计算机视觉中的注意力机制

## 简介
注意力机制已成为计算机视觉模型中不可或缺的组件。本文综述了注意力机制在计算机视觉中的发展与应用。

## 主要内容
1. 空间注意力
2. 通道注意力
3. 自注意力机制
4. 跨模态注意力

## 研究方法
我们分析了近五年来发表的主要论文，并对不同类型的注意力机制进行了系统分类。

## 结论
注意力机制不仅提高了模型性能，还增强了模型的可解释性，是未来计算机视觉研究的重要方向。""",

    "2023.24680": """# 多模态大语言模型研究进展

## 简介
随着大语言模型的快速发展，多模态能力成为了当前研究热点。本文介绍了多模态大语言模型的最新进展。

## 主要内容
1. 视觉-语言预训练
2. 跨模态对齐技术
3. 多模态指令微调
4. 多模态应用案例

## 研究方法
我们对代表性多模态大模型（如GPT-4V, Claude 3, Gemini）进行了多维度评测和分析。

## 结论
多模态大语言模型极大拓展了AI系统的能力边界，但在模态间深度语义理解和推理方面仍有待提高。"""
}

@router.get("", response_model=List[PaperBase])
async def get_papers(domain_id: Optional[int] = None):
    """获取论文列表（模拟数据）"""
    # 简化实现，忽略domain_id参数
    return MOCK_PAPERS

@router.get("/{paper_id}", response_model=PaperDetail)
async def get_paper_detail(paper_id: str):
    """获取论文详情（模拟数据）"""
    # 查找论文基本信息
    paper = next((p for p in MOCK_PAPERS if p["id"] == paper_id), None)
    
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    
    # 添加Markdown内容
    paper_with_content = {**paper}
    paper_with_content["markdownContent"] = PAPER_CONTENT.get(paper_id, "# 论文内容暂未提供")
    
    return paper_with_content 