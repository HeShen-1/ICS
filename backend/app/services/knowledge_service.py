"""知识库服务"""
import os
import uuid
from typing import List
from sqlalchemy.orm import Session, joinedload
from app.models.document import Document, DocumentStatus
from app.models.knowledge_base import KnowledgeBase
from app.config import get_settings
from app.rag.ingestion import DocumentIngestion


# ===================== 知识库 CRUD =====================

def create_kb(db: Session, user_id: int, name: str, description: str | None = None) -> KnowledgeBase:
    """创建知识库"""
    kb = KnowledgeBase(
        user_id=user_id,
        name=name,
        description=description,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


def get_kb_list(db: Session, user_id: int) -> List[KnowledgeBase]:
    """获取用户的知识库列表（预加载文档关系，避免 N+1）"""
    return (
        db.query(KnowledgeBase)
        .options(joinedload(KnowledgeBase.documents))
        .filter(KnowledgeBase.user_id == user_id)
        .order_by(KnowledgeBase.created_at.desc())
        .all()
    )


def update_kb(db: Session, kb_id: int, user_id: int, name: str | None = None, description: str | None = None) -> KnowledgeBase:
    """更新知识库"""
    kb = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id)
        .first()
    )
    if not kb:
        raise ValueError("知识库不存在")
    if name is not None:
        kb.name = name
    if description is not None:
        kb.description = description
    db.commit()
    db.refresh(kb)
    return kb


def delete_kb(db: Session, kb_id: int, user_id: int):
    """删除知识库, 同时删除关联文档及其 Milvus 向量"""
    kb = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id)
        .first()
    )
    if not kb:
        raise ValueError("知识库不存在")

    # 查询关联文档, 清理 Milvus 向量和磁盘文件
    docs = (
        db.query(Document)
        .filter(Document.kb_id == kb_id)
        .all()
    )
    for doc in docs:
        if doc.milvus_ids:
            from app.rag.vector_store import VectorStore
            vs = VectorStore()
            vs.delete_by_ids(doc.milvus_ids)
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        db.delete(doc)

    db.delete(kb)
    db.commit()


# ===================== 文档管理 =====================

def upload_document(db: Session, user_id: int, file_content: bytes, filename: str, kb_id: int | None = None) -> Document:
    """上传并处理文档

    Args:
        db: 数据库会话
        user_id: 用户 ID
        file_content: 文件内容
        filename: 原始文件名
        kb_id: 可选的知识库 ID
    """
    settings = get_settings()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = settings.upload_dir
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_name)

    with open(file_path, "wb") as f:
        f.write(file_content)

    file_size = len(file_content)

    doc = Document(
        user_id=user_id,
        kb_id=kb_id,
        name=filename,
        file_type=ext if ext in ("txt", "md", "pdf") else "txt",
        status=DocumentStatus.processing,
        file_size=file_size,
        file_path=file_path,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        ingestion = DocumentIngestion()
        result = ingestion.ingest_file(file_path, kb_id=str(kb_id) if kb_id else None, source_name=filename)

        if result["success"]:
            doc.status = DocumentStatus.ready
            doc.chunk_count = result["chunk_count"]
            doc.milvus_ids = result["milvus_ids"]
        else:
            doc.status = DocumentStatus.failed
            doc.error_msg = result["error"]
    except Exception as e:
        doc.status = DocumentStatus.failed
        doc.error_msg = str(e)

    db.commit()
    db.refresh(doc)
    return doc


def list_documents(db: Session, user_id: int, kb_id: int | None = None) -> List[Document]:
    """列出用户文档, 可按知识库过滤"""
    q = (
        db.query(Document)
        .filter(Document.user_id == user_id)
    )
    if kb_id is not None:
        q = q.filter(Document.kb_id == kb_id)
    return q.order_by(Document.created_at.desc()).all()


def delete_document(db: Session, doc_id: int, user_id: int):
    """删除文档及向量"""
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == user_id)
        .first()
    )
    if not doc:
        raise ValueError("文档不存在")

    if doc.milvus_ids:
        from app.rag.vector_store import VectorStore
        vs = VectorStore()
        vs.delete_by_ids(doc.milvus_ids)

    # 删除磁盘上的文件
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()


def get_document(db: Session, doc_id: int, user_id: int) -> Document:
    """获取单个文档, 校验所有权"""
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == user_id)
        .first()
    )
    if not doc:
        raise ValueError("文档不存在")
    return doc


def get_document_content(db: Session, doc_id: int, user_id: int) -> str:
    """读取文档文件内容"""
    doc = get_document(db, doc_id, user_id)
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise ValueError("文档文件不存在")
    with open(doc.file_path, "r", encoding="utf-8") as f:
        return f.read()
