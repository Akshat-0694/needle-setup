import re

import needle
from pydantic import BaseModel, Field

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
def arxiv_discover(
    query: str = "cat:cs.LG OR cat:cs.AI OR cat:cs.CL OR cat:cs.DC",
    limit: int = 20,
    days: int = 7,
) -> list[dict]:
    """Discover recent arXiv papers."""
    return call(
        "arxiv_discover",
        query=query,
        limit=limit,
        days=days,
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
# arXiv paper curation
# ============================================================

class PaperDecision(BaseModel):
    """
    Deliberately simple schema.

    Needle 2.0.10 reliably handles basic Pydantic schemas,
    while constrained JSON schemas were observed to return None.
    Numerical validation therefore happens in Python.
    """

    interesting: bool
    reason: str
    signals: list[str]


_TECHNICAL_SIGNALS = {
    "llm": (
        "large language model",
        "language model",
        "llm",
        "foundation model",
    ),
    "inference": (
        "inference",
        "serving",
        "generation",
        "decoding",
    ),
    "cuda": (
        "cuda",
        "gpu",
        "kernel",
        "triton",
        "flashattention",
        "flash attention",
    ),
    "optimization": (
        "optimization",
        "optimisation",
        "efficient",
        "efficiency",
        "latency",
        "throughput",
        "memory efficiency",
    ),
    "systems": (
        "systems",
        "runtime",
        "compiler",
        "distributed",
        "parallel",
        "scheduling",
    ),
    "architecture": (
        "architecture",
        "attention",
        "transformer",
        "mixture of experts",
        "moe",
        "state space model",
        "ssm",
    ),
    "agents": (
        "agent",
        "agents",
        "tool use",
        "reasoning",
        "planning",
    ),
    "training": (
        "training",
        "pretraining",
        "fine-tuning",
        "finetuning",
        "reinforcement learning",
        "post-training",
    ),
}


def _paper_text(paper):
    title = str(
        paper.get("title")
        or ""
    )

    abstract = str(
        paper.get("abstract")
        or paper.get("description")
        or ""
    )

    return (
        f"Title: {title}\n\n"
        f"Abstract: {abstract}"
    )


def _technical_signals(paper):
    text = _paper_text(paper).lower()

    found = []

    for category, terms in _TECHNICAL_SIGNALS.items():
        if any(term in text for term in terms):
            found.append(category)

    return found


def _deterministic_paper_score(paper):
    """
    Numerical score is owned by Python.

    Needle only provides semantic judgment.
    """

    signals = _technical_signals(paper)

    score = 0.0

    # Broad technical relevance.
    score += min(
        0.40,
        0.08 * len(signals),
    )

    # Stronger systems/infrastructure signals.
    strong = {
        "inference",
        "cuda",
        "optimization",
        "systems",
    }

    score += min(
        0.25,
        0.08 * len(
            set(signals) & strong
        ),
    )

    # Research architecture/training signals.
    if "architecture" in signals:
        score += 0.10

    if "training" in signals:
        score += 0.05

    if "agents" in signals:
        score += 0.05

    # Strong title/abstract technical indicators.
    text = _paper_text(paper).lower()

    high_signal_terms = (
        "flashattention",
        "pagedattention",
        "mixture of experts",
        "moe",
        "cuda kernel",
        "gpu kernel",
        "inference optimization",
        "distributed training",
        "distributed inference",
        "compiler",
        "runtime",
    )

    if any(
        term in text
        for term in high_signal_terms
    ):
        score += 0.15

    return max(
        0.0,
        min(1.0, score),
    )


def classify_paper(paper):
    """
    Classify one arXiv candidate with Needle.

    This function intentionally has NO network tools.
    The model sees only the candidate metadata.
    """

    signals = _technical_signals(paper)
    deterministic_score = _deterministic_paper_score(
        paper
    )

    # Cheap deterministic rejection.
    #
    # A paper with no relevant technical signal does not
    # need an expensive semantic classification.
    if not signals:
        return {
            "interesting": False,
            "score": deterministic_score,
            "reason": "No configured AI-systems technical signals found.",
            "signals": [],
            "model_used": False,
        }

    agent = needle.Needle(
        tools=[],
        system="""
You are Research Needle, an AI systems research curator.

Your job is to decide whether an arXiv paper is genuinely
interesting to a technical researcher working on:

- LLM systems
- inference
- GPU/CUDA
- kernels
- optimization
- ML systems
- distributed systems
- compilers
- runtimes
- model architecture
- training infrastructure
- agents

You receive ONLY the paper title, abstract, and deterministic
technical signals.

Do not invent facts.
Do not invent benchmarks.
Do not invent repositories.
Do not invent papers.
Do not invent numerical results.

interesting=True means the supplied abstract contains a
substantial technical contribution or meaningful technical
development relevant to the areas above.

interesting=False means the paper is merely adjacent, generic,
or insufficiently relevant.

The reason must explain the decision using evidence present
in the supplied title or abstract.

signals should contain only concrete technical concepts
supported by the supplied text.
""",
    )

    prompt = f"""
Classify this arXiv paper.

TITLE:
{paper.get("title", "")}

ABSTRACT:
{paper.get("abstract", paper.get("description", ""))}

DETERMINISTIC TECHNICAL SIGNALS:
{signals}

DETERMINISTIC BASE SCORE:
{deterministic_score:.3f}

Return the structured decision.
"""

    try:
        decision = agent.extract(
            prompt,
            PaperDecision,
            max_new_tokens=256,
        )

    except Exception as exc:
        return {
            "interesting": False,
            "score": deterministic_score,
            "reason": (
                "Needle classification failed: "
                f"{type(exc).__name__}: {exc}"
            ),
            "signals": signals,
            "model_used": False,
            "classification_error": True,
        }

    if decision is None:
        return {
            "interesting": False,
            "score": deterministic_score,
            "reason": "Needle returned no classification.",
            "signals": signals,
            "model_used": False,
            "classification_error": True,
        }

    # --------------------------------------------------------
    # Normalize model output.
    # --------------------------------------------------------

    interesting = bool(
        decision.interesting
    )

    reason = str(
        decision.reason or ""
    ).strip()

    model_signals = []

    for signal in (
        decision.signals or []
    ):
        signal = str(signal).strip()

        if signal and signal not in model_signals:
            model_signals.append(signal)

    # Never allow the model to create the numerical score.
    final_score = deterministic_score

    # Semantic confirmation gives a controlled bonus.
    if interesting:
        final_score += 0.20
    else:
        final_score -= 0.15

    # Clamp ourselves.
    final_score = max(
        0.0,
        min(1.0, final_score),
    )

    # A semantic "interesting" decision without any
    # deterministic signal is not trusted.
    if not signals:
        interesting = False
        final_score = 0.0

    return {
        "interesting": interesting,
        "score": final_score,
        "reason": reason,
        "signals": (
            model_signals
            or signals
        ),
        "deterministic_signals": signals,
        "deterministic_score": deterministic_score,
        "model_used": True,
    }



def _normalize_arxiv_decision(decision, paper):
    """
    Normalize common structural-token failures from local Needle.

    Needle.extract() is responsible only for the semantic decision.
    Python validates and cleans the returned fields before persistence.
    """

    title = str(
        paper.get("title") or ""
    ).strip()

    reason = str(
        getattr(decision, "reason", "") or ""
    ).strip()

    technical_area = str(
        getattr(decision, "technical_area", "") or ""
    ).strip()

    bad_reason_values = {
        "",
        title,
        "TITLE:",
        "ABSTRACT:",
        "CATEGORIES:",
        "DETERMINISTIC SCORE:",
        "DETERMINISTIC SIGNALS:",
    }

    bad_area_values = {
        "",
        "TITLE:",
        "ABSTRACT:",
        "CATEGORIES:",
        "DETERMINISTIC SCORE:",
        "DETERMINISTIC SIGNALS:",
    }

    if reason in bad_reason_values:
        signals = paper.get(
            "signals",
            paper.get("deterministic_signals", []),
        )

        if isinstance(signals, (list, tuple, set)):
            signal_text = ", ".join(
                str(x) for x in signals
                if str(x).strip()
            )
        else:
            signal_text = str(signals or "").strip()

        if signal_text:
            reason = (
                "The paper contains technical signals relevant "
                f"to AI systems: {signal_text}."
            )
        else:
            reason = (
                "The paper contains a technical contribution "
                "relevant to the configured AI-systems research scope."
            )

    if technical_area in bad_area_values:
        categories = paper.get("categories", [])

        if isinstance(categories, (list, tuple, set)):
            category_text = " ".join(
                str(x) for x in categories
            ).lower()
        else:
            category_text = str(categories or "").lower()

        if any(
            x in category_text
            for x in ("cs.lg", "cs.ai", "cs.cl")
        ):
            technical_area = "Machine Learning / AI"
        elif "cs.dc" in category_text:
            technical_area = "Distributed Systems"
        else:
            technical_area = "AI Systems"

    return reason, technical_area



# ============================================================
# Deterministic arXiv relevance scorer
# ============================================================

ARXIV_POSITIVE_SIGNALS = {
    # Model architecture
    "large language model": 8,
    "language model": 5,
    "transformer": 6,
    "attention": 4,
    "mixture of experts": 8,
    "moe": 6,

    # Inference / serving
    "inference": 8,
    "serving": 7,
    "speculative decoding": 10,

    # GPU / systems
    "cuda": 10,
    "gpu": 8,
    "kernel": 9,
    "triton": 9,
    "compiler": 8,
    "distributed": 7,

    # ML systems / efficiency
    "quantization": 7,
    "memory": 5,
    "optimization": 6,
    "efficient": 4,
    "systems": 6,
    "benchmark": 3,

    # Agents / training
    "agent": 5,
    "agents": 5,
    "reinforcement learning": 5,
    "post-training": 6,
    "fine-tuning": 5,
}

ARXIV_NEGATIVE_SIGNALS = {
    "survey": -8,
    "tutorial": -8,
    "position paper": -8,
    "review": -7,
    "perspective": -7,
}


def score_arxiv_paper(paper):
    """
    Deterministic first-pass arXiv relevance score.

    The score represents technical relevance evidence, not
    model confidence or probability.

    Strong systems/architecture signals receive substantially
    more weight than generic ML terminology.
    """

    categories = paper.get("categories", [])

    if isinstance(categories, (list, tuple, set)):
        categories_text = " ".join(
            str(x) for x in categories
        )
    else:
        categories_text = str(categories or "")

    title = str(
        paper.get("title", "") or ""
    )

    abstract = str(
        paper.get("abstract", "") or ""
    )

    text = " ".join([
        title,
        abstract,
        categories_text,
    ]).lower()

    raw = 0.0
    signals = []

    for term, weight in ARXIV_POSITIVE_SIGNALS.items():
        if term in text:
            raw += weight
            signals.append(term)

    for term, weight in ARXIV_NEGATIVE_SIGNALS.items():
        if term in text:
            raw += weight
            signals.append(
                "negative:" + term
            )

    # --------------------------------------------------------
    # Title bonus
    #
    # A technical term appearing in the title is stronger
    # evidence than the same term appearing incidentally
    # in an abstract.
    # --------------------------------------------------------

    title_text = title.lower()

    title_bonus = 0.0

    for term in (
        "transformer",
        "attention",
        "inference",
        "serving",
        "cuda",
        "gpu",
        "kernel",
        "triton",
        "compiler",
        "distributed",
        "quantization",
        "speculative decoding",
        "mixture of experts",
        "moe",
        "agent",
        "agents",
    ):
        if term in title_text:
            title_bonus += 3.0

    raw += title_bonus

    # --------------------------------------------------------
    # Category bonus
    #
    # cs.LG / cs.AI / cs.CL / cs.DC are useful discovery
    # categories but are deliberately weak evidence.
    # --------------------------------------------------------

    categories_lower = categories_text.lower()

    if any(
        category in categories_lower
        for category in (
            "cs.lg",
            "cs.ai",
            "cs.cl",
            "cs.dc",
        )
    ):
        raw += 1.0

    # --------------------------------------------------------
    # Normalize.
    #
    # 30 is the promotion-oriented reference point rather
    # than a probabilistic interpretation.
    # --------------------------------------------------------

    score = max(
        0.0,
        min(
            1.0,
            raw / 30.0,
        ),
    )

    return round(score, 3), signals


class ArxivCurationDecision(BaseModel):
    """
    Semantic decision made by the local Research Needle.

    Identity, ranking and persistence are deliberately handled
    by deterministic Python code.
    """

    interesting: bool = Field(
        description=(
            "True only when the paper contains a substantial "
            "technical contribution relevant to AI systems."
        )
    )

    reason: str = Field(
        description=(
            "Concise technical explanation supporting the "
            "interesting/not-interesting decision."
        )
    )

    technical_area: str = Field(
        description=(
            "Primary technical area, for example GPU systems, "
            "CUDA, inference, distributed systems, agents, "
            "machine learning, compilers, or NLP."
        )
    )


def curate_arxiv_papers(
    papers=None,
    limit=20,
    query="cat:cs.LG OR cat:cs.AI OR cat:cs.CL OR cat:cs.DC",
    days=7,
):
    """
    Curate arXiv papers using deterministic relevance scoring.

    Architecture:

        arxiv_discover()
            ->
        deterministic scoring
            ->
        deterministic filtering
            ->
        persistence
            ->
        ranking

    Needle is deliberately NOT authoritative for the
    interesting/not-interesting decision.

    This prevents malformed or hallucinated structured
    model output from changing research selection.
    """

    # --------------------------------------------------------
    # STEP 1 — Discovery
    # --------------------------------------------------------

    if papers is None:
        discovered = arxiv_discover(
            query=query,
            limit=limit,
            days=days,
        )
    else:
        discovered = papers

    if not discovered:
        return {
            "discovered": 0,
            "interesting": 0,
            "papers": [],
        }

    # --------------------------------------------------------
    # STEP 2 — Deterministic scoring
    # --------------------------------------------------------

    candidates = []

    for paper in discovered:

        deterministic_score, signals = (
            score_arxiv_paper(paper)
        )

        item = dict(paper)

        item["deterministic_score"] = float(
            deterministic_score
        )

        item["signals"] = signals

        # Needle fields remain present for schema compatibility.
        item["needle_score"] = None
        item["needle_interesting"] = None

        candidates.append(item)

        # Persist discovery immediately.
        state.upsert_research_paper(item)

    # --------------------------------------------------------
    # STEP 3 — Deterministic curation
    # --------------------------------------------------------

    final = []

    for item in candidates:

        deterministic_score = float(
            item.get(
                "deterministic_score",
                0.0,
            )
        )

        signals = item.get(
            "signals",
            [],
        )

        # No technical signal means no reason to spend
        # downstream research effort on the paper.
        if deterministic_score <= 0.0:
            interesting = False

            reason = (
                "No configured AI-systems technical "
                "relevance signals were found."
            )

            technical_area = ""

        # Strong deterministic relevance.
        elif deterministic_score >= 0.30:
            interesting = True

            reason = (
                "Deterministic technical relevance signals: "
                + ", ".join(
                    str(x) for x in signals
                )
                + "."
            )

            technical_area = (
                _infer_arxiv_technical_area(
                    signals
                )
            )

        # Borderline papers are retained in the database but
        # are not promoted into the interesting set.
        else:
            interesting = False

            reason = (
                "Technical signals were detected, but the "
                "deterministic relevance score is below "
                "the curation threshold."
            )

            technical_area = (
                _infer_arxiv_technical_area(
                    signals
                )
            )

        item["needle_score"] = None
        item["needle_interesting"] = None

        item["score"] = round(
            deterministic_score,
            3,
        )

        item["interesting"] = interesting
        item["reason"] = reason
        item["technical_area"] = technical_area

        state.upsert_research_paper(item)

        if interesting:
            final.append(item)

    # --------------------------------------------------------
    # STEP 4 — Ranking
    # --------------------------------------------------------

    final.sort(
        key=lambda x: (
            x.get("score", 0.0),
            x.get("deterministic_score", 0.0),
        ),
        reverse=True,
    )

    return {
        "discovered": len(discovered),
        "interesting": len(final),
        "papers": final,
    }


def _infer_arxiv_technical_area(signals):
    """
    Convert deterministic signal matches into a concise
    technical area.

    This is intentionally rule-based and cannot invent
    information.
    """

    signals = {
        str(x).lower()
        for x in (signals or [])
    }

    if signals & {
        "cuda",
        "gpu",
        "kernel",
        "triton",
    }:
        return "GPU Systems"

    if signals & {
        "inference",
        "serving",
        "speculative decoding",
    }:
        return "Inference"

    if signals & {
        "distributed",
    }:
        return "Distributed Systems"

    if signals & {
        "compiler",
    }:
        return "Compilers"

    if signals & {
        "agent",
        "agents",
    }:
        return "Agents"

    if signals & {
        "mixture of experts",
        "moe",
    }:
        return "Mixture-of-Experts"

    if signals & {
        "transformer",
        "attention",
        "large language model",
        "language model",
    }:
        return "Model Architecture"

    if signals & {
        "quantization",
        "optimization",
        "efficient",
    }:
        return "Efficient ML"

    if signals & {
        "reinforcement learning",
        "post-training",
        "fine-tuning",
    }:
        return "Training / Post-Training"

    if signals:
        return "Machine Learning / AI"

    return ""

def interesting_arxiv_papers(limit=20):
    return state.interesting_research_papers(
        limit
    )


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



# ============================================================
# arXiv Research Needle entry point
# ============================================================

def run_arxiv_research(limit=10):
    """
    Discover and curate arXiv papers.

    Discovery remains deterministic through the MCP capability.
    Semantic selection is handled by Needle.extract().
    """

    papers = call(
        "arxiv_discover",
        limit=limit,
    )

    if not isinstance(papers, list):
        return {
            "ok": False,
            "error": "arxiv_discover did not return a list.",
            "discovered": 0,
            "classified": 0,
            "interesting": 0,
            "papers": [],
        }

    result = curate_arxiv_papers(
        papers
    )

    return {
        "ok": True,
        **result,
    }
