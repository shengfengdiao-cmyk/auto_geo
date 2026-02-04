# -*- coding: utf-8 -*-
"""
n8n 服务封装 - 终极加固调试版 (v3.0)
1. 解决 n8n 返回非 JSON 格式导致的程序崩溃
2. 增加原始响应日志，方便排查 Basic LLM Chain 的输出问题
3. 适配多种 n8n 返回结构 (List, Dict, 纯文本)
4. 🌟 支持独立的 Webhook URL 配置（关键词蒸馏 vs 文章生成）
5. 增加调试日志，打印实际调用的 n8n URL
"""

import httpx
import json
from typing import Any, Literal, Optional, List, Dict
import re
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict

# 🌟 导入配置
from backend.config import (
    BASE_WEBHOOK,
    N8N_DISTILL_WEBHOOK_URL,
    N8N_GENERATE_WEBHOOK_URL
)


# ==================== 配置 ====================

class N8nConfig:
    # 🌟 n8n Webhook 基础地址 (将从 config.py 读取)
    WEBHOOK_BASE = None  # 将在运行时从 config.py 读取

    # 🌟 关键词蒸馏专用 Webhook URL
    DISTILL_WEBHOOK_URL = None  # 将在运行时从 config.py 读取

    # 🌟 文章生成专用 Webhook URL
    GENERATE_WEBHOOK_URL = None  # 将在运行时从 config.py 读取

    # 超时配置
    TIMEOUT_SHORT = 60.0  # 蒸馏、分析等任务稍微加长一点
    TIMEOUT_LONG = 900.0  # 长文章生成 (15分钟，适配深度长文生成)

    # 重试配置
    MAX_RETRIES = 1


# ==================== 请求模型 ====================

class KeywordDistillRequest(BaseModel):
    # 兼容旧版：以列表形式传递上下文
    keywords: Optional[List[str]] = None
    project_id: Optional[int] = None

    # 通用版：适配 n8n "AutoGeo-关键词蒸馏-通用版" 工作流
    core_kw: Optional[str] = None
    target_info: Optional[str] = None
    prefixes: Optional[str] = None
    suffixes: Optional[str] = None


class GenerateQuestionsRequest(BaseModel):
    question: str
    count: int = 10


class GeoArticleRequest(BaseModel):
    keyword: str
    platform: str = "zhihu"
    requirements: str = ""
    word_count: int = 1200
    # 🌟 内容驱动配图标志：True=AI提取视觉词，False=使用通用关键词
    content_driven_images: bool = True
    # 🌟 视觉词提取模版（可选）
    # 如果不提供，AI 将根据段落内容自动提取场景描述词
    visual_prompt_template: Optional[str] = None


class IndexCheckAnalysisRequest(BaseModel):
    keyword: str
    doubao_indexed: bool
    qianwen_indexed: bool
    deepseek_indexed: bool
    history: List[Dict] = []


# ==================== 响应模型 ====================

class N8nResponse(BaseModel):
    """n8n 统一响应格式"""
    status: Literal["success", "error", "processing"]
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== 辅助函数 ====================

def _extract_visual_keywords_from_markdown(content: str) -> List[str]:
    """
    从 Markdown 内容中提取 3 个不同的视觉描述词

    策略：
    1. 提取段落首句
    2. 提取重点关键词
    3. 生成差异化描述

    Returns:
        3 个视觉描述词的列表
    """
    try:
        visual_keywords = []

        # 1. 提取首句描述
        # 找到第一个完整句子
        sentences = re.split(r'[。！？\n]', content)
        first_sentence = ""
        for s in sentences:
            s = s.strip()
            if len(s) >= 10:  # 至少10个字符
                first_sentence = s
                break

        if first_sentence:
            # 提取前 2-4 个描述性词汇
            words = re.findall(r'[\u4e00-\u9fa5]+{2,6}', first_sentence)
            if words:
                # 选择最长的一个描述词
                desc_word = max(words, key=len)
                visual_keywords.append(desc_word)

        # 2. 提取图片相关关键词
        image_related_keywords = []
        patterns = [
            r'(图片|照片|图像|插画|配图|封面)(?:，|、|和|或|的)?',
            r'(场景|背景|环境|氛围)(?:，|、|和|或|的)?',
            r'(风格|色调|颜色)(?:，|、|和|或|的)?',
            r'(人物|人像|头像)(?:，|、|和|或|的)?',
            r'(商业|商务|专业|正式|简洁)(?:，|、|和|或|的)?',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            if matches:
                # 提取名词部分
                for m in matches:
                    nouns = re.findall(r'[\u4e00-\u9fa5]+{2,6}', m)
                    for noun in nouns:
                        if len(noun) >= 2 and noun not in image_related_keywords:
                            image_related_keywords.append(noun)

        # 选择最相关的前 2 个
        visual_keywords.extend(image_related_keywords[:2])

        # 3. 如果提取不足 3 个，补充通用词
        fallback_keywords = [
            "professional business scene",
            "modern clean background",
            "high quality photo"
        ]

        while len(visual_keywords) < 3:
            visual_keywords.extend(fallback_keywords)

        # 返回前 3 个
        logger.info(f"🎨 从内容中提取的视觉关键词: {visual_keywords[:3]}")
        return visual_keywords[:3]

    except Exception as e:
        logger.warning(f"⚠️ 视觉关键词提取失败: {e}")
        return ["professional business", "modern clean background", "high quality photo"]


# ==================== 服务类 ====================

class N8nService:
    """
    n8n 服务类
    集成日志推送，支持自动化流水线的实时监控
    """

    def __init__(self, config: Optional[N8nConfig] = None):
        self.config = config or N8nConfig()
        # 🌟 从 backend/config.py 读取 Webhook 配置
        self.config.WEBHOOK_BASE = BASE_WEBHOOK
        if N8N_DISTILL_WEBHOOK_URL:
            self.config.DISTILL_WEBHOOK_URL = N8N_DISTILL_WEBHOOK_URL
            logger.info(f"🔧 关键词蒸馏 Webhook URL: {N8N_DISTILL_WEBHOOK_URL}")
        if N8N_GENERATE_WEBHOOK_URL:
            self.config.GENERATE_WEBHOOK_URL = N8N_GENERATE_WEBHOOK_URL
            logger.info(f"🔧 文章生成 Webhook URL: {N8N_GENERATE_WEBHOOK_URL}")
        # 🌟 绑定模块名，用于前端实时日志
        self.log = logger.bind(module="AI中台")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.config.TIMEOUT_SHORT,
                follow_redirects=True
            )
        return self._client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _call_webhook(
            self,
            endpoint: str,
            payload: Dict[str, Any],
            timeout: Optional[float] = None,
            full_url: Optional[str] = None
    ) -> N8nResponse:
        """
        底层统一调用逻辑

        Args:
            endpoint: Webhook endpoint 路径 (如 "keyword-distill")
            payload: 请求数据
            timeout: 超时时间
            full_url: 完整的 Webhook URL (如果提供，则忽略 endpoint)
        """
        # 🌟 优先使用 full_url，否则使用 endpoint 拼接
        if full_url:
            url = full_url
            endpoint_display = full_url.split("/")[-1]  # 用于日志显示的简化端点名
        else:
            path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
            url = f"{self.config.WEBHOOK_BASE}{path}"
            endpoint_display = endpoint

        timeout_val = timeout or self.config.TIMEOUT_SHORT

        # 🌟 防御性日志：打印实际调用的 n8n URL
        self.log.debug(f"Target URL for this task: {url}")
        self.log.info(f"🛰️ [调用 n8n] 端点: {endpoint_display} | 完整 URL: {url}")

        for attempt in range(self.config.MAX_RETRIES + 1):
            try:
                response = await self.client.post(url, json=payload, timeout=timeout_val)

                # 获取原始文本，这是调试的关键！
                raw_text = response.text

                # 1. 检查 HTTP 状态码
                if response.status_code != 200:
                    err_msg = f"HTTP {response.status_code}: {raw_text[:200]}"
                    self.log.error(f"❌ n8n 返回错误: {err_msg}")
                    return N8nResponse(status="error", error=err_msg)

                # 2. 尝试解析 JSON
                try:
                    res_data = response.json()

                    # 如果 n8n 返回的是数组格式（n8n 默认行为），取第一个
                    if isinstance(res_data, list):
                        res_data = res_data[0] if len(res_data) > 0 else {}

                    # 兼容性处理：如果返回结果里没有 status 字段，我们手动包装一层
                    if isinstance(res_data, dict) and "status" not in res_data:
                        return N8nResponse(status="success", data=res_data)

                    # 按照标准模型解析
                    return N8nResponse(**res_data)

                except json.JSONDecodeError:
                    # 🌟 报错现场捕捉：打印 n8n 吐出的真实内容
                    self.log.error(f"❌ n8n 响应不是有效的 JSON 格式！")
                    self.log.error(f"🔍 原始响应内容如下:\n{raw_text}")

                    # 特殊情况处理：如果 n8n 没配 Respond to Webhook，默认会返回 "Workflow started"
                    if "Workflow was started" in raw_text or "Workflow started" in raw_text:
                        return N8nResponse(status="error",
                                           error="n8n工作流缺少 'Respond to Webhook' 节点，无法接收AI数据")

                    return N8nResponse(status="error", error=f"JSON解析失败: {raw_text[:100]}")

            except httpx.TimeoutException:
                self.log.warning(f"⏳ 请求超时 (尝试 {attempt + 1}/{self.config.MAX_RETRIES + 1})")
                if attempt == self.config.MAX_RETRIES:
                    return N8nResponse(status="error", error="AI 生成超时，请检查 n8n 资源占用")

            except Exception as e:
                self.log.error(f"🚨 传输层异常: {str(e)}")
                return N8nResponse(status="error", error=str(e))

        return N8nResponse(status="error", error="未知错误")

    # ==================== 业务方法 ====================

    async def distill_keywords(
            self,
            *,
            core_kw: Optional[str] = None,
            target_info: Optional[str] = None,
            prefixes: Optional[str] = None,
            suffixes: Optional[str] = None,
            keywords: Optional[List[str]] = None,
            project_id: Optional[int] = None
    ) -> N8nResponse:
        """关键词蒸馏 - 使用独立的 Webhook URL"""
        self.log.info(f"🧹 正在蒸馏提纯关键词...")

        payload = KeywordDistillRequest(
            keywords=keywords,
            project_id=project_id,
            core_kw=core_kw,
            target_info=target_info,
            prefixes=prefixes,
            suffixes=suffixes,
        ).model_dump(exclude_none=True)

        # 🌟 使用关键词蒸馏专用 Webhook URL
        return await self._call_webhook(
            "keyword-distill",
            payload,
            full_url=self.config.DISTILL_WEBHOOK_URL
        )

    async def generate_questions(self, question: str, count: int = 10) -> N8nResponse:
        """生成问题变体"""
        self.log.info(f"❓ 正在基于原题扩展变体...")
        payload = GenerateQuestionsRequest(question=question, count=count).model_dump()
        return await self._call_webhook("generate-questions", payload)

    async def generate_geo_article(
            self,
            keyword: str,
            platform: str = "zhihu",
            requirements: str = "",
            word_count: int = 1200,
            content_driven_images: bool = True,
            visual_prompt_template: Optional[str] = None
    ) -> N8nResponse:
        """
        生成 GEO 优化文章 (长任务) - 使用独立的 Webhook URL

        Args:
            keyword: 核心关键词
            platform: 目标平台
            requirements: 额外要求
            word_count: 目标字数
            content_driven_images: True=AI提取视觉词配图, False=使用通用关键词配图
            visual_prompt_template: 可选的视觉词提取模版
        """
        self.log.info(f"📝 正在撰写适用于 [{platform}] 的 GEO 文章 (内容驱动配图: {content_driven_images})...")

        # 🌟 深度 Prompt 重构：视觉词提取与配图语法规范
        # 如果启用内容驱动配图，添加详细的配图指令
        if content_driven_images:
            detailed_requirements = requirements + """

【🎨 图片配图规范（请严格遵守）】

1. 视觉词提取要求：
   - 撰写到每个 H2 小标题时，先思考该段落描述的具体场景
   - 提取 1-3 个具体的英文名词（例如：factory_robot, business_handshake, clean_city_street）
   - 禁止使用中文作为图片参数，必须转换为英文
   - 视觉词应为名词+形容词的组合，描述具体场景

2. 配图语法规范（必须严格遵守）：
   - Markdown 格式：![视觉描述](https://pollinations.ai/p/{视觉词}?width=800&height=450&nologo=true&seed={随机数})
   - 示例：![modern office scene](https://pollinations.ai/p/office_meeting_professional?width=800&height=450&nologo=true&seed=123456)
   - 必须包含 seed 参数，使用随机数防止缓存
   - 放弃 loremflickr，全面使用 Pollinations AI（响应更快）
   - URL 编码：视觉词需要进行 URL 编码

3. 图片位置规范：
   - 至少插入 3 张图片：第1张放文章开头，第2张放文章中间，第3张放文章结尾
   - 每张图片使用不同的视觉词，避免重复

4. 关键词类型参考：
   - 商务场景：business_meeting, office_collaboration, contract_signing
   - 科技场景：technology_lab, robot_assembly, factory_production
   - 城市场景：city_street, urban_landscape, modern_building
   - 人物场景：professional_handshake, team_collaboration, business_conversation
   - 抽象场景：clean_geometry, minimal_design, abstract_business
"""
        else:
            detailed_requirements = requirements

        payload = GeoArticleRequest(
            keyword=keyword,
            platform=platform,
            requirements=detailed_requirements,
            word_count=word_count,
            content_driven_images=content_driven_images,
            visual_prompt_template=visual_prompt_template
        ).model_dump()

        # 🌟 使用文章生成专用 Webhook URL
        return await self._call_webhook(
            "geo-article-generate",
            payload,
            timeout=self.config.TIMEOUT_LONG,
            full_url=self.config.GENERATE_WEBHOOK_URL
        )

    async def analyze_index_check(
            self,
            keyword: str,
            doubao_indexed: bool,
            qianwen_indexed: bool,
            deepseek_indexed: bool,
            history: Optional[List[Dict]] = None
    ) -> N8nResponse:
        """分析收录结果"""
        self.log.info(f"📊 正在请求 AI 深度分析收录趋势...")
        payload = IndexCheckAnalysisRequest(
            keyword=keyword,
            doubao_indexed=doubao_indexed,
            qianwen_indexed=qianwen_indexed,
            deepseek_indexed=deepseek_indexed,
            history=history or []
        ).model_dump()
        return await self._call_webhook("index-check-analysis", payload)


# ==================== 单例模式 ====================

_instance: Optional[N8nService] = None


async def get_n8n_service() -> N8nService:
    global _instance
    if _instance is None:
        _instance = N8nService()
    return _instance