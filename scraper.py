import requests

url = "https://smartaxom.nesdr.gov.in/analytics/flood/waterlevelinfo"

headers = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(url, headers=headers, timeout=30)

print("Status:", r.status_code)
print("Length:", len(r.text))

with open("page.html", "w", encoding="utf-8") as f:
    f.write(r.text)

print("Saved page.html")
