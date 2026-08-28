import os
import platform
import shutil
import needle


@needle.tool
def get_system_status():
    """Get read-only information about the EC2 machine."""
    disk = shutil.disk_usage("/")

    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "disk_total_gb": round(disk.total / 1024**3, 2),
        "disk_used_gb": round(disk.used / 1024**3, 2),
        "disk_free_gb": round(disk.free / 1024**3, 2),
    }


def run(prompt: str):
    agent = needle.Needle(
        tools=[get_system_status],
        system=(
            "You are the System Needle in a personal assistant system. "
            "You are strictly read-only. "
            "Use tools when necessary. "
            "Never invent system information."
        ),
    )

    return agent.run(
        prompt,
        max_steps=4,
        max_new_tokens=256,
    )
