"""Tests for app.services.auth_service — token creation, verification, register, login."""
import pytest
from unittest.mock import patch, MagicMock
from app.services.auth_service import create_token, verify_token, hash_password, verify_password


class TestPasswordHashing:
    def test_hash_produces_bcrypt(self):
        result = hash_password("MyPass123!")
        assert result.startswith("$2b$") or result.startswith("$2a$")

    def test_verify_correct_password(self):
        hashed = hash_password("MyPass123!")
        assert verify_password("MyPass123!", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("MyPass123!")
        assert verify_password("WrongPass!", hashed) is False


class TestToken:
    def test_create_and_verify_token(self, monkeypatch):
        monkeypatch.setattr("app.services.auth_service.settings.jwt_secret_key",
                            "jwt-ci-dev-key-32chars-abcdefghX")
        monkeypatch.setattr("app.services.auth_service.settings.jwt_algorithm", "HS256")
        monkeypatch.setattr("app.services.auth_service.settings.jwt_expire_minutes", 1440)

        token = create_token(42)
        assert isinstance(token, str)

        user_id = verify_token(token)
        assert user_id == 42

    def test_verify_invalid_token_returns_none(self):
        result = verify_token("not.a.valid.token")
        assert result is None

    def test_verify_empty_token_returns_none(self):
        result = verify_token("")
        assert result is None

    def test_verify_none_token(self):
        with pytest.raises(Exception):
            verify_token(None)  # type: ignore — testing runtime behavior


class TestRegisterAndLogin:
    def test_register_duplicate_phone(self, test_db):
        from app.services.auth_service import register_user
        register_user(test_db, "13900000099", "TestPass1!")
        with pytest.raises(ValueError, match="已注册"):
            register_user(test_db, "13900000099", "TestPass1!")

    def test_login_success(self, test_db):
        from app.services.auth_service import register_user, login_user
        register_user(test_db, "13900000088", "TestPass1!")
        user, token = login_user(test_db, "13900000088", "TestPass1!")
        assert user.phone == "13900000088"
        assert isinstance(token, str)

    def test_login_wrong_password(self, test_db):
        from app.services.auth_service import register_user, login_user
        register_user(test_db, "13900000077", "TestPass1!")
        with pytest.raises(ValueError, match="错误"):
            login_user(test_db, "13900000077", "WrongPass1!")

    def test_login_nonexistent_user(self, test_db):
        from app.services.auth_service import login_user
        with pytest.raises(ValueError, match="错误"):
            login_user(test_db, "13999999999", "TestPass1!")
