# -*- coding: utf-8 -*-
"""
收录检测服务 - v5.0 物理模拟版
用这个来检测AI平台的收录情况！

v5.0 增强：
1. 参考 toutiao.py 的物理模拟精神
2. 详细 logger.info 用于 Electron 前端实时追踪
3. 使用 secure_session_manager 从数据库加载存储状态
4. 自动登录检测与提示
"""

from typing import List, Dict, Any, Optional
from loguru import logger
from sqlalchemy.orm import Session
from playwright.async_api import async_playwright, Browser
import asyncio
from datetime import datetime

from backend.database.models import IndexCheckRecord, Keyword, QuestionVariant, Project
from backend.config import AI_PLATFORMS
from backend.services.playwright.ai_platforms import DoubaoChecker, QianwenChecker, DeepSeekChecker


class IndexCheckService:
    """
    收录检测服务 - v5.0 物理模拟版

    v5.0 增强：
    - 参考物理模拟精神
    - 详细日志追踪
    - 会话状态管理
    """

    def __init__(self, db: Session):
        """
        初始化收录检测服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.checkers = {
            "doubao": DoubaoChecker("doubao", AI_PLATFORMS["doubao"]),
            "qianwen": QianwenChecker("qianwen", AI_PLATFORMS["qianwen"]),
            "deepseek": DeepSeekChecker("deepseek", AI_PLATFORMS["deepseek"]),
        }

    async def check_keyword(
        self,
        keyword_id: int,
        company_name: str,
        platforms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        检测关键词在所有AI平台的收录情况

        Args:
            keyword_id: 关键词ID
            company_name: 公司名称
            platforms: 要检测的平台列表，默认全部

        Returns:
            检测结果列表
        """
        # 获取关键词信息
        keyword_obj = self.db.query(Keyword).filter(Keyword.id == keyword_id).first()
        if not keyword_obj:
            logger.error(f"[IndexCheck] 关键词不存在: {keyword_id}")
            return []

        logger.info(f"[IndexCheck] 开始检测关键词: {keyword_obj.keyword}, 公司: {company_name}")

        # 获取问题变体
        questions = self.db.query(QuestionVariant).filter(
            QuestionVariant.keyword_id == keyword_id
        ).all()

        if not questions:
            # 如果没有问题变体，使用默认问题
            questions = [QuestionVariant(
                id=0,
                keyword_id=keyword_id,
                question=f"什么是{keyword_obj.keyword}？推荐哪家公司？"
            )]
            logger.info(f"[IndexCheck] 使用默认问题: {questions[0].question}")

        # 确定要检测的平台
        if platforms is None:
            platforms = list(self.checkers.keys())

        logger.info(f"[IndexCheck] 检测平台: {platforms}, 问题数量: {len(questions)}")

        results = await self._execute_checks(
            keyword_id=keyword_id,
            keyword_obj=keyword_obj,
            questions=questions,
            company_name=company_name,
            platforms=platforms
        )

        logger.info(f"[IndexCheck] 收录检测完成: 关键词ID={keyword_id}, 检测数={len(results)}")
        return results

    async def check_project_keywords(
        self,
        project_id: int,
        platforms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        批量检测项目下所有关键词的收录情况

        Args:
            project_id: 项目ID
            platforms: 要检测的平台列表，默认全部

        Returns:
            检测结果列表
        """
        # 获取项目信息
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error(f"[IndexCheck] 项目不存在: {project_id}")
            return []

        logger.info(f"[IndexCheck] 开始检测项目: {project.name}, 公司: {project.company_name}")

        # 获取项目下所有关键词
        keywords = self.db.query(Keyword).filter(
            Keyword.project_id == project_id
        ).all()

        if not keywords:
            logger.error(f"[IndexCheck] 项目下没有关键词: {project_id}")
            return []

        all_results = []

        # 确定要检测的平台
        if platforms is None:
            platforms = list(self.checkers.keys())

        logger.info(f"[IndexCheck] 项目关键词数量: {len(keywords)}, 检测平台: {platforms}")

        # 使用单个Playwright实例处理所有关键词，提高效率
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])

            try:
                for keyword_obj in keywords:
                    logger.info(f"[IndexCheck] 检测关键词 ({keywords.index(keyword_obj) + 1}/{len(keywords)}): {keyword_obj.keyword}")

                    # 获取关键词的问题变体
                    questions = self.db.query(QuestionVariant).filter(
                        QuestionVariant.keyword_id == keyword_obj.id
                    ).all()

                    if not questions:
                        # 如果没有问题变体，使用默认问题
                        questions = [QuestionVariant(
                            id=0,
                            keyword_id=keyword_obj.id,
                            question=f"什么是{keyword_obj.keyword}？推荐哪家公司？"
                        )]

                    # 执行检测
                    results = await self._execute_checks(
                        keyword_id=keyword_obj.id,
                        keyword_obj=keyword_obj,
                        questions=questions,
                        company_name=project.company_name,
                        platforms=platforms,
                        browser=browser  # 传入共享的浏览器实例
                    )

                    all_results.extend(results)

                    # 短暂休息，避免被平台检测为自动化
                    await asyncio.sleep(2)

            finally:
                await browser.close()

        logger.info(f"[IndexCheck] 项目关键词批量检测完成: 项目ID={project_id}, 关键词数={len(keywords)}, 检测数={len(all_results)}")
        return all_results

    async def _execute_checks(
        self,
        keyword_id: int,
        keyword_obj: Keyword,
        questions: List[QuestionVariant],
        company_name: str,
        platforms: List[str],
        browser: Optional[Browser] = None
    ) -> List[Dict[str, Any]]:
        """
        执行检测的通用方法

        v5.0 增强：
        - 支持共享浏览器实例（提高效率）
        - 物理模拟用户登录
        - 详细日志追踪
        """
        results = []

        # 临时使用固定的用户ID和项目ID，实际应该从参数传递
        user_id = 1
        project_id = 1

        # 导入会话管理器
        from backend.services.session_manager import secure_session_manager
        # 导入UTC时间处理
        from datetime import datetime, timezone, timedelta

        # 如果没有提供浏览器，创建新的
        should_close_browser = browser is None
        if browser is None:
            p = await async_playwright().start()
            browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])

        try:
            # 为每个平台创建一个新的上下文和页面
            for platform_id in platforms:
                checker = self.checkers.get(platform_id)
                if not checker:
                    logger.warning(f"[IndexCheck] 未知的平台: {platform_id}")
                    continue

                logger.info(f"[IndexCheck] 开始检测平台: {checker.name}, 关键词: {keyword_obj.keyword}")

                # 加载平台的存储状态（授权状态）
                logger.info(f"[IndexCheck] 加载平台 {checker.name} 的存储状态...")
                storage_state = await secure_session_manager.load_session(
                    user_id=user_id,
                    project_id=project_id,
                    platform=platform_id,
                    validate=False
                )

                if storage_state:
                    logger.info(f"[IndexCheck] 成功加载平台 {checker.name} 的存储状态")
                else:
                    logger.warning(f"[IndexCheck] 未找到平台 {checker.name} 的存储状态，将使用新的会话")

                # 为每个平台创建新的上下文和页面
                context = await browser.new_context(storage_state=storage_state)
                page = await context.new_page()

                try:
                    # 执行单个平台的检测
                    platform_results = await self._execute_checks_for_single_platform(
                        keyword_id=keyword_id,
                        keyword_obj=keyword_obj,
                        questions=questions,
                        company_name=company_name,
                        platform_id=platform_id,
                        checker=checker,
                        page=page
                    )
                    results.extend(platform_results)

                    # 保存更新后的会话状态（如果登录状态发生了变化）
                    logger.info(f"[IndexCheck] 保存平台 {checker.name} 的更新会话状态...")
                    updated_storage_state = await context.storage_state()
                    # 保留原始会话中的时间戳信息
                    if storage_state:
                        updated_storage_state["created_at"] = storage_state.get("created_at")
                        updated_storage_state["last_modified"] = storage_state.get("last_modified")
                    save_result = await secure_session_manager.save_session(
                        user_id=user_id,
                        project_id=project_id,
                        platform=platform_id,
                        storage_state=updated_storage_state
                    )
                    if save_result:
                        logger.info(f"[IndexCheck] 成功保存平台 {checker.name} 的更新会话状态")
                    else:
                        logger.warning(f"[IndexCheck] 保存平台 {checker.name} 的更新会话状态失败")
                finally:
                    # 等待一段时间后再关闭上下文，让用户有时间看到结果
                    await asyncio.sleep(2)
                    await context.close()

        finally:
            # 如果是我们创建的浏览器，关闭它
            if should_close_browser:
                await browser.close()

        return results

    async def _execute_checks_for_single_platform(
        self,
        keyword_id: int,
        keyword_obj: Keyword,
        questions: List[QuestionVariant],
        company_name: str,
        platform_id: str,
        checker: Any,
        page: Any
    ) -> List[Dict[str, Any]]:
        """
        为单个平台执行检测

        v5.0 增强：
        - 详细日志追踪
        - 物理模拟用户行为
        - 健壮性重试机制
        """
        results = []
        max_retries = 2

        logger.info(f"[IndexCheck] 开始检测平台: {checker.name}, 关键词: {keyword_obj.keyword}")

        for qv in questions:
            logger.info(f"[IndexCheck] 准备检测问题: {qv.question[:50]}...")

            retry_count = 0
            success = False
            check_result = None

            while retry_count <= max_retries and not success:
                try:
                    logger.info(f"[IndexCheck] 执行检测 (尝试 {retry_count + 1}/{max_retries + 1})...")

                    # 调用检测器
                    check_result = await checker.check(
                        page=page,
                        question=qv.question,
                        keyword=keyword_obj.keyword,
                        company=company_name
                    )

                    success = check_result.get("success", False)
                    if success:
                        logger.info(f"[IndexCheck] 检测成功: 平台={checker.name}, 问题={qv.question[:30]}...")
                        break

                    retry_count += 1
                    logger.warning(f"[IndexCheck] 检测失败，正在重试 ({retry_count}/{max_retries}): {check_result.get('error_msg', '未知错误')}")

                    # 重试前清理聊天记录和等待
                    await checker.clear_chat_history(page)
                    await asyncio.sleep(3)

                except Exception as e:
                    retry_count += 1
                    logger.error(f"[IndexCheck] 检测异常，正在重试 ({retry_count}/{max_retries}): {str(e)}")

                    # 重试前等待
                    await asyncio.sleep(5)

                    # 尝试重新导航到页面
                    if retry_count > 1:
                        logger.info(f"[IndexCheck] 重新导航到平台首页...")
                        await checker.navigate_to_page(page)

            if not check_result:
                check_result = {
                    "success": False,
                    "answer": None,
                    "keyword_found": False,
                    "company_found": False,
                    "error_msg": "检测超时或多次失败"
                }

            # 记录详细日志
            logger.info(f"[IndexCheck] 检测结果: 关键词={keyword_obj.keyword}, "
                       f"关键词命中={check_result.get('keyword_found', False)}, "
                       f"公司命中={check_result.get('company_found', False)}")

            try:
                # 保存检测结果，强制使用北京时间 (UTC+8)
                beijing_time = datetime.now(timezone.utc) + timedelta(hours=8)

                record = IndexCheckRecord(
                    keyword_id=keyword_id,
                    platform=platform_id,
                    question=qv.question,
                    answer=check_result.get("answer"),
                    keyword_found=check_result.get("keyword_found", False),
                    company_found=check_result.get("company_found", False),
                    check_time=beijing_time.replace(tzinfo=None)  # 去除时区信息，直接存为本地时间
                )
                self.db.add(record)
                self.db.commit()
                logger.info(f"[IndexCheck] 检测记录已保存: ID={record.id}")
            except Exception as db_error:
                logger.error(f"[IndexCheck] 保存检测结果失败: {str(db_error)}")
                # 回滚事务
                self.db.rollback()

            results.append({
                "keyword_id": keyword_id,
                "keyword": keyword_obj.keyword,
                "platform": checker.name,
                "question": qv.question,
                "keyword_found": check_result.get("keyword_found", False),
                "company_found": check_result.get("company_found", False),
                "success": check_result.get("success", False),
                "retry_count": retry_count
            })

            # 每个问题检测后短暂休息
            await asyncio.sleep(1)

        return results

    def get_check_records(
        self,
        keyword_id: Optional[int] = None,
        platform: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
        keyword_found: Optional[bool] = None,
        company_found: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        question: Optional[str] = None
    ) -> tuple[List[IndexCheckRecord], int]:
        """
        获取检测记录（支持分页和多维筛选）

        Args:
            keyword_id: 关键词ID筛选
            platform: 平台筛选
            limit: 返回数量限制
            skip: 跳过数量
            keyword_found: 关键词命中筛选
            company_found: 公司名命中筛选
            start_date: 开始时间
            end_date: 结束时间
            question: 问题搜索（模糊匹配）

        Returns:
            (记录列表, 总记录数)
        """
        query = self.db.query(IndexCheckRecord)

        if keyword_id:
            query = query.filter(IndexCheckRecord.keyword_id == keyword_id)
        if platform:
            query = query.filter(IndexCheckRecord.platform == platform)
        if keyword_found is not None:
            query = query.filter(IndexCheckRecord.keyword_found == keyword_found)
        if company_found is not None:
            query = query.filter(IndexCheckRecord.company_found == company_found)
        if start_date:
            query = query.filter(IndexCheckRecord.check_time >= start_date)
        if end_date:
            query = query.filter(IndexCheckRecord.check_time <= end_date)
        if question:
            query = query.filter(IndexCheckRecord.question.ilike(f"%{question}%"))

        total = query.count()
        records = query.order_by(IndexCheckRecord.check_time.desc()).offset(skip).limit(limit).all()

        return records, total

    def delete_record(self, record_id: int) -> bool:
        """删除单条记录"""
        record = self.db.query(IndexCheckRecord).filter(IndexCheckRecord.id == record_id).first()
        if not record:
            return False
        self.db.delete(record)
        self.db.commit()
        return True

    def batch_delete_records(self, record_ids: List[int]) -> int:
        """批量删除记录"""
        count = self.db.query(IndexCheckRecord).filter(
            IndexCheckRecord.id.in_(record_ids)
        ).delete(synchronize_session=False)
        self.db.commit()
        return count

    def get_hit_rate(self, keyword_id: int) -> Dict[str, Any]:
        """
        计算关键词命中率

        Args:
            keyword_id: 关键词ID

        Returns:
            命中率统计
        """
        records = self.db.query(IndexCheckRecord).filter(
            IndexCheckRecord.keyword_id == keyword_id
        ).all()

        if not records:
            return {"hit_rate": 0, "total": 0, "keyword_found": 0, "company_found": 0}

        total = len(records)
        keyword_found = sum(1 for r in records if r.keyword_found)
        company_found = sum(1 for r in records if r.company_found)

        return {
            "hit_rate": round((keyword_found + company_found) / (total * 2) * 100, 2),
            "total": total,
            "keyword_found": keyword_found,
            "company_found": company_found
        }

    def get_keyword_trend(
        self,
        keyword_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取关键词收录趋势

        Args:
            keyword_id: 关键词ID
            days: 统计天数

        Returns:
            趋势数据
        """
        from datetime import timedelta

        # 获取起始时间
        start_date = datetime.now() - timedelta(days=days)

        # 获取关键词信息
        keyword = self.db.query(Keyword).filter(Keyword.id == keyword_id).first()
        if not keyword:
            return {"keyword": None, "trend": []}

        # 按天分组统计
        trend_data = []

        for day_offset in range(days, 0, -1):
            day_start = datetime.now() - timedelta(days=day_offset)
            day_end = day_start + timedelta(days=1)

            # 获取当天的检测记录
            records = self.db.query(IndexCheckRecord).filter(
                IndexCheckRecord.keyword_id == keyword_id,
                IndexCheckRecord.check_time >= day_start,
                IndexCheckRecord.check_time < day_end
            ).all()

            if not records:
                continue

            # 计算当天的统计数据
            total = len(records)
            keyword_found = sum(1 for r in records if r.keyword_found)
            company_found = sum(1 for r in records if r.company_found)

            # 计算命中率
            hit_rate = round((keyword_found + company_found) / (total * 2) * 100, 2) if total > 0 else 0

            trend_data.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "total": total,
                "keyword_found": keyword_found,
                "company_found": company_found,
                "hit_rate": hit_rate,
                "keyword_pct": round((keyword_found / total) * 100, 2) if total > 0 else 0,
                "company_pct": round((company_found / total) * 100, 2) if total > 0 else 0
            })

        return {
            "keyword": keyword.keyword,
            "trend": trend_data,
            "total_days": days
        }

    def get_project_analytics(
        self,
        project_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取项目的综合分析

        Args:
            project_id: 项目ID
            days: 统计天数

        Returns:
            项目分析数据
        """
        from datetime import timedelta

        # 获取项目信息
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"error": "项目不存在"}

        # 获取项目下所有关键词
        keywords = self.db.query(Keyword).filter(
            Keyword.project_id == project_id
        ).all()

        if not keywords:
            return {
                "project_name": project.name,
                "company_name": project.company_name,
                "total_keywords": 0,
                "analytics": [],
                "summary": {
                    "total_checks": 0,
                    "avg_hit_rate": 0,
                    "keyword_avg": 0,
                    "company_avg": 0
                }
            }

        start_date = datetime.now() - timedelta(days=days)

        keyword_analytics = []
        total_checks = 0
        total_hit_rate = 0
        total_keyword_avg = 0
        total_company_avg = 0

        for keyword in keywords:
            # 获取该关键词的检测记录
            records = self.db.query(IndexCheckRecord).filter(
                IndexCheckRecord.keyword_id == keyword.id,
                IndexCheckRecord.check_time >= start_date
            ).all()

            if not records:
                continue

            total = len(records)
            keyword_found = sum(1 for r in records if r.keyword_found)
            company_found = sum(1 for r in records if r.company_found)

            hit_rate = round((keyword_found + company_found) / (total * 2) * 100, 2) if total > 0 else 0
            keyword_pct = round((keyword_found / total) * 100, 2) if total > 0 else 0
            company_pct = round((company_found / total) * 100, 2) if total > 0 else 0

            keyword_analytics.append({
                "keyword_id": keyword.id,
                "keyword": keyword.keyword,
                "total_checks": total,
                "hit_rate": hit_rate,
                "keyword_pct": keyword_pct,
                "company_pct": company_pct,
                "status": "good" if hit_rate > 60 else "warning" if hit_rate > 30 else "critical"
            })

            # 累计统计
            total_checks += total
            total_hit_rate += hit_rate
            total_keyword_avg += keyword_pct
            total_company_avg += company_pct

        # 计算平均值
        keyword_count = len(keyword_analytics)
        summary = {
            "total_checks": total_checks,
            "avg_hit_rate": round(total_hit_rate / keyword_count, 2) if keyword_count > 0 else 0,
            "keyword_avg": round(total_keyword_avg / keyword_count, 2) if keyword_count > 0 else 0,
            "company_avg": round(total_company_avg / keyword_count, 2) if keyword_count > 0 else 0
        }

        return {
            "project_name": project.name,
            "company_name": project.company_name,
            "total_keywords": len(keywords),
            "active_keywords": keyword_count,
            "analytics": keyword_analytics,
            "summary": summary
        }

    def get_platform_performance(
        self,
        project_id: Optional[int] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取各平台的表现分析

        Args:
            project_id: 项目ID（可选）
            days: 统计天数

        Returns:
            平台表现数据
        """
        from datetime import timedelta

        start_date = datetime.now() - timedelta(days=days)

        # 构建查询条件
        query = self.db.query(IndexCheckRecord)

        if project_id:
            # 通过关键词关联到项目
            from sqlalchemy import and_
            query = query.join(Keyword).filter(
                and_(
                    IndexCheckRecord.check_time >= start_date,
                    Keyword.project_id == project_id,
                    Keyword.status == "active"
                )
            )
        else:
            query = query.filter(IndexCheckRecord.check_time >= start_date)

        records = query.all()

        if not records:
            return {"platforms": [], "summary": {"total_checks": 0}}

        # 按平台分组统计
        platform_data = {}

        for record in records:
            platform = record.platform
            if platform not in platform_data:
                platform_data[platform] = {
                    "platform": platform,
                    "total": 0,
                    "keyword_found": 0,
                    "company_found": 0,
                    "success_count": 0
                }

            platform_data[platform]["total"] += 1
            if record.keyword_found:
                platform_data[platform]["keyword_found"] += 1
            if record.company_found:
                platform_data[platform]["company_found"] += 1

            # 成功检测（有回答）
            if record.answer and record.answer.strip():
                platform_data[platform]["success_count"] += 1

        # 计算各平台的命中率和成功率
        platforms = []
        total_checks = 0
        total_success = 0

        for platform, data in platform_data.items():
            hit_rate = round((data["keyword_found"] + data["company_found"]) / (data["total"] * 2) * 100, 2) if data["total"] > 0 else 0
            keyword_pct = round((data["keyword_found"] / data["total"]) * 100, 2) if data["total"] > 0 else 0
            company_pct = round((data["company_found"] / data["total"]) * 100, 2) if data["total"] > 0 else 0
            success_rate = round((data["success_count"] / data["total"]) * 100, 2) if data["total"] > 0 else 0

            platforms.append({
                "platform": platform,
                "platform_name": self.checkers.get(platform, {}).name if platform in self.checkers else platform,
                "total_checks": data["total"],
                "hit_rate": hit_rate,
                "keyword_pct": keyword_pct,
                "company_pct": company_pct,
                "success_rate": success_rate,
                "status": "good" if hit_rate > 60 else "warning" if hit_rate > 30 else "critical"
            })

            total_checks += data["total"]
            total_success += data["success_count"]

        # 按命中率排序
        platforms.sort(key=lambda x: x["hit_rate"], reverse=True)

        summary = {
            "total_platforms": len(platforms),
            "total_checks": total_checks,
            "avg_success_rate": round((total_success / total_checks) * 100, 2) if total_checks > 0 else 0
        }

        return {
            "platforms": platforms,
            "summary": summary
        }
