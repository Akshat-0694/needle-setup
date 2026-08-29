import needle

from app.mcp.client import call
from app.agents.util import render
from app import state


@needle.tool
def list_opportunities():
    """List all watched opportunities."""
    return call("opportunity_list")


@needle.tool
def add_opportunity(
    url: str,
    title: str,
    note: str = "",
):
    """Start watching an opportunity. Provide the URL and a short title."""
    return call(
        "opportunity_add",
        url=url,
        title=title,
        note=note,
    )


@needle.tool
def remove_opportunity(opportunity_id: int):
    """Stop watching an opportunity by its id."""
    return call(
        "opportunity_remove",
        id=opportunity_id,
    )


@needle.tool
def check_opportunity(url: str):
    """Fetch a page and assess whether the opportunity is currently available."""
    return call(
        "research_fetch_url",
        url=url,
    )


def run(prompt):
    agent = needle.Needle(
        tools=[
            list_opportunities,
            add_opportunity,
            remove_opportunity,
            check_opportunity,
        ],
        system=(
            "You are Opportunity Needle. You maintain a personal list of "
            "opportunities the user wants to know about when they become "
            "available (e.g. an application window, a submission call, a "
            "limited opening). Use list_opportunities to see the list, "
            "add_opportunity to watch a new one, remove_opportunity to stop "
            "watching, and check_opportunity to fetch the page and assess "
            "whether it is currently open or available. Only claim what the "
            "fetched page actually says. Never invent availability."
        ),
    )

    return render(agent.run(prompt))


def classify_available(content):
    """
    Deterministically classify whether a fetched page signals an
    opportunity that is currently open/available.
    """
    if not content:
        return "unknown", ""

    text = str(content).lower()

    available_terms = [
        "apply now",
        "apply here",
        "applications open",
        "applications are open",
        "now accepting",
        "accepting applications",
        "open for",
        "is open",
        "available now",
        "register now",
        "sign up now",
        "enroll now",
        "reserve",
        "still available",
        "in stock",
    ]

    closed_terms = [
        "applications closed",
        "application closed",
        "closed",
        "deadline has passed",
        "registration closed",
        "sold out",
        "no longer available",
        "ended",
        "expired",
        "waitlist",
        "waiting list",
    ]

    for term in closed_terms:
        if term in text:
            return "not_available", term

    for term in available_terms:
        if term in text:
            return "available", term

    return "unknown", ""


def check_all():
    """
    Check every watched opportunity and return the ones that newly
    became available, so the scheduler can notify on Telegram.
    """
    results = []
    checked = 0
    failed = 0

    for opp in state.list_opportunities():
        if opp.get("status") == "available":
            continue

        checked += 1

        try:
            content = call(
                "research_fetch_url",
                url=opp["url"],
            )
        except Exception:
            failed += 1
            continue

        if isinstance(content, dict):
            text = content.get("content", "")
        else:
            text = str(content)

        status, signal = classify_available(text)

        state.update_opportunity_status(
            opp["id"],
            status,
            signal,
        )

        if status == "available":
            results.append(
                {
                    **opp,
                    "status": status,
                    "signal": signal,
                }
            )

    return {
        "checked": checked,
        "failed": failed,
        "newly_available": results,
    }
