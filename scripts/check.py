import json
import hashlib
import urllib.request
from pathlib import Path
from collections import Counter

BASE = "https://assamflood.org/"
CACHE = Path("previous_gauges.json")


def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AssamFloodChecker/1.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


print("=" * 80)
print("STEP 1 - Fetch current.json")
print("=" * 80)

ptr = fetch_json(BASE + "data/current.json")

print(json.dumps(ptr, indent=2))

content_url = ptr["content_url"]
if not content_url.startswith("http"):
    content_url = BASE + content_url

print("\nResolved content_url:")
print(content_url)

print("\n" + "=" * 80)
print("STEP 2 - Fetch content")
print("=" * 80)

data = fetch_json(content_url)
gauges = data["gauges"]

print("generated_at :", data.get("generated_at"))
print("schema_version :", data.get("schema_version"))
print("Gauge count :", len(gauges))

print("\n" + "=" * 80)
print("STEP 3 - Gauge SHA256")
print("=" * 80)

digest = hashlib.sha256(
    json.dumps(gauges, sort_keys=True).encode()
).hexdigest()

print(digest)

print("\n" + "=" * 80)
print("STEP 4 - Status counts")
print("=" * 80)

counts = Counter(g.get("status") for g in gauges)

for k in sorted(counts):
    print(f"{k:15} {counts[k]}")

print("\nUnique statuses:")
print(sorted(counts.keys()))

print("\n" + "=" * 80)
print("STEP 5 - First gauge fields")
print("=" * 80)

first = gauges[0]

print("Keys:")
for k in sorted(first.keys()):
    print(k)

print("\nValues:")

for key in [
    "site_name",
    "river",
    "river_name",
    "status",
    "level_m",
    "trend_cm_per_hr",
    "warning_level_m",
    "danger_level_m",
    "observed_at",
]:
    print(f"{key:20}: {first.get(key)}")

print("\n" + "=" * 80)
print("STEP 6 - Gauges with status != normal")
print("=" * 80)

for g in gauges:
    if g.get("status") != "normal":
        print(
            f"{g.get('site_name') or '-'} | "
            f"river={g.get('river')} | "
            f"river_name={g.get('river_name')} | "
            f"status={g.get('status')} | "
            f"level={g.get('level_m')} | "
            f"trend={g.get('trend_cm_per_hr')}"
        )

print("\n" + "=" * 80)
print("STEP 7 - Compare with previous run")
print("=" * 80)

current = {
    g["gauge_id"]: {
        "status": g.get("status"),
        "level": g.get("level_m"),
        "trend": g.get("trend_cm_per_hr"),
        "river": g.get("river"),
        "river_name": g.get("river_name"),
        "site_name": g.get("site_name"),
        "observed_at": g.get("observed_at"),
    }
    for g in gauges
}

if CACHE.exists():
    previous = json.loads(CACHE.read_text())

    changed = 0

    for gid in sorted(current):
        if gid not in previous:
            print(f"NEW: {gid}")
            changed += 1
            continue

        if current[gid] != previous[gid]:
            changed += 1

            print("\n" + "-" * 60)
            print(gid)

            for key in current[gid]:
                old = previous[gid].get(key)
                new = current[gid].get(key)

                if old != new:
                    print(f"{key}")
                    print(f"  OLD: {old}")
                    print(f"  NEW: {new}")

    print("\nTotal changed gauges:", changed)

else:
    print("No previous run found.")

CACHE.write_text(json.dumps(current, indent=2))

print("\nSaved current data to previous_gauges.json")
