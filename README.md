# Needle Daily V1
Personal task automation using Cactus Needle 2.0.10.

## Services
- app: FastAPI control API + Task Needle
- scheduler: reminder checker
- telegram: Telegram polling transport
- SQLite: persistent tasks/events

## Amazon Linux 2023
```bash
sudo dnf install -y docker git curl
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
```
Log out and back in.

## Configure
```bash
cp .env.example .env
nano .env
```

Set `TELEGRAM_BOT_TOKEN` from @BotFather. Set `TELEGRAM_CHAT_ID` to your numeric chat ID. Never commit `.env`.

## Start
```bash
./scripts/start.sh
curl http://127.0.0.1:8000/health
```

## Test Task Needle
```bash
curl -X POST http://127.0.0.1:8000/message   -H 'Content-Type: application/json'   -d '{"text":"Add finish my CUDA kernel to my tasks."}'
```

Then:
```bash
curl http://127.0.0.1:8000/tasks
```

## Telegram
After both Telegram variables are set:
```bash
docker compose up -d --build
docker compose logs -f telegram
```
Message the bot from the configured chat. `/tasks` lists tasks; `/done 1` completes task 1; normal natural language goes to Task Needle.

## V1 safety
Telegram token is never passed to Needle. There is no shell tool, arbitrary filesystem tool, GitHub write tool, or email-send tool.

V2 should add durable scheduling/reminder creation through validated tools, GitHub, Calendar, notification preferences, and a real event bus.
