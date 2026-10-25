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
.card{margin-bottom:10px;padding:12px;border-radius:18px;background:linear-gradient(180deg,#241433,#16101f);border:1px solid #ff4fd8;box-shadow:0 0 18px #ff00cc66;min-height:160px}
.card:hover{transform:scale(1.015);box-shadow:0 0 22px #ff00cc88}
.card.hit{border-color:gold;box-shadow:0 0 18px gold}
.card.miss{border-color:#553333;opacity:.8;box-shadow:none}
.card.wait{border-color:#6600ff;box-shadow:0 0 14px #6600ff66;animation:pulse 2.4s infinite}
.player{font-weight:700;font-size:1.02rem}
.prop{color:#ffb3ea;font-size:.72rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;margin:2px 0 6px}
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

.gm{background:#16121c;border:1px solid #8b6bb5;border-radius:14px;padding:12px 14px;margin-bottom:8px;color:#f4eef8}
.gm-top{display:flex;justify-content:space-between;align-items:center}
.gm-name{font-size:1.05rem;font-weight:800;color:#fff}.gm-row{display:flex;justify-content:space-between;font-size:.9rem;margin:3px 0}.gm-row span{color:#cbb6e0}.gm-books{font-size:.72rem;color:#e7d6f5;margin-top:6px}
.pscore{background:#ec4899;color:#fff;font-weight:800;font-size:.68rem;padding:4px 10px;border-radius:999px}
.run{font-size:.62rem;letter-spacing:.14em;color:#f9a8d4;font-weight:700}
.gm-sub{color:#c4b5d4;font-size:.72rem;margin:2px 0 6px}
.meters{display:flex;gap:4px;margin:4px 0 8px}
.meter{width:18px;height:6px;border-radius:3px;background:#374151}
.meter.on{background:linear-gradient(90deg,#f472b6,#c026d3)}
.gm-line{font-size:.84rem;margin:2px 0}
.mtags{display:flex;flex-wrap:wrap;gap:4px;margin:8px 0}
.mtag{background:#1b1226;border:1px solid #a855f7;border-radius:999px;padding:3px 8px;font-size:.62rem;font-weight:700;color:#e9d5ff}
.gm-why{font-size:.75rem;color:#fce7f3;margin-top:6px}
.gm-foot{font-size:.68rem;color:#d8c8ea;margin-top:6px}

.gm{background:#10241c;border:1px solid #ec4899;border-radius:18px;padding:14px;margin-bottom:10px;color:#fdf2f8}
.gm-top{display:flex;justify-content:space-between;align-items:center}
.run{font-size:.62rem;letter-spacing:.14em;color:#f9a8d4;font-weight:700}
.pscore{background:#ec4899;color:#fff;font-weight:800;font-size:.68rem;padding:4px 10px;border-radius:999px}
.gm-name{font-size:1.15rem;font-weight:800;color:#fff;margin-top:4px}
.gm-sub{color:#c4b5d4;font-size:.72rem;margin:2px 0 6px}
.meters{display:flex;gap:4px;margin:4px 0 8px}
.meter{width:18px;height:6px;border-radius:3px;background:#374151}
.meter.on{background:linear-gradient(90deg,#f472b6,#c026d3)}
.gm-line{font-size:.86rem;margin:2px 0}
.mtags{display:flex;flex-wrap:wrap;gap:4px;margin:8px 0}
.mtag{background:#1b1226;border:1px solid #a855f7;border-radius:999px;padding:3px 8px;font-size:.62rem;font-weight:700;color:#e9d5ff}
.gm-why{font-size:.75rem;color:#fce7f3;margin-top:6px}
.gm-foot{font-size:.66rem;color:#d8c8ea;margin-top:4px}

.hero{background:linear-gradient(90deg,#ff3ebf,#c77dff,#7b2cbf);border-radius:18px;padding:16px 20px;margin-bottom:10px;box-shadow:0 0 28px #ff3ebf55}
.hero-kicker{font-size:.68rem;letter-spacing:.2em;color:#ffe4f5;font-weight:700}
.hero-title{font-size:1.8rem;font-weight:800;color:#fff;text-shadow:0 0 12px #fff6}
.hero-sub{color:#ffeaf6;font-size:.95rem;margin-top:2px}

.gm{background:#16121e;border:1px solid #c77dff;border-radius:16px;padding:14px;margin-bottom:10px;color:#f7eefc}
.gm-kicker{font-size:.62rem;letter-spacing:.16em;color:#e9b3ff;font-weight:700}
.gm-name{font-size:1.1rem;font-weight:800;color:#fff;margin-top:4px}
.gm-sub{color:#cbb6e0;font-size:.74rem;margin-bottom:8px}
.gm-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:8px 0}
.gm-grid div{background:#21182c;border-radius:10px;padding:6px;text-align:center}
.gm-grid span{display:block;font-size:.6rem;color:#cbb6e0;letter-spacing:.06em}
.gm-grid b{display:block;font-size:1rem;color:#fff}
.gm-grid small{display:block;font-size:.6rem;color:#b9a4d4}
.mtags{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0}
.mtag{background:#21182c;border:1px solid #8b6bb5;border-radius:999px;padding:3px 8px;font-size:.62rem;color:#e7d6f5}
.gm-why{font-size:.75rem;color:#f4e6ff;margin-top:6px}
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
<strong>Be a better bettor.</strong> Hunt the true value. Catch the books sleeping at the wheel.<br><br><br><br>
<strong>True EV</strong> — the real edge. Blend the books, then compare to the longest number.<br>
<strong>Gap</strong> — how far the long number stands from the pack.<br>
<strong>Spike</strong> — one book screaming a number way off the pack. That is a TAKE.<br>
<strong>Soft book</strong> — the one that keeps hanging the longest number and paying you for it.<br>
<strong>Petty range</strong> — assists 3–8, points 8–15, rebounds 4–10, TD yes. Cute little alt lines.<br>
<strong>Receipts</strong> — after the game, NBA comes from BallDontLie, NFL from ESPN. HIT she did it. MISS she did not. N/A the data was trash.<br>
<strong>How to use this if you are new</strong><br>
1. Pull the heat board.<br>
2. Gap over 20% means one book is hanging a number way longer than the pack. That is the tell.<br>
3. Edge over 15% is the juice. +EV means that number is profitable over time if the math holds.<br>
4. After the games, run the receipts. HIT she did it. MISS she did not.<br>
5. Gold books are the soft ones. Play those more.<br><br>
<strong>Price gap</strong> — how far one book's number stands from the middle of the pack.<br>
<strong>+EV</strong> — expected value over zero. You are getting a longer number than the blend says is fair.<br>
<strong>CLV</strong> — your locked price against the close. Plus means you beat the market.
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


def weighted_fair_prob(book_prices, weights=None):
    weights = weights or load_auto_weights()
    weighted, total_w = [], 0.0
    for bk, price in (book_prices or {}).items():
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
    px = c.get("price")
    med = c.get("median")
    gap = c.get("ev_gap")
    tev = c.get("true_ev")
    px_txt = f"{int(px):+d}" if isinstance(px, (int, float)) else "—"
    med_txt = f"{int(med):+d}" if isinstance(med, (int, float)) else "the pack"
    return f"{bk} is paying {px_txt} where the pack is {med_txt} — gap {gap if gap is not None else '—'}%, edge {tev if tev is not None else '—'}%. Soft book energy."


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


@st.cache_data(ttl=90)
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
    gap = c.get("ev_gap") or 0
    edge = c.get("true_ev") or 0
    if c.get("decision") != "TAKE":
        return False
    if gap < 20 or edge < 15:
        return False
    if c.get("book_beh") == "Solo" and gap < 25:
        return False
    if not line_ok(c.get("prop"), c.get("line")):
        return False
    if (c.get("price") or 0) < 1000:
        return False
    return True


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


def glow_card(c, result=None):
    try:
        line_txt = "Yes" if c.get("prop") in ("DoubleDouble", "Anytime TD") else f"o{c.get('line')}"
        px, med = c.get("price"), c.get("median")
        px_txt = fmt_price(px)
        med_txt = fmt_price(med)
        gap = c.get("ev_gap") if isinstance(c.get("ev_gap"), (int, float)) else 0
        edge = c.get("true_ev") if isinstance(c.get("true_ev"), (int, float)) else 0
        prices = c.get("book_prices") or {c.get("book"): c.get("price")}
        books = "".join(f'<span class="mtag">{bk} {fmt_price(v)}</span>' for bk, v in list(prices.items())[:5])
        state = (result or c.get("decision") or "TAKE")
        state = str(state).upper()
        border = "#e8b923" if state == "HIT" else "#c45c7a" if state == "MISS" else "#c77dff"
        return (
            f'<div class="gm" style="border-color:{border}">'
            f'<div class="gm-kicker">TRUE VALUE · {state}</div>'
            f'<div class="gm-name">{c.get("player") or ""}</div>'
            f'<div class="gm-sub">{c.get("prop") or ""} {line_txt} · {c.get("event") or ""}</div>'
            f'<div class="gm-grid">'
            f'<div><span>Best</span><b>{px_txt}</b><small>{c.get("book") or ""}</small></div>'
            f'<div><span>Fair pack</span><b>{med_txt}</b><small>the blend</small></div>'
            f'<div><span>Gap</span><b>{gap}%</b><small>discrepancy</small></div>'
            f'<div><span>Edge</span><b>{edge}%</b><small>true EV</small></div>'
            f'</div>'
            f'<div class="mtags">{books}</div>'
            f'<div class="gm-why">{c.get("book") or "A book"} is hanging {px_txt}. The pack says {med_txt}. That gap is the tell.</div>'
            f'</div>'
        )
    except Exception:
        return f'<div class="gm">{c.get("player") or "Play"}</div>'


def chip(label, hits, n):
    rate = round(100 * hits / n) if n else 0
    hot = " hot" if n >= 8 and hits / n >= 0.15 else ""
    return f'<div class="rate-chip{hot}"><b>{rate}%</b><span>{label}<br>{hits} of {n}</span></div>'


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
    st.markdown("""
    <div class="hero">
      <div class="hero-kicker">CHAOS ENGINE</div>
      <div class="hero-title">Girl Magic Odds 2.0</div>
      <div class="hero-sub">Be a better bettor. Catch the books slippin.</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="pulse-bar"></div>', unsafe_allow_html=True)
    st.markdown('<div class="how-to">Pull the chaos board. The long number is the tell. Lock her. Run the receipts.</div>', unsafe_allow_html=True)
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
            cards = best_cards(plays, live)
            update_auto_weights(update_sharpness(cards))
            st.session_state[f"cards_{sport}"] = cards
            st.session_state["fetched"] = datetime.now().strftime("%H:%M")
            st.session_state["pull_note"] = f"{len(events)} events · {len(plays)} prices · {len(cards)} cards"
            st.session_state["last_sport"] = sport
            ledger = load_ledger()
            seen = {(r.get("sport"), _norm_name(r.get("player")), r.get("prop"), round(float(r.get("line") or 0), 1), r.get("event")) for r in ledger}
            added = 0
            per_player = defaultdict(int)
            lane_count = sum(1 for r in ledger if r.get("sport") == sport)
            ranked = sorted([c for c in cards if worth_locking(c)], key=lambda z: -(z.get("true_ev") or 0))
            for c in ranked:
                if lane_count >= 300:
                    break
                pkey = (_norm_name(c["player"]), c["event"])
                if per_player[pkey] >= 2:
                    continue
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
                per_player[pkey] += 1
                lane_count += 1
            save_ledger(ledger)
            st.toast(f"{sum(1 for c in cards if c.get('decision')=='TAKE')} TAKE · tracked {added}")
    cards = st.session_state.get(f"cards_{sport}") or []
    if st.session_state.get("last_sport") == sport and st.session_state.get("fetched"):
        qualified = sum(1 for c in cards if worth_locking(c))
        st.caption(f"{sport} @ {st.session_state['fetched']} · {len(cards)} priced · {qualified} worth locking · {st.session_state.get('pull_note','')}")
        if st.session_state.get("pull_debug"):
            st.warning(st.session_state["pull_debug"])
        if cards:
            density = round(100 * qualified / len(cards))
            st.markdown(f'<div class="how-to">Board density {density}%. {qualified} of {len(cards)} clear the chaos filter. Gap 20+, edge 15+.</div>', unsafe_allow_html=True)
    board, tracker, glossary = st.tabs(["Board", "Tracker", "What this means"])
    with board:
        if not cards:
            st.info("Pull the board.")
        else:
            a, b = st.columns(2)
            simple = a.toggle("TAKE only", value=True)
            petty = b.toggle("Petty ranges", value=False)
            props = ["Assists", "Points", "Rebounds", "DoubleDouble"] if sport == "NBA" else ["Anytime TD", "Rec Yards"]
            prop_filter = st.multiselect("Prop", props, default=props)
            min_odds = st.slider("Min odds", -200, 5000, 1000, 50)
            filtered = [x for x in cards if x.get("prop") in prop_filter and line_ok(x.get("prop"), x.get("line")) and (x.get("price") or 0) >= min_odds]
            if petty:
                filtered = [x for x in filtered if x.get("petty_range_match")]
            if simple:
                filtered = [x for x in filtered if worth_locking(x)]
            filtered = sorted(filtered, key=lambda x: -(x.get("true_ev") or -999))
            shown = filtered[:40]
            st.markdown(f"**{len(filtered)} match.** Top {len(shown)} by edge. No pages.")
            by_game = defaultdict(list)
            for x in shown:
                by_game[x.get("event") or "Unknown"].append(x)
            for game, rows in by_game.items():
                st.markdown(f'<div class="game-header">{game}</div>', unsafe_allow_html=True)
                cols = st.columns(2)
                for i, x in enumerate(rows):
                    with cols[i % 2]:
                        st.markdown(glow_card(x), unsafe_allow_html=True)
                        if st.button("Lock", key=f"lk_{sport}_{game}_{i}_{x['player']}_{x['line']}"):
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
        c1, c2 = st.columns(2)
        if c1.button("Clear the slate"):
            save_ledger([])
            st.rerun()
        regrade = st.checkbox("Regrade, clear old hits first")
        if c2.button("Run the receipts"):
            with st.spinner("Closing plays…"):
                ledger, msg = grade_nba(ledger, bdl_key, regrade=regrade) if sport == "NBA" else grade_nfl(ledger, regrade=regrade)
            st.success(msg)
            st.toast("Grading complete — chaos contained 💫")
            st.balloons()
            st.rerun()
        # fill CLV from the live board when the same play is still up
        live = {(x.get("player"), x.get("prop"), x.get("line")): x for x in cards}
        for r in ledger:
            match = live.get((r.get("player"), r.get("prop"), r.get("line")))
            if match and r.get("price") and match.get("median"):
                try:
                    r["clv"] = round((float(r["price"]) - float(match["median"])) / abs(float(match["median"])) * 100, 1)
                except Exception:
                    pass
        save_ledger(ledger)
        mine = [r for r in ledger if r.get("sport") == sport and line_ok(r.get("prop"), r.get("line"))]
        hits = [r for r in mine if r.get("result") == "HIT"]
        misses = [r for r in mine if r.get("result") == "MISS"]
        locked = [r for r in mine if r.get("result") not in ("HIT", "MISS")]
        counters(len(mine), len(hits) + len(misses), len(hits), len(misses))
        f1, f2, f3 = st.columns(3)
        prop_opts = sorted({r.get("prop") for r in mine if r.get("prop")})
        book_opts = sorted({r.get("book") for r in mine if r.get("book")})
        prop_f = f1.multiselect("Prop", prop_opts, default=prop_opts)
        book_f = f2.multiselect("Book", book_opts, default=book_opts)
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
        view = [r for r in mine if r.get("prop") in prop_f and r.get("book") in book_f and gap_ok(r)]
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
                avg = sum((float(z.get("true_ev")) if str(z.get("true_ev") or "").replace(".", "", 1).replace("-", "", 1).isdigit() else 0) for z in clean) / max(1, len(clean))
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
                    clv = r.get("clv")
                    clv_txt = f"{clv:+.1f}" if isinstance(clv, (int, float)) else "—"
                    got = f" · got {r.get('player_stat')}" if r.get("player_stat") is not None else ""
                    note = r.get("grade_note") or ""
                    rows_html.append(
                        f'<div style="margin-top:8px;padding:10px;border-radius:10px;background:{color}22;border:1px solid {color};box-shadow:0 0 10px {color}44">'
                        f'<b>{r.get("prop")} {r.get("line")}{got}</b> — {res}'
                        f'<div style="color:#ddd;font-size:.75rem;margin-top:4px">'
                        f'Locked {r.get("price")} at {r.get("book")}. Gap {r.get("ev_gap") or "—"}%. Edge {r.get("true_ev") or "—"}%. CLV {clv_txt}.'
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
            st.info('Charts are off while we get the app back.')
    with glossary:
        with st.expander("✨ Glossary", expanded=True):
            st.markdown(f'<div class="glossary">{GLOSSARY}</div>', unsafe_allow_html=True)


try:
    main()
except Exception as e:
    st.error(f"App error: {e}")
    st.exception(e)
