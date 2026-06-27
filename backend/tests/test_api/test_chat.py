"""Tests for /api/chat endpoints."""
import pytest


@pytest.fixture
def chat_session(auth_headers, test_client):
    """Create a chat session for testing."""
    r = test_client.post("/api/sessions", json={"title": "ChatTest"}, headers=auth_headers)
    return r.json()["id"]


class TestChatSSE:
    def test_chat_question_too_long(self, auth_headers, chat_session, test_client, monkeypatch):
        from app.config import Settings
        ts = Settings(
            mysql_host="localhost",
            mysql_user="test",
            mysql_password="test",
            mysql_database="test",
            deepseek_api_key="test-key",
            jwt_secret_key="jwt-ci-dev-key-32chars-abcdefghX",
            jwt_algorithm="HS256",
            jwt_expire_minutes=1440,
            upload_dir="/tmp/test_uploads",
            max_question_length=10,
            daily_question_limit=100,
            max_context_tokens=8000,
            max_history_rounds=5,
            top_k=5,
            similarity_threshold=0.65,
        )
        import app.services.chat_service as cs_mod
        monkeypatch.setattr(cs_mod, "get_settings", lambda: ts)

        response = test_client.post(
            f"/api/chat/{chat_session}",
            json={"content": "X" * 20},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "不能超过" in response.json()["detail"]

    def test_chat_daily_limit_exceeded(self, auth_headers, test_client, test_db, monkeypatch):
        """When daily limit is 0 and a record already exists with count=0, should reject."""
        from datetime import date
        from app.config import Settings
        import app.services.chat_service as cs_mod
        import app.rag.stream as stream_mod
        import app.rag.prompt as prompt_mod

        ts = Settings(
            mysql_host="localhost",
            mysql_user="test",
            mysql_password="test",
            mysql_database="test",
            deepseek_api_key="test-key",
            jwt_secret_key="jwt-ci-dev-key-32chars-abcdefghX",
            jwt_algorithm="HS256",
            jwt_expire_minutes=1440,
            upload_dir="/tmp/test_uploads",
            max_question_length=500,
            daily_question_limit=1,
            max_context_tokens=8000,
            max_history_rounds=5,
            top_k=5,
            similarity_threshold=0.65,
        )
        monkeypatch.setattr(cs_mod, "get_settings", lambda: ts)
        monkeypatch.setattr(stream_mod, "get_settings", lambda: ts)
        monkeypatch.setattr(prompt_mod, "get_settings", lambda: ts)

        # Pre-populate a record so that count >= limit
        from app.models.daily_question import DailyQuestionCount
        today = date.today()
        # Get the user_id from auth_headers - we need the actual user_id
        # Use the db directly to insert a limit-reaching record
        from app.models.user import User
        user = test_db.query(User).filter(User.phone == "13800000001").first()
        record = DailyQuestionCount(user_id=user.id, query_date=today, count=1)
        test_db.add(record)
        test_db.commit()

        # Create session
        r = test_client.post("/api/sessions", json={"title": "LimitTest"}, headers=auth_headers)
        session_id = r.json()["id"]

        response = test_client.post(
            f"/api/chat/{session_id}",
            json={"content": "hello"},
            headers=auth_headers,
        )
        assert response.status_code == 429

    def test_chat_sse_stream_mocked_llm(self, auth_headers, chat_session, test_client, monkeypatch):
        """Mock LLMClient.chat_stream to return fake tokens and verify SSE output."""
        import app.rag.llm as llm_mod
        import app.rag.retriever as retriever_mod

        # Mock LLM chat_stream
        async def _fake_chat_stream(self, messages):
            for token in ["Hello", ",", "this", "is", "test"]:
                yield token

        monkeypatch.setattr(llm_mod.LLMClient, "chat_stream", _fake_chat_stream)

        # Mock retriever search to return fake chunks
        def _fake_search(self, query, kb_id=None):
            return [
                {"source": "test.md", "text": "test knowledge content", "score": 0.95}
            ]

        def _fake_auto_route(self, query):
            return None

        monkeypatch.setattr(retriever_mod.Retriever, "search", _fake_search)
        monkeypatch.setattr(retriever_mod.Retriever, "auto_route", _fake_auto_route)

        response = test_client.post(
            f"/api/chat/{chat_session}",
            json={"content": "test question"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.text
        assert "event: token" in body or "test" in body

    def test_chat_session_not_found(self, auth_headers, test_client):
        response = test_client.post(
            "/api/chat/99999",
            json={"content": "hello"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_chat_requires_auth(self, test_client):
        response = test_client.post(
            "/api/chat/1",
            json={"content": "hello"},
        )
        assert response.status_code == 403
