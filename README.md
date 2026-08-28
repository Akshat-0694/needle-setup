# Needle V0

A small always-on personal-agent platform for an EC2 instance.

## What V0 contains

- FastAPI Hub
- Redis task queues
- SQLite persistent event log
- Independent Needle worker containers
- Watcher Needle
- Researcher Needle
- Docker Compose deployment
- Optional OpenAI-compatible LLM endpoint

## Architecture

You -> Hub -> per-Needle queue -> Needle -> event bus -> event log

The Hub is the control plane. Needles are workers.

## 1. EC2 prerequisites

Recommended starting point:

- Ubuntu 24.04 LTS
- 2+ vCPU
- 4+ GB RAM
- 20+ GB disk
- SSH access
- AWS security group allowing SSH only from your IP

Do NOT expose port 8000 to the public internet.

## 2. Install Docker

On the EC2 machine:

```bash
git clone <your-repository>
cd needle
chmod +x scripts/*.sh
./scripts/bootstrap-ubuntu.sh
```

Log out and back in.

Verify:

```bash
docker --version
docker compose version
```

## 3. Configure environment

```bash
cp .env.example .env
nano .env
```

For V0, you can leave the LLM fields empty.

## 4. Start

```bash
./scripts/start.sh
```

Check:

```bash
docker compose ps
curl http://127.0.0.1:8000/health
```

## 5. Smoke test

```bash
./scripts/test.sh
```

You should see a `research.completed` event.

## 6. Submit a research task

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"needle":"researcher","payload":{"question":"What is a CUDA warp?"}}'
```

Then:

```bash
curl http://127.0.0.1:8000/events
```

## 7. Configure an LLM

The researcher accepts an OpenAI-compatible endpoint.

Set:

```env
LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=your-key
LLM_MODEL=your-model
```

Then restart:

```bash
docker compose up -d --build
```

You can also point this at any OpenAI-compatible local/self-hosted inference server reachable from the EC2 container.

## 8. Watch a URL

Submit:

```bash
./scripts/submit-watch.sh https://example.com
```

The event will contain the HTTP status and SHA-256 content hash.

For actual change monitoring, persist the previous hash and submit it on the next check. V0 intentionally leaves scheduling/stateful monitoring as the next architectural step.

## 9. Logs

```bash
./scripts/logs.sh
```

Or:

```bash
docker compose logs -f hub
docker compose logs -f watcher
docker compose logs -f researcher
```

## 10. Stop

```bash
./scripts/stop.sh
```

## Security notes

V0 is intentionally not production-grade.

Before giving agents write access to email, GitHub, shell, browser, files, etc., add:

1. authentication for the Hub
2. per-Needle tool permissions
3. secrets management
4. isolated tool execution
5. approval gates for consequential actions
6. audit logs
7. rate limits
8. retry/dead-letter handling
9. resource limits per container

Do not give an LLM unrestricted shell access.

## Next milestones

V1:
- PostgreSQL
- scheduler
- persistent watcher state
- agent registry
- notification Needle

V2:
- GitHub Needle
- Calendar Needle
- Email Needle
- Web Research Needle
- memory service

V3:
- permission engine
- human approval workflow
- tool sandbox
- observability
- automatic retries

V4:
- Hub-level planning
- event-driven multi-Needle workflows
- long-term memory
- cost/latency budgets
