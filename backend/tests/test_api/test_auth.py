"""Tests for /api/auth endpoints."""
import pytest


class TestRegister:
    def test_register_success(self, test_client):
        response = test_client.post(
            "/api/auth/register",
            json={"phone": "13800000011", "password": "Test1234!@"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user_id"] > 0
        assert data["message"] == "注册成功"

    def test_register_duplicate_phone(self, test_client):
        # First registration
        test_client.post(
            "/api/auth/register",
            json={"phone": "13800000012", "password": "Test1234!@"},
        )
        # Duplicate
        response = test_client.post(
            "/api/auth/register",
            json={"phone": "13800000012", "password": "Test1234!@"},
        )
        assert response.status_code == 400
        assert "已注册" in response.json()["detail"]

    def test_register_weak_password(self, test_client):
        response = test_client.post(
            "/api/auth/register",
            json={"phone": "13800000013", "password": "1234567"},
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_register_invalid_phone_format(self, test_client):
        response = test_client.post(
            "/api/auth/register",
            json={"phone": "12345", "password": "Test1234!@"},
        )
        assert response.status_code == 422  # Pydantic validation error


class TestLogin:
    def test_login_success(self, test_client):
        # Register first
        test_client.post(
            "/api/auth/register",
            json={"phone": "13800000014", "password": "Test1234!@"},
        )
        # Login
        response = test_client.post(
            "/api/auth/login",
            json={"account": "13800000014", "password": "Test1234!@"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "登录成功" in data["message"]

    def test_login_wrong_password(self, test_client):
        test_client.post(
            "/api/auth/register",
            json={"phone": "13800000015", "password": "Test1234!@"},
        )
        response = test_client.post(
            "/api/auth/login",
            json={"account": "13800000015", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "错误" in response.json()["detail"]

    def test_login_nonexistent_user(self, test_client):
        response = test_client.post(
            "/api/auth/login",
            json={"account": "13899999999", "password": "Test1234!@"},
        )
        assert response.status_code == 401
