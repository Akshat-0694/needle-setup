# Needle Daily

An always-on personal task system using Cactus Needle 2 as the tiny tool-calling model.

Official Needle:
https://github.com/cactus-compute/needle

Needle 2 provides the model/tool-calling layer. This repository provides the personal-agent layer around it:
- task scheduler
- local task state
- agent registry
- safe read-only daily agents
- FastAPI control API
- logs
- Docker deployment

## Current agents

### Morning Brief
Runs on schedule and collects:
- current time
- local system health
- configured tasks

It is deliberately deterministic first. Needle is used where tool selection/reasoning is useful.

### Research
Accepts a natural-language question and lets Needle choose from a small research tool surface.

### System
Reports CPU, memory and disk information.

## Safety model

V0 is read-only.

No:
- email sending
- shell execution by the model
- arbitrary filesystem writes
- GitHub writes
- financial actions
- browser automation

Those should be added only behind explicit approval and permissions.

## EC2: Amazon Linux 2023

Install Docker:

```bash
sudo dnf update -y
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
```

Log out and back in.

Verify:

```bash
docker --version
```

If Docker Compose is unavailable, install the Compose plugin using the current Docker/Amazon Linux instructions rather than downloading an untrusted binary.

## Local Python test

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python -m app.cli doctor
python -m app.cli run "Give me a morning brief"
```

The first Needle invocation downloads/caches its inference engine.

## Docker

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f
```

Health:

```bash
curl http://127.0.0.1:8000/health
```

Create a task:

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"agent":"research","prompt":"Explain what CUDA unified memory is."}'
```

List tasks:

```bash
curl http://127.0.0.1:8000/tasks
```

## Scheduling

The default schedule is configured in `app/config.py`.

The morning brief defaults to 08:00 in `TIMEZONE`.

## Adding a Needle agent

Create a module under `app/agents/`.

Each agent should:
1. expose a small tool surface
2. instantiate `needle.Needle(...)`
3. keep tools narrow
4. return structured results
5. avoid side effects unless explicitly permitted

Example:

```python
import needle

@needle.tool
def get_something(query: str):
    """Read something from a safe source."""
    return {"query": query}

agent = needle.Needle(tools=[get_something])
```

Needle's documented API supports `Needle(tools=...)`, `agent.run(...)`, tool decorators, confidence gating and tool retrieval. See the official API docs.

## Design principle

Do not make every task an LLM task.

Use:

deterministic trigger -> deterministic collection -> Needle reasoning/tool selection -> structured result

This keeps the system cheap, debuggable and safe.
