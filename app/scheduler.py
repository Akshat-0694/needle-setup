import time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from app.config import settings
from app import state
from app.agents.morning import run

def morning_job():
    try:
        result = run()
        task_id = state.create_task("morning", "Scheduled morning brief")
        state.update_task(task_id, "completed", result)
        state.event("morning.completed", "morning", {"task_id": task_id, "result": result})
        print("[morning] completed", flush=True)
    except Exception as exc:
        state.event("morning.failed", "morning", {"error": str(exc)})
        print(f"[morning] failed: {exc}", flush=True)

scheduler = BlockingScheduler(timezone=ZoneInfo(settings.timezone))
scheduler.add_job(
    morning_job,
    CronTrigger(hour=8, minute=0, timezone=ZoneInfo(settings.timezone)),
    id="morning-brief",
    replace_existing=True,
)

if __name__ == "__main__":
    print(f"Scheduler running in {settings.timezone}; morning brief at 08:00.", flush=True)
    scheduler.start()
