import json
import urllib.request
import hashlib

BASE = "https://assamflood.org/"


def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Compare/1.0"}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


ptr = fetch_json(BASE + "data/current.json")

content_url = ptr["content_url"]
if not content_url.startswith("http"):
    content_url = BASE + content_url

data = fetch_json(content_url)

gauges = data["gauges"]

# Ignore generated_at and hash only the gauge data
digest = hashlib.sha256(
    json.dumps(gauges, sort_keys=True).encode()
).hexdigest()

print("generated_at :", data["generated_at"])
print("content_url  :", content_url)
print("Gauge SHA256 :", digest)
