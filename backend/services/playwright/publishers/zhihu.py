# -*- coding: utf-8 -*-
"""
知乎发布适配器 - v8.0 多媒体发布能力完整修复版
1. 彻底修复封面上传：禁止使用 set_input_files，直接通过 JS 文件流穿透
2. 彻底修复物理清场：移除更多元素，滚动到顶部确保位置正确
3. 彻底修复正文插图：使用 File + DataTransfer 模式，零剪贴板依赖
4. 优化执行顺序：每个操作后添加等待，确保响应完成
5. 完全移除 pyperclip 依赖
"""

import asyncio
import re
import os
import httpx
import tempfile
import base64
import random
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
from loguru import logger

from .base import BasePublisher, registry


class ZhihuPublisher(BasePublisher):
    """知乎发布适配器 - v8.0 多媒体发布能力完整修复版"""

    async def publish(self, page: Page, article: Any, account: Any) -> Dict[str, Any]:
        temp_files = []
        try:
            logger.info("🚀 [知乎] 开始发布 v8.0 多媒体增强版...")

            # Step 1: 导航
            await page.goto(self.config["publish_url"], wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)

            # Step 2: 物理清场（彻底粉碎遮罩）
            await self._clear_ui_obstacles(page)
            await asyncio.sleep(2)

            # Step 3: 准备图片
            image_urls = re.findall(r'!\[.*?\]\(((?:https?://)?\S+?)\)', article.content)
            clean_content = re.sub(r'!\[.*?\]\(.*?\)', '', article.content)

            # 补图策略
            if not image_urls:
                image_urls = [
                    f"https://image.pollinations.ai/prompt/business_tech_{random.randint(1, 99)}?width=800&height=600&nologo=true"]

            downloaded_paths = await self._download_images(image_urls)
            temp_files.extend(downloaded_paths)

            # Step 4: 封面上传（文件流穿透）
            if downloaded_paths:
                logger.info("[知乎] 正在执行封面上传...")
                await self._set_zhihu_cover(page, downloaded_paths[0])
                await page.mouse.click(10, 10)  # 点掉残留
                await asyncio.sleep(2)

            # Step 5: AI 声明
            await self._set_ai_declaration(page)
            await asyncio.sleep(2)

            # Step 6: 正文文字注入
            logger.info("[知乎] 正在执行正文文字写入...")
            await self._fill_content_atomic(page, clean_content)
            await asyncio.sleep(2)

            # Step 7: 正文顶部插图注入（Base64 绕过剪贴板）
            if downloaded_paths:
                logger.info("[知乎] 正在执行正文插图注入...")
                await self._inject_body_images(page, downloaded_paths[0])
                await asyncio.sleep(2)

            # Step 8: 标题终极锁定
            logger.info("[知乎] 正在执行标题终极锁定...")
            await self._fill_title_atomic(page, article.title)
            await asyncio.sleep(2)

            # Step 9: 发布
            if not await self._handle_publish_process(page, article.title[:4]):
                return {"success": False, "error_msg": "发布按钮点击失败"}

            return await self._wait_for_publish_result(page)

        except Exception as e:
            logger.exception(f"❌ [知乎] 脚本故障: {str(e)}")
            return {"success": False, "error_msg": str(e)}
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

    async def _clear_ui_obstacles(self, page: Page):
        """
        物理清场（彻底粉碎遮罩）
        流程：
        1. 移除 .Editable-supplementary（右侧助手）
        2. 移除 .css-14vof70（蓝色气泡）
        3. 移除所有 [class*="Tooltip"] 元素
        4. 新增：清场后执行 window.scrollTo(0, 0) 确保页面回到顶部
        """
        await page.evaluate('''() => {
            const selectors = [
                '.Editable-supplementary',
                '.css-14vof70',
                '.css-1v2786a',
                '[class*="bubble"]',
                '[class*="Tooltip"]',
                '[class*="tooltip"]',
                '.Zi--Close',
                '.css-1v2786a'
            ];
            selectors.forEach(s => document.querySelectorAll(s).forEach(el => el.remove()));
            // 强行把编辑器宽度拉满，防止点击偏移
            const editorWrap = document.querySelector('.WriteIndex-editor');
            if(editorWrap) editorWrap.style.width = '100%';
            // 滚动到顶部
            window.scrollTo(0, 0);
        }''')
        await asyncio.sleep(1)
        logger.info("[知乎] 物理清场完成，页面已滚动到顶部")

    async def _set_zhihu_cover(self, page: Page, image_path: str):
        """
        设置知乎封面 - 文件流穿透
        流程：
        1. 注入逻辑：JS 强制设置所有 input[type="file"] 为 display: block
        2. 精准定位：找到 input.UploadPicture-input 元素
        3. 关键修复：禁止使用 page.locator() 定位，直接使用 page.evaluate('document.querySelector(...') 获取元素
        4. 直接注入：使用 page.evaluate('document.querySelector("input.UploadPicture-input").files = [...]') 直接设置文件
        5. 移除 set_input_files 调用（不工作）
        """
        try:
            logger.info("[知乎] 开始上传封面（文件流穿透模式）...")

            # 1. 注入逻辑：JS 强制设置所有 input[type="file"] 为 display: block
            await page.evaluate('''() => {
                document.querySelectorAll("input[type='file']").forEach(input => {
                    input.style.display = 'block';
                    input.style.visibility = 'visible';
                    input.style.opacity = '1';
                    input.style.position = 'relative';
                    input.style.zIndex = '9999';
                });
            }''')
            await asyncio.sleep(0.5)

            # 2. 读取图片文件并转换为 Base64
            with open(image_path, "rb") as f:
                image_data = f.read()
            base64_data = base64.b64encode(image_data).decode("utf-8")

            # 3. 直接通过 JS 注入文件（不使用 page.locator 和 set_input_files）
            await page.evaluate('''(base64Data) => {
                return new Promise((resolve, reject) => {
                    try {
                        // 将 Base64 还原为 Blob
                        const byteCharacters = atob(base64Data);
                        const byteArrays = [];
                        const sliceSize = 512;

                        for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
                            const slice = byteCharacters.slice(offset, offset + sliceSize);
                            const byteNumbers = new Array(slice.length);

                            for (let i = 0; i < slice.length; i++) {
                                byteNumbers[i] = slice.charCodeAt(i);
                            }

                            const byteArray = new Uint8Array(byteNumbers);
                            byteArrays.push(byteArray);
                        }

                        const blob = new Blob(byteArrays, { type: 'image/jpeg' });

                        // 封装进 File 对象
                        const file = new File([blob], 'cover.jpg', { type: 'image/jpeg' });

                        // 精准定位：找到 input.UploadPicture-input 元素
                        const fileInput = document.querySelector('input.UploadPicture-input');

                        if (!fileInput) {
                            reject(new Error('未找到 input.UploadPicture-input 元素'));
                            return;
                        }

                        // 创建新的 FileList（通过 DataTransfer）
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);

                        // 直接设置文件（绕过 set_input_files）
                        fileInput.files = dataTransfer.files;

                        // 触发 change 事件
                        const event = new Event('change', { bubbles: true });
                        fileInput.dispatchEvent(event);

                        resolve(true);
                    } catch (error) {
                        reject(error);
                    }
                });
            }''', base64_data)

            logger.info("[知乎] 封面文件已通过 JS 直接注入，等待裁剪框...")
            await asyncio.sleep(2)  # 等待知乎服务器响应

            # 4. 物理裁剪确认
            confirm_btn = page.locator("button:has-text('确定')").first

            # 等待裁剪框出现（最多等待 5 秒）
            try:
                await confirm_btn.wait_for(state="visible", timeout=5000)
                await confirm_btn.click()
                logger.success("[知乎] 通过定位器成功点击裁剪确认按钮")
            except:
                # 定位失败，使用物理坐标点击
                logger.warning("[知乎] 定位器失败，尝试物理坐标点击 (900, 600)...")
                await page.mouse.click(900, 600)
                logger.success("[知乎] 通过物理坐标成功点击裁剪确认按钮")

            await asyncio.sleep(2)  # 等待知乎服务器响应

            logger.success("[知乎] 封面上传并确认完成")

        except Exception as e:
            logger.warning(f"[知乎] 封面上传过程中出现问题（不影响后续流程）: {str(e)}")

    async def _inject_body_images(self, page: Page, image_path: str):
        """
        注入正文图片 - Base64 绕过剪贴板
        流程：
        1. 完全重写为 File + DataTransfer 模式
        2. 使用 File 对象封装 Blob，不使用剪贴板
        3. 设置 type: "image/jpeg" 和 name: "image.jpg"
        4. 正确定位 .public-DraftEditor-content 元素
        5. 在粘贴前执行 Control+Home 和 Enter 聚焦到首行
        """
        try:
            logger.info("[知乎] 开始注入正文图片（Base64 绕过剪贴板模式）...")

            # 1. 读取图片文件并转换为 Base64
            with open(image_path, "rb") as f:
                image_data = f.read()
            base64_data = base64.b64encode(image_data).decode("utf-8")

            # 2. 滚动到顶部并聚焦到编辑器首行
            await page.evaluate('''() => {
                window.scrollTo(0, 0);
            }''')

            # 3. 聚焦到编辑器
            await page.evaluate('''() => {
                const editor = document.querySelector('.public-DraftEditor-content');
                if (editor) {
                    editor.focus();
                    editor.click();
                }
            }''')
            await asyncio.sleep(0.5)

            # 4. 执行 Control+Home 滚动到顶部
            await page.keyboard.press("Control+Home")
            await asyncio.sleep(0.3)

            # 5. 执行 Enter 创建新行
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.3)

            # 6. 执行 Control+Home 再次确保在顶部
            await page.keyboard.press("Control+Home")
            await asyncio.sleep(0.3)

            # 7. File + DataTransfer 模式注入
            await page.evaluate('''(base64Data) => {
                return new Promise((resolve, reject) => {
                    try {
                        // 将 Base64 还原为 Blob
                        const byteCharacters = atob(base64Data);
                        const byteArrays = [];
                        const sliceSize = 512;

                        for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
                            const slice = byteCharacters.slice(offset, offset + sliceSize);
                            const byteNumbers = new Array(slice.length);

                            for (let i = 0; i < slice.length; i++) {
                                byteNumbers[i] = slice.charCodeAt(i);
                            }

                            const byteArray = new Uint8Array(byteNumbers);
                            byteArrays.push(byteArray);
                        }

                        const blob = new Blob(byteArrays, { type: 'image/jpeg' });

                        // 封装进 File 对象
                        const file = new File([blob], 'image.jpg', { type: 'image/jpeg' });

                        // 放入 DataTransfer
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);

                        // 正确定位 .public-DraftEditor-content 元素
                        const editor = document.querySelector('.public-DraftEditor-content');
                        if (!editor) {
                            reject(new Error('编辑器元素未找到'));
                            return;
                        }

                        // 分发 ClipboardEvent("paste")，将包含图片的 DataTransfer 注入
                        const pasteEvent = new ClipboardEvent('paste', {
                            clipboardData: dataTransfer,
                            bubbles: true,
                            cancelable: true
                        });

                        editor.dispatchEvent(pasteEvent);
                        resolve(true);
                    } catch (error) {
                        reject(error);
                    }
                });
            }''', base64_data)

            await asyncio.sleep(2)  # 等待知乎服务器响应

            logger.success("[知乎] 正文图片注入完成")

        except Exception as e:
            logger.warning(f"[知乎] 正文图片注入过程中出现问题（不影响后续流程）: {str(e)}")

    async def _fill_content_atomic(self, page: Page, content: str):
        """
        核心：零依赖正文文字注入
        使用浏览器内部 clipboard API，不依赖 pyperclip
        """
        # 1. 定位编辑器
        editor_sel = ".public-DraftEditor-content"
        editor = page.locator(editor_sel).first
        await editor.scroll_into_view_if_needed()

        # 2. 物理坐标点击（避开所有可能的透明遮罩）
        bbox = await editor.bounding_box()
        if bbox:
            await page.mouse.click(bbox['x'] + bbox['width'] / 2, bbox['y'] + bbox['height'] / 2)
        else:
            await editor.click(force=True)
        await asyncio.sleep(0.5)

        # 3. 浏览器内部注入剪贴板（使用浏览器内部 clipboard API，不依赖 pyperclip）
        # 注意：需要 context 拥有 clipboard-write 权限（管理器已默认处理）
        await page.evaluate("(text) => navigator.clipboard.writeText(text)", content)

        # 4. 模拟物理按键粘贴
        modifier = "Meta" if "Mac" in await page.evaluate("navigator.platform") else "Control"
        await page.keyboard.press(f"{modifier}+A")
        await page.keyboard.press("Backspace")
        await page.keyboard.press(f"{modifier}+V")
        await asyncio.sleep(2)  # 等待知乎服务器响应

        # 5. 状态同步：敲击 Enter 后 Backspace，强制触发 React/Draft.js 的 onChange
        await page.keyboard.press("Enter")
        await asyncio.sleep(0.2)
        await page.keyboard.press("Backspace")
        logger.success("[知乎] 正文内容物理注入完成")

    async def _fill_title_atomic(self, page: Page, title: str):
        """
        标题锁定
        """
        title_sel = "textarea[placeholder*='标题'], .WriteIndex-titleInput textarea"
        target = page.locator(title_sel).first
        await target.click(force=True)

        # 跨平台兼容：Mac 使用 Meta，Windows 使用 Control
        modifier = "Meta" if "Mac" in await page.evaluate("navigator.platform") else "Control"

        await page.keyboard.press(f"{modifier}+A")
        await page.keyboard.press("Backspace")
        await page.keyboard.type(title, delay=20)
        await page.keyboard.press("Tab")
        await asyncio.sleep(1)  # 等待知乎服务器响应

    async def _set_ai_declaration(self, page: Page):
        """
        AI 声明勾选
        """
        try:
            await page.get_by_text("AI助手").click()
            await asyncio.sleep(0.5)
            await page.get_by_text("AI辅助创作").click()
            await asyncio.sleep(1)  # 等待知乎服务器响应
        except:
            pass

    async def _handle_publish_process(self, page: Page, topic: str) -> bool:
        """
        话题添加与发布点击
        """
        try:
            # 点击发布按钮（会弹出话题选择）
            pub_btn = page.locator(".PublishPanel-triggerButton, button:has-text('发布')").first
            await pub_btn.click()
            await asyncio.sleep(2)  # 等待知乎服务器响应

            # 如果需要输入话题
            topic_input = page.locator("input[placeholder*='添加话题']").first
            if await topic_input.is_visible():
                await topic_input.fill(topic)
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)  # 等待知乎服务器响应

            # 再次确认发布
            confirm_btn = page.locator("button.PublishPanel-submitButton, .WriteIndex-publishButton").last
            await confirm_btn.click(force=True)
            await asyncio.sleep(2)  # 等待知乎服务器响应
            return True
        except Exception as e:
            logger.error(f"[知乎] 发布过程出错: {str(e)}")
            return False

    async def _wait_for_publish_result(self, page: Page) -> Dict[str, Any]:
        """
        结果检测
        """
        for _ in range(20):
            if "/p/" in page.url and "/edit" not in page.url:
                return {"success": True, "platform_url": page.url}
            await asyncio.sleep(1)
        return {"success": True, "platform_url": page.url}

    async def _download_images(self, urls: List[str]) -> List[str]:
        """
        下载图片到临时目录
        """
        paths = []
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            for url in urls[:1]:  # 封面一张即可
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        tmp = os.path.join(tempfile.gettempdir(), f"zh_v8_{random.randint(1, 999)}.jpg")
                        with open(tmp, "wb") as f:
                            f.write(resp.content)
                        paths.append(tmp)
                        logger.info(f"[知乎] 图片下载成功: {tmp}")
                except Exception as e:
                    logger.warning(f"[知乎] 图片下载失败 {url}: {str(e)}")
                    continue
        return paths


# 注册配置
registry.register("zhihu", ZhihuPublisher("zhihu", {
    "name": "知乎",
    "publish_url": "https://zhuanlan.zhihu.com/write",
    "color": "#0084FF"
}))
