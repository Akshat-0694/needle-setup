from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

class Task(BaseModel):
    id: str
    needle: str
    action: str = "run"
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Event(BaseModel):
    type: str
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
