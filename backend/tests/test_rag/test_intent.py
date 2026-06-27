"""Tests for app.rag.intent - classify_intent."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.rag.intent import classify_intent, classify_intent_with_llm, _keyword_classify


class TestClassifyIntent:
    def test_classify_product_inquiry(self):
        assert _keyword_classify("这个产品有什么功能") == "产品咨询"
        assert _keyword_classify("价格是多少") == "产品咨询"
        assert _keyword_classify("能不能支持中文") == "产品咨询"

    def test_classify_after_sales(self):
        assert _keyword_classify("我想退货") == "售后问题"
        assert _keyword_classify("产品有故障怎么办") == "售后问题"
        assert _keyword_classify("报错了怎么处理") == "售后问题"

    def test_classify_complaint(self):
        assert _keyword_classify("我要投诉") == "投诉"
        assert _keyword_classify("客服态度太差") == "投诉"
        assert _keyword_classify("不满意的体验") == "投诉"

    def test_classify_chitchat(self):
        assert _keyword_classify("你好") == "闲聊"
        assert _keyword_classify("今天天气不错") == "闲聊"

    def test_classify_empty(self):
        result = _keyword_classify("")
        assert result == "闲聊"

    def test_classify_case_insensitive(self):
        result_upper = _keyword_classify("如何使USE功能")
        assert result_upper == "产品咨询"


class TestClassifyIntentWithLLM:
    @pytest.mark.asyncio
    @patch("app.rag.intent.AsyncOpenAI")
    async def test_llm_classify_product(self, mock_async_openai):
        mock_client = AsyncMock()
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="产品咨询"))
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_async_openai.return_value = mock_client

        with patch("app.rag.intent.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                deepseek_api_key="sk-test",
                deepseek_base_url="https://api.test.com",
                deepseek_model="test-model",
                llm_timeout=5,
            )
            result = await classify_intent("这个产品有什么功能")
            assert result == "产品咨询"

    @pytest.mark.asyncio
    @patch("app.rag.intent.AsyncOpenAI")
    async def test_llm_fallback_on_error(self, mock_async_openai):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
        mock_async_openai.return_value = mock_client

        with patch("app.rag.intent.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                deepseek_api_key="sk-test",
                deepseek_base_url="https://api.test.com",
                deepseek_model="test-model",
                llm_timeout=5,
            )
            result = await classify_intent("我想退货")
            assert result == "售后问题"  # keyword fallback

    @pytest.mark.asyncio
    @patch("app.rag.intent.get_settings")
    async def test_falls_back_to_keyword(self, mock_settings):
        mock_settings.return_value = MagicMock(
            deepseek_api_key="",  # no key → keyword fallback
            deepseek_base_url="",
            deepseek_model="",
            llm_timeout=5,
        )
        result = await classify_intent_with_llm("价格查询", llm_client=None)
        assert result == "产品咨询"
