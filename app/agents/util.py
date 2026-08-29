"""Helpers shared by the needle agents.

cactus-needle's `Needle.complete()` returns a raw tool-call envelope and
does NOT execute anything; `Needle.run()` executes the tool calls in a
loop and returns a final `type: "respond"` envelope. `render()` converts
either envelope into Telegram-friendly text.
"""


def _scalar(value):
    if isinstance(value, bool):
        return "yes" if value else "no"

    if isinstance(value, (int, float)):
        return str(value)

    text = str(value).strip()

    if len(text) > 400:
        return text[:400] + "…"

    return text


def _fmt_dict(value):
    lines = []

    for key, val in value.items():
        if val is None:
            continue

        if isinstance(val, (dict, list, tuple)):
            rendered = _fmt(val)

            if rendered:
                lines.append(f"{key}: {rendered}")
        else:
            lines.append(f"{key}: {_scalar(val)}")

    return "\n".join(lines)


def _fmt_list(value):
    lines = []

    for item in value:
        if isinstance(item, dict):
            title = (
                item.get("title")
                or item.get("name")
                or item.get("repo")
                or item.get("model_id")
                or item.get("url")
            )

            if title:
                lines.append("• " + _scalar(title))

                for key in ("url", "score"):
                    if key in item and item[key] is not None:
                        lines.append(
                            f"  {key}: {_scalar(item[key])}"
                        )
            else:
                lines.append(_fmt_dict(item))
        elif isinstance(item, (dict, list, tuple)):
            lines.append(_fmt(item))
        else:
            lines.append("• " + _scalar(item))

    return "\n".join(lines)


def _fmt(value):
    if isinstance(value, dict):
        return _fmt_dict(value)

    if isinstance(value, (list, tuple)):
        return _fmt_list(value)

    return _scalar(value)


def render(response):
    """
    Convert a cactus-needle response envelope into text.

    Handles both the intermediate `type: "call"` plan envelope (in case a
    caller used `complete()`) and the final `type: "respond"` envelope that
    `run()` returns.
    """
    if isinstance(response, dict):
        rtype = response.get("type")
        reason = response.get("reasoning") or ""

        if rtype == "call":
            calls = response.get("function_calls") or []

            if calls:
                lines = ["🔧 Plan:"]

                for call in calls:
                    name = call.get("name", "?")
                    args = call.get("arguments") or {}

                    rendered_args = ", ".join(
                        f"{k}={_scalar(v)}"
                        for k, v in args.items()
                    )

                    lines.append(
                        f"• {name}({rendered_args})"
                    )

                return "\n".join(lines)

            return reason or str(response)

        if rtype == "respond":
            results = response.get("results") or []
            parts = []

            if reason:
                parts.append(reason.strip())

            for result in results:
                rendered = _fmt(result)

                if rendered:
                    parts.append(rendered)

            if parts:
                return "\n\n".join(parts)

            return str(response)

        return reason or str(response)

    if isinstance(response, (list, tuple)):
        return _fmt_list(response)

    return _scalar(response)
