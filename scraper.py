import base64
import json
import urllib3
import requests

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# Ignore SSL certificate warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://smartaxom.nesdr.gov.in/api_v2/dataCWC"

AES_KEY = b"quvaFPLNdcpHqUgmrE71JI6QoSeq4dAZ"
AES_IV = b"5034195220579759"

# EXACT string used by JSON.stringify(...)
PAYLOAD = '{"keyId":"tDqR0XLgej9c0QuYabX69GR4cLl2H1eq"}'


def encrypt(text: str) -> str:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    encrypted = cipher.encrypt(pad(text.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


encrypted_key = encrypt(PAYLOAD)

print("=" * 60)
print("Encrypted key:")
print(encrypted_key)
print("=" * 60)

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 15; Pixel 9) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Mobile Safari/537.36"
    ),
    "Referer": "https://smartaxom.nesdr.gov.in/analytics/flood/waterlevelinfo",
    "Accept": "application/json, text/plain, */*",
}

response = requests.post(
    URL,
    headers=headers,
    files={
        "key": (None, encrypted_key),
    },
    verify=False,
    timeout=30,
)

print("Status:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))

with open("response.txt", "w", encoding="utf-8") as f:
    f.write(response.text)

print("\nFirst 500 characters:\n")
print(response.text[:500])

try:
    data = response.json()

    print("\nJSON received successfully")
    print("Success:", data.get("success"))
    print("Records:", len(data.get("data", [])))

    with open("waterlevels.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("Saved waterlevels.json")

except Exception:
    print("\nResponse is not valid JSON.")
