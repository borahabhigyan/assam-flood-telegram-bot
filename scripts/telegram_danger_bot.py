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
STATUS_LABEL = {"above_danger": "DANGER", "above_hfl": "ABOVE HFL"}


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "AssamFloodBot/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def load_gauges() -> tuple[list[dict], str]:
    ptr = fetch_json(BASE + "data/current.json")
    content_url = ptr["content_url"]
    if not content_url.startswith("http"):
        content_url = BASE + content_url
    data = fetch_json(content_url)
    return data.get("gauges") or [], data.get("generated_at") or ptr.get("generated_at") or ""


def river_of(g: dict) -> str:
    return g.get("river_name") or g.get("river") or "—"


def gauge_key(g: dict) -> str:
    return f"{g.get('gauge_id')}|{g.get('status')}"


def load_state() -> set[str]:
    if not STATE_PATH.exists():
        return set()
    try:
        return set(json.loads(STATE_PATH.read_text()).get("danger_keys") or [])
    except (json.JSONDecodeError, OSError):
        return set()


def save_state(keys: set[str], generated_at: str) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(
            {"generated_at": generated_at, "danger_keys": sorted(keys)},
            indent=2,
        )
        + "\n"
    )


def format_message(alerts: list[dict], generated_at: str) -> str:
    lines = [
        "🚨 *Assam river danger alert*",
        f"_Data time: {generated_at}_",
        "",
    ]
    for g in alerts:
        name = g.get("site_name") or g.get("gauge_id") or "Gauge"
        st = STATUS_LABEL.get(g.get("status") or "", "?")
        level = g.get("level_m")
        level_s = f"{float(level):.2f} m" if level is not None else "—"
        danger = g.get("danger_level_m")
        danger_s = f"{float(danger):.2f} m" if danger is not None else "—"
        trend = g.get("trend_cm_per_hr")
        trend_s = f"{trend:+.1f} cm/h" if trend is not None else "—"
        sentence = (g.get("sentence_en") or "").strip()

        block = (
            f"*{name}* ({river_of(g)})\n"
            f"Status: *{st}*\n"
            f"Level: `{level_s}` (danger mark `{danger_s}`)\n"
            f"Trend: `{trend_s}`"
        )
        if sentence:
            block += f"\n_{sentence}_"
        lines.append(block)
        lines.append("")

    lines.append(
        "Source: [assamflood.org](https://assamflood.org) (CWC data)\n"
        "Not an official warning. Emergency: ASDMA *1070*"
    )
    return "\n".join(lines)


def send_telegram(text: str, dry_run: bool) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    print("MESSAGE:\n", text)

    if dry_run:
        print("(dry-run — not sent)")
        return

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
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read().decode())
    if not resp.get("ok"):
        raise RuntimeError(f"Telegram error: {resp}")
    print("Sent to group.")


def main() -> int:
    dry_run = os.environ.get("DRY_RUN", "").lower() in {"1", "true", "yes"}

    gauges, generated_at = load_gauges()
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

    current = {gauge_key(g) for g in in_danger}
    previous = load_state()

    # First run: seed state only (don't spam current dangers)
    if not previous:
        print(f"First run: seeding {len(current)} keys, no message.")
        save_state(current, generated_at)
        return 0

    new_keys = current - previous
    new_alerts = [g for g in in_danger if gauge_key(g) in new_keys]
    save_state(current, generated_at)

    if not new_alerts:
        print("No new danger crossings.")
        return 0

    print(f"{len(new_alerts)} new danger alert(s).")
    text = format_message(new_alerts, generated_at)
    if len(text) > 4000:
        text = format_message(new_alerts[:8], generated_at) + "\n…(truncated)"

    send_telegram(text, dry_run)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
