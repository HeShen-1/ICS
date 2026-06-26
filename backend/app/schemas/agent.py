"""Agent 任务拆解相关 Schema"""
from pydantic import BaseModel, Field


class DecomposeRequest(BaseModel):
    """任务拆解请求"""

    requirement: str = Field(
        ...,
        max_length=2000,
        description="用户需求描述",
    )


class DecomposeTask(BaseModel):
    """单个拆解任务"""

    id: int = Field(..., description="任务唯一编号")
    service: str = Field(..., description="所属服务/模块名称")
    description: str = Field(..., description="任务描述")
    dependencies: list[int] = Field(default_factory=list, description="前置依赖任务 id 列表")


class DecomposeResponse(BaseModel):
    """任务拆解响应"""

    services: list[str] = Field(..., description="需要变更的服务列表")
    tasks: list[DecomposeTask] = Field(..., description="拆解后的任务列表")
    parallel_groups: list[list[int]] = Field(..., description="并行执行分组")
    explanation: str = Field(..., description="拆解方案说明")
