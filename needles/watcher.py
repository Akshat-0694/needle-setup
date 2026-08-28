import asyncio
import hashlib
import httpx
import os

from needles.base import NeedleWorker
from core.protocol import Task

class Watcher(NeedleWorker):
    name = "watcher"

    async def handle(self, task: Task):
        if task.action != "check":
            await self.emit("watcher.ignored", {"task_id": task.id, "reason": "unknown action"})
            return

        url = task.payload["url"]
        previous = task.payload.get("previous_hash")
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            response = await client.get(url)
            digest = hashlib.sha256(response.content).hexdigest()

        changed = previous is not None and previous != digest
        await self.emit("watcher.checked", {
            "task_id": task.id,
            "url": url,
            "status_code": response.status_code,
            "hash": digest,
            "changed": changed,
        })

if __name__ == "__main__":
    asyncio.run(Watcher().run())
