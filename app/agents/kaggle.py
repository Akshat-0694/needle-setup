import needle

from app import state
from app.mcp.client import call
from app.agents.util import render


POSITIVE = {
    "cuda": 6,
    "gpu": 5,
    "triton": 4,
    "kernel": 4,
    "llm": 5,
    "inference": 5,
    "vllm": 6,
    "transformer": 4,
    "attention": 4,
    "quantization": 5,
    "compression": 4,
    "distillation": 4,
    "distributed": 4,
    "ml infrastructure": 5,
    "mlops": 4,
    "compiler": 4,
    "pytorch": 3,
    "deep learning": 4,
    "nlp": 4,
    "computer vision": 4,
    "generative": 4,
    "diffusion": 4,
    "rag": 5,
    "fine-tuning": 4,
    "agent": 3,
    "benchmark": 3,
}

NEGATIVE = {
    "titanic": -5,
    "housing prices": -4,
    "iris": -6,
    "mnist": -4,
    "getting started": -5,
    "tutorial": -3,
    "starter": -3,
}


@needle.tool
def interesting_items(limit: int = 10) -> list[dict]:
    """Get curated interesting Kaggle competitions, datasets, and notebooks."""
    return state.interesting_kaggle(limit)


def _text(item):
    return " ".join([
        item.get("title", ""),
        item.get("subtitle", ""),
        item.get("reason", ""),
    ])


def _popularity(item):
    kind = item.get("kind")

    if kind == "competition":
        return float(item.get("team_count") or 0) / 500.0

    if kind == "notebook":
        return float(item.get("total_votes") or 0) / 200.0

    return float(item.get("download_count") or 0) / 100000.0


def _score(item):
    text = _text(item).lower()

    score = 0.0
    signals = []

    for keyword, weight in POSITIVE.items():
        if keyword in text:
            score += weight
            signals.append(keyword)

    for keyword, weight in NEGATIVE.items():
        if keyword in text:
            score += weight

    score += min(0.3, _popularity(item))

    normalized = max(0.0, min(1.0, score / 12.0))

    return normalized, signals


def scan(limit=20):
    """Discover and deterministically curate Kaggle items."""
    items = call("kaggle_discover", limit=limit)

    if not isinstance(items, list):
        return {
            "error": "kaggle_discover did not return a list",
            "discovered": 0,
            "interesting": 0,
            "items": [],
        }

    results = []

    for raw in items:
        item = dict(raw)

        score, signals = _score(item)

        item["deterministic_score"] = score
        item["score"] = score
        item["signals"] = signals
        item["reason"] = (
            "Signals: " + ", ".join(signals)
            if signals
            else "No strong technical signals."
        )
        item["interesting"] = bool(
            signals and score >= 0.30
        )

        state.upsert_kaggle_item(item)

        results.append(item)

    results.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return {
        "discovered": len(results),
        "interesting": [
            x for x in results
            if x.get("interesting")
        ],
        "items": results,
    }


def run(prompt="Show the most interesting Kaggle competitions, datasets, and notebooks."):
    agent = needle.Needle(
        tools=[interesting_items],
        system=(
            "You are Kaggle Needle. Present the most interesting Kaggle "
            "competitions, datasets, and notebooks returned by your tool. "
            "Keep it concise: include the kind, title, and URL. Do not "
            "invent items."
        ),
    )

    return render(agent.run(prompt))


def build_digest(items):
    if not items:
        return "No new interesting Kaggle items."

    lines = [
        "🏆 Kaggle — High-signal items",
        "",
    ]

    icons = {
        "competition": "🏁",
        "dataset": "📦",
        "notebook": "📓",
    }

    for i, item in enumerate(items, 1):
        kind = item.get("kind", "")
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        score = item.get("score", 0)
        reason = item.get("reason") or ""

        lines.append(
            f"{icons.get(kind, '•')} {i}. [{kind}] {title}"
        )

        lines.append(
            f"   Score: {float(score):.3f}"
        )

        if reason:
            lines.append(f"   {reason}")

        if url:
            lines.append(f"   {url}")

        lines.append("")

    return "\n".join(lines).strip()
