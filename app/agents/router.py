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
)


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

    return task.run(t)
