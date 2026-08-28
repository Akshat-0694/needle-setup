import httpx
from app.config import settings
API="https://api.telegram.org"
async def send_message(text):
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
    async with httpx.AsyncClient(timeout=20) as c:
        r=await c.post(f"{API}/bot{settings.telegram_bot_token}/sendMessage",
                       json={"chat_id":settings.telegram_chat_id,"text":str(text)[:4096]})
        r.raise_for_status(); return r.json()
async def get_updates(offset=None):
    if not settings.telegram_bot_token: raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    params={"timeout":30}
    if offset is not None: params["offset"]=offset
    async with httpx.AsyncClient(timeout=40) as c:
        r=await c.get(f"{API}/bot{settings.telegram_bot_token}/getUpdates",params=params)
        r.raise_for_status(); return r.json()
