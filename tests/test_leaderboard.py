import unittest

from leaderboard.board import build_boards, movers
from leaderboard.ratings import current_rating, games_by_class, period_summary, rating_at


def game(t, white, white_rating, black, black_rating, time_class="blitz", rated=True, rules="chess"):
    return {
        "end_time": t,
        "time_class": time_class,
        "rated": rated,
        "rules": rules,
        "white": {"username": white, "rating": white_rating},
        "black": {"username": black, "rating": black_rating},
    }


class RatingsTest(unittest.TestCase):
    def test_games_by_class_filters_unrated_and_variants(self):
        games = [
            game(1, "Alice", 1500, "bob", 1400),
            game(2, "bob", 1410, "alice", 1490, time_class="rapid"),
            game(3, "alice", 1505, "bob", 1395, rated=False),
            game(4, "alice", 1600, "carol", 1700, rules="chess960"),
            game(5, "carol", 1700, "dave", 1800),
        ]
        self.assertEqual(
            games_by_class(games, "alice"), {"blitz": [(1, 1500)], "rapid": [(2, 1490)]}
        )

    def test_rating_at_uses_last_game_at_or_before(self):
        history = [(10, 1500), (20, 1510), (30, 1520)]
        self.assertIsNone(rating_at(history, 5))
        self.assertEqual(rating_at(history, 20), 1510)
        self.assertEqual(rating_at(history, 25), 1510)
        self.assertEqual(rating_at(history, 99), 1520)

    def test_period_summary(self):
        history = [(10, 1500), (20, 1510), (30, 1520)]
        self.assertEqual(
            period_summary(history, 1520, 15), {"start": 1500, "games": 2, "new": False}
        )
        self.assertEqual(
            period_summary(history, 1520, 40), {"start": 1520, "games": 0, "new": False}
        )
        # First ever game is inside the window: measured from the rating after it.
        self.assertEqual(
            period_summary(history, 1520, 5), {"start": 1500, "games": 3, "new": True}
        )

    def test_current_rating_prefers_newer_source(self):
        history = [(10, 1500), (30, 1520)]
        self.assertEqual(current_rating(history, {"last": {"date": 20, "rating": 1510}}), 1520)
        self.assertEqual(current_rating(history, {"last": {"date": 40, "rating": 1530}}), 1530)
        self.assertEqual(current_rating([], None), None)


def week(start, games, new=False):
    return {"start": start, "games": games, "new": new}


class BoardTest(unittest.TestCase):
    def setUp(self):
        self.players = {
            "alice": {
                "blitz": {"current": 1550, "periods": {"week": week(1500, 80)}},
                "rapid": {"current": 1390, "periods": {"week": week(1400, 1)}},
            },
            "bob": {
                "blitz": {"current": 1200, "periods": {"week": week(1200, 0)}},
            },
            "carol": {
                "bullet": {"current": 900, "periods": {"week": week(800, 4, new=True)}},
            },
        }
        self.boards = build_boards(
            self.players, ["rapid", "blitz", "bullet"], ["week"], {"alice": "Alice A"}
        )

    def test_time_class_board(self):
        blitz = {r["username"]: r for r in self.boards["blitz"]}
        self.assertEqual(set(blitz), {"alice", "bob"})
        self.assertEqual(
            blitz["alice"]["periods"]["week"], {"delta": 50, "games": 80, "new": False}
        )
        self.assertEqual(blitz["alice"]["name"], "Alice A")
        self.assertEqual(blitz["bob"]["name"], "bob")

    def test_combined_is_games_weighted(self):
        combined = {r["username"]: r for r in self.boards["combined"]}
        # (50 * 80 + -10 * 1) / 81
        self.assertEqual(
            combined["alice"]["periods"]["week"], {"delta": 49.3, "games": 81, "new": False}
        )
        self.assertEqual(combined["bob"]["periods"]["week"], {"delta": 0, "games": 0, "new": False})
        self.assertEqual(
            combined["carol"]["periods"]["week"], {"delta": 100, "games": 4, "new": True}
        )

    def test_movers_ranks_by_change_and_needs_games(self):
        ranked = movers(self.boards["combined"], "week", min_games=1, limit=10)
        self.assertEqual([r["username"] for r in ranked], ["carol", "alice"])


if __name__ == "__main__":
    unittest.main()
