# Needle Daily V2

Personal multi-agent runtime around Cactus Needle 2 and MCP.

## Agents
- Task Needle: tasks/reminders
- Blog Needle: industry blog discovery + curation
- Opportunity Needle: network-intelligence over imported/approved LinkedIn profile data
- Research Needle: public web research via Jina Reader
- GitHub Needle: read-only `gh` capabilities
- Morning Needle: cross-domain briefing
- Telegram transport + scheduler

## Architecture
```text
Telegram -> Router -> specialized Needle -> MCP capability server -> state/APIs
                                      \-> Notification / scheduler -> Telegram
```

MCP is the capability boundary; Needle remains the reasoning/tool-selection layer. The official Python SDK supports MCP servers/clients and Streamable HTTP; this repo uses that pattern.

## Important LinkedIn constraint
Opportunity Needle does NOT scrape LinkedIn, automate login, send connection requests, or message people. Import profile records from an approved API/export/your own dataset, then enrich/rank them.

## Start
```bash
cp .env.example .env
chmod +x scripts/*.sh
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/health
```

For Telegram set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

## Commands
`/tasks`, `/done <id>`, `/blogs`, `/people`, `/morning`

Natural language is routed to a specialized Needle.
