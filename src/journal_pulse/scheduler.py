from apscheduler.schedulers.blocking import BlockingScheduler

from journal_pulse.config import Settings


def build_scheduler(settings: Settings, job):
    scheduler = BlockingScheduler(timezone='UTC')
    scheduler.add_job(job, 'cron', hour=settings.daily_report_hour, minute=settings.daily_report_minute)
    return scheduler
