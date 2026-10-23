# -*- coding: utf-8 -*-
"""
Girl Magic Odds 2.0
Lean odds model focused on plus-money props.

NBA: Assists o2.5–o6.5 (+750+), Points 8–15, Rebounds 5–8, Double-Doubles
NFL: Anytime TD (+300+), Receiving Yards 1–15 (+300+)

Tracks the books you use: FanDuel, DraftKings, BetMGM, Bet365, Caesars,
Fanatics, theScore (espnbet), Hard Rock.

Core loop: Fetch → filter → cards → lock → grade → see which odds and books cash.
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
.stApp{background:#0b0e14;color:#e6edf3;font-family:'Inter',sans-serif}
.hero{background:linear-gradient(135deg,#4c1d95,#7c3aed);border-radius:16px;padding:18px 22px;margin-bottom:16px}
.hero h1{margin:0;font-size:1.9rem;font-weight:800;color:#fff}
.hero p{margin:4px 0 0;color:#e9d5ff;font-size:.9rem}
.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:14px 16px;margin-bottom:12px}
.card:hover{border-color:#a78bfa}
.player{font-size:1.15rem;font-weight:800;color:#fff;margin:0}
.meta{color:#8b949e;font-size:.78rem;margin:2px 0 8px}
.line{font-size:1.05rem;font-weight:700;color:#c4b5fd}
.odds{font-size:1.45rem;font-weight:800;color:#a78bfa}
.book{font-size:.8rem;color:#f0abfc}
.ev{display:inline-block;background:#1e1b4b;color:#c4b5fd;border:1px solid #7c3aed;border-radius:999px;padding:2px 10px;font-size:.72rem;font-weight:700;margin-left:8px}
.tag{display:inline-block;background:#21262d;color:#c9d1d9;border-radius:999px;padding:2px 8px;font-size:.68rem;margin-right:4px}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
LEDGER = Path("odds_ledger.json")

# Books you actually use (Odds API keys)
MY_BOOKS = {
    "fanduel": "FanDuel",
    "draftkings": "DraftKings",
    "betmgm": "BetMGM",
    "bet365": "Bet365",
    "williamhill_us": "Caesars",
    "fanatics": "Fanatics",
    "espnbet": "theScore",
    "hardrockbet": "Hard Rock",
    "hardrockbet_az": "Hard Rock AZ",
    "hardrockbet_oh": "Hard Rock OH",
    "hardrockbet_fl": "Hard Rock FL",
    "caesars": "Caesars",
}

NBA_SKIP = {
    "nikola jokic", "trae young", "tyrese haliburton", "luka doncic",
    "james harden", "jalen brunson", "damian lillard", "stephen curry",
    "lamelo ball", "cade cunningham", "scoot henderson", "chris paul",
}

def normalize_book(key):
    k = str(key or "").lower()
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
        try:
            return json.loads(LEDGER.read_text())
        except Exception:
            return []
    return []

def save_ledger(rows):
    LEDGER.write_text(json.dumps(rows, indent=2))

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
        bk_raw = book.get("key") or ""
        bk = normalize_book(bk_raw)
        if bk not in MY_BOOKS and bk_raw not in MY_BOOKS:
            continue
        display = MY_BOOKS.get(bk) or MY_BOOKS.get(bk_raw) or bk
        for market in book.get("markets") or []:
            mkey = (market.get("key") or "").lower()
            prop_type = None
            if sport == "NBA":
                if "assists" in mkey: prop_type = "Assists"
                elif "points" in mkey and "rebounds" not in mkey and "assists" not in mkey: prop_type = "Points"
                elif "rebounds" in mkey and "points" not in mkey and "assists" not in mkey: prop_type = "Rebounds"
                elif "double_double" in mkey: prop_type = "DoubleDouble"
            else:  # NFL
                if "anytime_td" in mkey or mkey == "player_anytime_td": prop_type = "Anytime TD"
                elif "reception_yds" in mkey or "receiving_yds" in mkey: prop_type = "Rec Yards"
            if not prop_type:
                continue
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
                if sport == "NBA" and prop_type == "Assists" and any(x in str(player).lower() for x in NBA_SKIP):
                    continue
                try: price = int(o.get("price"))
                except: continue
                # Plus-money floors
                if sport == "NBA":
                    if prop_type == "Assists" and not (2.5 <= line <= 6.5): continue
                    if prop_type == "Points" and not (8.0 <= line <= 15.0): continue
                    if prop_type == "Rebounds" and not (5.0 <= line <= 8.0): continue
                    if prop_type != "DoubleDouble" and price < 750: continue
                    if prop_type == "DoubleDouble" and price < 400: continue
                else:
                    if prop_type == "Anytime TD" and price < 300: continue
                    if prop_type == "Rec Yards" and not (1.0 <= line <= 15.0): continue
                    if prop_type == "Rec Yards" and price < 300: continue
                plays.append({
                    "sport": sport, "event": event, "player": player,
                    "prop": prop_type, "line": line, "price": price, "book": display,
                })
    return plays

def best_cards(plays):
    by = defaultdict(list)
    for p in plays:
        key = (p["sport"], p["player"], p["prop"], p["line"], p["event"])
        by[key].append(p)
    cards = []
    for key, group in by.items():
        best = max(group, key=lambda x: x["price"])
        prices = [g["price"] for g in group]
        med = sorted(prices)[len(prices)//2] if prices else best["price"]
        cards.append({**best, "books": len(group), "gap": best["price"] - med, "median": med})
    cards.sort(key=lambda x: (-x["price"], -x["gap"]))
    return cards

def main():
    st.markdown('<div class="hero"><h1>✨ Girl Magic Odds 2.0</h1><p>Plus-money props only. NBA assists first. NFL TDs + low rec yards. Track what actually cashes.</p></div>', unsafe_allow_html=True)

    api_key = st.secrets.get("ODDS_API_KEY", "") or st.text_input("Odds API Key", type="password")
    if not api_key:
        st.info("Add ODDS_API_KEY to secrets or paste above.")
        return

    sport = st.radio("Lane", ["NBA", "NFL"], horizontal=True, index=0)
    sport_key = "basketball_nba" if sport == "NBA" else "americanfootball_nfl"
    markets = (
        "player_assists,player_assists_alternate,player_points,player_points_alternate,player_rebounds,player_rebounds_alternate,player_double_double"
        if sport == "NBA"
        else "player_anytime_td,player_reception_yds,player_reception_yds_alternate"
    )

    if st.button("Fetch Slate", type="primary"):
        with st.spinner(f"Loading {sport}..."):
            events = fetch_events(api_key, sport_key)
            all_plays = []
            for ev in events[:15]:
                data = fetch_odds(api_key, sport_key, ev.get("id"), markets)
                if data:
                    all_plays.extend(parse_plays(data, sport))
            st.session_state["cards"] = best_cards(all_plays)
            st.session_state["fetched"] = datetime.now().strftime("%H:%M")
            st.session_state["sport"] = sport

    cards = st.session_state.get("cards") or []
    if st.session_state.get("fetched"):
        st.caption(f"Last fetch {st.session_state['fetched']} · {len(cards)} plays · {sport}")

    tab1, tab2 = st.tabs(["Plays", "Ledger"])

    with tab1:
        if not cards:
            st.info("Hit Fetch Slate.")
            return
        c1, c2 = st.columns(2)
        with c1:
            min_odds = st.slider("Min odds", 300 if sport == "NFL" else 750, 2500, 750 if sport == "NBA" else 300, 50)
        with c2:
            min_gap = st.slider("Min gap vs median", 0, 300, 0, 10)
        filtered = [c for c in cards if c["price"] >= min_odds and c["gap"] >= min_gap]
        st.markdown(f"**{len(filtered)}** plays")
        cols = st.columns(2)
        for i, c in enumerate(filtered[:50]):
            line_txt = f"o{c['line']}" if c["prop"] not in ("DoubleDouble", "Anytime TD") else ("Yes" if c["prop"] == "DoubleDouble" else "Anytime")
            ev_html = f'<span class="ev">+{c["gap"]} vs med</span>' if c["gap"] > 0 else ""
            with cols[i % 2]:
                st.markdown(
                    f'''<div class="card">
                        <div class="player">{c["player"]}</div>
                        <div class="meta">{c["event"]} · {c["books"]} books</div>
                        <div class="line">{c["prop"]} {line_txt}</div>
                        <div><span class="odds">{c["price"]:+d}</span> <span class="book">{c["book"]}</span>{ev_html}</div>
                    </div>''',
                    unsafe_allow_html=True,
                )
                if st.button("Lock", key=f"lock_{i}_{c['player']}_{c['prop']}_{c['line']}"):
                    ledger = load_ledger()
                    ledger.append({
                        "ts": datetime.now().isoformat(),
                        "sport": c["sport"], "player": c["player"], "prop": c["prop"],
                        "line": c["line"], "price": c["price"], "book": c["book"],
                        "event": c["event"], "result": None,
                    })
                    save_ledger(ledger)
                    st.success("Locked")

    with tab2:
        ledger = load_ledger()
        if not ledger:
            st.info("No locks yet. Lock plays from the Plays tab.")
            return
        df = pd.DataFrame(ledger)
        st.dataframe(df[["ts", "sport", "player", "prop", "line", "price", "book", "result"]], use_container_width=True)
        st.caption("Grade results later — the Tracker will show which odds buckets and books cash.")

if __name__ == "__main__":
    main()
