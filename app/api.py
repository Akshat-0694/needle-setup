from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import state
from app.registry import AGENTS, run

app = FastAPI(title="Needle Daily", version="0.1.0")

class TaskRequest(BaseModel):
    agent: str
    prompt: str

@app.get("/health")
def health():
    return {"ok": True, "agents": sorted(AGENTS)}

@app.get("/agents")
def agents():
    return {"agents": sorted(AGENTS)}

@app.get("/tasks")
def tasks():
    return state.list_tasks()

@app.get("/events")
def events():
    return state.recent_events()

@app.post("/tasks")
def create(req: TaskRequest):
    if req.agent not in AGENTS:
        raise HTTPException(404, f"Unknown agent: {req.agent}")

    task_id = state.create_task(req.agent, req.prompt)
    try:
        result = run(req.agent, req.prompt)
        state.update_task(task_id, "completed", result)
        state.event("task.completed", req.agent, {"task_id": task_id, "result": result})
        return {"id": task_id, "status": "completed", "result": result}
    except Exception as exc:
        state.update_task(task_id, "failed", {"error": str(exc)})
        state.event("task.failed", req.agent, {"task_id": task_id, "error": str(exc)})
        raise HTTPException(500, str(exc))
