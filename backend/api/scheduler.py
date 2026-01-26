# -*- coding: utf-8 -*-
"""
定时任务API中心
对接前端控制面板，支持立即执行、配置保存和排期查询。
"""

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# 导入业务服务层
from backend.services.scheduler_service import get_scheduler_service
from backend.database import get_db
from backend.schemas import ApiResponse
from loguru import logger

router = APIRouter(prefix="/api/scheduler", tags=["定时任务中心"])


# ==================== 数据模型 (匹配前端UI需求) ====================

class JobInfo(BaseModel):
    """用于展示给前端的任务排期信息"""
    id: str
    name: str
    next_run: Optional[str] = None  # 统一使用 next_run
    params: Optional[str] = None


class TaskConfigPayload(BaseModel):
    """适配 UI 上的配置卡片数据包"""
    enabled: bool = Field(..., description="开关状态")
    time: str = Field(..., description="执行时间，格式 HH:mm")
    project_id: Optional[int] = Field(None, description="目标项目ID")
    count: int = Field(5, description="生成数量")
    task_type: str = Field("article_gen", description="任务类型标识")


# ==================== 服务单例管理 ====================

_scheduler_service = None


def get_scheduler():
    """获取并确保调度引擎已打火启动"""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = get_scheduler_service()
        # 设置数据库工厂，供后台任务开启 Session
        _scheduler_service.set_db_factory(lambda: next(get_db()))

    # 🌟 关键：确保每次调用 API 时引擎都是 Start 状态
    _scheduler_service.start()
    return _scheduler_service


# ==================== 接口实现 ====================

@router.get("/jobs", response_model=List[JobInfo])
async def get_all_jobs():
    """
    获取任务列表
    用于验证‘定时时间’是否成功进入调度引擎排班
    """
    service = get_scheduler()
    try:
        jobs = service.get_scheduled_jobs()
        return jobs
    except Exception as e:
        logger.error(f"查询任务排期失败: {e}")
        raise HTTPException(status_code=500, detail="调度引擎数据读取异常")


@router.post("/config/article_gen", response_model=ApiResponse)
async def save_article_gen_config(payload: TaskConfigPayload):
    """
    保存配置：对应前端卡片的‘开关’和‘保存’动作。
    """
    service = get_scheduler()

    try:
        # 封装参数
        params = {
            "project_id": payload.project_id,
            "count": payload.count
        }

        # 同步更新 APScheduler 中的定时计划
        service.update_schedule(
            task_type=payload.task_type,
            time_str=payload.time,
            params=params,
            enabled=payload.enabled
        )

        msg = f"配置成功！任务已{'挂载排期' if payload.enabled else '从引擎卸载'}"
        return ApiResponse(
            success=True,
            message=msg,
            data={"target_time": payload.time}
        )
    except Exception as e:
        logger.error(f"保存任务配置失败: {e}")
        return ApiResponse(success=False, message=f"配置保存异常: {str(e)}")


@router.post("/trigger-article-gen", response_model=ApiResponse)
async def trigger_article_gen_manually(
        project_id: int = Body(..., embed=True),
        count: int = Body(5, embed=True),
        task_type: str = Body("article_gen", embed=True)
):
    """
    立即运行一次：点击后后台批量执行，并返回执行日志响应。
    """
    service = get_scheduler()

    # 构造即时运行参数
    params = {"project_id": project_id, "count": count}

    # 获取实时执行日志
    logs = await service.run_task_immediately(task_type, params)

    return ApiResponse(
        success=True,
        message="立即执行指令已完成",
        data={"logs": logs},  # 将重要的日志响应返回给前端展示
        timestamp=datetime.now().isoformat()
    )


@router.get("/status")
async def get_scheduler_status():
    """获取引擎整体运行状态"""
    service = get_scheduler()
    return {
        "engine_running": service.scheduler.running,
        "timezone": str(service.scheduler.timezone),
        "job_count": len(service.scheduler.get_jobs()),
        "server_time": datetime.now().isoformat()
    }