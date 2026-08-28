import json
import sqlite3
from pathlib import Path
from typing import Any

class State:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            source TEXT NOT NULL,
            payload TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """)
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS kv (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)
        self.db.commit()

    def event(self, event_type: str, source: str, payload: dict[str, Any], timestamp: str):
        self.db.execute(
            "INSERT INTO events(type,source,payload,timestamp) VALUES(?,?,?,?)",
            (event_type, source, json.dumps(payload), timestamp),
        )
        self.db.commit()

    def get(self, key: str, default=None):
        row = self.db.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return default if row is None else json.loads(row[0])

    def set(self, key: str, value):
        self.db.execute(
            "INSERT OR REPLACE INTO kv(key,value) VALUES(?,?)",
            (key, json.dumps(value)),
        )
        self.db.commit()

    def recent_events(self, limit=50):
        rows = self.db.execute(
            "SELECT type,source,payload,timestamp FROM events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {"type": r[0], "source": r[1], "payload": json.loads(r[2]), "timestamp": r[3]}
            for r in rows
        ]
