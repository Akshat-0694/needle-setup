import needle
from datetime import datetime
from zoneinfo import ZoneInfo
from app.config import settings
from app.mcp.client import call
@needle.tool
def create_task(title:str): """Create a task.""";return call('tasks_create',title=title)
@needle.tool
def list_open_tasks(): """List open tasks.""";return call('tasks_list',status='open')
@needle.tool
def complete_task(task_id:int): """Complete a task.""";return call('tasks_complete',task_id=task_id)
@needle.tool
def get_current_time(): """Get current configured time.""";return datetime.now(ZoneInfo(settings.timezone)).isoformat()
@needle.tool
def schedule_reminder(task_id:int,remind_at:str): """Schedule a reminder.""";return call('reminders_schedule',task_id=task_id,remind_at=remind_at)
def run(prompt):
 a=needle.Needle(tools=[create_task,list_open_tasks,complete_task,get_current_time,schedule_reminder],system='You are Task Needle. Manage tasks and reminders using tools. Never invent IDs. Resolve relative times using get_current_time.');return a.complete(prompt)
