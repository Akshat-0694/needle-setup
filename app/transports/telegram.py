import httpx
from app.config import settings
def url(m):return f'https://api.telegram.org/bot{settings.telegram_bot_token}/{m}'
def send_message(text):
 r=httpx.post(url('sendMessage'),json={'chat_id':settings.telegram_chat_id,'text':str(text)[:4000]},timeout=20);r.raise_for_status();return r.json()
def get_updates(offset=None):
 p={'timeout':30};
 if offset is not None:p['offset']=offset
 r=httpx.get(url('getUpdates'),params=p,timeout=40);r.raise_for_status();return r.json()
