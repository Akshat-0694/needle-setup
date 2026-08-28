import json, sqlite3
from pathlib import Path
from app.config import settings
DB=Path(settings.data_dir)/"needle.db"
DB.parent.mkdir(parents=True,exist_ok=True)
db=sqlite3.connect(DB,check_same_thread=False)
db.row_factory=sqlite3.Row
db.execute("""CREATE TABLE IF NOT EXISTS tasks (
 id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '',
 due_at TEXT, status TEXT NOT NULL DEFAULT 'open',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, completed_at TEXT)""")
db.execute("""CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, source TEXT NOT NULL,
 payload TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
db.execute("""CREATE TABLE IF NOT EXISTS reminders (
 id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER NOT NULL,
 remind_at TEXT NOT NULL, sent INTEGER NOT NULL DEFAULT 0)""")
db.commit()
def create_task(title,notes="",due_at=None):
    cur=db.execute("INSERT INTO tasks(title,notes,due_at) VALUES(?,?,?)",(title,notes,due_at)); db.commit(); return cur.lastrowid
def get_task(task_id):
    r=db.execute("SELECT * FROM tasks WHERE id=?",(task_id,)).fetchone(); return dict(r) if r else None
def list_tasks(status="open"):
    if status=="all": rows=db.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
    else: rows=db.execute("SELECT * FROM tasks WHERE status=? ORDER BY id DESC",(status,)).fetchall()
    return [dict(r) for r in rows]
def complete_task(task_id):
    db.execute("UPDATE tasks SET status='completed',completed_at=CURRENT_TIMESTAMP WHERE id=?",(task_id,)); db.commit(); return get_task(task_id)
def add_reminder(task_id,remind_at):
    cur=db.execute("INSERT INTO reminders(task_id,remind_at) VALUES(?,?)",(task_id,remind_at)); db.commit(); return cur.lastrowid
def due_reminders(now_iso):
    rows=db.execute("""SELECT r.id,r.task_id,r.remind_at,t.title,t.notes FROM reminders r
    JOIN tasks t ON t.id=r.task_id WHERE r.sent=0 AND r.remind_at<=? ORDER BY r.id""",(now_iso,)).fetchall()
    return [dict(r) for r in rows]
def mark_reminder_sent(reminder_id):
    db.execute("UPDATE reminders SET sent=1 WHERE id=?",(reminder_id,)); db.commit()
def add_event(event_type,source,payload):
    db.execute("INSERT INTO events(event_type,source,payload) VALUES(?,?,?)",(event_type,source,json.dumps(payload))); db.commit()
def recent_events(limit=50):
    rows=db.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    return [{"id":r["id"],"type":r["event_type"],"source":r["source"],"payload":json.loads(r["payload"]),"created_at":r["created_at"]} for r in rows]
