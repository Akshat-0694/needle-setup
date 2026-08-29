import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    timezone: str = os.getenv("TIMEZONE", "Asia/Kolkata")
    data_dir: str = os.getenv("DATA_DIR", "/app/data")

    # Telegram
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # MCP capability server (our own tool server)
    mcp_url: str = os.getenv("MCP_URL", "http://mcp:9000/mcp")

    # Notion MCP server
    notion_token: str = os.getenv("NOTION_TOKEN", "")
    notion_mcp_auth_token: str = os.getenv("NOTION_MCP_AUTH_TOKEN", "")
    notion_mcp_url: str = os.getenv("NOTION_MCP_URL", "http://notion-mcp:3000/mcp")

    # Research sources
    jina_api_key: str = os.getenv("JINA_API_KEY", "")
    hf_token: str = os.getenv("HF_TOKEN", "")

    # GitHub CLI auth
    github_token: str = os.getenv("GITHUB_TOKEN", "")

    # Kaggle API auth
    kaggle_username: str = os.getenv("KAGGLE_USERNAME", "")
    kaggle_key: str = os.getenv("KAGGLE_KEY", "")

    # Notion parent pages per needle (child pages are created under these)
    notion_parent_github: str = os.getenv(
        "NOTION_PARENT_GITHUB",
        "3cbddaaf-2318-808d-8a01-000bf855c0b4",
    )
    notion_parent_blog: str = os.getenv(
        "NOTION_PARENT_BLOG",
        "3cbddaaf-2318-808d-8a01-000bf855c0b4",
    )
    notion_parent_research: str = os.getenv(
        "NOTION_PARENT_RESEARCH",
        "3cbddaaf-2318-808d-8a01-000bf855c0b4",
    )

    # Morning briefing time, local timezone, 24h "HH:MM"
    morning_time: str = os.getenv("MORNING_TIME", "08:30")

    # Safety switch for side-effecting tools
    allow_side_effects: bool = os.getenv("ALLOW_SIDE_EFFECTS", "false").lower() == "true"


settings = Settings()
