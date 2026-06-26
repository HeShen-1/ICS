"""Tests for app.rag.intent - classify_intent."""
from app.rag.intent import classify_intent, classify_intent_with_llm


class TestClassifyIntent:
    def test_classify_product_inquiry(self):
        assert classify_intent("这个产品有什么功能") == "产品咨询"
        assert classify_intent("价格是多少") == "产品咨询"
        assert classify_intent("能不能支持中文") == "产品咨询"

    def test_classify_after_sales(self):
        assert classify_intent("我想退货") == "售后问题"
        assert classify_intent("产品有故障怎么办") == "售后问题"
        assert classify_intent("报错了怎么处理") == "售后问题"

    def test_classify_complaint(self):
        assert classify_intent("我要投诉") == "投诉"
        assert classify_intent("客服态度太差") == "投诉"
        assert classify_intent("不满意的体验") == "投诉"

    def test_classify_chitchat(self):
        assert classify_intent("你好") == "闲聊"
        assert classify_intent("今天天气不错") == "闲聊"

    def test_classify_empty(self):
        # Empty string has no keywords -> chitchat
        result = classify_intent("")
        assert result == "闲聊"

    def test_classify_case_insensitive(self):
        # Intent classification should be case-insensitive
        result_upper = classify_intent("如何使USE功能")
        assert result_upper == "产品咨询"


class TestClassifyIntentWithLLM:
    def test_falls_back_to_keyword(self):
        # Without LLM client, it should fallback to keyword-based
        result = classify_intent_with_llm("价格查询", llm_client=None)
        assert result == "产品咨询"
