import asyncio
from app.telegram import get_updates,send_message
from app.hub import handle_text
from app import state
from app.config import settings

async def main():
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        print("[telegram] not configured; sleeping",flush=True)
        while True: await asyncio.sleep(3600)
    offset=None
    print("[telegram] polling",flush=True)
    while True:
        try:
            data=await get_updates(offset)
            for u in data.get("result",[]):
                offset=u["update_id"]+1
                m=u.get("message") or {}; chat=m.get("chat") or {}; text=m.get("text")
                if not text or str(chat.get("id"))!=str(settings.telegram_chat_id): continue
                try:
                    result=handle_text(text); reply=None
                    if isinstance(result,dict):
                        for x in result.get("results",[]):
                            reply=x.get("result") or x.get("text")
                            if reply: break
                    await send_message(reply or str(result))
                    state.add_event("telegram.message","telegram",{"text":text})
                except Exception as e: await send_message(f"❌ Error: {e}")
        except Exception as e:
            print(f"[telegram] {e}",flush=True); await asyncio.sleep(5)
if __name__=="__main__": asyncio.run(main())
