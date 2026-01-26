# -*- coding: utf-8 -*-
"""
定时任务API
管理收录检测、文章生成及发布任务的定时配置与手动触发！
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks, Body, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.scheduler_service import get_scheduler_service
from backend.schemas import ApiResponse
from loguru import logger

router = APIRouter(prefix="/api/scheduler", tags=["定时任务"])


# ==================== 响应与请求模型 (满足输入输出一致性) ====================

class JobInfo(BaseModel):
    """任务运行信息"""
    id: str
    name: str
    next_run_time: str | None


class JobConfig(BaseModel):
    """任务配置模型"""
    enabled: bool = Field(..., description="是否启用")
    schedule_type: str = Field(..., description="调度类型: daily, interval, weekdays")
    time: str = Field(..., description="执行时间 HH:mm")
    project_id: Optional[int] = None
    count: Optional[int] = Field(5, description="每次生成的数量")
    platforms: Optional[List[str]] = ["zhihu"]
    concurrency: Optional[int] = 3


class JobConfigRequest(BaseModel):
    """批量任务配置请求"""
    article_gen: Optional[JobConfig] = None
    index_check: Optional[JobConfig] = None
    article_publish: Optional[JobConfig] = None


# 全局服务实例
_scheduler_service = None


def get_scheduler():
    """获取定时任务服务单例并初始化数据库工厂"""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = get_scheduler_service()
        # 设置数据库工厂，确保异步任务能正常开启DB Session
        _scheduler_service.set_db_factory(lambda: get_db().__next__())
    return _scheduler_service


# ==================== 定时任务配置存储 ====================
# 内存存储配置（正式环境建议后续迁移至数据库）
_job_configs: Dict[str, JobConfig] = {
    "article_gen": JobConfig(
        enabled=False,
        schedule_type="daily",
        time="09:00",
        count=5
    ),
    "index_check": JobConfig(
        enabled=True,
        schedule_type="daily",
        time="02:00",
        platforms=["doubao", "qianwen", "deepseek"],
        concurrency=3
    ),
    "article_publish": JobConfig(
        enabled=False,
        schedule_type="daily",
        time="10:00",
        platforms=["zhihu", "baijiahao"],
        count=3
    ),
}


# ==================== 辅助函数：同步配置到调度器 ====================

def sync_job_with_scheduler(job_type: str, config: JobConfig):
    """根据配置更新或移除 APScheduler 中的任务"""
    scheduler = get_scheduler()
    job_id = f"scheduled_{job_type}"

    # 如果禁用，则移除任务
    if not config.enabled:
        try:
            if scheduler.scheduler.get_job(job_id):
                scheduler.scheduler.remove_job(job_id)
                logger.info(f"已移除定时任务: {job_id}")
        except Exception as e:
            logger.error(f"移除任务失败: {e}")
        return

    # 如果启用，则添加或更新任务
    try:
        hour, minute = config.time.split(":")

        # 这里以 article_gen 为例，对接你刚在 service 里写的真逻辑
        if job_type == "article_gen":
            # 注意：实际场景中这里需要具体的 project_id 和 company_name
            # 演示环境下我们假设有默认逻辑或从配置读取
            scheduler.add_custom_geo_job(
                keyword_id=config.project_id or 0,
                company_name="AutoSystem",
                cron_time=config.time
            )
        elif job_type == "index_check":
            # 保持原有的每日检测逻辑更新
            from apscheduler.triggers.cron import CronTrigger
            scheduler.scheduler.add_job(
                scheduler.daily_index_check,
                CronTrigger(hour=int(hour), minute=int(minute)),
                id=job_id,
                replace_existing=True
            )
        logger.info(f"已同步调度配置: {job_type} -> {config.time}")
    except Exception as e:
        logger.error(f"同步任务到调度器失败: {e}")


# ==================== 定时任务API (满足前端展示需求) ====================

@router.get("/jobs", response_model=List[JobInfo])
async def get_scheduled_jobs():
    """获取当前所有活跃的定时任务列表"""
    scheduler = get_scheduler()
    return scheduler.get_scheduled_jobs()


@router.get("/config", response_model=Dict[str, JobConfig])
async def get_job_configs():
    """获取所有任务的参数配置"""
    return _job_configs


@router.post("/config", response_model=ApiResponse)
async def update_job_configs(data: JobConfigRequest):
    """更新全量任务配置，并实时同步到调度引擎"""
    global _job_configs
    try:
        for job_type in ["article_gen", "index_check", "article_publish"]:
            config = getattr(data, job_type)
            if config:
                _job_configs[job_type] = config
                sync_job_with_scheduler(job_type, config)

        return ApiResponse(success=True, message="任务配置已更新并同步")
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        return ApiResponse(success=False, message=f"更新失败: {str(e)}")


@router.post("/config/{job_type}", response_model=ApiResponse)
async def update_single_job_config(job_type: str, config: JobConfig):
    """更新单个特定任务（如仅修改生成时间）"""
    global _job_configs
    if job_type not in _job_configs:
        return ApiResponse(success=False, message=f"未知任务类型: {job_type}")

    try:
        _job_configs[job_type] = config
        sync_job_with_scheduler(job_type, config)
        return ApiResponse(success=True, message=f"{job_type} 配置已实时同步")
    except Exception as e:
        return ApiResponse(success=False, message=str(e))


# ==================== 触发器API (手动触发逻辑) ====================

@router.post("/trigger-check", response_model=ApiResponse)
async def trigger_index_check(background_tasks: BackgroundTasks):
    """手动立即执行：收录检测"""
    scheduler = get_scheduler()
    background_tasks.add_task(scheduler.trigger_check_now)
    return ApiResponse(success=True, message="收录检测任务已在后台启动")


@router.post("/trigger-article-gen", response_model=ApiResponse)
async def trigger_article_gen(
        project_id: int = Body(..., embed=True),
        company_name: str = Body("默认公司", embed=True),
        background_tasks: BackgroundTasks = None
):
    """
    手动立即执行：文章生成任务
    满足前辈要求的 API 接口设计：输入(project_id) -> 输出(ApiResponse)
    """
    scheduler = get_scheduler()
    # 调用 scheduler_service 中的真实异步生成逻辑
    background_tasks.add_task(
        scheduler.execute_geo_generation_workflow,
        project_id,
        company_name,
        "zhihu"
    )
    return ApiResponse(success=True, message=f"已为项目 {project_id} 启动文章生成流程")


@router.post("/trigger-alert", response_model=ApiResponse)
async def trigger_alert_check(background_tasks: BackgroundTasks):
    """手动立即执行：预警检查"""
    scheduler = get_scheduler()
    background_tasks.add_task(scheduler.trigger_alert_now)
    return ApiResponse(success=True, message="预警检查任务已触发")


# ==================== 服务控制API ====================

@router.get("/status")
async def get_scheduler_status():
    """获取调度服务运行状态，供前端看板显示"""
    scheduler = get_scheduler()
    return {
        "running": scheduler.scheduler.running if scheduler else False,
        "job_count": len(scheduler.get_scheduled_jobs()) if scheduler else 0,
        "current_time": datetime.now().isoformat(),
        "configs": _job_configs
    }


@router.post("/start", response_model=ApiResponse)
async def start_scheduler():
    """手动启动调度服务"""
    scheduler = get_scheduler()
    if scheduler.scheduler.running:
        return ApiResponse(success=True, message="定时任务服务已在运行")
    scheduler.start()
    return ApiResponse(success=True, message="服务启动成功")


@router.post("/stop", response_model=ApiResponse)
async def stop_scheduler():
    """手动停止调度服务"""
    scheduler = get_scheduler()
    scheduler.stop()
    return ApiResponse(success=True, message="服务已安全停止")