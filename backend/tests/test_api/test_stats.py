"""Tests for /api/stats endpoints."""
import pytest


class TestDailyCount:
    def test_daily_count_zero_by_default(self, auth_headers, test_client):
        response = test_client.get("/api/stats/daily", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert data["count"] == 0


class TestOverview:
    def test_overview_stats(self, auth_headers, test_client):
        response = test_client.get("/api/stats/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_sessions" in data
        assert "total_messages" in data
        assert "total_documents" in data
        assert "feedback_positive_count" in data
        assert "feedback_negative_count" in data


class TestDailyTrend:
    def test_daily_trend_default(self, auth_headers, test_client):
        response = test_client.get("/api/stats/daily_trend", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for item in data:
            assert "date" in item
            assert "count" in item
