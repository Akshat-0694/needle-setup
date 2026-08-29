import time
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app import state

from app.transports.telegram import send_message

from app.agents.blog import scan as blog_scan
from app.agents.github import scan as github_scan


def build_blog_digest(articles):
    lines = [
        "🔥 High-signal industry reads",
        "",
    ]

    for i, article in enumerate(articles, 1):
        title = article.get(
            "title",
            "Untitled",
        )

        source = article.get(
            "source",
            "Unknown source",
        )

        summary = (
            article.get("summary")
            or "No summary available."
        )

        url = article.get(
            "url",
            "",
        )

        lines.append(
            f"{i}. {title}"
        )

        lines.append(
            f"   {source}"
        )

        lines.append(
            f"   {summary}"
        )

        lines.append(
            f"   {url}"
        )

        lines.append("")

    return "\n".join(
        lines
    ).strip()


def build_github_digest(repositories):
    trending = [
        x
        for x in repositories
        if x.get("category")
        == "trending_open_source"
    ]

    research = [
        x
        for x in repositories
        if x.get("category")
        == "research_implementation"
    ]

    lines = [
        "🐙 GitHub — High-signal projects",
        "",
    ]

    if trending:
        lines.extend([
            "🔥 Trending open source",
            "",
        ])

        for i, repo in enumerate(
            trending,
            1,
        ):
            lines.append(
                f"{i}. {repo.get('repo', 'Unknown')}"
            )

            lines.append(
                f"   ⭐ {repo.get('stars', 0):,} "
                f"| Score: {repo.get('score', 0):.3f}"
            )

            signals = (
                repo.get("technical_signals")
                or []
            )

            if signals:
                lines.append(
                    "   Signals: "
                    + ", ".join(signals)
                )

            lines.append(
                f"   {repo.get('url', '')}"
            )

            lines.append("")

    if research:
        lines.extend([
            "🧪 Research implementations",
            "",
        ])

        for i, repo in enumerate(
            research,
            1,
        ):
            lines.append(
                f"{i}. {repo.get('repo', 'Unknown')}"
            )

            lines.append(
                f"   ⭐ {repo.get('stars', 0):,} "
                f"| Score: {repo.get('score', 0):.3f}"
            )

            signals = (
                repo.get("research_signals")
                or []
            )

            if signals:
                lines.append(
                    "   Research: "
                    + ", ".join(signals)
                )

            if repo.get(
                "readme_verified"
            ):
                lines.append(
                    "   README verified: yes"
                )

            lines.append(
                f"   {repo.get('url', '')}"
            )

            lines.append("")

    return "\n".join(lines).strip()


def check_blog_notifications():
    articles = (
        state.unnotified_interesting_articles(5)
    )

    if not articles:
        return

    text = build_blog_digest(
        articles
    )

    try:
        send_message(text)

        state.mark_articles_notified(
            [
                article["url"]
                for article in articles
            ]
        )

        print(
            "[scheduler] sent blog digest: "
            f"{len(articles)} articles",
            flush=True,
        )

    except Exception as exc:
        print(
            "[scheduler] blog notification failed: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )


def check_github_notifications():
    repositories = (
        state.unnotified_github(5)
    )

    if not repositories:
        return

    text = build_github_digest(
        repositories
    )

    try:
        send_message(text)

        state.mark_github_notified(
            [
                repo["repo"]
                for repo in repositories
            ]
        )

        print(
            "[scheduler] sent GitHub digest: "
            f"{len(repositories)} repositories",
            flush=True,
        )

    except Exception as exc:
        print(
            "[scheduler] GitHub notification failed: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )


def check_reminders():
    now = datetime.now(
        ZoneInfo(
            settings.timezone
        )
    ).isoformat()

    for reminder in state.due_reminders(now):
        try:
            send_message(
                "⏰ Reminder: "
                + reminder["title"]
            )

            state.mark_sent(
                reminder["id"]
            )

        except Exception as exc:
            print(
                "[scheduler] reminder failed: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )


def refresh_sources():
    """
    Run discovery/curation pipelines.

    The pipelines themselves persist interesting results
    into the local SQLite state and Notion.
    """

    try:
        blog_result = blog_scan(20)

        print(
            "[scheduler] blog scan: "
            f"discovered={blog_result.get('discovered', 0)} "
            f"evaluated={blog_result.get('evaluated', 0)} "
            f"interesting="
            f"{len(blog_result.get('interesting', []))}",
            flush=True,
        )

    except Exception as exc:
        print(
            "[scheduler] blog scan failed: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

    try:
        github_result = github_scan(20)

        print(
            "[scheduler] GitHub scan: "
            f"count={github_result.get('count', 0)} "
            f"Notion="
            f"{github_result.get('notion_persisted', 0)}",
            flush=True,
        )

    except Exception as exc:
        print(
            "[scheduler] GitHub scan failed: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )


def main():
    print(
        "[scheduler] running in "
        f"{settings.timezone}",
        flush=True,
    )

    last_refresh = 0

    while True:
        now = time.time()

        # Discovery every 15 minutes.
        if now - last_refresh >= 900:
            refresh_sources()
            last_refresh = now

        check_reminders()
        check_blog_notifications()
        check_github_notifications()

        time.sleep(15)


if __name__ == "__main__":
    main()
