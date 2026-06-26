"""Agent 任务拆解接口"""
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user_id
from app.schemas.agent import DecomposeRequest, DecomposeResponse, DecomposeTask
from app.agent.decomposer import TaskDecomposer

router = APIRouter(prefix="/api/agent", tags=["Agent 任务拆解"])

# 模块级单例，复用 LLM 连接
_decomposer = TaskDecomposer()


@router.post("/decompose", response_model=DecomposeResponse)
async def decompose_requirement(
    req: DecomposeRequest,
    user_id: int = Depends(get_current_user_id),
) -> DecomposeResponse:
    """分析用户需求，拆解为微服务任务列表。

    Args:
        req: 包含 requirement 字段的请求体。
        user_id: 当前认证用户 ID（由 JWT 中间件注入）。

    Returns:
        包含 services, tasks, parallel_groups, explanation 的响应。
    """
    if not req.requirement.strip():
        raise HTTPException(status_code=400, detail="需求描述不能为空")

    try:
        result = await _decomposer.decompose(req.requirement)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return DecomposeResponse(
        services=result["services"],
        tasks=[DecomposeTask(**t) for t in result["tasks"]],
        parallel_groups=result["parallel_groups"],
        explanation=result["explanation"],
    )
