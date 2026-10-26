# Deadlock Tier Tracker

A small pipeline that pulls live Deadlock analytics from the public
[deadlock-api.com](https://api.deadlock-api.com), computes hero tiers, and
renders a single-file static site. This is the **vanilla** version — plain
HTML/CSS/JS, no framework, no build step. Built for the @SmileyJKR_DL
patch-day workflow: snapshot the meta, see what a patch moved, draft the tweet.

> The same dashboard rebuilt in React lives in
> [react-deadlock-tracker](https://github.com/SmileyJKR/react-deadlock-tracker).

## What it does

1. **fetch.py** — downloads the raw API data (hero stats, hero assets,
   patches, item stats) into `raw/`.
2. **snapshot.py** — the main entry point. Computes per-hero stats and
   tiers from `raw/`, writes a dated snapshot to `data/snapshots/`,
   computes the diff against the previous snapshot, and builds `site.html`
   from `site_template.html`.
3. **diff.py** — prints the current patch diff as a readable table.
4. **tweet.py** — drafts the patch-day tweet from `data/diff.json`.

## The tier math

Tiers are computed per snapshot, not absolute:

- **Score** = 0.7 * winrate percentile + 0.3 * pickrate percentile
  (weights in `config.json`).
- Heroes with fewer than `min_matches` (1000) are excluded — small
  samples make percentiles noisy.
- Score is bucketed into S / A / B / C / D tiers by percentile cutoffs.

The idea: a hero is "strong" if it wins a lot *and* people actually play
it. Winrate alone rewards niche picks; pickrate alone rewards staples.
The blend is a compromise, and the weights are tunable in `config.json`.

## The diff

Each snapshot is compared against the previous one to produce
`data/diff.json`: per-hero winrate/pickrate deltas (in percentage points)
and tier changes (e.g. `B -> A`). This is what the "Patch Diff" tab and
`tweet.py` consume.

**DEMO mode:** the first snapshot has no previous snapshot to diff
against, so `snapshot.py` generates a simulated previous snapshot and
labels the diff `DEMO`. Once a second real snapshot exists (after the
next patch), the diff becomes real automatically — no code change needed.

## The site

`site.html` is a single self-contained file (no build step, no external
JS). It embeds the current snapshot and diff as JSON and renders:

- **Tier Tracker tab** — hero cards with portrait, tier badge, winrate,
  pickrate, match count, and top items. Search, sort, and tier
  filter are all client-side.
- **Patch Diff tab** — a table of per-hero deltas and tier changes,
  sorted by winrate delta.

Portraits are loaded from the API's CDN (remote URLs), so the site needs
internet to show images. Everything else works offline.

## Running it

```bash
python fetch.py      # refresh raw/ from the API
python snapshot.py   # compute tiers + diff, rebuild site.html
python diff.py       # print the diff as a table
python tweet.py      # draft the patch-day tweet
```

`snapshot.py` is the one you usually run. It's idempotent for a given
day: re-running it on the same date overwrites that day's snapshot.

## Files

```
fetch.py            API -> raw/
snapshot.py         raw/ -> tiers, snapshot, diff, site.html  (main)
diff.py             print the diff
tweet.py            draft the tweet
config.json         min_matches + tier weights
site_template.html  the site template (tokens __DATA__ / __DIFF__)
site.html           the built site (what you open / deploy)
raw/                raw API responses
data/snapshots/     dated snapshots (one per run-day)
data/latest.json    copy of the newest snapshot
data/diff.json      current patch diff
```

## Notes / known quirks

- **Item names** come straight from the API and sometimes differ from
  in-game names (e.g. "Improved Spirit"). Left as-is rather than
  hand-mapping ~156 items.
- **Portraits** are 280x380; the card CSS uses that aspect ratio so the
  full portrait shows without cropping.
- The diff is only as good as the gap between snapshots. Run `snapshot.py`
  right before and right after a patch for a clean before/after.
