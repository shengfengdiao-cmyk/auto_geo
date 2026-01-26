# -*- coding: utf-8 -*-
import asyncio
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# 导入时区处理库 (通常系统自带，如果没有请运行 pip install pytz)
try:
    from pytz import timezone
except ImportError:
    timezone = None

from backend.services.geo_article_service import GeoArticleService
from backend.database.models import Keyword, Project


class SchedulerService:
    def __init__(self):
        # 1. 核心：初始化时直接锁定北京时区
        tz = timezone('Asia/Shanghai') if timezone else None
        self.scheduler = AsyncIOScheduler(timezone=tz)

        self.db_factory = None
        self.task_map = {
            "article_gen": self.execute_batch_geo_generation
        }

    def set_db_factory(self, db_factory):
        self.db_factory = db_factory

    def start(self):
        """确保引擎真正启动"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("🚀 定时任务引擎【北京时区】已打火启动！")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()

    async def run_task_immediately(self, task_type: str, params: Dict[str, Any]) -> List[str]:
        execution_logs = []
        handler = self.task_map.get(task_type)
        if not handler: return ["❌ 未定义任务类型"]
        try:
            await handler(params, execution_logs)
        except Exception as e:
            execution_logs.append(f"❌ 异常: {str(e)}")
        return execution_logs

    async def execute_batch_geo_generation(self, params: Dict[str, Any], log_collector: List[str] = None):
        project_id = params.get("project_id")
        count = params.get("count", 5)
        if not self.db_factory: return
        db = self.db_factory()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project: return
            keywords = db.query(Keyword).filter(Keyword.project_id == project_id, Keyword.status == "active").limit(
                count).all()
            service = GeoArticleService(db)
            for kw in keywords:
                res = await service.generate(kw.id, project.company_name)
                if log_collector is not None: log_collector.append(f"📝 {kw.keyword} -> {res.get('status')}")
        finally:
            db.close()

    def update_schedule(self, task_type: str, time_str: str, params: Dict[str, Any], enabled: bool):
        """更新排期并强制刷新"""
        # 确保在更新排期前，引擎是启动的
        self.start()

        job_id = f"job_{task_type}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        if enabled:
            h, m = time_str.split(":")
            # 锁定北京时区触发
            self.scheduler.add_job(
                self.task_map[task_type],
                CronTrigger(hour=int(h), minute=int(m), timezone=self.scheduler.timezone),
                id=job_id,
                args=[params],
                replace_existing=True
            )
            logger.info(f"📅 任务已排期：每天 {time_str}")

    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        # 强制更新一下 job 状态
        for job in self.scheduler.get_jobs():
            # 兼容性读取下一次运行时间
            next_run_dt = getattr(job, 'next_run_time', None)

            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run_dt.isoformat() if next_run_dt else "等待引擎计算...",
                "params": str(job.args[0]) if job.args else "{}"
            })
        return jobs


_instance = SchedulerService()


def get_scheduler_service(): return _instance