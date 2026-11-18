"""Daily GTA VI news from all over the world (Google News RSS, several queries incl. India + Rockstar official). Headlines only; no article text is copied."""
import re
import sys
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import datetime as dt
from urllib.parse import quote

import requests

QUERIES = [
    ("GTA 6 OR \"GTA VI\" OR \"Grand Theft Auto VI\"", "en-US", "US"),
    ("GTA 6 OR \"GTA VI\" OR \"Grand Theft Auto VI\"", "en-IN", "IN"),
    ("GTA 6 OR \"GTA VI\" OR \"Grand Theft Auto VI\"", "en-GB", "GB"),
    ("GTA 6 OR \"GTA VI\" OR \"Grand Theft Auto VI\"", "en-AU", "AU"),
    ("Rockstar Games GTA VI announcement OR trailer OR update", "en-US", "US"),
    ("Take-Two GTA VI", "en-US", "US"),
]
OFFICIAL = ("rockstar games", "take-two", "rockstargames.com", "newswire")


def _fetch(q, hl, gl):
    url = f"https://news.google.com/rss/search?q={quote(q + ' when:2d')}&hl={hl}&gl={gl}&ceid={gl}:{hl.split('-')[0]}"
    r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    out = []
    for it in ET.fromstring(r.content).iter("item"):
        t = (it.findtext("title") or "").strip()
        src = (it.findtext("source") or "").strip()
        if src and t.endswith(" - " + src):
            t = t[: -len(src) - 3]
        try:
            when = parsedate_to_datetime(it.findtext("pubDate"))
        except Exception:
            when = None
        out.append({"title": t, "source": src or "news", "link": it.findtext("link") or "", "when": when, "region": gl})
    return out


def _key(t):
    return re.sub(r"[^a-z0-9 ]", "", t.lower())[:60]


def fetch(seen=(), limit=14):
    """newest-first, de-duplicated, minus headlines already used. Returns list of dicts (never raises)."""
    items, keys = [], {_key(s) for s in seen}
    for q, hl, gl in QUERIES:
        try:
            items += _fetch(q, hl, gl)
        except Exception as ex:
            print("news fetch failed:", q[:30], gl, str(ex)[:100], file=sys.stderr)
    items.sort(key=lambda x: x["when"] or dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc), reverse=True)
    out = []
    for it in items:
        k = _key(it["title"])
        if len(k) < 15 or k in keys or any(k[:35] in o for o in keys):
            continue
        keys.add(k)
        it["official"] = any(o in (it["source"] + " " + it["link"]).lower() for o in OFFICIAL)
        out.append(it)
        if len(out) >= limit:
            break
    return out


def as_prompt(items):
    return "\n".join(f"- [{'OFFICIAL' if i['official'] else 'REPORTED'}] {i['title']} (source: {i['source']}, {i['region']})" for i in items)
