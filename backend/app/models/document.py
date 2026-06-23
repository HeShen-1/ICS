"""知识库文档模型"""
import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, JSON

from app.database import Base


class DocumentStatus(enum.Enum):
    processing = "processing"
    ready = "ready"
    failed = "failed"


class FileType(enum.Enum):
    txt = "txt"
    md = "md"
    pdf = "pdf"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="文档ID")
    name = Column(String(255), nullable=False, comment="文档名称")
    file_type = Column(Enum(FileType), nullable=False, comment="文件格式")
    status = Column(Enum(DocumentStatus), default=DocumentStatus.processing, comment="处理状态")
    chunk_count = Column(Integer, default=0, comment="分块数量")
    file_size = Column(Integer, default=0, comment="文件大小(bytes)")
    milvus_ids = Column(JSON, nullable=True, comment="Milvus向量ID数组")
    error_msg = Column(Text, nullable=True, comment="失败原因")
    created_at = Column(DateTime, default=datetime.utcnow, comment="上传时间")
