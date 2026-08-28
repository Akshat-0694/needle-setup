import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.blocking import BlockingScheduler
from app.config import settings
from app import state
from app.agents.notification import run as notify
from app.telegram import send_message

def check_reminders():
    now=datetime.now(ZoneInfo(settings.timezone)).isoformat()
    for r in state.due_reminders(now):
        event={"type":"task.reminder","task_id":r["task_id"],"title":r["title"],"notes":r["notes"],"remind_at":r["remind_at"]}
        try:
            result=notify(event); text=None
            if isinstance(result,dict):
                for x in result.get("results",[]):
                    text=x.get("result") or x.get("text")
                    if text: break
            if not text: text=f"⏰ Reminder: {r['title']}" + (f"\n{r['notes']}" if r["notes"] else "")
            asyncio.run(send_message(text)); state.mark_reminder_sent(r["id"])
            state.add_event("notification.sent","scheduler",event)
        except Exception as e:
            state.add_event("notification.failed","scheduler",{"reminder_id":r["id"],"error":str(e)})
            print(f"[scheduler] {e}",flush=True)
scheduler=BlockingScheduler(timezone=ZoneInfo(settings.timezone))
scheduler.add_job(check_reminders,"interval",seconds=30,id="reminder-check",replace_existing=True)
if __name__=="__main__":
    print(f"[scheduler] running in {settings.timezone}",flush=True); scheduler.start()
