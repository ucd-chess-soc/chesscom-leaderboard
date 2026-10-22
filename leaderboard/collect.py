"""Fetching each club member's ratings and per-period history from chess.com."""
from datetime import datetime, timezone

from .ratings import current_rating, games_by_class, needs_earlier_games, period_summary

# How far back to look for a player's last game before a period starts.
MAX_LOOKBACK_MONTHS = 36


def _month_index(url):
    year, month = url.rstrip("/").split("/")[-2:]
    return int(year) * 12 + int(month) - 1


def _month_index_from_ts(ts):
    d = datetime.fromtimestamp(ts, timezone.utc)
    return d.year * 12 + d.month - 1


def collect_player(client, username, time_classes, period_starts):
    """Ratings for one player.

    period_starts: {period_key: unix timestamp}.
    Returns {time_class: {"current": int, "periods": {key: {"start", "games"}}}},
    leaving out time classes the player has never played.
    """
    stats = client.stats(username)
    months = client.archive_months(username)
    earliest = min(period_starts.values())
    earliest_month = _month_index_from_ts(earliest)
    older = [u for u in months if _month_index(u) < earliest_month]
    recent = [u for u in months if _month_index(u) >= earliest_month]

    history = {tc: [] for tc in time_classes}

    def load(urls):
        for url in urls:
            for tc, games in games_by_class(client.month_games(url), username).items():
                if tc in history:
                    history[tc].extend(games)
        for games in history.values():
            games.sort()

    load(recent)
    lookback = 0
    while older and lookback < MAX_LOOKBACK_MONTHS and any(
        needs_earlier_games(history[tc], t) for tc in time_classes for t in period_starts.values()
    ):
        load([older.pop()])
        lookback += 1

    ratings = {}
    for tc in time_classes:
        current = current_rating(history[tc], stats.get(f"chess_{tc}"))
        if current is None:
            continue
        ratings[tc] = {
            "current": current,
            "periods": {
                key: period_summary(history[tc], current, t) for key, t in period_starts.items()
            },
        }
    return ratings

