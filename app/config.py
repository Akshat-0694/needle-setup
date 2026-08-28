import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    data_dir: str = os.getenv("DATA_DIR", "./data")
    timezone: str = os.getenv("TIMEZONE", "Asia/Kolkata")
    allow_side_effects: bool = os.getenv("ALLOW_SIDE_EFFECTS", "false").lower() == "true"
    notification_webhook_url: str = os.getenv("NOTIFICATION_WEBHOOK_URL", "")

settings = Settings()
