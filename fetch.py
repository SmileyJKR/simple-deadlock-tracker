#!/usr/bin/env python3
"""Fetch current Deadlock analytics from the public API into raw/.

No dependencies. Run: python fetch.py
"""
import json
import os
import time
import urllib.request

BASE = "https://api.deadlock-api.com"

ENDPOINTS = {
    "hero_stats": "/v1/analytics/hero-stats",
    "heroes": "/v1/assets/heroes",
    "patches": "/v1/patches",
    "item_stats": "/v1/analytics/item-stats",
}


def get(path):
    url = BASE + path
    req = urllib.request.Request(url, headers={"User-Agent": "deadlock-lens/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    os.makedirs("raw", exist_ok=True)
    for name, path in ENDPOINTS.items():
        out = os.path.join("raw", name + ".json")
        print(f"fetching {path} ...")
        data = get(path)
        with open(out, "w") as f:
            json.dump(data, f)
        n = len(data) if isinstance(data, list) else "object"
        print(f"  -> {out} ({n})")
        time.sleep(1)  # be polite; limit is 200 req/min
    print("done.")


if __name__ == "__main__":
    main()
