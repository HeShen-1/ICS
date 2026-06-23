"""知识库接口"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.knowledge import DocumentOut, DocumentListResponse
from app.services import knowledge_service

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])

ALLOWED_EXTENSIONS = {"txt", "md", "pdf"}


@router.post("/upload", response_model=DocumentOut)
async def upload(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件格式: {ext}")

    content = await file.read()
    max_size = 10 * 1024 * 1024  # 10MB
    if len(content) > max_size:
        raise HTTPException(400, "文件大小不能超过 10MB")

    doc = knowledge_service.upload_document(db, content, file.filename)
    return DocumentOut(
        id=doc.id,
        name=doc.name,
        file_type=doc.file_type.value if hasattr(doc.file_type, 'value') else doc.file_type,
        status=doc.status.value if hasattr(doc.status, 'value') else doc.status,
        chunk_count=doc.chunk_count,
        file_size=doc.file_size,
        created_at=doc.created_at,
    )


@router.get("/list", response_model=DocumentListResponse)
def list_docs(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    docs = knowledge_service.list_documents(db)
    return DocumentListResponse(
        documents=[
            DocumentOut(
                id=d.id,
                name=d.name,
                file_type=d.file_type.value if hasattr(d.file_type, 'value') else d.file_type,
                status=d.status.value if hasattr(d.status, 'value') else d.status,
                chunk_count=d.chunk_count,
                file_size=d.file_size,
                created_at=d.created_at,
            )
            for d in docs
        ],
        total=len(docs),
    )


@router.delete("/{doc_id}")
def delete_doc(
    doc_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        knowledge_service.delete_document(db, doc_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
