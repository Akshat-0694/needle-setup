import json
import sqlite3
from pathlib import Path
from app.config import settings

DB = Path(settings.data_dir) / "needle.db"
DB.parent.mkdir(parents=True, exist_ok=True)

db = sqlite3.connect(DB, check_same_thread=False)
db.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL,
    result TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
)
""")
db.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""")
db.commit()

def create_task(agent: str, prompt: str) -> int:
    cur = db.execute(
        "INSERT INTO tasks(agent,prompt,status) VALUES(?,?,?)",
        (agent, prompt, "queued"),
    )
    db.commit()
    return cur.lastrowid

def update_task(task_id: int, status: str, result=None):
    db.execute(
        "UPDATE tasks SET status=?, result=?, completed_at=CURRENT_TIMESTAMP WHERE id=?",
        (status, json.dumps(result) if result is not None else None, task_id),
    )
    db.commit()

def list_tasks(limit=50):
    rows = db.execute(
        "SELECT id,agent,prompt,status,result,created_at,completed_at "
        "FROM tasks ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    out = []
    for r in rows:
        out.append({
            "id": r[0], "agent": r[1], "prompt": r[2], "status": r[3],
            "result": json.loads(r[4]) if r[4] else None,
            "created_at": r[5], "completed_at": r[6],
        })
    return out

def event(event_type, source, payload):
    db.execute(
        "INSERT INTO events(event_type,source,payload) VALUES(?,?,?)",
        (event_type, source, json.dumps(payload)),
    )
    db.commit()

def recent_events(limit=50):
    rows = db.execute(
        "SELECT event_type,source,payload,created_at "
        "FROM events ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        {"type": r[0], "source": r[1], "payload": json.loads(r[2]), "created_at": r[3]}
        for r in rows
    ]
