import needle

from app.mcp.client import call
from app.agents.util import render


@needle.tool
def candidates(limit: int = 50):
    """Get imported unscored network profiles."""
    return call("linkedin_candidates", limit=limit)


@needle.tool
def save_score(
    profile_url: str,
    score: float,
    interesting: bool,
    reason: str,
    conversation_hook: str,
):
    """Save a profile score and a concrete conversation hook."""
    return call(
        "linkedin_save_score",
        profile_url=profile_url,
        score=score,
        interesting=interesting,
        reason=reason,
        conversation_hook=conversation_hook,
    )


def run(prompt):
    agent = needle.Needle(
        tools=[candidates, save_score],
        system=(
            "You are LinkedIn Needle. Rank approved/imported network "
            "profiles for genuine professional conversations. Favor "
            "technical depth, strong evidence of building/research/open "
            "source, relevance to AI/ML systems/CUDA/GPU/inference, "
            "trajectory and a concrete conversation hook. Do not infer "
            "private facts or automate outreach. Score 0..1."
        ),
    )
    return render(agent.run(prompt))
