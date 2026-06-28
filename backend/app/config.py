from urllib.parse import quote_plus
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "ics_customer_service"

    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Embedding
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "cpu"

    # Milvus
    milvus_db_path: str = "./data/milvus/ics_knowledge.db"

    # JWT
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # LLM
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048
    llm_timeout: int = 30
    max_context_tokens: int = 8000

    # Embedding
    embedding_dimension: int = 1024

    # App
    upload_dir: str = "./data/uploads"
    max_question_length: int = 500
    daily_question_limit: int = 100
    top_k: int = 12
    similarity_threshold: float = 0.55
    max_history_rounds: int = 5
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    fallback_threshold: float = 0.35
    llm_max_retries: int = 3
    llm_rewrite_enabled: bool = True  # 检索前 LLM Query Rewriting
    prompt_injection_enabled: bool = True  # Prompt 注入检测
    company_name: str = "云智客服平台"

    # RAGAS 自动评估
    ragas_llm_model: str = "deepseek-chat"  # 评估用的 LLM 模型
    eval_retrieval_top_k: int = 12  # 评估时的检索 top_k
    eval_similarity_threshold: float = 0.55  # 评估时的相似度阈值

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        v_lower = v.lower()
        weak_patterns = ["change-me", "changeme", "secret", "password", "123456", "test"]
        if any(pattern in v_lower for pattern in weak_patterns):
            raise ValueError(
                "JWT_SECRET_KEY contains a weak/guessable pattern. "
                "Generate a strong random key with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return v

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{quote_plus(self.mysql_password)}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
