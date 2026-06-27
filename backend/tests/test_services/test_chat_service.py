"""Tests for app.services.chat_service."""
import pytest
from unittest.mock import patch
from datetime import date
from app.config import Settings
from app.services.chat_service import validate_question
from app.models.daily_question import DailyQuestionCount


def _test_settings():
    return Settings(
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
        daily_question_limit=100,
        max_context_tokens=8000,
        max_history_rounds=5,
        top_k=5,
        similarity_threshold=0.65,
    )


class TestValidateQuestion:
    def test_validate_question_ok(self, monkeypatch):
        ts = _test_settings()
        import app.services.chat_service as mod
        monkeypatch.setattr(mod, "get_settings", lambda: ts)
        assert validate_question("这是一个正常的问题") is None

    def test_validate_question_too_long(self, monkeypatch):
        ts = _test_settings()
        ts.max_question_length = 10
        import app.services.chat_service as mod
        monkeypatch.setattr(mod, "get_settings", lambda: ts)
        error = validate_question("X" * 20)
        assert error is not None
        assert "不能超过" in error

    def test_validate_question_empty(self, monkeypatch):
        ts = _test_settings()
        import app.services.chat_service as mod
        monkeypatch.setattr(mod, "get_settings", lambda: ts)
        error = validate_question("")
        assert error is not None
        assert "不能为空" in error

    def test_validate_question_whitespace_only(self, monkeypatch):
        ts = _test_settings()
        import app.services.chat_service as mod
        monkeypatch.setattr(mod, "get_settings", lambda: ts)
        error = validate_question("   ")
        assert error is not None
        assert "不能为空" in error


class TestDailyLimit:
    def test_check_daily_limit_under(self, test_db, monkeypatch):
        """First question of the day should pass."""
        from app.services.chat_service import check_and_increment_daily_limit

        ts = _test_settings()
        import app.services.chat_service as mod
        monkeypatch.setattr(mod, "get_settings", lambda: ts)

        # Need a user first
        from app.models.user import User
        user = User(phone="13800000002", password_hash="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        result = check_and_increment_daily_limit(test_db, user.id)
        assert result is True

        # Verify count was created
        today = date.today()
        record = (
            test_db.query(DailyQuestionCount)
            .filter(
                DailyQuestionCount.user_id == user.id,
                DailyQuestionCount.query_date == today,
            )
            .first()
        )
        assert record is not None
        assert record.count == 1

    def test_check_daily_limit_exceeded(self, test_db, monkeypatch):
        """When count reaches limit, should return False."""
        from app.services.chat_service import check_and_increment_daily_limit

        ts = _test_settings()
        ts.daily_question_limit = 3
        import app.services.chat_service as mod
        monkeypatch.setattr(mod, "get_settings", lambda: ts)

        from app.models.user import User
        user = User(phone="13800000003", password_hash="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        today = date.today()
        # Manually set count to limit
        record = DailyQuestionCount(user_id=user.id, query_date=today, count=3)
        test_db.add(record)
        test_db.commit()

        result = check_and_increment_daily_limit(test_db, user.id)
        assert result is False
