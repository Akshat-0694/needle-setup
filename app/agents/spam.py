"""Gmail Spam Needle.

Deterministic by design: handling email is a safety-sensitive action, so
the scan/move logic lives in app.integrations.gmail and this module only
dispatches, formats, and reports. The model is never asked to decide what
is spam.
"""

from app import state
from app.config import settings
from app.mcp.client import call


def build_digest(result):
    lines = [
        "🛡️ Gmail spam — scan complete",
        "",
    ]

    moved = result.get("moved", [])

    if moved:
        lines.append(
            f"Moved {len(moved)} message(s) to Spam:"
        )

        for item in moved[:10]:
            lines.append(
                f"• {item.get('subject', 'Untitled')[:70]}"
            )

            sender = item.get("sender", "")

            if sender:
                lines.append(f"  from {sender}")

        lines.append("")
    else:
        lines.append("No new spam moved to Spam.")

    suspicious = result.get("suspicious", [])

    if suspicious:
        lines.append(
            f"ℹ️ {len(suspicious)} suspicious (left in inbox):"
        )

        for item in suspicious[:5]:
            lines.append(
                f"• {item.get('subject', 'Untitled')[:60]} — "
                f"{item.get('sender', '')}"
            )

        lines.append("")

    spam_count = result.get("spam_folder_count", 0)

    lines.append(
        f"Scanned: {result.get('scanned', 0)} | "
        f"Spam folder: {spam_count} messages"
    )

    return "\n".join(lines).strip()


def status_text():
    events = state.spam_events_since(10)
    today = state.spam_events_today()
    last = state.last_spam_scan()

    configured = bool(
        settings.gmail_email and settings.gmail_app_password
    )

    lines = [
        "🛡️ Gmail spam needle",
        "",
        f"Configured: {'yes' if configured else 'no (set GMAIL_EMAIL + GMAIL_APP_PASSWORD)'}",
        f"Moved to Spam today: {today}",
        f"Last scan: {last or 'never'}",
    ]

    if events:
        lines.append("")
        lines.append("Recent activity:")

        for event in events[:10]:
            lines.append(
                f"• {event.get('subject', 'Untitled')[:60]} — "
                f"{event.get('sender', '')} "
                f"({event.get('action', '')})"
            )

    return "\n".join(lines)


def run(prompt="Show my spam status"):
    text = (prompt or "").lower()

    if "scan" in text or "check" in text:
        try:
            result = call("spam_scan")
        except Exception as exc:
            return (
                f"❌ Spam scan failed: "
                f"{type(exc).__name__}: {exc}"
            )

        return build_digest(result)

    return status_text()
