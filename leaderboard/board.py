"""Turning per-player ratings into leaderboards.

One board per time class, plus a combined board whose change is the average
of a player's per-time-class changes weighted by games played in each. So a
+50 in blitz over 80 games outweighs a -10 in rapid from a single game.

A period marked "new" means the player's first game in that time class fell
inside it, so the change is measured from their rating after that game.
"""


def _row(username, display_names):
    return {"username": username, "name": display_names.get(username, username)}


def time_class_board(players, tc, period_keys, display_names):
    rows = []
    for username, ratings in players.items():
        r = ratings.get(tc)
        if r is None:
            continue
        row = _row(username, display_names)
        row["rating"] = r["current"]
        row["periods"] = {}
        for key in period_keys:
            p = r["periods"][key]
            row["periods"][key] = {
                "delta": r["current"] - p["start"],
                "games": p["games"],
                "new": p["new"],
            }
        rows.append(row)
    return rows


def combined_board(players, time_classes, period_keys, display_names):
    rows = []
    for username, ratings in players.items():
        played = [tc for tc in time_classes if tc in ratings]
        if not played:
            continue
        row = _row(username, display_names)
        row["rating"] = None
        row["periods"] = {}
        for key in period_keys:
            weighted = games = 0
            new = False
            for tc in played:
                r = ratings[tc]
                p = r["periods"][key]
                weighted += (r["current"] - p["start"]) * p["games"]
                games += p["games"]
                new = new or p["new"]
            delta = round(weighted / games, 1) if games else 0
            row["periods"][key] = {"delta": delta, "games": games, "new": new}
        rows.append(row)
    return rows


def build_boards(players, time_classes, period_keys, display_names):
    boards = {tc: time_class_board(players, tc, period_keys, display_names) for tc in time_classes}
    boards["combined"] = combined_board(players, time_classes, period_keys, display_names)
    return boards


def movers(rows, period_key, min_games, limit):
    """Players ranked by rating change over the period, biggest gain first."""
    eligible = [r for r in rows if r["periods"][period_key]["games"] >= min_games]
    eligible.sort(
        key=lambda r: (-r["periods"][period_key]["delta"], -r["periods"][period_key]["games"])
    )
    return eligible[:limit]


def ladder(rows, limit):
    """Players ranked by current rating."""
    return sorted(rows, key=lambda r: -r["rating"])[:limit]
