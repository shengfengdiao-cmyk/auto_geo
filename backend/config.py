# -*- coding: utf-8 -*-
"""
auto_geo 后端配置
老王我虽然暴躁，但配置必须清晰！
"""

import os
from pathlib import Path
from typing import Literal

# ==================== 项目路径 ====================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / ".cookies"
DATABASE_DIR = BASE_DIR / "backend" / "database"

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
DATABASE_DIR.mkdir(exist_ok=True)

# ==================== 应用配置 ====================
APP_NAME = "AutoGeo Backend"
APP_VERSION = "2.0.0"
DEBUG = True

# ==================== 服务配置 ====================
HOST = "127.0.0.1"
PORT = 8001  # 老王改的：避开8000端口的Windows残留占用问题
RELOAD = False  # 老王修复：Windows 上 Playwright 需要 ProactorEventLoop，与 reload 模式冲突！

# CORS配置
CORS_ORIGINS = [
    "http://localhost:5179",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "capacitor://localhost",
    "http://localhost",
]

# ==================== 数据库配置 ====================
DATABASE_URL = f"sqlite:///{DATABASE_DIR}/auto_geo_v3.db"

# ==================== 加密配置 ====================
# AES-256加密密钥（32字节）- 生产环境必须从环境变量读取
ENCRYPTION_KEY = os.getenv(
    "AUTO_GEO_ENCRYPTION_KEY",
    "auto-geo-default-key-32-bytes-length!!"  # 32字节密钥
).encode()[:32]  # 确保是32字节

# ==================== Playwright配置 ====================
# 浏览器类型
BROWSER_TYPE: Literal["chromium", "firefox", "webkit"] = "chromium"

# 浏览器启动参数
BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--window-size=1920,1080",
]

# 用户数据目录
USER_DATA_DIR = DATA_DIR / "browser_context"

# 登录检测配置
LOGIN_CHECK_INTERVAL = 1000  # 毫秒
LOGIN_MAX_WAIT_TIME = 120000  # 2分钟

# ==================== 平台配置 ====================
PLATFORMS = {
    "zhihu": {
        "id": "zhihu",
        "name": "知乎",
        "code": "ZH",
        "login_url": "https://www.zhihu.com/signin",
        "publish_url": "https://zhuanlan.zhihu.com/write",
        "color": "#0084FF",
    },
    "baijiahao": {
        "id": "baijiahao",
        "name": "百家号",
        "code": "BJH",
        "login_url": "https://baijiahao.baidu.com/builder/rc/static/login/index",
        "home_url": "https://baijiahao.baidu.com/builder/rc/static/edit/index",  # 百家号首页（作者中心）
        "publish_url": "https://baijiahao.baidu.com/builder/rc/edit/index",  # 编辑器首页
        "color": "#E53935",
    },
    "sohu": {
        "id": "sohu",
        "name": "搜狐号",
        "code": "SOHU",
        "login_url": "https://mp.sohu.com/",
        "publish_url": "https://mp.sohu.com/upload/article",
        "color": "#FF6B00",
    },
    "toutiao": {
        "id": "toutiao",
        "name": "头条号",
        "code": "TT",
        "login_url": "https://mp.toutiao.com/",
        "publish_url": "https://mp.toutiao.com/profile/article/article_edit",
        "color": "#333333",
    },
}

# ==================== 日志配置 ====================
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "auto_geo.log"
LOG_ROTATION = "100 MB"
LOG_RETENTION = "30 days"

LOG_DIR.mkdir(exist_ok=True)

# ==================== 任务配置 ====================
# 发布任务超时时间（秒）
PUBLISH_TIMEOUT = 300

# 最大并发发布数
MAX_CONCURRENT_PUBLISH = 3

# 失败重试次数
MAX_RETRY_COUNT = 2

# 重试间隔（秒）
RETRY_INTERVAL = 5
