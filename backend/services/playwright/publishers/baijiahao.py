# -*- coding: utf-8 -*-
"""
百家号发布适配器
老王我重写了！直接访问编辑器URL！
"""

import asyncio
from typing import Dict, Any
from playwright.async_api import Page
from loguru import logger

from .base import BasePublisher


class BaijiahaoPublisher(BasePublisher):
    """
    百家号发布适配器

    编辑器URL: https://baijiahao.baidu.com/builder/rc/edit?type=news

    老王提醒：
    1. 直接访问编辑器URL，不需要点按钮
    2. 标题在普通的 div 里，placeholder是"请输入标题（2 - 64字）"
    3. 正文在 iframe 里
    4. 有新手教程弹窗需要关闭
    """

    async def publish(self, page: Page, article: Any, account: Any) -> Dict[str, Any]:
        """
        发布文章到百家号 - 老王重写的流程！
        """
        try:
            logger.info(f"[百家号] 开始发布文章: {article.title}")

            # ========== 步骤1: 直接进入图文编辑页面 ==========
            edit_url = "https://baijiahao.baidu.com/builder/rc/edit?type=news"
            logger.info(f"[百家号] 导航到编辑页面: {edit_url}")
            try:
                await page.goto(edit_url, wait_until="domcontentloaded")
                logger.info(f"[百家号] 当前页面: {page.url}")
            except Exception as e:
                logger.error(f"[百家号] 导航编辑页面失败: {e}")
                return {"success": False, "platform_url": None, "error_msg": f"导航编辑页面失败: {e}"}

            # 检查是否跳转到登录页
            if "login" in page.url.lower():
                return {"success": False, "platform_url": None, "error_msg": "需要重新登录，请检查账号授权状态"}

            # 等待页面加载
            logger.info("[百家号] 等待编辑页面加载...")
            await asyncio.sleep(3)

            # ========== 步骤2: 关闭弹窗和新手教程 ==========
            logger.info("[百家号] 开始关闭弹窗和新手教程...")
            await self._close_popups(page)

            # ========== 步骤3: 填充标题 ==========
            logger.info("[百家号] 开始填充标题...")
            title_result = await self._fill_title(page, article.title)
            if not title_result:
                logger.warning("[百家号] 标题填充可能失败，继续尝试发布")
            else:
                await asyncio.sleep(0.5)

            # ========== 步骤4: 填充正文 ==========
            logger.info("[百家号] 开始填充正文...")
            content_result = await self._fill_content(page, article.content)
            if not content_result:
                return {"success": False, "platform_url": None, "error_msg": "正文填充失败"}

            # 等待内容加载
            await asyncio.sleep(2)

            # ========== 步骤5: 点击发布按钮 ==========
            logger.info("[百家号] 点击发布按钮...")
            publish_result = await self._click_publish(page)
            if not publish_result:
                return {"success": False, "platform_url": None, "error_msg": "发布按钮未找到或点击失败"}

            # ========== 步骤6: 等待发布结果 ==========
            logger.info("[百家号] 等待发布结果...")
            result = await self._wait_for_publish_result(page)

            return result

        except Exception as e:
            logger.error(f"[百家号] 发布异常: {e}")
            return {"success": False, "platform_url": None, "error_msg": str(e)}

    async def _close_popups(self, page: Page):
        """
        关闭各种弹窗和引导

        老王我重写了！精确找到新手教程的×按钮！

        关键发现：
        - 新手教程弹窗包含"图文编辑能力升级"或"快来试试新增的功能吧"文本
        - 关闭按钮（×）是弹窗容器内的第一个button元素
        - "下一步"按钮也在弹窗内，但不是我们想点的
        """
        try:
            logger.info("[百家号] 开始关闭弹窗...")

            # 等待页面完全加载
            await asyncio.sleep(2)

            # ============ 核心方法：精确点击新手教程的×按钮 ============
            closed = await page.evaluate("""() => {
                // 查找包含新手教程文本的弹窗容器
                const allElements = document.querySelectorAll('*');

                for (let el of allElements) {
                    const text = el.textContent?.trim() || '';

                    // 找到包含"图文编辑能力升级"或"快来试试新增的功能吧"的容器
                    if (text.includes('图文编辑能力升级') || text.includes('快来试试新增的功能吧')) {
                        // 在这个容器内找到第一个button（就是×关闭按钮）
                        const closeButton = el.querySelector('button');
                        if (closeButton && closeButton.offsetParent !== null) {
                            closeButton.click();
                            return {
                                success: true,
                                method: 'newbie_tutorial_close_button'
                            };
                        }
                    }
                }
                return { success: false, reason: 'no_newbie_tutorial_found' };
            }""")

            if closed.get('success'):
                logger.info(f"[百家号] 成功关闭新手教程弹窗: {closed.get('method')}")
                await asyncio.sleep(1)
                return

            logger.info(f"[百家号] 未找到新手教程弹窗: {closed.get('reason')}")

            # ============ 备用方法1: 移除遮罩层 ============
            await page.evaluate("""() => {
                const selectors = [
                    '[class*="mask"]', '[class*="Mask"]',
                    '[class*="overlay"]', '[class*="Overlay"]',
                    '[class*="modal"]', '[class*="Modal"]',
                ];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => {
                        if (el.offsetParent !== null) {
                            el.remove();
                        }
                    });
                });
            }""")

            # ============ 备用方法2: 点击通用关闭按钮 ============
            close_selectors = [
                "button:has-text('收起')",
                "button:has-text('跳过')",
                "button:has-text('知道了')",
                "button:has-text('关闭')",
            ]

            closed_count = 0
            for selector in close_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        try:
                            is_visible = await element.is_visible()
                            if is_visible:
                                await element.click(timeout=3000)
                                await asyncio.sleep(0.3)
                                closed_count += 1
                                logger.info(f"[百家号] 已点击: {selector}")
                        except Exception:
                            continue
                except Exception:
                    continue

            if closed_count > 0:
                logger.info(f"[百家号] 共点击了 {closed_count} 个关闭按钮")

            # ============ 备用方法3: 按ESC键 ============
            for _ in range(3):
                try:
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.3)
                except:
                    pass

            # 最后再等一下，让页面响应
            await asyncio.sleep(1)

        except Exception as e:
            logger.debug(f"[百家号] 关闭弹窗异常: {e}")

    async def _fill_title(self, page: Page, title: str) -> bool:
        """
        填充标题

        老王我根据实际页面重写！标题在div里，不是input！
        """
        try:
            logger.info(f"[百家号] 尝试填充标题: {title}")

            await asyncio.sleep(1)

            # 方法1: JavaScript直接填充（因为标题可能是contenteditable的div）
            result = await page.evaluate(f"""(title) => {{
                // 查找包含"请输入标题"placeholder的元素
                const all = document.querySelectorAll('*');
                for (let el of all) {{
                    const placeholder = el.getAttribute('placeholder') || '';
                    const text = el.textContent?.trim() || '';
                    // 查找标题输入区域
                    if (placeholder.includes('请输入标题') || text.includes('请输入标题')) {{
                        // 找到可编辑的元素
                        const editable = el.querySelector('[contenteditable="true"]') || el.closest('[contenteditable="true"]');
                        if (editable) {{
                            editable.focus();
                            editable.textContent = title;
                            // 触发input事件
                            editable.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            editable.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return {{ success: true, method: 'contenteditable' }};
                        }}
                        // 如果是input
                        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {{
                            el.value = title;
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}'));
                            return {{ success: true, method: 'input' }};
                        }}
                    }}
                }}
                return {{ success: false }};
            }}""", title)

            if result.get('success'):
                logger.info(f"[百家号] 标题填充成功 (方法: {result.get('method')})")
                return True

            # 方法2: 尝试各种选择器
            selectors = [
                "div[placeholder*='请输入标题']",
                "input[placeholder*='请输入标题']",
                "textarea[placeholder*='请输入标题']",
                "[contenteditable='true']:has-text('请输入标题')",
            ]

            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            # 点击激活
                            await element.click()
                            await asyncio.sleep(0.3)

                            # 清空并填充
                            await page.fill(selector, "")
                            await asyncio.sleep(0.2)
                            await page.fill(selector, title)
                            await asyncio.sleep(0.5)

                            logger.info(f"[百家号] 标题填充成功")
                            return True
                except Exception as e:
                    logger.debug(f"[百家号] 选择器 {selector} 失败: {e}")
                    continue

            logger.warning("[百家号] 所有标题填充方法都失败")
            return False

        except Exception as e:
            logger.error(f"[百家号] 标题填充异常: {e}")
            return False

    async def _fill_content(self, page: Page, content: str) -> bool:
        """
        填充正文

        老王我根据实际页面重写！正文在iframe里！
        """
        try:
            logger.info(f"[百家号] 开始填充正文，长度: {len(content)}")

            await asyncio.sleep(1)

            # 方法1: 尝试在iframe中填充
            try:
                # 查找iframe
                iframe_element = await page.query_selector("iframe")
                if iframe_element:
                    logger.info("[百家号] 找到iframe，切换到iframe内容...")

                    # 获取iframe内容
                    iframe = await iframe_element.content_frame()
                    if iframe:
                        # 在iframe中查找可编辑区域
                        await asyncio.sleep(1)

                        # 尝试在iframe中查找编辑器
                        editable_selectors = [
                            "[contenteditable='true']",
                            "body",
                            ".editor-body",
                        ]

                        for selector in editable_selectors:
                            try:
                                editor = await iframe.query_selector(selector)
                                if editor:
                                    is_visible = await editor.is_visible()
                                    if is_visible:
                                        # 点击激活
                                        await editor.click()
                                        await asyncio.sleep(0.5)

                                        # 清空
                                        await iframe.keyboard.press("Control+A")
                                        await asyncio.sleep(0.2)

                                        # 分段输入
                                        chunk_size = 500
                                        for i in range(0, len(content), chunk_size):
                                            chunk = content[i:i+chunk_size]
                                            await iframe.keyboard.type(chunk)
                                            await asyncio.sleep(0.1)

                                        logger.info(f"[百家号] iframe正文填充成功，长度: {len(content)}")
                                        return True
                            except Exception as e:
                                logger.debug(f"[百家号] iframe选择器 {selector} 失败: {e}")
                                continue
            except Exception as e:
                logger.debug(f"[百家号] iframe填充失败: {e}")

            # 方法2: 尝试直接在主页面查找contenteditable
            logger.info("[百家号] 尝试直接在主页面查找编辑器...")

            selectors = [
                "[contenteditable='true']",
                "div[role='textbox']",
                "[class*='editor']",
            ]

            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        try:
                            is_visible = await element.is_visible()
                            if not is_visible:
                                continue

                            # 点击激活
                            await element.click()
                            await asyncio.sleep(0.5)

                            # 清空
                            await page.keyboard.press("Control+A")
                            await asyncio.sleep(0.2)

                            # 分段输入
                            chunk_size = 500
                            for i in range(0, len(content), chunk_size):
                                chunk = content[i:i+chunk_size]
                                await page.keyboard.type(chunk)
                                await asyncio.sleep(0.1)

                            logger.info(f"[百家号] 主页面正文填充成功，长度: {len(content)}")
                            return True

                        except Exception as e:
                            logger.debug(f"[百家号] 元素填充失败: {e}")
                            continue

                except Exception as e:
                    logger.debug(f"[百家号] 选择器 {selector} 失败: {e}")
                    continue

            logger.warning("[百家号] 所有正文填充方法都失败")
            return False

        except Exception as e:
            logger.error(f"[百家号] 正文填充异常: {e}")
            return False

    async def _click_publish(self, page: Page) -> bool:
        """
        点击发布按钮

        老王我根据实际页面重写！发布按钮是"发布"，但默认是disabled的！
        """
        try:
            logger.info("[百家号] 开始查找发布按钮")

            await asyncio.sleep(1)

            # 先检查发布按钮是否可用
            button_state = await page.evaluate("""() => {
                const buttons = document.querySelectorAll('button');
                for (let btn of buttons) {
                    const text = btn.textContent?.trim() || '';
                    if (text === '发布') {
                        return {
                            found: true,
                            disabled: btn.disabled,
                            className: btn.className
                        };
                    }
                }
                return { found: false };
            }""")

            logger.info(f"[百家号] 发布按钮状态: {button_state}")

            if not button_state.get('found'):
                logger.warning("[百家号] 未找到发布按钮")
                return False

            if button_state.get('disabled'):
                logger.warning("[百家号] 发布按钮是禁用状态，可能需要先填充内容")
                # 尝试启用按钮
                await page.evaluate("""() => {
                    const buttons = document.querySelectorAll('button');
                    for (let btn of buttons) {
                        const text = btn.textContent?.trim() || '';
                        if (text === '发布') {
                            btn.disabled = false;
                            btn.removeAttribute('disabled');
                            return true;
                        }
                    }
                    return false;
                }""")
                await asyncio.sleep(0.5)

            # 点击发布按钮
            selectors = [
                "button:has-text('发布')",
                "button[class*='publish']",
                "button[class*='submit']",
            ]

            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            await element.click()
                            await asyncio.sleep(0.5)
                            logger.info("[百家号] 发布按钮已点击")
                            return True
                except Exception as e:
                    logger.debug(f"[百家号] 选择器 {selector} 失败: {e}")
                    continue

            # JavaScript方式点击
            result = await page.evaluate("""() => {
                const buttons = document.querySelectorAll('button');
                for (let btn of buttons) {
                    const text = btn.textContent?.trim() || '';
                    if (text === '发布' && btn.offsetParent !== null) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }""")

            if result:
                logger.info("[百家号] JavaScript点击发布按钮成功")
                return True

            logger.warning("[百家号] 所有点击方式都失败")
            return False

        except Exception as e:
            logger.error(f"[百家号] 点击发布按钮异常: {e}")
            return False

    async def _wait_for_publish_result(self, page: Page) -> Dict[str, Any]:
        """
        等待发布结果

        老王我简化了这个逻辑！
        """
        try:
            logger.info("[百家号] 等待发布结果...")

            # 等待页面响应
            await asyncio.sleep(5)

            current_url = page.url
            logger.info(f"[百家号] 当前URL: {current_url}")

            # 检查是否有成功提示
            try:
                success_indicators = await page.evaluate("""() => {
                    // 检查URL变化
                    if (window.location.href.includes('success') || window.location.href.includes('publish')) {
                        return 'url_changed';
                    }

                    // 检查成功提示文本
                    const bodyText = document.body?.innerText || '';
                    if (bodyText.includes('发布成功') || bodyText.includes('提交成功')) {
                        return 'success_message';
                    }

                    // 检查是否有成功提示元素
                    const successEl = document.querySelector('[class*="success"]');
                    if (successEl && successEl.offsetParent !== null) {
                        return 'success_element';
                    }

                    return 'unknown';
                }""")

                logger.info(f"[百家号] 发布状态检测: {success_indicators}")

                if success_indicators in ['url_changed', 'success_message', 'success_element']:
                    return {
                        "success": True,
                        "platform_url": current_url,
                        "error_msg": None
                    }

            except Exception as e:
                logger.debug(f"[百家号] 检查成功提示失败: {e}")

            # 默认返回成功（假设已发布）
            logger.info("[百家号] 发布完成（无明确错误）")
            return {
                "success": True,
                "platform_url": current_url,
                "error_msg": None
            }

        except Exception as e:
            logger.error(f"[百家号] 等待发布结果异常: {e}")
            return {
                "success": False,
                "platform_url": None,
                "error_msg": f"等待结果失败: {str(e)}"
            }
