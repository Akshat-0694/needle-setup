from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from app import state
from app.agents import task as task_agent
from app.config import settings
app=FastAPI(title="Needle Daily V1")
class Message(BaseModel): text:str
class TaskRequest(BaseModel): title:str; notes:str=""; due_at:str|None=None
@app.get("/health")
def health():
    return {"ok":True,"needle":"cactus-needle-2.0.10","telegram_configured":bool(settings.telegram_bot_token and settings.telegram_chat_id)}
@app.get("/tasks")
def tasks(): return state.list_tasks()
@app.get("/events")
def events(): return state.recent_events()
@app.post("/tasks")
def create(req:TaskRequest):
    tid=state.create_task(req.title,req.notes,req.due_at); return state.get_task(tid)
@app.post("/message")
def message(req:Message):
    try: return {"result":task_agent.run(req.text)}
    except Exception as e: raise HTTPException(500,str(e))
