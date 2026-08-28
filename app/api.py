from fastapi import FastAPI
from pydantic import BaseModel
from app.agents.router import route
from app import state
from app.config import settings
app=FastAPI(title='Needle Daily V2',version='0.2.0')
class Message(BaseModel):text:str
@app.get('/health')
def health():return {'ok':True,'needle':'cactus-needle-2.0.10','telegram_configured':bool(settings.telegram_bot_token and settings.telegram_chat_id),'mcp':'http://mcp:9000/mcp'}
@app.post('/message')
def message(x:Message):return {'result':route(x.text)}
@app.get('/tasks')
def tasks():return state.list_tasks()
@app.get('/blogs')
def blogs():return state.interesting_articles()
@app.get('/people')
def people():return state.interesting_people()
