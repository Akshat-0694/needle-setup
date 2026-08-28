import asyncio
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from core.protocol import Task, Event
from hub.bus import Bus
from hub.state import State

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DB_PATH = os.getenv("DB_PATH", "/app/data/needle.db")

bus = Bus(REDIS_URL)
state = State(DB_PATH)

NEEDLES = {
    "watcher": {"description": "Checks configured URLs for changes/status."},
    "researcher": {"description": "Turns a research request into a concise answer."},
}

class TaskRequest(BaseModel):
    needle: str
    action: str = "run"
    payload: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Needle Hub", version="0.1.0", lifespan=lifespan)

@app.get("/health")
async def health():
    try:
        await bus.r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    return {"ok": redis_ok, "needles": NEEDLES}

@app.get("/needles")
async def needles():
    return NEEDLES

@app.post("/tasks")
async def create_task(req: TaskRequest):
    if req.needle not in NEEDLES:
        raise HTTPException(404, f"Unknown needle: {req.needle}")
    task = Task(
        id=str(uuid.uuid4()),
        needle=req.needle,
        action=req.action,
        payload=req.payload,
    )
    await bus.enqueue(task)
    state.event("task.created", "hub", task.model_dump(), task.created_at)
    return task

@app.post("/events")
async def create_event(event: Event):
    state.event(event.type, event.source, event.payload, event.timestamp)
    await bus.publish(event)
    return {"ok": True}

@app.get("/events")
async def events(limit: int = 50):
    return state.recent_events(min(max(limit, 1), 200))
