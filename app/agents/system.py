import os
import shutil
import platform
import needle

@needle.tool
def system_info():
    """Read basic read-only information about the EC2 host."""
    total, used, free = shutil.disk_usage("/")
    return {
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "disk_free_gb": round(free / 1024**3, 2),
        "disk_total_gb": round(total / 1024**3, 2),
    }

def run(prompt: str):
    agent = needle.Needle(
        tools=[system_info],
        system="You are a read-only system assistant. Never execute commands or modify the host.",
    )
    return agent.run(prompt, max_steps=4, max_new_tokens=192)
