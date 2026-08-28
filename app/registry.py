from app.agents import research, system, morning

AGENTS = {
    "research": research.run,
    "system": system.run,
    "morning": lambda prompt: morning.run(),
}

def run(agent: str, prompt: str):
    if agent not in AGENTS:
        raise ValueError(f"Unknown agent: {agent}")
    return AGENTS[agent](prompt)
