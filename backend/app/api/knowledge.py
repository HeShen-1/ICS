"""知识库接口"""
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from app.config import get_settings

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.knowledge import (
    DocumentOut,
    DocumentListResponse,
    DocumentContentOut,
    ChunkOut,
    DocumentChunksOut,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseOut,
    KnowledgeBaseListResponse,
)
from app.services import knowledge_service

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])

ALLOWED_EXTENSIONS = {"txt", "md", "pdf"}


def _doc_to_out(doc) -> DocumentOut:
    """将 Document ORM 对象转为 DocumentOut"""
    return DocumentOut(
        id=doc.id,
        name=doc.name,
        file_type=doc.file_type.value if hasattr(doc.file_type, 'value') else doc.file_type,
        status=doc.status.value if hasattr(doc.status, 'value') else doc.status,
        chunk_count=doc.chunk_count,
        file_size=doc.file_size,
        kb_id=doc.kb_id,
        kb_name=doc.kb.name if doc.kb else None,
        created_at=doc.created_at,
    )


# ===================== 知识库 CRUD =====================

@router.post("/bases", response_model=KnowledgeBaseOut)
def create_knowledge_base(
    body: KnowledgeBaseCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """创建知识库"""
    kb = knowledge_service.create_kb(db, user_id, body.name, body.description)
    return KnowledgeBaseOut(
        id=kb.id,
        user_id=kb.user_id,
        name=kb.name,
        description=kb.description,
        document_count=0,
        created_at=kb.created_at,
    )


@router.get("/bases", response_model=KnowledgeBaseListResponse)
def list_knowledge_bases(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """获取知识库列表"""
    kbs = knowledge_service.get_kb_list(db, user_id)
    return KnowledgeBaseListResponse(
        knowledge_bases=[
            KnowledgeBaseOut(
                id=k.id,
                user_id=k.user_id,
                name=k.name,
                description=k.description,
                document_count=len(k.documents),
                created_at=k.created_at,
            )
            for k in kbs
        ],
        total=len(kbs),
    )


@router.put("/bases/{kb_id}", response_model=KnowledgeBaseOut)
def update_knowledge_base(
    kb_id: int,
    body: KnowledgeBaseUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """更新知识库"""
    try:
        kb = knowledge_service.update_kb(db, kb_id, user_id, body.name, body.description)
        return KnowledgeBaseOut(
            id=kb.id,
            user_id=kb.user_id,
            name=kb.name,
            description=kb.description,
            document_count=len(kb.documents),
            created_at=kb.created_at,
        )
    except ValueError as e:
        raise HTTPException(404, detail=str(e))


@router.delete("/bases/{kb_id}")
def delete_knowledge_base(
    kb_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """删除知识库"""
    try:
        knowledge_service.delete_kb(db, kb_id, user_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(404, detail=str(e))


# ===================== 文档管理 =====================

@router.post("/upload", response_model=DocumentOut)
async def upload(
    file: UploadFile = File(...),
    kb_id: int | None = Form(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """上传文档"""
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件格式: {ext}")

    content = await file.read()
    max_size = get_settings().max_upload_size
    if len(content) > max_size:
        raise HTTPException(400, "文件大小不能超过 10MB")

    doc = knowledge_service.upload_document(db, user_id, content, file.filename, kb_id=kb_id)
    return _doc_to_out(doc)


@router.get("/list", response_model=DocumentListResponse)
def list_docs(
    kb_id: int | None = Query(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出文档, 可按知识库过滤"""
    docs = knowledge_service.list_documents(db, user_id, kb_id=kb_id)
    return DocumentListResponse(
        documents=[_doc_to_out(d) for d in docs],
        total=len(docs),
    )


@router.get("/{doc_id}/content", response_model=DocumentContentOut)
def get_doc_content(
    doc_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """获取文档原始内容"""
    try:
        doc = knowledge_service.get_document(db, doc_id, user_id)
        content = knowledge_service.get_document_content(db, doc_id, user_id)
        return DocumentContentOut(id=doc.id, name=doc.name, content=content)
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        logger.error("Failed to read document content for doc_id=%s: %s", doc_id, e, exc_info=True)
        raise HTTPException(500, detail="读取文档失败，请稍后重试")


@router.get("/{doc_id}/chunks", response_model=DocumentChunksOut)
def get_doc_chunks(
    doc_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """获取文档的所有分块"""
    try:
        doc = knowledge_service.get_document(db, doc_id, user_id)
    except ValueError as e:
        raise HTTPException(404, detail=str(e))

    from app.rag.vector_store import VectorStore
    vs = VectorStore()
    kb_id_str = str(doc.kb_id) if doc.kb_id else None
    chunks = vs.query_by_source(doc.name, kb_id=kb_id_str)

    return DocumentChunksOut(
        id=doc.id,
        name=doc.name,
        chunks=[
            ChunkOut(chunk_index=c["chunk_index"], text=c["text"], source=c["source"])
            for c in chunks
        ],
    )


@router.delete("/{doc_id}")
def delete_doc(
    doc_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """删除文档"""
    try:
        knowledge_service.delete_document(db, doc_id, user_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
