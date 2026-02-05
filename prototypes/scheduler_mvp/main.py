import json
import time
import logging
import os
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

# ==========================================
# 1. 日志配置：让你的程序运行过程清晰可见
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(module)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ==========================================
# 2. 核心业务逻辑（Mock 模拟函数）
# ==========================================

def ai_generate_content(city, keyword):
    """
    模拟调用 AI 接口生成文章
    后期接入：替换为 requests.post 调用公司大模型接口
    """
    logger.info(f"👉 [步骤1: AI生成] 正在为 {city} 生成关于 '{keyword}' 的内容...")
    time.sleep(1.5)  # 模拟网络耗时
    return f"【{city}{keyword}专题】这是一篇经过SEO优化的自动化生成文章内容。"


def auto_publish(content):
    """
    模拟文章发布到公司 CMS 系统
    后期接入：替换为公司现有的发布 API 函数
    """
    logger.info(f"👉 [步骤2: 自动发布] 正在将内容推送到发布接口...")
    time.sleep(1)  # 模拟发布耗时
    mock_url = f"https://www.example.com/article/{int(time.time())}.html"
    return mock_url


def check_indexing(url):
    """
    模拟搜索引擎收录查询
    后期接入：对接百度/Google收录查询脚本
    """
    logger.info(f"👉 [步骤3: 收录查询] 正在检测链接收录状态: {url}")
    time.sleep(1)
    return "查询中 (预计24小时内更新)"


# ==========================================
# 3. 任务执行流：串联生成、发布、查询
# ==========================================

def run_geo_workflow(task_info):
    """
    单个任务的完整生命周期
    """
    city = task_info.get("city")
    keyword = task_info.get("keyword")
    task_id = task_info.get("id")

    print("\n" + "=" * 50)
    logger.info(f"🔔 任务触发 | ID: {task_id} | 目标: {city}-{keyword}")

    try:
        # 1. 生成内容
        article_content = ai_generate_content(city, keyword)

        # 2. 自动发布
        published_url = auto_publish(article_content)
        logger.info(f"✅ 发布成功: {published_url}")

        # 3. 查询收录
        status = check_indexing(published_url)
        logger.info(f"ℹ️ 当前状态: {status}")

    except Exception as e:
        logger.error(f"❌ 任务 {task_id} 执行出错: {str(e)}")

    print("=" * 50 + "\n")


# ==========================================
# 4. 任务加载与调度配置
# ==========================================

def load_tasks_from_json():
    """从本地 tasks.json 读取任务列表"""
    file_path = 'tasks.json'
    if not os.path.exists(file_path):
        logger.error(f"找不到配置文件: {file_path}")
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def start_scheduler():
    # 从 JSON 加载任务数据
    tasks = load_tasks_from_json()
    if not tasks:
        logger.warning("任务列表为空，程序退出。")
        return

    # 初始化调度器
    scheduler = BlockingScheduler()

    for task in tasks:
        # --- 测试模式说明 ---
        # 为了让你运行后能立即看到效果，这里使用了 'interval' (每隔多久执行一次)
        # 如果要按照 tasks.json 里的 cron_time 执行，可以改为 trigger='cron'

        scheduler.add_job(
            func=run_geo_workflow,
            trigger='interval',
            seconds=20,  # 每 20 秒执行一次，方便演示
            args=[task],  # 传递任务字典
            id=f"job_{task['id']}",
            replace_existing=True
        )
        logger.info(f"📍 任务已排期: [{task['city']}-{task['keyword']}] - 模式: 测试循环(20s)")

    logger.info(f"🚀 GEO 调度系统启动成功 (共 {len(tasks)} 个任务)")
    logger.info("按下 Ctrl+C 可停止运行")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 系统已安全关闭")


if __name__ == "__main__":
    start_scheduler()