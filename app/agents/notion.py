import needle

from app.integrations import notion
from app.integrations.needle_notion import (
    persist_github,
    persist_blog,
    persist_research,
)


@needle.tool
def notion_search(query: str):
    """Search the user's accessible Notion workspace."""
    return notion.search(query)


@needle.tool
def notion_read_page(page_id: str):
    """Read a Notion page as Markdown."""
    return notion.get_page_markdown(page_id)


@needle.tool
def notion_create_page(
    parent_page_id: str,
    title: str,
    markdown: str = "",
):
    """Create a new Notion page."""
    return notion.create_page(
        parent_page_id,
        title,
        markdown,
    )


@needle.tool
def notion_update_page(
    page_id: str,
    markdown: str,
):
    """Update a Notion page."""
    return notion.update_page_markdown(
        page_id,
        markdown,
    )


@needle.tool
def notion_save_github(item: dict):
    """Save a GitHub project into Needle Daily."""
    return persist_github(item)


@needle.tool
def notion_save_blog(item: dict):
    """Save an industry article into Needle Daily."""
    return persist_blog(item)


@needle.tool
def notion_save_research(item: dict):
    """Save a research item into Needle Daily."""
    return persist_research(item)


def tools():
    return [
        notion_search,
        notion_read_page,
        notion_create_page,
        notion_update_page,
        notion_save_github,
        notion_save_blog,
        notion_save_research,
    ]
