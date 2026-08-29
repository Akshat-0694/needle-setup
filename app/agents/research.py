import re

import needle

from app.mcp.client import call
from app.integrations import needle_notion
from app import state


# ============================================================
# MCP / capability tools
# ============================================================

@needle.tool
def fetch_url(url: str) -> dict:
    """Fetch readable public web content from a URL."""
    return call(
        "research_fetch_url",
        url=url,
    )


@needle.tool
def interesting_blogs(limit: int = 10) -> list[dict]:
    """Get curated high-signal industry articles."""
    return call(
        "blog_interesting",
        limit=limit,
    )


@needle.tool
def interesting_github(limit: int = 10) -> list[dict]:
    """Get high-signal GitHub repositories."""
    try:
        return state.interesting_github(limit)
    except Exception:
        return []


# ============================================================
# URL helpers
# ============================================================

def _clean_url(url):
    if not url:
        return ""

    url = str(url).strip()

    # Remove common Markdown / punctuation contamination.
    url = url.strip(
        " \t\r\n<>[](){}\"'`"
    )

    url = re.sub(
        r"[\)\]\}\>,.;:!?]+$",
        "",
        url,
    )

    # Remove Markdown fragments accidentally attached to URLs.
    url = url.split(")[", 1)[0]
    url = url.split(")**", 1)[0]

    return url


def _extract_urls(text):
    if not text:
        return []

    matches = re.findall(
        r"https?://[^\s<>\"]+",
        str(text),
    )

    seen = set()
    output = []

    for raw in matches:
        url = _clean_url(raw)

        if not url:
            continue

        if url not in seen:
            seen.add(url)
            output.append(url)

    return output


def _extract_paper_urls(text):
    paper_domains = (
        "arxiv.org",
        "openreview.net",
        "aclanthology.org",
        "paperswithcode.com",
    )

    return [
        url
        for url in _extract_urls(text)
        if any(
            domain in url.lower()
            for domain in paper_domains
        )
    ]


# ============================================================
# Research Needle
# ============================================================

def _make_research_needle():
    return needle.Needle(
        tools=[
            fetch_url,
            interesting_blogs,
            interesting_github,
        ],
        system="""
You are Research Needle.

You are the deep technical research layer of Needle Daily.

Your job is to investigate technical developments using
primary sources and technical evidence.

You may use:

- fetch_url
- interesting_blogs
- interesting_github

RESEARCH RULES

1. Never invent technical facts.
2. Never invent papers, benchmarks, repositories,
   datasets, numerical results, or citations.
3. Distinguish explicit source evidence from inference.
4. Prefer primary technical sources.
5. When a source references a paper or repository,
   follow the link with fetch_url when possible.
6. Do not treat a marketing claim as experimental evidence.
7. Identify missing evidence explicitly.
8. If a claim cannot be verified from available sources,
   say so.
9. Prefer technical mechanisms over promotional language.
10. Explain why the development matters to someone working
    on AI systems, inference, CUDA, GPU systems, agents,
    distributed systems, compilers, or ML infrastructure.

RESEARCH PROCESS

For a specific URL:

1. Fetch the URL.
2. Inspect the content.
3. Identify important paper/research links.
4. Identify implementation/GitHub links.
5. Fetch the most relevant primary sources when useful.
6. Synthesize the evidence.

For a broad research request:

1. Search curated blog sources and GitHub sources.
2. Select high-signal candidates.
3. Fetch the most relevant sources.
4. Investigate them.
5. Produce a ranked technical synthesis.

OUTPUT FORMAT

TITLE:
...

ONE-LINE TAKEAWAY:
...

PROBLEM:
...

TECHNICAL CONTRIBUTION:
...

HOW IT WORKS:
...

EVIDENCE:
- ...

PAPER / RESEARCH CONNECTIONS:
- ...

IMPLEMENTATION / GITHUB CONNECTIONS:
- ...

LIMITATIONS:
- ...

WHY IT MATTERS:
...

WHAT TO INVESTIGATE NEXT:
- ...

CONFIDENCE:
HIGH / MEDIUM / LOW

SOURCE EVIDENCE:
- ...

INFERENCE:
- ...

UNKNOWN / NEEDS VERIFICATION:
- ...
"""
    )


# ============================================================
# Single-source investigation
# ============================================================

def investigate(url: str):
    if not url:
        return {
            "ok": False,
            "error": "URL is required.",
        }

    url = _clean_url(url)

    # --------------------------------------------------------
    # STEP 1 — deterministic primary-source fetch
    # --------------------------------------------------------

    fetched = fetch_url(url)

    if not isinstance(fetched, dict):
        return {
            "ok": False,
            "error": "Unexpected fetch result.",
            "url": url,
        }

    content = fetched.get("content", "")

    if not content:
        return {
            "ok": False,
            "error": "No readable content returned.",
            "url": url,
        }

    # --------------------------------------------------------
    # STEP 2 — let Needle analyze the already-fetched source
    # --------------------------------------------------------

    # IMPORTANT:
    # The synthesis Needle receives already-fetched content and
    # must not have network tools available. This prevents it
    # from hallucinating or recursively corrupting URLs.
    agent = needle.Needle(
        tools=[],
        system=(
            "You are a technical research analyst. "
            "Analyze only the source material supplied in the prompt. "
            "Do not fetch URLs. Do not invent URLs. "
            "Do not claim evidence that is not present in the source."
        ),
    )

    prompt = f"""
Analyze the following technical source.

The source has ALREADY been fetched successfully.

You MUST NOT call fetch_url for the original URL.

Original source URL:
{url}

Source content:
--------------------
{content}
--------------------

Analyze only the supplied source unless additional
verification is genuinely necessary.

If you discover a clearly relevant paper, implementation,
GitHub repository, benchmark, or technical source that
needs verification, you may use fetch_url on that specific
URL.

Do not invent URLs.

Produce the complete research report using this format:

TITLE:
...

ONE-LINE TAKEAWAY:
...

PROBLEM:
...

TECHNICAL CONTRIBUTION:
...

HOW IT WORKS:
...

EVIDENCE:
- ...

PAPER / RESEARCH CONNECTIONS:
- ...

IMPLEMENTATION / GITHUB CONNECTIONS:
- ...

LIMITATIONS:
- ...

WHY IT MATTERS:
...

WHAT TO INVESTIGATE NEXT:
- ...

CONFIDENCE:
HIGH / MEDIUM / LOW

SOURCE EVIDENCE:
- ...

INFERENCE:
- ...

UNKNOWN / NEEDS VERIFICATION:
- ...
"""

    result = agent.complete(
        prompt,
        max_new_tokens=768,
    )

    return {
        "ok": True,
        "url": url,
        "result": result,
        "paper_urls": _extract_paper_urls(content),
        "urls": _extract_urls(content),
    }


# ============================================================
# Blog research
# ============================================================

def research_blog(article):
    url = article.get("url")

    if not url:
        return {
            "ok": False,
            "error": "Article has no URL.",
        }

    result = investigate(url)

    if not result.get("ok"):
        return result

    return {
        **result,
        "kind": "blog",
        "title": article.get("title"),
        "source": article.get("source"),
        "research": result.get("result"),
    }


def research_interesting_blogs(limit=5):
    articles = state.interesting_articles(limit)

    results = []

    for article in articles:
        try:
            result = research_blog(article)

            if result.get("ok"):
                results.append(result)

        except Exception as exc:
            results.append({
                "ok": False,
                "title": article.get("title"),
                "url": article.get("url"),
                "error": (
                    f"{type(exc).__name__}: {exc}"
                ),
            })

    return results


# ============================================================
# Notion persistence
# ============================================================

def persist_investigation(result):
    if not result.get("ok"):
        return {
            "ok": False,
            "reason": "Cannot persist failed investigation.",
        }

    url = result.get("url")

    if not url:
        return {
            "ok": False,
            "reason": "Investigation has no URL.",
        }

    research = result.get(
        "research",
        result.get("result", ""),
    )

    item = {
        "url": url,
        "title": (
            result.get("title")
            or "Research Investigation"
        ),
        "summary": research,
    }

    return needle_notion.persist_research(
        item
    )


# ============================================================
# Batch research + persistence
# ============================================================

def run_blog_research(limit=5):
    results = research_interesting_blogs(
        limit
    )

    persisted = []
    failed = []

    for result in results:
        if not result.get("ok"):
            failed.append(result)
            continue

        try:
            persistence = persist_investigation(
                result
            )

            persisted.append({
                "title": result.get("title"),
                "url": result.get("url"),
                "persistence": persistence,
            })

        except Exception as exc:
            failed.append({
                "title": result.get("title"),
                "url": result.get("url"),
                "error": (
                    f"{type(exc).__name__}: {exc}"
                ),
            })

    return {
        "researched": len(results),
        "persisted": len(persisted),
        "failed": len(failed),
        "results": results,
        "persisted_items": persisted,
        "errors": failed,
    }


# ============================================================
# General Research Needle entry point
# ============================================================

def run(
    prompt="Research the latest high-signal technical developments."
):
    # IMPORTANT:
    # The synthesis Needle receives already-fetched content and
    # must not have network tools available. This prevents it
    # from hallucinating or recursively corrupting URLs.
    agent = needle.Needle(
        tools=[],
        system=(
            "You are a technical research analyst. "
            "Analyze only the source material supplied in the prompt. "
            "Do not fetch URLs. Do not invent URLs. "
            "Do not claim evidence that is not present in the source."
        ),
    )

    return agent.complete(
        prompt,
        max_new_tokens=768,
    )
