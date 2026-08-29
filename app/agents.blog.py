import re
import needle

from app.mcp.client import call


# ============================================================
# Blog relevance model
# ============================================================

POSITIVE = {
    # GPU / CUDA
    "cuda": 6,
    "gpu": 5,
    "gpu kernel": 7,
    "kernel": 5,
    "triton": 5,
    "rocm": 4,
    "accelerator": 4,

    # LLM / inference
    "llm": 5,
    "inference": 6,
    "serving": 5,
    "vllm": 6,
    "transformer": 4,
    "attention": 5,
    "kv cache": 6,
    "speculative decoding": 7,

    # Optimization
    "quantization": 6,
    "compression": 5,
    "distillation": 5,
    "optimization": 4,
    "performance": 3,
    "latency": 5,
    "throughput": 5,
    "memory": 3,

    # ML systems
    "distributed": 5,
    "distributed systems": 6,
    "ml infrastructure": 7,
    "training infrastructure": 6,
    "cluster": 4,
    "scheduler": 4,
    "scheduling": 4,

    # Systems
    "compiler": 5,
    "compilers": 5,
    "runtime": 4,
    "systems": 3,
    "operating system": 3,

    # Agents / research
    "agent": 4,
    "agents": 4,
    "reinforcement learning": 5,
    "rl": 3,
    "fine-tuning": 4,
    "finetuning": 4,
    "open source": 3,
    "open-source": 3,

    # Strong technical signals
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
    matched_positive = []
    matched_negative = []

    for keyword, weight in POSITIVE.items():
        if keyword in text:
            score += weight
            matched_positive.append(keyword)

    for keyword, weight in NEGATIVE.items():
        if keyword in text:
            score += weight
            matched_negative.append(keyword)

    return {
        "raw_score": score,
        "positive": matched_positive,
        "negative": matched_negative,
    }


def classify(article):
    result = relevance_score(article)

    score = result["raw_score"]

    # Strong technical signal.
    if score >= 12:
        classification = "HIGH_SIGNAL"
        normalized = 0.95

    # Worth reading.
    elif score >= 7:
        classification = "INTERESTING"
        normalized = 0.70

    # Potentially useful.
    elif score >= 3:
        classification = "MAYBE"
        normalized = 0.35

    # Ignore.
    else:
        classification = "IGNORE"
        normalized = 0.0

    return {
        "relevance": classification,
        "score": normalized,
        "interesting": classification in {
            "INTERESTING",
            "HIGH_SIGNAL",
        },
        "raw_score": score,
        "matched_positive": result["positive"],
        "matched_negative": result["negative"],
    }


# ============================================================
# MCP operations
# ============================================================

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


def save_article(
    url,
    score,
    interesting,
    summary,
):
    return call(
        "blog_save_score",
        url=url,
        score=score,
        interesting=interesting,
        summary=summary,
    )


# ============================================================
# Lightweight extractive summarizer
# ============================================================

def summarize_text(content, max_sentences=3):
    """
    Create a deterministic summary from article text.

    This intentionally does not use Needle 2.
    """

    if not content:
        return ""

    # Remove excessive whitespace.
    content = re.sub(
        r"\s+",
        " ",
        str(content),
    ).strip()

    if not content:
        return ""

    sentences = re.split(
        r"(?<=[.!?])\s+",
        content,
    )

    sentences = [
        s.strip()
        for s in sentences
        if 60 <= len(s.strip()) <= 500
    ]

    if not sentences:
        return content[:700]

    technical_terms = [
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
    ]

    scored = []

    for index, sentence in enumerate(sentences):
        lower = sentence.lower()

        technical_hits = sum(
            1
            for term in technical_terms
            if term in lower
        )

        # Prefer earlier sentences slightly because
        # technical articles usually establish the
        # main contribution near the beginning.
        position_bonus = max(
            0,
            3 - index * 0.05,
        )

        scored.append(
            (
                technical_hits + position_bonus,
                index,
                sentence,
            )
        )

    selected = sorted(
        scored,
        reverse=True,
    )[:max_sentences]

    # Restore article order.
    selected.sort(
        key=lambda x: x[1]
    )

    return " ".join(
        x[2]
        for x in selected
    )


# ============================================================
# Blog Radar
# ============================================================

def scan(candidate_limit=30):
    """
    Complete Blog Radar.

    Deterministic ranking controls classification.
    MCP handles retrieval and persistence.
    """

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

        classification = decision["relevance"]
        score = decision["score"]

        summary = (
            "Technical signals: "
            + ", ".join(
                decision["matched_positive"]
            )
            if decision["matched_positive"]
            else "No strong technical signals detected."
        )

        # Only retrieve full articles for promising
        # candidates.
        if classification in {
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

                extracted = summarize_text(
                    content
                )

                if extracted:
                    summary = extracted

            except Exception as exc:
                summary = (
                    f"{summary} "
                    f"Full article fetch failed: "
                    f"{type(exc).__name__}"
                )

        save_article(
            url=article["url"],
            score=score,
            interesting=decision["interesting"],
            summary=summary,
        )

        results.append({
            "id": article.get("id"),
            "source": article.get("source"),
            "title": article.get("title"),
            "url": article.get("url"),
            "relevance": classification,
            "score": score,
            "interesting": decision["interesting"],
            "summary": summary,
            "signals": decision["matched_positive"],
            "negative_signals": decision["matched_negative"],
        })

    results.sort(
        key=lambda x: x["score"],
        reverse=True,
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
