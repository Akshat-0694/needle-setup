import time
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app import state

from app.transports.telegram import send_message

from app.agents.blog import scan as blog_scan
from app.agents.github import scan as github_scan
from app.agents import research
from app.agents import kaggle as kaggle_agent
from app.agents import opportunity as opportunity_agent
from app.agents import morning as morning_agent


def build_arxiv_digest(papers):
    """
    Build a deterministic Telegram digest for curated arXiv papers.

    This function only formats already-curated database records.
    It does not perform discovery or classification.
    """

    if not papers:
        return "No new interesting arXiv papers."

    lines = [
        "📚 Research — Interesting arXiv papers",
        "",
    ]

    for i, paper in enumerate(papers, 1):
        title = paper.get(
            "title",
            "Untitled paper",
        )

        score = paper.get(
            "score",
            0,
        )

        area = (
            paper.get("technical_area")
            or "Unknown"
        )

        reason = (
            paper.get("reason")
            or "No reason available."
        )

        url = paper.get(
            "url",
            "",
        )

        arxiv_id = paper.get(
            "arxiv_id",
            "",
        )

        lines.append(
            f"{i}. {title}"
        )

        lines.append(
            f"   Score: {float(score):.3f}"
        )

        lines.append(
            f"   Area: {area}"
        )

        lines.append(
            f"   Why: {reason}"
        )

        if arxiv_id:
            lines.append(
                f"   arXiv: {arxiv_id}"
            )

        if url:
            lines.append(
                f"   {url}"
            )

        lines.append("")

    return "\n".join(lines).strip()


def notify_arxiv_papers(limit=10):
    """
    Deliver curated but unnotified arXiv papers to Telegram.

    Database state is authoritative:

        interesting=1 AND notified=0
            -> send
            -> mark notified

    A paper is marked notified only after Telegram succeeds.
    """

    papers = state.unnotified_research_papers(
        limit
    )

    if not papers:
        return {
            "found": 0,
            "sent": 0,
            "failed": 0,
            "papers": [],
        }

    message = build_arxiv_digest(
        papers
    )

    try:
        send_message(message)

    except Exception as exc:
        return {
            "found": len(papers),
            "sent": 0,
            "failed": len(papers),
            "papers": papers,
            "error": (
                f"{type(exc).__name__}: {exc}"
            ),
        }

    arxiv_ids = [
        p["arxiv_id"]
        for p in papers
        if p.get("arxiv_id")
    ]

    state.mark_research_papers_notified(
        arxiv_ids
    )

    return {
        "found": len(papers),
        "sent": len(arxiv_ids),
        "failed": 0,
        "papers": papers,
    }


def build_hf_digest(models):
    if not models:
        return "No new interesting Hugging Face models."

    lines = [
        "🤗 Hugging Face — High-signal models",
        "",
    ]

    for i, model in enumerate(models, 1):
        title = model.get(
            "model_id",
            "Untitled",
        )

        score = model.get(
            "score",
            0,
        )

        area = (
            model.get("technical_area")
            or "Unknown"
        )

        reason = (
            model.get("reason")
            or ""
        )

        url = model.get(
            "url",
            "",
        )

        lines.append(
            f"{i}. {title}"
        )

        lines.append(
            f"   Score: {float(score):.3f} "
            f"| Area: {area}"
        )

        if reason:
            lines.append(
                f"   {reason}"
            )

        if url:
            lines.append(
                f"   {url}"
            )

        lines.append("")

    return "\n".join(lines).strip()


def notify_hf_models(limit=10):
    models = state.unnotified_hf_models(limit)

    if not models:
        return {
            "found": 0,
            "sent": 0,
            "failed": 0,
            "models": [],
        }

    message = build_hf_digest(models)

    try:
        send_message(message)
    except Exception as exc:
        return {
            "found": len(models),
            "sent": 0,
            "failed": len(models),
            "models": models,
            "error": f"{type(exc).__name__}: {exc}",
        }

    model_ids = [
        m["model_id"]
        for m in models
        if m.get("model_id")
    ]

    state.mark_hf_models_notified(model_ids)

    return {
        "found": len(models),
        "sent": len(model_ids),
        "failed": 0,
        "models": models,
    }


def notify_kaggle(limit=10):
    items = state.unnotified_kaggle(limit)

    if not items:
        return {
            "found": 0,
            "sent": 0,
            "failed": 0,
            "items": [],
        }

    message = kaggle_agent.build_digest(items)

    try:
        send_message(message)
    except Exception as exc:
        return {
            "found": len(items),
            "sent": 0,
            "failed": len(items),
            "items": items,
            "error": f"{type(exc).__name__}: {exc}",
        }

    item_ids = [
        item["item_id"]
        for item in items
        if item.get("item_id")
    ]

    state.mark_kaggle_notified(item_ids)

    return {
        "found": len(items),
        "sent": len(item_ids),
        "failed": 0,
        "items": items,
    }


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

    research_repos = [
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

    if research_repos:
        lines.extend([
            "🧪 Research implementations",
            "",
        ])

        for i, repo in enumerate(
            research_repos,
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


def check_opportunities():
    result = opportunity_agent.check_all()

    newly_available = result.get(
        "newly_available",
        [],
    )

    if not newly_available:
        return result

    lines = [
        "🎯 Opportunities now available",
        "",
    ]

    for opp in newly_available:
        lines.append(
            f"• {opp.get('title', 'Untitled')}"
        )

        signal = opp.get("signal")

        if signal:
            lines.append(
                f"  ({signal})"
            )

        url = opp.get("url")

        if url:
            lines.append(f"  {url}")

        lines.append("")

    try:
        send_message(
            "\n".join(lines).strip()
        )
    except Exception as exc:
        print(
            "[scheduler] opportunity notification failed: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

    return result


def maybe_send_morning_brief():
    now = datetime.now(
        ZoneInfo(settings.timezone)
    )

    today = now.date().isoformat()

    if state.get_kv("morning_sent_date") == today:
        return

    if now.strftime("%H:%M") < settings.morning_time:
        return

    try:
        text = morning_agent.run()
    except Exception as exc:
        print(
            "[scheduler] morning brief failed: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
        return

    try:
        send_message(
            "🌅 Morning Briefing\n\n"
            + str(text)[:4000]
        )

        state.set_kv("morning_sent_date", today)

        print(
            "[scheduler] sent morning brief",
            flush=True,
        )

    except Exception as exc:
        print(
            "[scheduler] morning send failed: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )


def refresh_sources():
    """
    Run the fast discovery/curation pipelines.

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


def refresh_research():
    """
    Run the slower research/curation pipelines: arXiv, Hugging Face,
    and Kaggle.
    """

    try:
        arxiv_result = research.run_arxiv_research(limit=10)

        print(
            "[scheduler] arXiv scan: "
            f"discovered={arxiv_result.get('discovered', 0)} "
            f"interesting={arxiv_result.get('interesting', 0)}",
            flush=True,
        )

    except Exception as exc:
        print(
            "[scheduler] arXiv scan failed: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

    try:
        hf_result = research.curate_hf_models(
            limit=20,
        )

        print(
            "[scheduler] Hugging Face scan: "
            f"discovered={hf_result.get('discovered', 0)} "
            f"interesting={hf_result.get('interesting', 0)}",
            flush=True,
        )

    except Exception as exc:
        print(
            "[scheduler] Hugging Face scan failed: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

    try:
        kaggle_result = kaggle_agent.scan(20)

        print(
            "[scheduler] Kaggle scan: "
            f"discovered={kaggle_result.get('discovered', 0)} "
            f"interesting="
            f"{len(kaggle_result.get('interesting', []))}",
            flush=True,
        )

    except Exception as exc:
        print(
            "[scheduler] Kaggle scan failed: "
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
    last_research = 0
    last_opportunity = 0

    while True:
        now = time.time()

        # Fast discovery every 15 minutes.
        if now - last_refresh >= 900:
            refresh_sources()
            last_refresh = now

        # Research (arXiv + HF + Kaggle) every 6 hours.
        if now - last_research >= 21600:
            refresh_research()
            last_research = now

        # Opportunity availability checks every 6 hours.
        if now - last_opportunity >= 21600:
            try:
                result = check_opportunities()
                print(
                    "[scheduler] opportunity check: "
                    f"checked={result.get('checked', 0)} "
                    f"newly_available="
                    f"{len(result.get('newly_available', []))}",
                    flush=True,
                )
            except Exception as exc:
                print(
                    "[scheduler] opportunity check failed: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )
            last_opportunity = now

        maybe_send_morning_brief()

        check_reminders()
        check_blog_notifications()
        check_github_notifications()
        notify_arxiv_papers(limit=10)
        notify_hf_models(limit=10)
        notify_kaggle(limit=10)

        time.sleep(15)


if __name__ == "__main__":
    main()
