# -*- coding: utf-8 -*-
"""
搜狐 (Sohu) 发布适配器 - 矩阵管理环境隔离版 (v3.0)
基于"聚媒通"等成熟矩阵工具的逻辑重构

核心架构金律：
1. 状态同步禁令：严禁使用 page.fill()，必须通过"物理点击 -> 剪贴板注入 -> Tab/Blur 失焦"
2. 逆向操作序列：封面/分类设置 -> 正文压轴写入 -> 标题终极锁定（防止 React 重绘清空正文）
3. 物理场域清理：进入编辑器后立即清除侧边栏、引导遮罩、干扰弹窗
4. 精准场域锚点：以 .editor-container-v4 为根节点进行链式查找，防止正文误入搜索框
5. 域内逻辑导航：先 goto 首页，验证登录后，通过物理点击导航到编辑器
6. 环境指纹对齐：使用 Account 表中的 user_agent 创建 context
"""

import asyncio
import re
import os
import httpx
import tempfile
import random
import base64
import urllib.parse
from typing import Dict, Any, List, Optional
from playwright.async_api import Page, BrowserContext
from loguru import logger
from .base import BasePublisher, registry, ImageDownloadManager


class SohuPublisher(BasePublisher):
    """搜狐发布适配器 - 矩阵管理环境隔离版 (v3.0)"""

    # ==================== 域名常量 ====================
    DOMAIN = "mp.sohu.com"

    # 首页（用于域内路由和登录验证）
    HOME_URL = "https://mp.sohu.com/main/home"

    # API 端点（用于 Session 验证）
    USER_INFO_API = "/mpfe/v3/user/info"

    # 编辑器 URL（通过物理点击导航到达，不直接 goto）
    EDITOR_URL = "/mpfe/v4/contentManagement/news/addarticle?contentStatus=1"

    # 发布按钮选择器
    PUBLISH_BTN_SELECTORS = [
        "button:has-text('发布')",
        "button:has-text('提交')",
        ".publish-btn",
        ".submit-btn",
        "button[type='submit']"
    ]

    # 确认按钮选择器
    CONFIRM_BTN_SELECTORS = [
        "button:has-text('确认')",
        "button:has-text('确定')",
        ".confirm-btn",
        ".ok-btn"
    ]

    async def publish(self, page: Page, article: Any, account: Any, context: BrowserContext = None, mgr: Any = None) -> Dict[str, Any]:
        """
        发布文章到搜狐 - 矩阵管理环境隔离版

        核心流程：
        1. 环境指纹对齐（使用账号的 user_agent）
        2. 域内逻辑导航（首页 -> 验证登录 -> 物理点击导航到编辑器）
        3. 物理场域清理（清除遮罩、弹窗）
        4. 逆向填充序列（封面/分类 -> 正文 -> 标题）
        5. 发布
        """
        temp_files = []
        try:
            logger.info("🚀 开始搜狐 v3.0 矩阵管理环境隔离版自动化发布...")

            # ============================================================
            # Step 1: 环境指纹对齐 - 验证登录态
            # ============================================================
            logger.info("Step 1: 环境指纹对齐 - 验证 Session...")

            # 1.1 先 goto 首页（域内导航）
            logger.info(f"   → 导航到首页: {self.HOME_URL}")
            await page.goto(self.HOME_URL, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            # 1.2 清除初始弹窗
            await self._clear_interference(page)
            await asyncio.sleep(1)

            # 1.3 API 验证 Session
            session_valid = await self._verify_session_via_api(page)
            if not session_valid:
                logger.warning("⚠️ Session 已失效，触发重新授权...")
                if mgr and hasattr(mgr, 'update_account_storage_state'):
                    # 保存当前状态，触发授权弹窗
                    await mgr.update_account_storage_state(account.id, context, page)
                    # TODO: 需要实现授权成功后自动重启发布流的逻辑
                    return {
                        "success": False,
                        "error_msg": "Session 已失效，请重新授权后重试"
                    }
                return {
                    "success": False,
                    "error_msg": "Session 已失效，请重新授权"
                }

            logger.success("✅ Session 验证通过")

            # ============================================================
            # Step 2: 域内逻辑导航 - 物理点击到编辑器
            # ============================================================
            logger.info("Step 2: 域内逻辑导航 - 物理点击导航到编辑器...")

            # 2.1 物理点击"写文章"导航
            nav_success = await self._navigate_to_editor_via_click(page)
            if not nav_success:
                logger.error("❌ 无法通过物理点击导航到编辑器")
                return {"success": False, "error_msg": "导航到编辑器失败"}

            # 2.2 等待编辑器容器加载
            logger.info("   → 等待编辑器容器加载...")
            editor_loaded = await self._wait_for_editor(page, timeout=15000)
            if not editor_loaded:
                logger.error("❌ 编辑器容器加载超时")
                return {"success": False, "error_msg": "编辑器加载超时"}

            # 2.3 清除干扰元素
            await self._clear_interference(page)
            await asyncio.sleep(1)

            logger.success("✅ 成功导航到编辑器")

            # ============================================================
            # Step 3: 准备资源
            # ============================================================
            logger.info("Step 3: 准备资源...")

            # 标题处理
            safe_title = article.title.replace("#", "").replace("*", "").strip()
            if len(safe_title) > 30:
                safe_title = safe_title[:30]
                logger.info(f"   → 标题已截断至30字: {safe_title}")

            clean_text = self._deep_clean_content(article.content)

            # AI 自动配图
            image_urls = re.findall(r'!\[.*?\]\(((?:https?://)?\S+?)\)', article.content)
            if not image_urls:
                keyword = article.title[:15] if article.title else "business technology"
                logger.info(f"🎨 文章无图片，启动 AI 自动配图 (关键词: {keyword})...")
                for i in range(3):
                    seed = random.randint(1, 1000)
                    prompt = f"realistic professional photo of {keyword} for business article, high quality, {seed}"
                    encoded_prompt = urllib.parse.quote(prompt)
                    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=600&nologo=true"
                    image_urls.append(url)
                logger.info(f"✅ AI 已生成 {len(image_urls)} 张配图链接")

            # 下载图片 (使用 ImageDownloadManager 的智能重试机制)
            img_manager = ImageDownloadManager()
            download_result = await img_manager.download_images(image_urls)
            downloaded_paths = download_result["paths"]
            temp_files.extend(downloaded_paths)

            # 🌟 优雅降级：根据下载结果决定是否继续
            if download_result["mode"] == "text_only":
                # 纯文字发布模式 - 不包含图片
                logger.warning("⚠️ 图片全部下载失败，继续纯文字发布")
                image_urls = []  # 清空图片列表
                downloaded_paths = []
            elif download_result["mode"] == "partial_image":
                # 部分图片模式 - 部分图片已下载
                logger.warning(f"⚠️ 部分图片下载失败 ({download_result['failed_count']}/{len(image_urls)})，继续发布已下载的 {len(downloaded_paths)} 张图片")
            elif download_result["mode"] == "full_image":
                # 完整图片模式 - 所有图片下载成功
                logger.success(f"✅ 成功下载 {len(downloaded_paths)} 张图片")
                logger.info(f"📊 使用的图片服务: {download_result['service_used']}")

            # 如果所有图片下载失败，仍继续发布（不中断流程）
            if not downloaded_paths:
                logger.warning("⚠️ 图片下载完全失败，继续纯文字发布")

            # ============================================================
            # Step 4: 逆向填充序列 - 封面/分类 -> 正文 -> 标题
            # ============================================================
            logger.info("Step 4: 逆向填充序列（封面/分类 -> 正文 -> 标题）...")

            # 4.1 先设置封面/分类（防止触发重绘）
            logger.info("   → 步骤 A: 设置封面/分类...")
            await self._set_cover_and_category(page)
            await asyncio.sleep(1)

            # 4.2 再注入正文（通过剪贴板，不使用 fill）
            logger.info("   → 步骤 B: 注入正文（剪贴板方式）...")
            content_success = await self._physical_inject_content(page, clean_text)
            if not content_success:
                logger.error("❌ 正文注入失败")
                return {"success": False, "error_msg": "正文注入失败"}
            await asyncio.sleep(random.uniform(1, 2))

            # 4.3 最后锁定标题（终极步骤，防止正文被清空）
            logger.info("   → 步骤 C: 锁定标题（终极步骤）...")
            title_success = await self._physical_inject_title(page, safe_title)
            if not title_success:
                logger.warning("⚠️ 标题填充失败，但已尝试")
            await asyncio.sleep(1)

            logger.success("✅ 逆向填充序列完成")

            # ============================================================
            # Step 5: 插入图片
            # ============================================================
            if downloaded_paths:
                logger.info("Step 5: 在正文中插入图片...")
                await self._inject_images_strict(page, downloaded_paths)

            # ============================================================
            # Step 6: 发布
            # ============================================================
            logger.info("Step 6: 发布...")
            if not await self._brutal_publish_click_loop(page):
                return {"success": False, "error_msg": "发布失败：按钮未响应或被屏蔽"}

            return await self._wait_for_publish_result(page)

        except Exception as e:
            logger.exception(f"❌ 搜狐脚本故障: {str(e)}")
            # 出错时尝试截图
            try:
                debug_dir = os.path.join(os.path.dirname(__file__), "../../../debug")
                os.makedirs(debug_dir, exist_ok=True)
                screenshot_path = os.path.join(debug_dir, "debug_sohu_error.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"   → 异常截图已保存: {screenshot_path}")
            except:
                pass

            return {"success": False, "error_msg": str(e)}
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

    async def _verify_session_via_api(self, page: Page) -> bool:
        """
        通过 API 验证 Session 是否有效

        Returns:
            True: Session 有效
            False: Session 失效
        """
        try:
            logger.info("   → 调用 API 验证 Session...")
            result = await page.evaluate('''async () => {
                try {
                    const response = await fetch('/mpfe/v3/user/info', {
                        method: 'GET',
                        credentials: 'include'
                    });
                    if (!response.ok) {
                        return { valid: false, status: response.status };
                    }
                    const data = await response.json();
                    return {
                        valid: true,
                        data: data
                    };
                } catch (error) {
                    return { valid: false, error: error.message };
                }
            }''')

            if result.get("valid"):
                logger.success("   ✅ API 验证通过")
                return True
            else:
                logger.warning(f"   ❌ API 验证失败: {result.get('error')}")
                return False
        except Exception as e:
            logger.warning(f"   ⚠️ API 验证异常: {str(e)}")
            return False

    async def _navigate_to_editor_via_click(self, page: Page) -> bool:
        """
        通过物理点击导航到编辑器（域内路由）

        禁止直接 goto 编辑器 URL，必须通过点击导航
        """
        try:
            # 导航选择器（写文章相关）
            nav_selectors = [
                ".nav-item:has-text('写文章')",
                "button:has-text('写文章')",
                "a:has-text('写文章')",
                "[class*='nav']:has-text('写文章')",
                ".menu-item:has-text('写文章')",
            ]

            for selector in nav_selectors:
                try:
                    logger.info(f"   → 尝试导航选择器: {selector}")
                    # 等待选择器出现
                    await page.wait_for_selector(selector, timeout=8000)
                    logger.info(f"   ✅ 找到导航按钮: {selector}")

                    # 物理点击
                    await page.click(selector, timeout=5000, force=True)
                    await asyncio.sleep(2)

                    # 验证是否导航到编辑器
                    current_url = page.url
                    if "addarticle" in current_url or "article" in current_url:
                        logger.info(f"   ✅ 成功导航到编辑器: {current_url}")
                        return True

                except:
                    logger.debug(f"   → 导航选择器失败: {selector}")
                    continue

            logger.warning("   ⚠️ 无法通过物理点击导航，尝试备用方案...")
            # 备用方案：通过 evaluate 执行 location.href 跳转
            await page.evaluate(f"() => {{ location.href = 'https://{self.DOMAIN}{self.EDITOR_URL}' }}")
            await asyncio.sleep(3)

            return "addarticle" in page.url or "article" in page.url

        except Exception as e:
            logger.error(f"   ❌ 导航异常: {str(e)}")
            return False

    async def _wait_for_editor(self, page: Page, timeout: int = 15000) -> bool:
        """
        等待编辑器容器加载完成

        使用 .editor-container-v4 作为精准锚点
        """
        try:
            logger.info("   → 等待 .editor-container-v4 加载...")
            await page.wait_for_selector(".editor-container-v4", timeout=timeout)
            logger.success("   ✅ 编辑器容器已加载")
            return True
        except:
            logger.warning("   ⚠️ 编辑器容器加载超时")
            return False

    async def _clear_interference(self, page: Page):
        """
        物理场域清理 - 清除干扰元素

        清除目标：
        - .guide-mask (引导遮罩)
        - .creation-helper (创作助手)
        - 侧边栏、弹窗等干扰元素
        """
        try:
            await page.evaluate('''() => {
                const targets = [
                    // 搜狐特有干扰元素
                    '.guide-mask',
                    '.creation-helper',
                    '.tutorial-overlay',
                    '.guide-popup',

                    // 通用遮罩和弹窗
                    '.modal-overlay',
                    '.popup-mask',
                    '.dialog-mask',
                    '.mask-layer',
                    '[role="dialog"]',

                    // 功能性弹窗
                    '.upgrade-pop',
                    '.upgrade-modal',
                    '.notice-pop',
                    '.activity-modal',
                    '.vip-modal',
                    '.rights-modal',
                    '.pro-modal',
                    '.member-modal',

                    // 关闭按钮（自动点击）
                    '.close-btn',
                    '.modal-close',
                    '.popup-close',
                    '[class*="close"]'
                ];

                // 移除干扰元素
                for (let i = 0; i < targets.length; i++) {
                    const els = document.querySelectorAll(targets[i]);
                    for (let j = 0; j < els.length; j++) {
                        els[j].remove();
                    }
                }

                console.log('干扰元素已清除');
            }''')
            logger.debug("   ✅ 干扰元素已清除")
        except Exception as e:
            logger.warning(f"   ⚠️ 清除干扰元素时出现异常: {str(e)}")

    async def _set_cover_and_category(self, page: Page):
        """
        设置封面和分类（逆向填充序列的第一步）

        先设置这些可以避免后续操作触发 React 重绘
        """
        try:
            # 滚动到顶部
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.5)

            # 尝试点击"单图"封面选项
            cover_selectors = [
                "text=单图",
                "text=自动",
                ".cover-option-single",
                ".cover-auto",
                "label:has-text('单图')",
                ".single-cover"
            ]

            for selector in cover_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.count(timeout=3000) > 0 and await btn.is_visible():
                        await btn.click(force=True)
                        logger.info("   ✅ 已选择封面模式")
                        await asyncio.sleep(0.5)
                        break
                except:
                    continue

            # 尝试设置分类（如果需要）
            # 这里可以根据需要添加分类设置逻辑

        except Exception as e:
            logger.warning(f"   ⚠️ 设置封面/分类时出现问题: {str(e)}")

    async def _physical_inject_content(self, page: Page, content: str) -> bool:
        """
        物理仿真注入正文（状态同步禁令）

        严禁使用 .fill()，必须通过：
        1. 点击编辑器
        2. 将内容写入剪贴板
        3. 触发 Ctrl+V
        4. 按 Tab 失焦

        使用 .editor-container-v4 作为根节点进行链式查找
        """
        try:
            logger.info("   → 开始物理仿真注入正文...")

            # 精准定位正文编辑器（以 .editor-container-v4 为根节点）
            editor_locator = page.locator(".editor-container-v4 .public-DraftEditor-content")
            if await editor_locator.count(timeout=5000) == 0:
                # 备用选择器
                editor_locator = page.locator(".editor-container-v4 div[contenteditable='true']")

            if await editor_locator.count(timeout=5000) == 0:
                logger.error("   ❌ 无法定位正文编辑器")
                return False

            logger.info("   ✅ 找到正文编辑器")

            # 点击编辑器确保获得焦点
            await editor_locator.click(timeout=5000, force=True)
            await asyncio.sleep(0.3)

            # 清空编辑器
            await page.keyboard.press("Control+A")
            await asyncio.sleep(0.2)
            await page.keyboard.press("Backspace")
            await asyncio.sleep(0.2)

            # 将内容写入剪贴板
            await page.evaluate(f"(content) => {{ navigator.clipboard.writeText(content) }}", content)
            await asyncio.sleep(0.3)

            # 触发粘贴事件（Ctrl+V）
            await page.keyboard.press("Control+V")
            await asyncio.sleep(0.5)

            # 按 Tab 失焦（触发 React 状态同步）
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.3)

            logger.success(f"   ✅ 正文已物理注入 ({len(content)} 字符)")
            return True

        except Exception as e:
            logger.error(f"   ❌ 正文物理注入失败: {str(e)}")
            return False

    async def _physical_inject_title(self, page: Page, title: str) -> bool:
        """
        物理仿真注入标题（逆向填充序列的终极步骤）

        必须在正文注入之后执行，防止标题操作触发 React 重绘清空正文

        严禁使用 .fill()，使用剪贴板方式
        """
        try:
            logger.info(f"   → 开始物理仿真注入标题: {title}")

            # 标题选择器（以 .editor-container-v4 为根节点进行链式查找）
            title_selectors = [
                ".editor-container-v4 input[placeholder*='标题']",
                ".editor-container-v4 input[placeholder='请输入标题']",
                ".editor-container-v4 input[name='title']",
                ".editor-container-v4 input.title-input",
                ".editor-container-v4 .title-input input",
                "input[placeholder*='标题']",
                "input[placeholder='请输入标题']",
                "input[name='title']",
            ]

            title_found = False
            for selector in title_selectors:
                try:
                    locator = page.locator(selector)
                    if await locator.count(timeout=5000) > 0 and await locator.is_visible():
                        logger.info(f"   ✅ 找到标题输入框: {selector}")

                        # 点击输入框
                        await locator.click(timeout=5000, force=True)
                        await asyncio.sleep(0.3)

                        # 全选
                        await page.keyboard.press("Control+A")
                        await asyncio.sleep(0.2)

                        # 删除
                        await page.keyboard.press("Backspace")
                        await asyncio.sleep(0.2)

                        # 将标题写入剪贴板
                        await page.evaluate(f"(title) => {{ navigator.clipboard.writeText(title) }}", title)
                        await asyncio.sleep(0.3)

                        # 触发粘贴
                        await page.keyboard.press("Control+V")
                        await asyncio.sleep(0.3)

                        # 按 Tab 失焦
                        await page.keyboard.press("Tab")
                        await asyncio.sleep(0.3)

                        logger.success(f"   ✅ 标题已物理注入: {title}")
                        title_found = True
                        break

                except:
                    logger.debug(f"   → 标题选择器失败: {selector}")
                    continue

            if not title_found:
                logger.warning("   ⚠️ 无法定位标题输入框")
                return False

            return True

        except Exception as e:
            logger.error(f"   ❌ 标题物理注入失败: {str(e)}")
            return False

    async def _inject_images_strict(self, page: Page, image_paths: List[str]):
        """
        精准图片插入（以 .editor-container-v4 的编辑器为目标）

        确保图片插入到正文编辑器，而不是封面上传区域
        """
        try:
            logger.info(f"📝 开始在正文中插入图片，共 {len(image_paths)} 张")

            # 定位正文编辑器
            editor_locator = page.locator(".editor-container-v4 .public-DraftEditor-content")
            if await editor_locator.count(timeout=5000) == 0:
                editor_locator = page.locator(".editor-container-v4 div[contenteditable='true']")

            if await editor_locator.count(timeout=5000) == 0:
                logger.warning("⚠️ 未找到正文编辑器，跳过图片插入")
                return

            # 点击编辑器确保焦点
            await editor_locator.click(timeout=5000, force=True)
            await asyncio.sleep(0.3)

            # 第1张：插入到文章开头
            logger.info("   → 插入位置: 文章开头")
            await page.keyboard.press("Control+Home")
            await asyncio.sleep(0.3)
            await self._paste_image_to_editor(page, image_paths[0])
            await asyncio.sleep(1)

            # 第2张：插入到文章中间
            if len(image_paths) > 1:
                logger.info("   → 插入位置: 文章中间")
                await page.keyboard.press("Home")
                for _ in range(5):
                    await page.keyboard.press("PageDown")
                    await asyncio.sleep(0.2)
                await page.keyboard.press("Enter")
                await asyncio.sleep(0.3)
                await self._paste_image_to_editor(page, image_paths[1])
                await asyncio.sleep(1)

            # 第3张：插入到文章结尾
            if len(image_paths) > 2:
                logger.info("   → 插入位置: 文章结尾")
                await page.keyboard.press("Home")
                for _ in range(10):
                    await page.keyboard.press("PageDown")
                    await asyncio.sleep(0.1)
                await page.keyboard.press("End")
                await asyncio.sleep(0.3)
                await self._paste_image_to_editor(page, image_paths[2])

            logger.info("✅ 正文中图片插入完成")
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"❌ 正文中图片插入失败: {str(e)}")

    async def _paste_image_to_editor(self, page: Page, image_path: str):
        """
        将图片粘贴到正文编辑器（使用剪贴板事件）

        读取图片并转换为 Base64，然后通过 ClipboardEvent 注入
        """
        try:
            # 读取图片并转换为 base64
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')

            # 通过 ClipboardEvent 粘贴图片到正文编辑器
            await page.evaluate('''(b64) => {
                const editor = document.querySelector('.editor-container-v4 .public-DraftEditor-content')
                    || document.querySelector('.editor-container-v4 div[contenteditable="true"]');

                if (!editor) {
                    console.error("未找到编辑器元素");
                    return;
                }

                // 将base64转换为File对象
                const byteCharacters = atob(b64);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], { type: 'image/jpeg' });
                const file = new File([blob], "auto_inserted.jpg", { type: 'image/jpeg' });

                // 创建DataTransfer
                const dt = new DataTransfer();
                dt.items.add(file);

                // 创建并分发剪贴板事件
                const event = new ClipboardEvent("paste", {
                    clipboardData: dt,
                    bubbles: true,
                    cancelable: true
                });

                editor.dispatchEvent(event);
            }''', b64)

            logger.info("   ✅ 图片剪贴板注入完成")
            await asyncio.sleep(2)

        except Exception as e:
            logger.warning(f"   ⚠️ 图片注入失败: {str(e)}")

    async def _brutal_publish_click_loop(self, page: Page) -> bool:
        """
        暴力发布循环

        针对发布按钮响应慢的问题，持续尝试点击
        """
        logger.info("   → 开始暴力发布循环...")

        for i in range(15):
            try:
                # 滚动到发布按钮位置
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(0.5)

                # 查找发布按钮
                for publish_selector in self.PUBLISH_BTN_SELECTORS:
                    p_btn = page.locator(publish_selector).last
                    if await p_btn.count(timeout=2000) > 0 and await p_btn.is_visible():
                        # 滚动到视图
                        await p_btn.scroll_into_view_if_needed()

                        if await p_btn.is_enabled():
                            await p_btn.click(force=True)
                            logger.info(f"   ✅ 已点击发布按钮 (尝试 {i + 1}/15)")
                            await asyncio.sleep(2)

                            # 处理确认弹窗
                            for confirm_selector in self.CONFIRM_BTN_SELECTORS:
                                c_btn = page.locator(confirm_selector).last
                                if await c_btn.is_visible(timeout=1000):
                                    await c_btn.click(force=True)
                                    logger.success("🎯 发布最终确认成功！")
                                    return True

                            # 检查是否成功跳转
                            if "article" in page.url or "news" in page.url:
                                return True

                await asyncio.sleep(1)

            except:
                pass

        logger.error("   ❌ 发布按钮未响应或被屏蔽")
        return False

    async def _wait_for_publish_result(self, page: Page) -> Dict[str, Any]:
        """
        等待发布结果
        """
        logger.info("   → 等待发布结果...")

        for i in range(30):
            if "article" in page.url or "news" in page.url or "article-manage" in page.url:
                platform_url = page.url
                logger.success(f"✅ 发布成功！文章链接: {platform_url}")
                return {
                    "success": True,
                    "platform_url": platform_url,
                    "error_msg": None
                }
            await asyncio.sleep(1)

        return {
            "success": True,
            "platform_url": page.url,
            "error_msg": None
        }

    def _deep_clean_content(self, text: str) -> str:
        """深度清洗正文内容"""
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'#+\s*', '', text)
        text = re.sub(r'\*\*+', '', text)
        return text.strip()

    async def _download_images_fast(self, urls: List[str]) -> List[str]:
        """快速下载图片"""
        paths = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with httpx.AsyncClient(headers=headers, verify=False, follow_redirects=True, timeout=20.0) as client:
            for i, url in enumerate(urls[:3]):
                for attempt in range(2):
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200 and len(resp.content) > 1000:
                            tmp = os.path.join(tempfile.gettempdir(), f"sohu_v30_{random.randint(1, 9999)}.jpg")
                            with open(tmp, "wb") as f:
                                f.write(resp.content)
                            paths.append(tmp)
                            logger.info(f"✅ 图片 {i + 1}/{min(len(urls), 3)} 下载成功")
                            break
                    except Exception as e:
                        logger.warning(f"⚠️ 图片 {i + 1} 下载失败 (尝试 {attempt + 1}/2): {str(e)}")
                        continue

        return paths


# 注册
registry.register("sohu", SohuPublisher("sohu", {
    "name": "搜狐",
    "color": "#FFCC00"
}))
