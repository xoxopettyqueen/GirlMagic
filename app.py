# -*- coding: utf-8 -*-
"""
Girl Magic Odds 2.0 — No early returns
Tracker and Glossary always render.
"""

import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path

st.set_page_config(page_title="Girl Magic Odds 2.0", page_icon="✨", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600;700&family=Pacifico&display=swap');
.stApp{background:#0c0c10!important;color:#fff!important;font-family:'Inter',sans-serif!important}
.hero{background:linear-gradient(90deg,#FF3EBF,#C77DFF,#7B2CBF)!important;border-radius:20px;padding:18px 22px;margin-bottom:12px;color:#fff;box-shadow:0 0 28px rgba(255,62,191,.4);animation:pulseBar 6s linear infinite}
@keyframes pulseBar{0%,100%{filter:brightness(1)}50%{filter:brightness(1.12)}}
.hero h1{margin:0;font-size:1.75rem;font-weight:700;font-family:'Inter',sans-serif;text-shadow:0 0 10px rgba(255,215,0,.45)}
.hero p{margin:4px 0 0;opacity:.95;font-size:1.05rem;color:#F5E9FF;font-family:'Pacifico',cursive;text-shadow:0 0 8px rgba(199,125,255,.6)}
button[kind="primary"], .stButton > button[kind="primary"]{background:linear-gradient(90deg,#FF3EBF,#FF7AC4)!important;border:none!important;border-radius:999px!important;font-weight:700!important;min-height:44px}
.card{background:linear-gradient(180deg,rgba(21,21,27,.95) 0%,rgba(16,16,20,.95) 100%);border:1px solid #2a2a33;border-radius:14px;padding:11px 13px;margin-bottom:10px;position:relative;transition:box-shadow .4s ease-in-out,transform .3s}
.card:hover{transform:translateY(-2px);box-shadow:0 0 22px rgba(255,62,191,.55)}
.card.take-card{border-color:#FF3EBF;box-shadow:0 0 16px rgba(255,62,191,.5)}
.card.true-ev-glow{border-color:#FF3EBF;box-shadow:0 0 22px rgba(255,62,191,.75)}
.card.dimmed{opacity:0.65;border-color:#5a4a6a}
.player{font-size:1.15rem;font-weight:700;margin:0;font-family:'Inter',sans-serif}
.meta{color:#aaa;font-size:.65rem;margin:2px 0 4px}
.prop{font-size:.85rem;font-weight:600;color:#FF3EBF;margin-bottom:4px;text-transform:uppercase}
.books{display:flex;flex-wrap:wrap;gap:4px;margin:4px 0}
.bk{background:#0d0d12;border:1px solid #333;border-radius:999px;padding:3px 7px;text-align:center;min-width:50px;font-size:.64rem;font-weight:600;color:#fff}
.bk.best{border-color:#FF3EBF;box-shadow:0 0 8px rgba(255,62,191,.6)}
.true-ev{font-size:.9rem;font-weight:700;color:#FF3EBF;margin:3px 0;text-shadow:0 0 6px rgba(255,62,191,.4)}
.score{font-size:.8rem;font-weight:700;color:#FFD700;margin:2px 0}
.why{font-size:.72rem;color:#e0d4f5;margin-top:4px;line-height:1.3;max-width:90%}
.take-tag{position:absolute;top:6px;right:8px;font-size:.55rem;letter-spacing:.1em;color:#FF3EBF;font-weight:700}
.tag{display:inline-block;background:rgba(199,125,255,.15);color:#F5E9FF;border:1px solid rgba(199,125,255,.4);border-radius:999px;padding:1px 6px;font-size:.55rem;margin:2px 2px 0 0}
.tag.range{background:rgba(255,62,191,.2);border-color:#FF3EBF}
.glossary{font-size:.85rem;color:#e8e0f0;margin-top:10px;padding:18px 20px;background:linear-gradient(180deg,#121218 0%,#0e0e14 100%);border-radius:12px;border:1px solid #2a2a33;line-height:1.7}
.glossary strong{color:#FF3EBF;font-weight:700}
.softness-title{font-size:1.1rem;font-weight:700;color:#fff;margin:18px 0 8px;font-family:'Inter',sans-serif}
.game-header{font-size:1.05rem;font-weight:700;color:#FF3EBF;margin:18px 0 8px;border-bottom:1px solid #2a2a33;padding-bottom:4px}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
LEDGER = Path("odds_ledger.json")
SHARPNESS = Path("book_sharpness.json")
WEIGHTS_FILE = Path("auto_weights.json")

MY_BOOKS = {
    "fanduel":"FD","draftkings":"DK","betmgm":"MGM","bet365":"365",
    "williamhill_us":"CZR","fanatics":"FAN","espnbet":"SCR","hardrockbet":"HR",
    "hardrockbet_az":"HR","hardrockbet_oh":"HR","hardrockbet_fl":"HR",
    "pinnacle":"PIN","circa":"CIR","bookmaker":"BM",
}
BOOK_FULL = {"FD":"FanDuel","DK":"DraftKings","MGM":"BetMGM","365":"Bet365","CZR":"Caesars","FAN":"Fanatics","SCR":"theScore","HR":"Hard Rock","PIN":"Pinnacle","CIR":"Circa","BM":"Bookmaker"}

ALL_BOOK_CODES = sorted(set(BOOK_FULL.keys()))

BASE_WEIGHTS = {
    "PIN": 3.5, "CIR": 3.0, "BM": 2.8,
    "FD": 2.0, "DK": 1.8, "365": 2.0, "MGM": 1.4,
    "CZR": 1.3, "FAN": 1.2, "SCR": 1.1, "HR": 1.1,
}

GLOSSARY = """
<strong>Glossary</strong><br><br>
<strong>True EV</strong> — Expected value vs the weighted fair price. Positive means the longest price is better than the blended fair number.<br>
<strong>Fair price</strong> — The no-vig probability after blending all books using their weights.<br>
<strong>EV Gap</strong> — How much longer the best price is compared to the median price.<br>
<strong>Spike</strong> — Chaos score that mixes the gap, how much the books moved, and how far apart they are.<br>
<strong>Volatility</strong> — How far apart the books currently are on the same prop.<br>
<strong>Solo / Cluster</strong> — Solo means one book is standing alone with the longest price. Cluster means the books are close together.<br>
<strong>Weak-spot</strong> — A book that has been hanging soft numbers more often than others.<br>
<strong>Petty Mode</strong> — Only shows props inside your preferred line ranges (Assists 3–8, Points 8–15, Rebounds 4–10).<br>
<strong>Auto Weights</strong> — The app watches which books are soft and slowly adjusts how much it trusts them.<br>
<strong>TAKE / LEAN / PASS</strong> — TAKE = strongest edges. LEAN = okay but optional. PASS = no real edge.<br>
<strong>Score</strong> — Simple strength number on TAKE cards (higher = stronger edge).
"""

def in_user_range(prop, line):
    if prop == "Assists": return 3 <= line <= 8
    if prop == "Points": return 8 <= line <= 15
    if prop == "Rebounds": return 4 <= line <= 10
    if prop in ("DoubleDouble", "Anytime TD"): return True
    return False

def load_sharpness():
    if SHARPNESS.exists():
        try: return json.loads(SHARPNESS.read_text())
        except: pass
    return {}

def save_sharpness(data):
    try: SHARPNESS.write_text(json.dumps(data, indent=2))
    except: pass

def load_auto_weights():
    if WEIGHTS_FILE.exists():
        try: return json.loads(WEIGHTS_FILE.read_text())
        except: pass
    return BASE_WEIGHTS.copy()

def save_auto_weights(w):
    try: WEIGHTS_FILE.write_text(json.dumps(w, indent=2))
    except: pass

def update_auto_weights(sharp):
    current = load_auto_weights()
    for bk, data in sharp.items():
        total = data.get("total", 0)
        soft = data.get("soft_count", 0)
        if total < 10: continue
        soft_rate = soft / total
        base = BASE_WEIGHTS.get(bk, 1.0)
        if soft_rate > 0.25:
            current[bk] = max(0.8, round(base * 0.75, 2))
        elif soft_rate > 0.15:
            current[bk] = max(0.9, round(base * 0.85, 2))
        else:
            current[bk] = round(min(3.5, base * 1.05), 2)
    save_auto_weights(current)
    return current

def implied(price):
    try:
        p = int(price)
        return 100/(p+100) if p > 0 else abs(p)/(abs(p)+100)
    except: return None

def weighted_fair_prob(book_prices, weights=None):
    if weights is None: weights = load_auto_weights()
    weighted = []
    total_w = 0.0
    for bk, price in book_prices.items():
        w = weights.get(bk, 1.0)
        if w <= 0: continue
        imp = implied(price)
        if imp and 0 < imp < 1:
            weighted.append(imp * w)
            total_w += w
    if not weighted or total_w == 0: return None
    fair = sum(weighted) / total_w
    return max(0.08, min(0.75, fair))

def compute_true_ev(best_price, fair_prob):
    if not fair_prob or best_price is None: return None
    try:
        decimal = (best_price / 100 + 1) if best_price > 0 else (100 / abs(best_price) + 1)
        ev = (fair_prob * decimal - 1) * 100
        return round(max(-15, min(18, ev)), 1)
    except: return None

def plain_reason(c):
    tev = c.get("true_ev") or 0
    bk = c.get("book", "")
    if c.get("decision") == "TAKE" and tev >= 3:
        return f"Strong edge. {bk} is hanging a soft number vs the blend."
    if c.get("decision") == "TAKE":
        return f"Books disagree. {bk} is the longest."
    return "Tight. Skip."

def card_score(true_ev, spike):
    tev = true_ev or 0
    sp = spike or 0
    raw = (max(0, tev) * 0.35) + (sp * 4)
    return round(max(1.0, min(10.0, raw)), 1)

def normalize_book(key):
    k = str(key or "").lower()
    if "pinnacle" in k: return "pinnacle"
    if "circa" in k: return "circa"
    if "bookmaker" in k: return "bookmaker"
    if "bet365" in k: return "bet365"
    if "fanatic" in k: return "fanatics"
    if "hardrock" in k: return "hardrockbet"
    if "espnbet" in k or "score" in k: return "espnbet"
    if "draftking" in k: return "draftkings"
    if "fanduel" in k: return "fanduel"
    if "betmgm" in k or k == "mgm": return "betmgm"
    if "williamhill" in k or "caesar" in k: return "williamhill_us"
    return k

def load_ledger():
    if LEDGER.exists():
        try: return json.loads(LEDGER.read_text())
        except: pass
    return st.session_state.get("ledger", [])

def save_ledger(rows):
    st.session_state["ledger"] = rows
    try: LEDGER.write_text(json.dumps(rows, indent=2))
    except: pass

def auto_grade_nba(ledger):
    try:
        r = requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard", timeout=10)
        if r.status_code != 200:
            return ledger
        data = r.json()
    except:
        return ledger

    finished = []
    for event in data.get("events", []):
        status = (event.get("status", {}).get("type", {}) or {}).get("name", "")
        if status not in ("STATUS_FINAL", "STATUS_FULL_TIME"):
            continue
        finished.append(event.get("id"))

    if not finished:
        return ledger

    updated = False
    for row in ledger:
        if row.get("sport") != "NBA" or row.get("result") is not None:
            continue
        player = (row.get("player") or "").lower()
        prop = row.get("prop")
        line = row.get("line")
        if not player or prop not in ("Assists", "Points", "Rebounds", "DoubleDouble"):
            continue

        for game_id in finished:
            try:
                box = requests.get(
                    f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}",
                    timeout=8
                )
                if box.status_code != 200:
                    continue
                box_data = box.json()
            except:
                continue

            for team in box_data.get("boxscore", {}).get("players", []):
                stats_list = team.get("statistics", [{}])
                if not stats_list:
                    continue
                for athlete in stats_list[0].get("athletes", []):
                    name = (athlete.get("athlete", {}).get("displayName") or "").lower()
                    if player not in name and name not in player:
                        continue
                    stats = athlete.get("stats", [])
                    try:
                        reb = float(stats[4]) if len(stats) > 4 else 0
                        ast = float(stats[5]) if len(stats) > 5 else 0
                        pts = float(stats[11]) if len(stats) > 11 else 0
                    except:
                        continue

                    actual = None
                    if prop == "Assists":
                        actual = ast
                    elif prop == "Points":
                        actual = pts
                    elif prop == "Rebounds":
                        actual = reb
                    elif prop == "DoubleDouble":
                        actual = 1 if sum(1 for x in (pts, reb, ast) if x >= 10) >= 2 else 0

                    if actual is not None:
                        row["result"] = "hit" if actual > line else "miss"
                        updated = True
                        break
            if row.get("result"):
                break

    if updated:
        save_ledger(ledger)
    return ledger

@st.cache_data(ttl=120)
def fetch_events(api_key, sport_key):
    try:
        r = requests.get(f"{ODDS_API_BASE}/sports/{sport_key}/events", params={"apiKey": api_key}, timeout=15)
        if r.status_code == 200: return r.json() or []
    except: pass
    return []

@st.cache_data(ttl=90)
def fetch_odds(api_key, sport_key, event_id, markets):
    try:
        r = requests.get(f"{ODDS_API_BASE}/sports/{sport_key}/events/{event_id}/odds",
            params={"apiKey": api_key, "regions": "us,us2,uk", "markets": markets, "oddsFormat": "american"}, timeout=20)
        if r.status_code == 200: return r.json()
    except: pass
    return None

def parse_plays(data, sport):
    if not data: return []
    event = f"{data.get('away_team')} @ {data.get('home_team')}"
    plays = []
    for book in data.get("bookmakers") or []:
        bk = normalize_book(book.get("key"))
        if bk not in MY_BOOKS: continue
        short = MY_BOOKS[bk]
        for market in book.get("markets") or []:
            mkey = (market.get("key") or "").lower()
            prop_type = None
            if "NBA" in str(sport) or "basketball" in str(sport).lower():
                if "assist" in mkey: prop_type = "Assists"
                elif "point" in mkey and "rebound" not in mkey and "assist" not in mkey: prop_type = "Points"
                elif "rebound" in mkey and "point" not in mkey and "assist" not in mkey: prop_type = "Rebounds"
                elif "double_double" in mkey: prop_type = "DoubleDouble"
            else:
                if "anytime_td" in mkey: prop_type = "Anytime TD"
                elif "reception_yds" in mkey or "receiving_yds" in mkey: prop_type = "Rec Yards"
            if not prop_type: continue
            for o in market.get("outcomes") or []:
                oname = str(o.get("name") or "").lower().strip()
                desc = str(o.get("description") or "").lower().strip()
                full_text = f"{oname} {desc}"

                is_over_like = (
                    oname in ("over", "yes", "o")
                    or "over" in oname
                    or "+" in full_text
                    or "or more" in full_text
                    or full_text.startswith("o")
                )

                if prop_type in ("DoubleDouble", "Anytime TD"):
                    if "yes" not in oname and oname not in ("over", "yes"): continue
                    player = o.get("description") or o.get("name")
                    line = 0.5 if prop_type == "Anytime TD" else 1.0
                else:
                    if not is_over_like: continue
                    player = o.get("description") or o.get("name")
                    line = o.get("point")
                    if line is None:
                        m = re.search(r"(\d+\.?\d*)", full_text)
                        if m:
                            try:
                                line = float(m.group(1))
                            except:
                                continue
                        else:
                            continue
                    else:
                        try:
                            line = float(line)
                        except:
                            continue

                if not player or str(player).lower() in ("yes", "no", "over", "under", "o", "u"): continue
                try:
                    price = int(o.get("price"))
                except:
                    continue
                plays.append({
                    "sport": sport, "event": event, "player": player,
                    "prop": prop_type, "line": line, "price": price, "book": short
                })
    return plays

def compute_signals(book_prices, best_price):
    prices = list(book_prices.values())
    if not prices: return {}, "PASS"
    med = sorted(prices)[len(prices)//2]
    longest = max(prices)
    ev_gap = (longest - med) / med if med else 0
    spread = (max(prices) - min(prices)) / med if med else 0
    vol = "High" if spread > 0.4 else "Medium" if spread > 0.15 else "Low"
    move = "Snap" if spread > 0.5 else "Drift" if spread > 0.2 else "Freeze"
    book_beh = "Solo" if len(prices) <= 2 or (longest - med) / med > 0.6 else "Cluster"
    spike = ev_gap + (0.3 if vol == "High" else 0.15 if vol == "Medium" else 0.05) * spread
    if spike > 0.25 and vol != "Low": decision = "TAKE"
    elif spike > 0.08: decision = "LEAN"
    else: decision = "PASS"
    return {
        "median": int(med), "longest": longest, "ev_gap": round(ev_gap*100, 1),
        "vol": vol, "move": move, "book_beh": book_beh, "spike": round(spike, 2),
        "decision": decision,
    }, decision

def update_sharpness(cards):
    sharp = load_sharpness()
    for c in cards:
        bk = c.get("book")
        if not bk: continue
        if bk not in sharp: sharp[bk] = {"soft_count": 0, "total": 0, "props": {}}
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
        key = (p["sport"], p["player"], p["prop"], round(p["line"], 1), p["event"])
        by[key].append(p)
    cards = []
    sharp = load_sharpness()
    for key, group in by.items():
        best = max(group, key=lambda x: x["price"])
        book_prices = {g["book"]: g["price"] for g in group}
        signals, decision = compute_signals(book_prices, best["price"])
        fair = weighted_fair_prob(book_prices, weights)
        true_ev = compute_true_ev(best["price"], fair)
        petty = in_user_range(best["prop"], best["line"])
        tags = []
        if signals.get("book_beh") == "Solo": tags.append("Solo")
        if signals.get("move") == "Snap": tags.append("Snap")
        if signals.get("vol") == "High": tags.append("Surge")
        bk = best["book"]
        if bk in sharp and sharp[bk]["soft_count"] >= 3:
            tags.append(f"{bk} soft")
        if true_ev and true_ev >= 3: tags.append("True EV")
        if petty:
            tags.append("In range")
        else:
            tags.append("Outside range")
        score = card_score(true_ev, signals.get("spike"))
        cards.append({
            **best, "book_prices": book_prices, **signals, "tags": tags,
            "decision": decision,
            "fair_prob": round(fair*100, 1) if fair else None,
            "true_ev": true_ev,
            "one_sided": True,
            "petty_range_match": petty,
            "devig_method": "multiplicative",
            "score": score,
        })
    cards.sort(key=lambda x: (x.get("event", ""), -(x.get("true_ev") or -999)))
    return cards

def render_softness(sharp):
    if not sharp: return
    rows = []
    for bk, data in sharp.items():
        total = data.get("total", 0)
        soft = data.get("soft_count", 0)
        pct = round((soft / total * 100), 1) if total else 0
        props = data.get("props", {})
        top_prop = max(props, key=props.get) if props else "—"
        rows.append({
            "Book": BOOK_FULL.get(bk, bk),
            "% Soft": pct,
            "Softest Prop": top_prop
        })
    if not rows: return
    df = pd.DataFrame(rows).sort_values("% Soft", ascending=False)
    st.markdown('<div class="softness-title">Which books are soft</div>', unsafe_allow_html=True)
    softest = df.iloc[0]
    st.markdown(f"**{softest['Book']}** is hanging soft numbers most often right now ({softest['% Soft']}% on {softest['Softest Prop']}).")
    chart_df = df.set_index("Book")[["% Soft"]]
    st.bar_chart(chart_df, use_container_width=True, color="#FF3EBF")

def main():
    st.markdown('<div class="hero"><h1>✨ Girl Magic Odds 2.0</h1><p>Open the site. Edges appear. You lock them. 💅</p></div>', unsafe_allow_html=True)

    api_key = st.secrets.get("ODDS_API_KEY", "") or st.text_input("Odds API Key", type="password")
    if not api_key:
        st.info("Add your Odds API key.")
        return

    auto_weights = load_auto_weights()

    with st.sidebar:
        st.markdown("### 💅 Book Weights (auto)")
        st.caption("Updated automatically. Override only if you want.")
        live_weights = {}
        for short in sorted(set(list(BASE_WEIGHTS.keys()) + list(BOOK_FULL.keys()))):
            default = auto_weights.get(short, BASE_WEIGHTS.get(short, 1.0))
            live_weights[short] = st.slider(short, 0.5, 4.0, float(default), 0.1, key=f"w_{short}")
        if st.button("Reset weights to auto"):
            save_auto_weights(BASE_WEIGHTS.copy())
            st.rerun()

    sport_choice = st.radio("Lane", ["NBA 🔮", "NFL 🔥"], horizontal=True, key="sport_choice")
    current_sport = "NBA" if "NBA" in sport_choice else "NFL"

    if st.button("Pull the chaos 💅", type="primary", use_container_width=True):
        sport_key = "basketball_nba" if current_sport == "NBA" else "americanfootball_nfl"
        markets = ("player_assists,player_assists_alternate,player_points,player_points_alternate,"
                   "player_rebounds,player_rebounds_alternate,player_double_double"
                   if current_sport == "NBA" else
                   "player_anytime_td,player_reception_yds,player_reception_yds_alternate")
        with st.spinner(f"Pulling {current_sport} edges…"):
            events = fetch_events(api_key, sport_key)
            now = datetime.utcnow()
            pregame = [ev for ev in events if ev.get("commence_time") and datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00")).replace(tzinfo=None) > now]
            target = pregame if pregame else events
            all_plays = []
            for ev in target[:30]:
                data = fetch_odds(api_key, sport_key, ev.get("id"), markets)
                if data:
                    all_plays.extend(parse_plays(data, current_sport))
            cards = best_cards(all_plays, live_weights)
            sharp = update_sharpness(cards)
            update_auto_weights(sharp)
            st.session_state[f"cards_{current_sport}"] = cards
            st.session_state["fetched"] = datetime.now().strftime("%H:%M")
            st.session_state["last_sport"] = current_sport
            ledger = load_ledger()
            existing = {(r.get("player"), r.get("prop"), r.get("line"), r.get("price")) for r in ledger}
            added = 0
            for c in cards:
                if c.get("decision") == "TAKE" and (c.get("price") or 0) >= 300:
                    key = (c["player"], c["prop"], c["line"], c["price"])
                    if key not in existing:
                        ledger.append({
                            "ts": datetime.now().isoformat(timespec="minutes"),
                            "sport": c["sport"], "player": c["player"], "prop": c["prop"],
                            "line": c["line"], "price": c["price"],
                            "book": BOOK_FULL.get(c["book"], c["book"]),
                            "event": c["event"],
                            "true_ev": c.get("true_ev"),
                            "fair_prob": c.get("fair_prob"),
                            "decision": c.get("decision"),
                            "petty_range_match": c.get("petty_range_match"),
                            "result": None,
                            "clv": None,
                            "locked_price": c["price"],
                            "petty_mode": st.session_state.get("petty_mode", True),
                        })
                        existing.add(key)
                        added += 1
            save_ledger(ledger)
            if added: st.toast(f"Auto-tracked {added} TAKE plays (+300+)")
            st.toast("Weights auto-tuned")

    cards = st.session_state.get(f"cards_{current_sport}") or []
    if st.session_state.get("fetched") and st.session_state.get("last_sport") == current_sport:
        st.caption(f"{current_sport} board live @ {st.session_state['fetched']} — {len(cards)} props")

    tab_board, tab_tracker, tab_glossary = st.tabs(["📊 Board", "🔒 Tracker", "📖 Glossary"])

    with tab_board:
        if not cards:
            st.info(f"Hit **Pull the chaos** for {current_sport}.")
        else:
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                simple_mode = st.toggle("✨ Simple Mode", value=st.session_state.get("simple_mode", True))
                st.session_state["simple_mode"] = simple_mode
            with col_b:
                detailed = st.toggle("🔍 Detailed", value=st.session_state.get("detailed", False))
                st.session_state["detailed"] = detailed
            with col_c:
                petty_mode = st.toggle("💅 Petty Mode", value=st.session_state.get("petty_mode", False))
                st.session_state["petty_mode"] = petty_mode

            f1, f2, f3 = st.columns(3)
            with f1:
                prop_options = ["Assists", "Points", "Rebounds", "DoubleDouble"] if current_sport == "NBA" else ["Anytime TD", "Rec Yards"]
                prop_filter = st.multiselect("Prop Type", prop_options, default=prop_options)
            with f2:
                decision_filter = st.multiselect("Decision", ["TAKE", "LEAN", "PASS"], default=["TAKE", "LEAN"])
            with f3:
                min_ev = st.slider("Min True EV %", -5.0, 15.0, 0.0, 0.5)

            o1, o2 = st.columns(2)
            with o1:
                min_odds = st.number_input("Min Odds", value=-500, step=50)
            with o2:
                max_odds = st.number_input("Max Odds", value=2000, step=100)

            book_filter = st.multiselect(
                "Book (longest price)",
                ALL_BOOK_CODES,
                default=ALL_BOOK_CODES,
                format_func=lambda x: BOOK_FULL.get(x, x)
            )

            filtered = cards[:]
            if petty_mode:
                filtered = [c for c in filtered if c.get("petty_range_match")]
            if simple_mode:
                filtered = [c for c in filtered if c.get("decision") == "TAKE" and (c.get("true_ev") or 0) >= 2]
            filtered = [c for c in filtered if c.get("prop") in prop_filter]
            filtered = [c for c in filtered if c.get("decision") in decision_filter]
            filtered = [c for c in filtered if (c.get("true_ev") or -999) >= min_ev]
            filtered = [c for c in filtered if min_odds <= c.get("price", 0) <= max_odds]
            filtered = [c for c in filtered if c.get("book") in book_filter]

            if not filtered:
                st.info("No matching edges with current filters.")
            else:
                st.markdown(f"**{len(filtered)} plays ready.**")
                by_game = defaultdict(list)
                for c in filtered:
                    by_game[c.get("event", "Unknown")].append(c)
                for game, game_cards in by_game.items():
                    st.markdown(f'<div class="game-header">{game}</div>', unsafe_allow_html=True)
                    cols = st.columns(2)
                    for i, c in enumerate(game_cards):
                        line_txt = f"o{c['line']}" if c["prop"] not in ("DoubleDouble", "Anytime TD") else "Yes"
                        boxes_html = "".join(
                            f'<div class="bk {"best" if bk == c["book"] else ""}"><span>{bk}</span>{px:+d}</div>'
                            for bk, px in sorted(c.get("book_prices", {}).items(), key=lambda x: -x[1])
                        )
                        tags_html = "".join(
                            f'<span class="tag {"range" if "range" in t.lower() else ""}">{t}</span>'
                            for t in c.get("tags", [])
                        ) if not simple_mode else ""
                        card_cls = "card"
                        if c.get("decision") == "TAKE": card_cls += " take-card"
                        if (c.get("true_ev") or 0) >= 3 and c.get("decision") == "TAKE": card_cls += " true-ev-glow"
                        if not c.get("petty_range_match") and not simple_mode:
                            card_cls += " dimmed"
                        take_tag = '<div class="take-tag">TAKE</div>' if c.get("decision") == "TAKE" else ""
                        score_val = c.get("score")
                        score_html = f'<div class="score">Score {score_val}</div>' if c.get("decision") == "TAKE" and score_val is not None else ""
                        html = (
                            f'<div class="{card_cls}">{take_tag}'
                            f'<div class="player">{c["player"]}</div>'
                            f'<div class="meta">{c["event"]}</div>'
                            f'<div class="prop">{c["prop"]} {line_txt}</div>'
                            f'<div class="books">{boxes_html}</div>'
                            f'{tags_html}'
                            f'<div class="true-ev">True EV {c.get("true_ev", "—")}%</div>'
                            f'{score_html}'
                            f'<div class="why">{plain_reason(c)}</div>'
                            f'</div>'
                        )
                        with cols[i % 2]:
                            st.markdown(html, unsafe_allow_html=True)
                            if detailed:
                                with st.expander("Why this is a play"):
                                    tev = c.get("true_ev") or 0
                                    bk = c.get("book", "")
                                    st.markdown(f"**Decision:** {c.get('decision')}")
                                    if c.get("decision") == "TAKE" and tev >= 3:
                                        st.markdown(f"**Why it glows:** {bk} is the longest price and the weighted fair price says this is a real edge ({tev}%).")
                                    elif c.get("decision") == "TAKE":
                                        st.markdown(f"**Why it shows:** {bk} is paying more than the blend.")
                                    else:
                                        st.markdown("**Why it’s here:** The numbers are close.")
                            if st.button("Lock 🔒", key=f"lk_{current_sport}_{game}_{i}_{c['player']}_{c['prop']}_{c['line']}"):
                                ledger = load_ledger()
                                ledger.append({
                                    "ts": datetime.now().isoformat(timespec="minutes"),
                                    "sport": c["sport"], "player": c["player"], "prop": c["prop"],
                                    "line": c["line"], "price": c["price"],
                                    "book": BOOK_FULL.get(c["book"], c["book"]),
                                    "event": c["event"],
                                    "true_ev": c.get("true_ev"),
                                    "decision": c.get("decision"),
                                    "result": None,
                                    "locked_price": c["price"],
                                })
                                save_ledger(ledger)
                                st.toast("Locked.")

    with tab_tracker:
        ledger = load_ledger()
        ledger = auto_grade_nba(ledger)
        sharp = load_sharpness()
        if st.button("Wipe the slate"):
            save_ledger([])
            st.rerun()
        if not ledger:
            st.info("Nothing locked yet.")
        else:
            clean = [r for r in ledger if (r.get("price") or 0) >= 300]
            if not clean:
                st.info("No +300 or higher plays locked yet.")
            else:
                df = pd.DataFrame(clean)
                keep = ["ts", "sport", "player", "prop", "line", "price", "book", "event", "true_ev", "decision", "result"]
                existing = [c for c in keep if c in df.columns]
                df = df[existing].fillna("—")
                finished = df[df["result"].isin(["hit", "miss"])] if "result" in df.columns else pd.DataFrame()
                hits = (finished["result"] == "hit").sum() if not finished.empty else 0
                st.markdown(f"**{len(df)} longer-priced plays locked.** {len(finished)} finished. {hits} hit.")
                st.dataframe(df, use_container_width=True, hide_index=True)
                render_softness(sharp)

    with tab_glossary:
        st.markdown(f'<div class="glossary">{GLOSSARY}</div>', unsafe_allow_html=True)

try:
    main()
except Exception as e:
    st.error(f"App error: {e}")
    st.exception(e)
