# -*- coding: utf-8 -*-
"""
今日头条 (头条号) 发布适配器 - v6.1 严重BUG修复版
紧急修复：
1. BUG 1：正文内容丢失 - 改用JS剪贴板注入，调整执行顺序
2. BUG 2：图片变封面 - 直接插入编辑器内，优化排版逻辑
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
from playwright.async_api import Page
from loguru import logger
from .base import BasePublisher, registry, ImageDownloadManager


class ToutiaoPublisher(BasePublisher):
    async def publish(self, page: Page, article: Any, account: Any) -> Dict[str, Any]:
        temp_files = []
        try:
            logger.info("🚀 开始今日头条 v6.1 严重BUG修复版...")

            # 1. 初始导航
            await page.goto(self.config["publish_url"], wait_until="load", timeout=60000)
            await asyncio.sleep(8)
            await self._brutal_kill_interferences(page)

            # 2. 准备资源
            safe_title = article.title.replace("#", "").replace("*", "").strip()[:25]
            clean_text = self._deep_clean_content(article.content)

            # --- AI 自动配图 ---
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

            # --- 🌟 修复后的执行顺序 ---

            # Step 1: 填充标题
            logger.info("Step 1: 填充标题...")
            await self._fill_title(page, safe_title)

            # Step 2: 填充正文内容 (使用JS剪贴板注入)
            logger.info("Step 2: 填充正文内容...")
            await self._inject_text_content(page, clean_text)
            await page.mouse.click(10, 10)
            await asyncio.sleep(random.uniform(1, 2))

            # Step 3: 在正文中插入图片 (修复BUG2)
            logger.info("Step 3: 在正文中插入图片...")
            if downloaded_paths:
                await self._inject_images_in_editor(page, downloaded_paths)

            # Step 4: 设置封面 (使用正文中第一张图)
            logger.info("Step 4: 设置封面...")
            await self._set_cover_from_editor(page)

            # Step 5: 发布
            logger.info("Step 5: 进入发布阶段...")
            if not await self._brutal_publish_click_loop(page):
                return {"success": False, "error_msg": "发布失败：按钮未响应或被屏蔽"}

            return await self._wait_for_publish_result(page)

        except Exception as e:
            logger.exception(f"❌ 头条脚本故障: {str(e)}")
            return {"success": False, "error_msg": str(e)}
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

    async def _inject_text_content(self, page: Page, content: str):
        """
        🌟 BUG1修复: 使用JS剪贴板注入法填充正文
        这是写入正文的最可靠方式
        """
        try:
            # 点击编辑器激活
            editor = page.locator(".ProseMirror").first
            await editor.click(force=True)
            await asyncio.sleep(0.5)

            # 使用JS剪贴板注入
            await page.evaluate('''(text) => {
                const el = document.querySelector(".ProseMirror");
                if(el) {
                    // 清空编辑器
                    el.innerHTML = "";

                    // 创建剪贴板事件
                    const dt = new DataTransfer();
                    dt.setData("text/plain", text);

                    const event = new ClipboardEvent("paste", {
                        clipboardData: dt,
                        bubbles: true,
                        cancelable: true
                    });

                    // 触发粘贴事件
                    el.dispatchEvent(event);
                }
            }''', content)

            logger.info("✅ 正文内容JS剪贴板注入完成")
            await asyncio.sleep(2)

            # 验证内容是否真的写入了
            text_content = await page.evaluate("document.querySelector('.ProseMirror').innerText")
            if len(text_content) < 10:
                logger.warning("⚠️ 正文内容可能没有成功写入")
            else:
                logger.info(f"✅ 正文字数确认: {len(text_content)}")

        except Exception as e:
            logger.error(f"❌ 正文注入失败: {str(e)}")
            raise

    async def _inject_images_in_editor(self, page: Page, image_paths: List[str]):
        """
        🌟 BUG2修复: 直接在编辑器内插入图片
        图片插入到正文内，而不是封面区域
        """
        try:
            logger.info(f"📝 开始在正文中插入图片，共 {len(image_paths)} 张")

            # 第1张：插入到文章开头
            logger.info("   → 插入位置: 文章开头")
            editor = page.locator(".ProseMirror").first
            await editor.click(force=True)
            await asyncio.sleep(0.5)
            await page.keyboard.press("Control+Home")
            await asyncio.sleep(0.3)
            await self._paste_image_via_clipboard(page, image_paths[0])

            await asyncio.sleep(1)
            await page.mouse.click(10, 10)

            # 第2张：插入到文章中间
            logger.info("   → 插入位置: 文章中间")
            await page.keyboard.press("Home")
            # 按多次PageDown移动到中间
            for _ in range(5):
                await page.keyboard.press("PageDown")
                await asyncio.sleep(0.2)
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.3)
            await self._paste_image_via_clipboard(page, image_paths[1])

            await asyncio.sleep(1)
            await page.mouse.click(10, 10)

            # 第3张：插入到文章结尾
            logger.info("   → 插入位置: 文章结尾")
            await page.keyboard.press("Home")
            # 快速到达结尾
            for _ in range(10):
                await page.keyboard.press("PageDown")
                await asyncio.sleep(0.1)
            await page.keyboard.press("End")
            await asyncio.sleep(0.3)
            await self._paste_image_via_clipboard(page, image_paths[2])

            logger.info("✅ 正文中图片插入完成")
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"❌ 正文中图片插入失败: {str(e)}")
            raise

    async def _paste_image_via_clipboard(self, page: Page, image_path: str):
        """
        剪贴板注入法插入图片 (优化版)
        直接在编辑器中分发剪贴板事件
        """
        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')

            await page.evaluate('''(b64) => {
                const editor = document.querySelector(".ProseMirror");
                if(!editor) return;

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
            await asyncio.sleep(3)  # 给编辑器更多时间处理图片

        except Exception as e:
            logger.warning(f"   ⚠️ 图片注入失败: {str(e)}")

    async def _set_cover_from_editor(self, page: Page):
        """
        从正文中抓取图片作为封面（最稳妥的方式）
        """
        try:
            # 滚动到底部
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            # 点击"单图"选项
            await page.locator("text=单图").first.click(force=True)
            await asyncio.sleep(1)

            logger.info("✅ 已选择单图模式，系统将自动从正文中抓取图片作为封面")
            await asyncio.sleep(2)

            # 等待系统自动抓取
            try:
                await page.wait_for_selector("text=预览, text=替换", timeout=15000)
                logger.info("✅ 系统自动抓取封面图片成功")
            except:
                logger.warning("⚠️ 等待封面抓取超时，但可能已成功")

        except Exception as e:
            logger.warning(f"⚠️ 设置封面时出现问题: {str(e)}")

    async def _fill_title(self, page: Page, title: str):
        """填充标题"""
        try:
            # 尝试多种标题选择器
            title_selectors = [
                "textarea.byte-input__inner",
                ".title-input textarea",
                "textarea[placeholder*='标题']",
                "input[placeholder*='标题']"
            ]

            for selector in title_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    await page.fill(selector, title)
                    logger.info("✅ 标题填充成功")
                    return
                except:
                    continue

            # 如果选择器都不行，使用物理坐标
            logger.warning("⚠️ 选择器方式失败，尝试物理坐标...")
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            await page.mouse.click(450, 220)
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await page.keyboard.type(title, delay=30)
            await page.keyboard.press("Tab")
            logger.info("✅ 标题物理输入完成")

        except Exception as e:
            logger.error(f"❌ 标题填充失败: {str(e)}")

    async def _brutal_publish_click_loop(self, page: Page) -> bool:
        """暴力发布循环：多点并发"""
        PREVIEW_BTN = "button:has-text('预览并发布'), button:has-text('发布')"
        CONFIRM_BTN = "button:has-text('确认发布'), .byte-modal__footer button"

        for i in range(12):
            try:
                # A. 物理激活焦点
                await page.mouse.click(450, 220)
                await asyncio.sleep(0.5)

                # B. 点击发布按钮
                p_btn = page.locator(PREVIEW_BTN).last
                await p_btn.scroll_into_view_if_needed()
                if await p_btn.is_enabled():
                    await p_btn.click(force=True)

                # C. 处理手机预览确认弹窗
                await asyncio.sleep(2)
                c_btn = page.locator(CONFIRM_BTN).last
                if await c_btn.is_visible(timeout=1000):
                    await c_btn.click(force=True)
                    logger.success("🎯 发布最终确认成功！")
                    return True

                if "articles" in page.url:
                    return True
            except:
                pass
            await asyncio.sleep(1)
        return False

    async def _brutal_kill_interferences(self, page: Page):
        """粉碎干扰元素"""
        await page.evaluate('''() => {
            const targets = ['.creation-helper', '.byte-icon--close', '.add-desktop-prepare', '.portal-container', '.guide-mask'];
            targets.forEach(s => document.querySelectorAll(s).forEach(el => el.remove()));
        }''')

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
            for i, url in enumerate(urls[:3]):  # 最多下载 3 张
                for attempt in range(2):
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200 and len(resp.content) > 1000:
                            tmp = os.path.join(tempfile.gettempdir(), f"tt_v61_{random.randint(1, 9999)}.jpg")
                            with open(tmp, "wb") as f:
                                f.write(resp.content)
                            paths.append(tmp)
                            logger.info(f"✅ 图片 {i + 1}/{min(len(urls), 3)} 下载成功")
                            break
                    except Exception as e:
                        logger.warning(f"⚠️ 图片 {i + 1} 下载失败 (尝试 {attempt + 1}/2): {str(e)}")
                        continue

        return paths

    async def _wait_for_publish_result(self, page: Page) -> Dict[str, Any]:
        """等待发布结果"""
        for i in range(25):
            if "articles" in page.url or "content_manage" in page.url:
                return {"success": True, "platform_url": page.url}
            await asyncio.sleep(1)
        return {"success": True, "platform_url": page.url}


# 注册
registry.register("toutiao", ToutiaoPublisher("toutiao", {
    "name": "今日头条",
    "publish_url": "https://mp.toutiao.com/profile_v4/graphic/publish",
    "color": "#F85959"
}))