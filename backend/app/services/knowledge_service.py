"""知识库服务"""
import os
import uuid
from typing import List
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentStatus
from app.rag.ingestion import DocumentIngestion


def upload_document(db: Session, file_content: bytes, filename: str) -> Document:
    """上传并处理文档"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_name)

    with open(file_path, "wb") as f:
        f.write(file_content)

    file_size = len(file_content)

    doc = Document(
        name=filename,
        file_type=ext if ext in ("txt", "md", "pdf") else "txt",
        status=DocumentStatus.processing,
        file_size=file_size,
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


def list_documents(db: Session) -> List[Document]:
    return (
        db.query(Document)
        .order_by(Document.created_at.desc())
        .all()
    )


def delete_document(db: Session, doc_id: int):
    """删除文档及向量"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise ValueError("文档不存在")

    if doc.milvus_ids:
        from app.rag.vector_store import VectorStore
        vs = VectorStore()
        vs.delete_by_ids(doc.milvus_ids)

    db.delete(doc)
    db.commit()
