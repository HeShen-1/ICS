"""Tests for /api/sessions endpoints."""
import pytest


class TestCreateSession:
    def test_create_session_default_title(self, auth_headers, test_client):
        response = test_client.post(
            "/api/sessions",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "新会话"
        assert data["status"] == "active"
        assert data["id"] > 0

    def test_create_session_custom_title(self, auth_headers, test_client):
        response = test_client.post(
            "/api/sessions",
            json={"title": "测试会话"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "测试会话"

    def test_create_session_requires_auth(self, test_client):
        response = test_client.post("/api/sessions", json={})
        assert response.status_code == 403  # Forbidden without auth


class TestListSessions:
    def test_list_sessions_empty(self, auth_headers, test_client):
        response = test_client.get("/api/sessions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data

    def test_list_sessions_with_data(self, auth_headers, test_client):
        # Create a session first
        test_client.post("/api/sessions", json={"title": "S1"}, headers=auth_headers)
        test_client.post("/api/sessions", json={"title": "S2"}, headers=auth_headers)

        response = test_client.get("/api/sessions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["sessions"]) == 2


class TestGetSessionDetail:
    def test_get_session_detail(self, auth_headers, test_client):
        # Create a session
        r = test_client.post("/api/sessions", json={"title": "详情测试"}, headers=auth_headers)
        session_id = r.json()["id"]

        response = test_client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "详情测试"
        assert "messages" in data

    def test_get_session_not_found(self, auth_headers, test_client):
        response = test_client.get("/api/sessions/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_cannot_access_other_user_session(self, test_client):
        """A second user should not see first user's sessions."""
        # User 1 creates session
        r1 = test_client.post(
            "/api/auth/register",
            json={"phone": "13900000001", "password": "Test1234!@"},
        )
        token1 = r1.json()["token"]
        h1 = {"Authorization": f"Bearer {token1}"}

        r_sess = test_client.post("/api/sessions", json={"title": "U1Session"}, headers=h1)
        sess_id = r_sess.json()["id"]

        # User 2 registers and tries to access U1's session
        r2 = test_client.post(
            "/api/auth/register",
            json={"phone": "13900000002", "password": "Test1234!@"},
        )
        token2 = r2.json()["token"]
        h2 = {"Authorization": f"Bearer {token2}"}

        response = test_client.get(f"/api/sessions/{sess_id}", headers=h2)
        assert response.status_code == 404
