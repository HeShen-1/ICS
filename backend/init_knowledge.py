"""系统初始化：创建数据库表 + 默认知识库 + 批量入库示例文档 + 增量迁移"""
import sys
import os
import secrets
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
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
    """创建所有表 + 增量迁移"""
    Base.metadata.create_all(bind=engine)
    # 增量迁移: 为已有数据库添加新列
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE sessions ADD COLUMN pinned BOOLEAN DEFAULT 0"))
            conn.commit()
        except Exception:
            pass  # 列已存在
    print("✅ 数据库表创建/迁移完成")


def _ensure_system_user(db):
    """确保存在系统用户，返回 user_id"""
    from app.models.user import User
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = db.query(User).filter(User.phone == "00000000000").first()
    if not user:
        system_password = os.getenv("SYSTEM_USER_PASSWORD")
        if not system_password:
            system_password = secrets.token_urlsafe(12)
            print(f"[SECURITY] SYSTEM_USER_PASSWORD not set. Generated random password: {system_password}")
            print("[SECURITY] Save this password if system user login is needed (phone: 00000000000).")
        user = User(
            phone="00000000000",
            email="system@ics.local",
            password_hash=pwd_context.hash(system_password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user.id


def _ensure_knowledge_bases(db, user_id: int):
    """确保存在三个分类知识库，返回 {kb_name: kb_id}"""
    kb_defs = [
        ("产品知识库", "产品功能介绍、FAQ、技术支持、版本更新"),
        ("售后与服务", "退换货政策、售后流程"),
        ("法律条款", "隐私政策、用户协议"),
    ]
    kb_map = {}
    for name, desc in kb_defs:
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.user_id == user_id,
            KnowledgeBase.name == name,
        ).first()
        if not kb:
            kb = KnowledgeBase(user_id=user_id, name=name, description=desc)
            db.add(kb)
            db.commit()
            db.refresh(kb)
        kb_map[name] = kb
        print(f"📁 {name} (ID: {kb.id})")
    return kb_map


# 文档 → 知识库 分类映射
_DOC_KB_MAP = {
    "公司产品介绍.txt": "产品知识库",
    "常见问题FAQ.md": "产品知识库",
    "技术支持说明.md": "产品知识库",
    "版本更新日志.md": "产品知识库",
    "退换货政策.txt": "售后与服务",
    "隐私政策.txt": "法律条款",
    "用户协议.txt": "法律条款",
}


def init_knowledge():
    """批量入库示例文档，按分类存入对应知识库"""
    example_dir = os.path.join(os.path.dirname(__file__), "example_docs")
    if not os.path.isdir(example_dir):
        print("⚠️  example_docs 目录不存在，跳过知识库初始化")
        return

    from app.database import SessionLocal
    ingestion = DocumentIngestion()
    db = SessionLocal()

    try:
        system_user_id = _ensure_system_user(db)
        kb_map = _ensure_knowledge_bases(db, system_user_id)

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

            # 路由到对应知识库
            kb_name = _DOC_KB_MAP.get(filename)
            if kb_name is None:
                print(f"⏭️  未配置知识库分类: {filename}，跳过")
                continue
            kb = kb_map[kb_name]
            kb_id = str(kb.id)

            print(f"📄 处理: {filename} → {kb_name} ...")
            result = ingestion.ingest_file(file_path, kb_id=kb_id)

            # 保存文档记录到 MySQL
            doc = Document(
                user_id=system_user_id,
                kb_id=kb.id,
                name=filename,
                file_type=file_type,
                status=DocumentStatus.ready if result["success"] else DocumentStatus.failed,
                chunk_count=result["chunk_count"],
                file_size=os.path.getsize(file_path),
                file_path=file_path,
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
