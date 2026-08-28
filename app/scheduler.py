import time
from datetime import datetime
from zoneinfo import ZoneInfo
from app.config import settings
from app import state
from app.transports.telegram import send_message
def main():
 print('[scheduler] running',flush=True)
 while True:
  now=datetime.now(ZoneInfo(settings.timezone)).isoformat()
  for r in state.due_reminders(now):
   send_message('⏰ Reminder: '+r['title']);state.mark_sent(r['id'])
  time.sleep(15)
if __name__=='__main__':main()
