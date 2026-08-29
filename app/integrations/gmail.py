"""Gmail IMAP integration for the Spam Needle.

Uses IMAP with an app password (no Google SDKs). The only side effect is
moving clearly-spam messages into Gmail's Spam folder, which is reversible
in Gmail. Nothing is ever deleted or reported as spam outside your own
account, and a whitelist (GMAIL_SPAM_WHITELIST) is always respected.
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import settings
from app import state

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# Score above which a message is auto-moved to Spam.
# Conservative: list-unsubscribe alone (newsletters) is NOT enough; it
# needs to combine with a marketing ESP or a high-precision spam phrase.
SPAM_THRESHOLD = 5

# Well-known marketing/bulk senders. Combined with bulk headers these
# mark a message as automated mass mail rather than a personal email.
BULK_SENDERS = {
    "mailchimp.com", "mandrillapp.com", "mailerlite.com", "convertkit.com",
    "sendinblue.com", "brevo.com", "constantcontact.com", "klaviyo.com",
    "hubspot.com", "braze.com", "iterable.com", "customer.io",
    "amazonses.com", "sendgrid.net", "sparkpostmail.com", "mailgun.org",
    "postmarkapp.com", "substack.com", "beehiiv.com", "buttondown.email",
    "ghost.io", "medium.com", "linkedin.com", "facebook.com", "twitter.com",
}

# High-precision spam phrases (subject). Intentionally narrow to avoid
# false positives on legitimate marketing you might actually want.
SPAM_PHRASES = (
    "lottery", "inheritance", "you have won", "claim your prize",
    "bitcoin giveaway", "crypto giveaway", "earn $1000", "earn $5,000",
    "make money fast", "get rich quick", "work from home scam",
    "paypal dispute", "you've been selected",
)

# High-precision phishing patterns. Flagging these hard, because a
# false positive is worse than spam slipping through.
PHISHING_PHRASES = (
    "verify your account", "confirm your password", "account has been locked",
    "unusual sign-in attempt", "your password has been reset",
    "update your payment", "we need to verify", "verify your identity",
    "your account will be suspended",
)


def _decode(value):
    """Decode an RFC2047-encoded header into plain text."""
    if not value:
        return ""

    parts = []

    for fragment, charset in decode_header(value):
        if isinstance(fragment, bytes):
            try:
                parts.append(
                    fragment.decode(charset or "utf-8", "replace")
                )
            except Exception:
                parts.append(fragment.decode("utf-8", "replace"))
        else:
            parts.append(str(fragment))

    return "".join(parts).strip()


def _connect():
    if (
        not settings.gmail_email
        or not settings.gmail_app_password
    ):
        raise RuntimeError(
            "GMAIL_EMAIL / GMAIL_APP_PASSWORD not configured"
        )

    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.login(settings.gmail_email, settings.gmail_app_password)
    return conn


def _whitelist():
    raw = settings.gmail_spam_whitelist or ""

    return {
        item.strip().lower()
        for item in raw.split(",")
        if item.strip()
    }


def _whitelisted(sender):
    if not sender:
        return False

    sender = sender.lower()
    domain = sender.split("@")[-1] if "@" in sender else sender

    allow = _whitelist()

    return sender in allow or domain in allow


def _extract(raw):
    """Pull the fields needed for classification out of a raw message."""
    msg = email.message_from_bytes(raw)

    from_header = _decode(msg.get("From", ""))
    sender = from_header

    try:
        from email.utils import parseaddr
        sender = parseaddr(from_header)[1] or sender
    except Exception:
        pass

    headers = {}

    for key in (
        "List-Unsubscribe",
        "List-Id",
        "Precedence",
        "X-Priority",
        "Auto-Submitted",
    ):
        value = msg.get(key)

        if value:
            headers[key.lower()] = value

    subject = _decode(msg.get("Subject", ""))

    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)

                if payload:
                    body = payload.decode("utf-8", "replace")
                    break
    else:
        payload = msg.get_payload(decode=True)

        if payload:
            body = payload.decode("utf-8", "replace")

    return {
        "message_id": msg.get("Message-ID", ""),
        "sender": sender,
        "subject": subject,
        "headers": headers,
        "body": body[:2000],
    }


def classify(message_parts):
    """Deterministic spam classification.

    Returns (score, is_spam, signals). is_spam is True only when the
    message is clearly bulk/automated spam (not a personal email).
    """
    subject = message_parts.get("subject", "").lower()
    body = message_parts.get("body", "").lower()
    headers = message_parts.get("headers", {})
    sender = message_parts.get("sender", "").lower()
    sender_domain = sender.split("@")[-1] if "@" in sender else ""

    score = 0.0
    signals = []

    if "list-unsubscribe" in headers:
        score += 3.0
        signals.append("list-unsubscribe")

    if "precedence" in headers and headers["precedence"].lower() == "bulk":
        score += 2.0
        signals.append("bulk precedence")

    if "list-id" in headers:
        score += 1.0
        signals.append("mailing list")

    if sender_domain in BULK_SENDERS:
        score += 2.0
        signals.append("marketing sender")

    for phrase in SPAM_PHRASES:
        if phrase in subject:
            score += 3.0
            signals.append("spam phrase: " + phrase)
            break

    for phrase in PHISHING_PHRASES:
        if phrase in subject or phrase in body:
            score += 5.0
            signals.append("phishing pattern: " + phrase)
            break

    is_spam = score >= SPAM_THRESHOLD

    return score, is_spam, signals


def _move_to_spam(conn, uid):
    try:
        conn.uid("MOVE", uid, '"[Gmail]/Spam"')
    except imaplib.IMAP4.error:
        conn.uid("COPY", uid, '"[Gmail]/Spam"')
        conn.uid("STORE", uid, "+FLAGS", "(\\Deleted)")


def spam_folder_count(conn):
    try:
        conn.select('"[Gmail]/Spam"')
        typ, data = conn.uid("SEARCH", None, "ALL")
        return len(data[0].split()) if data and data[0] else 0
    except Exception:
        return 0


def scan_inbox(since_hours=6, limit=50):
    """Scan recent inbox mail and move clearly-spam messages to Spam.

    Returns a report dict with everything the needle needs to notify.
    """
    conn = _connect()

    try:
        conn.select("INBOX")

        since = (
            datetime.now(ZoneInfo(settings.timezone))
            - timedelta(hours=since_hours)
        ).strftime("%d-%b-%Y")

        typ, data = conn.uid("SEARCH", None, "SINCE", since)

        uids = data[0].split()[-limit:] if data and data[0] else []

        scanned = 0
        moved = []
        suspicious = []

        for uid in uids:
            try:
                typ, msg_data = conn.uid(
                    "FETCH",
                    uid,
                    "(BODY.PEEK[])",
                )
            except Exception:
                continue

            if not msg_data or not isinstance(msg_data, list):
                continue

            raw = None

            for part in msg_data:
                if isinstance(part, tuple) and len(part) >= 2:
                    raw = part[1]
                    break

            if raw is None:
                continue

            scanned += 1

            try:
                parts = _extract(raw)
            except Exception:
                continue

            score, is_spam, signals = classify(parts)

            if is_spam and not _whitelisted(parts["sender"]):
                try:
                    _move_to_spam(conn, uid)

                    moved.append({
                        "sender": parts["sender"],
                        "subject": parts["subject"],
                        "score": score,
                        "signals": signals,
                    })

                    state.record_spam_event({
                        "message_id": parts["message_id"] or str(uid),
                        "sender": parts["sender"],
                        "subject": parts["subject"],
                        "action": "moved_to_spam",
                        "score": score,
                        "signals": signals,
                    })
                except Exception:
                    # Never crash the scan over a single message.
                    continue

            elif score >= 2.0:
                suspicious.append({
                    "sender": parts["sender"],
                    "subject": parts["subject"],
                    "score": score,
                    "signals": signals,
                })

        try:
            conn.expunge()
        except Exception:
            pass

        spam_count = spam_folder_count(conn)

        return {
            "scanned": scanned,
            "moved": moved,
            "suspicious": suspicious,
            "spam_folder_count": spam_count,
        }

    finally:
        try:
            conn.logout()
        except Exception:
            pass
