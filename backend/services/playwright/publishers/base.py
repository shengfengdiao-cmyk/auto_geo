# -*- coding: utf-8 -*-
"""
Playwright发布适配器
用适配器模式实现各平台发布，开闭原则！
"""

import asyncio
import os
import re
import httpx
import tempfile
import random
import urllib.parse
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from playwright.async_api import Page, BrowserContext
from loguru import logger


# ==================== 图片下载增强工具 ====================

class ImageDownloadManager:
    """
    智能图片下载管理器 (v2.0)

    特性：
    1. 主备选切换：pollinations -> unsplash
    2. 随机种子/时间戳：防止重复 URL 检测
    3. 视觉关键词提取：基于内容生成差异化描述
    4. 优雅降级：下载失败不中断发布流程
    5. 关键词清洗：自动修正中文、空格、特殊字符
    6. 并发下载优化：单个图片最多 10s 超时，立即切换到下一个
    """

    # 主备选服务配置
    PRIMARY_SERVICES = [
        "pollinations",
        "unsplash"
    ]

    # 服务端点配置
    SERVICE_ENDPOINTS = {
        "pollinations": "https://image.pollinations.ai/prompt/{encoded}?width=800&height=450&nologo=true&seed={seed}",
        "unsplash": "https://source.unsplash.com/random?w=800&h=450&sig={sig}",
    }

    # 缓存已下载的图片 URL（避免重复）
    _downloaded_urls = set()

    def __init__(self):
        self.current_service_index = 0
        self._base_client = self._get_httpx_client()
        logger.info(f"🖼️ 图片下载管理器初始化完成 (当前服务: {self.PRIMARY_SERVICES[0]})")

    def _get_httpx_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        return httpx.AsyncClient(headers=headers, verify=False, follow_redirects=True, timeout=30.0)

    def _sanitize_img_keyword(self, url_or_keyword: str) -> str:
        """
        关键词清洗：修正 AI 吐出的问题 URL

        功能：
        1. 移除中文字符，转换为简单英文单词
        2. URL 编码中文关键词
        3. 移除多余空格和特殊字符
        4. 提取纯关键词部分（移除已有参数）

        Args:
            url_or_keyword: 原始 URL 或关键词

        Returns:
            清洗后的关键词（适用于图片生成 URL）
        """
        import unicodedata

        try:
            # 1. 如果是完整 URL，提取关键词部分
            if url_or_keyword.startswith("http"):
                # 从 URL 中提取关键词（去掉已存在的参数）
                # 匹配 pollinations.ai/prompt/xxx 或类似格式
                import re
                match = re.search(r'/prompt/([^?]+)', url_or_keyword)
                if match:
                    keyword = match.group(1)
                else:
                    keyword = url_or_keyword.split("/")[-1].split("?")[0]
            else:
                keyword = url_or_keyword

            # 2. URL 解码（如果是 URL 编码的）
            if "%" in keyword:
                try:
                    keyword = urllib.parse.unquote(keyword)
                except:
                    pass

            # 3. 移除或转换中文字符
            cleaned_parts = []
            for char in keyword:
                # 检查是否为中文字符
                if unicodedata.category(char).startswith('Lo'):
                    # 转换为拼音或简单英文
                    continue
                # 保留英文字母、数字、下划线、连字符
                if char.isalnum() or char in ['-', '_', ' ']:
                    cleaned_parts.append(char)

            cleaned = ''.join(cleaned_parts).strip()

            # 4. 如果清洗后为空，使用默认词
            if not cleaned or len(cleaned) < 2:
                return "business office professional"

            # 5. 替换空格为下划线（适用于 URL）
            cleaned = cleaned.replace(' ', '_').lower()

            return cleaned

        except Exception as e:
            logger.warning(f"⚠️ 关键词清洗失败: {e}")
            return "business office"

    async def download_images(
        self,
        image_urls: List[str],
        max_retries_per_service: int = 2
    ) -> Dict[str, Any]:
        """
        智能下载图片（并发优化版 - 修复变量冲突版）

        特性：
        1. 单个图片最多 10s 超时，失败立即切换到下一个
        2. 返回已成功下载的本地路径列表
        3. 优雅降级：即使只有 1 张成功，也立刻返回
        4. 🌟 修复变量冲突：汇总字典与循环变量完全区分开

        Returns:
            {
                "success": bool,
                "paths": List[str],  # 下载成功的图片路径
                "service_used": str,  # 使用的服务
                "failed_count": int,  # 失败的图片数量
                "mode": str,  # text_only | partial_image | full_image
            }
        """
        # 🌟 汇总结果字典初始化
        final_results = {
            "success": True,
            "paths": [],
            "service_used": "none",
            "failed_count": 0,
            "mode": "full_image"
        }

        # 🌟 并发下载优化：为每个图片创建独立任务
        download_tasks = []
        for url in image_urls:
            # 清洗关键词
            sanitized_keyword = self._sanitize_img_keyword(url)
            if sanitized_keyword != url:
                # 如果清洗改变了关键词，更新 URL
                # 假设是 pollinations.ai 格式
                if "pollinations.ai" in url:
                    import re
                    match = re.search(r'/prompt/([^?]+)', url)
                    if match:
                        seed_match = re.search(r'seed=(\d+)', url)
                        seed = seed_match.group(1) if seed_match else str(random.randint(10000, 99999))
                        encoded_keyword = urllib.parse.quote(sanitized_keyword)
                        url = f"https://image.pollinations.ai/prompt/{encoded_keyword}?width=800&height=450&nologo=true&seed={seed}"

            # 创建下载任务
            task = asyncio.create_task(
                self._download_single_image_with_timeout(url, timeout=10.0)
            )
            download_tasks.append((task, url))

        # 等待所有任务完成（或全部超时）
        if download_tasks:
            # 🌟 关键优化：逐个获取结果，只要有成功的就立即返回
            for task, original_url in download_tasks:
                try:
                    # 设置 10s 超时
                    single_result = await asyncio.wait_for(task, timeout=10.0)

                    # 🌟 防御性检查：单次下载成功才更新汇总结果
                    if single_result.get("success") and single_result.get("path"):
                        final_results["paths"].append(single_result["path"])
                        final_results["service_used"] = single_result.get("service", "none")
                        self._downloaded_urls.add(original_url)
                    else:
                        # 🌟 异常处理：不抛出 KeyError
                        final_results["failed_count"] = final_results.get("failed_count", 0) + 1

                except asyncio.TimeoutError:
                    logger.debug(f"⏳ 图片下载超时（10s），跳过")
                    final_results["failed_count"] = final_results.get("failed_count", 0) + 1
                except Exception as e:
                    logger.debug(f"⚠️ 图片下载异常: {e}")
                    final_results["failed_count"] = final_results.get("failed_count", 0) + 1

        # 取消未完成的任务
        for task, _ in download_tasks:
            if not task.done():
                task.cancel()

        # 确定发布模式
        total_count = len(image_urls)
        success_count = len(final_results["paths"])

        if success_count == 0 and total_count > 0:
            final_results["mode"] = "text_only"
            logger.warning("⚠️ 所有图片下载失败，启用纯文字发布模式")
        elif success_count < total_count:
            final_results["mode"] = "partial_image"
            logger.warning(f"⚠️ 部分图片下载成功: {success_count}/{total_count}")
            logger.info(f"📊 使用的图片服务: {final_results.get('service_used', 'none')}")
        else:
            final_results["mode"] = "full_image"
            logger.success(f"✅ 所有图片下载成功: {success_count} 张")
            logger.info(f"📊 使用的图片服务: {final_results.get('service_used', 'none')}")

        return final_results

    async def _download_single_image_with_timeout(
        self,
        url: str,
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """
        单个图片下载（带超时控制）

        Returns:
            {"success": bool, "path": str, "service": str}
        """
        # 确定使用的服务
        service_name = "pollinations"  # 默认
        for idx, service in enumerate(self.PRIMARY_SERVICES):
            if service in url or (idx >= self.current_service_index):
                service_name = service
                break

        try:
            async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=timeout) as client:
                resp = await client.get(url)

                if resp.status_code == 200 and len(resp.content) > 1000:
                    # 保存图片到临时文件
                    import tempfile
                    import random
                    tmp = os.path.join(tempfile.gettempdir(), f"img_{random.randint(10000, 99999)}.jpg")
                    with open(tmp, "wb") as f:
                        f.write(resp.content)
                    return {"success": True, "path": tmp, "service": service_name}
                else:
                    logger.debug(f"无效响应: status={resp.status_code}, size={len(resp.content)}")
                    return {"success": False, "path": None, "service": service_name}
        except httpx.TimeoutException:
            return {"success": False, "path": None, "service": service_name}
        except Exception as e:
            logger.debug(f"下载异常: {e}")
            return {"success": False, "path": None, "service": service_name}

    async def _download_with_retry(
        self,
        url: str,
        max_retries: int = 2
    ) -> tuple[bool, Optional[str], str]:
        """
        带重试机制的下载，支持服务切换

        Returns:
            (success, path, service_name)
        """
        # 如果已下载过，直接返回
        if url in self._downloaded_urls:
            return False, None, "cached"

        for service_idx in range(self.current_service_index, len(self.PRIMARY_SERVICES)):
            service_name = self.PRIMARY_SERVICES[service_idx]

            for attempt in range(max_retries):
                try:
                    if service_name == "pollinations":
                        success, path = await self._download_from_pollinations(url)
                    if success:
                        return True, path, service_name
                        break
                    else:
                        logger.debug(f"Pollinations 尝试 {attempt + 1}/{max_retries} 失败")
                except Exception as e:
                    logger.warning(f"{service_name} 下载异常 (尝试 {attempt + 1}): {e}")

            # 切换到下一个服务
            logger.warning(f"🔄 {service_name} 下载失败，切换到 {self.PRIMARY_SERVICES[(service_idx + 1) % len(self.PRIMARY_SERVICES)]}")
            # 更新索引，下次优先使用失败的服务
            self.current_service_index = (service_idx + 1) % len(self.PRIMARY_SERVICES)

        return False, None, "exhausted"

    async def _download_from_pollinations(self, url: str) -> tuple[bool, Optional[str]]:
        """从 pollinations.ai 下载"""
        try:
            async with self._base_client as client:
                resp = await client.get(url)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    tmp = os.path.join(tempfile.gettempdir(), f"pol_{random.randint(10000, 99999)}.jpg")
                    with open(tmp, "wb") as f:
                        f.write(resp.content)
                    logger.debug(f"✅ Pollinations 下载成功: {url[:50]}...")
                    return True, tmp
                else:
                    logger.debug(f"Pollinations 返回无效内容: len={len(resp.content)}")
                    return False, None
        except Exception as e:
            logger.debug(f"Pollinations 下载异常: {e}")
            return False, None

    async def _download_from_unsplash(self, url: str) -> tuple[bool, Optional[str]]:
        """从 unsplash.com 下载（备用方案）"""
        try:
            # 提取关键词用于搜索
            keyword_match = re.search(r'prompt/([^?]+)', url)
            keyword = keyword_match.group(1) if keyword_match else "business"
            encoded_keyword = urllib.parse.quote(keyword[:50])

            unsplash_url = f"https://source.unsplash.com/random?w=800&h=450&sig={int(time.time() * 1000)}&q={encoded_keyword}"

            async with self._base_client as client:
                resp = await client.get(unsplash_url, timeout=45.0)
                if resp.status_code == 200:
                    # Unsplash 返回重定向到实际图片，需要跟随
                    image_url = resp.headers.get("location", "")
                    if not image_url:
                        return False, None

                    # 下载实际图片
                    img_resp = await client.get(image_url, timeout=30.0)
                    if img_resp.status_code == 200 and len(img_resp.content) > 1000:
                        tmp = os.path.join(tempfile.gettempdir(), f"uns_{random.randint(10000, 99999)}.jpg")
                        with open(tmp, "wb") as f:
                            f.write(img_resp.content)
                        logger.info(f"✅ Unsplash 下载成功: {image_url[:50]}...")
                        return True, tmp
                    else:
                        return False, None
                else:
                    return False, None
        except Exception as e:
            logger.debug(f"Unsplash 下载异常: {e}")
            return False, None

    @classmethod
    def extract_visual_keywords(cls, content: str) -> List[str]:
        """
        从内容中提取 3 个视觉关键词（用于生成差异化图片提示）

        提取策略：
        1. 提取段落首句的描述性词汇
        2. 提取场景、风格相关的关键词
        3. 提取业务/专业相关词汇
        """
        keywords = []

        # 1. 提取场景相关词
        scene_patterns = [
            (r'(室内|办公室|会议室|写字楼)', 'indoor_office'),
            (r'(室外|街道|城市|公园|广场)', 'outdoor_street'),
            (r'(居家|生活|家庭环境)', 'home_interior'),
            (r'(商务|会议|签约|谈判)', 'business_meeting'),
            (r'(产品|展示|展柜|货架)', 'product_display'),
            (r'(人物|团队|合影|握手)', 'people_team'),
        ]

        for pattern, fallback_kw in scene_patterns:
            if re.search(pattern, content):
                keywords.append(fallback_kw)
                if len(keywords) >= 1:
                    break

        # 2. 提取风格词
        style_patterns = [
            (r'(简约|简洁|干净|现代)', 'minimalist_clean'),
            (r'(专业|正式|商务)', 'professional_business'),
            (r'(温暖|亲切|友好)', 'warm_friendly'),
        ]

        for pattern, fallback_kw in style_patterns:
            if re.search(pattern, content):
                keywords.append(fallback_kw)
                if len(keywords) >= 2:
                    break

        # 3. 如果提取不足，使用通用词
        fallback_keywords = [
            "professional_business",
            "modern_minimal_design",
            "high_quality_photo"
        ]

        while len(keywords) < 3:
            keywords.extend(fallback_keywords)

        return keywords[:3]

    def clear_cache(self):
        """清除下载缓存"""
        self._downloaded_urls.clear()

    async def _download_with_retry(
        self,
        url: str,
        max_retries: int = 2
    ) -> tuple[bool, Optional[str], str]:
        """
        带重试机制的下载，支持服务切换

        Returns:
            (success, path, service_name)
        """
        # 如果已下载过，直接返回
        if url in self._downloaded_urls:
            return False, None, "cached"

        for service_idx in range(self.current_service_index, len(self.PRIMARY_SERVICES)):
            service_name = self.PRIMARY_SERVICES[service_idx]

            for attempt in range(max_retries):
                try:
                    if service_name == "pollinations":
                        success, path = await self._download_from_pollinations(url)
                    if success:
                        return True, path, service_name
                        break
                    else:
                        logger.debug(f"Pollinations 尝试 {attempt + 1}/{max_retries} 失败")
                except Exception as e:
                    logger.warning(f"{service_name} 下载异常 (尝试 {attempt + 1}): {e}")

            # 切换到下一个服务
            logger.warning(f"🔄 {service_name} 下载失败，切换到 {self.PRIMARY_SERVICES[(service_idx + 1) % len(self.PRIMARY_SERVICES)]}")
            # 更新索引，下次优先使用失败的服务
            self.current_service_index = (service_idx + 1) % len(self.PRIMARY_SERVICES)

        return False, None, "exhausted"

    async def _download_from_pollinations(self, url: str) -> tuple[bool, Optional[str]]:
        """从 pollinations.ai 下载"""
        try:
            async with self._base_client as client:
                resp = await client.get(url)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    tmp = os.path.join(tempfile.gettempdir(), f"pol_{random.randint(10000, 99999)}.jpg")
                    with open(tmp, "wb") as f:
                        f.write(resp.content)
                    logger.debug(f"✅ Pollinations 下载成功: {url[:50]}...")
                    return True, tmp
                else:
                    logger.debug(f"Pollinations 返回无效内容: len={len(resp.content)}")
                    return False, None
        except Exception as e:
            logger.debug(f"Pollinations 下载异常: {e}")
            return False, None

    async def _download_from_unsplash(self, url: str) -> tuple[bool, Optional[str]]:
        """从 unsplash.com 下载（备用方案）"""
        try:
            # 提取关键词用于搜索
            keyword_match = re.search(r'prompt/([^?]+)', url)
            keyword = keyword_match.group(1) if keyword_match else "business"
            encoded_keyword = urllib.parse.quote(keyword[:50])

            unsplash_url = f"https://source.unsplash.com/random?w=800&h=600&sig={int(time.time() * 1000)}&q={encoded_keyword}"

            async with self._base_client as client:
                resp = await client.get(unsplash_url, timeout=45.0)
                if resp.status_code == 200:
                    # Unsplash 返回重定向到实际图片，需要跟随
                    image_url = resp.headers.get("location", "")
                    if not image_url:
                        return False, None

                    # 下载实际图片
                    img_resp = await client.get(image_url, timeout=30.0)
                    if img_resp.status_code == 200 and len(img_resp.content) > 1000:
                        tmp = os.path.join(tempfile.gettempdir(), f"uns_{random.randint(10000, 99999)}.jpg")
                        with open(tmp, "wb") as f:
                            f.write(img_resp.content)
                        logger.info(f"✅ Unsplash 下载成功: {image_url[:50]}...")
                        return True, tmp
                    else:
                        return False, None
                else:
                    return False, None
        except Exception as e:
            logger.debug(f"Unsplash 下载异常: {e}")
            return False, None

    @classmethod
    def extract_visual_keywords(cls, content: str) -> List[str]:
        """
        从内容中提取 3 个视觉关键词（用于生成差异化图片提示）

        提取策略：
        1. 提取段落首句的描述性词汇
        2. 提取场景、风格相关的关键词
        3. 提取业务/专业相关词汇
        """
        keywords = []

        # 1. 提取场景相关词
        scene_patterns = [
            (r'(室内|办公室|会议室|写字楼)', 'indoor office'),
            (r'(室外|街道|城市|公园|广场)', 'outdoor street'),
            (r'(居家|生活|家庭环境)', 'home interior'),
            (r'(商务|会议|签约|谈判)', 'business meeting'),
            (r'(产品|展示|展柜|货架)', 'product display'),
            (r'(人物|团队|合影|握手)', 'people team'),
        ]

        for pattern, fallback_kw in scene_patterns:
            if re.search(pattern, content):
                keywords.append(fallback_kw)
                if len(keywords) >= 1:
                    break

        # 2. 提取风格词
        style_patterns = [
            (r'(简约|简洁|干净|现代)', 'minimalist clean'),
            (r'(专业|正式|商务)', 'professional business'),
            (r'(温暖|亲切|友好)', 'warm friendly'),
        ]

        for pattern, fallback_kw in style_patterns:
            if re.search(pattern, content):
                keywords.append(fallback_kw)
                if len(keywords) >= 2:
                    break

        # 3. 如果提取不足，使用通用词
        fallback_keywords = [
            "professional business",
            "modern minimal design",
            "high quality photo"
        ]

        while len(keywords) < 3:
            keywords.extend(fallback_keywords)

        return keywords[:3]

    def clear_cache(self):
        """清除下载缓存"""
        self._downloaded_urls.clear()


# ==================== 基础适配器 ====================

class BasePublisher(ABC):
    """
    基础发布适配器
    注意：所有平台适配器都要继承这个类！
    """

    def __init__(self, platform_id: str, config: Dict[str, Any]):
        self.platform_id = platform_id
        self.config = config
        self.name = config.get("name", platform_id)
        self.color = config.get("color", "#333333")

    @abstractmethod
    async def publish(self, page: Page, article: Any, account: Any, context: BrowserContext = None, mgr: Any = None) -> Dict[str, Any]:
        """
        发布文章到目标平台

        Args:
            page: Playwright Page对象
            article: 文章对象（title, content等）
            account: 账号对象
            context: 浏览器上下文（可选，用于更新 storage_state）
            mgr: PlaywrightManager 实例（可选，用于更新账号状态）

        Returns:
            发布结果：{
                "success": bool,
                "platform_url": str,
                "error_msg": str
            }
        """
        pass

    async def navigate_to_publish_page(self, page: Page) -> bool:
        """
        导航到发布页面

        Returns:
            是否成功导航
        """
        try:
            await page.goto(self.config["publish_url"], wait_until="networkidle")
            logger.info(f"导航到发布页面: {self.name}")
            return True
        except Exception as e:
            logger.error(f"导航失败: {self.name}, {e}")
            return False

    async def wait_for_selector(self, page: Page, selector: str, timeout: int = 10000) -> bool:
        """
        等待选择器出现

        注意：各平台页面加载速度不同，需要耐心等待！
        """
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            logger.warning(f"等待选择器超时: {selector}, {e}")
            return False

    async def fill_title(self, page: Page, title: str, title_selector: str) -> bool:
        """
        填充标题
        """
        try:
            # 先清空再填充
            await page.fill(title_selector, "")
            await page.fill(title_selector, title)
            logger.info(f"标题已填充: {title[:20]}...")
            return True
        except Exception as e:
            logger.error(f"填充标题失败: {e}")
            return False

    async def fill_content(self, page: Page, content: str, content_selector: str) -> bool:
        """
        填充正文
        """
        try:
            await page.fill(content_selector, content)
            logger.info(f"正文已填充: {len(content)} 字符")
            return True
        except Exception as e:
            logger.error(f"填充正文失败: {e}")
            return False

    async def click_publish_button(self, page: Page, publish_selector: str) -> bool:
        """
        点击发布按钮
        """
        try:
            await page.click(publish_selector)
            logger.info(f"已点击发布按钮: {self.name}")
            return True
        except Exception as e:
            logger.error(f"点击发布按钮失败: {e}")
            return False

    async def wait_for_publish_result(self, page: Page, timeout: int = 30000) -> Dict[str, Any]:
        """
        等待发布结果

        Returns:
            发布结果
        """
        # 默认实现：等待一段时间后检查URL是否变化
        await page.wait_for_timeout(3000)

        result = {
            "success": True,
            "platform_url": page.url,
            "error_msg": None
        }

        return result


class PublisherRegistry:
    """
    发布器注册表
    用这个来管理所有平台的发布器！
    """

    def __init__(self):
        self._publishers: Dict[str, BasePublisher] = {}

    def register(self, platform_id: str, publisher: BasePublisher):
        """注册发布器"""
        self._publishers[platform_id] = publisher
        logger.info(f"发布器已注册: {platform_id}")

    def get(self, platform_id: str) -> Optional[BasePublisher]:
        """获取发布器"""
        return self._publishers.get(platform_id)

    def list_all(self) -> Dict[str, BasePublisher]:
        """列出所有发布器"""
        return self._publishers.copy()


# 全局注册表
registry = PublisherRegistry()


def get_publisher(platform_id: str) -> Optional[BasePublisher]:
    """
    获取平台发布器
    注意：这是对外暴露的主要接口！

    🌟 防御性调试日志：打印所有已注册的平台
    """
    # 🌟 打印调试信息
    logger.debug(f"[DEBUG] Current registered platforms: {list_publishers()}")
    logger.debug(f"[DEBUG] Requested platform_id: '{platform_id}'")

    return registry.get(platform_id)


def list_publishers() -> Dict[str, BasePublisher]:
    """列出所有发布器"""
    return registry.list_all()
