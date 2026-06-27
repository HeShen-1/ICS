"""聊天 SSE 接口"""
import json
import logging
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.chat import ChatRequest
from app.services import session_service, chat_service

logger = logging.getLogger(__name__)
from app.rag.stream import generate_chat_stream
from app.rag.intent import classify_intent

router = APIRouter(prefix="/api/chat", tags=["聊天"])


def _strip_followup(text: str) -> str:
    """移除 LLM 输出的 [追问]... 标记, 追问内容通过 followup SSE 事件单独处理"""
    cleaned = re.sub(r"\n?\[追问\].*$", "", text, flags=re.DOTALL)
    return cleaned.strip()


@router.post("/{session_id}")
async def chat(
    session_id: int,
    req: ChatRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # 1. 校验会话归属
    session = session_service.get_session_detail(db, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 2. 校验问题
    error = chat_service.validate_question(req.content)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # 3. 原子地检查并增加每日提问次数
    if not chat_service.check_and_increment_daily_limit(db, user_id):
        raise HTTPException(status_code=429, detail="今日提问次数已达上限")

    # 4. 意图识别（先分类再保存消息）
    intent_tag = req.intent if req.intent else await classify_intent(req.content)

    # 5. 首条消息后自动更新会话标题 (取问题前10字)
    if session.title == "新会话" and len(session.messages) == 0:
        title = req.content.strip()[:10]
        if title:
            session_service.update_session(db, session_id, user_id, title=title)

    # 6. 保存用户消息
    session_service.create_message(db, session_id, "user", req.content, intent_tag=intent_tag)

    # 7. 获取历史消息
    messages = session_service.get_session_messages(db, session_id)
    history = [
        {"role": m.role.value, "content": m.content}
        for m in messages[:-1]  # 不包含刚保存的用户消息
    ]

    # 7. 返回 SSE 流
    async def event_stream():
        async for sse_str in generate_chat_stream(
            query=req.content,
            session_id=session_id,
            history_messages=history,
            intent_classify=False,
            intent_tag=intent_tag,
            kb_id=str(req.kb_id) if req.kb_id else None,
        ):
            # 拦截 done 事件: 先入库获取真实 message_id, 注入后 yield
            if "event: done" in sse_str:
                try:
                    data_str = sse_str.split("data: ")[1]
                    done_data = json.loads(data_str)
                    full_response = done_data.get("full_response", "")
                    references = done_data.get("references", [])

                    if full_response:
                        cleaned = _strip_followup(full_response)
                        msg = session_service.create_message(
                            db, session_id, "assistant", cleaned,
                            intent_tag=intent_tag, references=references,
                        )
                        done_data["message_id"] = msg.id
                        done_data["full_response"] = cleaned
                        sse_str = f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"
                except Exception:
                    logger.error("Failed to save assistant message for session %s", session_id, exc_info=True)
                    pass

            yield sse_str

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
