#!/usr/bin/env python3
"""
Fetch CWC water-level data from smartaxom.nesdr.gov.in and save as JSON.
"""

import base64
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter("ignore", InsecureRequestWarning)

KEY_ID = "tDqR0XLgej9c0QuYabX69GR4cLl2H1eq"
E_KEY = b"quvaFPLNdcpHqUgmrE71JI6QoSeq4dAZ"
E_IV = b"5034195220579759"
API_URL = "https://smartaxom.nesdr.gov.in/api_v2/dataCWC"

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "water_level_data.json"


def encrypt_payload(payload: str) -> str:
    cipher = AES.new(E_KEY, AES.MODE_CBC, E_IV)
    ct_bytes = cipher.encrypt(pad(payload.encode("utf-8"), AES.block_size))
    return base64.b64encode(ct_bytes).decode("utf-8")


def fetch_data() -> dict:
    payload = json.dumps({"keyId": KEY_ID}, separators=(",", ":"))
    encrypted = encrypt_payload(payload)

    # Force multipart/form-data exactly like the browser FormData does
    # (None, value) = ordinary form field, no filename
    files = {"key": (None, encrypted)}

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Origin": "https://smartaxom.nesdr.gov.in",
        "Referer": "https://smartaxom.nesdr.gov.in/analytics/flood/waterlevelinfo",
        "Accept": "application/json, text/plain, */*",
    }

    response = requests.post(
        API_URL,
        files=files,
        headers=headers,
        timeout=30,
        verify=False,
    )

    # Helpful debug if it still fails
    if response.status_code != 200:
        print("Status:", response.status_code)
        print("Response body:", response.text[:500])

    response.raise_for_status()
    return response.json()


def main() -> None:
    data = fetch_data()

    if not data.get("success"):
        raise RuntimeError(f"API returned success=false: {data}")

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "success": True,
        "count": len(data["data"]),
        "data": data["data"],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Saved {output['count']} records → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
