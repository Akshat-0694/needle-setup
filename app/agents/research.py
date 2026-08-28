from datetime import datetime, timezone
import needle
import httpx

@needle.tool
def current_utc_time():
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()

@needle.tool
def fetch_url(url: str):
    """Fetch a public HTTP/HTTPS URL and return a bounded text response. Read-only."""
    if not (url.startswith("https://") or url.startswith("http://")):
        return {"error": "Only HTTP(S) URLs are allowed."}

    try:
        with httpx.Client(follow_redirects=True, timeout=15) as client:
            r = client.get(url, headers={"User-Agent": "needle-daily/0.1"})
            text = r.text[:12000]
            return {
                "status_code": r.status_code,
                "url": str(r.url),
                "content": text,
            }
    except Exception as exc:
        return {"error": str(exc)}

def run(prompt: str):
    agent = needle.Needle(
        tools=[current_utc_time, fetch_url],
        system=(
            "You are the research Needle in a personal automation system. "
            "Use only the provided read-only tools. "
            "Do not claim to have searched sources you did not fetch. "
            "Be concise and state uncertainty."
        ),
    )
    return agent.run(prompt, max_steps=6, max_new_tokens=256)
