"""Reconstructing a player's rating at past dates from their game history.

Each game in the chess.com archive records the player's rating *after* that
game, so the rating at time t is the rating from the last game ending at or
before t. Only rated, standard-chess games count (not Chess960 etc., which
have separate ratings).
"""
from bisect import bisect_right


def games_by_class(games, username):
    """Rated standard games for one player -> {time_class: [(end_time, rating_after), ...]}."""
    username = username.lower()
    out = {}
    for g in games:
        if not g.get("rated") or g.get("rules") != "chess":
            continue
        if g["white"]["username"].lower() == username:
            side = g["white"]
        elif g["black"]["username"].lower() == username:
            side = g["black"]
        else:
            continue
        out.setdefault(g["time_class"], []).append((g["end_time"], side["rating"]))
    return out


def rating_at(history, t):
    """Rating after the last game ending at or before t, or None if no such game.

    history must be sorted by end_time.
    """
    i = bisect_right(history, t, key=lambda game: game[0])
    return history[i - 1][1] if i else None


def games_after(history, t):
    return len(history) - bisect_right(history, t, key=lambda game: game[0])


def needs_earlier_games(history, t):
    """True if the window after t has games but nothing loaded shows the rating at t."""
    return games_after(history, t) > 0 and rating_at(history, t) is None


def current_rating(history, stats_entry):
    """Latest rating, from whichever of the stats endpoint or archive is newer.

    The stats endpoint can lag the archive by several hours.
    """
    candidates = []
    if history:
        candidates.append(history[-1])
    if stats_entry and "last" in stats_entry:
        candidates.append((stats_entry["last"]["date"], stats_entry["last"]["rating"]))
    return max(candidates)[1] if candidates else None


def period_summary(history, current, since):
    """Start rating and games played for the window (since, now].

    When the player's first ever game in this time class falls inside the
    window there's no prior rating, so change is measured from the rating after
    that first game and the period is flagged "new".
    """
    games = games_after(history, since)
    if games == 0:
        return {"start": current, "games": 0, "new": False}
    start = rating_at(history, since)
    if start is None:
        return {"start": history[len(history) - games][1], "games": games, "new": True}
    return {"start": start, "games": games, "new": False}
