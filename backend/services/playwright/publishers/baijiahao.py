# -*- coding: utf-8 -*-
"""
百家号发布适配器 - v3.0 会话预热版
修复：即使授权有效也被重定向回登录页的问题

核心策略：三步走
1. 会话预热：先导航首页，等待JS完成Cookie到Token置换
2. 内部导航：通过点击侧边栏"发布内容"->"图文"进入编辑器
3. Referer伪造：跳转时带上Referer头绕过百度安全检查
"""

import asyncio
from typing import Dict, Any
from playwright.async_api import Page
from loguru import logger

from .base import BasePublisher, registry


class BaijiahaoPublisher(BasePublisher):
    """
    百家号发布适配器

    编辑器URL: https://baijiahao.baidu.com/builder/rc/edit?type=news
    首页URL: https://baijiahao.baidu.com/builder/rc/home

    注意：
    1. 必须先访问首页进行会话预热，不能直接跳编辑器
    2. 优先通过侧边栏点击进入编辑器
    3. 标题在普通的div里，placeholder是"请输入标题（2 - 64字）"
    4. 正文在iframe里
    5. 有新手教程弹窗需要关闭
    """

    async def publish(self, page: Page, article: Any, account: Any) -> Dict[str, Any]:
        """
        发布文章到百家号 - 会话预热版
        """
        try:
            logger.info(f"[百家号] 开始发布文章: {article.title}")

            # ========== 步骤0: 会话预热 (Session Warm-up) ==========
            logger.info("[百家号] ===== 步骤0: 会话预热 =====")
            home_url = "https://baijiahao.baidu.com/builder/rc/home"

            # Step 0.1: 导航到作者中心首页
            logger.info(f"[百家号] 导航到作者中心首页: {home_url}")
            try:
                await page.goto(home_url, wait_until="networkidle", timeout=60000)
                logger.info(f"[百家号] 首页加载完成，当前URL: {page.url}")
            except Exception as e:
                logger.error(f"[百家号] 导航首页失败: {e}")
                return {"success": False, "platform_url": None, "error_msg": f"导航首页失败: {e}"}

            # Step 0.2: 等待3-5秒，让百度JS跑完，完成Cookie到Token的置换
            logger.info("[百家号] 等待会话预热（Cookie到Token置换）...")
            await asyncio.sleep(4)

            # Step 0.3: 检查登录特征（验证会话是否有效）
            login_check = await self._check_login_status(page)
            if not login_check:
                logger.error("[百家号] 会话验证失败，需要重新登录")
                return {"success": False, "platform_url": None, "error_msg": "会话验证失败，需要重新登录"}

            logger.success("[百家号] 会话预热完成，登录状态有效")

            # ========== 步骤1: 内部导航进入编辑器 ==========
            logger.info("[百家号] ===== 步骤1: 尝试通过侧边栏进入编辑器 =====")

            # 优先方案：点击侧边栏"发布内容" -> "图文"按钮
            edit_via_nav = await self._navigate_via_sidebar(page)

            if not edit_via_nav:
                # 备选方案：使用URL跳转 + Referer头
                logger.info("[百家号] 侧边栏导航失败，使用URL跳转方式...")
                edit_via_url = await self._navigate_to_editor_with_referer(page)

                if not edit_via_url:
                    return {"success": False, "platform_url": None, "error_msg": "无法进入编辑页面"}
            else:
                logger.success("[百家号] 已通过侧边栏进入编辑器")

            # 再次检查是否跳转到登录页
            if "login" in page.url.lower():
                logger.error(f"[百家号] 进入编辑器后被重定向到登录页: {page.url}")
                return {"success": False, "platform_url": None, "error_msg": "进入编辑器时被重定向，需要重新登录"}

            logger.info(f"[百家号] 编辑器加载完成，当前URL: {page.url}")

            # 等待页面加载
            await asyncio.sleep(2)

            # ========== 步骤2: 关闭弹窗和新手教程 ==========
            logger.info("[百家号] 开始关闭弹窗和新手教程...")
            await self._close_popups(page)

            # ========== 步骤3: 填充标题（带清理-重试循环）==========
            logger.info("[百家号] 开始填充标题（支持重试）...")

            title_result = False
            max_title_retries = 3

            for retry in range(max_title_retries):
                title_result = await self._fill_title(page, article.title)

                if title_result:
                    logger.success(f"[百家号] 标题填充成功 (第 {retry + 1} 次尝试)")
                    await asyncio.sleep(0.5)
                    break
                else:
                    logger.warning(f"[百家号] 标题填充失败 (第 {retry + 1}/{max_title_retries} 次尝试)")

                    # 如果不是最后一次尝试，执行二次清场并重试
                    if retry < max_title_retries - 1:
                        logger.info("[百家号] 执行二次清场...")
                        await self._close_popups(page)
                        await asyncio.sleep(2)
                    else:
                        logger.warning("[百家号] 标题填充已达到最大重试次数，继续流程")

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

    async def _check_login_status(self, page: Page) -> bool:
        """
        检查登录状态

        检查登录特征：
        1. 头像元素 .avatar-img
        2. canvas元素
        3. 用户名区域
        4. 页面URL是否包含login
        """
        try:
            # 检查URL是否跳转到登录页
            if "login" in page.url.lower():
                logger.warning("[百家号] URL显示已跳转到登录页")
                return False

            # 检查登录特征元素
            login_indicators = await page.evaluate("""() => {
                const checks = {};

                // 检查头像
                checks.hasAvatar = !!document.querySelector('.avatar-img') ||
                                  !!document.querySelector('[class*="avatar"]') ||
                                  !!document.querySelector('[class*="Avatar"]');

                // 检查canvas元素
                checks.hasCanvas = !!document.querySelector('canvas');

                // 检查用户名区域
                checks.hasUsername = !!document.querySelector('[class*="username"]') ||
                                    !!document.querySelector('[class*="user-name"]') ||
                                    !!document.querySelector('[class*="UserName"]');

                // 检查侧边栏是否正常显示
                checks.hasSidebar = !!document.querySelector('[class*="sidebar"]') ||
                                   !!document.querySelector('[class*="Sidebar"]');

                // 检查是否有"发布内容"按钮
                checks.hasPublishButton = document.body.innerText.includes('发布内容');

                return checks;
            }""")

            logger.debug(f"[百家号] 登录状态检查: {login_indicators}")

            # 至少满足其中一个条件即认为登录成功
            is_logged_in = any([
                login_indicators.get('hasAvatar'),
                login_indicators.get('hasCanvas'),
                login_indicators.get('hasUsername'),
                login_indicators.get('hasSidebar'),
                login_indicators.get('hasPublishButton')
            ])

            if is_logged_in:
                logger.success("[百家号] 检测到登录特征，会话有效")
            else:
                logger.warning("[百家号] 未检测到登录特征，可能未登录")

            return is_logged_in

        except Exception as e:
            logger.error(f"[百家号] 登录状态检查异常: {e}")
            return False

    async def _navigate_via_sidebar(self, page: Page) -> bool:
        """
        通过侧边栏导航进入编辑器

        点击路径：侧边栏 -> "发布内容" -> "图文"
        """
        try:
            logger.info("[百家号] 尝试通过侧边栏进入编辑器...")

            # 方法1: 查找并点击"发布内容"按钮
            publish_content_selectors = [
                "text=发布内容",
                "a:has-text('发布内容')",
                "[class*='sidebar'] :text('发布内容')",
                "div:has-text('发布内容')",
            ]

            for selector in publish_content_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            await element.click()
                            logger.info(f"[百家号] 已点击'发布内容' (选择器: {selector})")
                            await asyncio.sleep(1)

                            # 查找并点击"图文"按钮
                            tuwen_selectors = [
                                "text=图文",
                                "a:has-text('图文')",
                                ":text('图文')",
                            ]

                            for tw_selector in tuwen_selectors:
                                try:
                                    tw_element = await page.query_selector(tw_selector)
                                    if tw_element:
                                        tw_visible = await tw_element.is_visible()
                                        if tw_visible:
                                            await tw_element.click()
                                            logger.info(f"[百家号] 已点击'图文'，等待进入编辑器...")
                                            await asyncio.sleep(3)

                                            # 检查是否成功进入编辑器
                                            if "/edit" in page.url or "type=news" in page.url:
                                                logger.success("[百家号] 已成功进入编辑器（侧边栏导航）")
                                                return True
                                except:
                                    continue

                except Exception:
                    continue

            # 方法2: JavaScript点击
            nav_result = await page.evaluate("""() => {
                // 查找所有包含"发布内容"文本的元素
                const allElements = document.querySelectorAll('*');
                for (let el of allElements) {
                    const text = el.textContent?.trim() || '';
                    if (text === '发布内容') {
                        el.click();
                        // 等待页面响应
                        return new Promise(resolve => {
                            setTimeout(() => {
                                // 再找"图文"
                                const twElements = document.querySelectorAll('*');
                                for (let tw of twElements) {
                                    const twText = tw.textContent?.trim() || '';
                                    if (twText === '图文') {
                                        tw.click();
                                        resolve({ success: true, method: 'js_click' });
                                        return;
                                    }
                                }
                                resolve({ success: false, reason: 'no_tuwen_button' });
                            }, 1000);
                        });
                    }
                }
                return { success: false, reason: 'no_publish_button' };
            }""")

            if nav_result.get('success'):
                await asyncio.sleep(3)
                if "/edit" in page.url or "type=news" in page.url:
                    logger.success("[百家号] 已成功进入编辑器（JS点击）")
                    return True

            logger.info("[百家号] 侧边栏导航未成功")
            return False

        except Exception as e:
            logger.debug(f"[百家号] 侧边栏导航异常: {e}")
            return False

    async def _navigate_to_editor_with_referer(self, page: Page) -> bool:
        """
        使用URL跳转 + Referer头进入编辑器

        Referer: https://baijiahao.baidu.com/builder/rc/home
        """
        try:
            logger.info("[百家号] 使用URL跳转 + Referer头进入编辑器...")

            # 设置Referer头
            await page.set_extra_http_headers({
                "Referer": "https://baijiahao.baidu.com/builder/rc/home"
            })

            # 跳转到编辑器
            edit_url = "https://baijiahao.baidu.com/builder/rc/edit?type=news"
            logger.info(f"[百家号] 导航到编辑页面: {edit_url}")

            await page.goto(edit_url, wait_until="domcontentloaded", timeout=60000)
            logger.info(f"[百家号] 编辑器加载完成，当前URL: {page.url}")

            # 清除Referer头（避免影响后续请求）
            await page.set_extra_http_headers({})

            # 等待页面稳定
            await asyncio.sleep(2)

            # 检查是否成功
            if "/edit" in page.url or "type=news" in page.url:
                if "login" not in page.url.lower():
                    logger.success("[百家号] 已成功进入编辑器（URL+Referer）")
                    return True

            logger.warning("[百家号] 编辑器进入失败或被重定向")
            return False

        except Exception as e:
            logger.error(f"[百家号] URL跳转异常: {e}")
            return False

    async def _close_popups(self, page: Page):
        """
        关闭各种弹窗和引导 - Z-Index 扫描器版 v3.0

        v3.0 增强：
        1. Z-Index 扫描器：遍历所有元素，检测 computedStyle
        2. 点击空白处：模拟 Escape 键和屏幕边缘点击
        3. 百家号特有干扰源选择器
        """
        try:
            logger.info("[百家号] 开始关闭弹窗（Z-Index 扫描器）...")

            # 等待页面完全加载
            await asyncio.sleep(2)

            # ============ 核心：暴力清除所有干扰元素 ============
            cleanup_result = await page.evaluate("""() => {
                const report = {
                    removed: [],
                    clicked: [],
                    zIndexRemoved: 0,
                    failed: []
                };

                // 白名单：不删除导航栏和底部发布栏
                const whitelistSelectors = [
                    '[class*="navbar"]', '[class*="Navbar"]',
                    '[class*="header"]', '[class*="Header"]',
                    '[class*="sidebar"]', '[class*="Sidebar"]',
                    '[class*="toolbar"]', '[class*="Toolbar"]',
                    '[class*="publish-bar"]', '[class*="PublishBar"]',
                    '[class*="footer"]', '[class*="Footer"]',
                    'nav', 'header', 'footer',
                ];

                // 辅助函数：检查元素是否在白名单中
                const isInWhitelist = (el) => {
                    return whitelistSelectors.some(sel => {
                        try {
                            return el.matches(sel) || el.closest(sel);
                        } catch (e) {
                            return false;
                        }
                    });
                };

                // 1. 移除遮罩层
                const maskSelectors = [
                    '.mask', '[class*="mask"]',
                    '.Mask', '[class*="Mask"]',
                    '.overlay', '[class*="overlay"]',
                    '.Overlay', '[class*="Overlay"]',
                    '.modal', '[class*="modal"]',
                    '.Modal', '[class*="Modal"]',
                    '.guide', '[class*="guide"]',
                    '.Guide', '[class*="Guide"]',
                    '.popover', '[class*="popover"]',
                    '.Popover', '[class*="Popover"]',
                ];

                maskSelectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => {
                        if (el.offsetParent !== null && !isInWhitelist(el)) {
                            el.remove();
                            report.removed.push(sel);
                        }
                    });
                });

                // 2. 百家号特有干扰源
                const baiduSelectors = [
                    '[class*="ai-assistant"]',
                    '[class*="AI-assistant"]',
                    '[class*="cheetah-guide"]',
                    '[class*="Cheetah-guide"]',
                    '[class*="cheetah"]',
                    '[class*="Cheetah"]',
                    '.new-feature-tip',
                    '[class*="new-feature"]',
                    '[class*="feature-tip"]',
                    '[class*="AI"]',
                    '.ai-tooltip',
                    '[class*="ai-tooltip"]',
                    '#driver-popover-item',
                    '[class*="guide-mask"]',
                    '[class*="bui-dialog"]',
                    '[class*="bui-dialog-mask"]',
                    '[class*="bui-modal"]',
                    '[class*="driver-popover"]',
                ];

                baiduSelectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => {
                        if (el.offsetParent !== null && !isInWhitelist(el)) {
                            el.remove();
                            report.removed.push('BD:' + sel);
                        }
                    });
                });

                // 3. Z-Index 扫描器：遍历所有元素，检测高z-index
                const allElements = document.querySelectorAll('*');
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                const centerX = viewportWidth / 2;
                const centerY = viewportHeight / 2;

                for (let el of allElements) {
                    try {
                        // 跳过白名单元素
                        if (isInWhitelist(el)) continue;
                        if (el.tagName === 'BODY' || el.tagName === 'HTML') continue;

                        const style = window.getComputedStyle(el);
                        const position = style.position;
                        const zIndex = parseInt(style.zIndex) || 0;
                        const opacity = parseFloat(style.opacity) || 1;

                        // 如果元素是 fixed/absolute，高z-index，且不透明
                        if ((position === 'fixed' || position === 'absolute') && zIndex > 999 && opacity > 0.1) {
                            // 检查元素是否覆盖屏幕中心区域（干扰核心编辑区）
                            const rect = el.getBoundingClientRect();
                            const coversCenter = (
                                rect.left < centerX && rect.right > centerX &&
                                rect.top < centerY && rect.bottom > centerY
                            );

                            if (coversCenter) {
                                el.remove();
                                report.zIndexRemoved++;
                                report.removed.push(`Z-Idx:${zIndex}`);
                            }
                        }
                    } catch (e) {
                        // 忽略 getComputedStyle 错误
                    }
                }

                // 4. 查找并点击所有可见的关闭按钮
                const closeSelectors = [
                    'button:has-text("×")',
                    'button:has-text("关闭")',
                    'button:has-text("收起")',
                    'button:has-text("跳过")',
                    'button:has-text("知道了")',
                    'button:has-text("取消")',
                    '.close', '[class*="close"]',
                    '.Close', '[class*="Close"]',
                    '.cancel', '[class*="cancel"]',
                    '[aria-label="关闭"]',
                    '[aria-label="close"]',
                ];

                closeSelectors.forEach(sel => {
                    try {
                        const elements = document.querySelectorAll(sel);
                        elements.forEach(el => {
                            if (el.offsetParent !== null && !isInWhitelist(el)) {
                                el.click();
                                report.clicked.push(sel);
                            }
                        });
                    } catch (e) {
                        report.failed.push(sel);
                    }
                });

                // 5. 查找包含特定文本的元素并关闭
                const textPatterns = [
                    '图文编辑能力升级',
                    '快来试试新增的功能吧',
                    'AI助手',
                    '新功能',
                    '智能推荐',
                    '使用教程',
                    '新手引导',
                ];

                const allTextElements = document.querySelectorAll('*');
                for (let el of allTextElements) {
                    if (isInWhitelist(el)) continue;
                    if (el.tagName === 'BODY' || el.tagName === 'HTML') continue;

                    const text = el.textContent?.trim() || '';
                    for (let pattern of textPatterns) {
                        if (text.includes(pattern)) {
                            // 在容器内查找关闭按钮
                            const closeBtn = el.querySelector('button');
                            if (closeBtn && closeBtn.offsetParent !== null) {
                                closeBtn.click();
                                report.clicked.push('text-pattern:' + pattern);
                            }
                            // 如果没有按钮，直接移除容器
                            if (el.offsetParent !== null && !isInWhitelist(el)) {
                                el.remove();
                                report.removed.push('text-pattern:' + pattern);
                            }
                            break;
                        }
                    }
                }

                return report;
            }""")

            logger.info(f"[百家号] 清场结果: 移除={len(cleanup_result.get('removed', []))}, 点击={len(cleanup_result.get('clicked', []))}, Z-Index清除={cleanup_result.get('zIndexRemoved', 0)}")

            # ============ 点击空白处逻辑 ============
            # 模拟按下 Escape 键 3 次
            logger.info("[百家号] 按下 Escape 键关闭模态框...")
            for _ in range(3):
                try:
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.3)
                except:
                    pass

            # 模拟点击屏幕边缘 (点击页面空白处)
            logger.info("[百家号] 点击页面空白处触发关闭...")
            try:
                await page.mouse.click(10, 10)
                await asyncio.sleep(0.2)
                await page.mouse.click(1, 1)
            except:
                pass

            # 等待页面响应
            await asyncio.sleep(1)

            logger.success("[百家号] 弹窗清理完成")

        except Exception as e:
            logger.debug(f"[百家号] 关闭弹窗异常: {e}")

    async def _fill_title(self, page: Page, title: str) -> bool:
        """
        填充标题

        标题在div里，不是input！
        """
        try:
            logger.info(f"[百家号] 尝试填充标题: {title}")

            await asyncio.sleep(1)

            # 方法1: JavaScript直接填充（因为标题可能是contenteditable的div）
            result = await page.evaluate("""(title) => {
                // 查找包含"请输入标题"placeholder的元素
                const all = document.querySelectorAll('*');
                for (let el of all) {
                    const placeholder = el.getAttribute('placeholder') || '';
                    const text = el.textContent?.trim() || '';
                    // 查找标题输入区域
                    if (placeholder.includes('请输入标题') || text.includes('请输入标题')) {
                        // 找到可编辑的元素
                        const editable = el.querySelector('[contenteditable="true"]') || el.closest('[contenteditable="true"]');
                        if (editable) {
                            editable.focus();
                            editable.textContent = title;
                            // 触发input事件
                            editable.dispatchEvent(new Event('input', { bubbles: true }));
                            editable.dispatchEvent(new Event('change', { bubbles: true }));
                            return { success: true, method: 'contenteditable' };
                        }
                        // 如果是input
                        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                            el.value = title;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            return { success: true, method: 'input' };
                        }
                    }
                }
                return { success: false };
            }""", title)

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

        正文在iframe里！
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
        点击发布按钮 - 双重点击逻辑

        v2.0 增强：
        - 第一击：点击"发布"按钮
        - 等待：检查是否弹出二次确认框
        - 第二击：点击确认框中的"确定"/"发布"按钮
        """
        try:
            logger.info("[百家号] ===== 双重点击逻辑 =====")

            await asyncio.sleep(1)

            # ========== 第一步：确保发布按钮可用 ==========
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
                logger.warning("[百家号] 发布按钮是禁用状态，尝试启用")
                await page.evaluate("""() => {
                    const buttons = document.querySelectorAll('button');
                    for (let btn of buttons) {
                        const text = btn.textContent?.trim() || '';
                        if (text === '发布') {
                            btn.disabled = false;
                            btn.removeAttribute('disabled');
                            btn.style.opacity = '1';
                            btn.style.pointerEvents = 'auto';
                            return true;
                        }
                    }
                    return false;
                }""")
                await asyncio.sleep(0.5)

            # ========== 第二步：第一击 - 点击"发布"按钮 ==========
            logger.info("[百家号] ===== 第一击：点击'发布'按钮 =====")

            clicked = False
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
                            logger.info(f"[百家号] 已点击发布按钮 (选择器: {selector})")
                            clicked = True
                            break
                except Exception:
                    continue

            if not clicked:
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
                    clicked = True
                else:
                    logger.warning("[百家号] 所有点击方式都失败")
                    return False

            # ========== 第三步：等待并检查二次确认框 ==========
            logger.info("[百家号] ===== 等待二次确认框... =====")

            # 先清除可能的AI弹窗
            await self._close_popups(page)

            # 等待1-2秒，检查是否弹出确认框
            await asyncio.sleep(2)

            # 检查是否有确认弹窗
            has_confirm_dialog = await page.evaluate("""() => {
                const dialogSelectors = [
                    // 百家号常见的确认框选择器
                    '.dialog', '[class*="dialog"]',
                    '.Dialog', '[class*="Dialog"]',
                    '.confirm', '[class*="confirm"]',
                    '.Confirm', '[class*="Confirm"]',
                    '.modal', '[class*="modal"]',
                    '.Modal', '[class*="Modal"]',
                    '.popover', '[class*="popover"]',
                    '.Popover', '[class*="Popover"]',
                ];

                for (let sel of dialogSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {
                        return {
                            hasDialog: true,
                            selector: sel
                        };
                    }
                }

                // 检查页面文本是否包含确认相关内容
                const bodyText = document.body?.innerText || '';
                const confirmTexts = ['确认发布', '确定', '发布确认', '声明原创', '选择分类'];
                for (let text of confirmTexts) {
                    if (bodyText.includes(text)) {
                        return {
                            hasDialog: true,
                            foundByText: text
                        };
                    }
                }

                return { hasDialog: false };
            }""")

            logger.info(f"[百家号] 二次确认框检测结果: {has_confirm_dialog}")

            # ========== 第四步：第二击 - 点击确认框 ==========
            if has_confirm_dialog.get('hasDialog'):
                logger.info("[百家号] ===== 第二击：点击确认框中的按钮 =====")

                # 查找确认框中的按钮（优先级：确认发布 > 确定 > 发布）
                confirm_selectors = [
                    "button:has-text('确认发布')",
                    "button:has-text('确定')",
                    "button:has-text('发布')",
                    "button:has-text('立即发布')",
                    "button:has-text('确认')",
                    "button[class*='confirm']",
                    "button[class*='submit']",
                ]

                confirm_clicked = False
                for selector in confirm_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            try:
                                is_visible = await element.is_visible()
                                if is_visible:
                                    # 排除取消按钮
                                    btn_text = await element.text_content()
                                    if btn_text and '取消' not in btn_text:
                                        await element.click()
                                        await asyncio.sleep(0.5)
                                        logger.info(f"[百家号] 已点击确认按钮 (选择器: {selector})")
                                        confirm_clicked = True
                                        break
                            except Exception:
                                continue
                        if confirm_clicked:
                            break
                    except Exception:
                        continue

                if not confirm_clicked:
                    # JavaScript方式点击确认按钮
                    js_result = await page.evaluate("""() => {
                        const buttonTexts = ['确认发布', '确定', '发布', '立即发布', '确认'];
                        const buttons = document.querySelectorAll('button');
                        for (let btn of buttons) {
                            const text = btn.textContent?.trim() || '';
                            // 找到确认相关按钮，且不是取消按钮
                            if (btn.offsetParent !== null && buttonTexts.some(t => text.includes(t)) && !text.includes('取消')) {
                                btn.click();
                                return {
                                    clicked: true,
                                    buttonText: text
                                };
                            }
                        }
                        return { clicked: false };
                    }""")

                    if js_result.get('clicked'):
                        logger.info(f"[百家号] JavaScript点击确认按钮成功: {js_result.get('buttonText')}")
                        confirm_clicked = True
                    else:
                        logger.warning("[百家号] 未找到确认按钮，继续流程")
            else:
                logger.info("[百家号] 未检测到二次确认框，可能直接发布")

            # 等待页面响应
            await asyncio.sleep(2)

            return True

        except Exception as e:
            logger.error(f"[百家号] 点击发布按钮异常: {e}")
            return False

    async def _wait_for_publish_result(self, page: Page) -> Dict[str, Any]:
        """
        等待发布结果 - 严格验证版

        v2.0 增强：
        - 严禁仅凭"success"文本判断
        - 必须校验URL变化
        - 成功标准：URL跳转或出现全屏成功提示
        """
        try:
            logger.info("[百家号] ===== 等待发布结果（严格验证）=====")

            # 记录初始URL
            initial_url = page.url
            logger.info(f"[百家号] 初始URL: {initial_url}")

            # 轮询检查，最多等待30秒
            max_wait = 30
            check_interval = 2

            for i in range(max_wait // check_interval):
                current_url = page.url
                logger.info(f"[百家号] 检查第 {i+1} 次，当前URL: {current_url}")

                # ============ 关键验证：URL必须变化 ============
                # 如果URL仍停留在编辑器页面，视为失败
                if "/rc/edit" in current_url:
                    logger.debug(f"[百家号] URL仍在编辑器页面，继续等待...")

                    # 检查是否有错误提示
                    error_check = await page.evaluate("""() => {
                        const errorSelectors = [
                            '[class*="error"]',
                            '[class*="Error"]',
                            '[class*="fail"]',
                            '[class*="Fail"]',
                        ];
                        for (let sel of errorSelectors) {
                            const el = document.querySelector(sel);
                            if (el && el.offsetParent !== null) {
                                return {
                                    hasError: true,
                                    text: el.textContent?.trim() || ''
                                };
                            }
                        }
                        // 检查错误文本
                        const bodyText = document.body?.innerText || '';
                        const errorTexts = ['发布失败', '提交失败', '网络错误', '服务器错误', '操作失败'];
                        for (let text of errorTexts) {
                            if (bodyText.includes(text)) {
                                return {
                                    hasError: true,
                                    text: text
                                };
                            }
                        }
                        return { hasError: false };
                    }""")

                    if error_check.get('hasError'):
                        logger.error(f"[百家号] 检测到错误提示: {error_check.get('text')}")
                        return {
                            "success": False,
                            "platform_url": current_url,
                            "error_msg": f"发布失败: {error_check.get('text')}"
                        }

                    # 继续等待
                    await asyncio.sleep(check_interval)
                    continue

                # ============ URL已变化，检查是否跳转到成功页面 ============
                logger.success(f"[百家号] URL已变化: {initial_url} -> {current_url}")

                # 检查是否跳转到文章列表页或其他成功页面
                success_url_patterns = [
                    '/rc/home',        # 首页
                    '/rc/list',        # 列表页
                    '/article/',        # 文章详情页
                    '/success',        # 成功页
                    '/detail',         # 详情页
                ]

                url_is_success = any(pattern in current_url for pattern in success_url_patterns)

                if url_is_success:
                    logger.success("[百家号] URL跳转到成功页面，发布成功")
                    return {
                        "success": True,
                        "platform_url": current_url,
                        "error_msg": None
                    }

                # 检查是否有全屏成功提示
                full_success_check = await page.evaluate("""() => {
                    // 检查全屏成功提示元素
                    const successSelectors = [
                        // 百家号常见的全屏成功提示
                        '.success-full-screen',
                        '[class*="success-full-screen"]',
                        '.publish-success',
                        '[class*="publish-success"]',
                        '.submit-success',
                        '[class*="submit-success"]',
                    ];

                    for (let sel of successSelectors) {
                        const el = document.querySelector(sel);
                        if (el && el.offsetParent !== null) {
                            return {
                                hasFullSuccess: true,
                                selector: sel,
                                text: el.textContent?.trim() || ''
                            };
                        }
                    }

                    // 检查全屏成功提示文本（排除自动保存提示）
                    const bodyText = document.body?.innerText || '';
                    const successPatterns = [
                        '发布成功，正在审核',
                        '文章已发布',
                        '提交成功',
                        '审核中',
                    ];

                    // 排除自动保存提示
                    if (bodyText.includes('自动保存')) {
                        return { hasFullSuccess: false, reason: 'auto-save-detected' };
                    }

                    for (let pattern of successPatterns) {
                        if (bodyText.includes(pattern)) {
                            // 进一步检查是否是全屏提示（而不是小toast）
                            const allElements = document.querySelectorAll('*');
                            for (let el of allElements) {
                                const text = el.textContent?.trim() || '';
                                if (text.includes(pattern) && el.offsetWidth > 300 && el.offsetHeight > 200) {
                                    return {
                                        hasFullSuccess: true,
                                        foundBy: 'full-screen-text',
                                        text: pattern
                                    };
                                }
                            }
                        }
                    }

                    return { hasFullSuccess: false };
                }""")

                if full_success_check.get('hasFullSuccess'):
                    logger.success(f"[百家号] 检测到全屏成功提示: {full_success_check.get('text')}")
                    return {
                        "success": True,
                        "platform_url": current_url,
                        "error_msg": None
                    }
                elif full_success_check.get('reason') == 'auto-save-detected':
                    logger.warning("[百家号] 检测到自动保存提示，不是真正的发布成功")
                    # 继续等待真正的发布结果
                    await asyncio.sleep(check_interval)
                    continue

            # ============ 超时：URL仍在编辑器页面 ============
            final_url = page.url
            logger.error(f"[百家号] 发布超时，URL仍在编辑器: {final_url}")
            return {
                "success": False,
                "platform_url": final_url,
                "error_msg": "发布超时，URL未跳转，可能发布失败或需要二次确认"
            }

        except Exception as e:
            logger.error(f"[百家号] 等待发布结果异常: {e}")
            return {
                "success": False,
                "platform_url": None,
                "error_msg": f"等待结果失败: {str(e)}"
            }


# 注册
BAIJIAHAO_CONFIG = {
    "name": "百家号",
    "login_url": "https://baijiahao.baidu.com/builder/rc/static/login/index",
    "home_url": "https://baijiahao.baidu.com/builder/rc/home",
    "publish_url": "https://baijiahao.baidu.com/builder/rc/edit?type=news",
    "color": "#E53935"
}
registry.register("baijiahao", BaijiahaoPublisher("baijiahao", BAIJIAHAO_CONFIG))
