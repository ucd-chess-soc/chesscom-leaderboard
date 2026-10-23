# UCD Chess Society leaderboard

Every Monday, GitHub Actions fetches the ratings of everyone in the
[UCD Chess Society club on chess.com](https://www.chess.com/club/ucd-chess-society),
publishes a leaderboard website on GitHub Pages and renders Instagram graphics
(1080×1350). Free to run: no server, no API key, no paid services.

## What it shows

- One leaderboard each for **Rapid**, **Blitz** and **Bullet**, plus **Combined**.
- Rating change over the **last week**, **last 30 days** and **this term**, with games played.
- **Combined** change is each player's change per time control, weighted by the
  number of games played in it.
- Only rated, standard-chess games count.

Ratings at past dates come from each player's game archive (every game records
the player's rating after it), so a player who joins mid-term still gets a full
term figure. A player whose first ever game in a time control falls inside the
period (e.g. a fresher who made an account in September) is measured from
their rating after that first game, and marked "new player".

## Weekly operation

Nothing to do. On Monday morning the site updates and the graphics appear on
it under **Graphics**: download and post. If a `DISCORD_WEBHOOK` secret is set,
the weekly graphics are also posted to that Discord channel.

Each week's numbers are saved to `data/history/YYYY-MM-DD.json`, so there is a
permanent record for awards.

## Settings (`config.json`)

| Key | What it does |
| --- | --- |
| `time_classes` | Which leaderboards to show. Add `"daily"` for correspondence chess. |
| `exclude` | Usernames to leave out (e.g. the society's own account). |
| `joined_within_days` | Only include members who joined the chess.com club within this many days (365 = the last year). Set to `null` to include everyone. |
| `display_names` | Optional `{"username": "Real Name"}` shown instead of usernames. The site is public, so only add names of people who are happy to be listed. |
| `periods` | The comparison windows: rolling (`"days": 7`) or fixed (`"since": "2026-09-07"`). **Update the term `since` date each term.** |
| `graphics.movers` | Which periods get "movers" graphics. |
| `graphics.ladder` | Also render "Top rated" graphics per time control. |
| `graphics.rows` / `min_games` | Rows per graphic; games needed to appear on a movers graphic. |

Edit the file on github.com and commit; the next run picks it up. To run
straight away: **Actions → Weekly leaderboard → Run workflow**.

## One-time setup

1. Create a **public** repository on GitHub (ideally under a society
   organisation so it survives committee handovers) and push this folder to it.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
3. **Actions → Weekly leaderboard → Run workflow** to build it for the first time.
4. The site is at `https://<owner>.github.io/<repo>/`.

GitHub pauses scheduled workflows in repositories with no activity for 60 days.
The weekly data commit counts as activity, so this shouldn't happen; if it
does, re-enable the workflow under the Actions tab.

## Running locally

```sh
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # macOS/Linux: .venv/bin/pip
.venv/Scripts/python -m playwright install chromium
.venv/Scripts/python -m leaderboard                 # writes site/ and data/history/
.venv/Scripts/python -m leaderboard --skip-fetch    # re-render from the last saved week
.venv/Scripts/python -m unittest
```

Open `site/index.html` to view.
