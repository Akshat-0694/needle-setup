from app.agents.notion import notion_search, notion_read_page, notion_create_page, notion_update_page
import needle

from app.mcp.client import call
from app.agents.github import (
    trending_projects,
    research_implementations as github_research_implementations,
)


@needle.tool
def tasks():
    """Get open tasks."""
    return call("tasks_list", status="open")


@needle.tool
def blogs():
    """Get interesting technical blog posts."""
    return call("blog_interesting", limit=10)


@needle.tool
def people():
    """Get interesting network candidates."""
    return call("opportunity_interesting", limit=10)


@needle.tool
def trending_open_source():
    """Get interesting trending open-source projects from GitHub."""
    return trending_projects(10)


@needle.tool
def research_implementations():
    """Get interesting research-paper implementations from GitHub."""
    return github_research_implementations(10)


def run(prompt="Prepare my morning briefing."):
    agent = needle.Needle(
        tools=[
            tasks,
            blogs,
            people,
            trending_open_source,
            research_implementations,
        ],
        system="""
You are Morning Briefing Needle.

Produce a compact, technically useful morning briefing.

Organize the briefing into these sections when data is available:

🔥 High-signal industry reads
🧪 Interesting research implementations
🚀 Trending open-source projects
📋 Tasks
👤 Network opportunities

For technical reading:
- Give a concise 2-4 sentence summary.
- Explain why the item is interesting when useful.
- Never reproduce raw HTML, Markdown boilerplate, or extraction errors.

For research implementations:
- Give the repository name.
- Explain what research/paper it implements.
- Include stars when available.
- Include the GitHub URL.

For trending open-source projects:
- Give the repository name.
- Give a concise description.
- Include stars.
- Include relevant technical signals.
- Include the GitHub URL.

Do not invent information that is not returned by the tools.

Keep the briefing compact and prioritize the highest-signal items.
""",
    )

    return agent.complete(prompt)
