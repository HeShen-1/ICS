"""DeepSeek LLM 调用模块"""
import asyncio
from typing import List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.config import get_settings


class LLMClient:
    """DeepSeek API 封装（兼容 OpenAI SDK）"""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self.model = settings.deepseek_model
        self.timeout = settings.llm_timeout
        self.max_retries = 3
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens

    async def chat(
        self,
        messages: List[Dict],
        temperature: float | None = None,
        **kwargs: Any,
    ):
        """非流式调用 LLM，返回完整的 ChatCompletion 响应。

        Args:
            messages: 消息列表。
            temperature: 可选温度参数，不传则使用默认值。
            **kwargs: 透传给 chat.completions.create 的额外参数（如 response_format）。

        Returns:
            完整的 ChatCompletion 对象。

        Raises:
            RuntimeError: 所有重试均失败时抛出。
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature if temperature is not None else self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                    **kwargs,
                )
                return response

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
                    await asyncio.sleep(wait)
                continue

        raise RuntimeError(f"LLM 调用失败（已重试 {self.max_retries} 次）: {last_error}")

    async def chat_stream(
        self,
        messages: List[Dict],
    ) -> AsyncGenerator[str, None]:
        """流式调用 LLM，每次 yield 一个 token 文本"""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                )

                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

                return  # success

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
                    await asyncio.sleep(wait)
                continue

        raise RuntimeError(f"LLM 调用失败（已重试 {self.max_retries} 次）: {last_error}")
