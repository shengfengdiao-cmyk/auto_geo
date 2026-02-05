# -*- coding: utf-8 -*-
"""
Playwright浏览器管理器 - v5.0 指纹闭环版
负责：浏览器生命周期、账号授权、自动化发布、用户名提取
整合了浏览器管理和发布任务执行的基础设施

v5.0 新增 - 指纹闭环：
1. 从数据库 Account 表提取 user_agent 和 storage_state 注入浏览器上下文
2. verify_session 私有方法：发布前访问平台首页，检查登录状态
3. UA 绝对一致性：确保与授权时保存的 UA 完全一致
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError
from loguru import logger
from sqlalchemy.orm import Session

from backend.config import (
    BROWSER_TYPE, BROWSER_ARGS,
    LOGIN_CHECK_INTERVAL, LOGIN_MAX_WAIT_TIME, PLATFORMS
)
from backend.services.crypto import encrypt_cookies, encrypt_storage_state, decrypt_cookies, decrypt_storage_state
# 注意：这里我们只导入 registry，具体的发布器注册逻辑通常在应用启动时完成
from backend.services.playwright.publishers.base import registry


class AuthExpiredException(Exception):
    """会话已过期异常"""
    pass


class AuthTask:
    """授权任务模型"""

    def __init__(
            self,
            platform: str,
            account_id: Optional[int] = None,
            account_name: Optional[str] = None
    ):
        self.task_id = str(uuid.uuid4())
        self.platform = platform
        self.account_id = account_id
        self.account_name = account_name
        self.status = "pending"  # pending, running, success, failed, timeout
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.cookies: List[Dict] = []
        self.storage_state: Dict = {}
        self.error_message: Optional[str] = None
        self.created_at = datetime.now()
        # 授权成功后的账号ID（新账号创建后）
        self.created_account_id: Optional[int] = None


class PlaywrightManager:
    """
    Playwright 管理器 (单例模式)
    管理所有浏览器实例、授权任务和上下文

    v5.0 新增：指纹闭环
    """

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._auth_tasks: Dict[str, AuthTask] = {}
        self._contexts: Dict[str, BrowserContext] = {}
        self._is_running = False
        # 数据库会话工厂（由外部设置，通常是 SessionLocal）
        self._db_factory: Optional[Callable] = None
        # WebSocket 通知回调
        self._ws_callback: Optional[Callable] = None

    def set_db_factory(self, db_factory: Callable):
        """设置数据库会话工厂"""
        self._db_factory = db_factory

    def set_ws_callback(self, callback: Callable):
        """设置 WebSocket 通知回调"""
        self._ws_callback = callback

    def _get_db(self) -> Optional[Session]:
        """获取数据库会话"""
        if self._db_factory:
            # 如果是生成器函数，使用 next()
            # 如果是类（如 SessionLocal），直接实例化
            try:
                db_obj = self._db_factory()
                if hasattr(db_obj, '__next__'):
                    return next(db_obj)
                return db_obj
            except Exception as e:
                logger.error(f"获取数据库会话失败: {e}")
                return None
        return None

    async def start(self):
        """启动浏览器服务"""
        if self._is_running:
            return

        logger.info("🚀 正在启动 Playwright 浏览器服务...")
        self._playwright = await async_playwright().start()

        # 尝试查找本地 Chrome 路径（绕过检测，更稳定）
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]

        executable_path = None
        for path in chrome_paths:
            if os.path.exists(path):
                executable_path = path
                logger.info(f"✅ 找到本地 Chrome 浏览器: {path}")
                break

        launch_options = {
            "headless": False,  # 授权和发布通常需要有头模式，或者由上层控制
            "args": BROWSER_ARGS + [
                "--disable-blink-features=AutomationControlled",  # 核心反爬
                "--disable-dev-shm-usage",
                "--disable-background-networking",
                "--disable-features=Translate",
                "--no-sandbox"
            ]
        }

        if executable_path:
            launch_options["executable_path"] = executable_path

        try:
            self._browser = await self._playwright[BROWSER_TYPE].launch(**launch_options)
            self._is_running = True
            logger.success(f"✅ Playwright 浏览器 ({BROWSER_TYPE}) 已就绪")
        except Exception as e:
            logger.error(f"❌ 浏览器启动失败: {e}")
            raise e

    async def stop(self):
        """停止浏览器服务"""
        if not self._is_running:
            return

        # 关闭所有上下文
        for context in self._contexts.values():
            await context.close()
        self._contexts.clear()

        # 关闭浏览器
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        self._is_running = False
        logger.info("🛑 Playwright 浏览器服务已停止")

    # ==================== 指纹闭环相关 ====================

    async def _verify_session(self, page: Page, platform: str) -> bool:
        """
        验证会话状态 - v5.1 增强版

        验证方式：
        1. 访问平台首页，检查是否出现登录按钮（UI 检查）
        2. 针对知乎、搜狐、百家号增加"静默接口校验"（v5.1 新增）
           - 知乎：检查 /me/api/v3/user/info 接口
           - 百家号：检查登录状态接口
           - 搜狐：检查登录状态接口

        如果未登录，立即抛出 AuthExpiredException。

        遵守架构金律第4条：指纹对齐
        必须从数据库 Account 表提取 user_agent 和 storage_state 注入浏览器上下文

        Args:
            page: Playwright Page对象
            platform: 平台ID

        Returns:
            是否已登录

        Raises:
            AuthExpiredException: 如果会话已过期
        """
        logger.info(f"[Fingerprint] 验证会话状态: {platform}")

        try:
            # 获取平台首页 URL
            platform_config = PLATFORMS.get(platform)
            if not platform_config:
                logger.warning(f"[Fingerprint] 未找到平台配置: {platform}")
                return False

            home_url = platform_config.get("home_url") or platform_config.get("login_url")

            # 访问平台首页
            logger.info(f"[Fingerprint] 访问平台首页: {home_url}")
            await page.goto(home_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # ========== v5.1 新增：静默接口校验 ==========
            api_check_passed = True
            if platform == "zhihu":
                api_check_passed = await self._zhihu_api_check(page)
            elif platform == "baijiahao":
                api_check_passed = await self._baijiahao_api_check(page)
            elif platform == "sohu":
                api_check_passed = await self._sohu_api_check(page)

            if not api_check_passed:
                logger.error(f"[Fingerprint] 静默接口校验失败，会话已过期: {platform}")
                raise AuthExpiredException(f"平台 {platform} 静默接口校验失败，会话已过期")

            # ========== UI 检查：是否出现登录按钮 ==========
            has_login_button = await page.evaluate('''() => {
                // 查找包含登录关键词的按钮
                const loginSelectors = [
                    'button:has-text("登录")',
                    'button:has-text("Log in")',
                    'button:has-text("Sign in")',
                    'a[href*="login"]',
                    'a[href*="signin"]',
                    '[class*="login"]',
                    '[id*="login"]'
                ];

                for (let selector of loginSelectors) {
                    const elements = document.querySelectorAll(selector);
                    for (let el of elements) {
                        if (el.offsetParent !== null) {
                            // 检查按钮文本
                            const text = el.textContent?.trim().toLowerCase() || '';
                            if (text.includes('登录') ||
                                text.includes('login') ||
                                text.includes('sign in')) {
                                return true;
                            }
                        }
                    }
                }
                return false;
            }''')

            if has_login_button:
                logger.error(f"[Fingerprint] 检测到登录按钮，会话已过期: {platform}")
                raise AuthExpiredException(f"平台 {platform} 会话已过期，需要重新授权")

            logger.info(f"[Fingerprint] 会话验证通过: {platform}")
            return True

        except AuthExpiredException:
            raise
        except Exception as e:
            logger.warning(f"[Fingerprint] 会话验证异常: {e}")
            # 验证失败不阻止发布，由发布器自行处理
            return True

    async def _zhihu_api_check(self, page: Page) -> bool:
        """
        知乎静默接口校验

        通过检查 /me/api/v3/user/info 接口的响应状态来判断会话是否有效
        """
        try:
            logger.info("[Fingerprint] 执行知乎静默接口校验...")
            status = await page.evaluate('''
                async () => {
                    try {
                        const response = await fetch('/me/api/v3/user/info', {
                            method: 'GET',
                            credentials: 'include'
                        });
                        return response.status;
                    } catch (e) {
                        return 999; // 网络错误
                    }
                }
            ''')
            logger.info(f"[Fingerprint] 知乎接口响应状态: {status}")

            if status in [401, 403]:
                logger.warning(f"[Fingerprint] 知乎接口返回 {status}，会话已过期")
                return False
            return True
        except Exception as e:
            logger.debug(f"[Fingerprint] 知乎接口校验异常: {e}")
            return True  # 校验失败不阻止，继续执行

    async def _baijiahao_api_check(self, page: Page) -> bool:
        """
        百家号静默接口校验

        通过检查用户信息接口的响应状态来判断会话是否有效
        """
        try:
            logger.info("[Fingerprint] 执行百家号静默接口校验...")
            status = await page.evaluate('''
                async () => {
                    try {
                        // 尝试访问用户信息接口
                        const response = await fetch('/authorpc/api/user/info', {
                            method: 'GET',
                            credentials: 'include'
                        });
                        return response.status;
                    } catch (e) {
                        return 999; // 网络错误
                    }
                }
            ''')
            logger.info(f"[Fingerprint] 百家号接口响应状态: {status}")

            if status in [401, 403]:
                logger.warning(f"[Fingerprint] 百家号接口返回 {status}，会话已过期")
                return False
            return True
        except Exception as e:
            logger.debug(f"[Fingerprint] 百家号接口校验异常: {e}")
            return True  # 校验失败不阻止，继续执行

    async def _sohu_api_check(self, page: Page) -> bool:
        """
        搜狐静默接口校验

        通过检查用户信息接口的响应状态来判断会话是否有效
        """
        try:
            logger.info("[Fingerprint] 执行搜狐静默接口校验...")
            status = await page.evaluate('''
                async () => {
                    try {
                        // 尝试访问用户信息接口
                        const response = await fetch('/api/user/info', {
                            method: 'GET',
                            credentials: 'include'
                        });
                        return response.status;
                    } catch (e) {
                        return 999; // 网络错误
                    }
                }
            ''')
            logger.info(f"[Fingerprint] 搜狐接口响应状态: {status}")

            if status in [401, 403]:
                logger.warning(f"[Fingerprint] 搜狐接口返回 {status}，会话已过期")
                return False
            return True
        except Exception as e:
            logger.debug(f"[Fingerprint] 搜狐接口校验异常: {e}")
            return True  # 校验失败不阻止，继续执行

    # ==================== 授权相关 ====================

    async def create_auth_task(
            self,
            platform: str,
            account_id: Optional[int] = None,
            account_name: Optional[str] = None
    ) -> AuthTask:
        """
        创建授权任务：启动浏览器，打开登录页，注入JS桥接

        v5.0 增强：保存 user_agent 到数据库
        """
        logger.info(f"[Auth] 开始创建授权任务: platform={platform}, account_id={account_id}")

        await self.start()

        if platform not in PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}")

        task = AuthTask(platform, account_id, account_name)
        self._auth_tasks[task.task_id] = task

        platform_config = PLATFORMS[platform]

        # 标准化 User-Agent（确保与后续发布时一致）
        standard_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        # 创建浏览器上下文（使用标准 UA）
        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=standard_ua
        )
        task.context = context

        # 注入 JS 桥接函数：供前端控制页调用
        async def confirm_auth_wrapper(task_id_from_browser: str) -> str:
            """浏览器调用的确认授权函数"""
            return await self._finalize_auth(task_id_from_browser, standard_ua)

        await context.expose_function("confirmAuth", confirm_auth_wrapper)
        logger.info(f"[Auth] confirmAuth 函数已注入")

        # Tab 1: 打开目标平台登录页
        login_page = await context.new_page()
        task.page = login_page
        await login_page.goto(platform_config["login_url"], wait_until="domcontentloaded")

        # Tab 2: 打开本地控制页
        # 假设 static 目录在 backend 下
        static_dir = Path(__file__).parent.parent / "static"
        control_page_path = static_dir / "auth_confirm.html"

        # 兼容性处理：如果找不到文件，使用内置HTML
        if not control_page_path.exists():
            logger.warning(f"控制页模板未找到: {control_page_path}")

        control_page_url = f"file:///{control_page_path.as_posix()}?task_id={task.task_id}&platform={platform}"
        control_page = await context.new_page()
        try:
            await control_page.goto(control_page_url)
        except Exception as e:
            logger.error(f"打开控制页失败: {e}")

        task.status = "running"
        logger.info(f"[Auth] 授权任务就绪: {task.task_id}")

        return task

    async def _finalize_auth(self, task_id: str, user_agent: str) -> str:
        """
        核心：提取登录凭证并入库

        v5.0 增强：保存 user_agent 到数据库，确保指纹一致性

        v5.1 修复：使用 context.storage_state() 获取标准格式的 StorageState
        - 不再手动拼接 localStorage 字典
        - 直接调用 Playwright 标准 API 获取包含 Cookies 和 LocalStorage 的完整状态
        - 这样存储的格式与 browser.new_context(storage_state=...) 完全兼容
        """
        task = self._auth_tasks.get(task_id)
        if not task:
            return json.dumps({"success": False, "message": "任务已失效"})

        logger.info(f"[Auth] 收到确认信号: {task_id}")

        try:
            # 1. 提取标准格式的 StorageState (v5.1 修复)
            # 直接使用 context.storage_state() 获取 Playwright 标准格式
            # 返回格式: {"cookies": [...], "origins": [{"origin": "https://...", "localStorage": [...]}]}
            storage_state = await task.context.storage_state()
            cookies = storage_state.get("cookies", [])

            logger.info(f"[Auth] StorageState 提取完成: {len(cookies)} cookies, {len(storage_state.get('origins', []))} origins")

            # 2. 基础验证
            # 针对不同平台的关键 Cookie 检查
            platform_checks = {
                "zhihu": "z_c0",
                "baijiahao": "BDUSS",
                "toutiao": "sessionid"
            }
            key_cookie = platform_checks.get(task.platform)
            if key_cookie and not any(c['name'] == key_cookie for c in cookies):
                return json.dumps({"success": False, "message": f"未检测到登录凭证 ({key_cookie})，请先登录"})

            # 3. 提取用户名
            username = await self._extract_username(task.page, task.platform)
            logger.info(f"[Auth] 提取到用户名: {username}")

            # 4. 数据库操作
            db = self._get_db()
            if not db:
                return json.dumps({"success": False, "message": "数据库连接失败"})

            try:
                from backend.database.models import Account

                # 加密敏感数据
                enc_cookies = encrypt_cookies(cookies)
                enc_storage = encrypt_storage_state(storage_state)

                if task.account_id:
                    # 更新
                    account = db.query(Account).filter(Account.id == task.account_id).first()
                    if account:
                        account.cookies = enc_cookies
                        account.storage_state = enc_storage
                        account.username = username or account.username
                        account.user_agent = user_agent  # v5.0 新增：保存 UA
                        account.status = 1
                        account.last_auth_time = datetime.now()
                        db.commit()
                        logger.success(f"[Auth] 账号 {account.account_name} 更新成功 (UA 已保存)")
                else:
                    # 新增
                    name = task.account_name or f"{PLATFORMS[task.platform]['name']}_{username or 'User'}"
                    account = Account(
                        platform=task.platform,
                        account_name=name,
                        username=username,
                        cookies=enc_cookies,
                        storage_state=enc_storage,
                        user_agent=user_agent,  # v5.0 新增：保存 UA
                        status=1,
                        last_auth_time=datetime.now()
                    )
                    db.add(account)
                    db.commit()
                    db.refresh(account)
                    task.created_account_id = account.id
                    logger.success(f"[Auth] 新账号 {name} 创建成功 (UA 已保存)")

                task.status = "success"

                # WebSocket 通知
                if self._ws_callback:
                    await self._ws_callback({
                        "type": "auth_complete",
                        "task_id": task_id,
                        "success": True,
                        "platform": task.platform
                    })

                # 延时关闭
                asyncio.create_task(self._delayed_close_task(task_id))

                return json.dumps({"success": True, "message": "授权成功！账号已保存"})

            except Exception as e:
                db.rollback()
                logger.error(f"[Auth] 数据库错误: {e}")
                return json.dumps({"success": False, "message": str(e)})
            finally:
                db.close()

        except Exception as e:
            logger.error(f"[Auth] 处理异常: {e}")
            return json.dumps({"success": False, "message": str(e)})

    async def _delayed_close_task(self, task_id: str):
        """延时关闭任务，给前端反应时间"""
        await asyncio.sleep(5)
        await self.close_auth_task(task_id)

    async def close_auth_task(self, task_id: str):
        """关闭任务资源"""
        task = self._auth_tasks.get(task_id)
        if task:
            if task.context: await task.context.close()
            if task_id in self._auth_tasks: del self._auth_tasks[task_id]
            logger.info(f"[Auth] 任务资源已释放: {task_id}")

    async def _extract_username(self, page: Page, platform: str) -> Optional[str]:
        """
        从页面提取用户名 (增强版)
        """
        try:
            if platform == "zhihu":
                # 尝试多种选择器
                selectors = [".AppHeader-profileText", ".Header-userName", ".UserLink-link", ".ProfileHeader-name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "toutiao":
                selectors = [".user-name", ".name", ".mp-name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            return None
        except:
            return None

    # ==================== 发布相关 ====================

    async def execute_publish(self, article: Any, account: Any) -> Dict[str, Any]:
        """
        供 Service 调用的发布执行入口 (核心)

        v5.0 增强：
        1. 从数据库 Account 表提取 user_agent 注入浏览器上下文
        2. 发布前调用 verify_session 验证登录状态
        3. 确保 UA 绝对一致性

        v5.1 修复：
        1. 修复 StorageState 注入流程：确保解密出的 JSON 直接作为 browser.new_context 的参数
        2. 增加 UA 注入安全性检查日志

        v6.0 首席架构师修复：
        1. 反检测抹除：context.add_init_script() 彻底抹除 navigator.webdriver 特征
        2. 指纹校验：UA 为空时拒绝执行
        """
        # ========== v6.0 新增：指纹校验 - UA 为空时拒绝执行 ==========
        stored_user_agent = getattr(account, 'user_agent', None)
        if not stored_user_agent:
            logger.error(f"[Fingerprint] ❌ 账号 {account.account_name} 缺少 user_agent，拒绝执行发布")
            return {"success": False, "error_msg": "账号缺少 user_agent，请先完成授权流程"}

        # 打印当前数据库存储的 UA
        logger.info(f"[Fingerprint] ✓ 账号 {account.account_name} 数据库 UA: {stored_user_agent[:60] if stored_user_agent else 'None'}...")

        await self.start()

        # 动态获取发布器
        publisher = registry.get(account.platform)
        if not publisher:
            return {"success": False, "error_msg": f"未找到平台 {account.platform} 的适配器"}

        # 准备上下文
        context = None
        try:
            # ========== v5.1 修复：解密并注入标准格式的 StorageState ==========
            state_data = None
            if account.storage_state:
                try:
                    decrypted = decrypt_storage_state(account.storage_state)
                    if decrypted:
                        state_data = decrypted
                        logger.info(f"[Fingerprint] StorageState 解密成功: {len(decrypted.get('cookies', []))} cookies, {len(decrypted.get('origins', []))} origins")
                    else:
                        logger.warning(f"[Fingerprint] 账号 {account.account_name} StorageState 解密结果为空")
                except Exception as e:
                    logger.warning(f"[Fingerprint] 账号 {account.account_name} StorageState 解密失败: {e}，尝试裸奔")

            # ========== v5.1 新增：UA 注入安全性检查 ==========
            # 从数据库提取 user_agent（指纹对齐），确保与授权时保存的 UA 完全一致
            stored_user_agent = getattr(account, 'user_agent', None)
            if not stored_user_agent:
                logger.warning(f"[Fingerprint] 账号 {account.account_name} 缺少 user_agent，使用默认 UA")

            # 定义标准 UA（与授权时一致）
            standard_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            user_agent = stored_user_agent or standard_ua

            # UA 注入安全性日志：检查 UA 是否匹配
            if stored_user_agent:
                if stored_user_agent == standard_ua:
                    logger.info(f"[Fingerprint] ✓ UA 注入验证通过：数据库 UA 与标准 UA 一致")
                    logger.info(f"[Fingerprint] 注入 UA: {user_agent[:60]}...")
                else:
                    logger.warning(f"[Fingerprint] ⚠ UA 不匹配告警：数据库 UA 与标准 UA 不一致")
                    logger.warning(f"[Fingerprint] 数据库 UA: {stored_user_agent[:60]}...")
                    logger.warning(f"[Fingerprint] 标准 UA: {standard_ua[:60]}...")
                    logger.warning(f"[Fingerprint] 注入 UA: {user_agent[:60]}...")
            else:
                logger.info(f"[Fingerprint] 使用默认 UA: {user_agent[:60]}...")

            # 创建浏览器上下文（注入标准格式的 storage_state 和 user_agent）
            # v5.1 修复：确保 state_data 是符合 Playwright 标准的 Dict 格式
            # 这样 Playwright 会自动处理跨域的 localStorage 恢复

            # ========== v6.0 首席架构师修复：Session 拯救（反检测抹除）==========
            # 彻底抹除 navigator.webdriver 特征，避免被反爬虫系统识别
            anti_detection_script = '''
                // 覆盖 navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });

                // 覆盖 Chrome 对象的检测
                Object.defineProperty(window, 'chrome', {
                    get: () => undefined,
                    configurable: true
                });

                // 覆盖权限查询
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = () => Promise.resolve({ state: 'granted', onchange: null });

                // 覆盖 plugins 长度
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                    configurable: true
                });

                // 覆盖 languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                    configurable: true
                });
            '''

            context = await self._browser.new_context(
                storage_state=state_data if state_data else None,
                user_agent=user_agent,
                viewport={"width": 1280, "height": 800}
            )

            # 注入反检测抹除脚本
            await context.add_init_script(anti_detection_script)
            logger.info("[Fingerprint] 已注入反检测抹除脚本")

            page = await context.new_page()

            # v6.0 新增：预警截图机制
            async def take_failure_screenshot(reason: str):
                """捕获失败截图"""
                try:
                    import os
                    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
                    os.makedirs(logs_dir, exist_ok=True)
                    screenshot_path = os.path.join(logs_dir, f"fail_{account.platform}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png")
                    await page.screenshot(path=screenshot_path, full_page=True)
                    logger.info(f"[Fingerprint] 预警截图已保存: {screenshot_path} (原因: {reason})")
                except Exception as e:
                    logger.error(f"[Fingerprint] 截图失败: {e}")

            # v5.0 新增：验证会话状态（带截图）
            logger.info("[Fingerprint] 开始验证会话状态...")
            try:
                await self._verify_session(page, account.platform)
            except AuthExpiredException as e:
                logger.error(f"[Fingerprint] 会话验证失败: {e}")
                await take_failure_screenshot("会话过期")
                return {"success": False, "error_msg": str(e)}
            except Exception as e:
                logger.error(f"[Fingerprint] 会话验证异常: {e}")
                await take_failure_screenshot(f"验证异常: {e}")
                return {"success": False, "error_msg": str(e)}

            # 执行发布逻辑
            logger.info(f"🚀 [Publish] 开始执行发布: {account.platform} - {article.title}")
            try:
                result = await publisher.publish(page, article, account)
                return result
            except TimeoutError as e:
                logger.error(f"[Publish] 超时错误: {e}")
                await take_failure_screenshot(f"超时: {e}")
                return {"success": False, "error_msg": f"操作超时: {str(e)}"}
            except AuthExpiredException as e:
                logger.error(f"[Publish] 认证失败: {e}")
                await take_failure_screenshot(f"认证失败: {e}")
                return {"success": False, "error_msg": f"认证失败: {str(e)}"}
            except Exception as e:
                logger.exception(f"[Publish] 执行异常: {e}")
                await take_failure_screenshot(f"发布异常: {e}")
                return {"success": False, "error_msg": str(e)}

        except Exception as e:
            logger.exception(f"❌ [Publish] 执行异常: {e}")
            return {"success": False, "error_msg": str(e)}
        finally:
            if context:
                await context.close()


# 全局单例
playwright_mgr = PlaywrightManager()
