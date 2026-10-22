"""Building the static leaderboard site and the Instagram graphics (1080x1350 PNGs)."""
import base64
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .board import ladder, movers

TEMPLATES = Path(__file__).resolve().parent / "templates"
ASSETS = Path(__file__).resolve().parent.parent / "assets"

TC_LABELS = {
    "rapid": "Rapid",
    "blitz": "Blitz",
    "bullet": "Bullet",
    "daily": "Daily",
    "combined": "Combined",
}


def _date(iso):
    d = datetime.fromisoformat(iso)
    return f"{d.day} {d:%b %Y}"


def _range(since_iso, until_iso):
    since, until = datetime.fromisoformat(since_iso), datetime.fromisoformat(until_iso)
    if since.year == until.year:
        return f"{since.day} {since:%b} – {until.day} {until:%b %Y}"
    return f"{_date(since_iso)} – {_date(until_iso)}"


def _signed(value):
    value = round(value)
    return f"+{value}" if value > 0 else ("±0" if value == 0 else f"−{-value}")


def _env():
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape())
    env.filters["signed"] = _signed
    return env


def graphics_plan(week, config):
    """Every graphic to render: one card per (period, board) for movers, plus ladders."""
    g = config["graphics"]
    boards = week["boards"]
    generated = week["generated_at"]
    cards = []
    for key in g["movers"]:
        period = week["periods"][key]
        when = (
            _range(period["since"], generated)
            if period["rolling"]
            else f"Since {_date(period['since'])}"
        )
        for tc in [*week["time_classes"], "combined"]:
            cards.append(
                {
                    "file": f"{key}-{tc}.png",
                    "kind": "movers",
                    "period": key,
                    "board": tc,
                    "title": period["headline"],
                    "subtitle": TC_LABELS[tc],
                    "when": when,
                    "rows": movers(boards[tc], key, g["min_games"], g["rows"]),
                }
            )
    if g["ladder"]:
        for tc in week["time_classes"]:
            cards.append(
                {
                    "file": f"ladder-{tc}.png",
                    "kind": "ladder",
                    "board": tc,
                    "title": "Top rated",
                    "subtitle": TC_LABELS[tc],
                    "when": f"As of {_date(generated)}",
                    "rows": ladder(boards[tc], g["rows"]),
                }
            )
    return cards


def _logo_data_uri():
    data = base64.b64encode((ASSETS / "bishop.png").read_bytes()).decode()
    return f"data:image/png;base64,{data}"


def render_site(week, config, out_dir, images=True):
    env = _env()
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "graphics").mkdir(parents=True)
    for asset in ("logo.png", "bishop.png"):
        shutil.copy(ASSETS / asset, out_dir / asset)

    cards = graphics_plan(week, config)
    if images:
        _render_cards(env, cards, week, config, out_dir / "graphics")

    boards = [
        {"key": tc, "label": TC_LABELS[tc], "rows": week["boards"][tc]}
        for tc in [*week["time_classes"], "combined"]
    ]
    data = {"periods": week["periods"], "boards": boards}
    html = env.get_template("site.html").render(
        club=config["club"],
        updated=_date(week["generated_at"]),
        periods=week["periods"],
        boards=boards,
        data_json=json.dumps(data).replace("</", "<\\/"),
        cards=cards if images else [],
    )
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    (out_dir / "data.json").write_text(json.dumps(week, indent=1), encoding="utf-8")
    print(f"built {out_dir}", file=sys.stderr)


def _render_cards(env, cards, week, config, out_dir):
    from playwright.sync_api import sync_playwright

    template = env.get_template("card.html")
    logo = _logo_data_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for card in cards:
            page.set_content(
                template.render(card=card, logo=logo, club=config["club"]),
                wait_until="networkidle",
            )
            page.evaluate("document.fonts.ready")
            page.screenshot(path=str(out_dir / card["file"]))
            print(f"  graphic {card['file']}", file=sys.stderr)
        browser.close()
