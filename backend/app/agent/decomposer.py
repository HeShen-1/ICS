"""任务拆解器 — 加载系统文档 + 调用 LLM 生成任务拆解方案"""
import json
import logging
from pathlib import Path

from app.agent.prompt import DECOMPOSE_SYSTEM_PROMPT
from app.rag.llm import LLMClient

# 项目根目录 (backend/ 的父目录)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = _PROJECT_ROOT / "docs"

logger = logging.getLogger(__name__)


class TaskDecomposer:
    """结合系统文档和 LLM 进行需求任务拆解"""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        """初始化拆解器。

        Args:
            llm_client: 可选的 LLM 客户端实例，不传则自动创建。
        """
        self.llm = llm_client or LLMClient()

    def _load_docs(self) -> str:
        """加载 docs/ 目录下所有 .md 文件，拼接为上下文文本。

        Returns:
            拼接后的文档内容，每篇文档以文件名作为标题头。
        """
        parts: list[str] = []

        for md_file in sorted(DOCS_DIR.rglob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
                relative_path = md_file.relative_to(DOCS_DIR)
                parts.append(f"# {relative_path}\n\n{content}\n")
            except Exception:
                logger.warning("Failed to read doc %s", md_file, exc_info=True)
                continue

        return "\n---\n".join(parts)

    async def decompose(self, requirement: str) -> dict:
        """根据用户需求拆解任务。

        Args:
            requirement: 用户需求描述文本。

        Returns:
            包含 services, tasks, parallel_groups, explanation 的字典。

        Raises:
            ValueError: LLM 返回的 JSON 格式无效或缺少必要字段。
            RuntimeError: LLM 调用失败。
        """
        docs_text = self._load_docs()

        messages = [
            {"role": "system", "content": DECOMPOSE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"## 系统文档\n\n{docs_text}\n\n## 用户需求\n\n{requirement}",
            },
        ]

        try:
            response = await self.llm.chat(
                messages=messages,
                temperature=0,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"LLM 调用失败: {e}") from e

        raw_text = response.choices[0].message.content or ""

        # 解析 JSON
        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error("LLM returned invalid JSON. Raw response: %s", raw_text)
            raise ValueError("LLM 返回格式异常，请重试") from e

        # 校验必要字段
        required_fields = ["services", "tasks", "parallel_groups", "explanation"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"LLM 响应缺少必要字段 '{field}'。响应: {result}")

        return result
