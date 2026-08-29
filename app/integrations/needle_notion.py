from app.integrations import notion


NEEDLE_DAILY_DATA_SOURCE = (
    "3cbddaaf-2318-808d-8a01-000bf855c0b4"
)


def _title_for(item, kind):
    if kind == "github":
        return f"🐙 GitHub — {item.get('repo', 'Unknown repository')}"

    if kind == "blog":
        return f"📰 Blog — {item.get('title', 'Untitled')}"

    if kind == "research":
        return f"🔬 Research — {item.get('title', 'Untitled')}"

    return f"Needle — {item.get('title', 'Untitled')}"


def _markdown_for(item, kind):
    if kind == "github":
        signals = item.get("technical_signals") or []
        research = item.get("research_signals") or []

        return f"""# GitHub Project

**Repository:** `{item.get('repo', '')}`

**Category:** `{item.get('category', '')}`

**Score:** {item.get('score', 0)}

**Stars:** {item.get('stars', 0)}

**Forks:** {item.get('forks', 0)}

**Language:** {item.get('language') or 'Unknown'}

## Technical signals

{", ".join(signals) if signals else "None"}

## Research signals

{", ".join(research) if research else "None"}

## URL

{item.get('url', '')}

## Last updated

{item.get('updated_at') or 'Unknown'}
"""

    if kind == "blog":
        return f"""# Industry Article

**Source:** {item.get('source', 'Unknown')}

**Score:** {item.get('score', 0)}

**Interesting:** {bool(item.get('interesting'))}

## Summary

{item.get('summary') or 'No summary available.'}

## URL

{item.get('url', '')}

## Published

{item.get('published_at') or 'Unknown'}
"""

    return f"""# Needle Record

**Score:** {item.get('score', 0)}

## Summary

{item.get('summary') or item.get('description') or 'No summary available.'}

## URL

{item.get('url', '')}
"""


def _find_existing(url):
    if not url:
        return None

    result = notion.search(url, page_size=20)

    if not isinstance(result, dict):
        return None

    for item in result.get("results", []):
        if item.get("object") == "page":
            return item

    return None


def persist(item, kind):
    """
    Persist one interesting GitHub/blog/research item.

    Uses the canonical URL as the idempotency key.
    """
    url = item.get("url")

    if not url:
        return {
            "ok": False,
            "created": False,
            "updated": False,
            "reason": "missing URL",
        }

    title = _title_for(item, kind)
    markdown = _markdown_for(item, kind)

    existing = _find_existing(url)

    if existing:
        page_id = existing.get("id")

        if not page_id:
            return {
                "ok": False,
                "created": False,
                "updated": False,
                "reason": "existing page has no ID",
            }

        notion.update_page_markdown(
            page_id,
            markdown,
        )

        return {
            "ok": True,
            "created": False,
            "updated": True,
            "page_id": page_id,
            "url": url,
        }

    result = notion.create_page(
        NEEDLE_DAILY_DATA_SOURCE,
        title,
        markdown,
    )

    page_id = None

    if isinstance(result, dict):
        page_id = result.get("id")

    return {
        "ok": True,
        "created": True,
        "updated": False,
        "page_id": page_id,
        "url": url,
    }


def persist_github(item):
    return persist(item, "github")


def persist_blog(item):
    return persist(item, "blog")


def persist_research(item):
    return persist(item, "research")
