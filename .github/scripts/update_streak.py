"""Build assets/streak.svg from real GitHub contribution data.

Queries the contribution calendar via GraphQL, computes total / current /
longest streaks, and renders a dark gold card. Only rewrites the file when
the output changes. Never fails the workflow on API errors (keeps last SVG).
"""
import datetime as dt
import json
import os
import urllib.request

USER = "rawalsinghpsnl"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
WEEKS = 18
GOLD = "#D4A017"
BG = "#0d1117"
CARD = "#161b22"
MUTED = "#8b949e"
TEXT = "#f0e6d2"

LEVELS = ["#21262d", "#5a4510", "#8a6a14", "#b8911c", GOLD]


def api(query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-streak-updater",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def level(count):
    if count <= 0:
        return LEVELS[0]
    if count == 1:
        return LEVELS[1]
    if count <= 3:
        return LEVELS[2]
    if count <= 6:
        return LEVELS[3]
    return LEVELS[4]


def short(date_str):
    d = dt.date.fromisoformat(date_str)
    return f"{d.strftime('%b')} {d.day}"


def main():
    if not TOKEN:
        print("GITHUB_TOKEN missing; leaving streak untouched")
        return
    try:
        data = api(
            '{ user(login: "%s") { contributionsCollection {'
            " contributionCalendar { totalContributions weeks {"
            " contributionDays { date contributionCount } } } } } }" % USER
        )
    except Exception as exc:  # noqa: BLE001 - keep last SVG on failure
        print(f"contribution fetch failed, keeping last SVG: {exc}")
        return
    try:
        cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except (KeyError, TypeError):
        print(f"unexpected API shape, keeping last SVG: {data}")
        return

    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    total = cal["totalContributions"]
    today = dt.date.today().isoformat()

    counts = {d["date"]: d["contributionCount"] for d in days}
    ordered = [d["date"] for d in days if d["date"] <= today]

    # Current streak: walk back from today (allow today still in progress).
    cur = 0
    cursor = today
    if counts.get(cursor, 0) == 0:
        cursor = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    while counts.get(cursor, 0) > 0:
        cur += 1
        cursor = (dt.date.fromisoformat(cursor) - dt.timedelta(days=1)).isoformat()
    cur_start = (dt.date.fromisoformat(cursor) + dt.timedelta(days=1)).isoformat()

    # Longest streak + its range.
    best, run, run_start, best_start, best_end = 0, 0, None, None, None
    for date_str in ordered:
        if counts.get(date_str, 0) > 0:
            if run == 0:
                run_start = date_str
            run += 1
            if run > best:
                best, best_start, best_end = run, run_start, date_str
        else:
            run = 0

    def fmt_range(start, end):
        if not start:
            return "—"
        if start == end:
            return short(start)
        return f"{short(start)} - {short(end)}"

    cur_label = f"{short(cur_start)} - Present" if cur else "—"
    long_label = fmt_range(best_start, best_end) if best else "—"
    units = lambda n: "day" if n == 1 else "days"  # noqa: E731

    cells = days[-(WEEKS * 7):]
    while len(cells) < WEEKS * 7:
        cells.insert(0, {"date": "", "contributionCount": 0})
    cols = [cells[i * 7:(i + 1) * 7] for i in range(WEEKS)]
    cell, gap, ox, oy = 11, 4, 26, 118
    rects = []
    for ci, col in enumerate(cols):
        for ri, day in enumerate(col):
            x, y = ox + ci * (cell + gap), oy + ri * (cell + gap)
            rects.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5"'
                f' fill="{level(day["contributionCount"])}">'
                + (f"<title>{day['date']}: {day['contributionCount']}</title>" if day["date"] else "")
                + "</rect>"
            )
    heat = "\n    ".join(rects)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="670" height="248" viewBox="0 0 670 248" font-family="Segoe UI, Ubuntu, Sans-Serif">
  <rect x="0.5" y="0.5" width="669" height="247" rx="10" fill="{CARD}" stroke="#30363d"/>
  <text x="26" y="36" font-size="17" font-weight="700" fill="{TEXT}">Contribution Streak <tspan fill="{GOLD}">⚜</tspan></text>
  <text x="644" y="36" font-size="12" fill="{MUTED}" text-anchor="end">{USER}</text>
  <g text-anchor="middle">
    <text x="125" y="76" font-size="30" font-weight="800" fill="{GOLD}">{total}</text>
    <text x="125" y="94" font-size="11" fill="{MUTED}">Total Contributions</text>
    <text x="335" y="76" font-size="30" font-weight="800" fill="{GOLD}">{cur}</text>
    <text x="335" y="94" font-size="11" fill="{MUTED}">Current Streak ({units(cur)})</text>
    <text x="335" y="108" font-size="10" fill="{MUTED}">{cur_label}</text>
    <text x="545" y="76" font-size="30" font-weight="800" fill="{GOLD}">{best}</text>
    <text x="545" y="94" font-size="11" fill="{MUTED}">Longest Streak ({units(best)})</text>
    <text x="545" y="108" font-size="10" fill="{MUTED}">{long_label}</text>
  </g>
  <g>
    {heat}
  </g>
  <text x="26" y="238" font-size="10" fill="{MUTED}">auto-updated daily from real contributions · less</text>
  <text x="644" y="238" font-size="10" fill="{MUTED}" text-anchor="end">more &#8594;</text>
</svg>
"""
    path = "assets/streak.svg"
    os.makedirs("assets", exist_ok=True)
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    if old != svg:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"streak updated: total={total} current={cur} longest={best}")
    else:
        print("streak already up to date")


if __name__ == "__main__":
    main()
