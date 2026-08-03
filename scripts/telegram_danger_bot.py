from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://assamflood.org/"
STATE_PATH = Path("bot_state/danger_state.json")

DANGER_STATUSES = {"above_danger", "above_hfl"}
STATUS_LABEL = {
    "above_hfl": "ABOVE HFL",
    "above_danger": "DANGER",
    "warning": "WARNING",
    "normal": "NORMAL",
    "no_data": "NO DATA",
}


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AssamFloodTelegramBot/1.1"},
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.loads(response.read().decode())


def load_gauges() -> tuple[list[dict], str]:
    ptr = fetch_json(BASE + "data/current.json")
    content_url = ptr["content_url"]
    if not content_url.startswith("http"):
        content_url = BASE + content_url
    data = fetch_json(content_url)
    gauges = data.get("gauges") or []
    generated_at = data.get("generated_at") or ptr.get("generated_at") or ""
    return gauges, generated_at


def river_of(g: dict) -> str:
    return g.get("river_name") or g.get("river") or "—"


def gauge_key(g: dict) -> str:
    return f"{g.get('gauge_id')}|{g.get('status')}"


def load_state() -> set[str]:
    if not STATE_PATH.exists():
        return set()
    try:
        data = json.loads(STATE_PATH.read_text())
        return set(data.get("danger_keys") or [])
    except (json.JSONDecodeError, OSError):
        return set()


def save_state(keys: set[str], generated_at: str) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "danger_keys": sorted(keys),
            },
            indent=2,
        )
        + "\n"
    )


def fmt_level(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.2f} m"
    except (TypeError, ValueError):
        return "—"


def fmt_trend(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):+.1f} cm/h"
    except (TypeError, ValueError):
        return "—"


def format_status(
    in_danger: list[dict],
    all_gauges: list[dict],
    generated_at: str,
    new_keys: set[str],
) -> str:
    n_hfl = sum(1 for g in in_danger if g.get("status") == "above_hfl")
    n_danger = sum(1 for g in in_danger if g.get("status") == "above_danger")
    n_warn = sum(1 for g in all_gauges if g.get("status") == "warning")

    lines = [
        "📡 *Assam river update*",
        f"_Data time: {generated_at}_",
        "",
        f"Above HFL: *{n_hfl}* · Danger: *{n_danger}* · Warning: *{n_warn}*",
        "",
    ]

    if new_keys:
        lines.append("⚠️ *New danger crossing(s) since last check*")
        lines.append("")

    if not in_danger:
        lines.append("No gauges at danger level right now.")
    else:
        lines.append("*Gauges at danger / HFL:*")
        for g in in_danger[:15]:
            name = g.get("site_name") or g.get("gauge_id") or "Gauge"
            st = STATUS_LABEL.get(g.get("status") or "", g.get("status") or "?")
            level_s = fmt_level(g.get("level_m"))
            danger_s = fmt_level(g.get("danger_level_m"))
            trend_s = fmt_trend(g.get("trend_cm_per_hr"))
            tag = " 🆕" if gauge_key(g) in new_keys else ""
            lines.append(
                f"• *{name}* ({river_of(g)}){tag}\n"
                f"  {st} · level `{level_s}` · danger mark `{danger_s}` · trend `{trend_s}`"
            )
        if len(in_danger) > 15:
            lines.append(f"…and {len(in_danger) - 15} more")

    lines.append("")
    lines.append(
         "Not an official warning. Emergency: ASDMA *1070*"
    )
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing or empty")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID is missing or empty")

    print("MESSAGE:\n", text)
    print("---")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": "true",
        }
    ).encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        resp = json.loads(response.read().decode())

    if not resp.get("ok"):
        raise RuntimeError(f"Telegram API error: {resp}")

    print("Sent to group.")


def main() -> int:
    gauges, generated_at = load_gauges()
    print(f"Loaded {len(gauges)} gauges · generated_at={generated_at}")

    in_danger = [
        g
        for g in gauges
        if (g.get("status") or "") in DANGER_STATUSES and g.get("level_m") is not None
    ]
    in_danger.sort(
        key=lambda g: (
            0 if g.get("status") == "above_hfl" else 1,
            -(g.get("level_m") or 0),
        )
    )

    current_keys = {gauge_key(g) for g in in_danger}
    previous_keys = load_state()
    new_keys = current_keys - previous_keys if previous_keys else set()

    save_state(current_keys, generated_at)

    text = format_status(in_danger, gauges, generated_at, new_keys)
    if len(text) > 4000:
        text = format_status(in_danger[:10], gauges, generated_at, new_keys)
        if len(text) > 4000:
            text = text[:3900] + "\n…(truncated)"

    send_telegram(text)
    print(
        f"Done. at_danger={len(in_danger)} new_crossings={len(new_keys)} "
        f"subscribers_state_keys={len(current_keys)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
