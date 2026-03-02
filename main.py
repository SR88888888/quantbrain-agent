import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.logger import log
from src.core.config import settings
from src.scheduler.cron import report_scheduler
from src.workflow.daily_report import generate_report

# 注册MCP工具
import src.mcp.tools.stock_tools  # noqa: F401


async def main():
    log.warning("=" * 50)
    log.warning("QuantBrain Agent v2.0 - 金融研报系统")
    log.warning("=" * 50)
    log.warning(f"LLM: {settings.MODEL_NAME} @ {settings.LLM_BASE_URL}")
    log.warning(f"监控: {settings.WATCH_LIST}")
    log.warning(f"早盘: {settings.SCHEDULE_MORNING}")
    log.warning(f"午间: {settings.SCHEDULE_NOON}")
    log.warning(f"收盘: {settings.SCHEDULE_CLOSING}")
    log.warning("=" * 50)

#     # 启动时立即生成一次报告
#     log.warning("首次启动, 生成测试报告...")
#     try:
#         await generate_report(report_type="closing")
#     except Exception as e:
#         log.error(f"测试报告生成失败: {e}")

    # 启动定时调度
    report_scheduler.start()

    log.warning("系统就绪, 等待定时任务触发...")
    try:
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        log.warning("收到中断信号, 系统关闭")
        report_scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
