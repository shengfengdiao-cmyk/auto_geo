# -*- coding: utf-8 -*-
"""
GEO文章生成服务 (Mock版)
用于演示调度系统逻辑，跳过 n8n 依赖，直接生成模拟数据！
"""

import asyncio
import random
from typing import Any, Dict, Optional
from loguru import logger
from sqlalchemy.orm import Session

from backend.database.models import GeoArticle, Keyword
from backend.services.n8n_client import get_n8n_client


class GeoArticleService:
    """
    GEO文章服务
    注意：这个服务负责与n8n交互完成文章生成！
    (当前为 Mock 模式，模拟 n8n 返回)
    """

    def __init__(self, db: Session):
        """
        初始化文章服务

        Args:
            db: 数据库会话
        """
        self.db = db
        # self.n8n = get_n8n_client() # Mock模式下不需要真实客户端

    async def generate(
            self,
            keyword_id: int,
            company_name: str,
            platform: str = "zhihu"
    ) -> Dict[str, Any]:
        """
        生成文章 (Mock逻辑：直接返回成功，不改变原有接口定义)

        Args:
            keyword_id: 关键词ID
            company_name: 公司名称
            platform: 目标发布平台

        Returns:
            生成结果
        """
        # 获取关键词
        keyword_obj = self.db.query(Keyword).filter(Keyword.id == keyword_id).first()
        if not keyword_obj:
            return {"status": "error", "message": "关键词不存在"}

        logger.info(f"🚀 [调度触发] 开始生成文章: {keyword_obj.keyword} - {platform}")

        # =======================================================
        # 🔴 Mock 区域：模拟 AI 生成过程 (跳过 n8n)
        # 保持了原有的逻辑结构，只是伪造了 result 变量
        # =======================================================
        logger.warning(f"⚠️ 正在使用 Mock 模式生成，未调用 n8n 接口...")

        # 模拟网络延迟 1.5 秒
        await asyncio.sleep(1.5)

        # 伪造一个完美的 AI 返回结果
        fake_title = f"【深度解析】{company_name}教你如何搞定{keyword_obj.keyword}"
        fake_content = (
            f"这里是自动生成的关于 {keyword_obj.keyword} 的详细指南。\n\n"
            f"1. 为什么选择{company_name}？\n因为我们要测试调度系统是否正常工作。\n\n"
            f"2. {keyword_obj.keyword}的注意事项...\n(此处省略800字AI生成内容)"
        )

        # 模拟 n8n 返回的 result 字典
        result = {
            "status": "success",
            "title": fake_title,
            "content": fake_content
        }
        # =======================================================

        # 原有逻辑：判断 n8n 是否报错 (Mock 模式下永远成功)
        if result.get("status") == "error":
            logger.error(f"文章生成失败: {result.get('message')}")
            return {"status": "error", "message": result.get("message")}

        # 原有逻辑：保存文章到数据库 (完全保留，数据会真的存进去)
        article = GeoArticle(
            keyword_id=keyword_id,
            title=result.get("title"),
            content=result.get("content"),
            platform=platform,
            quality_status="pending"
        )
        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)

        logger.info(f"✅ 文章已生成 (Mock模式): {article.id}")
        return {
            "status": "success",
            "article_id": article.id,
            "title": article.title,
            "content": article.content
        }

    async def check_quality(self, article_id: int) -> Dict[str, Any]:
        """
        质检文章 (Mock逻辑：直接返回通过，不改变原有接口定义)

        Args:
            article_id: 文章ID

        Returns:
            质检结果
        """
        article = self.db.query(GeoArticle).filter(GeoArticle.id == article_id).first()
        if not article:
            return {"status": "error", "message": "文章不存在"}

        logger.info(f"🔍 开始质检文章: {article_id}")

        # =======================================================
        # 🔴 Mock 区域：模拟质检过程 (跳过 n8n)
        # =======================================================
        await asyncio.sleep(1)  # 模拟耗时

        # 伪造 n8n 返回的高分结果
        result = {
            "status": "success",
            "quality_score": random.randint(85, 98),
            "ai_score": random.randint(10, 30),  # AI率低越好
            "readability_score": random.randint(80, 95)
        }
        # =======================================================

        if result.get("status") == "error":
            logger.error(f"质检失败: {result.get('message')}")
            return {"status": "error", "message": result.get("message")}

        # 原有逻辑：更新数据库
        article.quality_score = result.get("quality_score")
        article.ai_score = result.get("ai_score")
        article.readability_score = result.get("readability_score")

        # 判断是否通过质检
        if article.quality_score and article.quality_score >= 60:
            article.quality_status = "passed"
        else:
            article.quality_status = "failed"

        self.db.commit()

        logger.info(f"✅ 质检完成 (Mock模式): {article_id} - {article.quality_status}")
        return {
            "status": "success",
            "quality_score": article.quality_score,
            "ai_score": article.ai_score,
            "readability_score": article.readability_score,
            "quality_status": article.quality_status
        }

    def get_article(self, article_id: int) -> Optional[GeoArticle]:
        """获取文章详情 (原有功能保持不变)"""
        return self.db.query(GeoArticle).filter(GeoArticle.id == article_id).first()

    def get_keyword_articles(self, keyword_id: int) -> list[GeoArticle]:
        """获取关键词的所有文章 (原有功能保持不变)"""
        return self.db.query(GeoArticle).filter(
            GeoArticle.keyword_id == keyword_id
        ).order_by(GeoArticle.created_at.desc()).all()

    def update_article(
            self,
            article_id: int,
            title: Optional[str] = None,
            content: Optional[str] = None
    ) -> Optional[GeoArticle]:
        """更新文章 (原有功能保持不变)"""
        article = self.db.query(GeoArticle).filter(GeoArticle.id == article_id).first()
        if not article:
            return None

        if title is not None:
            article.title = title
        if content is not None:
            article.content = content

        self.db.commit()
        self.db.refresh(article)
        return article