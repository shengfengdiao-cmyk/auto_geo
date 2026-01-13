# -*- coding: utf-8 -*-
"""
百家号发布完整流程测试脚本
老王专门写来调试发布流程的，别tm乱改！
"""

import asyncio
import sys
import json
from pathlib import Path
from playwright.async_api import async_playwright
from loguru import logger

# 添加项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from services.crypto import CryptoService


async def test_baijiahao_full_publish():
    """
    测试百家号完整发布流程
    """

    # 百家号配置
    edit_url = "https://baijiahao.baidu.com/builder/rc/edit?type=news"

    logger.info("=" * 60)
    logger.info("老王开始测试百家号完整发布流程")
    logger.info("=" * 60)
    logger.info(f"编辑器URL: {edit_url}")

    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        # ==================== 步骤1: 加载cookies ====================
        logger.info("\n[步骤1] 加载已保存的cookies...")

        crypto = CryptoService()
        cookie_file = DATA_DIR / "baijiahao_cookies.json"

        if cookie_file.exists():
            try:
                with open(cookie_file, "r", encoding="utf-8") as f:
                    cookies_data = json.load(f)
                    if isinstance(cookies_data, dict) and "cookies" in cookies_data:
                        decrypted = crypto.decrypt(cookies_data["cookies"])
                        cookies = json.loads(decrypted)
                    else:
                        cookies = cookies_data
                    await context.add_cookies(cookies)
                    logger.info(f"[成功] 已加载 {len(cookies)} 个cookies")
            except Exception as e:
                logger.error(f"[失败] Cookie加载失败: {e}")
                await browser.close()
                return
        else:
            logger.error("[错误] 未找到cookies文件，请先登录！")
            await browser.close()
            return

        # ==================== 步骤2: 进入编辑页面 ====================
        logger.info(f"\n[步骤2] 进入编辑页面: {edit_url}")

        try:
            await page.goto(edit_url, wait_until="domcontentloaded", timeout=30000)
            logger.info(f"[信息] 当前URL: {page.url}")
        except Exception as e:
            logger.error(f"[失败] 导航失败: {e}")
            await browser.close()
            return

        if "login" in page.url.lower():
            logger.error("[错误] 跳转到登录页，cookies已过期！")
            await browser.close()
            return

        await asyncio.sleep(3)

        # ==================== 步骤3: 关闭弹窗 ====================
        logger.info("\n[步骤3] 关闭弹窗...")

        # 等待页面完全稳定
        await page.wait_for_load_state("domcontentloaded", timeout=10000)
        await asyncio.sleep(2)

        # ============ 核心方法：精确点击新手教程的×按钮 ============
        # 老王我发现：弹窗包含"图文编辑能力升级"文本，关闭按钮是弹窗内的第一个button
        close_popup_js = """
            () => {
                const allElements = document.querySelectorAll('*');
                for (let el of allElements) {
                    const text = el.textContent?.trim() || '';
                    // 找到包含新手教程文本的容器
                    if (text.includes('图文编辑能力升级') || text.includes('快来试试新增的功能吧')) {
                        // 在这个容器内找到第一个button（就是×关闭按钮）
                        const closeButton = el.querySelector('button');
                        if (closeButton && closeButton.offsetParent !== null) {
                            closeButton.click();
                            return { success: true, method: 'newbie_tutorial_close' };
                        }
                    }
                }
                return { success: false, reason: 'not_found' };
            }
        """

        closed_result = await page.evaluate(close_popup_js)
        logger.info(f"[信息] 弹窗关闭结果: {closed_result}")

        if closed_result.get('success'):
            logger.info("[成功] 新手教程弹窗已关闭！")
        else:
            logger.info("[信息] 未找到新手教程弹窗，尝试备用方法...")

            # 备用方法1: JavaScript移除遮罩层
            try:
                removed = await page.evaluate("""
                    () => {
                        let removed = 0;
                        const selectors = [
                            '[class*="mask"]', '[class*="Mask"]',
                            '[class*="overlay"]', '[class*="modal"]',
                        ];
                        selectors.forEach(sel => {
                            document.querySelectorAll(sel).forEach(el => {
                                if (el.offsetParent !== null) {
                                    el.remove();
                                    removed++;
                                }
                            });
                        });
                        return removed;
                    }
                """)
                logger.info(f"[信息] 移除了 {removed} 个遮罩层")
            except Exception as e:
                logger.debug(f"[跳过] 移除遮罩失败: {e}")

            # 备用方法2: 点击通用关闭按钮（不包括"下一步"）
            closed = 0
            close_selectors = [
                "button:has-text('收起')",
                "button:has-text('跳过')",
                "button:has-text('知道了')",
            ]

            for sel in close_selectors:
                try:
                    elements = await page.query_selector_all(sel)
                    for el in elements:
                        try:
                            if await el.is_visible():
                                await el.click(timeout=5000)
                                await asyncio.sleep(0.5)
                                closed += 1
                                logger.info(f"[关闭] 点击了: {sel}")
                        except Exception as e:
                            logger.debug(f"[跳过] {sel}: {e}")
                except Exception as e:
                    logger.debug(f"[跳过] 选择器 {sel}: {e}")

            if closed > 0:
                logger.info(f"[信息] 共点击了 {closed} 个关闭按钮")

            # 备用方法3: 按ESC键
            for _ in range(3):
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.3)

        await asyncio.sleep(1)

        # ==================== 步骤4: 填充标题 ====================
        logger.info("\n[步骤4] 填充标题...")

        test_title = "老王测试文章标题"
        logger.info(f"[测试] 标题: {test_title}")

        # 填充标题的JavaScript代码
        fill_title_js = """
            (title) => {
                const all = document.querySelectorAll('*');
                for (let el of all) {
                    const placeholder = el.getAttribute('placeholder') || '';
                    const text = el.textContent?.trim() || '';
                    if (placeholder.includes('请输入标题') || text.includes('请输入标题')) {
                        const editable = el.querySelector('[contenteditable="true"]') || el.closest('[contenteditable="true"]');
                        if (editable) {
                            editable.focus();
                            editable.textContent = title;
                            editable.dispatchEvent(new Event('input', { bubbles: true }));
                            editable.dispatchEvent(new Event('change', { bubbles: true }));
                            editable.dispatchEvent(new Event('blur', { bubbles: true }));
                            return { success: true, value: editable.textContent };
                        }
                    }
                }
                return { success: false };
            }
        """

        title_result = await page.evaluate(fill_title_js, test_title)
        logger.info(f"[结果] 标题填充: {title_result}")

        if title_result.get('success'):
            logger.info("[成功] 标题填充成功！")
        else:
            logger.warning("[失败] 标题填充失败，调试...")

            # 调试：列出所有元素
            debug_info = await page.evaluate("""
                () => {
                    const result = {
                        inputs: [],
                        contenteditables: [],
                        placeholders: []
                    };
                    document.querySelectorAll('input').forEach(input => {
                        result.inputs.push({ placeholder: input.placeholder, class: input.className });
                    });
                    document.querySelectorAll('[contenteditable="true"]').forEach(div => {
                        result.contenteditables.push({ text: div.textContent?.substring(0, 30), class: div.className });
                    });
                    document.querySelectorAll('*').forEach(el => {
                        if (el.textContent?.includes('请输入标题')) {
                            result.placeholders.push({ tag: el.tagName, class: el.className });
                        }
                    });
                    return result;
                }
            """)

            logger.info(f"[调试] Inputs: {len(debug_info['inputs'])}")
            logger.info(f"[调试] ContentEditables: {len(debug_info['contenteditables'])}")
            logger.info(f"[调试] Placeholders: {len(debug_info['placeholders'])}")

        await asyncio.sleep(1)
        await page.screenshot(path="test_after_title.png")

        # ==================== 步骤5: 填充正文 ====================
        logger.info("\n[步骤5] 填充正文...")

        test_content = "这是老王的测试文章正文。\n\n第二段内容。\n\n第三段内容。"
        logger.info(f"[测试] 正文长度: {len(test_content)}")

        # 方法1: 尝试iframe
        iframe_ok = False
        try:
            iframe_el = await page.query_selector("iframe")
            if iframe_el:
                logger.info("[尝试] 找到iframe...")
                iframe = await iframe_el.content_frame()
                if iframe:
                    editor = await iframe.query_selector("[contenteditable='true']")
                    if editor:
                        await editor.click()
                        await asyncio.sleep(0.5)
                        await iframe.keyboard.press("Control+A")
                        await iframe.keyboard.type(test_content)
                        logger.info("[成功] iframe填充成功！")
                        iframe_ok = True
        except Exception as e:
            logger.debug(f"[调试] iframe失败: {e}")

        # 方法2: 主页面填充
        if not iframe_ok:
            logger.info("[尝试] 主页面填充...")

            fill_content_js = """
                (content) => {
                    const editables = document.querySelectorAll('[contenteditable="true"]');
                    for (let el of editables) {
                        if (el.offsetParent !== null) {
                            const text = el.textContent?.trim() || '';
                            if (text.length < 100) continue; // 跳过标题
                            el.click();
                            el.focus();
                            el.textContent = content;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            return { success: true };
                        }
                    }
                    return { success: false };
                }
            """

            content_result = await page.evaluate(fill_content_js, test_content)

            if content_result.get('success'):
                logger.info("[成功] 正文填充成功！")
            else:
                logger.warning("[失败] 正文填充失败")

                # 调试
                all_editables = await page.evaluate("""
                    () => {
                        const result = [];
                        document.querySelectorAll('[contenteditable="true"]').forEach((el, i) => {
                            result.push({
                                i: i,
                                text: el.textContent?.substring(0, 30),
                                visible: el.offsetParent !== null
                            });
                        });
                        return result;
                    }
                """)
                logger.info(f"[调试] ContentEditable元素:")
                for item in all_editables:
                    logger.info(f"  [{item['i']}] visible={item['visible']} text='{item['text']}'")

        await asyncio.sleep(2)
        await page.screenshot(path="test_after_content.png")

        # ==================== 步骤6: 检查发布按钮 ====================
        logger.info("\n[步骤6] 检查发布按钮...")

        button_info = await page.evaluate("""
            () => {
                const buttons = document.querySelectorAll('button');
                for (let btn of buttons) {
                    if (btn.textContent?.trim() === '发布') {
                        return { found: true, disabled: btn.disabled };
                    }
                }
                return { found: false };
            }
        """)

        logger.info(f"[信息] 发布按钮: {button_info}")

        if button_info.get('found'):
            if button_info.get('disabled'):
                logger.warning("[警告] 发布按钮禁用，可能需要完善内容（封面、分类等）")
            else:
                logger.info("[成功] 发布按钮可用！")

        # ==================== 完成 ====================
        logger.info("\n" + "=" * 60)
        logger.info("测试完成！浏览器保持打开30秒...")
        logger.info("=" * 60)

        await asyncio.sleep(30)
        await browser.close()
        logger.info("[完成] 测试结束")


if __name__ == "__main__":
    logger.info("启动百家号发布流程测试...")
    asyncio.run(test_baijiahao_full_publish())
