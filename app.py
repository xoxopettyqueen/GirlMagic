# -*- coding: utf-8 -*-
"""
Girl Magic Odds 2.0 — chaos glow.
Gap math and grader are unchanged. This is the skin.
"""
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Girl Magic Odds 2.0", page_icon="✨", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
.stApp{background:linear-gradient(180deg,#0b0b0f 0%,#1a1a24 100%)!important;color:#fff!important;font-family:'Inter',sans-serif!important}
h1{font-family:'Inter',sans-serif!important;font-weight:700!important;font-size:2.1rem!important;margin:0!important;background:linear-gradient(90deg,#ff00cc,#b366ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.pulse-bar{height:6px;border-radius:999px;margin:8px 0 14px;background:linear-gradient(90deg,#ff00cc,#6600ff,#b366ff,#ff00cc);background-size:200% 100%;animation:shimmer 3s linear infinite,pulse 3s ease-in-out infinite;box-shadow:0 0 16px #ff00cc88}
@keyframes shimmer{0%{background-position:0 0}100%{background-position:200% 0}}
@keyframes pulse{0%,100%{opacity:.85;filter:brightness(1)}50%{opacity:1;filter:brightness(1.25)}}
.how-to{background:#14141c;border:1px solid #ff00cc55;border-radius:999px;padding:8px 16px;margin-bottom:12px;font-size:.8rem;color:#f3e8ff;box-shadow:0 0 12px #ff00cc33}
.stButton>button{background:linear-gradient(90deg,#ff00cc,#6600ff)!important;color:#fff!important;border:none!important;border-radius:999px!important;font-weight:700!important;box-shadow:0 0 14px #ff00cc66!important;transition:transform .15s,box-shadow .15s}
.stButton>button:hover{transform:scale(1.03);box-shadow:0 0 22px #ff00ccaa!important}
.counters{display:flex;gap:14px;margin:8px 0 16px;flex-wrap:wrap}
.counter{padding:12px 18px;border-radius:14px;color:#fff;min-width:110px;animation:pulse 2s infinite;box-shadow:0 0 18px #ff00cc55}
.counter b{display:block;font-size:1.4rem}
.counter.locked{background:#ff00cc}
.counter.done{background:#6600ff}
.counter.hits{background:gold;color:#1a1020;box-shadow:0 0 18px gold}
.counter.miss{background:#2a2a34;box-shadow:0 0 12px #444}
.game-header{font-size:1rem;font-weight:700;color:#ffb3ea;margin:16px 0 8px}
.card{margin-bottom:16px;padding:18px;border-radius:22px;background:linear-gradient(165deg,#1A1A22 0%,#14141A 70%);border:1px solid #FF4EC8;box-shadow:0 8px 28px #FF4EC833;transition:transform .25s ease,box-shadow .25s ease}
.card:hover{transform:scale(1.015);box-shadow:0 0 22px #ff00cc88}
.card.hit{border-color:gold;box-shadow:0 0 18px gold}
.card.miss{border-color:#3A3A42;opacity:.75;box-shadow:none}
.card.take{animation:heartbeat 1.6s ease-in-out infinite}
@keyframes heartbeat{0%,100%{box-shadow:0 8px 28px #FF4EC833}50%{box-shadow:0 8px 36px #FFD44766}}
.card.wait{border-color:#6600ff;box-shadow:0 0 14px #6600ff66;animation:pulse 2.4s infinite}
.player{font-weight:800;font-size:1.25rem;letter-spacing:-.01em}
.prop{color:#ffd0f2;font-size:.85rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin:4px 0 8px}
.books{display:flex;flex-wrap:wrap;gap:5px}
.bk{background:#12121a;border:1px solid #6600ff;border-radius:999px;padding:3px 8px;font-size:.66rem;font-weight:700}
.bk.best{background:#ff00cc;border-color:#ffd0f2;box-shadow:0 0 10px #ff00cc88}
.nums{float:right;text-align:right}
.pill{display:inline-block;background:#ff00cc;color:#fff;font-weight:800;font-size:.66rem;padding:3px 9px;border-radius:999px;box-shadow:0 0 10px #ff00cc88}
.pill.hit{background:gold;color:#1a1020;box-shadow:0 0 12px gold}
.pill.miss{background:#444}
.ev{display:block;color:#ffe27a;font-weight:700;margin-top:4px}
.why{color:#f3e8ff;font-size:.74rem;margin-top:6px;clear:both}
.tag{display:inline-block;background:#2a1040;color:#f3e8ff;border:1px solid #b366ff;border-radius:999px;padding:2px 7px;font-size:.6rem;margin:3px 3px 0 0}
.rate-chip{display:inline-block;background:#1a1a24;border:1px solid #b366ff;border-radius:14px;padding:10px 12px;margin:4px;text-align:center;min-width:84px;box-shadow:0 0 10px #6600ff44}
.rate-chip.hot{border-color:gold;box-shadow:0 0 14px gold}
.rate-chip b{display:block;font-size:1.1rem}
.rate-chip span{font-size:.62rem;color:#ddd}
.glossary{background:#14141c;border:1px solid #ff00cc66;border-radius:16px;padding:16px;box-shadow:0 0 16px #ff00cc33;line-height:1.65}
.glossary strong{color:#ffb3ea}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
BDL_BASE = "https://api.balldontlie.io/nba/v1"
LEDGER = Path("odds_ledger.json")
SHARPNESS = Path("book_sharpness.json")
WEIGHTS_FILE = Path("auto_weights.json")
MY_BOOKS = {
    "fanduel": "FD", "draftkings": "DK", "betmgm": "MGM", "bet365": "365",
    "williamhill_us": "CZR", "fanatics": "FAN", "espnbet": "SCR",
    "hardrockbet": "HR", "hardrockbet_az": "HR", "hardrockbet_oh": "HR", "hardrockbet_fl": "HR",
    "pinnacle": "PIN", "circa": "CIR", "bookmaker": "BM",
}
BOOK_FULL = {"FD": "FanDuel", "DK": "DraftKings", "MGM": "BetMGM", "365": "Bet365", "CZR": "Caesars", "FAN": "Fanatics", "SCR": "theScore", "HR": "Hard Rock", "PIN": "Pinnacle", "CIR": "Circa", "BM": "Bookmaker"}
ALL_BOOK_CODES = sorted(BOOK_FULL)
BASE_WEIGHTS = {"PIN": 3.5, "CIR": 3.0, "BM": 2.8, "FD": 2.0, "DK": 1.8, "365": 2.0, "MGM": 1.4, "CZR": 1.3, "FAN": 1.2, "SCR": 1.1, "HR": 1.1}
GLOSSARY = """
<strong>Be a better bettor. Crack the code.</strong> The longest number against the pack is the tell. These books are cooked.<br><br>
<strong>True EV</strong> — the real juice. Longest price against the weighted blend.<br>
<strong>Gap</strong> — how far she stands from the crowd. Big gap, one book out on her own.<br>
<strong>Spike</strong> — gap plus how far the books are apart. High spike is a TAKE.<br>
<strong>Solo</strong> — one book standing alone with the long number.<br>
<strong>Soft book</strong> — keeps hanging the long number, and those plays cash.<br>
<strong>Grader</strong> — NBA uses your BallDontLie GOAT key. NFL uses ESPN finals. The gold line is the number it used. If that number is wrong, the grade is wrong.<br>
<strong>How to read a chart</strong> — gold is a hit, pink or gray is a miss. The donut is the whole slate. The scatter is gap on the bottom, edge up the side. Top-right is the chaos that also had juice.
"""

def secret(name):
    try:
        return st.secrets.get(name, "") or ""
    except Exception:
        return ""


def in_user_range(prop, line):
    try:
        line = float(line)
    except Exception:
        return False
    if prop == "Assists":
        return 3 <= line <= 8
    if prop == "Points":
        return 8 <= line <= 15
    if prop == "Rebounds":
        return 4 <= line <= 10
    return prop in ("DoubleDouble", "Anytime TD")


def line_ok(prop, line):
    try:
        line = float(line)
    except Exception:
        return True
    if prop == "Points":
        return line <= 40
    if prop == "Rebounds":
        return line <= 20
    if prop == "Assists":
        return line <= 16
    if prop == "Rec Yards":
        return line <= 50
    return True


def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return default


def save_json(path, data):
    try:
        path.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def load_sharpness():
    return load_json(SHARPNESS, {})


def save_sharpness(data):
    save_json(SHARPNESS, data)


def load_auto_weights():
    out = BASE_WEIGHTS.copy()
    out.update(load_json(WEIGHTS_FILE, {}) or {})
    return out


def save_auto_weights(w):
    save_json(WEIGHTS_FILE, w)


def update_auto_weights(sharp):
    current = load_auto_weights()
    for bk, data in (sharp or {}).items():
        total = data.get("total", 0)
        soft = data.get("soft_count", 0)
        if total < 10:
            continue
        rate = soft / total
        base = BASE_WEIGHTS.get(bk, 1.0)
        if rate > 0.25:
            current[bk] = max(0.8, round(base * 0.75, 2))
        elif rate > 0.15:
            current[bk] = max(0.9, round(base * 0.85, 2))
        else:
            current[bk] = round(min(3.5, base * 1.05), 2)
    save_auto_weights(current)
    return current


def implied(price):
    try:
        p = int(price)
    except Exception:
        return None
    if p > 0:
        return 100 / (p + 100)
    if p < 0:
        return abs(p) / (abs(p) + 100)
    return None


SHARP = {"PIN", "CIR", "BM"}

def weighted_fair_prob(book_prices, weights=None):
    weights = weights or load_auto_weights()
    sharp_prices = {bk: px for bk, px in (book_prices or {}).items() if bk in SHARP}
    source = sharp_prices if sharp_prices else (book_prices or {})
    weighted, total_w = [], 0.0
    for bk, price in source.items():
        w = float(weights.get(bk, 1.0) or 1.0)
        imp = implied(price)
        if w > 0 and imp and 0 < imp < 1:
            weighted.append(imp * w)
            total_w += w
    if not weighted or not total_w:
        return None
    return max(0.05, min(0.85, sum(weighted) / total_w))


def compute_true_ev(best_price, fair_prob):
    if not fair_prob or best_price is None:
        return None
    try:
        decimal = (best_price / 100 + 1) if int(best_price) > 0 else (100 / abs(int(best_price)) + 1)
        return round(max(-20, min(80, (fair_prob * decimal - 1) * 100)), 1)
    except Exception:
        return None


def card_score(true_ev, spike):
    raw = (max(0, true_ev or 0) * 0.25) + ((spike or 0) * 4)
    return round(max(1.0, min(10.0, raw)), 1)


def plain_reason(c):
    bk = c.get("book") or "A book"
    tev = c.get("true_ev")
    tev_txt = f"{tev}%" if tev is not None else "n/a"
    gap = c.get("ev_gap")
    gap_txt = f"{gap}%" if gap is not None else "n/a"
    if c.get("decision") == "TAKE" and (tev or 0) >= 3:
        return f"{bk} is the long number. Gap {gap_txt} vs the pack. Edge {tev_txt}."
    if c.get("decision") == "TAKE":
        return f"Books disagree. {bk} is longest. Gap {gap_txt}."
    return "Tight. The books agree. Skip."


def normalize_prop(name):
    n = str(name or "").lower().replace(" ", "").replace("_", "").replace("-", "")
    if "double" in n or n in ("dd",):
        return "DoubleDouble"
    if "assist" in n:
        return "Assists"
    if "rebound" in n or n in ("reb", "rebs"):
        return "Rebounds"
    if "point" in n and "three" not in n:
        return "Points"
    if "recyard" in n or "receivingyard" in n:
        return "Rec Yards"
    if "td" in n or "touchdown" in n:
        return "Anytime TD"
    return name

def normalize_book(key):
    k = str(key or "").lower()
    for needle, name in (
        ("pinnacle", "pinnacle"), ("circa", "circa"), ("bookmaker", "bookmaker"),
        ("bet365", "bet365"), ("fanatic", "fanatics"), ("hardrock", "hardrockbet"),
        ("espnbet", "espnbet"), ("score", "espnbet"), ("draftking", "draftkings"),
        ("fanduel", "fanduel"), ("betmgm", "betmgm"), ("williamhill", "williamhill_us"),
        ("caesar", "williamhill_us"),
    ):
        if needle in k:
            return name
    return k


def load_ledger():
    rows = load_json(LEDGER, None)
    rows = st.session_state.get("ledger", []) if rows is None else rows
    kept, seen = [], set()
    for r in rows:
        key = (r.get("sport"), _norm_name(r.get("player")), r.get("prop"), round(float(r.get("line") or 0), 1), r.get("event"))
        if key in seen:
            continue
        seen.add(key)
        kept.append(r)
    return kept


def save_ledger(rows):
    st.session_state["ledger"] = rows
    save_json(LEDGER, rows)


def _norm_name(s):
    return re.sub(r"[^a-z]", "", str(s or "").lower())


def bdl_get(path, key, params=None):
    r = requests.get(
        f"{BDL_BASE}/{path}",
        headers={"Authorization": key},
        params=params or {},
        timeout=25,
    )
    body = r.json() if r.status_code == 200 else {"error": (r.text or "")[:220]}
    return r.status_code, body


def teams_in(event):
    parts = [x.strip() for x in str(event or "").split("@")]
    return [p for p in parts if p]


def event_matches(event, home, away):
    blob = str(event or "").lower()
    if not blob:
        return True
    def token(name):
        parts = [w for w in str(name or "").lower().replace(".", "").split() if w not in ("the", "at")]
        return parts[-1] if parts else ""
    ht, at = token(home), token(away)
    return (ht and ht in blob) or (at and at in blob)


def grade_nba(ledger, bdl_key, days=6, regrade=False):
    if not bdl_key:
        return ledger, "No BallDontLie key. Add BALLDONTLIE_API_KEY to secrets."
    if regrade:
        for r in ledger:
            if r.get("sport") == "NBA":
                r["result"] = None
                r["player_stat"] = None
    pending = [
        r for r in ledger
        if r.get("sport") == "NBA" and r.get("result") in (None, "", "—")
        and r.get("prop") in ("Assists", "Points", "Rebounds", "DoubleDouble")
        and line_ok(r.get("prop"), r.get("line"))
    ]
    if not pending:
        return ledger, "NBA: nothing left to grade."
    pending = pending[:30]
    by_name = defaultdict(list)
    for row in pending:
        by_name[_norm_name(row.get("player"))].append(row)
    updated, skipped, notes = 0, 0, []
    for back in range(days):
        day = (datetime.now(timezone.utc) - timedelta(days=back)).strftime("%Y-%m-%d")
        status, games = bdl_get("games", bdl_key, {"dates[]": day, "per_page": 30})
        if status != 200:
            notes.append(f"{day} games {status}")
            continue
        game_rows = games.get("data") or []
        ids = [g.get("id") for g in game_rows if g.get("id")]
        if not ids:
            continue
        names = {}
        for g in game_rows:
            home = ((g.get("home_team") or {}).get("full_name")) or ""
            away = ((g.get("visitor_team") or {}).get("full_name")) or ""
            names[g.get("id")] = (home, away)
        page, all_stats = 1, []
        while page <= 8:
            status, stats = bdl_get("stats", bdl_key, {"game_ids[]": ids, "per_page": 100, "page": page})
            if status != 200:
                notes.append(f"{day} stats {status}")
                break
            chunk = stats.get("data") or []
            all_stats.extend(chunk)
            if len(chunk) < 100:
                break
            page += 1
        for stat in all_stats:
            player = stat.get("player") or {}
            full = _norm_name(f"{player.get('first_name', '')} {player.get('last_name', '')}")
            gid = (stat.get("game") or {}).get("id") or stat.get("game_id")
            home, away = names.get(gid, ("", ""))
            pts, reb, ast = stat.get("pts"), stat.get("reb"), stat.get("ast")
            if pts is None and reb is None and ast is None:
                continue
            for row in by_name.get(full) or []:
                if row.get("result") in ("HIT", "MISS", "N/A"):
                    continue
                if row.get("event") and not event_matches(row.get("event"), home, away):
                    continue
                prop = row.get("prop")
                line = float(row.get("line") or 0)
                actual = {"Points": pts, "Rebounds": reb, "Assists": ast}.get(prop)
                if prop == "DoubleDouble":
                    if None in (pts, reb, ast):
                        continue
                    actual = 1 if sum(float(x) >= 10 for x in (pts, reb, ast)) >= 2 else 0
                    line = 1
                if actual is None:
                    row["result"] = "N/A"
                    row["grade_note"] = "stat missing"
                    skipped += 1
                    continue
                actual = float(actual)
                row["result"] = "HIT" if actual >= line else "MISS"
                row["player_stat"] = actual
                row["grade_note"] = f"{prop} {actual} vs {line} · {away} @ {home}"
                row["graded_ts"] = datetime.now().isoformat(timespec="minutes")
                updated += 1
    leftover = [r for r in pending if r.get("result") in (None, "", "—")]
    by_player_stats = defaultdict(list)
    for back in range(days):
        day = (datetime.now(timezone.utc) - timedelta(days=back)).strftime("%Y-%m-%d")
        status, games = bdl_get("games", bdl_key, {"dates[]": day, "per_page": 30})
        if status != 200:
            continue
        ids = [g.get("id") for g in (games.get("data") or []) if g.get("id")]
        if not ids:
            continue
        status, stats = bdl_get("stats", bdl_key, {"game_ids[]": ids, "per_page": 100})
        if status != 200:
            continue
        for stat in stats.get("data") or []:
            player = stat.get("player") or {}
            full = _norm_name(f"{player.get('first_name', '')} {player.get('last_name', '')}")
            by_player_stats[full].append(stat)
    for row in leftover:
        stats = by_player_stats.get(_norm_name(row.get("player"))) or []
        if len(stats) != 1:
            continue
        stat = stats[0]
        pts, reb, ast = stat.get("pts"), stat.get("reb"), stat.get("ast")
        prop = row.get("prop")
        line = float(row.get("line") or 0)
        actual = {"Points": pts, "Rebounds": reb, "Assists": ast}.get(prop)
        if prop == "DoubleDouble" and None not in (pts, reb, ast):
            actual = 1 if sum(float(x) >= 10 for x in (pts, reb, ast)) >= 2 else 0
            line = 1
        if actual is None:
            continue
        actual = float(actual)
        row["result"] = "HIT" if actual >= line else "MISS"
        row["player_stat"] = actual
        row["grade_note"] = f"{prop} {actual} vs {line} · only game in window"
        row["graded_ts"] = datetime.now().isoformat(timespec="minutes")
        updated += 1
    save_ledger(ledger)
    msg = f"NBA graded {updated}. Left {skipped} as N/A."
    if notes:
        msg += " API: " + ", ".join(notes[:3])
    return ledger, msg



def espn(url, params=None):
    try:
        r = requests.get(url, params=params or {}, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def grade_nfl(ledger, days=6, regrade=False):
    if regrade:
        for r in ledger:
            if r.get("sport") == "NFL":
                r["result"] = None
                r["player_stat"] = None
    pending = [
        r for r in ledger
        if r.get("sport") == "NFL" and r.get("result") in (None, "", "—")
        and r.get("prop") in ("Anytime TD", "Rec Yards")
        and line_ok(r.get("prop"), r.get("line"))
    ]
    if not pending:
        return ledger, "NFL: nothing left to grade."
    pending = pending[:30]
    updated = 0
    for back in range(days):
        day = (datetime.now(timezone.utc) - timedelta(days=back)).strftime("%Y%m%d")
        board = espn("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard", {"dates": day})
        for ev in board.get("events") or []:
            comp = (ev.get("competitions") or [{}])[0]
            if ((comp.get("status") or {}).get("type") or {}).get("state") != "post":
                continue
            teams = [((t.get("team") or {}).get("displayName") or "") for t in (comp.get("competitors") or [])]
            box = espn("https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary", {"event": ev.get("id")})
            by_player = {}
            for team in ((box.get("boxscore") or {}).get("players") or []):
                for block in team.get("statistics") or []:
                    name = str(block.get("name") or "").lower()
                    labels = [str(x).lower() for x in (block.get("labels") or [])]
                    for ath in block.get("athletes") or []:
                        nm = ((ath.get("athlete") or {}).get("displayName")) or ""
                        key = _norm_name(nm)
                        stats = ath.get("stats") or []
                        row = by_player.setdefault(key, {"name": nm})
                        mapped = {labels[i]: stats[i] for i in range(min(len(labels), len(stats)))}
                        if "receiving" in name and "yds" in mapped:
                            row["receiving_yards"] = mapped.get("yds")
                        if "rushing" in name and "yds" in mapped:
                            row["rushing_yards"] = mapped.get("yds")
                        if "td" in mapped:
                            row.setdefault("td_parts", []).append(mapped.get("td"))
            for rec in pending:
                if rec.get("result") in ("HIT", "MISS", "N/A"):
                    continue
                if rec.get("event") and not any(t and t.lower() in str(rec.get("event")).lower() for t in teams):
                    continue
                key = _norm_name(rec.get("player"))
                hit = by_player.get(key)
                if not hit:
                    continue
                if rec.get("prop") == "Anytime TD":
                    td = 0.0
                    for v in hit.get("td_parts") or []:
                        try:
                            td += float(v)
                        except Exception:
                            pass
                    rec["result"] = "HIT" if td > 0 else "MISS"
                    rec["player_stat"] = td
                    rec["grade_note"] = f"touchdowns {td} · {' @ '.join(teams)}"
                elif rec.get("prop") == "Rec Yards":
                    raw = hit.get("receiving_yards")
                    if raw is None:
                        rec["result"] = "N/A"
                        rec["grade_note"] = "receiving_yards missing"
                        continue
                    try:
                        yds = float(str(raw).split("-")[-1])
                    except Exception:
                        rec["result"] = "N/A"
                        rec["grade_note"] = "receiving_yards unreadable"
                        continue
                    rec["result"] = "HIT" if yds >= float(rec.get("line") or 0) else "MISS"
                    rec["player_stat"] = yds
                    rec["grade_note"] = f"receiving_yards {yds} vs {rec.get('line')} · {' @ '.join(teams)}"
                rec["graded_ts"] = datetime.now().isoformat(timespec="minutes")
                updated += 1
    save_ledger(ledger)
    return ledger, f"NFL graded {updated}."


@st.cache_data(ttl=120)
def fetch_events(api_key, sport_key):
    try:
        r = requests.get(f"{ODDS_API_BASE}/sports/{sport_key}/events", params={"apiKey": api_key}, timeout=15)
        if r.status_code == 200:
            return r.json() or []
    except Exception:
        pass
    return []


@st.cache_data(ttl=45)
def fetch_odds(api_key, sport_key, event_id, markets):
    try:
        r = requests.get(
            f"{ODDS_API_BASE}/sports/{sport_key}/events/{event_id}/odds",
            params={"apiKey": api_key, "regions": "us,us2,uk", "markets": markets, "oddsFormat": "american"},
            timeout=20,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def parse_plays(data, sport):
    if not data:
        return []
    event = f"{data.get('away_team')} @ {data.get('home_team')}"
    plays = []
    for book in data.get("bookmakers") or []:
        bk = normalize_book(book.get("key"))
        if bk not in MY_BOOKS:
            continue
        short = MY_BOOKS[bk]
        for market in book.get("markets") or []:
            mkey = (market.get("key") or "").lower()
            prop = None
            if sport == "NBA":
                if "assist" in mkey:
                    prop = "Assists"
                elif "point" in mkey and "rebound" not in mkey and "assist" not in mkey:
                    prop = "Points"
                elif "rebound" in mkey and "point" not in mkey:
                    prop = "Rebounds"
                elif "double_double" in mkey:
                    prop = "DoubleDouble"
            elif "anytime_td" in mkey:
                prop = "Anytime TD"
            elif "reception_yds" in mkey or "receiving_yds" in mkey:
                prop = "Rec Yards"
            if not prop:
                continue
            for o in market.get("outcomes") or []:
                name = str(o.get("name") or "").lower().strip()
                desc = str(o.get("description") or "").lower().strip()
                blob = f"{name} {desc}"
                over = name in ("over", "yes", "o") or "over" in name or "+" in blob or "or more" in blob
                if prop in ("DoubleDouble", "Anytime TD"):
                    if "yes" not in name and name not in ("over", "yes"):
                        continue
                    player, line = o.get("description") or o.get("name"), (0.5 if prop == "Anytime TD" else 1.0)
                else:
                    if not over:
                        continue
                    player = o.get("description") or o.get("name")
                    line = o.get("point")
                    if line is None:
                        m = re.search(r"(\d+\.?\d*)", blob)
                        if not m:
                            continue
                        line = float(m.group(1))
                    else:
                        line = float(line)
                if not player or str(player).lower() in ("yes", "no", "over", "under"):
                    continue
                try:
                    price = int(o.get("price"))
                except Exception:
                    continue
                plays.append({"sport": sport, "event": event, "player": player, "prop": prop, "line": line, "price": price, "book": short})
    return plays


def compute_signals(book_prices, best_price):
    prices = list((book_prices or {}).values())
    if not prices:
        return {}, "PASS"
    med = sorted(prices)[len(prices) // 2]
    longest = max(prices)
    ev_gap = (longest - med) / med if med else 0
    spread = (max(prices) - min(prices)) / abs(med) if med else 0
    vol = "High" if spread > 0.4 else "Medium" if spread > 0.15 else "Low"
    move = "Snap" if spread > 0.5 else "Drift" if spread > 0.2 else "Freeze"
    book_beh = "Solo" if len(prices) <= 2 or (longest - med) / med > 0.6 else "Cluster"
    spike = ev_gap + (0.3 if vol == "High" else 0.15 if vol == "Medium" else 0.05) * spread
    decision = "TAKE" if spike > 0.25 and vol != "Low" else "LEAN" if spike > 0.08 else "PASS"
    return {
        "median": int(med), "longest": longest, "ev_gap": round(ev_gap * 100, 1),
        "vol": vol, "move": move, "book_beh": book_beh, "spike": round(spike, 2), "decision": decision,
    }, decision


def update_sharpness(cards):
    sharp = load_sharpness()
    for c in cards:
        bk = c.get("book")
        if not bk:
            continue
        sharp.setdefault(bk, {"soft_count": 0, "total": 0, "props": {}})
        sharp[bk]["total"] += 1
        if c.get("decision") == "TAKE" and (c.get("true_ev") or 0) >= 2:
            sharp[bk]["soft_count"] += 1
            prop = c.get("prop", "Other")
            sharp[bk]["props"][prop] = sharp[bk]["props"].get(prop, 0) + 1
    save_sharpness(sharp)
    return sharp



def worth_locking(c):
    if c.get("decision") != "TAKE":
        return False
    if (c.get("price") or 0) < 500:
        return False
    if (c.get("true_ev") or 0) < 4:
        return False
    if not in_user_range(c.get("prop"), c.get("line")):
        return False
    return True



@st.cache_data(ttl=60)
def sgo_fair(sgo_key, player, prop):
    if not sgo_key:
        return None
    try:
        r = requests.get(
            "https://api.sportsgameodds.com/v2/events",
            headers={"x-api-key": sgo_key},
            params={"leagueID": "NBA", "oddsAvailable": "true", "limit": 5},
            timeout=12,
        )
        if r.status_code != 200:
            return None
        stat = {"Points": "points", "Rebounds": "rebounds", "Assists": "assists"}.get(prop)
        if not stat:
            return None
        token = _norm_name(player).replace(" ", "_").upper()
        for ev in (r.json().get("data") or []):
            for odd in (ev.get("odds") or {}).values():
                if stat in str(odd.get("statID") or "") and token.split("_")[-1] in str(odd.get("playerID") or "").upper():
                    fo = odd.get("fairOdds")
                    if fo:
                        return int(str(fo).replace("+", ""))
    except Exception:
        return None
    return None

def best_cards(plays, weights=None):
    by = defaultdict(list)
    for p in plays:
        by[(p["sport"], p["player"], p["prop"], round(float(p["line"]), 1), p["event"])].append(p)
    cards, sharp = [], load_sharpness()
    for group in by.values():
        best = max(group, key=lambda x: x["price"])
        book_prices = {g["book"]: g["price"] for g in group}
        signals, decision = compute_signals(book_prices, best["price"])
        fair = weighted_fair_prob(book_prices, weights)
        true_ev = compute_true_ev(best["price"], fair)
        petty = in_user_range(best["prop"], best["line"])
        tags = []
        if signals.get("book_beh") == "Solo":
            tags.append("Solo")
        if signals.get("move") == "Snap":
            tags.append("Snap")
        if signals.get("vol") == "High":
            tags.append("Surge")
        if best["book"] in sharp and sharp[best["book"]].get("soft_count", 0) >= 3:
            tags.append(f"{best['book']} soft")
        if true_ev and true_ev >= 3:
            tags.append("Gap")
        tags.append("In range" if petty else "Wide")
        cards.append({
            **best, "book_prices": book_prices, **signals, "tags": tags, "decision": decision,
            "fair_prob": round(fair * 100, 1) if fair else None, "true_ev": true_ev,
            "petty_range_match": petty, "score": card_score(true_ev, signals.get("spike")),
        })
    cards.sort(key=lambda x: (-(x.get("true_ev") or -999), x.get("event") or ""))
    return cards


def fmt_price(px):
    try:
        return f"{int(px):+d}"
    except Exception:
        return "—"



def fmt_price(px):
    try:
        return f"{int(px):+d}"
    except Exception:
        return "—"



LEAGUE_AVG = {"Points": 112.0, "Assists": 26.0, "Rebounds": 44.0}

def dvp_answer(player, prop, event, bdl_key):
    """What this defense allows of this stat to this position."""
    if not bdl_key or prop not in ("Points", "Rebounds", "Assists"):
        return None
    cache = st.session_state.setdefault("dvp_cache", {})
    parts = [x.strip() for x in str(event or "").split("@")]
    opp = parts[1] if len(parts) == 2 else ""
    key = (player, prop, opp)
    if key in cache:
        return cache[key]
    field = {"Points": "pts", "Rebounds": "reb", "Assists": "ast"}[prop]
    try:
        status, found = bdl_get("players", bdl_key, {"search": str(player).split()[-1], "per_page": 10})
        me = next((p for p in (found.get("data") or []) if _norm_name(f"{p.get('first_name','')} {p.get('last_name','')}") == _norm_name(player)), None)
        pos = (me or {}).get("position") or ""
        pos = pos.split("-")[0].strip()
        status, teams = bdl_get("teams", bdl_key, {"per_page": 50})
        token = opp.split()[-1].lower() if opp else ""
        team = next((t for t in (teams.get("data") or []) if token and token in str(t.get("full_name") or "").lower()), None)
        if not team or not pos:
            return None
        tid = team.get("id")
        abbr = team.get("abbreviation") or token.upper()
        status, games = bdl_get("games", bdl_key, {"team_ids[]": tid, "per_page": 6})
        ids = [g.get("id") for g in (games.get("data") or []) if g.get("home_team_score")][:4]
        if not ids:
            return None
        status, stats = bdl_get("stats", bdl_key, {"game_ids[]": ids, "per_page": 100})
        allowed = []
        for s in stats.get("data") or []:
            if ((s.get("team") or {}).get("id") == tid):
                continue
            s_pos = ((s.get("player") or {}).get("position") or "").split("-")[0].strip()
            if s_pos == pos:
                allowed.append(float(s.get(field) or 0))
        if not allowed:
            return None
        avg = sum(allowed) / max(1, len(ids))
        league = {"Points": 15, "Rebounds": 6, "Assists": 4}.get(prop, 10)
        pct = round((avg - league) / league * 100) if league else 0
        word = "Yes" if avg >= league else "No"
        line = f"{word}. {abbr} allows {avg:.1f} {prop.lower()} a game to {pos}, {abs(pct)}% {'more' if pct >= 0 else 'less'} than average."
        cache[key] = line
        return line
    except Exception:
        return None



NBA_ABBR = {"lakers":"lal","celtics":"bos","warriors":"gs","bucks":"mil","nets":"bkn","knicks":"ny","heat":"mia","bulls":"chi","mavs":"dal","mavericks":"dal","suns":"phx","nuggets":"den","clippers":"lac","76ers":"phi","sixers":"phi","raptors":"tor","hawks":"atl","hornets":"cha","cavaliers":"cle","cavs":"cle","pistons":"det","pacers":"ind","grizzlies":"mem","timberwolves":"min","wolves":"min","pelicans":"no","thunder":"okc","magic":"orl","trail blazers":"por","blazers":"por","kings":"sac","spurs":"sa","jazz":"utah","wizards":"wsh"}
BOOK_LOGO = {"FD":"https://www.fanduel.com/favicon.ico","DK":"https://www.draftkings.com/favicon.ico","MGM":"https://www.betmgm.com/favicon.ico","CZR":"https://www.caesars.com/favicon.ico","HR":"https://www.hardrock.bet/favicon.ico","365":"https://www.bet365.com/favicon.ico","FAN":"https://www.fanatics.com/favicon.ico","SCR":"https://www.thescore.bet/favicon.ico"}

def team_logo(event, sport):
    parts = [x.strip().lower() for x in str(event or "").split("@")]
    name = parts[-1] if parts else ""
    abbr = NBA_ABBR.get(name.split()[-1], "") if name else ""
    if not abbr:
        for k, v in NBA_ABBR.items():
            if k in name:
                abbr = v
                break
    if not abbr:
        return ""
    league = "nba" if sport == "NBA" else "nfl"
    return f"https://a.espncdn.com/i/teamlogos/{league}/500/{abbr}.png"


def player_photo(player, bdl_key):
    if not bdl_key:
        return ""
    cache = st.session_state.setdefault("photo_cache", {})
    if player in cache:
        return cache[player]
    try:
        status, found = bdl_get("players", bdl_key, {"search": str(player).split()[-1], "per_page": 5})
        me = next((p for p in (found.get("data") or []) if _norm_name(f"{p.get('first_name','')} {p.get('last_name','')}") == _norm_name(player)), None)
        if me and me.get("id"):
            url = f"https://a.espncdn.com/i/headshots/nba/players/full/{me['id']}.png"
            cache[player] = url
            return url
    except Exception:
        pass
    cache[player] = ""
    return ""

def glow_card(c, result=None):
    tev = c.get("true_ev")
    line_txt = "Yes" if c.get("prop") in ("DoubleDouble", "Anytime TD") else f"o{c.get('line')}"
    prices = c.get("book_prices") or {c.get("book"): c.get("price")}
    ranked = sorted(prices.items(), key=lambda z: -(z[1] or 0))[:6]
    next_best = ranked[1] if len(ranked) > 1 else None
    boxes = "".join(
        f'<div style="background:{("#ff4fd8" if bk == c.get("book") else {"FD":"#1493ff22","DK":"#53d33722","MGM":"#b8972e22","365":"#0a7a3222","CZR":"#1a3a6b22","FAN":"#e23b2f22","SCR":"#6b6b6b22","HR":"#c8102e22"}.get(bk, "#1a1024"))};border:2px solid {("#ffd0f2" if bk == c.get("book") else {"FD":"#1493ff","DK":"#53d337","MGM":"#b8972e","365":"#0a7a32","CZR":"#1a3a6b","FAN":"#e23b2f","SCR":"#6b6b6b","HR":"#c8102e"}.get(bk, "#3a2450"))};border-radius:12px;padding:8px;text-align:center">'
        f'<div style="font-size:.7rem;font-weight:800;color:{"#1a1020" if bk == c.get("book") else "#fff"}">{BOOK_FULL.get(bk, bk)}</div>'
        f'<div style="font-weight:800;font-size:1rem;color:{"#1a1020" if bk == c.get("book") else "#fff"}">{fmt_price(px)}</div>'
        + (f'<div style="font-size:.55rem;color:#1a1020;font-weight:700">BEST</div>' if bk == c.get("book") else "")
        + '</div>'
        for bk, px in ranked
    )
    state = (result or c.get("decision") or "").upper()
    cls = "card"
    if state == "HIT":
        cls += " hit"
    elif state == "MISS":
        cls += " miss"
    elif state in ("LOCKED", "WAITING", ""):
        cls += " wait"
    tev = c.get("true_ev")
    if (tev or 0) >= 25:
        cls += " take"
    gap = c.get("ev_gap")
    stat = c.get("player_stat")
    got = f" · got {stat}" if stat is not None else ""
    note = c.get("grade_note") or ""
    locked = c.get("ts") or "—"
    graded = c.get("graded_ts") or "—"
    fair = c.get("fair_prob")
    def prob_to_american(pct):
        try:
            p = float(pct) / 100
            if p <= 0 or p >= 1:
                return None
            return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)
        except Exception:
            return None
    fair_price = prob_to_american(fair)
    fair_txt = f"{fair_price:+d}" if fair_price else "—"
    vals = sorted([v for v in prices.values() if isinstance(v, (int, float))], reverse=True)
    vs_next = "—"
    if len(vals) >= 2 and vals[1]:
        try:
            vs_next = f"{round((vals[0] - vals[1]) / abs(vals[1]) * 100)}%"
        except Exception:
            vs_next = "—"
    market = c.get("median")
    market_txt = f"{int(market):+d}" if isinstance(market, (int, float)) else "—"
    desc = (
        f"Longest was {c.get('book') or '?'} {fmt_price(c.get('price'))}. "
        f"Fair value {fair_txt}. Market {market_txt}. "
        f"Gap {gap if gap is not None else '—'}%. Edge {tev if tev is not None else '—'}%."
    )
    book = c.get("book") or "A book"
    price = fmt_price(c.get("price"))
    more = ""
    if isinstance(market, (int, float)) and market and c.get("price"):
        try:
            more = f"Pays {round((c.get('price') - market) / abs(market) * 100)}% more than the pack."
        except Exception:
            more = ""
    tags = []
    if len(prices) <= 2:
        tags.append("Solo")
    if (gap or 0) >= 25:
        tags.append("Big Gap")
    if c.get("book") in ("HR", "SCR", "FAN"):
        tags.append("Soft Book")
    tag_txt = " · ".join(tags)
    stake = ""
    if isinstance(tev, (int, float)) and tev > 0:
        low = max(5, round(tev * 0.5))
        high = max(low + 5, round(tev * 1.5))
        stake = f"Stake ${low}–${high} on a $1k bankroll."
    sgo = c.get("sgo_fair")
    sgo_txt = f" SGO fair {int(sgo):+d}." if isinstance(sgo, (int, float)) else ""
    both = isinstance(sgo, (int, float)) and (c.get("price") or 0) > sgo and (tev or 0) > 0
    agree = " Both fairs agree." if both else ""
    if both:
        tags.append("High Confidence")
        tag_txt = " · ".join(tags)
    why = f"{book} is hanging {price}. The pack is {market_txt}."
    dvp_line = ""
    if c.get("dvp"):
        dvp_line = ""
    edge_color = "#ffd84a" if (tev or 0) >= 25 else "#ff4fd8"
    take_score = min(100, round((tev or 0) * 2 + (gap or 0)))
    gauge = f'<div style="width:64px;height:64px;border-radius:50%;background:conic-gradient(#FFD447 {take_score}%, #2a1a3a 0);display:flex;align-items:center;justify-content:center"><div style="width:48px;height:48px;border-radius:50%;background:#14141A;display:flex;align-items:center;justify-content:center;font-size:.7rem;font-weight:800;color:#FFD447">{take_score}</div></div>'
    return (
        f'<div class="{cls}">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
        f'<div style="display:flex;gap:10px;align-items:center"><img src="{player_photo(c.get("player"), secret("BALLDONTLIE_API_KEY"))}" style="width:48px;height:48px;border-radius:12px;object-fit:cover" onerror="this.remove()"><img src="{team_logo(c.get("event"), c.get("sport"))}" style="width:32px;height:32px;border-radius:50%;object-fit:contain" onerror="this.remove()">'
        f'<div><div class="player" style="font-size:1.6rem;text-shadow:0 0 12px #FF4EC8">{c.get("player")}</div>'
        f'<div class="prop" style="color:#FFD447;font-weight:700">{c.get("prop")} {line_txt}</div>'
        f'<div style="color:#b9a8d4;font-size:.75rem">{c.get("event") or ""}</div></div></div>'
        f'<div style="text-align:right;display:flex;gap:10px;align-items:center">'
        f'{gauge}'
        f'<div><div style="font-size:2.6rem;font-weight:800;color:#fff;text-shadow:0 0 16px {edge_color}">{price}</div>'
        f'<div style="display:inline-block;margin-top:2px;background:{edge_color};color:#1a1020;font-weight:800;font-size:.68rem;padding:2px 8px;border-radius:999px">{book} BEST</div></div></div></div>'
        f'<div class="why" style="font-size:.88rem;margin:12px 0 8px;line-height:1.4">{why}</div>'
        f'<div style="display:flex;gap:8px;margin:10px 0">'
        f'<div style="background:#1a1024;border:1px solid #3a2450;border-radius:12px;padding:8px 14px;text-align:center"><span style="display:block;font-size:.58rem;color:#cbb6e0">FAIR</span><b>{fair_txt}</b></div>'
        f'<div style="background:#1a1024;border:1px solid {edge_color};border-radius:12px;padding:8px 14px;text-align:center"><span style="display:block;font-size:.58rem;color:{edge_color}">EDGE</span><b style="color:{edge_color}">{tev if tev is not None else "—"}%</b></div>'
        f'<div style="background:#1a1024;border:1px solid #3a2450;border-radius:12px;padding:8px 14px;text-align:center"><span style="display:block;font-size:.58rem;color:#cbb6e0">GAP</span><b>{gap if gap is not None else "—"}%</b></div></div>'
        f'<div style="margin:8px 0"><div style="display:flex;justify-content:space-between;font-size:.65rem;color:#cbb6e0"><span>Fair {fair_txt}</span><span>Longest {price}</span></div><div style="height:8px;border-radius:999px;background:linear-gradient(90deg,#C07CFF,#FFD447);margin-top:3px"></div></div>'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:8px">{boxes}</div>'
        f'{("<div class=why>Next best " + fmt_price(next_best[1]) + " at " + BOOK_FULL.get(next_best[0], next_best[0]) + ".</div>") if next_best else ""}'
        f'{dvp_line}'
        f'</div>'
    )


def counters(locked, finished, hits, misses):
    st.markdown(
        f'''<div class="counters">
        <div class="counter locked">Locked<b>{locked}</b><span style="font-size:.65rem">tighten the chaos</span></div>
        <div class="counter done">Receipts<b>{finished}</b></div>
        <div class="counter hits">She hit that<b>{hits}</b></div>
        <div class="counter miss">Did not hit<b>{misses}</b></div>
        </div>''',
        unsafe_allow_html=True,
    )


def main():
    st.markdown("# ✨ Girl Magic Odds 2.0")
    st.caption("Be a better bettor. Crack the code. These books are cooked.")
    st.markdown('<div class="pulse-bar"></div>', unsafe_allow_html=True)
    st.markdown('<div class="how-to">Be a better bettor. Crack the code. The long number is the tell. These books are cooked.</div>', unsafe_allow_html=True)
    api_key = secret("ODDS_API_KEY") or st.text_input("Odds API Key", type="password")
    if not api_key:
        st.info("Add your Odds API key.")
        return
    bdl_key = secret("BALLDONTLIE_API_KEY")
    auto_weights = load_auto_weights()
    with st.sidebar:
        st.markdown("### Book weights")
        st.caption("Heavier book counts more in the blend.")
        live = {}
        for short in sorted(BASE_WEIGHTS):
            live[short] = st.slider(short, 0.5, 4.0, float(auto_weights.get(short, BASE_WEIGHTS[short])), 0.1, key=f"w_{short}")
        if st.button("Reset weights"):
            save_auto_weights(BASE_WEIGHTS.copy())
            st.rerun()
    sport = st.radio("Lane", ["NBA", "NFL"], horizontal=True)
    if st.button("Pull the chaos board", type="primary", use_container_width=True):
        sport_key = "basketball_nba" if sport == "NBA" else "americanfootball_nfl"
        markets = (
            "player_assists,player_assists_alternate,player_points,player_points_alternate,player_rebounds,player_rebounds_alternate,player_double_double"
            if sport == "NBA" else "player_anytime_td,player_reception_yds,player_reception_yds_alternate"
        )
        with st.spinner(f"Pulling {sport}…"):
            events = fetch_events(api_key, sport_key)
            now = datetime.now(timezone.utc)
            pregame = []
            for ev in events:
                try:
                    start = datetime.fromisoformat((ev.get("commence_time") or "").replace("Z", "+00:00"))
                    if start > now:
                        pregame.append(ev)
                except Exception:
                    continue
            plays = []
            for ev in (pregame or events)[:30]:
                data = fetch_odds(api_key, sport_key, ev.get("id"), markets)
                if data:
                    plays.extend(parse_plays(data, sport))
            pulled = datetime.now(timezone.utc).isoformat()
            cards = best_cards(plays, live)
            for c in cards:
                c["pulled_at"] = pulled
            sgo_key = secret("SGO_API_KEY")
            if sgo_key:
                for c in cards:
                    if worth_locking(c):
                        c["sgo_fair"] = sgo_fair(sgo_key, c.get("player"), c.get("prop"))
            update_auto_weights(update_sharpness(cards))
            st.session_state["dvp_cache"] = {}
            st.session_state[f"cards_{sport}"] = cards
            st.session_state["fetched"] = datetime.now().strftime("%H:%M")
            st.session_state["last_sport"] = sport
            ledger = load_ledger()
            seen = {(r.get("sport"), _norm_name(r.get("player")), r.get("prop"), round(float(r.get("line") or 0), 1), r.get("event")) for r in ledger}
            added = 0
            lane_count = sum(1 for r in ledger if r.get("sport") == sport)
            ranked = sorted([c for c in cards if worth_locking(c)], key=lambda z: -(z.get("true_ev") or 0))
            for c in ranked:
                key = (c["sport"], _norm_name(c["player"]), c["prop"], round(float(c["line"]), 1), c["event"])
                if key in seen:
                    continue
                ledger.append({
                    "ts": datetime.now().isoformat(timespec="minutes"), "sport": c["sport"],
                    "player": c["player"], "prop": c["prop"], "line": c["line"], "price": c["price"],
                    "book": c["book"], "event": c["event"], "true_ev": c.get("true_ev"),
                    "ev_gap": c.get("ev_gap"), "result": None,
                })
                seen.add(key)
                added += 1
                lane_count += 1
            save_ledger(ledger)
            st.toast(f"{sum(1 for c in cards if c.get('decision')=='TAKE')} TAKE · tracked {added}")
    cards = st.session_state.get(f"cards_{sport}") or []
    if st.session_state.get("last_sport") == sport and st.session_state.get("fetched"):
        qualified = sum(1 for c in cards if worth_locking(c))
        st.caption(f"{sport} @ {st.session_state['fetched']} · {len(cards)} priced · {qualified} worth locking")
        if cards:
            density = round(100 * qualified / len(cards))
            st.markdown(f'<div class="how-to">Board density {density}%. {qualified} of {len(cards)} clear the chaos filter. Gap 20+, edge 15+.</div>', unsafe_allow_html=True)
    board, tracker, glossary = st.tabs(["Board", "Tracker", "What this means"])
    with board:
        if not cards:
            st.info("Pull the board.")
        else:
            a, b, c3 = st.columns(3)
            simple = a.toggle("TAKE only", value=True)
            petty = b.toggle("Petty ranges", value=True)
            props = ["Assists", "Points", "Rebounds", "DoubleDouble"] if sport == "NBA" else ["Anytime TD", "Rec Yards"]
            prop_filter = st.multiselect("Prop", props, default=props, key=f"board_prop_{sport}")
            min_odds = st.slider("Min odds", -200, 2000, 100, 25)
            now_ts = datetime.now(timezone.utc)
            def fresh(x):
                try:
                    pulled = datetime.fromisoformat(x.get("pulled_at"))
                    return (now_ts - pulled).total_seconds() <= 90
                except Exception:
                    return True
            filtered = [x for x in cards if fresh(x) and x.get("sport") == sport and x.get("prop") in prop_filter and line_ok(x.get("prop"), x.get("line")) and (x.get("price") or 0) >= min_odds]
            if petty:
                filtered = [x for x in filtered if x.get("petty_range_match")]
            if simple:
                filtered = [x for x in filtered if worth_locking(x)]
            filtered = sorted(filtered, key=lambda x: -(x.get("true_ev") or -999))
            page = st.number_input("Board page", min_value=1, value=1, step=1)
            start = (int(page) - 1) * 24
            shown = filtered[start:start + 24]
            st.markdown(f"**{len(filtered)} match.** Showing {start + 1}–{start + len(shown)}. Best gaps first.")
            by_game = defaultdict(list)
            for x in shown:
                by_game[x.get("event") or "Unknown"].append(x)
            for game, rows in by_game.items():
                st.markdown(f'<div class="game-header">{game}</div>', unsafe_allow_html=True)
                cols = st.columns(2)
                for i, x in enumerate(rows):
                    with cols[i % 2]:
                        st.markdown(glow_card(x), unsafe_allow_html=True)
                        if st.button("LOCK THIS PLAY 💅", key=f"lk_{sport}_{page}_{game}_{i}_{x['player']}_{x['line']}"):
                            ledger = load_ledger()
                            ledger.append({
                                "ts": datetime.now().isoformat(timespec="minutes"), "sport": x["sport"],
                                "player": x["player"], "prop": x["prop"], "line": x["line"], "price": x["price"],
                                "book": x["book"], "event": x["event"], "true_ev": x.get("true_ev"),
                                "ev_gap": x.get("ev_gap"), "result": None,
                            })
                            save_ledger(ledger)
                            st.toast("Locked 💫")
    with tracker:
        ledger = load_ledger()
        st.markdown('<div class="how-to">Once a play is tracked, it stays. Only Wipe tracker removes plays. Filters hide rows. They do not delete them.</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("Wipe tracker"):
            save_ledger([])
            st.rerun()
        st.download_button("Download the ledger", json.dumps(load_ledger(), indent=2), "girlmagic_ledger.json", "application/json")
        upload = st.file_uploader("Upload lost receipts", type=["json", "csv"])
        do_restore = st.button("Restore this file")
        if upload is not None and do_restore:
            raw = upload.getvalue().decode("utf-8", errors="ignore")
            incoming = []
            if upload.name.endswith(".json"):
                try:
                    incoming = json.loads(raw)
                except Exception:
                    incoming = []
            else:
                import csv, io
                incoming = list(csv.DictReader(io.StringIO(raw)))
            if isinstance(incoming, dict):
                incoming = incoming.get("plays") or incoming.get("ledger") or []
            merged = load_ledger()
            have = {(str(r.get("player")), str(r.get("prop")), str(r.get("line"))) for r in merged}
            added_up = 0
            for r in incoming:
                low = {str(k).strip().lower(): v for k, v in r.items()}
                player = low.get("player") or low.get("name")
                if not player:
                    continue
                res = str(low.get("result") or low.get("grade") or "").strip().upper()
                if res in ("HIT", "H", "WIN", "W"):
                    res = "HIT"
                elif res in ("MISS", "M", "LOSS", "L"):
                    res = "MISS"
                else:
                    res = None
                row = {
                    "player": player, "prop": low.get("prop") or low.get("market") or low.get("stat"),
                    "line": low.get("line") or low.get("point"), "price": low.get("price") or low.get("odds"),
                    "book": MY_BOOKS.get(normalize_book(low.get("book") or low.get("sportsbook")), low.get("book") or low.get("sportsbook")), "event": low.get("event") or low.get("matchup") or low.get("game"),
                    "sport": ("NFL" if "nfl" in str(low.get("sport") or low.get("league") or "").lower() or "football" in str(low.get("sport") or "").lower() else "NBA" if "nba" in str(low.get("sport") or low.get("league") or "").lower() or "basketball" in str(low.get("sport") or "").lower() else sport), "result": res,
                    "true_ev": low.get("true_ev"), "ev_gap": low.get("ev_gap") or low.get("gap"),
                    "player_stat": low.get("player_stat") or low.get("actual"),
                }
                key = (str(row["player"]), str(row["prop"]), str(row["line"]))
                if key in have:
                    if row.get("result"):
                        for old in merged:
                            if (str(old.get("player")), str(old.get("prop")), str(old.get("line"))) == key:
                                old["result"] = row["result"]
                                if row.get("player_stat"):
                                    old["player_stat"] = row["player_stat"]
                                added_up += 1
                                break
                    continue
                merged.append(row)
                have.add(key)
                added_up += 1
            save_ledger(merged)
            cols = sorted({k for r in incoming[:1] for k in r}) if incoming else []
            graded_in = sum(1 for r in incoming if str(r.get("result") or r.get("grade") or "").strip())
            names = sorted({str(r.get("player")) for r in merged if r.get("player")})
            st.success(f"File {len(incoming)} rows. Added {added_up}. Ledger {len(merged)} players {len(names)}.")
            st.write(", ".join(names[:40]))
        regrade = st.checkbox("Regrade, clear old hits first")
        if c2.button("Grade finals"):
            with st.spinner("Closing plays…"):
                ledger, msg = grade_nba(ledger, bdl_key, regrade=regrade) if sport == "NBA" else grade_nfl(ledger, regrade=regrade)
            st.success(msg)
            st.toast("Grading complete — chaos contained 💫")
            st.balloons()
            st.rerun()
        save_ledger(ledger)
        st.caption(f"{sport} only. {sum(1 for r in ledger if r.get('sport') == sport)} in this lane.")
        mine = [r for r in ledger if str(r.get("sport") or "").upper() == sport]
        hits = [r for r in mine if r.get("result") == "HIT"]
        misses = [r for r in mine if r.get("result") == "MISS"]
        locked = [r for r in mine if r.get("result") not in ("HIT", "MISS")]
        counters(len(mine), len(hits) + len(misses), len(hits), len(misses))
        f1, f2, f3 = st.columns(3)
        prop_opts = sorted({r.get("prop") for r in mine if r.get("prop")})
        book_opts = sorted({r.get("book") for r in mine if r.get("book")})
        prop_f = f1.multiselect("Prop", prop_opts)
        book_f = f2.multiselect("Book", book_opts)
        gap_f = f3.selectbox("Gap", ["All", "0–20", "21–40", "41+"])
        def gap_ok(r):
            g = r.get("ev_gap") or 0
            if gap_f == "0–20":
                return g < 21
            if gap_f == "21–40":
                return 21 <= g <= 40
            if gap_f == "41+":
                return g >= 41
            return True
        find = st.text_input("Find a player", placeholder="Kuzma, Ekholm, Gillespie")
        book_ok = set(book_f) | {BOOK_FULL.get(b, b) for b in book_f}
        view = [r for r in mine if (not prop_f or r.get("prop") in prop_f) and (not book_f or r.get("book") in book_ok) and gap_ok(r)]
        if find:
            q = find.lower()
            view = [r for r in mine if q in str(r.get("player") or "").lower()]
        tab_all, tab_hits, tab_misses, tab_locked, tab_charts = st.tabs(["All Plays", "She Hit That", "Did Not Hit", "Still Cooking", "Read the Charts"])

        def show(rows, key):
            if not rows:
                st.caption("Nothing in this cut.")
                return
            grouped = {}
            for r in rows:
                gkey = (r.get("player"), r.get("sport"), r.get("event") or "")
                grouped.setdefault(gkey, []).append(r)
            cards = []
            for gkey, props in grouped.items():
                seen = set()
                clean = []
                for r in props:
                    sig = (r.get("prop"), r.get("line"), r.get("book"))
                    if sig in seen:
                        continue
                    seen.add(sig)
                    clean.append(r)
                clean.sort(key=lambda z: -(z.get("ev_gap") or 0))
                avg = sum((z.get("true_ev") or 0) for z in clean) / max(1, len(clean))
                cards.append((avg, gkey, clean))
            cards.sort(key=lambda z: -z[0])
            page = st.number_input("Page", min_value=1, value=1, step=1, key=key)
            start = (int(page) - 1) * 8
            pair = st.columns(2)
            for n, (avg, (player, sport_name, event), props) in enumerate(cards[start:start + 8]):
                rows_html = []
                for r in props:
                    res = r.get("result") or "LOCKED"
                    color = "gold" if res == "HIT" else "#ff4d4d" if res == "MISS" else "#ff00cc"
                    got = f" · got {r.get('player_stat')}" if r.get("player_stat") is not None else ""
                    note = r.get("grade_note") or ""
                    rows_html.append(
                        f'<div style="margin-top:8px;padding:10px;border-radius:10px;background:{color}22;border:1px solid {color};box-shadow:0 0 10px {color}44">'
                        f'<b>{r.get("prop")} {r.get("line")}{got}</b> — {res}'
                        f'<div style="color:#ddd;font-size:.75rem;margin-top:4px">'
                        f'Locked {r.get("price")} at {r.get("book")}. Gap {r.get("ev_gap") or "—"}%. Edge {r.get("true_ev") or "—"}%.'
                        f'</div><div style="color:#ffe27a;font-size:.72rem">{note or "Waiting on the box score."}</div></div>'
                    )
                with pair[n % 2]:
                    st.markdown(
                    f'<div style="margin-bottom:12px;padding:12px;border-radius:16px;background:#16101f;border:1px solid #ff00cc;box-shadow:0 0 14px #ff00cc44">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<b style="color:#ff00cc;font-size:18px">{player}</b>'
                    f'<span style="color:#aaa;font-size:13px">{sport_name} · {event}</span></div>'
                    + "".join(rows_html) + "</div>",
                    unsafe_allow_html=True,
                )
            st.caption(f"{len(cards)} players · {len(rows)} props · page {int(page)}")

        with tab_all:
            show(view, "pg_all")
        with tab_hits:
            show([r for r in view if r.get("result") == "HIT"], "pg_hit")
        with tab_misses:
            show([r for r in view if r.get("result") == "MISS"], "pg_miss")
        with tab_locked:
            show([r for r in view if r.get("result") not in ("HIT", "MISS")], "pg_lock")
        with tab_charts:
            graded = [r for r in view if r.get("result") in ("HIT", "MISS")]
            if not graded:
                st.info("Grade a slate and the charts fill in.")
            else:
                chart_df = pd.DataFrame([{"book": BOOK_FULL.get(r.get("book"), r.get("book") or "?"), "result": r.get("result")} for r in graded])
                hit_chart = alt.Chart(chart_df).mark_bar(size=26, cornerRadiusEnd=6).encode(
                    x=alt.X("book:N", title="Sportsbook", sort="-y"),
                    y=alt.Y("count():Q", title="Plays"),
                    color=alt.Color("result:N", scale=alt.Scale(domain=["HIT", "MISS"], range=["gold", "#555"])),
                    tooltip=["book", "result", "count()"],
                ).properties(height=260, title="Who cashed — gold is a hit, gray is a miss")
                st.altair_chart(hit_chart, use_container_width=True)
                gap_df = pd.DataFrame([{"gap": r.get("ev_gap") or 0, "edge": r.get("true_ev") or 0, "result": r.get("result")} for r in graded])
                scatter = alt.Chart(gap_df).mark_circle(size=70).encode(
                    x=alt.X("gap:Q", title="Gap %"),
                    y=alt.Y("edge:Q", title="Edge %"),
                    color=alt.Color("result:N", scale=alt.Scale(domain=["HIT", "MISS"], range=["gold", "#ff00cc"])),
                    tooltip=["gap", "edge", "result"],
                ).properties(height=260, title="Gap across, edge up. Top right is the loud one that also had juice")
                st.altair_chart(scatter, use_container_width=True)
                pie_df = pd.DataFrame([{"result": "HIT", "count": sum(r.get("result")=="HIT" for r in graded)}, {"result": "MISS", "count": sum(r.get("result")=="MISS" for r in graded)}])
                pie = alt.Chart(pie_df).mark_arc(innerRadius=55).encode(
                    theta="count:Q",
                    color=alt.Color("result:N", scale=alt.Scale(domain=["HIT", "MISS"], range=["gold", "#555"])),
                    tooltip=["result", "count"],
                ).properties(height=260, title="The whole slate. Gold slice is she hit that")
                st.altair_chart(pie, use_container_width=True)
                prop_df = pd.DataFrame([{"prop": r.get("prop"), "result": r.get("result")} for r in graded])
                heat = alt.Chart(prop_df).mark_rect().encode(
                    x=alt.X("prop:N", title="Prop"),
                    y=alt.Y("result:N", title=""),
                    color=alt.Color("count():Q", scale=alt.Scale(scheme="plasma")),
                    tooltip=["prop", "result", "count()"],
                ).properties(height=140, title="Which props cash")
                st.altair_chart(heat, use_container_width=True)
        st.markdown("**What cashed**")
        all_books = ["DraftKings", "FanDuel", "BetMGM", "Caesars", "Bet365", "Fanatics", "Hard Rock", "theScore"]
        short_to_full = {"DK": "DraftKings", "FD": "FanDuel", "MGM": "BetMGM", "CZR": "Caesars", "365": "Bet365", "FAN": "Fanatics", "HR": "Hard Rock", "SCR": "theScore"}
        book_stats = {b: {"hits": 0, "total": 0} for b in all_books}
        for r in [x for x in view if x.get("result") in ("HIT", "MISS")]:
            name = short_to_full.get(r.get("book"), r.get("book"))
            if name in book_stats:
                book_stats[name]["total"] += 1
                book_stats[name]["hits"] += r.get("result") == "HIT"
        tiles = []
        for book, stats in book_stats.items():
            h, total = stats["hits"], stats["total"]
            pct = round(h / total * 100, 1) if total else 0
            color = "gold" if pct >= 10 else "#ff00cc" if pct >= 5 else "#6600ff" if pct > 0 else "#333"
            tiles.append(
                f'<div style="width:148px;height:108px;background:#12121a;border-radius:14px;border:2px solid {color};'
                f'box-shadow:0 0 12px {color}55;display:flex;flex-direction:column;align-items:center;justify-content:center;margin:6px">'
                f'<div style="font-size:22px;color:{color};font-weight:700">{pct}%</div>'
                f'<div style="color:#fff;font-size:13px">{book}</div>'
                f'<div style="color:#aaa;font-size:12px">{h} of {total}</div></div>'
            )
        st.markdown('<div style="display:flex;flex-wrap:wrap">' + "".join(tiles) + "</div>", unsafe_allow_html=True)
        st.markdown('<div class="pulse-bar"></div>', unsafe_allow_html=True)
    with glossary:
        with st.expander("✨ Glossary", expanded=True):
            st.markdown(f'<div class="glossary">{GLOSSARY}</div>', unsafe_allow_html=True)


try:
    main()
except Exception as e:
    st.error(f"App error: {e}")
    st.exception(e)
