#!/usr/bin/env python3
"""Print the current diff in a readable table. Run: python diff.py"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(HERE, "data", "diff.json")) as f:
        d = json.load(f)

    if d.get("demo"):
        print("DEMO DIFF (first snapshot - no real previous data yet)\n")
    print(f"winrate: {d['from']} -> {d['to']}   patch: {d['patch']}\n")

    print("TOP WINRATE MOVERS")
    for m in d["winrate_movers"][:5]:
        print(f"  {m['name']:<14} {m['from']:>6.2f} -> {m['to']:>6.2f}  ({m['delta']:+.2f})")
    print("\nBOTTOM WINRATE MOVERS")
    for m in d["winrate_movers"][-5:][::-1]:
        print(f"  {m['name']:<14} {m['from']:>6.2f} -> {m['to']:>6.2f}  ({m['delta']:+.2f})")

    print("\nTOP PICKRATE MOVERS")
    for m in d["pickrate_movers"][:5]:
        print(f"  {m['name']:<14} {m['from']:>6.2f} -> {m['to']:>6.2f}  ({m['delta']:+.2f})")

    if d["tier_changes"]:
        print("\nTIER CHANGES")
        for t in d["tier_changes"]:
            print(f"  {t['name']:<14} {t['from']} -> {t['to']}")
    else:
        print("\nno tier changes")


if __name__ == "__main__":
    main()
