import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()
@dataclass(frozen=True)
class Settings:
    timezone:str=os.getenv("TIMEZONE","Asia/Kolkata")
    data_dir:str=os.getenv("DATA_DIR","/app/data")
    telegram_bot_token:str=os.getenv("TELEGRAM_BOT_TOKEN","")
    telegram_chat_id:str=os.getenv("TELEGRAM_CHAT_ID","")
    jina_api_key:str=os.getenv("JINA_API_KEY","")
    hf_token:str=os.getenv("HF_TOKEN","")
    allow_side_effects:bool=os.getenv("ALLOW_SIDE_EFFECTS","false").lower()=="true"
settings=Settings()
