"""Check PyPI package metadata."""
from __future__ import annotations

import json
import urllib.request


def main() -> None:
    url = "https://pypi.org/pypi/petfishframework/0.1.0/json"
    resp = urllib.request.urlopen(url, timeout=15)
    data = json.loads(resp.read().decode())
    info = data.get("info", {})

    print("=== PROJECT URLS ===")
    urls = info.get("project_urls", {})
    if urls:
        for k, v in urls.items():
            print(f"  {k}: {v}")
    else:
        print("  NONE — project_urls not set!")

    print("\n=== HOMEPAGE ===")
    print(f"  {info.get('homepage_url', 'NOT SET')}")

    print("\n=== DESCRIPTION / README ===")
    desc = info.get("description", "")
    print(f"  Length: {len(desc)} chars")
    if not desc:
        print("  EMPTY — README not included!")
    else:
        print(f"  First 300 chars:\n  {desc[:300]}")

    print("\n=== KEY METADATA ===")
    for key in ["name", "version", "license", "requires_python", "summary"]:
        print(f"  {key}: {info.get(key, 'MISSING')}")


if __name__ == "__main__":
    main()
