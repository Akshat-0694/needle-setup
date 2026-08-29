from app import state
import base64
import json
import math
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlencode


TECHNICAL_TERMS = {
    "llm": 5,
    "inference": 7,
    "serving": 6,
    "gpu": 5,
    "cuda": 7,
    "kernel": 6,
    "triton": 6,
    "vllm": 7,
    "transformer": 5,
    "attention": 5,
    "quantization": 6,
    "distributed": 5,
    "distributed systems": 7,
    "ml infrastructure": 8,
    "training infrastructure": 7,
    "compiler": 6,
    "runtime": 5,
    "agent": 4,
    "agents": 5,
    "reinforcement learning": 6,
    "fine-tuning": 5,
    "finetuning": 5,
    "benchmark": 4,
    "architecture": 5,
    "systems": 4,
    "optimization": 5,
    "performance": 4,
    "memory": 3,
    "moe": 5,
    "mixture-of-experts": 6,
}


RESEARCH_POSITIVE = {
    "arxiv": 5,
    "implementation": 5,
    "implemented": 5,
    "reimplementation": 9,
    "reproduction": 9,
    "reproduce": 8,
    "paper implementation": 10,
    "implementation of": 10,
    "based on the paper": 10,
    "based on arxiv": 10,
    "research implementation": 10,
    "research experiment": 8,
    "official implementation": 8,
    "reference implementation": 9,
    "equation": 4,
    "equations": 4,
    "benchmark": 3,
    "evaluation": 3,
}


RESEARCH_NEGATIVE = {
    "paper search": -10,
    "paper search engine": -10,
    "paper collection": -10,
    "paper browser": -8,
    "paper reader": -8,
    "paper translator": -8,
    "paper summarizer": -8,
    "research assistant": -8,
    "research agent": -6,
    "paper-to-code": -5,
    "paper to code": -5,
    "generate code from papers": -8,
    "course": -8,
    "tutorial": -7,
}


GENERIC_NEGATIVE = {
    "awesome": -10,
    "books": -10,
    "book": -8,
    "course": -8,
    "courses": -8,
    "tutorial": -8,
    "tutorials": -8,
    "roadmap": -10,
    "interview": -8,
    "cheatsheet": -8,
    "cheatsheets": -8,
    "collection": -6,
    "list of": -6,
}


def gh_api(endpoint):
    result = subprocess.run(
        ["gh", "api", endpoint],
        capture_output=True,
        text=True,
        timeout=75,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"gh api failed: {result.stderr.strip()}"
        )

    return json.loads(result.stdout)


def search_repositories(
    query,
    sort="stars",
    order="desc",
    limit=20,
):
    params = urlencode({
        "q": query,
        "sort": sort,
        "order": order,
        "per_page": limit,
    })

    return gh_api(
        f"search/repositories?{params}"
    ).get("items", [])


def repo_text(repo):
    return " ".join([
        repo.get("name", ""),
        repo.get("full_name", ""),
        repo.get("description") or "",
        " ".join(repo.get("topics") or []),
    ]).lower()


def technical_score(repo):
    text = repo_text(repo)

    score = 0
    signals = []

    for term, weight in TECHNICAL_TERMS.items():
        if term in text:
            score += weight
            signals.append(term)

    for term, weight in GENERIC_NEGATIVE.items():
        if term in text:
            score += weight

    return score, signals


def research_metadata_score(repo):
    text = repo_text(repo)

    score = 0
    signals = []

    for term, weight in RESEARCH_POSITIVE.items():
        if term in text:
            score += weight
            signals.append(term)

    for term, weight in RESEARCH_NEGATIVE.items():
        if term in text:
            score += weight

    return score, signals


def popularity_score(repo):
    stars = repo.get("stargazers_count") or 0
    forks = repo.get("forks_count") or 0

    return (
        min(8.0, math.log10(max(stars, 1)) * 1.8)
        + min(3.0, math.log10(max(forks, 1)) * 1.2)
    )


def recency_score(repo):
    updated = repo.get("updated_at")

    if not updated:
        return 0.0

    try:
        dt = datetime.fromisoformat(
            updated.replace("Z", "+00:00")
        )
    except ValueError:
        return 0.0

    age_days = (
        datetime.now(timezone.utc) - dt
    ).total_seconds() / 86400

    if age_days <= 1:
        return 6.0
    if age_days <= 3:
        return 5.0
    if age_days <= 7:
        return 4.0
    if age_days <= 14:
        return 2.5
    if age_days <= 30:
        return 1.0

    return 0.0


def get_readme(repo):
    full_name = repo.get("full_name")

    if not full_name:
        return ""

    try:
        data = gh_api(
            f"repos/{full_name}/readme"
        )

        content = data.get("content", "")

        if not content:
            return ""

        return base64.b64decode(
            content
        ).decode(
            "utf-8",
            errors="replace",
        )

    except Exception:
        return ""


def research_readme_score(readme):
    if not readme:
        return 0, []

    text = readme.lower()

    score = 0
    signals = []

    strong_patterns = {
        "implementation of": 10,
        "implements the": 9,
        "implementation for": 9,
        "reimplementation of": 12,
        "reproduction of": 12,
        "reproduce the results": 10,
        "reproduces the results": 10,
        "based on the paper": 10,
        "based on arxiv": 10,
        "paper implementation": 12,
        "reference implementation": 10,
        "research implementation": 12,
        "official implementation": 9,
        "research experiment": 8,
        "we implement": 9,
        "we reproduce": 10,
        "we reimplement": 11,
    }

    for pattern, weight in strong_patterns.items():
        if pattern in text:
            score += weight
            signals.append(pattern)

    if "arxiv.org/abs/" in text:
        score += 6
        signals.append("arxiv-paper-link")

    if "arxiv:" in text:
        score += 4
        signals.append("arxiv-identifier")

    mapping_terms = [
        "equation",
        "eq.",
        "module",
        "implementation details",
        "source code",
        "benchmark",
        "evaluation",
        "results",
    ]

    mapping_hits = sum(
        1
        for term in mapping_terms
        if term in text
    )

    if mapping_hits >= 3:
        score += 6
        signals.append(
            "paper-to-code/evaluation evidence"
        )

    for term, weight in RESEARCH_NEGATIVE.items():
        if term in text:
            score += weight
            signals.append(f"negative:{term}")

    return score, signals


def normalize_repo(repo, category):
    technical, technical_signals = technical_score(repo)

    research = 0
    research_signals = []

    if category == "research_implementation":
        research, research_signals = (
            research_metadata_score(repo)
        )

    raw_score = (
        technical
        + research
        + popularity_score(repo)
        + recency_score(repo)
    )

    return {
        "source": "GitHub",
        "repo": repo.get("full_name"),
        "name": repo.get("name"),
        "description": repo.get("description") or "",
        "url": repo.get("html_url"),
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "language": repo.get("language"),
        "topics": repo.get("topics") or [],
        "updated_at": repo.get("updated_at"),
        "category": category,
        "raw_score": round(raw_score, 2),
        "score": 0.0,
        "technical_signals": technical_signals,
        "research_signals": research_signals,
    }


def finalize_score(item):
    raw = max(0.0, item["raw_score"])

    item["score"] = round(
        1.0 - math.exp(-raw / 55.0),
        3,
    )

    return item


def trending_projects(limit=20):
    queries = [
        "llm inference pushed:>2026-08-01 archived:false",
        "cuda gpu pushed:>2026-08-01 archived:false",
        "ml infrastructure pushed:>2026-08-01 archived:false",
        "compiler runtime distributed pushed:>2026-08-01 archived:false",
        "agents inference pushed:>2026-08-01 archived:false",
    ]

    repos = {}

    for query in queries:
        for repo in search_repositories(
            query,
            sort="updated",
            order="desc",
            limit=10,
        ):
            if repo.get("full_name"):
                repos[repo["full_name"]] = repo

    results = []

    for repo in repos.values():
        item = normalize_repo(
            repo,
            "trending_open_source",
        )

        if not item["technical_signals"]:
            continue

        if (
            item["stars"] == 0
            and item["raw_score"] < 15
        ):
            continue

        results.append(
            finalize_score(item)
        )

    results.sort(
        key=lambda x: (
            x["raw_score"],
            x["stars"],
        ),
        reverse=True,
    )

    results = results[:limit]

    for item in results:
        item["interesting"] = item["score"] >= 0.50
        state.upsert_github_repository(item)

    return results


def research_implementations(limit=20):
    queries = [
        "arxiv implementation llm pushed:>2026-08-01 archived:false",
        "arxiv implementation inference pushed:>2026-08-01 archived:false",
        "arxiv implementation agents pushed:>2026-08-01 archived:false",
        "arxiv implementation cuda pushed:>2026-08-01 archived:false",
        "reimplementation reproduction paper pushed:>2026-08-01 archived:false",
    ]

    repos = {}

    for query in queries:
        for repo in search_repositories(
            query,
            sort="updated",
            order="desc",
            limit=10,
        ):
            if repo.get("full_name"):
                repos[repo["full_name"]] = repo

    candidates = []

    for repo in repos.values():
        technical, technical_signals = (
            technical_score(repo)
        )

        research, research_signals = (
            research_metadata_score(repo)
        )

        if not research_signals:
            continue

        if not technical_signals:
            continue

        if technical + research < 12:
            continue

        candidates.append(repo)

    candidates.sort(
        key=lambda r: (
            research_metadata_score(r)[0]
            + technical_score(r)[0]
            + popularity_score(r)
            + recency_score(r)
        ),
        reverse=True,
    )

    results = []

    for repo in candidates[:max(limit * 2, 20)]:
        item = normalize_repo(
            repo,
            "research_implementation",
        )

        readme = get_readme(repo)

        readme_score, readme_signals = (
            research_readme_score(readme)
        )

        item["readme_verified"] = bool(readme)
        item["readme_research_score"] = readme_score
        item["readme_signals"] = readme_signals

        item["raw_score"] += readme_score

        has_negative = any(
            signal.startswith("negative:")
            for signal in readme_signals
        )

        strong_evidence = (
            readme_score >= 10
            and not has_negative
        )

        if not strong_evidence:
            continue

        results.append(
            finalize_score(item)
        )

    results.sort(
        key=lambda x: (
            x["raw_score"],
            x["stars"],
        ),
        reverse=True,
    )

    results = results[:limit]

    for item in results:
        item["interesting"] = item["score"] >= 0.50
        state.upsert_github_repository(item)

    return results


def scan(limit=20):
    trending = trending_projects(limit)
    research = research_implementations(limit)

    seen = set()
    final = []

    for item in trending + research:
        if item["repo"] in seen:
            continue

        seen.add(item["repo"])
        final.append(item)

    final.sort(
        key=lambda x: x["raw_score"],
        reverse=True,
    )

    return {
        "trending_open_source": trending,
        "research_implementations": research,
        "all": final,
        "count": len(final),
    }


def run(prompt="Scan GitHub"):
    return scan()
