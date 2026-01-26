# -*- coding: utf-8 -*-
"""
定时任务服务
管理收录检测、GEO文章自动生成及其他自动化任务！
"""

import asyncio
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

# 导入公司现有的配置和服务
from backend.config import INDEX_CHECK_HOUR, INDEX_CHECK_MINUTE
from backend.services.index_check_service import IndexCheckService
from backend.services.geo_article_service import GeoArticleService  # 你要对接的真零件
from backend.services.notification_service import get_notification_service, WebSocketNotificationChannel
from backend.database.models import Keyword, Project, IndexCheckRecord


class SchedulerService:
    """
    定时任务服务
    负责管理系统所有的自动化任务（收录检测 + GEO文章生成）
    """

    def __init__(self):
        """初始化定时任务服务"""
        self.scheduler = AsyncIOScheduler()
        self.db_factory = None
        self.ws_callback = None

    def set_db_factory(self, db_factory):
        """设置数据库工厂（由 main.py 初始化时传入）"""
        self.db_factory = db_factory

    def set_ws_callback(self, callback: Callable):
        """设置WebSocket回调"""
        self.ws_callback = callback

    def start(self):
        """启动定时任务系统"""
        # 1. 原有任务：每日收录检测
        self.scheduler.add_job(
            self.daily_index_check,
            CronTrigger(hour=INDEX_CHECK_HOUR, minute=INDEX_CHECK_MINUTE),
            id="daily_index_check",
            name="每日收录检测",
            replace_existing=True
        )

        # 2. 原有任务：每日预警检查
        alert_hour = (INDEX_CHECK_HOUR + 1) % 24
        self.scheduler.add_job(
            self.daily_alert_check,
            CronTrigger(hour=alert_hour, minute=INDEX_CHECK_MINUTE),
            id="daily_alert_check",
            name="每日预警检查",
            replace_existing=True
        )

        # 3. 原有任务：失败重试（每6小时）
        self.scheduler.add_job(
            self.retry_failed_checks,
            CronTrigger(hour="*/6"),
            id="retry_failed_checks",
            name="失败重试任务",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info(f"🚀 定时任务服务已启动！")
        logger.info(f"📅 默认收录检测设定为: {INDEX_CHECK_HOUR:02d}:{INDEX_CHECK_MINUTE:02d}")

    def stop(self):
        """停止定时任务"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("定时任务服务已停止")

    # ==========================================
    # 新增功能：GEO文章自动生成调度逻辑
    # ==========================================

    async def add_custom_geo_job(self, keyword_id: int, company_name: str, cron_time: str, platform: str = "zhihu"):
        """
        核心方法：动态添加一个自定义时间的GEO生成任务
        满足前辈要求的“自定义设置”和“API调用参数修改”

        Args:
            keyword_id: 关键词ID
            company_name: 公司名
            cron_time: 时间格式 "HH:mm" (如 "10:30")
            platform: 发布平台
        """
        try:
            hour, minute = cron_time.split(":")
            job_id = f"geo_gen_{keyword_id}"

            # 使用 Cron 触发器实现“每天准点运行”
            job = self.scheduler.add_job(
                self.execute_geo_generation_workflow,
                CronTrigger(hour=int(hour), minute=int(minute)),
                id=job_id,
                name=f"GEO自动生成-{company_name}",
                args=[keyword_id, company_name, platform],
                replace_existing=True
            )

            logger.info(f"✨ 已成功排期新任务: {job_id}，运行时间: {cron_time}")
            return job
        except Exception as e:
            logger.error(f"添加调度任务失败: {e}")
            raise e

    async def execute_geo_generation_workflow(self, keyword_id: int, company_name: str, platform: str):
        """
        真正被定时触发的文章生成流程
        """
        logger.info(f"🔔 定时器唤醒：准备为 [{company_name}] 生成关键词ID为 {keyword_id} 的GEO文章")

        if not self.db_factory:
            logger.error("数据库工厂缺失，无法执行生成任务")
            return

        db = self.db_factory()
        try:
            # 实例化前辈写的核心生成服务
            article_service = GeoArticleService(db)

            # 1. 执行生成逻辑（对接 n8n）
            result = await article_service.generate(
                keyword_id=keyword_id,
                company_name=company_name,
                platform=platform
            )

            if result.get("status") == "success":
                logger.info(f"✅ 定时生成成功！文章ID: {result.get('article_id')}")

                # 2. 自动触发质检逻辑
                await article_service.check_quality(result.get("article_id"))

                # 发送实时进度通知到前端
                if self.ws_callback:
                    await self.ws_callback({
                        "type": "geo_gen_success",
                        "data": {"keyword_id": keyword_id, "title": result.get("title")}
                    })
            else:
                logger.error(f"❌ 定时生成失败: {result.get('message')}")

        except Exception as e:
            logger.error(f"GEO调度流程执行异常: {e}")
        finally:
            db.close()

    # ==========================================
    # 原有功能：收录检测与预警 (保持不变以防报错)
    # ==========================================

    async def daily_index_check(self):
        """每日收录检测任务"""
        logger.info("开始执行每日收录检测任务")
        if not self.db_factory: return
        db = self.db_factory()
        try:
            service = IndexCheckService(db)
            projects = db.query(Project).filter(Project.status == 1).all()
            for project in projects:
                keywords = db.query(Keyword).filter(Keyword.project_id == project.id, Keyword.status == "active").all()
                for keyword in keywords:
                    results = await service.check_keyword(keyword_id=keyword.id, company_name=project.company_name)
                    if self.ws_callback:
                        await self.ws_callback({"type": "index_check_progress", "data": {"keyword": keyword.keyword}})
            logger.info("每日收录检测任务完成")
        except Exception as e:
            logger.error(f"检测任务失败: {e}")
        finally:
            db.close()

    async def daily_alert_check(self):
        """每日预警检查任务"""
        logger.info("开始执行每日预警检查任务")
        if not self.db_factory: return
        db = self.db_factory()
        try:
            notification_service = get_notification_service(db)
            if self.ws_callback:
                notification_service.add_channel(WebSocketNotificationChannel(self.ws_callback))
            await notification_service.check_and_alert()
        finally:
            db.close()

    async def retry_failed_checks(self):
        """失败重试任务"""
        logger.info("开始执行失败重试任务")
        if not self.db_factory: return
        db = self.db_factory()
        try:
            service = IndexCheckService(db)
            yesterday = datetime.now().replace(hour=0, minute=0, second=0)
            keywords = db.query(Keyword).filter(Keyword.status == "active").all()
            for keyword in keywords:
                latest = db.query(IndexCheckRecord).filter(IndexCheckRecord.keyword_id == keyword.id).order_by(
                    IndexCheckRecord.check_time.desc()).first()
                if not latest or latest.check_time < yesterday:
                    project = db.query(Project).filter(Project.id == keyword.project_id).first()
                    if project: await service.check_keyword(keyword.id, project.company_name)
        finally:
            db.close()

    def get_scheduled_jobs(self) -> list[Dict[str, Any]]:
        """获取当前所有排期的定时任务（用于前端展示）"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs


# ==========================================
# 单例管理（对外暴露的接口）
# ==========================================

scheduler_service: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    global scheduler_service
    if scheduler_service is None:
        scheduler_service = SchedulerService()
    return scheduler_service