import time
from app.config import settings
from app.agents.router import route
from app.transports.telegram import get_updates,send_message
def fmt(x):
 if isinstance(x,dict):
  if x.get('error'):return '❌ '+str(x['error'])
  if x.get('title'):return '• '+str(x['title'])
  return str(x)
 if isinstance(x,list):
  return '\n'.join(('• '+str(y.get('title') or y.get('name') or y.get('url') or y) if isinstance(y,dict) else '• '+str(y)) for y in x) or 'Nothing found.'
 return str(x)
def main():
 if not settings.telegram_bot_token or not settings.telegram_chat_id:
  print('[telegram] not configured; sleeping',flush=True)
  while True:time.sleep(3600)
 off=None;print('[telegram] polling',flush=True)
 while True:
  try:
   for u in get_updates(off).get('result',[]):
    off=u['update_id']+1;m=u.get('message') or {};c=m.get('chat') or {};text=m.get('text')
    if text and str(c.get('id'))==str(settings.telegram_chat_id):send_message(fmt(route(text)))
  except Exception as e:print('[telegram] error:',e,flush=True);time.sleep(5)
if __name__=='__main__':main()
