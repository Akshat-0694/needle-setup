import needle
from datetime import datetime
from zoneinfo import ZoneInfo
from app.config import settings
from app import state

@needle.tool
def create_task(
    title: str,
    notes: str = "",
    due_at: str = "",
):
    """Create a new personal task.

    Args:
        title: The task to add. Extract the user's requested task from natural language.
        notes: Optional additional details about the task.
        due_at: Optional ISO-8601 date and time for when the task is due. Leave empty if no date/time was given.
    """
    task_id = state.create_task(title=title)
    task = state.get_task(task_id)

    state.add_event("task.created", "task-needle", task)
    return task

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
