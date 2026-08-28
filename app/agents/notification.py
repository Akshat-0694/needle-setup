import needle

@needle.tool
def format_task_reminder(title: str, notes: str=""):
    """Format a reminder. Does not send it."""
    return f"⏰ Reminder: {title}" + (f"\n{notes}" if notes else "")

@needle.tool
def format_task_created(title: str):
    """Format task-created notification. Does not send it."""
    return f"✅ Added task: {title}"

def run(event):
    agent=needle.Needle(tools=[format_task_reminder,format_task_created],
        system="You are Notification Needle. Format concise notifications. Never claim you sent anything.")
    return agent.run(f"Create a notification for this event:\n{event}",max_steps=3,max_new_tokens=128)
