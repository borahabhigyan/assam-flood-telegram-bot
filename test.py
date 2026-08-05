import json
import urllib.request

BASE = "https://assamflood.org/"


def fetch_json(url):
    print(f"\nFetching: {url}")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TestBot/1.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


# Step 1: Load current.json
ptr = fetch_json(BASE + "data/current.json")

print("\n===== current.json =====")
print(json.dumps(ptr, indent=2))

# Step 2: Load actual data file
content_url = ptr["content_url"]
if not content_url.startswith("http"):
    content_url = BASE + content_url

print("\nContent URL:", content_url)

data = fetch_json(content_url)

print("\n===== Dataset Info =====")
print("generated_at:", data.get("generated_at"))
print("Number of gauges:", len(data.get("gauges", [])))

print("\n===== First 10 Gauges =====")

for g in data.get("gauges", [])[:10]:
    print(
        f"{g.get('site_name'):<25} "
        f"{g.get('river_name'):<20} "
        f"Level={g.get('level_m')} "
        f"Trend={g.get('trend_cm_per_hr')} "
        f"Status={g.get('status')}"
    )

print("\n===== Gauges Above Warning =====")

for g in data.get("gauges", []):
    if g.get("status") in ("warning", "above_danger", "above_hfl"):
        print(
            f"{g.get('site_name')} | "
            f"{g.get('river_name')} | "
            f"{g.get('status')} | "
            f"{g.get('level_m')} | "
            f"{g.get('trend_cm_per_hr')}"
        )
