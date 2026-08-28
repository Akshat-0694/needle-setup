from app.agents import task as task_agent
def handle_text(text):
    t=text.strip()
    if t.lower()=="/tasks": return task_agent.run("List my open tasks.")
    if t.lower().startswith("/done "): return task_agent.run(f"Mark task {t[6:].strip()} as completed.")
    return task_agent.run(t)
