"""Minimal client for the chess.com Published-Data API (read-only, no auth).

Docs: https://www.chess.com/news/view/published-data-api
Requests are made one at a time, as chess.com asks; parallel requests get 429s.
"""
import json
import time
import urllib.error
import urllib.request

BASE = "https://api.chess.com/pub"


class NotFound(Exception):
    pass


class Client:
    def __init__(self, user_agent, pause=0.2, retries=4):
        self.user_agent = user_agent
        self.pause = pause
        self.retries = retries
        self._cache = {}

    def get(self, url):
        if url in self._cache:
            return self._cache[url]
        req = urllib.request.Request(
            url, headers={"User-Agent": self.user_agent, "Accept": "application/json"}
        )
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.load(resp)
                break
            except urllib.error.HTTPError as e:
                if e.code in (404, 410):
                    raise NotFound(url) from e
                retryable = e.code == 429 or e.code >= 500
                if not retryable or attempt == self.retries:
                    raise
            except urllib.error.URLError:
                if attempt == self.retries:
                    raise
            time.sleep(2 * 2**attempt)
        time.sleep(self.pause)
        self._cache[url] = data
        return data

    def club_members(self, club):
        """All usernames in the club (the API groups them by activity, not join date)."""
        data = self.get(f"{BASE}/club/{club}/members")
        return sorted({m["username"].lower() for group in data.values() for m in group})

    def stats(self, username):
        return self.get(f"{BASE}/player/{username}/stats")

    def archive_months(self, username):
        """Monthly game archive URLs, oldest first. Only months with games are listed."""
        return self.get(f"{BASE}/player/{username}/games/archives")["archives"]

    def month_games(self, url):
        return self.get(url)["games"]
