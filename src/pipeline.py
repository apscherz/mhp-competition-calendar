from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from ics import Calendar, Event


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"

BJCP_BASE = "https://app.bjcp.org/competition-calendar"


def parse_date(s):
    try:
        return dateparser.parse(s).date()
    except Exception:
        return None


def fetch_bjcp():
    comps = []
    page = 1
    while True:
        url = f"{BJCP_BASE}?order_by=date&page={page}"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        table = soup.find("table")
        if not table:
            break

        rows = table.find_all("tr")
        if len(rows) <= 1:
            break

        for tr in rows[1:]:
            tds = tr.find_all("td")
            if len(tds) < 6:
                continue

            name = tds[3].get_text(strip=True)
            judging = parse_date(tds[1].get_text(strip=True))
            deadline = parse_date(tds[4].get_text(strip=True))
            location = tds[2].get_text(strip=True)

            comps.append({
                "name": name,
                "judging_date": judging.isoformat() if judging else None,
                "entry_deadline": deadline.isoformat() if deadline else None,
                "location": location
            })

        page += 1
        if page > 50:
            break

    return comps


def build_ics(comps):
    cal = Calendar()
    for c in comps:
        if c["entry_deadline"]:
            e = Event()
            e.name = f'{c["name"]} — Entry Deadline'
            e.begin = c["entry_deadline"]
            e.make_all_day()
            e.description = f'Location: {c["location"]}'
            cal.events.add(e)

        if c["judging_date"]:
            e = Event()
            e.name = f'{c["name"]} — Judging Date'
            e.begin = c["judging_date"]
            e.make_all_day()
            e.description = f'Location: {c["location"]}'
            cal.events.add(e)

    return cal


def main():
    DOCS_DIR.mkdir(exist_ok=True)

    comps = fetch_bjcp()

    # Save JSON
    with open(DOCS_DIR / "competitions.json", "w", encoding="utf-8") as f:
        json.dump(comps, f, indent=2)

    # Save ICS
    cal = build_ics(comps)
    with open(DOCS_DIR / "all-us-rolling.ics", "w", encoding="utf-8") as f:
        f.writelines(cal)

    print("Done.")


if __name__ == "__main__":
    main()
