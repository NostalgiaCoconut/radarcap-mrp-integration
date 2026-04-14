"""
SAP Sandbox Diagnostic Tool
Run: python diagnose_sap.py
Reads $metadata from SAP sandbox and prints all available entity sets.
This tells us the exact names to use in the connector.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import xml.etree.ElementTree as ET
from pathlib import Path

def load_env():
    env = Path(__file__).parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()

API_KEY  = os.environ.get("SAP_API_KEY", "")
BASE_URL = os.environ.get("SAP_BASE_URL", "https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap")

SERVICES = [
    "API_WORK_CENTERS",
    "API_PLANNED_ORDERS_SRV",
    "API_PRODUCTION_ORDERS_SRV",
    "API_MAINTNOTIFICATION",
    "API_PRODUCT_SRV",
]

session = requests.Session()
session.headers.update({"APIKey": API_KEY, "Accept": "application/json"})

print(f"\nSAP Sandbox Diagnostic")
print(f"Base URL: {BASE_URL}")
print(f"API Key:  {API_KEY[:8]}...\n")
print("=" * 60)

for svc in SERVICES:
    print(f"\nService: {svc}")
    url = f"{BASE_URL}/{svc}/$metadata"
    try:
        r = requests.get(url, headers={"APIKey": API_KEY}, timeout=15)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            # Parse XML metadata to get entity set names
            try:
                root = ET.fromstring(r.text)
                ns = {"edm": "http://schemas.microsoft.com/ado/2008/09/edm"}
                entity_sets = []
                for ns_uri in ["http://schemas.microsoft.com/ado/2008/09/edm",
                               "http://docs.oasis-open.org/odata/ns/edm"]:
                    for ec in root.iter(f"{{{ns_uri}}}EntityContainer"):
                        for es in ec.iter(f"{{{ns_uri}}}EntitySet"):
                            entity_sets.append(es.get("Name"))
                if entity_sets:
                    print(f"  Entity sets:")
                    for e in entity_sets[:10]:
                        print(f"    - {e}")
                    if len(entity_sets) > 10:
                        print(f"    ... and {len(entity_sets)-10} more")
                else:
                    print(f"  (Could not parse entity sets from metadata)")
                    print(f"  Raw (first 300): {r.text[:300]}")
            except Exception as ex:
                print(f"  Parse error: {ex}")
                print(f"  Raw (first 300): {r.text[:300]}")
        else:
            print(f"  Response: {r.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "=" * 60)
print("Copy the entity set names above into the connector config.")
