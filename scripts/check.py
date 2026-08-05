import json
import urllib.request
from collections import Counter

BASE = "https://assamflood.org/"


def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "StatusChecker/1.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


# Load current.json
ptr = fetch_json(BASE + "data/current.json")

content_url = ptr["content_url"]
if not content_url.startswith("http"):
    content_url = BASE + content_url

# Load gauges
data = fetch_json(content_url)
gauges = data.get("gauges", [])

print("Generated at:", data.get("generated_at"))
print("Total gauges:", len(gauges))

# Count statuses
status_counts = Counter(g.get("status") for g in gauges)

print("\n===== Status Counts =====")
for status, count in sorted(status_counts.items()):
    print(f"{status}: {count}")

print("\n===== Gauges with status != normal =====")

for g in gauges:
    status = g.get("status")
    if status != "normal":
        print(
            f"{g.get('site_name') or '-'} | "
            f"River: {g.get('river') or g.get('river_name') or '-'} | "
            f"Status: {status} | "
            f"Level: {g.get('level_m')} | "
            f"Trend: {g.get('trend_cm_per_hr')}"
        )

print("\n===== All Unique Status Strings =====")
print(sorted(status_counts.keys()))
