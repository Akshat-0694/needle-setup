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


# ============================================================
# ARXIV DISCOVERY
# V2 additive capability.
# ============================================================

@mcp.tool()
def arxiv_discover(
    query: str = "cat:cs.LG OR cat:cs.AI OR cat:cs.CL OR cat:cs.DC",
    limit: int = 20,
    days: int = 7,
):
    """
    Discover recent arXiv papers.

    This capability performs deterministic discovery only.
    It does not decide whether a paper is interesting.
    """

    import re
    import urllib.parse
    import urllib.request
    import xml.etree.ElementTree as ET
    from datetime import datetime, timedelta, timezone

    limit = max(1, min(int(limit), 100))
    days = max(1, min(int(days), 90))

    params = urllib.parse.urlencode({
        "search_query": query,
        "start": 0,
        "max_results": limit,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })

    request = urllib.request.Request(
        "https://export.arxiv.org/api/query?" + params,
        headers={
            "User-Agent": "NeedleDaily/2.0"
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
    }

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=days)
    )

    papers = []

    for entry in root.findall(
        "atom:entry",
        ns,
    ):
        raw_id = (
            entry.findtext(
                "atom:id",
                "",
                ns,
            )
            .strip()
        )

        match = re.search(
            r"arxiv\.org/(?:abs/)?([^?#]+)",
            raw_id,
        )

        if not match:
            continue

        arxiv_id = match.group(1).strip()

        # Remove version suffix for stable identity.
        arxiv_id = re.sub(
            r"v\d+$",
            "",
            arxiv_id,
        )

        published = (
            entry.findtext(
                "atom:published",
                "",
                ns,
            )
            .strip()
        )

        updated = (
            entry.findtext(
                "atom:updated",
                "",
                ns,
            )
            .strip()
        )

        try:
            published_dt = datetime.fromisoformat(
                published.replace(
                    "Z",
                    "+00:00",
                )
            )
        except Exception:
            published_dt = None

        if (
            published_dt
            and published_dt < cutoff
        ):
            continue

        title = " ".join(
            entry.findtext(
                "atom:title",
                "",
                ns,
            ).split()
        )

        abstract = " ".join(
            entry.findtext(
                "atom:summary",
                "",
                ns,
            ).split()
        )

        authors = [
            x.findtext(
                "atom:name",
                "",
                ns,
            ).strip()
            for x in entry.findall(
                "atom:author",
                ns,
            )
        ]

        categories = [
            x.attrib.get(
                "term",
                "",
            )
            for x in entry.findall(
                "atom:category",
                ns,
            )
            if x.attrib.get("term")
        ]

        papers.append({
            "arxiv_id": arxiv_id,
            "url": (
                "https://arxiv.org/abs/"
                + arxiv_id
            ),
            "title": title,
            "authors": ", ".join(authors),
            "abstract": abstract,
            "published_at": published,
            "updated_at": updated,
            "categories": ", ".join(categories),
            "source": "arxiv",
        })

    return papers


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=9000,
        stateless_http=True,
        json_response=True,
    )
