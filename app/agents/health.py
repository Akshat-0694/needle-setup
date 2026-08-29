"""Server health inspection.

Dependency-free: reads /proc for system stats, the local SQLite state for
app stats, and the kv table for the last time each scheduler job ran.
"""

import os
import socket

from app import state
from app.config import settings
from app.mcp.client import call


def _read_proc(path):
    try:
        with open(path) as handle:
            return handle.read().strip()
    except Exception:
        return ""


def _bytes(n):
    value = float(n)

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(value)}{unit}"
            return f"{value:.1f}{unit}"
        value /= 1024.0

    return f"{n}B"


def inspect():
    load = _read_proc("/proc/loadavg").split()
    load_avg = " ".join(load[:3]) if load else "n/a"

    try:
        uptime = float(_read_proc("/proc/uptime").split()[0])
    except Exception:
        uptime = 0.0

    mem = {}

    for line in _read_proc("/proc/meminfo").splitlines():
        key, _, value = line.partition(":")
        try:
            mem[key] = int(value.strip().split()[0]) * 1024
        except Exception:
            pass

    mem_total = mem.get("MemTotal", 0)
    mem_avail = mem.get("MemAvailable", 0)
    mem_used = mem_total - mem_avail

    try:
        cpu_cores = _read_proc("/proc/cpuinfo").count("processor")
    except Exception:
        cpu_cores = os.cpu_count() or 0

    try:
        stat = os.statvfs(settings.data_dir)
        disk_total = stat.f_frsize * stat.f_blocks
        disk_free = stat.f_frsize * stat.f_bavail
    except Exception:
        disk_total = 0
        disk_free = 0

    # MCP reachability (fast failure if the service is down).
    mcp_ok = False
    mcp_error = None

    try:
        call("tasks_list", status="open")
        mcp_ok = True
    except Exception as exc:
        detail = str(exc).splitlines()[0] if str(exc) else ""
        mcp_error = f"{type(exc).__name__}: {detail[:120]}"

    db_size = 0
    db_counts = {}

    try:
        db_size = os.path.getsize(state.DB)

        queries = {
            "tasks_open": "SELECT COUNT(*) FROM tasks WHERE status='open'",
            "articles_interesting": "SELECT COUNT(*) FROM articles WHERE interesting=1",
            "github_interesting": "SELECT COUNT(*) FROM github_repositories WHERE interesting=1",
            "research_interesting": "SELECT COUNT(*) FROM research_papers WHERE interesting=1",
            "hf_interesting": "SELECT COUNT(*) FROM huggingface_models WHERE interesting=1",
            "kaggle_interesting": "SELECT COUNT(*) FROM kaggle_items WHERE interesting=1",
            "opportunities": "SELECT COUNT(*) FROM opportunities",
            "spam_moved_today": "SELECT COUNT(*) FROM spam_events WHERE date(created_at)=date('now')",
        }

        for name, sql in queries.items():
            try:
                db_counts[name] = state.db.execute(sql).fetchone()[0]
            except Exception:
                db_counts[name] = "n/a"
    except Exception:
        pass

    jobs = {}

    for key in (
        "last_blog_scan",
        "last_github_scan",
        "last_research_scan",
        "last_kaggle_scan",
        "last_opportunity_check",
        "last_morning",
        "last_spam_scan",
    ):
        jobs[key] = state.get_kv(key, None)

    return {
        "hostname": socket.gethostname(),
        "container": os.path.exists("/.dockerenv"),
        "load_avg": load_avg,
        "uptime": uptime,
        "cpu_cores": cpu_cores,
        "mem_total": mem_total,
        "mem_used": mem_used,
        "mem_avail": mem_avail,
        "disk_total": disk_total,
        "disk_free": disk_free,
        "mcp_ok": mcp_ok,
        "mcp_error": mcp_error,
        "telegram_configured": bool(
            settings.telegram_bot_token and settings.telegram_chat_id
        ),
        "notion_configured": bool(
            settings.notion_token and settings.notion_mcp_auth_token
        ),
        "gmail_configured": bool(
            settings.gmail_email and settings.gmail_app_password
        ),
        "db_size": db_size,
        "db": db_counts,
        "jobs": jobs,
    }


def _format_uptime(seconds):
    days, rem = divmod(int(seconds), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)

    return f"{days}d {hours}h {minutes}m"


def format_health(info):
    lines = [
        "🖥️ Server health",
        "",
        f"Host: {info['hostname']}"
        + ("  (docker)" if info["container"] else ""),
        f"Uptime: {_format_uptime(info['uptime'])}",
        f"Load: {info['load_avg']}   (cores: {info['cpu_cores']})",
        f"Mem: {_bytes(info['mem_used'])} / {_bytes(info['mem_total'])} used, "
        f"{_bytes(info['mem_avail'])} free",
        f"Disk ({settings.data_dir}): {_bytes(info['disk_free'])} free / "
        f"{_bytes(info['disk_total'])}",
        "",
        "Services:",
        f"• MCP: {'✅ up' if info['mcp_ok'] else '❌ ' + (info['mcp_error'] or 'down')}",
        f"• Telegram: {'✅ configured' if info['telegram_configured'] else '❌ not configured'}",
        f"• Notion: {'✅ configured' if info['notion_configured'] else '❌ not configured'}",
        f"• Gmail spam: {'✅ configured' if info['gmail_configured'] else '❌ not configured'}",
        "",
        f"DB: {_bytes(info['db_size'])}",
    ]

    for key, value in info["db"].items():
        lines.append(f"  {key}: {value}")

    lines.append("")
    lines.append("Last scheduler runs:")

    for key, value in info["jobs"].items():
        lines.append(
            f"  {key.replace('last_', '').replace('_', ' ')}: "
            f"{value or 'never'}"
        )

    return "\n".join(lines)


def run(prompt=""):
    return format_health(inspect())
