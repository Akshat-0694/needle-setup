import needle
from datetime import datetime
from zoneinfo import ZoneInfo
from app.config import settings
from app import state

@needle.tool
def create_task(title: str, notes: str="", due_at: str=""):
    """Create a personal task. due_at is ISO-8601 with timezone, or empty."""
    tid=state.create_task(title,notes,due_at or None); task=state.get_task(tid)
    state.add_event("task.created","task-needle",task); return task

@needle.tool
def list_open_tasks():
    """List all open personal tasks."""
    return state.list_tasks("open")

@needle.tool
def complete_task(task_id: int):
    """Mark a task completed."""
    task=state.complete_task(task_id)
    if task: state.add_event("task.completed","task-needle",task)
    return task or {"error":"Task not found"}

@needle.tool
def get_current_time():
    """Return current time in configured user timezone."""
    return datetime.now(ZoneInfo(settings.timezone)).isoformat()

def run(prompt):
    agent=needle.Needle(tools=[create_task,list_open_tasks,complete_task,get_current_time],
        system=("You are Task Needle. Manage personal tasks using tools. "
                "Never invent task state. Create/complete tasks only through tools. "
                "If a date/time is ambiguous, ask for clarification."))
    return agent.run(prompt,max_steps=6,max_new_tokens=256)
