import json
from datetime import datetime
from pathlib import Path

import feedparser
import httpx

from mcp.server.mcpserver import MCPServer

from app import state
from app.config import settings


mcp = MCPServer("needle-daily-v2")


@mcp.tool()
def tasks_create(
    title: str,
    notes: str = "",
    due_at: str | None = None,
) -> dict:
    """Create a personal task."""
    task_id = state.create_task(title, notes, due_at)
    return state.get_task(task_id)


@mcp.tool()
def tasks_list(status: str = "open") -> list[dict]:
    """List personal tasks."""
    return state.list_tasks(status)


@mcp.tool()
def tasks_complete(task_id: int) -> dict:
    """Complete a personal task."""
    task = state.complete_task(task_id)

    if task is None:
        return {"error": "Task not found"}

    return task


@mcp.tool()
def reminders_schedule(
    task_id: int,
    remind_at: str,
) -> dict:
    """Schedule an ISO-8601 reminder for a task."""

    try:
        parsed = datetime.fromisoformat(remind_at)
    except ValueError:
        return {
            "error": "Invalid ISO-8601 timestamp."
        }

    if parsed.tzinfo is None:
        return {
            "error": "remind_at must include a timezone offset."
        }

    if not state.get_task(task_id):
        return {
            "error": "Task not found"
        }

    reminder_id = state.add_reminder(
        task_id,
        parsed.isoformat(),
    )

    return {
        "id": reminder_id,
        "task_id": task_id,
        "remind_at": parsed.isoformat(),
    }


@mcp.tool()
def blog_fetch_new(
    limit_per_source: int = 20,
) -> list[dict]:
    """Fetch recent posts from configured RSS/Atom feeds."""

    output = []

    sources_path = Path("/app/data/sources.json")

    if not sources_path.exists():
        return []

    sources = json.loads(
        sources_path.read_text()
    )

    for source in sources:

        feed = feedparser.parse(
            source["feed"]
        )

        for entry in feed.entries[:limit_per_source]:

            if not entry.get("link"):
                continue

            article = {
                "source": source["name"],
                "url": entry.link,
                "title": entry.get("title", ""),
                "published_at": entry.get(
                    "published",
                    "",
                ),
                "description": entry.get(
                    "summary",
                    "",
                ),
            }

            state.upsert_article(article)

            output.append(article)

    return output


@mcp.tool()
def blog_candidates(
    limit: int = 50,
) -> list[dict]:
    """Get unscored blog candidates."""

    return state.candidates(limit)


@mcp.tool()
def blog_save_score(
    url: str,
    score: float,
    interesting: bool,
    summary: str,
) -> dict:
    """Save an article relevance score and summary."""

    score = max(
        0.0,
        min(1.0, score),
    )

    state.score_article(
        url,
        score,
        interesting,
        summary,
    )

    return {"ok": True}


@mcp.tool()
def blog_interesting(
    limit: int = 20,
) -> list[dict]:
    """Get curated interesting articles."""

    return state.interesting_articles(limit)


@mcp.tool()
def research_fetch_url(
    url: str,
) -> dict:
    """Fetch readable public web content."""

    # Jina Reader converts public webpages into readable
    # text/Markdown instead of returning raw HTML.
    target = "https://r.jina.ai/" + url

    headers = {
        "Accept": "text/plain",
    }

    if settings.jina_api_key:
        headers["Authorization"] = (
            "Bearer " + settings.jina_api_key
        )

    response = httpx.get(
        target,
        headers=headers,
        timeout=45,
        follow_redirects=True,
    )

    response.raise_for_status()

    return {
        "url": url,
        "content": response.text[:50000],
    }


@mcp.tool()
def opportunity_import_profiles(
    profiles: list[dict],
) -> dict:
    """Import approved/user-provided network profiles.

    This tool does not scrape LinkedIn.
    """

    imported = 0

    for profile in profiles:

        if (
            profile.get("profile_url")
            and profile.get("name")
        ):
            state.import_person(profile)
            imported += 1

    return {
        "imported": imported
    }


@mcp.tool()
def opportunity_candidates(
    limit: int = 50,
) -> list[dict]:
    """Get unscored network profiles."""

    return state.people_candidates(limit)


@mcp.tool()
def opportunity_save_score(
    profile_url: str,
    score: float,
    interesting: bool,
    reason: str,
    conversation_hook: str,
) -> dict:
    """Save network opportunity score."""

    score = max(
        0.0,
        min(1.0, score),
    )

    state.score_person(
        profile_url,
        score,
        interesting,
        reason,
        conversation_hook,
    )

    return {"ok": True}


@mcp.tool()
def opportunity_interesting(
    limit: int = 20,
) -> list[dict]:
    """Get high-value network candidates."""

    return state.interesting_people(limit)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=9000,
        stateless_http=True,
        json_response=True,
    )
