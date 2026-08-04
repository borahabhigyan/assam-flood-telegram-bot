from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime

BASE = "https://assamflood.org/"


def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AssamFloodTelegramBot/1.1"},
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def load_gauges():
    ptr = fetch_json(BASE + "data/current.json")

    content_url = ptr["content_url"]
    if not content_url.startswith("http"):
        content_url = BASE + content_url

    data = fetch_json(content_url)

    return (
        data.get("gauges", []),
        data.get("generated_at") or ptr.get("generated_at", ""),
    )


def river_of(g):
    return g.get("river_name") or g.get("river") or "Unknown River"


def place_of(g):
    return g.get("site_name") or g.get("gauge_id") or "Unknown"


def fmt_trend(v):
    if v is None:
        return "→ Stable"

    try:
        v = float(v)

        if abs(v) < 0.05:
            return "→ Stable"

        return f"{'↑' if v > 0 else '↓'}{abs(v):.1f} cm/h"

    except Exception:
        return "—"


def above(level, threshold):
    if level is None or threshold is None:
        return None

    try:
        return float(level) - float(threshold)
    except Exception:
        return None


def send(text):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = os.environ["TELEGRAM_CHAT_ID"]

    body = urllib.parse.urlencode(
        {
            "chat_id": chat,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": "true",
        }
    ).encode()

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read().decode())

    if not resp.get("ok"):
        raise RuntimeError(resp)


def split_message(text, limit=4000):
    parts = []
    current = ""

    for line in text.splitlines(True):
        if len(current) + len(line) > limit:
            parts.append(current.rstrip())
            current = line
        else:
            current += line

    if current:
        parts.append(current.rstrip())

    return parts


def main():
    gauges, generated_at = load_gauges()

    try:
        ts = datetime.fromisoformat(
            generated_at.replace("Z", "+00:00")
        ).strftime("%d %b, %H:%M")
    except Exception:
        ts = generated_at

    hfl = [g for g in gauges if g.get("status") == "above_hfl"]
    danger = [g for g in gauges if g.get("status") == "above_danger"]
    warning = [g for g in gauges if g.get("status") == "warning"]

    lines = [
        "🌊 *Assam Flood Update*",
        f"Data as of 🕒 {ts}",
        "",
    ]

    if hfl:
        lines.append("🔴 *HFL*")

        for g in sorted(hfl, key=lambda x: -(x.get("level_m") or 0)):
            diff = above(g.get("level_m"), g.get("hfl_m"))

            if diff is None:
                continue

            lines.append(
                 f"• {river_of(g)} ({place_of(g)})\n"
                 f"  +{diff:.2f} m • {fmt_trend(g.get('trend_cm_per_hr'))}\n"
            )

        lines.append("")

    if danger:
        lines.append("🟠 *Danger*")

        for g in sorted(danger, key=lambda x: -(x.get("level_m") or 0)):
            diff = above(g.get("level_m"), g.get("danger_level_m"))

            if diff is None:
                continue

            lines.append(
                 f"• {river_of(g)} ({place_of(g)})\n"
                 f"  +{diff:.2f} m • {fmt_trend(g.get('trend_cm_per_hr'))}\n"
            )

        lines.append("")

    if warning:
        lines.append("🟡 *Warning*")

        for g in sorted(warning, key=lambda x: -(x.get("level_m") or 0)):
            diff = above(g.get("level_m"), g.get("warning_level_m"))

            if diff is None:
                continue

            lines.append(
                 f"• {river_of(g)} ({place_of(g)})\n"
                 f"  +{diff:.2f} m • {fmt_trend(g.get('trend_cm_per_hr'))}\n"
            )


        lines.append("")

    if not (hfl or danger or warning):
        lines.append("✅ No gauges are above warning level.")

    text = "\n".join(lines)

    for part in split_message(text):
        send(part)

    print("Done")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(e, file=sys.stderr)
        raise
