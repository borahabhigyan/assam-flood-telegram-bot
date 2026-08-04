import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://smartaxom.nesdr.gov.in/analytics/flood/waterlevelinfo"

headers = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(
    url,
    headers=headers,
    timeout=30,
    verify=False,   # TEMPORARY
)

print("Status:", r.status_code)
print("Length:", len(r.text))

with open("page.html", "w", encoding="utf-8") as f:
    f.write(r.text)

print("Saved page.html")
