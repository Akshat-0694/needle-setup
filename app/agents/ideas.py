import needle

from app.mcp.client import call
from app.agents.util import render


@needle.tool
def list_ideas(status: str = "open") -> list[dict]:
    """List ideas. status: open, done, or all."""
    return call("ideas_list", status=status)


@needle.tool
def add_idea(title: str, details: str = ""):
    """Save a new idea."""
    return call(
        "ideas_add",
        title=title,
        details=details,
    )


@needle.tool
def update_idea(idea_id: int, title: str = "", details: str = ""):
    """Update an idea's title and/or details."""
    return call(
        "ideas_update",
        idea_id=idea_id,
        title=title or None,
        details=details or None,
    )


@needle.tool
def complete_idea(idea_id: int):
    """Mark an idea as done."""
    return call(
        "ideas_complete",
        idea_id=idea_id,
    )


@needle.tool
def remove_idea(idea_id: int):
    """Permanently remove an idea by id."""
    return call(
        "ideas_remove",
        idea_id=idea_id,
    )


def format_ideas(ideas):
    if not ideas:
        return "No ideas."

    lines = ["💡 Ideas", ""]

    for idea in ideas:
        title = idea.get("title", "Untitled")
        details = idea.get("details", "")
        status = idea.get("status", "open")
        idea_id = idea.get("id")

        line = f"• {title}"

        if status == "done":
            line = "✔ " + title

        lines.append(line)

        if details:
            lines.append(f"  {details}")

        if idea_id is not None:
            lines.append(f"  (id: {idea_id})")

    return "\n".join(lines)


def list_text(status="open"):
    return format_ideas(
        call("ideas_list", status=status)
    )


def remove(idea_id):
    """Deterministic removal by id (for /remove_idea <id>)."""
    return call("ideas_remove", idea_id=idea_id)


def complete(idea_id):
    """Deterministic complete-by-id (for /idea done <id>)."""
    return call("ideas_complete", idea_id=idea_id)


def run(prompt):
    agent = needle.Needle(
        tools=[
            list_ideas,
            add_idea,
            update_idea,
            complete_idea,
            remove_idea,
        ],
        system=(
            "You are Ideas Needle. Capture and organize the user's ideas. "
            "Use add_idea to save a new idea, list_ideas to show them, "
            "update_idea to edit, complete_idea to mark one done, and "
            "remove_idea to delete one. Never invent idea ids."
        ),
    )

    return render(agent.run(prompt))
