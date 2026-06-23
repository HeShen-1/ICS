"""知识库服务"""
import os
import uuid
from typing import List
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentStatus
from app.config import get_settings
from app.rag.ingestion import DocumentIngestion


def upload_document(db: Session, user_id: int, file_content: bytes, filename: str) -> Document:
    """上传并处理文档"""
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
        result = ingestion.ingest_file(file_path)

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


def list_documents(db: Session, user_id: int) -> List[Document]:
    return (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
        .all()
    )


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
