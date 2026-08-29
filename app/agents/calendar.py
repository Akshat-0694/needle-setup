import re
import needle
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import settings
from app.mcp.client import call
from app.agents.util import render


def _resolve_event_date(value):
    """
    Deterministically resolve relative dates ("tomorrow", "next monday",
    "in 3 days", …) to YYYY-MM-DD, regardless of what the model emitted.
    """
    if not value:
        return value

    text = str(value).strip().lower()
    today = datetime.now(ZoneInfo(settings.timezone)).date()

    day = None

    if "day after tomorrow" in text:
        day = today + timedelta(days=2)
    elif "tomorrow" in text:
        day = today + timedelta(days=1)
    elif "today" in text:
        day = today
    else:
        weekdays = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }

        for name, idx in weekdays.items():
            if name in text:
                delta = (idx - today.weekday() + 7) % 7

                if delta == 0:
                    delta = 7

                day = today + timedelta(days=delta)
                break

    if day is None:
        match = re.search(r"in (\d+) days?", text)

        if match:
            day = today + timedelta(days=int(match.group(1)))

    if day is not None:
        return day.isoformat()

    return value


def _extract_time(value):
    match = re.search(
        r"(?:at|@)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm|noon|midnight)?)",
        (value or "").lower(),
    )

    return match.group(1) if match else ""


@needle.tool
def get_current_date():
    """Get today's date as YYYY-MM-DD."""
    return datetime.now(
        ZoneInfo(settings.timezone)
    ).strftime("%Y-%m-%d")


@needle.tool
def list_events(days: int = 7) -> list[dict]:
    """List calendar events from today forward for N days."""
    return call("calendar_list", days=days)


@needle.tool
def add_event(
    title: str,
    event_date: str,
    event_time: str = "",
    details: str = "",
):
    """Add a calendar event. Relative dates like 'tomorrow' are resolved."""
    resolved_date = _resolve_event_date(event_date)

    if not event_time:
        event_time = _extract_time(event_date)

    return call(
        "calendar_add",
        title=title,
        event_date=resolved_date,
        event_time=event_time,
        details=details,
    )


@needle.tool
def remove_event(event_id: int):
    """Remove a calendar event by id."""
    return call(
        "calendar_remove",
        event_id=event_id,
    )


def format_events(events):
    if not events:
        return "No calendar events."

    lines = ["📅 Calendar", ""]

    for event in events:
        title = event.get("title", "Untitled")
        date = event.get("event_date", "")
        time = event.get("event_time", "")
        details = event.get("details", "")
        event_id = event.get("id")

        when = date

        if time:
            when += f" {time}"

        line = f"• {when}  {title}"

        if details:
            line += f"  — {details}"

        lines.append(line)

        if event_id is not None:
            lines.append(f"  (id: {event_id})")

    return "\n".join(lines)


def upcoming(days=7):
    return format_events(
        call("calendar_list", days=days)
    )


def remove(event_id):
    """Deterministic removal by id (for /remove_event <id>)."""
    return call("calendar_remove", event_id=event_id)


def run(prompt):
    agent = needle.Needle(
        tools=[
            get_current_date,
            list_events,
            add_event,
            remove_event,
        ],
        system=(
            "You are Calendar Needle. Manage the user's calendar. "
            "Use get_current_date to learn today's date, list_events to "
            "show events, add_event to schedule new ones (resolve relative "
            "dates like 'tomorrow' into YYYY-MM-DD using get_current_date), "
            "and remove_event to cancel one. Never invent event ids."
        ),
    )

    return render(agent.run(prompt))
