# -*- coding: utf-8 -*-
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.database.models import ScheduledTask
from backend.services.scheduler_service import get_scheduler_service
from backend.schemas import ApiResponse

router = APIRouter(prefix="/api/scheduler", tags=["定时任务管理"])


# --- Schema ---
class TaskUpdate(BaseModel):
    cron_expression: str
    is_active: bool


class TaskResponse(BaseModel):
    id: int
    name: str
    task_key: str
    cron_expression: str
    is_active: bool
    description: Optional[str] = None

    class Config:
        from_attributes = True


# --- API ---

@router.get("/jobs", response_model=List[TaskResponse])
async def list_jobs(db: Session = Depends(get_db)):
    """获取所有定时任务配置"""
    return db.query(ScheduledTask).all()


@router.put("/jobs/{task_id}", response_model=ApiResponse)
async def update_job(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    """更新任务配置（Cron或开关）"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        return ApiResponse(success=False, message="任务不存在")

    # 更新数据库
    task.cron_expression = data.cron_expression
    task.is_active = data.is_active
    db.commit()

    # 🌟 关键：通知调度器热重载该任务
    scheduler = get_scheduler_service()
    scheduler.reload_task(task_id)

    return ApiResponse(success=True, message="任务配置已更新并生效")