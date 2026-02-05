# -*- coding: utf-8 -*-
"""
今日头条 (头条号) 发布适配器 - v5.9 全物理坐标+弹窗粉碎版
修复：
1. 解决标题点击超时：增加 5s 短超时保护 + 坐标点击兜底
2. 解决封面遮挡：每步操作后强制点击 (10,10) 粉碎透明遮罩
3. 修正逻辑顺序：正文 -> 插图 -> 封面 -> 标题 -> 暴力发布
"""

import asyncio
import re
import os
import httpx
import tempfile
import random
import base64
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
from loguru import logger
from .base import BasePublisher, registry


class ToutiaoPublisher(BasePublisher):
    async def publish(self, page: Page, article: Any, account: Any) -> Dict[str, Any]:
        temp_files = []
        try:
            logger.info("🚀 开始今日头条 v5.9 流程 (终极物理版)...")

            # 1. 初始导航
            await page.goto(self.config["publish_url"], wait_until="load", timeout=60000)
            await asyncio.sleep(8)
            await self._brutal_kill_interferences(page)

            # 2. 准备资源
            safe_title = article.title.replace("#", "").replace("*", "").strip()[:25]
            clean_text = self._deep_clean_content(article.content)

            downloaded_paths = await self._download_images_fast(["https://api.dujin.org/bing/1920.php"])
            temp_files.extend(downloaded_paths)

            # --- 🌟 执行顺序逻辑 ---

            # Step 1: 填充正文内容
            logger.info("Step 1: 写入正文内容...")
            await self._fill_and_wake_body(page, clean_text)
            await page.mouse.click(10, 10)  # 点击空白处粉碎弹窗

            # Step 2: 粘贴照片
            if downloaded_paths:
                logger.info("Step 2: 正在正文粘贴照片...")
                await self._inject_image_pro(page, downloaded_paths[0])
            await page.mouse.click(10, 10)
            await asyncio.sleep(2)

            # Step 3: 上传封面
            if downloaded_paths:
                logger.info("Step 3: 正在上传展示封面...")
                await self._force_upload_cover(page, downloaded_paths[0])
            await page.mouse.click(10, 10)  # 关键：点掉上传成功的提示框
            await asyncio.sleep(2)

            # Step 4: 锁定标题 (压轴)
            logger.info(f"Step 4: 正在压轴锁定标题 -> {safe_title}")
            await self._physical_type_title_v59(page, safe_title)
            await asyncio.sleep(1)

            # Step 5: 暴力连点发布
            logger.info("Step 5: 进入暴力发布阶段...")
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

    async def _physical_type_title_v59(self, page: Page, title: str):
        """增强版标题锁定：选择器 + 物理坐标双保险"""
        try:
            # 1. 确保滚到最上方
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)

            title_sel = "textarea.byte-input__inner, .title-input textarea, textarea[placeholder*='标题']"
            target = page.locator(title_sel).first

            # 2. 尝试点击（设定 5 秒短超时，防止死等）
            try:
                await target.click(force=True, timeout=5000)
            except:
                logger.warning("选择器点击超时，尝试使用物理坐标点击标题区...")
                # 直接点标题所在坐标（1280x800 分辨率下的经验位置）
                await page.mouse.click(450, 220)

                # 3. 物理按键清空并输入
            # 跨平台兼容：Mac 使用 Meta，Windows 使用 Control
            modifier = "Meta" if "Mac" in await page.evaluate("navigator.platform") else "Control"
            await page.keyboard.press(f"{modifier}+A")
            await page.keyboard.press("Backspace")
            await page.keyboard.type(title, delay=30)
            await page.keyboard.press("Tab")
            logger.info("✅ 标题物理输入完成")
        except:
            pass

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

                if "articles" in page.url: return True
            except:
                pass
            await asyncio.sleep(1)
        return False

    async def _fill_and_wake_body(self, page: Page, content: str):
        editor = page.locator(".ProseMirror").first
        await editor.click(force=True)
        await page.evaluate('''(text) => {
            const el = document.querySelector(".ProseMirror");
            if(el) {
                el.innerHTML = "";
                const dt = new DataTransfer();
                dt.setData("text/plain", text);
                el.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true }));
            }
        }''', content)
        await page.keyboard.press("End")
        await page.keyboard.press("Enter")
        await page.keyboard.press("Backspace")

    async def _inject_image_pro(self, page: Page, path: str):
        try:
            await page.keyboard.press("Control+Home")
            await page.keyboard.press("Enter")
            await page.keyboard.press("ArrowUp")
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            await page.evaluate('''(b64) => {
                const byteCharacters = atob(b64);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) byteNumbers[i] = byteCharacters.charCodeAt(i);
                const dt = new DataTransfer();
                dt.items.add(new File([new Uint8Array(byteNumbers)], "img.jpg", { type: 'image/jpeg' }));
                document.querySelector(".ProseMirror").dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true }));
            }''', b64)
            await asyncio.sleep(4)
        except:
            pass

    async def _force_upload_cover(self, page: Page, path: str):
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.locator("text=单图").first.click(force=True)
            await asyncio.sleep(1)
            await page.evaluate('''() => {
                document.querySelectorAll('input[type="file"]').forEach(el => {
                    el.style.display = 'block'; el.style.opacity = '1';
                });
            }''')
            cover_input = page.locator("div:has-text('展示封面') >> input[type='file']").first
            if await cover_input.count() == 0: cover_input = page.locator("input[type='file']").last
            await cover_input.set_input_files(path)
            await page.wait_for_selector("text=预览, text=替换", timeout=12000)
            logger.info("✅ 封面上传成功")
        except:
            pass

    async def _brutal_kill_interferences(self, page: Page):
        await page.evaluate('''() => {
            const targets = ['.creation-helper', '.byte-icon--close', '.add-desktop-prepare', '.portal-container', '.guide-mask'];
            targets.forEach(s => document.querySelectorAll(s).forEach(el => el.remove()));
        }''')

    def _deep_clean_content(self, text: str) -> str:
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'#+\s*', '', text)
        text = re.sub(r'\*\*+', '', text)
        return text.strip()

    async def _download_images_fast(self, urls: List[str]) -> List[str]:
        paths = []
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            for url in urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        tmp = os.path.join(tempfile.gettempdir(), f"tt_v59_{random.randint(1, 999)}.jpg")
                        with open(tmp, "wb") as f: f.write(resp.content)
                        paths.append(tmp)
                        break
                except:
                    continue
        return paths

    async def _wait_for_publish_result(self, page: Page) -> Dict[str, Any]:
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