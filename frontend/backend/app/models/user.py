from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.database import Base

# 用户和研究领域的多对多关联表
user_domain_association = Table(
    'user_domain_association',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('domain_id', Integer, ForeignKey('research_domains.id'), primary_key=True)
)

class User(Base):
    """用户模型，存储用户基本信息"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(100), nullable=True)  # 为支持微信登录，密码可空
    
    # 微信相关字段
    wx_openid = Column(String(50), unique=True, index=True, nullable=True)
    wx_nickname = Column(String(50), nullable=True)
    wx_avatar_url = Column(String(255), nullable=True)
    wx_phone = Column(String(20), nullable=True)
    
    # 用户偏好
    push_frequency = Column(String(20), default="daily")  # daily, weekly
    
    # 元数据
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    interests_description = Column(Text, nullable=True)  # 用户自定义研究兴趣描述
    research_domains = relationship("ResearchDomain", secondary=user_domain_association, back_populates="users")
    favorite_papers = relationship("FavoritePaper", back_populates="user")


class ResearchDomain(Base):
    """研究领域模型，存储AI领域分类"""
    __tablename__ = "research_domains"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    code = Column(String(20), unique=True)  # 简短代码，如'NLP', 'CV'等
    description = Column(Text, nullable=True)
    
    # 关联关系
    users = relationship("User", secondary=user_domain_association, back_populates="research_domains")


class FavoritePaper(Base):
    """用户收藏的论文"""
    __tablename__ = "favorite_papers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    paper_id = Column(String(50), index=True)  # 论文外部ID (arXiv ID等)
    title = Column(String(255))
    authors = Column(String(255))
    abstract = Column(Text, nullable=True)
    url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    user = relationship("User", back_populates="favorite_papers") 