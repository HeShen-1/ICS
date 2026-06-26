"""系统初始化：创建数据库表 + 创建默认知识库 + 批量入库示例文档"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, Base
from app.models.user import User  # noqa: F401 — registers model with Base.metadata
from app.models.session import Session  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.feedback import Feedback  # noqa: F401
from app.models.knowledge_base import KnowledgeBase  # noqa: F401
from app.models.document import Document, DocumentStatus, FileType
from app.rag.ingestion import DocumentIngestion
from app.rag.vector_store import VectorStore


def init_database():
    """创建所有表"""
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建完成")


def _ensure_system_user(db):
    """确保存在系统用户，返回 user_id"""
    from app.models.user import User
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = db.query(User).filter(User.phone == "00000000000").first()
    if not user:
        user = User(
            phone="00000000000",
            email="system@ics.local",
            password_hash=pwd_context.hash("system"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user.id


def _ensure_default_kb(db, user_id: int) -> KnowledgeBase:
    """确保存在默认知识库，返回 kb_id"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.user_id == user_id,
        KnowledgeBase.name == "默认知识库",
    ).first()
    if not kb:
        kb = KnowledgeBase(
            user_id=user_id,
            name="默认知识库",
            description="系统默认知识库，用于存放示例文档",
        )
        db.add(kb)
        db.commit()
        db.refresh(kb)
    return kb


def init_knowledge():
    """批量入库示例文档"""
    example_dir = os.path.join(os.path.dirname(__file__), "example_docs")
    if not os.path.isdir(example_dir):
        print("⚠️  example_docs 目录不存在，跳过知识库初始化")
        return

    from app.database import SessionLocal
    ingestion = DocumentIngestion()
    db = SessionLocal()

    try:
        system_user_id = _ensure_system_user(db)
        default_kb = _ensure_default_kb(db, system_user_id)
        kb_id = str(default_kb.id)
        print(f"📁 使用知识库: {default_kb.name} (ID: {kb_id})")

        for filename in os.listdir(example_dir):
            file_path = os.path.join(example_dir, filename)
            if not os.path.isfile(file_path):
                continue

            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            try:
                file_type = FileType(ext)
            except ValueError:
                print(f"⏭️  跳过不支持的文件格式: {filename} (.{ext})")
                continue

            print(f"📄 处理: {filename} ...")
            result = ingestion.ingest_file(file_path, kb_id=kb_id)

            # 保存文档记录到 MySQL
            doc = Document(
                user_id=system_user_id,
                kb_id=default_kb.id,
                name=filename,
                file_type=file_type,
                status=DocumentStatus.ready if result["success"] else DocumentStatus.failed,
                chunk_count=result["chunk_count"],
                file_size=os.path.getsize(file_path),
                milvus_ids=result["milvus_ids"],
                error_msg=result["error"],
            )
            db.add(doc)
            db.commit()

            if result["success"]:
                print(f"   ✅ {result['chunk_count']} 个分块入库成功")
            else:
                print(f"   ❌ 失败: {result['error']}")
    finally:
        db.close()

    vs = VectorStore()
    print(f"\n📊 Milvus 向量总数: {vs.count()}")


if __name__ == "__main__":
    init_database()
    init_knowledge()
    print("\n🎉 初始化完成！")
