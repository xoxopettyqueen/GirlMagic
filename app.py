# -*- coding: utf-8 -*-
"""
Girl Magic Odds 2.0 — usable version
Plus-money props with real cards, filters, and a Tracker that shows
which odds buckets and books are cashing once you grade.
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.stApp{background:#09090b;color:#fafafa;font-family:'Inter',sans-serif}
.hero{background:linear-gradient(135deg,#6d28d9 0%,#7c3aed 50%,#a78bfa 100%);border-radius:20px;padding:20px 24px;margin-bottom:20px;box-shadow:0 8px 32px rgba(109,40,217,.25)}
.hero h1{margin:0;font-size:1.85rem;font-weight:800;letter-spacing:-.02em}
.hero p{margin:6px 0 0;opacity:.9;font-size:.92rem}
.card{background:#18181b;border:1px solid #27272a;border-radius:16px;padding:16px 18px;margin-bottom:14px;transition:border-color .15s}
.card:hover{border-color:#a78bfa}
.player{font-size:1.2rem;font-weight:800;margin:0 0 2px}
.meta{color:#a1a1aa;font-size:.78rem;margin-bottom:10px}
.prop{font-size:1rem;font-weight:700;color:#c4b5fd}
.odds{font-size:1.6rem;font-weight:800;color:#fafafa;letter-spacing:-.03em}
.book{font-size:.82rem;color:#d4d4d8;margin-left:6px}
.badge{display:inline-block;background:#27272a;color:#e4e4e7;border-radius:999px;padding:3px 10px;font-size:.7rem;font-weight:600;margin-right:6px}
.ev-pos{display:inline-block;background:#14532d;color:#86efac;border-radius:999px;padding:3px 10px;font-size:.72rem;font-weight:700}
.ev-neg{display:inline-block;background:#3f1d1d;color:#fca5a5;border-radius:999px;padding:3px 10px;font-size:.72rem;font-weight:700}
.stat-row{display:flex;gap:16px;margin-top:10px;font-size:.75rem;color:#a1a1aa}
.stat-row b{color:#fafafa}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
LEDGER = Path("odds_ledger.json")

MY_BOOKS = {
    "fanduel": "FanDuel", "draftkings": "DraftKings", "betmgm": "BetMGM",
    "bet365": "Bet365", "williamhill_us": "Caesars", "fanatics": "Fanatics",
    "espnbet": "theScore", "hardrockbet": "Hard Rock",
    "hardrockbet_az": "Hard Rock", "hardrockbet_oh": "Hard Rock", "hardrockbet_fl": "Hard Rock",
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
        try: return json.loads(LEDGER.read_text())
        except: return []
    return []

def save_ledger(rows):
    LEDGER.write_text(json.dumps(rows, indent=2))

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
        r = requests.get(
            f"{ODDS_API_BASE}/sports/{sport_key}/events/{event_id}/odds",
            params={"apiKey": api_key, "regions": "us,us2,uk", "markets": markets, "oddsFormat": "american"},
            timeout=20,
        )
        if r.status_code == 200: return r.json()
    except: pass
    return None

def parse_plays(data, sport):
    if not data: return []
    event = f"{data.get('away_team')} @ {data.get('home_team')}"
    plays = []
    for book in data.get("bookmakers") or []:
        bk_raw = book.get("key") or ""
        bk = normalize_book(bk_raw)
        if bk not in MY_BOOKS: continue
        display = MY_BOOKS.get(bk, bk)
        for market in book.get("markets") or []:
            mkey = (market.get("key") or "").lower()
            prop_type = None
            if sport == "NBA":
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
                if sport == "NBA" and prop_type == "Assists" and any(x in str(player).lower() for x in NBA_SKIP):
                    continue
                try: price = int(o.get("price"))
                except: continue
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
        key = (p["sport"], p["player"], p["prop"], round(p["line"], 1), p["event"])
        by[key].append(p)
    cards = []
    for key, group in by.items():
        best = max(group, key=lambda x: x["price"])
        prices = sorted(g["price"] for g in group)
        med = prices[len(prices)//2]
        # Simple +EV proxy: best price vs the median of the other books
        others = [g["price"] for g in group if g["book"] != best["book"]]
        fair = sorted(others)[len(others)//2] if others else med
        gap = best["price"] - fair
        # Implied edge rough: higher price = lower implied prob
        cards.append({
            **best,
            "books": len(group),
            "gap": int(gap),
            "fair": int(fair),
            "all_prices": prices,
        })
    cards.sort(key=lambda x: (-x["gap"], -x["price"]))
    return cards

def odds_bucket(price):
    if price < 500: return "+300–499"
    if price < 750: return "+500–749"
    if price < 1000: return "+750–999"
    if price < 1500: return "+1000–1499"
    if price < 2500: return "+1500–2499"
    return "+2500+"

def main():
    st.markdown('<div class="hero"><h1>✨ Girl Magic Odds 2.0</h1><p>Plus-money props. Best price vs the field. Lock it, grade it, see what cashes.</p></div>', unsafe_allow_html=True)

    api_key = st.secrets.get("ODDS_API_KEY", "") or st.text_input("Odds API Key", type="password")
    if not api_key:
        st.info("Add ODDS_API_KEY to secrets or paste above.")
        return

    col_sport, col_fetch = st.columns([1, 3])
    with col_sport:
        sport = st.radio("Lane", ["NBA", "NFL"], horizontal=True, index=0)
    with col_fetch:
        if st.button("Fetch Slate", type="primary", use_container_width=True):
            sport_key = "basketball_nba" if sport == "NBA" else "americanfootball_nfl"
            markets = (
                "player_assists,player_assists_alternate,player_points,player_points_alternate,player_rebounds,player_rebounds_alternate,player_double_double"
                if sport == "NBA"
                else "player_anytime_td,player_reception_yds,player_reception_yds_alternate"
            )
            with st.spinner(f"Loading {sport}..."):
                events = fetch_events(api_key, sport_key)
                all_plays = []
                for ev in events[:12]:
                    data = fetch_odds(api_key, sport_key, ev.get("id"), markets)
                    if data: all_plays.extend(parse_plays(data, sport))
                st.session_state["cards"] = best_cards(all_plays)
                st.session_state["fetched"] = datetime.now().strftime("%H:%M")
                st.session_state["sport"] = sport

    cards = st.session_state.get("cards") or []
    if st.session_state.get("fetched"):
        st.caption(f"Fetched {st.session_state['fetched']} · {len(cards)} plays · {st.session_state.get('sport','')}")

    tab_plays, tab_tracker = st.tabs(["Plays", "Tracker"])

    with tab_plays:
        if not cards:
            st.info("Hit Fetch Slate.")
            return

        f1, f2, f3, f4 = st.columns(4)
        with f1:
            prop_opts = sorted({c["prop"] for c in cards})
            prop_f = st.multiselect("Prop", prop_opts, default=prop_opts[:1] if prop_opts else [])
        with f2:
            min_odds = st.slider("Min odds", 300, 2000, 750 if sport == "NBA" else 300, 50)
        with f3:
            max_odds = st.slider("Max odds", 1000, 5000, 2000, 100)
        with f4:
            min_gap = st.slider("Min gap", -100, 400, 0, 25)
            sort_by = st.selectbox("Sort", ["Biggest gap", "Highest odds", "Most books"])

        filtered = [
            c for c in cards
            if c.get("prop") in prop_f
            and min_odds <= int(c.get("price", 0)) <= max_odds
            and int(c.get("gap", 0)) >= min_gap
        ]
        if sort_by == "Highest odds":
            filtered.sort(key=lambda x: -x["price"])
        elif sort_by == "Most books":
            filtered.sort(key=lambda x: -x["books"])
        else:
            filtered.sort(key=lambda x: (-x["gap"], -x["price"]))

        st.markdown(f"**{len(filtered)}** plays")

        cols = st.columns(2)
        for i, c in enumerate(filtered[:40]):
            line_txt = f"o{c['line']}" if c["prop"] not in ("DoubleDouble", "Anytime TD") else "Yes"
            gap = int(c.get("gap", 0))
            gap_cls = "ev-pos" if gap >= 50 else ("ev-neg" if gap < 0 else "badge")
            gap_txt = f"+{gap}" if gap >= 0 else str(gap)
            with cols[i % 2]:
                st.markdown(
                    f'''<div class="card">
                        <div class="player">{c["player"]}</div>
                        <div class="meta">{c["event"]}</div>
                        <div class="prop">{c["prop"]} {line_txt}</div>
                        <div style="margin:8px 0">
                            <span class="odds">{c["price"]:+d}</span>
                            <span class="book">{c["book"]}</span>
                            <span class="{gap_cls}">{gap_txt} vs field</span>
                        </div>
                        <div class="stat-row">
                            <span><b>{c.get("books", 1)}</b> books</span>
                            <span>field med <b>{int(c.get("fair", c.get("price", 0))):+d}</b></span>
                        </div>
                    </div>''',
                    unsafe_allow_html=True,
                )
                if st.button("Lock", key=f"lk_{i}_{c['player']}_{c['prop']}_{c['line']}_{c['price']}"):
                    ledger = load_ledger()
                    ledger.append({
                        "ts": datetime.now().isoformat(timespec="minutes"),
                        "sport": c["sport"], "player": c["player"], "prop": c["prop"],
                        "line": c["line"], "price": c["price"], "book": c["book"],
                        "event": c["event"], "result": None, "bucket": odds_bucket(c["price"]),
                    })
                    save_ledger(ledger)
                    st.toast("Locked")

    with tab_tracker:
        ledger = load_ledger()
        if not ledger:
            st.info("Lock some plays first. Once you grade them (hit/miss), this shows which odds buckets and books cash.")
            return
        df = pd.DataFrame(ledger)
        st.subheader("Locked plays")
        st.dataframe(df, use_container_width=True, hide_index=True)

        graded = df[df["result"].notna()]
        if graded.empty:
            st.caption("No graded results yet. After games, set result to hit or miss in the JSON (or we can add buttons next).")
            return

        st.subheader("By odds bucket")
        bucket = graded.groupby("bucket").agg(n=("result", "count"), hits=("result", lambda s: (s == "hit").sum()))
        bucket["hit%"] = (bucket["hits"] / bucket["n"] * 100).round(1)
        st.dataframe(bucket.sort_values("n", ascending=False), use_container_width=True)

        st.subheader("By book")
        book = graded.groupby("book").agg(n=("result", "count"), hits=("result", lambda s: (s == "hit").sum()))
        book["hit%"] = (book["hits"] / book["n"] * 100).round(1)
        st.dataframe(book.sort_values("hit%", ascending=False), use_container_width=True)

if __name__ == "__main__":
    main()
