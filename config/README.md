# Configuration

V0 deliberately keeps configuration simple.

The Hub knows which Needles exist.
Each Needle owns its own implementation.
Later, move this into a registry/database and add per-Needle permissions.

Example future configuration:

```yaml
github:
  schedule: "*/30 * * * *"
  permissions:
    - github.read

email:
  schedule: "*/15 * * * *"
  permissions:
    - email.read
    - notification.send
```
