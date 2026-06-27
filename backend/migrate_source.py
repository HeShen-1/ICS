"""数据迁移脚本: 修复 Milvus 中 source 字段
问题: 入库时 source 用了 UUID 文件名 (abc123.txt), 但查询时用 doc.name (产品介绍.txt), 不匹配
修复: 对每个 ready 文档, 删旧向量, 用 doc.name 作为 source 重新入库
"""
import sys
import os
import io

# 确保 backend 在 sys.path 中
sys.path.insert(0, os.path.dirname(__file__))

# Windows: 强制 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.rag.vector_store import VectorStore
from app.rag.ingestion import DocumentIngestion


def migrate():
    db = SessionLocal()
    vs = VectorStore()
    ingestion = DocumentIngestion()

    docs = db.query(Document).filter(Document.status == DocumentStatus.ready).all()
    print(f"找到 {len(docs)} 个 ready 文档")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for doc in docs:
        print(f"\n--- 文档 [{doc.id}] {doc.name} (user_id={doc.user_id}, kb_id={doc.kb_id}) ---")

        if not doc.file_path or not os.path.exists(doc.file_path):
            print(f"  [SKIP] 文件不存在: {doc.file_path}")
            skip_count += 1
            continue

        # 1. 删除旧 Milvus 向量
        if doc.milvus_ids:
            print(f"  删除旧向量: {len(doc.milvus_ids)} 条")
            vs.delete_by_ids(doc.milvus_ids)
        else:
            print(f"  无旧向量记录")

        # 2. 用 doc.name 作为 source 重新入库
        try:
            kb_id = str(doc.kb_id) if doc.kb_id else None
            result = ingestion.ingest_file(doc.file_path, kb_id=kb_id, source_name=doc.name)

            if result["success"]:
                doc.chunk_count = result["chunk_count"]
                doc.milvus_ids = result["milvus_ids"]
                print(f"  [OK] 重新入库成功: {result['chunk_count']} 块")
                success_count += 1
            else:
                print(f"  [FAIL] 入库失败: {result['error']}")
                fail_count += 1
        except Exception as e:
            print(f"  [FAIL] 异常: {e}")
            fail_count += 1

    db.commit()
    db.close()
    print(f"\n{'='*50}")
    print(f"迁移完成: 成功={success_count}, 跳过={skip_count}, 失败={fail_count}")


if __name__ == "__main__":
    migrate()
