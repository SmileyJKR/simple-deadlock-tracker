#!/usr/bin/env python3
"""Compute hero stats + tiers from raw/, write a dated snapshot, and build site.html.

Run: python snapshot.py
Writes:
  data/snapshots/YYYY-MM-DD.json   (dated snapshot, the meta record)
  data/latest.json                 (alias of the newest snapshot)
  data/diff.json                   (diff vs previous snapshot, or demo if first)
  site.html                        (self-contained dashboard, open anywhere)
"""
import datetime
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, "raw", name + ".json")) as f:
        return json.load(f)


def clean_item(it):
    name = it.get("class_name", "")
    for prefix in ("upgrade_", "item_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return {
        "name": name.replace("_", " ").title(),
        "pick": round(it.get("pick_pct", 0), 1),
        "wr": round(it.get("winrate_pct", 0), 1),
    }


def top_items(hero, n=3):
    seen, items = set(), []
    pi = hero.get("popular_items", {})
    for slot in ("mid_game", "late_game", "early_game"):
        for it in pi.get(slot, []):
            key = it.get("class_name")
            if key and key not in seen:
                seen.add(key)
                items.append(clean_item(it))
    items.sort(key=lambda x: -x["pick"])
    return items[:n]


def pct_rank(value, values):
    below = sum(1 for v in values if v < value)
    return below / max(len(values) - 1, 1)


def compute(cfg):
    stats = {h["hero_id"]: h for h in load("hero_stats")}
    heroes = {h["id"]: h for h in load("heroes")}
    patches = sorted(load("patches"), key=lambda p: p.get("pub_date", ""))
    total_matches = sum(h.get("matches", 0) for h in stats.values())

    rows = []
    for hid, s in stats.items():
        h = heroes.get(hid)
        if not h or not h.get("player_selectable", True):
            continue
        matches = s.get("matches", 0)
        wins = s.get("wins", 0)
        rows.append({
            "id": hid,
            "name": h["name"],
            "type": h.get("hero_type", ""),
            "image": h.get("images", {}).get("icon_hero_card", ""),
            "matches": matches,
            "wins": wins,
            "winrate": round(wins / matches * 100, 2) if matches else 0.0,
            "pickrate": round(matches / total_matches * 100, 2) if total_matches else 0.0,
            "top_items": top_items(h),
        })

    # tier assignment: weighted percentile of winrate + pickrate, min-match floor
    eligible = [r for r in rows if r["matches"] >= cfg["min_matches"]]
    wrs = [r["winrate"] for r in eligible]
    prs = [r["pickrate"] for r in eligible]
    for r in eligible:
        score = (cfg["weights"]["winrate"] * pct_rank(r["winrate"], wrs)
                 + cfg["weights"]["pickrate"] * pct_rank(r["pickrate"], prs))
        r["score"] = round(score, 4)
    eligible.sort(key=lambda r: -r["score"])
    n = len(eligible)
    for i, r in enumerate(eligible):
        frac = (i + 0.5) / n
        r["tier"] = next(t["name"] for t in cfg["tiers"] if frac <= t["top_pct"])
    for r in rows:
        if r["matches"] < cfg["min_matches"]:
            r["tier"] = "-"

    latest = patches[-1] if patches else None
    return {
        "date": datetime.date.today().isoformat(),
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "latest_patch": {
            "title": latest.get("title", ""),
            "pub_date": latest.get("pub_date", ""),
            "link": latest.get("link", ""),
        } if latest else None,
        "total_matches": total_matches,
        "heroes": rows,
    }


def make_diff(snapshots_dir):
    """Diff the two newest snapshots. If only one exists, make a clearly-labeled demo."""
    files = sorted(f for f in os.listdir(snapshots_dir) if f.endswith(".json"))
    if len(files) >= 2:
        old_f, new_f = files[-2], files[-1]
        with open(os.path.join(snapshots_dir, old_f)) as f:
            old = json.load(f)
        with open(os.path.join(snapshots_dir, new_f)) as f:
            new = json.load(f)
        demo = False
    else:
        new = json.load(open(os.path.join(snapshots_dir, files[-1])))
        old = json.loads(json.dumps(new))  # deep copy
        rng = random.Random(42)
        for r in old["heroes"]:
            r["winrate"] = round(r["winrate"] + rng.uniform(-0.9, 0.9), 2)
            r["pickrate"] = round(r["pickrate"] + rng.uniform(-0.3, 0.3), 2)
            r["tier"] = rng.choice(["S", "A", "A", "B", "B", "B", "C", "C", "D"])
        old["date"] = "demo"
        demo = True

    old_by = {r["id"]: r for r in old["heroes"]}
    wr_moves, pr_moves, tier_moves = [], [], []
    for r in new["heroes"]:
        o = old_by.get(r["id"])
        if not o:
            continue
        dw = round(r["winrate"] - o["winrate"], 2)
        dp = round(r["pickrate"] - o["pickrate"], 2)
        wr_moves.append({"name": r["name"], "delta": dw, "from": o["winrate"], "to": r["winrate"]})
        pr_moves.append({"name": r["name"], "delta": dp, "from": o["pickrate"], "to": r["pickrate"]})
        if r["tier"] != o["tier"] and r["tier"] != "-":
            tier_moves.append({"name": r["name"], "from": o["tier"], "to": r["tier"]})

    wr_moves.sort(key=lambda x: -x["delta"])
    pr_moves.sort(key=lambda x: -x["delta"])
    return {
        "demo": demo,
        "from": old["date"],
        "to": new["date"],
        "patch": new.get("latest_patch", {}).get("title", ""),
        "winrate_movers": wr_moves,
        "pickrate_movers": pr_moves,
        "tier_changes": tier_moves,
    }


def diff_view(snapshot, diff):
    """Reshape make_diff output into the shape the template's diff tab expects."""
    if diff["demo"]:
        note = "DEMO - first snapshot; previous data is simulated to show the diff layout."
    else:
        note = "%s -> %s  (%s)" % (diff["from"], diff["to"], diff["patch"])
    wr = {m["name"]: m["delta"] for m in diff["winrate_movers"]}
    pr = {m["name"]: m["delta"] for m in diff["pickrate_movers"]}
    tc = {m["name"]: m for m in diff["tier_changes"]}
    rows = []
    for h in snapshot["heroes"]:
        t = tc.get(h["name"])
        tier_change = "%s \u2192 %s" % (t["from"], t["to"]) if t else h["tier"]
        rows.append({
            "name": h["name"],
            "tier_change": tier_change,
            "winrate_delta": wr.get(h["name"], 0.0),
            "pickrate_delta": pr.get(h["name"], 0.0),
            "matches": h["matches"],
        })
    return {"note": note, "rows": rows}


def build_site(snapshot, diff):
    with open(os.path.join(HERE, "site_template.html")) as f:
        html = f.read()
    html = html.replace("__DATA__", json.dumps(snapshot))
    html = html.replace("__DIFF__", json.dumps(diff_view(snapshot, diff)))
    with open(os.path.join(HERE, "site.html"), "w") as f:
        f.write(html)


def main():
    with open(os.path.join(HERE, "config.json")) as f:
        cfg = json.load(f)

    snap = compute(cfg)

    snap_dir = os.path.join(HERE, "data", "snapshots")
    os.makedirs(snap_dir, exist_ok=True)
    snap_path = os.path.join(snap_dir, snap["date"] + ".json")
    with open(snap_path, "w") as f:
        json.dump(snap, f, indent=1)

    with open(os.path.join(HERE, "data", "latest.json"), "w") as f:
        json.dump(snap, f, indent=1)

    diff = make_diff(snap_dir)
    with open(os.path.join(HERE, "data", "diff.json"), "w") as f:
        json.dump(diff, f, indent=1)

    build_site(snap, diff)

    print(f"snapshot: {snap_path} ({len(snap['heroes'])} heroes, {snap['total_matches']:,} total matches)")
    print(f"latest patch: {snap['latest_patch']['title']} ({snap['latest_patch']['pub_date']})")
    print(f"diff: {'DEMO (first snapshot)' if diff['demo'] else diff['from'] + ' -> ' + diff['to']}")
    print("site.html built.")


if __name__ == "__main__":
    main()
