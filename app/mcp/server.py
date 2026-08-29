import json
from datetime import datetime
from pathlib import Path

import feedparser
import httpx

from mcp.server.mcpserver import MCPServer

from app import state
from app.config import settings


mcp = MCPServer("needle-daily-v2")


@mcp.tool()
def tasks_create(
    title: str,
    notes: str = "",
    due_at: str | None = None,
) -> dict:
    """Create a personal task."""
    task_id = state.create_task(title, notes, due_at)
    return state.get_task(task_id)


@mcp.tool()
def tasks_list(status: str = "open") -> list[dict]:
    """List personal tasks."""
    return state.list_tasks(status)


@mcp.tool()
def tasks_complete(task_id: int) -> dict:
    """Complete a personal task."""
    task = state.complete_task(task_id)

    if task is None:
        return {"error": "Task not found"}

    return task


@mcp.tool()
def reminders_schedule(
    task_id: int,
    remind_at: str,
) -> dict:
    """Schedule an ISO-8601 reminder for a task."""

    try:
        parsed = datetime.fromisoformat(remind_at)
    except ValueError:
        return {
            "error": "Invalid ISO-8601 timestamp."
        }

    if parsed.tzinfo is None:
        return {
            "error": "remind_at must include a timezone offset."
        }

    if not state.get_task(task_id):
        return {
            "error": "Task not found"
        }

    reminder_id = state.add_reminder(
        task_id,
        parsed.isoformat(),
    )

    return {
        "id": reminder_id,
        "task_id": task_id,
        "remind_at": parsed.isoformat(),
    }


@mcp.tool()
def blog_fetch_new(
    limit_per_source: int = 20,
) -> list[dict]:
    """Fetch recent posts from configured RSS/Atom feeds."""

    output = []

    sources_path = Path(settings.data_dir) / "sources.json"

    if not sources_path.exists():
        return []

    sources = json.loads(
        sources_path.read_text()
    )

    for source in sources:

        feed = feedparser.parse(
            source["feed"]
        )

        for entry in feed.entries[:limit_per_source]:

            if not entry.get("link"):
                continue

            article = {
                "source": source["name"],
                "url": entry.link,
                "title": entry.get("title", ""),
                "published_at": entry.get(
                    "published",
                    "",
                ),
                "description": entry.get(
                    "summary",
                    "",
                ),
            }

            state.upsert_article(article)

            output.append(article)

    return output


@mcp.tool()
def blog_candidates(
    limit: int = 50,
) -> list[dict]:
    """Get unscored blog candidates."""

    return state.candidates(limit)


@mcp.tool()
def blog_save_score(
    url: str,
    score: float,
    interesting: bool,
    summary: str,
) -> dict:
    """Save an article relevance score and summary."""

    score = max(
        0.0,
        min(1.0, score),
    )

    state.score_article(
        url,
        score,
        interesting,
        summary,
    )

    return {"ok": True}


@mcp.tool()
def blog_interesting(
    limit: int = 20,
) -> list[dict]:
    """Get curated interesting articles."""

    return state.interesting_articles(limit)


@mcp.tool()
def research_fetch_url(
    url: str,
) -> dict:
    """Fetch readable public web content."""

    # Jina Reader converts public webpages into readable
    # text/Markdown instead of returning raw HTML.
    target = "https://r.jina.ai/" + url

    headers = {
        "Accept": "text/plain",
    }

    if settings.jina_api_key:
        headers["Authorization"] = (
            "Bearer " + settings.jina_api_key
        )

    response = httpx.get(
        target,
        headers=headers,
        timeout=45,
        follow_redirects=True,
    )

    response.raise_for_status()

    return {
        "url": url,
        "content": response.text[:50000],
    }


@mcp.tool()
def linkedin_import_profiles(
    profiles: list[dict],
) -> dict:
    """Import approved/user-provided network profiles.

    This tool does not scrape LinkedIn.
    """

    imported = 0

    for profile in profiles:

        if (
            profile.get("profile_url")
            and profile.get("name")
        ):
            state.import_person(profile)
            imported += 1

    return {
        "imported": imported
    }


@mcp.tool()
def linkedin_candidates(
    limit: int = 50,
) -> list[dict]:
    """Get unscored network profiles."""

    return state.people_candidates(limit)


@mcp.tool()
def linkedin_save_score(
    profile_url: str,
    score: float,
    interesting: bool,
    reason: str,
    conversation_hook: str,
) -> dict:
    """Save network opportunity score."""

    score = max(
        0.0,
        min(1.0, score),
    )

    state.score_person(
        profile_url,
        score,
        interesting,
        reason,
        conversation_hook,
    )

    return {"ok": True}


@mcp.tool()
def linkedin_interesting(
    limit: int = 20,
) -> list[dict]:
    """Get high-value network candidates."""

    return state.interesting_people(limit)


@mcp.tool()
def opportunity_list() -> list[dict]:
    """List all watched opportunities."""

    return state.list_opportunities()


@mcp.tool()
def opportunity_add(
    url: str,
    title: str,
    note: str = "",
) -> list[dict]:
    """Start watching an opportunity. Upserts by URL."""

    return state.add_opportunity(url, title, note)


@mcp.tool()
def opportunity_remove(
    id: int,
) -> dict:
    """Stop watching an opportunity by its id."""

    state.remove_opportunity(id)

    return {"ok": True, "removed": id}


@mcp.tool()
def kaggle_discover(
    limit: int = 20,
) -> list[dict]:
    """
    Discover active Kaggle competitions, datasets, and notebooks.

    Uses the Kaggle API v1 with KAGGLE_USERNAME / KAGGLE_KEY.
    Returns an empty list when Kaggle is not configured.
    """

    import base64
    import os

    username = os.getenv("KAGGLE_USERNAME", "")
    key = os.getenv("KAGGLE_KEY", "")

    if not username or not key:
        return []

    auth = "Basic " + base64.b64encode(
        f"{username}:{key}".encode("utf-8")
    ).decode("ascii")

    headers = {
        "Authorization": auth,
        "User-Agent": "NeedleDaily/2.0",
    }

    limit = max(1, min(int(limit), 100))

    items = []

    # --- Competitions ---
    try:
        response = httpx.get(
            "https://www.kaggle.com/api/v1/competitions/list",
            headers=headers,
            timeout=30,
            follow_redirects=True,
        )

        response.raise_for_status()

        for comp in response.json()[:limit]:
            ref = comp.get("ref")

            if not ref:
                continue

            items.append({
                "item_id": "competition:" + ref,
                "kind": "competition",
                "title": comp.get("title") or ref,
                "url": "https://www.kaggle.com/competitions/" + ref,
                "subtitle": comp.get("subtitle") or "",
                "team_count": int(comp.get("teamCount") or 0),
                "reward": comp.get("reward") or "",
                "deadline": comp.get("deadline") or "",
            })
    except Exception:
        pass

    # --- Datasets ---
    try:
        response = httpx.get(
            "https://www.kaggle.com/api/v1/datasets/list",
            params={
                "sortBy": "updated",
                "pageSize": limit,
            },
            headers=headers,
            timeout=30,
            follow_redirects=True,
        )

        response.raise_for_status()

        for ds in response.json()[:limit]:
            owner = (
                ds.get("ownerName")
                or (ds.get("owner") or {}).get("userName", "")
            )

            title = ds.get("title") or ""

            ref = ds.get("ref") or (
                f"{owner}/{title.replace(' ', '-')}"
                if owner and title
                else ""
            )

            if not ref:
                continue

            items.append({
                "item_id": "dataset:" + ref,
                "kind": "dataset",
                "title": title or ref,
                "url": "https://www.kaggle.com/datasets/" + ref,
                "subtitle": ds.get("subtitle") or "",
                "download_count": int(ds.get("downloadCount") or 0),
                "total_bytes": int(ds.get("totalBytes") or 0),
                "last_updated": ds.get("lastUpdated") or "",
            })
    except Exception:
        pass

    # --- Notebooks (kernels) ---
    try:
        response = httpx.get(
            "https://www.kaggle.com/api/v1/kernels/list",
            params={
                "page": 1,
                "pageSize": limit,
                "sortBy": "hotness",
            },
            headers=headers,
            timeout=30,
            follow_redirects=True,
        )

        response.raise_for_status()

        for kn in response.json()[:limit]:
            author = kn.get("author", "")
            slug = kn.get("slug", "")

            if not author or not slug:
                continue

            items.append({
                "item_id": "notebook:" + author + "/" + slug,
                "kind": "notebook",
                "title": kn.get("title") or slug,
                "url": (
                    "https://www.kaggle.com/code/"
                    + author + "/" + slug
                ),
                "subtitle": kn.get("subtitle") or "",
                "total_votes": int(kn.get("totalVotes") or 0),
                "total_views": int(kn.get("totalViews") or 0),
            })
    except Exception:
        pass

    return items


# ============================================================
# ARXIV DISCOVERY
# V2 additive capability.
# ============================================================

@mcp.tool()
def arxiv_discover(
    query: str = "cat:cs.LG OR cat:cs.AI OR cat:cs.CL OR cat:cs.DC",
    limit: int = 20,
    days: int = 7,
):
    """
    Discover recent arXiv papers.

    This capability performs deterministic discovery only.
    It does not decide whether a paper is interesting.
    """

    import re
    import urllib.parse
    import urllib.request
    import xml.etree.ElementTree as ET
    from datetime import datetime, timedelta, timezone

    limit = max(1, min(int(limit), 100))
    days = max(1, min(int(days), 90))

    params = urllib.parse.urlencode({
        "search_query": query,
        "start": 0,
        "max_results": limit,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })

    request = urllib.request.Request(
        "https://export.arxiv.org/api/query?" + params,
        headers={
            "User-Agent": "NeedleDaily/2.0"
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
    }

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=days)
    )

    papers = []

    for entry in root.findall(
        "atom:entry",
        ns,
    ):
        raw_id = (
            entry.findtext(
                "atom:id",
                "",
                ns,
            )
            .strip()
        )

        match = re.search(
            r"arxiv\.org/(?:abs/)?([^?#]+)",
            raw_id,
        )

        if not match:
            continue

        arxiv_id = match.group(1).strip()

        # Remove version suffix for stable identity.
        arxiv_id = re.sub(
            r"v\d+$",
            "",
            arxiv_id,
        )

        published = (
            entry.findtext(
                "atom:published",
                "",
                ns,
            )
            .strip()
        )

        updated = (
            entry.findtext(
                "atom:updated",
                "",
                ns,
            )
            .strip()
        )

        try:
            published_dt = datetime.fromisoformat(
                published.replace(
                    "Z",
                    "+00:00",
                )
            )
        except Exception:
            published_dt = None

        if (
            published_dt
            and published_dt < cutoff
        ):
            continue

        title = " ".join(
            entry.findtext(
                "atom:title",
                "",
                ns,
            ).split()
        )

        abstract = " ".join(
            entry.findtext(
                "atom:summary",
                "",
                ns,
            ).split()
        )

        authors = [
            x.findtext(
                "atom:name",
                "",
                ns,
            ).strip()
            for x in entry.findall(
                "atom:author",
                ns,
            )
        ]

        categories = [
            x.attrib.get(
                "term",
                "",
            )
            for x in entry.findall(
                "atom:category",
                ns,
            )
            if x.attrib.get("term")
        ]

        papers.append({
            "arxiv_id": arxiv_id,
            "url": (
                "https://arxiv.org/abs/"
                + arxiv_id
            ),
            "title": title,
            "authors": ", ".join(authors),
            "abstract": abstract,
            "published_at": published,
            "updated_at": updated,
            "categories": ", ".join(categories),
            "source": "arxiv",
        })

    return papers


# ============================================================
# HUGGING FACE MODEL DISCOVERY
# V1 additive capability.
# ============================================================

@mcp.tool()
def hf_discover(
    query: str = "",
    limit: int = 20,
    sort: str = "trendingScore",
):
    """
    Discover Hugging Face models.

    This capability performs deterministic discovery only.
    It does not decide whether a model is interesting.

    Multiple technical search lanes are used when no explicit
    query is supplied. Results are deduplicated by model ID.
    """

    limit = max(1, min(int(limit), 100))

    allowed_sorts = {
        "trendingScore",
        "downloads",
        "likes",
        "lastModified",
    }

    if sort not in allowed_sorts:
        sort = "trendingScore"

    if query:
        queries = [str(query).strip()]
    else:
        # Search lanes intentionally mirror the curator's
        # strong technical vocabulary. Avoid generic queries
        # such as "LLM" or "transformer" because they produce
        # large numbers of low-signal model variants.
        queries = [
            "vllm",
            "speculative decoding",
            "flashattention",
            "triton",
            "CUDA",
            "quantization",
            "AWQ",
            "GPTQ",
            "bitsandbytes",
            "mixture of experts",
            "expert pruning",
            "QLoRA",
            "GGUF",
            "llama.cpp",
        ]

    headers = {
        "User-Agent": "NeedleDaily/2.0",
        "Accept": "application/json",
    }

    if settings.hf_token:
        headers["Authorization"] = (
            "Bearer " + settings.hf_token
        )

    models_by_id = {}

    # Give every technical lane a chance to contribute.
    # The final result is still capped by `limit`.
    # Search broadly across every technical lane before
    # applying the final result limit.
    per_query_limit = min(
        10,
        max(5, limit),
    )

    for search_query in queries:

        params = {
            "search": search_query,
            "limit": per_query_limit,
            "sort": sort,
            "direction": -1,
        }

        try:
            response = httpx.get(
                "https://huggingface.co/api/models",
                params=params,
                headers=headers,
                timeout=30,
                follow_redirects=True,
            )

            response.raise_for_status()

            payload = response.json()

        except Exception:
            # Discovery should remain best-effort across
            # independent search lanes.
            continue

        if not isinstance(payload, list):
            continue

        for model in payload:

            if not isinstance(model, dict):
                continue

            model_id = (
                model.get("id")
                or model.get("modelId")
            )

            if not model_id:
                continue

            model_id = str(model_id)

            if model_id in models_by_id:
                continue

            tags = model.get("tags") or []

            if not isinstance(tags, list):
                tags = [str(tags)]

            models_by_id[model_id] = {
                "model_id": model_id,
                "url": (
                    "https://huggingface.co/"
                    + model_id
                ),
                "author": (
                    model.get("author")
                    or ""
                ),
                "pipeline_tag": (
                    model.get("pipeline_tag")
                    or ""
                ),
                "library_name": (
                    model.get("library_name")
                    or ""
                ),
                "tags": [
                    str(x)
                    for x in tags
                ],
                "description": (
                    model.get("description")
                    or ""
                ),
                "downloads": int(
                    model.get("downloads") or 0
                ),
                "likes": int(
                    model.get("likes") or 0
                ),
                "trending_score": float(
                    model.get("trendingScore") or 0
                ),
                "created_at_hf": (
                    model.get("createdAt")
                    or ""
                ),
                "last_modified": (
                    model.get("lastModified")
                    or ""
                ),
                "source": "huggingface",
            }

            # Continue collecting from every technical lane.
            # Final ranking happens after all lanes have run.

    # --------------------------------------------------------
    # Rank the discovery pool using popularity metadata only.
    #
    # This is NOT relevance scoring. Technical relevance is
    # handled later by score_hf_model().
    # --------------------------------------------------------

    models = list(models_by_id.values())

    def discovery_rank(item):
        trending = float(
            item.get("trending_score") or 0
        )

        likes = int(
            item.get("likes") or 0
        )

        downloads = int(
            item.get("downloads") or 0
        )

        return (
            trending,
            likes,
            downloads,
        )

    models.sort(
        key=discovery_rank,
        reverse=True,
    )

    return models[:limit]



if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=9000,
        stateless_http=True,
        json_response=True,
    )
