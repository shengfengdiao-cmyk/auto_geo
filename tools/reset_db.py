# -*- coding: utf-8 -*-
"""
数据库重置工具 - 解决数据库损坏问题
功能：
1. 关闭所有数据库连接
2. 删除损坏的数据库文件及 WAL/SHM 文件
3. 重新初始化干净的表结构
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from backend.database import init_db, engine, Base
from backend.config import DATABASE_DIR, DATABASE_URL


def close_all_connections():
    """关闭所有数据库连接"""
    try:
        engine.dispose()
        logger.info("已关闭所有数据库连接池")
    except Exception as e:
        logger.warning(f"关闭连接时出现警告: {e}")


def remove_database_files():
    """删除损坏的数据库文件及关联文件"""
    db_path = DATABASE_DIR / "auto_geo_v3.db"

    # 需要删除的文件列表
    files_to_remove = [
        db_path,  # 主数据库文件
        db_path.with_suffix(".db-wal"),  # WAL 日志文件
        db_path.with_suffix(".db-shm"),  # 共享内存文件
    ]

    removed_files = []
    for file_path in files_to_remove:
        if file_path.exists():
            try:
                os.remove(file_path)
                removed_files.append(str(file_path))
                logger.info(f"已删除: {file_path.name}")
            except PermissionError:
                logger.error(f"删除失败: {file_path} - 文件可能被其他进程占用")
                return False
            except Exception as e:
                logger.error(f"删除 {file_path} 失败: {e}")
                return False

    if not removed_files:
        logger.warning("未找到数据库文件，无需删除")
    else:
        logger.success(f"成功删除 {len(removed_files)} 个文件")

    return True


def init_fresh_database():
    """初始化全新的数据库"""
    try:
        init_db()
        logger.success("数据库初始化完成")
        return True
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False


def verify_database_integrity():
    """验证数据库完整性"""
    try:
        with engine.connect() as conn:
            # 尝试执行一个简单的查询来验证数据库
            result = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in result]
            logger.info(f"数据库包含 {len(tables)} 个表: {tables}")
            return True
    except Exception as e:
        logger.error(f"数据库完整性检查失败: {e}")
        return False


def main():
    """主流程"""
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )

    logger.warning("=" * 60)
    logger.warning("开始重置数据库 - 所有数据将被清空！")
    logger.warning("=" * 60)

    # 1. 关闭所有连接
    logger.info("\n[1/4] 关闭所有数据库连接...")
    close_all_connections()

    # 2. 删除损坏的数据库文件
    logger.info("\n[2/4] 删除损坏的数据库文件...")
    if not remove_database_files():
        logger.error("删除数据库文件失败，请检查是否有进程正在使用")
        sys.exit(1)

    # 3. 重新初始化数据库
    logger.info("\n[3/4] 重新初始化数据库表结构...")
    if not init_fresh_database():
        logger.error("数据库初始化失败")
        sys.exit(1)

    # 4. 验证数据库完整性
    logger.info("\n[4/4] 验证数据库完整性...")
    if not verify_database_integrity():
        logger.error("数据库完整性验证失败")
        sys.exit(1)

    logger.success("\n" + "=" * 60)
    logger.success("数据库重置完成！")
    logger.success("=" * 60)
    logger.info("\n提示:")
    logger.info("1. 请重启后端服务以应用新的数据库")
    logger.info("2. 如果问题仍然存在，请检查磁盘空间和文件权限")
    logger.info("3. WAL 模式已启用，可防止并发锁问题")


if __name__ == "__main__":
    confirm = input("警告: 此操作将清空所有数据库数据！确认继续? (yes/no): ")
    if confirm.lower() in ["yes", "y"]:
        main()
    else:
        logger.info("操作已取消")
