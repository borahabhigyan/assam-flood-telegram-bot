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

# Suppress only the InsecureRequestWarning for this call
warnings.simplefilter("ignore", InsecureRequestWarning)

# Credentials from the frontend Environment.js
KEY_ID = "tDqR0XLgej9c0QuYabX69GR4cLl2H1eq"
E_KEY = b"quvaFPLNdcpHqUgmrE71JI6QoSeq4dAZ"
E_IV = b"5034195220579759"
API_URL = "https://smartaxom.nesdr.gov.in/api_v2/dataCWC"

# Save inside the data/ folder at the repo root
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "water_level_data.json"


def encrypt_payload(payload: str) -> str:
    """AES-CBC + PKCS7 – matches CryptoJS when key/IV are WordArrays."""
    cipher = AES.new(E_KEY, AES.MODE_CBC, E_IV)
    ct_bytes = cipher.encrypt(pad(payload.encode("utf-8"), AES.block_size))
    return base64.b64encode(ct_bytes).decode("utf-8")


def fetch_data() -> dict:
    payload = json.dumps({"keyId": KEY_ID}, separators=(",", ":"))
    encrypted = encrypt_payload(payload)

    response = requests.post(
        API_URL,
        data={"key": encrypted},
        timeout=30,
        verify=False,          # ← required because of self-signed cert in chain
    )
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
