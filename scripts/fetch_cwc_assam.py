#!/usr/bin/env python3
"""
Fetch latest CWC water levels for major Assam stations
from https://ffs.india-water.gov.in
"""

import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "cwc_assam_water_levels.json"

# Station codes for major Assam CWC sites.
# These are the internal codes used by the FFS portal.
# (Taken / cross-checked from public CWC station lists + GUARDIAN name-code mapping)
ASSAM_STATIONS = {
    "Neamatighat": "001A03",          # Brahmaputra - Jorhat
    "Dibrugarh": "001A01",            # Brahmaputra - Dibrugarh
    "Tezpur": "001A05",               # Brahmaputra - Sonitpur
    "Guwahati(D.C.Court)": "001A07",  # Brahmaputra - Kamrup
    "Goalpara": "001A09",             # Brahmaputra - Goalpara
    "Dhubri": "001A11",               # Brahmaputra - Dhubri
    "Numaligarh": "001B01",           # Dhansiri - Golaghat
    "Sivasagar": "001B03",            # Dikhow - Sivasagar
    "Naharkatia": "001C01",           # Buridehing - Dibrugarh
    "Chenimari (Khowang)": "001C03",  # Buridehing
    "Badatighat": "001D01",           # Subansiri - Lakhimpur
    "Ranganadi NT Road crossing": "001D03",
    "NT Road Crossing Jia-Bharali": "001E01",
    "Kampur": "001F01",               # Kopili - Nagaon
    "Dharamtul": "001F03",            # Kopili - Morigaon
    "Annapurnaghat": "002A01",        # Barak - Cachar
    "Badarpurghat": "002A03",         # Barak
    "Karimganj": "002B01",            # Kushiyara
    "Matijuri": "002C01",             # Katakhal
    "Golaghat": "001B05",
}

API_URL = "https://ffs.india-water.gov.in/iam/api/new-entry-data/specification/sorted"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://ffs.india-water.gov.in/",
    "Origin": "https://ffs.india-water.gov.in",
}


def build_specification(station_code: str, start: str, end: str) -> str:
    """Build the nested JSON specification expected by the API."""
    spec = {
        "where": {
            "where": {
                "where": {
                    "expression": {
                        "valueIsRelationField": False,
                        "fieldName": "id.stationCode",
                        "operator": "eq",
                        "value": station_code,
                    }
                },
                "and": {
                    "expression": {
                        "valueIsRelationField": False,
                        "fieldName": "id.datatypeCode",
                        "operator": "eq",
                        "value": "HHS",
                    }
                },
            },
            "and": {
                "expression": {
                    "valueIsRelationField": False,
                    "fieldName": "dataValue",
                    "operator": "null",
                    "value": "false",
                }
            },
        },
        "and": {
            "expression": {
                "valueIsRelationField": False,
                "fieldName": "id.dataTime",
                "operator": "btn",
                "value": f"{start}T00:00:00.000,{end}T23:59:59.999",
            }
        },
    }
    return json.dumps(spec, separators=(",", ":"))


def fetch_station(station_code: str, name: str, days: int = 3) -> dict | None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    sdate = start.strftime("%Y-%m-%d")
    edate = end.strftime("%Y-%m-%d")

    sort_criteria = json.dumps(
        {"sortOrderDtos": [{"sortDirection": "DESC", "field": "id.dataTime"}]},
        separators=(",", ":"),
    )

    params = {
        "sort-criteria": sort_criteria,
        "specification": build_specification(station_code, sdate, edate),
    }

    try:
        r = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [{name}] request failed: {e}")
        return None

    if not data:
        print(f"  [{name}] no data returned")
        return None

    # Take the most recent reading
    latest = data[0]
    try:
        return {
            "station_code": station_code,
            "name": name,
            "water_level_m": latest.get("dataValue"),
            "observed_at": latest.get("id", {}).get("dataTime"),
            "datatype": latest.get("id", {}).get("datatypeCode"),
        }
    except Exception as e:
        print(f"  [{name}] parse error: {e}")
        return None


def main() -> None:
    print("Fetching CWC water levels for Assam stations...")
    results = []

    for name, code in ASSAM_STATIONS.items():
        print(f"→ {name} ({code})")
        row = fetch_station(code, name)
        if row:
            results.append(row)
            print(f"   {row['water_level_m']} m @ {row['observed_at']}")

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "https://ffs.india-water.gov.in",
        "state": "Assam",
        "count": len(results),
        "data": results,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {len(results)} stations → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
