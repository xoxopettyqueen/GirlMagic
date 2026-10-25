# -*- coding: utf-8 -*-
"""
Girl Magic Odds 2.0
Price-gap model. Weighted books. BallDontLie GOAT grader.
Paste this whole file over app.py.
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700;900&family=Space+Grotesk:wght@500;700&display=swap');
.stApp{background:#0c0a1a;color:#fce7f3;font-family:'Inter',sans-serif}
h1{font-family:'Playfair Display',serif!important;font-weight:900!important;color:#f8f4ff!important;font-size:2.2rem!important;margin:0!important}
.queen-banner{display:inline-block;background:linear-gradient(90deg,#db2777,#9333ea);color:#fff;font-size:.72rem;font-weight:700;padding:5px 14px;border-radius:16px;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px}
.how-to{background:#16101f;border:1px solid #2a2038;border-radius:999px;padding:8px 16px;margin:8px 0 14px;font-size:.78rem;color:#d8c8ea}
.stButton>button{background:linear-gradient(90deg,#db2777,#9333ea)!important;color:#fff!important;border:none!important;border-radius:10px!important;font-weight:700!important;font-family:'Space Grotesk',sans-serif!important;letter-spacing:.04em}
.game-header{font-size:.95rem;font-weight:700;color:#f9a8d4;margin:16px 0 6px;border-bottom:1px solid #2a2038;padding-bottom:4px}
.row{display:flex;gap:12px;align-items:center;background:#16101f;border:1px solid #2a2038;border-radius:14px;padding:10px 12px;margin-bottom:6px}
.row.take{border-color:#db2777;box-shadow:0 0 0 1px rgba(219,39,119,.35)}
.row.hit{border-color:#34d399}
.row.miss{opacity:.72}
.who{min-width:190px;flex:0 0 190px}
.player{font-weight:700;color:#fff;font-size:.95rem}
.prop{color:#f9a8d4;font-size:.7rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase}
.books{display:flex;flex-wrap:wrap;gap:4px;flex:1}
.bk{background:#1b1226;border:1px solid #3b0764;border-radius:999px;padding:3px 7px;font-size:.64rem;font-weight:700;color:#e9d5ff}
.bk.best{background:#db2777;border-color:#f9a8d4;color:#fff}
.nums{min-width:150px;text-align:right}
.score-pill{display:inline-block;background:#ec4899;color:#fff;font-weight:800;font-size:.68rem;padding:3px 8px;border-radius:999px}
.ev{display:block;color:#ffe27a;font-weight:700;font-size:.85rem;margin-top:3px}
.gap{display:block;color:#d8c8ea;font-size:.68rem}
.why{color:#e9d5ff;font-size:.72rem;margin-top:2px}
.tag{display:inline-block;background:#1b1226;color:#e9d5ff;font-size:.6rem;font-weight:700;padding:2px 7px;border-radius:999px;margin:2px 3px 0 0;border:1px solid #3b0764}
.rate-chip{display:inline-block;background:#1a0f28;border:1px solid #a855f7;border-radius:12px;padding:8px 12px;margin:4px;text-align:center;min-width:78px}
.rate-chip.hot{border-color:#34d399;background:#0c2418}
.rate-chip b{display:block;font-size:1.05rem;color:#fce7f3}
.rate-chip span{font-size:.62rem;color:#d8c8ea}
.statpill{background:#16101f;border:1px solid #2a2038;border-radius:14px;padding:10px;text-align:center}
.statpill b{display:block;font-size:1.35rem;color:#f9a8d4}
.glossary{background:#16101f;border:1px solid #2a2038;border-radius:16px;padding:16px;font-size:.9rem;line-height:1.65;color:#f3e8ff}
.glossary strong{color:#f9a8d4}
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
BOOK_FULL = {
    "FD": "FanDuel", "DK": "DraftKings", "MGM": "BetMGM", "365": "Bet365",
    "CZR": "Caesars", "FAN": "Fanatics", "SCR": "theScore", "HR": "Hard Rock",
    "PIN": "Pinnacle", "CIR": "Circa", "BM": "Bookmaker",
}
ALL_BOOK_CODES = sorted(BOOK_FULL)
BASE_WEIGHTS = {
    "PIN": 3.5, "CIR": 3.0, "BM": 2.8, "FD": 2.0, "DK": 1.8, "365": 2.0,
    "MGM": 1.4, "CZR": 1.3, "FAN": 1.2, "SCR": 1.1, "HR": 1.1,
}
GLOSSARY = """
<strong>This is a price-gap tool.</strong> The longest number against the pack is the tell. Weights decide how much each book counts in the blend.<br><br>
<strong>True EV</strong> — longest price vs the weighted blend. Positive means that book is hanging a softer number than the group.<br>
<strong>Gap</strong> — how much longer the best price is than the median. Big gap, one book out on its own, is the chaos.<br>
<strong>Spike</strong> — gap plus how far apart the books are. TAKE is a high spike. LEAN is a smaller one.<br>
<strong>Solo</strong> — one book is standing alone with the long number.<br>
<strong>Soft book</strong> — a book that keeps being the longest, and those plays cash.<br>
<strong>Grader</strong> — NBA uses your BallDontLie GOAT key. NFL uses ESPN finals. Click Grade. Do not do it by hand.
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
        return line <= 120
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
    tev = c.get("true_ev")
    tev_txt = f"{tev}%" if tev is not None else "n/a"
    gap = c.get("ev_gap")
    gap_txt = f"{gap}%" if gap is not None else "n/a"
    if c.get("decision") == "TAKE" and (tev or 0) >= 3:
        return f"{bk} is the long number. Gap {gap_txt} vs the pack. Edge {tev_txt}."
    if c.get("decision") == "TAKE":
        return f"Books disagree. {bk} is longest. Gap {gap_txt}."
    return "Tight. The books agree. Skip."


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
    return st.session_state.get("ledger", []) if rows is None else rows


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


def grade_nba(ledger, bdl_key, days=5):
    if not bdl_key:
        return ledger, "No BallDontLie key. Add BALLDONTLIE_API_KEY to secrets."
    pending = [
        r for r in ledger
        if r.get("sport") == "NBA" and r.get("result") in (None, "", "—")
        and r.get("prop") in ("Assists", "Points", "Rebounds", "DoubleDouble")
    ]
    if not pending:
        return ledger, "NBA: nothing left to grade."
    by_name = defaultdict(list)
    for row in pending:
        by_name[_norm_name(row.get("player"))].append(row)
    updated, notes = 0, []
    for back in range(days):
        day = (datetime.now(timezone.utc) - timedelta(days=back)).strftime("%Y-%m-%d")
        status, games = bdl_get("games", bdl_key, {"dates[]": day, "per_page": 30})
        if status != 200:
            notes.append(f"{day} games {status}")
            continue
        ids = [g.get("id") for g in (games.get("data") or []) if g.get("id")]
        if not ids:
            continue
        status, stats = bdl_get("stats", bdl_key, {"game_ids[]": ids, "per_page": 100})
        if status != 200:
            notes.append(f"{day} stats {status}")
            continue
        for stat in stats.get("data") or []:
            player = stat.get("player") or {}
            full = _norm_name(f"{player.get('first_name', '')} {player.get('last_name', '')}")
            for row in by_name.get(full) or []:
                if row.get("result") in ("HIT", "MISS"):
                    continue
                pts = float(stat.get("pts") or 0)
                reb = float(stat.get("reb") or 0)
                ast = float(stat.get("ast") or 0)
                prop = row.get("prop")
                line = float(row.get("line") or 0)
                actual = {"Points": pts, "Rebounds": reb, "Assists": ast}.get(prop)
                if prop == "DoubleDouble":
                    actual, line = (1 if sum(x >= 10 for x in (pts, reb, ast)) >= 2 else 0), 1
                if actual is None:
                    continue
                row["result"] = "HIT" if actual >= line else "MISS"
                row["player_stat"] = actual
                updated += 1
    save_ledger(ledger)
    msg = f"NBA graded {updated}."
    if notes:
        msg += " API said: " + ", ".join(notes[:3])
    return ledger, msg


def espn(url, params=None):
    try:
        r = requests.get(url, params=params or {}, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def grade_nfl(ledger, days=5):
    pending = [
        r for r in ledger
        if r.get("sport") == "NFL" and r.get("result") in (None, "", "—")
        and r.get("prop") in ("Anytime TD", "Rec Yards")
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
            box = espn("https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary", {"event": ev.get("id")})
            players = []
            for team in ((box.get("boxscore") or {}).get("players") or []):
                for block in team.get("statistics") or []:
                    labels = [str(x).lower() for x in (block.get("labels") or [])]
                    for ath in block.get("athletes") or []:
                        nm = ((ath.get("athlete") or {}).get("displayName")) or ""
                        stats = ath.get("stats") or []
                        row = {labels[i]: stats[i] for i in range(min(len(labels), len(stats)))}
                        players.append((nm, row))
            for rec in pending:
                if rec.get("result") in ("HIT", "MISS"):
                    continue
                hit = next((row for nm, row in players if _norm_name(rec.get("player")) == _norm_name(nm) or _norm_name(rec.get("player")) in _norm_name(nm)), None)
                if not hit:
                    continue
                if rec.get("prop") == "Anytime TD":
                    td = 0
                    for k, v in hit.items():
                        if "td" in k:
                            try:
                                td += float(v)
                            except Exception:
                                pass
                    rec["result"] = "HIT" if td > 0 else "MISS"
                    rec["player_stat"] = td
                    updated += 1
                elif rec.get("prop") == "Rec Yards":
                    yds = None
                    for k in ("yds", "rec yds", "receiving yards"):
                        if k in hit:
                            try:
                                yds = float(str(hit[k]).split("-")[-1])
                            except Exception:
                                pass
                    if yds is None:
                        continue
                    rec["result"] = "HIT" if yds >= float(rec.get("line") or 0) else "MISS"
                    rec["player_stat"] = yds
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


def row_html(c, result=None):
    line_txt = "Yes" if c.get("prop") in ("DoubleDouble", "Anytime TD") else f"o{c.get('line')}"
    boxes = "".join(
        f'<div class="bk {"best" if bk == c.get("book") else ""}">{bk} {fmt_price(px)}</div>'
        for bk, px in sorted((c.get("book_prices") or {c.get("book"): c.get("price")}).items(), key=lambda z: -(z[1] or 0))
    )
    tags = "".join(f'<span class="tag">{t}</span>' for t in (c.get("tags") or []))
    cls = "row"
    if result == "HIT" or c.get("decision") == "TAKE":
        cls += " take" if result != "MISS" else " miss"
    if result == "HIT":
        cls += " hit"
    if result == "MISS":
        cls += " miss"
    pill = result or c.get("decision") or ""
    tev = c.get("true_ev")
    tev_txt = f"{tev}%" if tev is not None else "—"
    gap = c.get("ev_gap")
    gap_txt = f"gap {gap}%" if gap is not None else ""
    return (
        f'<div class="{cls}"><div class="who"><div class="player">{c.get("player")}</div>'
        f'<div class="prop">{c.get("prop")} {line_txt}</div></div>'
        f'<div class="books">{boxes}{tags}</div>'
        f'<div class="nums"><span class="score-pill">{pill}</span>'
        f'<span class="ev">{tev_txt}</span><span class="gap">{gap_txt} · {c.get("book")}</span>'
        f'<div class="why">{plain_reason(c)}</div></div></div>'
    )


def chip(label, hits, n, hot=False):
    rate = round(100 * hits / n) if n else 0
    cls = "rate-chip hot" if hot and n >= 8 else "rate-chip"
    return f'<div class="{cls}"><b>{rate}%</b><span>{label}<br>{hits} of {n}</span></div>'


def main():
    st.markdown('<div class="queen-banner">Girl Magic · 2.0</div>', unsafe_allow_html=True)
    st.markdown("# Odds, gaps, tells")
    st.markdown('<div class="how-to">Pull the board. The long number is the tell. Lock it. Grade closes it. No scrolling a thousand cards.</div>', unsafe_allow_html=True)
    api_key = secret("ODDS_API_KEY") or st.text_input("Odds API Key", type="password")
    if not api_key:
        st.info("Add your Odds API key.")
        return
    bdl_key = secret("BALLDONTLIE_API_KEY")
    auto_weights = load_auto_weights()
    with st.sidebar:
        st.markdown("### Book weights")
        st.caption("Heavier book counts more in the blend. Auto-tunes after 10 plays.")
        live = {}
        for short in sorted(BASE_WEIGHTS):
            live[short] = st.slider(short, 0.5, 4.0, float(auto_weights.get(short, BASE_WEIGHTS[short])), 0.1, key=f"w_{short}")
        if st.button("Reset weights"):
            save_auto_weights(BASE_WEIGHTS.copy())
            st.rerun()
    sport = st.radio("Lane", ["NBA", "NFL"], horizontal=True)
    if st.button("Pull the board", type="primary", use_container_width=True):
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
            st.session_state["last_sport"] = sport
            ledger = load_ledger()
            seen = {(r.get("player"), r.get("prop"), r.get("line"), r.get("price")) for r in ledger}
            added = 0
            for c in cards:
                if c.get("decision") == "TAKE" and (c.get("price") or 0) >= 150:
                    key = (c["player"], c["prop"], c["line"], c["price"])
                    if key not in seen:
                        ledger.append({
                            "ts": datetime.now().isoformat(timespec="minutes"), "sport": c["sport"],
                            "player": c["player"], "prop": c["prop"], "line": c["line"], "price": c["price"],
                            "book": c["book"], "event": c["event"], "true_ev": c.get("true_ev"),
                            "ev_gap": c.get("ev_gap"), "book_beh": c.get("book_beh"), "result": None,
                        })
                        seen.add(key)
                        added += 1
            save_ledger(ledger)
            takes = sum(1 for c in cards if c.get("decision") == "TAKE")
            st.toast(f"{takes} TAKE · auto-tracked {added}")
    cards = st.session_state.get(f"cards_{sport}") or []
    if st.session_state.get("last_sport") == sport and st.session_state.get("fetched"):
        st.caption(f"{sport} @ {st.session_state['fetched']} · {len(cards)} priced · {sum(1 for c in cards if c.get('decision')=='TAKE')} TAKE")
    board, tracker, glossary = st.tabs(["Board", "Tracker", "What this means"])
    with board:
        if not cards:
            st.info("Pull the board.")
        else:
            a, b, c = st.columns(3)
            simple = a.toggle("TAKE only", value=True)
            petty = b.toggle("Petty ranges", value=False)
            show_why = c.toggle("Show the why", value=True)
            props = ["Assists", "Points", "Rebounds", "DoubleDouble"] if sport == "NBA" else ["Anytime TD", "Rec Yards"]
            f1, f2 = st.columns(2)
            prop_filter = f1.multiselect("Prop", props, default=props)
            books = f2.multiselect("Longest book", ALL_BOOK_CODES, default=ALL_BOOK_CODES, format_func=lambda x: BOOK_FULL.get(x, x))
            min_odds = st.slider("Min odds", -200, 2000, 100, 25)
            filtered = [x for x in cards if x.get("prop") in prop_filter and x.get("book") in books and line_ok(x.get("prop"), x.get("line"))]
            if petty:
                filtered = [x for x in filtered if x.get("petty_range_match")]
            if simple:
                filtered = [x for x in filtered if x.get("decision") == "TAKE"]
            filtered = [x for x in filtered if (x.get("price") or 0) >= min_odds]
            filtered = sorted(filtered, key=lambda x: -(x.get("true_ev") or -999))[:80]
            if not filtered:
                st.info("Nothing clears. Turn TAKE only off, or drop the min odds.")
            else:
                st.markdown(f"**{len(filtered)} on the board.** Best gaps first. Not the whole slate.")
                by_game = defaultdict(list)
                for x in filtered:
                    by_game[x.get("event") or "Unknown"].append(x)
                for game, rows in by_game.items():
                    st.markdown(f'<div class="game-header">{game}</div>', unsafe_allow_html=True)
                    for i, x in enumerate(rows):
                        html = row_html(x)
                        if not show_why:
                            html = html.replace(f'<div class="why">{plain_reason(x)}</div>', "")
                        st.markdown(html, unsafe_allow_html=True)
                        if st.button("Lock", key=f"lk_{sport}_{game}_{i}_{x['player']}_{x['line']}"):
                            ledger = load_ledger()
                            ledger.append({
                                "ts": datetime.now().isoformat(timespec="minutes"), "sport": x["sport"],
                                "player": x["player"], "prop": x["prop"], "line": x["line"], "price": x["price"],
                                "book": x["book"], "event": x["event"], "true_ev": x.get("true_ev"),
                                "ev_gap": x.get("ev_gap"), "result": None,
                            })
                            save_ledger(ledger)
                            st.toast("Locked.")
    with tracker:
        ledger = load_ledger()
        c1, c2 = st.columns(2)
        if c1.button("Wipe tracker"):
            save_ledger([])
            st.rerun()
        if c2.button("Grade finals"):
            with st.spinner("Closing plays…"):
                if sport == "NBA":
                    ledger, msg = grade_nba(ledger, bdl_key)
                else:
                    ledger, msg = grade_nfl(ledger)
            st.success(msg)
            st.rerun()
        mine = [r for r in ledger if r.get("sport") == sport]
        if not mine:
            st.info("Nothing locked on this lane.")
        else:
            hits = sum(r.get("result") == "HIT" for r in mine)
            misses = sum(r.get("result") == "MISS" for r in mine)
            waiting = len(mine) - hits - misses
            a, b, c, d = st.columns(4)
            a.markdown(f'<div class="statpill"><b>{len(mine)}</b>locked</div>', unsafe_allow_html=True)
            b.markdown(f'<div class="statpill"><b>{hits}</b>hit</div>', unsafe_allow_html=True)
            c.markdown(f'<div class="statpill"><b>{misses}</b>miss</div>', unsafe_allow_html=True)
            d.markdown(f'<div class="statpill"><b>{waiting}</b>waiting</div>', unsafe_allow_html=True)
            graded = [r for r in mine if r.get("result") in ("HIT", "MISS")]
            if graded:
                st.markdown("**What cashed**")
                by_book = defaultdict(lambda: [0, 0])
                by_gap = defaultdict(lambda: [0, 0])
                for r in graded:
                    by_book[r.get("book") or "?"][1] += 1
                    by_book[r.get("book") or "?"][0] += r.get("result") == "HIT"
                    gap = r.get("ev_gap") or 0
                    bucket = "gap 40+" if gap >= 40 else "gap 20–39" if gap >= 20 else "gap under 20"
                    by_gap[bucket][1] += 1
                    by_gap[bucket][0] += r.get("result") == "HIT"
                html = "".join(chip(BOOK_FULL.get(bk, bk), h, n, h / n >= 0.2) for bk, (h, n) in sorted(by_book.items(), key=lambda z: -z[1][0]))
                html += "".join(chip(bucket, h, n, h / n >= 0.2) for bucket, (h, n) in by_gap.items())
                st.markdown(html, unsafe_allow_html=True)
            st.markdown("**Latest locks**")
            page = st.number_input("Page", min_value=1, value=1, step=1)
            start = (int(page) - 1) * 20
            for r in list(reversed(mine))[start:start + 20]:
                fake = {
                    "player": r.get("player"), "prop": r.get("prop"), "line": r.get("line"),
                    "book": r.get("book"), "price": r.get("price"), "true_ev": r.get("true_ev"),
                    "ev_gap": r.get("ev_gap"), "decision": r.get("result") or "LOCKED",
                    "book_prices": {r.get("book"): r.get("price")}, "tags": [],
                }
                st.markdown(row_html(fake, r.get("result")), unsafe_allow_html=True)
    with glossary:
        st.markdown(f'<div class="glossary">{GLOSSARY}</div>', unsafe_allow_html=True)


try:
    main()
except Exception as e:
    st.error(f"App error: {e}")
    st.exception(e)
