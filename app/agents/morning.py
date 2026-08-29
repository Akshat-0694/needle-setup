"""Morning Briefing Needle.

Gathers the day's data deterministically (tasks, Notion calendar/ideas,
industry reads, GitHub, network opportunities) and formats a compact
briefing. Deterministic gathering is intentional: the local needle model
is reliable for single tool actions but not for multi-tool composition,
and the morning brief is a scheduled deliverable that must not depend on
model whim.
"""

from app.agents.github import (
    trending_projects,
    research_implementations,
)
from app.mcp.client import call


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _items(value):
    if isinstance(value, dict) and value.get("error"):
        return [value]

    if not isinstance(value, list):
        return []

    return value


def _format_items(items, show_summary=False):
    lines = []

    for item in _items(items):
        if isinstance(item, dict):
            if item.get("error"):
                lines.append(f"⚠️ {item['error']}")
                continue

            title = (
                item.get("title")
                or item.get("repo")
                or item.get("name")
                or item.get("model_id")
            )

            if not title:
                continue

            when = ""

            if item.get("event_date"):
                when = f"  ({item['event_date']}"

                if item.get("event_time"):
                    when += f" {item['event_time']}"

                when += ")"

            line = f"• {title}{when}"

            if show_summary and item.get("summary"):
                line += f" — {item['summary']}"

            lines.append(line)

            details = item.get("details")

            if details:
                lines.append(f"  {details}")

            url = item.get("url")

            if url:
                lines.append(f"  {url}")
        else:
            lines.append(f"• {item}")

    return lines


def _gather():
    return {
        "tasks": _safe(call, "tasks_list", status="open"),
        "blogs": _safe(call, "blog_interesting", limit=5),
        "people": _safe(call, "linkedin_interesting", limit=5),
        "trending": _safe(trending_projects, 5),
        "research": _safe(research_implementations, 5),
        "calendar": _safe(call, "calendar_list", days=7),
        "ideas": _safe(call, "ideas_list", status="open"),
    }


def run(prompt="Prepare my morning briefing for today."):
    data = _gather()

    sections = []

    # --- Tasks ---
    task_items = _items(data["tasks"])

    if task_items:
        lines = ["📋 Tasks", ""]

        for item in task_items:
            if isinstance(item, dict):
                if item.get("error"):
                    lines.append(f"⚠️ {item['error']}")
                    continue

                title = item.get("title")
                due = item.get("due_at")

                if not title:
                    continue

                line = f"• {title}"

                if due:
                    line += f"  (due: {due})"

                lines.append(line)

        sections.append("\n".join(lines))

    # --- Calendar events ---
    calendar_lines = _format_items(data["calendar"])

    if calendar_lines:
        sections.append(
            "📅 Calendar (next 7 days)\n\n" + "\n".join(calendar_lines)
        )

    # --- Ideas ---
    idea_lines = _format_items(data["ideas"])

    if idea_lines:
        sections.append(
            "💡 Ideas\n\n" + "\n".join(idea_lines)
        )

    # --- Industry reads ---
    blog_lines = _format_items(data["blogs"], show_summary=True)

    if blog_lines:
        sections.append(
            "🔥 High-signal industry reads\n\n" + "\n".join(blog_lines)
        )

    # --- Research implementations ---
    research_lines = _format_items(data["research"])

    if research_lines:
        sections.append(
            "🧪 Research implementations\n\n" + "\n".join(research_lines)
        )

    # --- Trending open source ---
    trending_lines = _format_items(data["trending"])

    if trending_lines:
        sections.append(
            "🚀 Trending open-source projects\n\n" + "\n".join(trending_lines)
        )

    # --- Network opportunities ---
    people_lines = _format_items(data["people"])

    if people_lines:
        sections.append(
            "👤 Network opportunities\n\n" + "\n".join(people_lines)
        )

    if not sections:
        sections.append(
            "No data available for the morning briefing yet. "
            "Set up sources (RSS feeds in data/sources.json, GitHub "
            "token, Notion token) and tasks to populate it."
        )

    return "🌅 Morning Briefing\n\n" + "\n\n".join(sections)
