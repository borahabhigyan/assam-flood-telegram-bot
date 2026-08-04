import json
import base64
import requests
import urllib3

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# Ignore SSL warning (the site uses an untrusted certificate chain)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://smartaxom.nesdr.gov.in/api_v2/dataCWC"

KEY_ID = "tDqR0XLgej9c0QuYabX69GR4cLl2H1eq"
AES_KEY = b"quvaFPLNdcpHqUgmrE71JI6QoSeq4dAZ"
AES_IV = b"5034195220579759"


def encrypt(data: str) -> str:
    """
    Equivalent to:
    CryptoJS.AES.encrypt(data, key, { iv: iv }).toString()
    """

    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    encrypted = cipher.encrypt(pad(data.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


payload = json.dumps(
    {
        "keyId": KEY_ID
    },
    separators=(",", ":"),
)

encrypted = encrypt(payload)

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),
    "Origin": "https://smartaxom.nesdr.gov.in",
    "Referer": "https://smartaxom.nesdr.gov.in/analytics/flood/waterlevelinfo",
    "Accept": "application/json, text/plain, */*",
}

response = requests.post(
    URL,
    headers=headers,
    files={
        "key": (None, encrypted),
    },
    timeout=30,
    verify=False,
)

print("Status:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))

print("\nFirst 500 characters:\n")
print(response.text[:500])

with open("response.txt", "w", encoding="utf-8") as f:
    f.write(response.text)

try:
    data = response.json()

    print("\nSuccess field:", data.get("success"))
    print("Records:", len(data.get("data", [])))

    with open("waterlevels.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("Saved waterlevels.json")

except Exception:
    print("\nResponse is not valid JSON.")
