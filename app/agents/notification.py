import needle


@needle.tool
def format_task_reminder(title: str, notes: str = ""):
    """Format a task reminder. Does not send it."""
    return (
        f"⏰ Reminder: {title}"
        + (f"\n{notes}" if notes else "")
    )


@needle.tool
def format_task_created(title: str):
    """Format a task-created notification. Does not send it."""
    return f"✅ Added task: {title}"


@needle.tool
def format_blog_digest(articles: list):
    """Format a blog digest. Does not send it."""
    if not articles:
        return "No new high-signal industry reads."

    lines = [
        "🔥 High-signal industry reads",
        "",
    ]

    for i, article in enumerate(articles, 1):
        title = article.get("title", "Untitled")
        source = article.get("source", "Unknown source")
        summary = article.get(
            "summary",
            "No summary available.",
        )
        url = article.get("url", "")

        lines.append(f"{i}. {title}")
        lines.append(f"   {source}")
        lines.append(f"   {summary}")

        if url:
            lines.append(f"   {url}")

        lines.append("")

    return "\n".join(lines).strip()


def run(event):
    event_type = event.get("type") if isinstance(event, dict) else None

    if event_type == "blog.digest":
        articles = event.get("articles", [])

        # Formatting is deterministic here.
        # Needle is not allowed to reinterpret the event.
        return format_blog_digest(articles)

    if event_type == "task.reminder":
        return format_task_reminder(
            event.get("title", ""),
            event.get("notes", ""),
        )

    if event_type == "task.created":
        return format_task_created(
            event.get("title", ""),
        )

    return "Notification received."
