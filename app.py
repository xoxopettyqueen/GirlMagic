# -*- coding: utf-8 -*-
"""
Girl Magic Odds 2.0 — Phase 2
Detailed Mode + book sharpness + steam/lag + weak spots + CLV ready.
"""

import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
from collections import defaultdict
from pathlib import Path

st.set_page_config(page_title="Girl Magic Odds 2.0", page_icon="✨", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;600;700&family=Pacifico&display=swap');
.stApp{background:#0e0e12!important;color:#fff!important;font-family:'Inter',sans-serif!important}
.hero{background:linear-gradient(90deg,#FF3EBF,#C77DFF,#7B2CBF)!important;border-radius:20px;padding:16px 20px;margin-bottom:12px;color:#fff;box-shadow:0 0 24px rgba(255,62,191,.35)}
.hero h1{margin:0;font-size:1.55rem;font-weight:700;font-family:'Playfair Display',serif}
.hero p{margin:3px 0 0;opacity:.9;font-size:.8rem;color:#F5E9FF;font-family:'Pacifico',cursive}
button[kind="primary"], .stButton > button[kind="primary"]{background:linear-gradient(90deg,#FF3EBF,#FF7AC4)!important;border:none!important;border-radius:999px!important;font-weight:700!important}
.card{background:linear-gradient(180deg,#16161c 0%,#121218 100%);border:1px solid #2a2a33;border-radius:14px;padding:10px 12px;margin-bottom:10px;position:relative}
.card.take-card{border-color:#FF3EBF;box-shadow:0 0 18px rgba(255,62,191,.55)}
.card.true-ev-glow{border-color:#FF3EBF;box-shadow:0 0 24px rgba(255,62,191,.8)}
.player{font-size:1.08rem;font-weight:700;margin:0;font-family:'Playfair Display',serif}
.meta{color:#999;font-size:.65rem;margin:1px 0 4px}
.prop{font-size:.82rem;font-weight:600;color:#FF3EBF;margin-bottom:4px;text-transform:uppercase}
.books{display:flex;flex-wrap:wrap;gap:3px;margin:4px 0}
.bk{background:#0d0d12;border:1px solid #333;border-radius:999px;padding:3px 7px;text-align:center;min-width:52px;font-size:.65rem;font-weight:600}
.bk.best{border-color:#FF3EBF;box-shadow:0 0 8px rgba(255,62,191,.6)}
.true-ev{font-size:.8rem;font-weight:700;color:#FF3EBF;margin:3px 0}
.why{font-size:.68rem;color:#ddd;margin-top:4px;line-height:1.3}
.take-tag{position:absolute;top:6px;right:8px;font-size:.55rem;letter-spacing:.1em;color:#FF3EBF;font-weight:700}
.tag{display:inline-block;background:rgba(199,125,255,.15);color:#F5E9FF;border:1px solid rgba(199,125,255,.4);border-radius:999px;padding:1px 6px;font-size:.55rem;margin:2px 2px 0 0}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
LEDGER = Path("odds_ledger.json")
SHARPNESS = Path("book_sharpness.json")

MY_BOOKS = {
    "fanduel":"FD","draftkings":"DK","betmgm":"MGM","bet365":"365",
    "williamhill_us":"CZR","fanatics":"FAN","espnbet":"SCR","hardrockbet":"HR",
    "hardrockbet_az":"HR","hardrockbet_oh":"HR","hardrockbet_fl":"HR",
    "pinnacle":"PIN","circa":"CIR","bookmaker":"BM",
}
BOOK_FULL = {"FD":"FanDuel","DK":"DraftKings","MGM":"BetMGM","365":"Bet365","CZR":"Caesars","FAN":"Fanatics","SCR":"theScore","HR":"Hard Rock","PIN":"Pinnacle","CIR":"Circa","BM":"Bookmaker"}

DEFAULT_WEIGHTS = {
    "PIN": 3.5, "CIR": 3.0, "BM": 2.8,
    "FD": 2.0, "DK": 1.8, "365": 2.0, "MGM": 1.4,
    "CZR": 1.3, "FAN": 1.2, "SCR": 1.1, "HR": 1.1,
}

def load_sharpness():
    if SHARPNESS.exists():
        try: return json.loads(SHARPNESS.read_text())
        except: pass
    return {}

def save_sharpness(data):
    try: SHARPNESS.write_text(json.dumps(data, indent=2))
    except: pass

def implied(price):
    try:
        p = int(price)
        return 100/(p+100) if p > 0 else abs(p)/(abs(p)+100)
    except: return None

def weighted_fair_prob(book_prices, weights=None):
    if weights is None: weights = DEFAULT_WEIGHTS
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
        return round(max(-20, min(25, ev)), 1)
    except: return None

def plain_reason(c):
    tev = c.get("true_ev") or 0
    if c.get("decision") == "TAKE" and tev >= 3:
        return "Strong edge. Books disagree and the fair price likes it."
    if c.get("decision") == "TAKE":
        return "Books are paying more than the blend. Worth a look."
    if c.get("decision") == "LEAN":
        return "Soft edge. Only if you already like it."
    return "Tight. Skip."

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
            if "NBA" in str(sport):
                if "assists" in mkey: prop_type = "Assists"
                elif "points" in mkey and "rebounds" not in mkey and "assists" not in mkey: prop_type = "Points"
                elif "rebounds" in mkey and "points" not in mkey and "assists" not in mkey: prop_type = "Rebounds"
                elif "double_double" in mkey: prop_type = "DoubleDouble"
            else:
                if "anytime_td" in mkey: prop_type = "Anytime TD"
                elif "reception_yds" in mkey or "receiving_yds" in mkey: prop_type = "Rec Yards"
            if not prop_type: continue
            for o in market.get("outcomes") or []:
                oname = str(o.get("name") or "").lower()
                if prop_type in ("DoubleDouble", "Anytime TD"):
                    if oname not in ("yes", "over"): continue
                    player = o.get("description") or o.get("name")
                    line = 0.5 if prop_type == "Anytime TD" else 1.0
                else:
                    if oname != "over": continue
                    player = o.get("description")
                    line = o.get("point")
                    if line is None: continue
                    try: line = float(line)
                    except: continue
                if not player or str(player).lower() in ("yes", "no", "over", "under"): continue
                try: price = int(o.get("price"))
                except: continue
                plays.append({"sport": sport, "event": event, "player": player, "prop": prop_type, "line": line, "price": price, "book": short})
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
        if bk not in sharp:
            sharp[bk] = {"soft_count": 0, "total": 0, "props": {}}
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
        tags = []
        if signals.get("book_beh") == "Solo": tags.append("Solo")
        if signals.get("move") == "Snap": tags.append("Snap")
        if signals.get("vol") == "High": tags.append("Surge")
        # Weak-spot / lag tag
        bk = best["book"]
        if bk in sharp and sharp[bk]["soft_count"] >= 3:
            tags.append(f"{bk} soft")
        if true_ev and true_ev >= 3: tags.append("True EV")
        cards.append({
            **best, "book_prices": book_prices, **signals, "tags": tags,
            "decision": decision,
            "fair_prob": round(fair*100, 1) if fair else None,
            "true_ev": true_ev,
        })
    cards.sort(key=lambda x: (-(x.get("true_ev") or -999), -x.get("spike", 0)))
    return cards

def main():
    st.markdown('<div class="hero"><h1>✨ Girl Magic Odds 2.0</h1><p>Open the site. Edges appear. You lock them. 💅</p></div>', unsafe_allow_html=True)

    api_key = st.secrets.get("ODDS_API_KEY", "") or st.text_input("Odds API Key", type="password")
    if not api_key:
        st.info("Add your Odds API key.")
        return

    with st.sidebar:
        st.markdown("### 💅 Book Weights")
        live_weights = {}
        for short in sorted(set(list(DEFAULT_WEIGHTS.keys()) + list(BOOK_FULL.keys()))):
            default = DEFAULT_WEIGHTS.get(short, 1.0)
            live_weights[short] = st.slider(short, 0.0, 5.0, float(default), 0.1, key=f"w_{short}")

    c1, c2 = st.columns([1, 4])
    with c1:
        sport = st.radio("Lane", ["NBA 🔮", "NFL 🔥"], horizontal=True)
    with c2:
        if st.button("Pull the chaos 💅", type="primary", use_container_width=True):
            sport_key = "basketball_nba" if "NBA" in str(sport) else "americanfootball_nfl"
            markets = "player_assists,player_assists_alternate,player_points,player_points_alternate,player_rebounds,player_rebounds_alternate,player_double_double" if "NBA" in str(sport) else "player_anytime_td,player_reception_yds,player_reception_yds_alternate"
            with st.spinner("Pulling edges…"):
                events = fetch_events(api_key, sport_key)
                now = datetime.utcnow()
                pregame = [ev for ev in events if ev.get("commence_time") and datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00")).replace(tzinfo=None) > now]
                target = pregame if pregame else events
                all_plays = []
                for ev in target[:15]:
                    data = fetch_odds(api_key, sport_key, ev.get("id"), markets)
                    if data: all_plays.extend(parse_plays(data, sport))
                cards = best_cards(all_plays, live_weights)
                update_sharpness(cards)
                st.session_state["cards"] = cards
                st.session_state["fetched"] = datetime.now().strftime("%H:%M")
                ledger = load_ledger()
                existing = {(r.get("player"), r.get("prop"), r.get("line"), r.get("price")) for r in ledger}
                added = 0
                for c in cards:
                    if c.get("decision") == "TAKE":
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
                                "ev_gap": c.get("ev_gap"),
                                "spike": c.get("spike"),
                                "decision": c.get("decision"),
                                "result": None,
                                "clv": None,
                            })
                            existing.add(key)
                            added += 1
                save_ledger(ledger)
                if added: st.toast(f"Auto-tracked {added} TAKE plays")

    cards = st.session_state.get("cards") or []
    if st.session_state.get("fetched"):
        st.caption(f"Board live @ {st.session_state['fetched']} — {len(cards)} props")

    tab_board, tab_tracker = st.tabs(["📊 Board", "🔒 Tracker"])

    with tab_board:
        if not cards:
            st.info("Hit **Pull the chaos**.")
            return
        simple_mode = st.toggle("✨ Simple Mode (recommended)", value=True)
        detailed = st.toggle("🔍 Detailed Mode", value=False)
        if simple_mode:
            filtered = [c for c in cards if c.get("decision") == "TAKE" and (c.get("true_ev") or 0) >= 2]
            st.markdown("**Strongest edges only.**")
        else:
            filtered = cards
        if not filtered:
            st.info("No strong edges right now.")
            return
        st.markdown(f"**{len(filtered)} plays ready.**")

        cols = st.columns(2)
        for i, c in enumerate(filtered[:20]):
            line_txt = f"o{c['line']}" if c["prop"] not in ("DoubleDouble", "Anytime TD") else "Yes"
            boxes_html = "".join(
                f'<div class="bk {"best" if bk == c["book"] else ""}"><span>{bk}</span>{px:+d}</div>'
                for bk, px in sorted(c.get("book_prices", {}).items(), key=lambda x: -x[1])
            )
            tags_html = "".join(f'<span class="tag">{t}</span>' for t in c.get("tags", []))
            card_cls = "card"
            if c.get("decision") == "TAKE": card_cls += " take-card"
            if (c.get("true_ev") or 0) >= 3 and c.get("decision") == "TAKE": card_cls += " true-ev-glow"
            take_tag = '<div class="take-tag">TAKE</div>' if c.get("decision") == "TAKE" else ""
            html = (
                f'<div class="{card_cls}">{take_tag}'
                f'<div class="player">{c["player"]}</div>'
                f'<div class="meta">{c["event"]}</div>'
                f'<div class="prop">{c["prop"]} {line_txt}</div>'
                f'<div class="books">{boxes_html}</div>'
                f'{tags_html}'
                f'<div class="true-ev">True EV {c.get("true_ev", "—")}%</div>'
                f'<div class="why">{plain_reason(c)}</div>'
                f'</div>'
            )
            with cols[i % 2]:
                st.markdown(html, unsafe_allow_html=True)
                if detailed:
                    with st.expander("Why this card"):
                        st.write(f"**True EV:** {c.get('true_ev')}% · Fair {c.get('fair_prob')}%")
                        st.write(f"**EV Gap:** {c.get('ev_gap')}% · Spike {c.get('spike')}")
                        st.write(f"**Vol / Move:** {c.get('vol')} / {c.get('move')}")
                        st.write("**All books:**")
                        st.json(c.get("book_prices", {}))
                        if "soft" in str(c.get("tags")):
                            st.caption("This book has been hanging soft numbers recently.")
                if st.button("Lock 🔒", key=f"lk_{i}_{c['player']}_{c['prop']}_{c['line']}"):
                    ledger = load_ledger()
                    ledger.append({
                        "ts": datetime.now().isoformat(timespec="minutes"),
                        "sport": c["sport"], "player": c["player"], "prop": c["prop"],
                        "line": c["line"], "price": c["price"],
                        "book": BOOK_FULL.get(c["book"], c["book"]),
                        "event": c["event"],
                        "true_ev": c.get("true_ev"),
                        "fair_prob": c.get("fair_prob"),
                        "decision": c.get("decision"),
                        "result": None,
                        "clv": None,
                    })
                    save_ledger(ledger)
                    st.toast("Locked.")

    with tab_tracker:
        ledger = load_ledger()
        sharp = load_sharpness()
        if st.button("Wipe the slate"):
            save_ledger([])
            st.rerun()
        if not ledger:
            st.info("Nothing locked yet.")
        else:
            df = pd.DataFrame(ledger)
            st.markdown(f"**You’ve locked {len(df)} plays.**")
            st.dataframe(df, use_container_width=True, hide_index=True)
            if sharp:
                st.subheader("Book Sharpness (soft counts)")
                st.json(sharp)

try:
    main()
except Exception as e:
    st.error(f"App error: {e}")
    st.exception(e)
