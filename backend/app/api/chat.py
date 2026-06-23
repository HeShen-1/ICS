"""聊天 SSE 接口"""
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.chat import ChatRequest
from app.services import session_service, chat_service
from app.rag.stream import generate_chat_stream

router = APIRouter(prefix="/api/chat", tags=["聊天"])


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

    # 4. 保存用户消息
    session_service.create_message(db, session_id, "user", req.content)

    # 5. 获取历史消息
    messages = session_service.get_session_messages(db, session_id)
    history = [
        {"role": m.role.value, "content": m.content}
        for m in messages[:-1]  # 不包含刚保存的用户消息
    ]

    # 7. 返回 SSE 流
    async def event_stream():
        full_response = ""
        references = []

        async for sse_str in generate_chat_stream(
            query=req.content,
            session_id=session_id,
            history_messages=history,
        ):
            # 解析 done 事件获取完整回答和引用
            if 'event: done' in sse_str:
                try:
                    data_str = sse_str.split('data: ')[1]
                    done_data = json.loads(data_str)
                    full_response = done_data.get("full_response", "")
                    references = done_data.get("references", [])
                except Exception:
                    pass

            yield sse_str

        # 8. 保存 AI 回答到数据库
        if full_response:
            session_service.create_message(
                db,
                session_id,
                "assistant",
                full_response,
                references=references,
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
