# Needle Daily V2

Personal multi-agent runtime around Cactus Needle 2 and MCP. Runs on a server (EC2 / VPS / your own box) and notifies you on Telegram.

## Needles

| Needle | What it does | Trigger |
|---|---|---|
| **Morning** | Pings you each morning (default `08:30`, configurable) with the day's tasks, Notion calendar/ideas, industry reads, GitHub projects, research and network opportunities | Scheduled + `/morning` |
| **Task** | Manage tasks and reminders from natural language | Any message + `/tasks`, `/done <id>`, `/remove <id>`, `/delete <id>` |
| **Calendar** | Your own calendar: add events, list upcoming, remove | `/calendar`, `/calendar add …`, `/remove_event <id>` |
| **Ideas** | Capture and organize ideas | `/ideas`, `/ideas add …`, `/idea done <id>`, `/remove_idea <id>` |
| **GitHub** | Read-only `gh` CLI: trending open source + research implementations | `/github …` or keywords + scheduled |
| **Info** | General web browsing via Jina Reader, plus arXiv discovery | `research …`, `look up …` |
| **Hugging Face** | Discovers and curates high-signal models (vLLM, speculative decoding, CUDA, quantization, …) | Scheduled |
| **Kaggle** | Discovers active competitions, datasets, notebooks via the Kaggle API | Scheduled + `/kaggle` |
| **LinkedIn** | Ranks your imported/approved network profiles for genuine conversations | `/people`, `/linkedin …` |
| **Opportunity** | Watches a list of opportunities you add and notifies you when one becomes available | `/add_opportunity <url> <title>`, `/opportunities`, scheduled |
| **Blog / Industry news** | Curates high-signal industry reads from your RSS feeds | `/blogs` + scheduled |
| **Research / arXiv** | Deterministically discovers + curates arXiv papers and sends digests | Scheduled |
| **Gmail Spam** | Scans your inbox (IMAP, app password), moves clearly-spam mail to Gmail's Spam folder and pings you with what it did | `/spam`, `/spam scan`, scheduled |
| **Server Health** | System load/memory/disk/uptime, service status (MCP/Telegram/Notion/Gmail), DB stats and last scheduler runs | `/health` or `/status` |

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

`/health` (or `/status`), `/tasks`, `/done <id>`, `/remove <id>`,
`/delete <id>`, `/calendar`, `/calendar add <event>`, `/remove_event <id>`,
`/ideas`, `/ideas add <idea>`, `/idea done <id>`, `/remove_idea <id>`,
`/blogs`, `/people`, `/opportunities`,
`/add_opportunity <url> <title>`, `/remove_opportunity <id>`,
`/spam`, `/spam scan`, `/morning`.

Natural language is routed to the matching Needle (tasks, calendar, ideas,
github, blog, linkedin, opportunity, research, spam, health). Relative dates
in calendar events ("tomorrow", "next monday", "in 3 days") are resolved
automatically.

## Calendar & Ideas

Both are local to the server (SQLite), so they work without Notion.

- **Calendar**: `/calendar` lists the next 7 days. `/calendar add gym
  session tomorrow at 7am` schedules it — dates/times are extracted and
  relative dates resolved automatically. `/remove_event <id>` removes one.
  Today's/upcoming events appear in the morning briefing.
- **Ideas**: `/ideas` lists open ideas. `/ideas add <idea>` captures one,
  `/idea done <id>` or `/ideas done <id>` marks it done,
  `/remove_idea <id>` deletes it.
- **Tasks**: `/done <id>` completes a task (it disappears from `/tasks`),
  `/remove <id>` or `/delete <id>` permanently removes it.

## Gmail spam needle

Requires `GMAIL_EMAIL` and `GMAIL_APP_PASSWORD` (Google Account → Security →
2-Step Verification → App passwords, with IMAP enabled in Gmail settings).

- Every `GMAIL_SCAN_HOURS` (default 3) the scheduler scans recent inbox mail.
- It only auto-moves mail that is *clearly* bulk/automated spam (multiple
  strong signals: `List-Unsubscribe` + a marketing sender, or high-precision
  spam/phishing phrases). Newsletters alone are not moved.
- Nothing is deleted — moving to Gmail's Spam folder is reversible.
- `GMAIL_SPAM_WHITELIST` (comma-separated emails/domains) is always respected.
- You get a Telegram digest of what was moved, plus a separate "suspicious"
  list that is left in your inbox for you to judge.

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
  Kaggle + opportunity checks every 6 hours; Gmail spam scan every
  `GMAIL_SCAN_HOURS`; morning brief once a day at `MORNING_TIME`.
- Setting `ALLOW_SIDE_EFFECTS=true` enables side-effecting tools.

## One-shot EC2 setup (t3.micro)

Everything below you run **once, in a terminal after `ssh`ing into the
instance**. `docker compose up -d` starts all services in the background and
they keep running after you close the terminal; `restart: unless-stopped`
even brings them back after a reboot. Copy-paste block by block:

```bash
# 1) SSH in (from your laptop)
ssh -i ~/.ssh/your-key.pem ubuntu@<your-ec2-public-ip>

# 2) Install Docker + the compose plugin
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
newgrp docker            # apply group membership in this session

# 3) t3.micro has only 1 GB RAM — add a little swap so the needle
#    engine + containers don't get OOM-killed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 4) Get the code
git clone <your-repo-url> needle-setup
cd needle-setup

# 5) Configure
cp .env.example .env
nano .env                 # fill in TELEGRAM_*, NOTION_*, GITHUB_TOKEN, KAGGLE_*, GMAIL_*, …

# 6) Build and start everything in the background
docker compose up -d --build

# 7) Check it's healthy, then you can close the terminal — it keeps running
curl -s http://127.0.0.1:8000/health && echo
docker compose ps
docker compose logs -f scheduler telegram     # press Ctrl-C to stop watching logs
```

That's it. After step 7 you can disconnect — the API, scheduler, Telegram
bot and all needles run in the background on the server.

### Useful admin commands

```bash
docker compose ps                  # see running services
docker compose logs -f scheduler   # watch the scheduler
docker compose logs -f telegram    # watch the Telegram bot
docker compose restart scheduler   # restart one service
docker compose down                # stop everything
docker compose up -d --build       # rebuild + restart after pulling new code
```

To check on it from Telegram later, send `/health` to your bot — it reports
load, memory, disk, service status, DB stats and the last run of every job.
