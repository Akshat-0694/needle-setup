from app.agents import (
    task,
    blog,
    linkedin,
    opportunity,
    research,
    github,
    morning,
    spam,
    health,
    calendar,
    ideas,
)


def _task_delete(ident):
    try:
        return task.delete_task(int(ident))
    except Exception:
        return {"error": "Usage: /remove <id>"}


def route(t):
    l = t.lower().strip()

    if l in ("/health", "/status"):
        return health.run()

    if l == "/spam":
        return spam.run("Show my spam status")

    if l.startswith("/spam "):
        return spam.run(t)

    if l == "/tasks":
        return task.list_open_tasks()

    if l.startswith("/done "):
        try:
            return task.complete_task(int(l[6:].strip()))
        except Exception:
            return {"error": "Usage: /done <id>"}

    if l.startswith("/remove "):
        return _task_delete(l[8:].strip())

    if l.startswith("/delete "):
        return _task_delete(l[8:].strip())

    if l == "/calendar":
        return calendar.upcoming()

    if l.startswith("/calendar "):
        return calendar.run(t)

    if l.startswith("/remove_event "):
        try:
            return calendar.remove(int(l[14:].strip()))
        except Exception:
            return {"error": "Usage: /remove_event <id>"}

    if l == "/ideas":
        return ideas.list_text()

    if l.startswith("/idea done ") or l.startswith("/ideas done "):
        ident = l[10:].strip() if l.startswith("/idea done ") else l[12:].strip()

        try:
            return ideas.complete(int(ident))
        except Exception:
            return {"error": "Usage: /ideas done <id>"}

    if l.startswith("/ideas ") or l.startswith("/idea "):
        return ideas.run(t)

    if l.startswith("/remove_idea "):
        try:
            return ideas.remove(int(l[12:].strip()))
        except Exception:
            return {"error": "Usage: /remove_idea <id>"}

    if l == "/blogs":
        return blog.run("Fetch new posts, curate them, and show interesting ones.")

    if l == "/people":
        return linkedin.run("Show the most interesting imported network profiles.")

    if l == "/opportunities":
        return opportunity.run("List all watched opportunities.")

    if l.startswith("/add_opportunity ") or l.startswith("/add opp"):
        return opportunity.run(t)

    if l.startswith("/remove_opportunity ") or l.startswith("/remove opp"):
        return opportunity.run(t)

    if l == "/morning":
        return morning.run()

    if any(x in l for x in ["github", "pull request", "repository", "repo"]):
        return github.run(t)

    if any(x in l for x in ["blog", "industry news", "company news"]):
        return blog.run(t)

    if any(x in l for x in ["linkedin", "profile", "network", "person to talk"]):
        return linkedin.run(t)

    if any(x in l for x in ["opportunity", "opportunities", "open role", "job opening"]):
        return opportunity.run(t)

    if any(x in l for x in ["research", "paper", "arxiv", "look up"]):
        return research.run(t)

    if any(x in l for x in ["spam", "gmail", "unsubscribe", "phishing"]):
        return spam.run(t)

    if any(x in l for x in ["server health", "health", "server status", "how is the server"]):
        return health.run()

    if any(x in l for x in ["calendar", "appointment", "meeting", "add event"]):
        return calendar.run(t)

    if any(x in l for x in ["idea", "ideas", "brainstorm"]):
        return ideas.run(t)

    return task.run(t)
