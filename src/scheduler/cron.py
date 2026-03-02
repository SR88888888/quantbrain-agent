import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from src.core.config import settings
from src.core.logger import log
from src.workflow.daily_report import generate_report
from src.memory.store import memory_store


class ReportScheduler:
    """定时任务调度器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        # 优化点4: 只执行早上09:00的任务
        morning_h, morning_m = self._parse_time(settings.SCHEDULE_MORNING)
        
        # 考虑到生成需要时间，提前1分钟触发，确保09:00准时发出（如果生成很快）
        # 或者准点触发
        self.scheduler.add_job(
            self._run_morning,
            CronTrigger(hour=morning_h, minute=morning_m, day_of_week="mon-fri"),
            id="morning_report",
            name="每日晨报",
        )

        # 每天凌晨衰减记忆
        self.scheduler.add_job(
            self._decay_memory,
            CronTrigger(hour=2, minute=0),
            id="memory_decay",
            name="记忆衰减",
        )

    async def _run_morning(self):
        log.warning("定时任务触发: 每日晨报")
        try:
            # 报告类型统一为 morning
            await generate_report(report_type="morning")
        except Exception as e:
            log.error(f"晨报生成失败: {e}")

    async def _decay_memory(self):
        memory_store.decay_importance()
        log.debug("记忆衰减完成")

    def start(self):
        self.scheduler.start()
        jobs = self.scheduler.get_jobs()
        log.warning(f"调度器启动: {len(jobs)}个任务")
        for job in jobs:
            log.warning(f"  - {job.name}: {job.trigger}")

    def stop(self):
        self.scheduler.shutdown()
        log.warning("调度器已停止")

    @staticmethod
    def _parse_time(time_str: str):
        parts = time_str.split(":")
        return int(parts[0]), int(parts[1])


report_scheduler = ReportScheduler()
