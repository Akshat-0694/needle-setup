import time
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app import state
from app.transports.telegram import send_message


def build_blog_digest(articles):
    lines = ["🔥 High-signal industry reads", ""]

    for i, article in enumerate(articles, 1):
        title = article.get("title", "Untitled")
        source = article.get("source", "Unknown source")
        summary = article.get("summary") or "No summary available."
        url = article.get("url", "")

        lines.append(f"{i}. {title}")
        lines.append(f"   {source}")
        lines.append(f"   {summary}")
        lines.append(f"   {url}")
        lines.append("")

    return "\n".join(lines).strip()


def build_github_digest(repositories):
    trending = [
        repo
        for repo in repositories
        if repo.get("category") == "trending_open_source"
    ]

    research = [
        repo
        for repo in repositories
        if repo.get("category") == "research_implementation"
    ]

    lines = ["🐙 GitHub — High-signal projects", ""]

    if trending:
        lines.append("🔥 Trending open source")
        lines.append("")

        for i, repo in enumerate(trending, 1):
            name = repo.get("repo", "Unknown repository")
            stars = repo.get("stars", 0)
            score = repo.get("score", 0.0)
            signals = repo.get("technical_signals") or []
            url = repo.get("url", "")

            lines.append(f"{i}. {name}")
            lines.append(f"   ⭐ {stars:,} | Score: {score:.3f}")

            if signals:
                lines.append(
                    "   Signals: " + ", ".join(signals)
                )

            if url:
                lines.append(f"   {url}")

            lines.append("")

    if research:
        lines.append("🧪 Research implementations")
        lines.append("")

        for i, repo in enumerate(research, 1):
            name = repo.get("repo", "Unknown repository")
            stars = repo.get("stars", 0)
            score = repo.get("score", 0.0)
            signals = repo.get("research_signals") or []
            url = repo.get("url", "")
            readme_verified = repo.get(
                "readme_verified",
                False,
            )

            lines.append(f"{i}. {name}")
            lines.append(f"   ⭐ {stars:,} | Score: {score:.3f}")

            if signals:
                lines.append(
                    "   Research: " + ", ".join(signals)
                )

            lines.append(
                "   README verified: "
                + ("yes" if readme_verified else "no")
            )

            if url:
                lines.append(f"   {url}")

            lines.append("")

    return "\n".join(lines).strip()


def check_blog_notifications():
    articles = state.unnotified_interesting_articles(5)

    if not articles:
        return

    text = build_blog_digest(articles)

    try:
        send_message(text)

        state.mark_articles_notified(
            [article["url"] for article in articles]
        )

        print(
            f"[scheduler] sent blog digest: "
            f"{len(articles)} articles",
            flush=True,
        )

    except Exception as exc:
        print(
            f"[scheduler] blog notification failed: {exc}",
            flush=True,
        )


def check_github_notifications():
    repositories = state.unnotified_github(10)

    if not repositories:
        return

    text = build_github_digest(repositories)

    try:
        send_message(text)

        state.mark_github_notified(
            [repo["repo"] for repo in repositories]
        )

        print(
            f"[scheduler] sent GitHub digest: "
            f"{len(repositories)} repositories",
            flush=True,
        )

    except Exception as exc:
        print(
            f"[scheduler] GitHub notification failed: {exc}",
            flush=True,
        )


def check_reminders():
    now = datetime.now(
        ZoneInfo(settings.timezone)
    ).isoformat()

    for reminder in state.due_reminders(now):
        try:
            send_message(
                "⏰ Reminder: " + reminder["title"]
            )

            state.mark_sent(reminder["id"])

        except Exception as exc:
            print(
                f"[scheduler] reminder failed: {exc}",
                flush=True,
            )


def main():
    print(
        f"[scheduler] running in {settings.timezone}",
        flush=True,
    )

    while True:
        check_reminders()
        check_blog_notifications()
        check_github_notifications()
        time.sleep(15)


if __name__ == "__main__":
    main()
