# -*- coding: utf-8 -*-
"""清理 MySQL 旧文档 + 重新初始化

Milvus 数据目录需手动删除 (Windows 下 drop_collection 有 manifest.json.tmp bug):
  rm -rf data/milvus/ics_knowledge.db
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models.document import Document

print("Deleting old document records from MySQL...")
db = SessionLocal()
count = db.query(Document).delete()
db.commit()
db.close()
print(f"  Deleted {count} records.")

print("\nRe-initializing...")
import init_knowledge
init_knowledge.init_database()
init_knowledge.init_knowledge()
print("\nDone.")
