from app import state
import re

from app.mcp.client import call
from app.integrations.needle_notion import persist_blog


POSITIVE = {
    "cuda": 6,
    "gpu": 5,
    "gpu kernel": 7,
    "kernel": 5,
    "triton": 5,
    "rocm": 4,
    "accelerator": 4,
    "llm": 5,
    "inference": 6,
    "serving": 5,
    "vllm": 6,
    "transformer": 4,
    "attention": 5,
    "kv cache": 6,
    "speculative decoding": 7,
    "quantization": 6,
    "compression": 5,
    "distillation": 5,
    "optimization": 4,
    "performance": 3,
    "latency": 5,
    "throughput": 5,
    "memory": 3,
    "distributed": 5,
    "distributed systems": 6,
    "ml infrastructure": 7,
    "training infrastructure": 6,
    "cluster": 4,
    "scheduler": 4,
    "scheduling": 4,
    "compiler": 5,
    "compilers": 5,
    "runtime": 4,
    "systems": 3,
    "operating system": 3,
    "agent": 4,
    "agents": 4,
    "reinforcement learning": 5,
    "rl": 3,
    "fine-tuning": 4,
    "finetuning": 4,
    "open source": 3,
    "open-source": 3,
    "benchmark": 3,
    "architecture": 4,
    "implementation": 5,
    "under the hood": 5,
    "how we built": 5,
    "internals": 5,
}

NEGATIVE = {
    "hiring": -8,
    "job opening": -8,
    "jobs": -7,
    "careers": -7,
    "funding": -8,
    "fundraise": -8,
    "raised": -7,
    "investment": -6,
    "webinar": -5,
    "event": -3,
    "announcement": -4,
    "launch": -3,
    "available now": -3,
    "pricing": -5,
    "partnership": -5,
    "customer story": -6,
}


def _text(article):
    return " ".join([
        str(article.get("title", "")),
        str(article.get("description", "")),
        str(article.get("source", "")),
    ]).lower()


def relevance_score(article):
    text = _text(article)

    score = 0
    positive = []
    negative = []

    for keyword, weight in POSITIVE.items():
        if keyword in text:
            score += weight
            positive.append(keyword)

    for keyword, weight in NEGATIVE.items():
        if keyword in text:
            score += weight
            negative.append(keyword)

    return {
        "raw_score": score,
        "positive": positive,
        "negative": negative,
    }


def classify(article):
    result = relevance_score(article)
    score = result["raw_score"]

    if score >= 12:
        relevance = "HIGH_SIGNAL"
        normalized = 0.95
    elif score >= 7:
        relevance = "INTERESTING"
        normalized = 0.70
    elif score >= 3:
        relevance = "MAYBE"
        normalized = 0.35
    else:
        relevance = "IGNORE"
        normalized = 0.0

    return {
        "relevance": relevance,
        "score": normalized,
        "interesting": relevance in {
            "INTERESTING",
            "HIGH_SIGNAL",
        },
        "raw_score": score,
        "matched_positive": result["positive"],
        "matched_negative": result["negative"],
    }


def fetch_new_articles():
    return call(
        "blog_fetch_new",
        limit_per_source=20,
    )


def get_candidates(limit=30):
    return call(
        "blog_candidates",
        limit=limit,
    )


def read_article(url):
    return call(
        "research_fetch_url",
        url=url,
    )


def save_article(url, score, interesting, summary):
    return call(
        "blog_save_score",
        url=url,
        score=score,
        interesting=interesting,
        summary=summary,
    )

def clean_article_content(content):
    if not content:
        return ""

    text = str(content)

    # Jina Reader wrapper.
    marker = "Markdown Content:"
    marker_index = text.find(marker)

    if marker_index >= 0:
        text = text[
            marker_index + len(marker):
        ]

    # Remove Markdown images.
    text = re.sub(
        r"!\[[^\]]*\]\([^)]+\)",
        "",
        text,
    )

    # Convert Markdown links to their visible text.
    text = re.sub(
        r"\[([^\]]+)\]\([^)]+\)",
        r"\1",
        text,
    )

    # Remove HTML tags if any slipped through.
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    cleaned_lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # Remove Markdown headings.
        line = re.sub(
            r"^\s{0,3}#{1,6}\s+",
            "",
            line,
        )

        # Ignore navigation / metadata fragments.
        lower = line.lower()

        if lower in {
            "related resources",
            "developer tools & techniques",
            "english",
            "中文",
        }:
            continue

        cleaned_lines.append(line)

    text = " ".join(cleaned_lines)

    # Normalize whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()

def summarize_text(content, max_sentences=3):
    if not content:
        return ""

    content = clean_article_content(content)

    if not content:
        return ""

    # Remove Markdown headings that may remain inline.
    content = re.sub(
        r"#{1,6}\s*",
        "",
        content,
    )

    # Remove Markdown links while preserving visible text.
    content = re.sub(
        r"\[([^\]]+)\]\([^)]+\)",
        r"\1",
        content,
    )

    content = re.sub(
        r"\s+",
        " ",
        content,
    ).strip()

    sentences = re.split(
        r"(?<=[.!?])\s+",
        content,
    )

    sentences = [
        s.strip()
        for s in sentences
        if 80 <= len(s.strip()) <= 600
    ]

    if not sentences:
        return content[:700]

    terms = [
        "cuda",
        "gpu",
        "inference",
        "llm",
        "kernel",
        "quantization",
        "latency",
        "throughput",
        "memory",
        "distributed",
        "compiler",
        "optimization",
        "architecture",
        "performance",
        "training",
        "serving",
        "recovery",
        "benchmark",
        "tokens",
        "power",
    ]

    scored = []

    for index, sentence in enumerate(sentences):
        lower = sentence.lower()

        hits = sum(
            1
            for term in terms
            if term in lower
        )

        # Prefer early article content.
        position_bonus = max(
            0,
            3 - index * 0.05,
        )

        # Prefer sentences containing actual
        # technical information.
        score = hits + position_bonus

        scored.append(
            (
                score,
                index,
                sentence,
            )
        )

    selected = sorted(
        scored,
        key=lambda x: (
            x[0],
            -x[1],
        ),
        reverse=True,
    )[:max_sentences]

    selected.sort(
        key=lambda x: x[1],
    )

    return " ".join(
        x[2]
        for x in selected
    )

def article_content_is_valid(content):
    if not content:
        return False

    text = content.strip()
    lower = text.lower()

    if len(text) < 500:
        return False

    bad_markers = [
        "<!doctype html",
        "<html",
        "<head",
        "<script",
        "window.nreum",
        "loader_config",
        "webpack",
    ]

    bad_hits = sum(
        1
        for marker in bad_markers
        if marker in lower
    )

    return bad_hits < 2

def scan(candidate_limit=30):
    discovered = fetch_new_articles()

    candidates = get_candidates(
        limit=candidate_limit
    )

    if not isinstance(candidates, list):
        return {
            "error": "blog_candidates did not return a list",
            "raw": candidates,
        }

    results = []

    for article in candidates:
        decision = classify(article)

        summary = (
            "Technical signals: "
            + ", ".join(
                decision["matched_positive"]
            )
            if decision["matched_positive"]
            else "No strong technical signals detected."
        )

        if decision["relevance"] in {
            "INTERESTING",
            "HIGH_SIGNAL",
        }:
            try:
                article_data = read_article(
                    article["url"]
                )

                if isinstance(article_data, dict):
                    content = article_data.get(
                        "content",
                        "",
                    )
                else:
                    content = str(article_data)

                extracted = clean_article_content(
                    content
                )

                if article_content_is_valid(
                    extracted
                ):
                    summary = summarize_text(
                        extracted
                    )
                else:
                    summary = (
                        "Summary unavailable: "
                        "article extraction returned "
                        "unusable content."
                    )

            except Exception as exc:
                summary += (
                    f" Full article fetch failed: "
                    f"{type(exc).__name__}"
                )

        save_article(
            url=article["url"],
            score=decision["score"],
            interesting=decision["interesting"],
            summary=summary,
        )

        results.append({
            "id": article.get("id"),
            "source": article.get("source"),
            "title": article.get("title"),
            "url": article.get("url"),
            "relevance": decision["relevance"],
            "score": decision["score"],
            "interesting": decision["interesting"],
            "summary": summary,
            "signals": decision["matched_positive"],
            "negative_signals": decision["matched_negative"],
        })

    results.sort(
        key=lambda x: x["score"],
        reverse=True,
    )


    # Persist interesting blog articles into Notion.
    notion_persisted = 0
    notion_failed = 0

    for item in interesting:
        try:
            result = persist_blog(item)

            if result.get("ok"):
                notion_persisted += 1
            else:
                notion_failed += 1

        except Exception as exc:
            notion_failed += 1
            print(
                f"[blog] Notion persistence failed for "
                f"{item.get('title')}: {type(exc).__name__}: {exc}",
                flush=True,
            )

    return {
        "discovered": (
            len(discovered)
            if isinstance(discovered, list)
            else None
        ),
        "evaluated": len(results),
        "interesting": [
            x
            for x in results
            if x["interesting"]
        ],
        "all": results,
    }


def run(prompt="Scan my industry blogs"):
    return scan()


def refresh_interesting_summaries(limit=100):
    """Re-fetch existing interesting articles and refresh their summaries."""

    articles = state.interesting_articles(limit)
    refreshed = []
    failed = []

    for article in articles:
        url = article.get("url")

        if not url:
            continue

        try:
            article_data = read_article(url)

            if isinstance(article_data, dict):
                content = article_data.get("content", "")
            else:
                content = str(article_data)

            extracted = clean_article_content(content)

            if not article_content_is_valid(extracted):
                failed.append({
                    "title": article.get("title"),
                    "url": url,
                    "reason": "invalid extracted content",
                })
                continue

            summary = summarize_text(extracted)

            if not summary:
                failed.append({
                    "title": article.get("title"),
                    "url": url,
                    "reason": "empty summary",
                })
                continue

            # Preserve the existing score and interesting flag.
            save_article(
                url=url,
                score=article.get("score", 0.0),
                interesting=bool(
                    article.get("interesting", False)
                ),
                summary=summary,
            )

            refreshed.append({
                "title": article.get("title"),
                "url": url,
                "summary": summary,
            })

        except Exception as exc:
            failed.append({
                "title": article.get("title"),
                "url": url,
                "reason": f"{type(exc).__name__}: {exc}",
            })

    return {
        "refreshed": len(refreshed),
        "failed": len(failed),
        "articles": refreshed,
        "errors": failed,
    }


def refresh_interesting_summaries(limit=100):
    """Re-fetch existing interesting articles and refresh their summaries."""

    articles = state.interesting_articles(limit)
    refreshed = []
    failed = []

    for article in articles:
        url = article.get("url")

        if not url:
            continue

        try:
            article_data = read_article(url)

            if isinstance(article_data, dict):
                content = article_data.get("content", "")
            else:
                content = str(article_data)

            extracted = clean_article_content(content)

            if not article_content_is_valid(extracted):
                failed.append({
                    "title": article.get("title"),
                    "url": url,
                    "reason": "invalid extracted content",
                })
                continue

            summary = summarize_text(extracted)

            if not summary:
                failed.append({
                    "title": article.get("title"),
                    "url": url,
                    "reason": "empty summary",
                })
                continue

            # Preserve the existing score and interesting flag.
            save_article(
                url=url,
                score=article.get("score", 0.0),
                interesting=bool(
                    article.get("interesting", False)
                ),
                summary=summary,
            )

            refreshed.append({
                "title": article.get("title"),
                "url": url,
                "summary": summary,
            })

        except Exception as exc:
            failed.append({
                "title": article.get("title"),
                "url": url,
                "reason": f"{type(exc).__name__}: {exc}",
            })

    return {
        "refreshed": len(refreshed),
        "failed": len(failed),
        "articles": refreshed,
        "errors": failed,
    }
