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
.card{margin-bottom:10px;padding:12px 14px;border-radius:14px;background:linear-gradient(90deg,#1a1a24,#2a2a3a);border:2px solid #ff00cc;box-shadow:0 0 14px #ff00cc44;transition:transform .15s,box-shadow .15s}
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
<strong>This is a price-gap tool.</strong> The longest number against the pack is the tell.<br><br>
<strong>True EV</strong> — longest price vs the weighted blend.<br>
<strong>Gap</strong> — how much longer the best price is than the median.<br>
<strong>Spike</strong> — gap plus how far apart the books are. High spike is TAKE.<br>
<strong>Solo</strong> — one book standing alone with the long number.<br>
<strong>Soft book</strong> — keeps being the longest, and those plays cash.<br>
<strong>Grader</strong> — NBA uses your BallDontLie GOAT key. NFL uses ESPN finals.
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
                row["graded_ts"] = datetime.now().isoformat(timespec="minutes")
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
                    rec["graded_ts"] = datetime.now().isoformat(timespec="minutes")
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
    line_txt = "Yes" if c.get("prop") in ("DoubleDouble", "Anytime TD") else f"o{c.get('line')}"
    prices = c.get("book_prices") or {c.get("book"): c.get("price")}
    boxes = "".join(
        f'<span class="bk {"best" if bk == c.get("book") else ""}">{bk} {fmt_price(px)}</span>'
        for bk, px in sorted(prices.items(), key=lambda z: -(z[1] or 0))
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
    gap = c.get("ev_gap")
    stat = c.get("player_stat")
    got = f" · got {stat}" if stat is not None else ""
    clv = c.get("clv")
    clv_txt = f"{clv:+.1f}" if isinstance(clv, (int, float)) else "—"
    locked = c.get("ts") or "—"
    graded = c.get("graded_ts") or "—"
    desc = (
        f"Longest was {c.get('book') or '?'} {fmt_price(c.get('price'))}. "
        f"Gap {gap if gap is not None else '—'}% vs the pack. "
        f"Edge {tev if tev is not None else '—'}%. CLV {clv_txt}."
    )
    return (
        f'<div class="{cls}">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
        f'<div><div class="player">{c.get("player")}</div>'
        f'<div class="prop">{c.get("prop")} {line_txt}{got}</div>'
        f'<div style="color:#c9b8de;font-size:.72rem">{c.get("event") or ""}</div></div>'
        f'<div style="text-align:right"><span class="pill">{state or "TAKE"}</span>'
        f'<div class="ev">{tev if tev is not None else "—"}%</div>'
        f'<div style="color:#ffe27a;font-size:.72rem">gap {gap if gap is not None else "—"}%</div></div></div>'
        f'<div class="books" style="margin-top:8px">{boxes}</div>'
        f'<div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">'
        f'<span class="tag">book {c.get("book") or "?"}</span>'
        f'<span class="tag">price {fmt_price(c.get("price"))}</span>'
        f'<span class="tag">edge {tev if tev is not None else "—"}%</span>'
        f'<span class="tag">CLV {clv_txt}</span>'
        f'<span class="tag">locked {locked}</span>'
        f'<span class="tag">graded {graded}</span></div>'
        f'<div class="why">{desc}</div></div>'
    )


def chip(label, hits, n):
    rate = round(100 * hits / n) if n else 0
    hot = " hot" if n >= 8 and hits / n >= 0.15 else ""
    return f'<div class="rate-chip{hot}"><b>{rate}%</b><span>{label}<br>{hits} of {n}</span></div>'


def counters(locked, finished, hits, misses):
    st.markdown(
        f'''<div class="counters">
        <div class="counter locked">Locked<b>{locked}</b></div>
        <div class="counter done">Finished<b>{finished}</b></div>
        <div class="counter hits">Hits<b>{hits}</b></div>
        <div class="counter miss">Misses<b>{misses}</b></div>
        </div>''',
        unsafe_allow_html=True,
    )


def main():
    st.markdown("# ✨ Girl Magic Odds 2.0")
    st.markdown('<div class="pulse-bar"></div>', unsafe_allow_html=True)
    st.markdown('<div class="how-to">Pull the board. The long number is the tell. Lock it. Grade closes it.</div>', unsafe_allow_html=True)
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
                if c.get("decision") == "TAKE" and (c.get("price") or 0) >= 150 and line_ok(c.get("prop"), c.get("line")):
                    key = (c["player"], c["prop"], c["line"], c["price"])
                    if key not in seen:
                        ledger.append({
                            "ts": datetime.now().isoformat(timespec="minutes"), "sport": c["sport"],
                            "player": c["player"], "prop": c["prop"], "line": c["line"], "price": c["price"],
                            "book": c["book"], "event": c["event"], "true_ev": c.get("true_ev"),
                            "ev_gap": c.get("ev_gap"), "result": None,
                        })
                        seen.add(key)
                        added += 1
            save_ledger(ledger)
            st.toast(f"{sum(1 for c in cards if c.get('decision')=='TAKE')} TAKE · tracked {added}")
    cards = st.session_state.get(f"cards_{sport}") or []
    if st.session_state.get("last_sport") == sport and st.session_state.get("fetched"):
        st.caption(f"{sport} @ {st.session_state['fetched']} · {len(cards)} priced · {sum(1 for c in cards if c.get('decision')=='TAKE')} TAKE")
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
            min_odds = st.slider("Min odds", -200, 2000, 100, 25)
            filtered = [x for x in cards if x.get("prop") in prop_filter and line_ok(x.get("prop"), x.get("line")) and (x.get("price") or 0) >= min_odds]
            if petty:
                filtered = [x for x in filtered if x.get("petty_range_match")]
            if simple:
                filtered = [x for x in filtered if x.get("decision") == "TAKE"]
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
                for i, x in enumerate(rows):
                    st.markdown(glow_card(x), unsafe_allow_html=True)
                    if st.button("Lock", key=f"lk_{sport}_{page}_{game}_{i}_{x['player']}_{x['line']}"):
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
        if c1.button("Wipe tracker"):
            save_ledger([])
            st.rerun()
        if c2.button("Grade finals"):
            with st.spinner("Closing plays…"):
                ledger, msg = grade_nba(ledger, bdl_key) if sport == "NBA" else grade_nfl(ledger)
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
        tab_all, tab_hits, tab_misses, tab_locked, tab_charts = st.tabs(["All Plays", "Hits Only", "Misses Only", "Locked Only", "Charts"])

        def show(rows, key):
            if not rows:
                st.caption("Nothing in this cut.")
                return
            page = st.number_input("Page", min_value=1, value=1, step=1, key=key)
            start = (int(page) - 1) * 10
            for r in list(reversed(rows))[start:start + 10]:
                card = {
                    "player": r.get("player"), "prop": r.get("prop"), "line": r.get("line"),
                    "book": r.get("book"), "price": r.get("price"), "true_ev": r.get("true_ev"),
                    "ev_gap": r.get("ev_gap"), "event": r.get("event"), "ts": r.get("ts"),
                    "graded_ts": r.get("graded_ts"), "player_stat": r.get("player_stat"),
                    "clv": r.get("clv"), "book_prices": {r.get("book"): r.get("price")},
                    "decision": r.get("result") or "LOCKED",
                }
                st.markdown(glow_card(card, r.get("result") or "LOCKED"), unsafe_allow_html=True)
            st.caption(f"{len(rows)} plays · page {int(page)}")

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
                ).properties(height=260, title="Hit rate by book")
                st.altair_chart(hit_chart, use_container_width=True)
                gap_df = pd.DataFrame([{"gap": r.get("ev_gap") or 0, "edge": r.get("true_ev") or 0, "result": r.get("result")} for r in graded])
                scatter = alt.Chart(gap_df).mark_circle(size=70).encode(
                    x=alt.X("gap:Q", title="Gap %"),
                    y=alt.Y("edge:Q", title="Edge %"),
                    color=alt.Color("result:N", scale=alt.Scale(domain=["HIT", "MISS"], range=["gold", "#ff00cc"])),
                    tooltip=["gap", "edge", "result"],
                ).properties(height=260, title="Gap vs edge")
                st.altair_chart(scatter, use_container_width=True)
                pie_df = pd.DataFrame([{"result": "HIT", "count": sum(r.get("result")=="HIT" for r in graded)}, {"result": "MISS", "count": sum(r.get("result")=="MISS" for r in graded)}])
                pie = alt.Chart(pie_df).mark_arc(innerRadius=55).encode(
                    theta="count:Q",
                    color=alt.Color("result:N", scale=alt.Scale(domain=["HIT", "MISS"], range=["gold", "#555"])),
                    tooltip=["result", "count"],
                ).properties(height=260, title="Hit vs miss")
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
