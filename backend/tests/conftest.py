"""Pytest fixtures for backend tests."""
import os
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Set env var BEFORE any app imports, since app.database calls get_settings()
# at module level which validates jwt_secret_key != "change-me"
os.environ.setdefault("JWT_SECRET_KEY", "pytest-test-secret-key")

TEST_DB_URL = "sqlite:///:memory:"


def _build_test_engine():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_fks(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture
def test_db():
    """Create a SQLite in-memory DB with all tables, yielding a session."""
    # Ensure all model tables are registered on Base metadata
    import app.models  # noqa: F401
    from app.database import Base

    engine = _build_test_engine()
    Base.metadata.create_all(bind=engine)

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _test_settings():
    from app.config import Settings
    return Settings(
        mysql_host="localhost",
        mysql_user="test",
        mysql_password="test",
        mysql_database="test",
        deepseek_api_key="test-key",
        jwt_secret_key="test-secret-key-not-change-me",
        jwt_algorithm="HS256",
        jwt_expire_minutes=1440,
        upload_dir="/tmp/test_uploads",
        max_question_length=500,
        daily_question_limit=100,
        max_context_tokens=8000,
        max_history_rounds=5,
        top_k=5,
        similarity_threshold=0.65,
        llm_timeout=30,
        llm_temperature=0.3,
        llm_max_tokens=2048,
    )


def _patch_get_settings(monkeypatch, settings):
    """Patch get_settings in all modules that import it."""
    import app.config
    monkeypatch.setattr(app.config, "get_settings", lambda: settings)

    import app.services.chat_service
    monkeypatch.setattr(app.services.chat_service, "get_settings", lambda: settings)

    import app.services.auth_service
    monkeypatch.setattr(app.services.auth_service, "get_settings", lambda: settings)

    import app.rag.prompt
    monkeypatch.setattr(app.rag.prompt, "get_settings", lambda: settings)

    import app.rag.stream
    monkeypatch.setattr(app.rag.stream, "get_settings", lambda: settings)

    import app.services.knowledge_service
    monkeypatch.setattr(app.services.knowledge_service, "get_settings", lambda: settings)

    import app.database
    monkeypatch.setattr(app.database, "get_settings", lambda: settings)


@pytest.fixture
def test_client(test_db, monkeypatch):
    """FastAPI TestClient with overridden get_db dependency."""
    test_settings = _test_settings()
    _patch_get_settings(monkeypatch, test_settings)

    # Ensure upload dir exists
    os.makedirs(test_settings.upload_dir, exist_ok=True)

    from app.main import app
    from app.database import get_db

    app.dependency_overrides[get_db] = lambda: test_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(test_client):
    """Register a test user and return Authorization header dict."""
    response = test_client.post(
        "/api/auth/register",
        json={"phone": "13800000001", "password": "test123456"},
    )
    assert response.status_code == 200, f"Register failed: {response.text}"
    data = response.json()
    return {"Authorization": f"Bearer {data['token']}"}
