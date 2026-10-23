"""Weekly run: fetch ratings, save the week's leaderboard, build the site and graphics.

    python -m leaderboard                 # full run
    python -m leaderboard --no-images     # skip the Instagram graphics
    python -m leaderboard --skip-fetch    # re-render from the latest saved week
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .board import build_boards
from .chesscom import Client, NotFound
from .collect import collect_player

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "history"


def load_config():
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def period_windows(config, now):
    """{key: {"label", "headline", "since", "rolling"}} with since as an aware datetime."""
    windows = {}
    for p in config["periods"]:
        if "days" in p:
            since = now - timedelta(days=p["days"])
        else:
            since = datetime.fromisoformat(p["since"]).replace(tzinfo=timezone.utc)
        windows[p["key"]] = {
            "label": p["label"],
            "headline": p["headline"],
            "since": since,
            "rolling": "days" in p,
        }
    return windows


def fetch(config, now):
    client = Client(config["user_agent"])
    windows = period_windows(config, now)
    starts = {key: int(w["since"].timestamp()) for key, w in windows.items()}
    exclude = {u.lower() for u in config["exclude"]}
    joined_after = 0
    if config.get("joined_within_days"):
        joined_after = (now - timedelta(days=config["joined_within_days"])).timestamp()
    members = sorted(
        u
        for u, joined in client.club_members(config["club"]).items()
        if u not in exclude and joined >= joined_after
    )

    players = {}
    for i, username in enumerate(members, 1):
        print(f"[{i}/{len(members)}] {username}", file=sys.stderr)
        try:
            players[username] = collect_player(client, username, config["time_classes"], starts)
        except NotFound:
            print(f"  skipped: {username} not found on chess.com", file=sys.stderr)

    display_names = {k.lower(): v for k, v in config["display_names"].items()}
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "club": config["club"],
        "time_classes": config["time_classes"],
        "periods": {
            key: {**w, "since": w["since"].isoformat()} for key, w in windows.items()
        },
        "boards": build_boards(players, config["time_classes"], list(windows), display_names),
        "players": players,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-images", action="store_true", help="skip rendering graphics")
    parser.add_argument("--skip-fetch", action="store_true", help="use the latest saved week")
    args = parser.parse_args()
    config = load_config()

    if args.skip_fetch:
        latest = max(HISTORY.glob("*.json"))
        week = json.loads(latest.read_text(encoding="utf-8"))
    else:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        week = fetch(config, now)
        HISTORY.mkdir(parents=True, exist_ok=True)
        out = HISTORY / f"{now.date().isoformat()}.json"
        out.write_text(json.dumps(week, indent=1), encoding="utf-8")
        print(f"saved {out.relative_to(ROOT)}", file=sys.stderr)

    from .render import render_site

    render_site(week, config, ROOT / "site", images=not args.no_images)


if __name__ == "__main__":
    main()
