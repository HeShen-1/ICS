"""Tests for /api/feedback endpoints."""
import pytest


class TestSubmitFeedback:
    def test_submit_positive_feedback(self, auth_headers, test_client, test_db):
        """Submit positive feedback on a message."""
        # Create session + messages first
        r = test_client.post("/api/sessions", json={"title": "FBTest"}, headers=auth_headers)
        assert r.status_code == 200
        session_id = r.json()["id"]

        # Chat to create a message (mocked)
        from app.services import session_service
        from app.services.auth_service import verify_token
        from app.database import get_db
        from app.config import get_settings

        # Manually insert a message
        token = auth_headers["Authorization"].split(" ")[1]
        user_id = verify_token(token)
        msg = session_service.create_message(test_db, session_id, "assistant", "测试回复")

        r = test_client.post(
            "/api/feedback",
            json={"message_id": msg.id, "rating": "positive"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["id"] > 0

    def test_submit_feedback_twice_updates(self, auth_headers, test_client, test_db):
        """Second submission should update, not duplicate."""
        from app.services import session_service
        from app.services.auth_service import verify_token

        r = test_client.post("/api/sessions", json={"title": "FBTest2"}, headers=auth_headers)
        session_id = r.json()["id"]

        token = auth_headers["Authorization"].split(" ")[1]
        user_id = verify_token(token)
        msg = session_service.create_message(test_db, session_id, "assistant", "回复")

        # First: positive
        test_client.post("/api/feedback", json={"message_id": msg.id, "rating": "positive"}, headers=auth_headers)

        # Second: negative (should update)
        r2 = test_client.post("/api/feedback", json={"message_id": msg.id, "rating": "negative"}, headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["id"] > 0

        # Verify only one row exists
        from app.models.feedback import Feedback
        count = test_db.query(Feedback).filter(Feedback.message_id == msg.id).count()
        assert count == 1

    def test_submit_feedback_requires_own_message(self, auth_headers, test_client, test_db):
        """Cannot submit feedback for another user's message."""
        # Register another user
        r2 = test_client.post("/api/auth/register", json={"phone": "13800000100", "password": "Test1234!@"})
        token2 = r2.json()["token"]
        h2 = {"Authorization": f"Bearer {token2}"}

        # User 1 creates message
        from app.services import session_service
        from app.services.auth_service import verify_token

        r = test_client.post("/api/sessions", json={"title": "FBTest3"}, headers=auth_headers)
        session_id = r.json()["id"]

        token = auth_headers["Authorization"].split(" ")[1]
        user_id = verify_token(token)
        msg = session_service.create_message(test_db, session_id, "assistant", "回复")

        # User 2 tries to submit feedback on User 1's message
        r3 = test_client.post(
            "/api/feedback",
            json={"message_id": msg.id, "rating": "positive"},
            headers=h2,
        )
        assert r3.status_code == 404 or r3.status_code == 403
