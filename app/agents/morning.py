from datetime import datetime
from zoneinfo import ZoneInfo
import needle
from app.config import settings

@needle.tool
def local_time():
    """Return the current time in the user's configured timezone."""
    return datetime.now(ZoneInfo(settings.timezone)).isoformat()

@needle.tool
def daily_system_status():
    """Return a small read-only system status summary."""
    from app.agents.system import system_info
    return system_info()

def run():
    agent = needle.Needle(
        tools=[local_time, daily_system_status],
        system=(
            "You are the user's morning briefing Needle. "
            "Use the tools to create a short actionable briefing. "
            "Do not invent calendar, email, GitHub or task information."
        ),
    )
    return agent.run(
        "Prepare my morning brief using the available information.",
        max_steps=4,
        max_new_tokens=256,
    )
