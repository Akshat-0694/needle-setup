# Needle Daily V2

Personal multi-agent runtime around Cactus Needle 2 and MCP. Runs on a server (EC2 / VPS / your own box) and notifies you on Telegram.

## Needles

| Needle | What it does | Trigger |
|---|---|---|
| **Morning** | Pings you each morning (default `08:30`, configurable) with the day's tasks, Notion calendar/ideas, industry reads, GitHub projects, research and network opportunities | Scheduled + `/morning` |
| **Task** | Manage tasks and reminders from natural language | Any message + `/tasks`, `/done <id>` |
| **Calendar / Ideas** | Reads your Notion workspace (search + read pages) | Part of Morning brief, and available via `/morning` |
| **GitHub** | Read-only `gh` CLI: trending open source + research implementations | `/github …` or keywords + scheduled |
| **Info** | General web browsing via Jina Reader, plus arXiv discovery | `research …`, `look up …` |
| **Hugging Face** | Discovers and curates high-signal models (vLLM, speculative decoding, CUDA, quantization, …) | Scheduled |
| **Kaggle** | Discovers active competitions, datasets, notebooks via the Kaggle API | Scheduled + `/kaggle` |
| **LinkedIn** | Ranks your imported/approved network profiles for genuine conversations | `/people`, `/linkedin …` |
| **Opportunity** | Watches a list of opportunities you add and notifies you when one becomes available | `/add_opportunity <url> <title>`, `/opportunities`, scheduled |
| **Blog / Industry news** | Curates high-signal industry reads from your RSS feeds | `/blogs` + scheduled |
| **Research / arXiv** | Deterministically discovers + curates arXiv papers and sends digests | Scheduled |

All scheduled discoveries notify you on Telegram. Blog/GitHub/Research/HF/Kaggle items are also persisted into Notion as child pages (one page per item, under a configurable parent page per needle).

## Architecture

```text
Telegram  ->  Router  ->  specialized Needle  ->  MCP capability server  ->  state / APIs
                                          \->  Scheduler / notifications ->  Telegram
```

- **MCP** (`app/mcp/server.py`) is the capability boundary: DB access, RSS fetch, Jina reader, arXiv, HF, Kaggle, opportunities.
- **Needle agents** (`app/agents/*.py`) do tool selection/reasoning on top of Cactus Needle 2 (a local compiled inference engine — no API key, no network dependency after first-run engine download).
- **State** is a SQLite database at `DATA_DIR/needle.db` (mounted volume).

## Setup

```bash
cp .env.example .env
# edit .env — at minimum:
#   TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID   (notifications)
#   NOTION_TOKEN, NOTION_MCP_AUTH_TOKEN    (Notion)
#   GITHUB_TOKEN                           (GitHub needle)
#   KAGGLE_USERNAME, KAGGLE_KEY            (Kaggle needle, optional)
#   JINA_API_KEY, HF_TOKEN                 (optional, rate limits)
chmod +x scripts/*.sh
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/health
```

> Notion: the needle persistence uses parent page IDs in `.env`
> (`NOTION_PARENT_GITHUB`, `NOTION_PARENT_BLOG`, `NOTION_PARENT_RESEARCH`).
> Create a page per needle in your Notion workspace and put its 32-char page
> ID there. All three default to one shared page so it works out of the box.
> Blog RSS feeds live in `data/sources.json`.

## Telegram commands

`/tasks`, `/done <id>`, `/blogs`, `/people`, `/opportunities`,
`/add_opportunity <url> <title>`, `/remove_opportunity <id>`, `/morning`.

Natural language is routed to the matching Needle (tasks, github, blog,
linkedin, opportunity, research).

## Deploying to EC2

1. **Create an instance** — Ubuntu 22.04/24.04, `t3.medium` or bigger
   (the Cactus Needle inference engine needs a bit of RAM; ~1 GB+).
   In the security group open SSH (22) and optionally TCP 8000 if you want
   the API reachable directly.
2. **Install Docker + Compose plugin** on the instance:
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose-v2
   sudo usermod -aG docker $USER
   # log out and back in (or: newgrp docker)
   ```
3. **Get the code** (replace with your repo):
   ```bash
   git clone https://github.com/<you>/needle-setup.git && cd needle-setup
   ```
4. **Configure**:
   ```bash
   cp .env.example .env
   nano .env        # fill in tokens (Telegram, Notion, GitHub, Kaggle…)
   ```
5. **Run**:
   ```bash
   docker compose up -d --build
   docker compose ps
   curl http://127.0.0.1:8000/health
   docker compose logs -f scheduler telegram
   ```
6. **First run** — each container that uses the Needle engine downloads it
   from Hugging Face once (~a few seconds) into a shared `needle-cache`
   volume, then everything runs locally.

The API binds to `127.0.0.1:8000` by default (reachable via an SSH tunnel:
`ssh -L 8000:127.0.0.1:8000 ubuntu@<ec2-ip>`). To expose it publicly, change
the port mapping in `docker-compose.yml` to `"8000:8000"` and open port 8000
in the security group.

## Notes / constraints

- **LinkedIn**: never scrapes LinkedIn or automates outreach — it ranks
  profiles you import/approve.
- **Scheduler cadence**: blog + GitHub every 15 min; arXiv + Hugging Face +
  Kaggle + opportunity checks every 6 hours; morning brief once a day at
  `MORNING_TIME`.
- Setting `ALLOW_SIDE_EFFECTS=true` enables side-effecting tools.
