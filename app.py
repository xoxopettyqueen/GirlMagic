# -*- coding: utf-8 -*-
"""
Girl Magic Odds 2.0
BeeBettor-style board: every book side by side on the props you care about.
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
.stApp{background:#07070a;color:#fff;font-family:'Inter',sans-serif}
.hero{background:linear-gradient(120deg,#4c1d95,#7c3aed 50%,#c084fc);border-radius:22px;padding:20px 24px;margin-bottom:16px;box-shadow:0 12px 40px rgba(124,58,237,.3)}
.hero h1{margin:0;font-size:1.85rem;font-weight:900}
.hero p{margin:5px 0 0;opacity:.9;font-size:.9rem}
.card{background:#121214;border:1px solid #2a2a30;border-radius:16px;padding:14px 16px;margin-bottom:12px}
.card:hover{border-color:#a78bfa}
.player{font-size:1.15rem;font-weight:800;margin:0}
.meta{color:#9ca3af;font-size:.72rem;margin:2px 0 6px}
.prop{font-size:.95rem;font-weight:700;color:#d8b4fe}
.books-row{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.book-pill{background:#1e1e22;border:1px solid #333;border-radius:10px;padding:6px 10px;font-size:.75rem;font-weight:600;min-width:70px;text-align:center}
.book-pill.best{background:#14532d;border-color:#22c55e;color:#fff}
.book-pill .bk{font-size:.65rem;color:#a1a1aa;display:block}
.book-pill.best .bk{color:#bbf7d0}
.edge{display:inline-block;background:#16a34a;color:#fff;border-radius:999px;padding:3px 10px;font-size:.72rem;font-weight:800;margin-left:8px}
.tag{display:inline-block;background:#27272a;border-radius:999px;padding:2px 8px;font-size:.65rem;font-weight:700;margin:2px 3px 0 0}
.tag-hot{background:#15803d;color:#fff}
.why{font-size:.72rem;color:#a1a1aa;margin-top:6px;font-style:italic}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
LEDGER = Path("odds_ledger.json")

MY_BOOKS = {
    "fanduel": "FD", "draftkings": "DK", "betmgm": "MGM",
    "bet365": "365", "williamhill_us": "CZR", "fanatics": "FAN",
    "espnbet": "SCR", "hardrockbet": "HR",
    "hardrockbet_az": "HR", "hardrockbet_oh": "HR", "hardrockbet_fl": "HR",
}
BOOK_FULL = {
    "FD": "FanDuel", "DK": "DraftKings", "MGM": "BetMGM",
    "365": "Bet365", "CZR": "Caesars", "FAN": "Fanatics",
    "SCR": "theScore", "HR": "Hard Rock",
}

HOT_ENDS = {5, 10, 25, 30, 35, 40, 55, 65, 75, 80, 85, 90}
DEAD_ENDS = {0, 50}
NBA_SKIP = {
    "nikola jokic", "trae young", "tyrese haliburton", "luka doncic",
    "james harden", "jalen brunson", "damian lillard", "stephen curry",
    "lamelo ball", "cade cunningham", "scoot henderson", "chris paul",
}

def last_two(p):
    try: return abs(int(p)) % 100
    except: return None

def implied(price):
    try:
        p = int(price)
        return 100 / (p + 100) if p > 0 else abs(p) / (abs(p) + 100)
    except: return None

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
        bk = normalize_book(book.get("key"))
        if bk not in MY_BOOKS: continue
        short = MY_BOOKS[bk]
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
                    "prop": prop_type, "line": line, "price": price, "book": short,
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
        book_prices = {g["book"]: g["price"] for g in group}
        prices = sorted(book_prices.values())
        med = prices[len(prices)//2]
        others = [v for k, v in book_prices.items() if k != best["book"]]
        fair = sorted(others)[len(others)//2] if others else med
        gap = best["price"] - fair
        best_imp = implied(best["price"]) or 0.5
        fair_imp = implied(fair) or 0.5
        edge = round((fair_imp - best_imp) * 100, 1) if best_imp and fair_imp else 0
        end = last_two(best["price"])
        tags = []
        if end in HOT_ENDS: tags.append(("hot", f"Hot {end:02d}"))
        if end in DEAD_ENDS: tags.append(("dead", f"Dead {end:02d}"))
        why = f"Best price is {gap:+d} longer than the field median on this exact prop."
        if edge >= 2: why = f"+{edge}% edge — one of your books is meaningfully longer than the rest."
        cards.append({
            **best,
            "books": len(book_prices),
            "book_prices": book_prices,
            "gap": int(gap),
            "fair": int(fair),
            "edge": edge,
            "end": end,
            "tags": tags,
            "why": why,
        })
    cards.sort(key=lambda x: (-x["edge"], -x["gap"], -x["price"]))
    return cards

def odds_bucket(price):
    if price < 500: return "+300–499"
    if price < 750: return "+500–749"
    if price < 1000: return "+750–999"
    if price < 1500: return "+1000–1499"
    if price < 2500: return "+1500–2499"
    return "+2500+"

def main():
    st.markdown('<div class="hero"><h1>✨ Girl Magic Odds 2.0</h1><p>Side-by-side books on the plus-money props. Biggest gaps first.</p></div>', unsafe_allow_html=True)

    api_key = st.secrets.get("ODDS_API_KEY", "") or st.text_input("Odds API Key", type="password")
    if not api_key:
        st.info("Add ODDS_API_KEY to secrets or paste above.")
        return

    c1, c2 = st.columns([1, 4])
    with c1:
        sport = st.radio("Lane", ["NBA", "NFL"], horizontal=True)
    with c2:
        if st.button("Fetch Board", type="primary", use_container_width=True):
            sport_key = "basketball_nba" if sport == "NBA" else "americanfootball_nfl"
            markets = (
                "player_assists,player_assists_alternate,player_points,player_points_alternate,player_rebounds,player_rebounds_alternate,player_double_double"
                if sport == "NBA"
                else "player_anytime_td,player_reception_yds,player_reception_yds_alternate"
            )
            with st.spinner(f"Scanning {sport}..."):
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
        st.caption(f"Fetched {st.session_state['fetched']} · {len(cards)} props · {st.session_state.get('sport','')}")

    tab_board, tab_tracker, tab_how = st.tabs(["Board", "Tracker", "How It Works"])

    with tab_board:
        if not cards:
            st.info("Hit Fetch Board.")
            return
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            props = sorted({c["prop"] for c in cards})
            prop_f = st.multiselect("Prop", props, default=props)
        with f2:
            min_odds = st.slider("Min odds", 300, 2000, 750 if sport == "NBA" else 300, 50)
        with f3:
            max_odds = st.slider("Max odds", 1000, 4000, 2500, 100)
        with f4:
            min_edge = st.slider("Min edge %", 0.0, 8.0, 0.0, 0.5)
            only_hot = st.checkbox("Hot endings only")

        filtered = [
            c for c in cards
            if c.get("prop") in prop_f
            and min_odds <= int(c.get("price", 0)) <= max_odds
            and float(c.get("edge", 0)) >= min_edge
            and (not only_hot or c.get("end") in HOT_ENDS)
        ]
        filtered.sort(key=lambda x: (-float(x.get("edge", 0)), -int(x.get("gap", 0))))
        st.markdown(f"**{len(filtered)}** props")

        if not filtered:
            st.info("No props at these filters.")
            return

        cols = st.columns(2)
        for i, c in enumerate(filtered[:24]):
            line_txt = f"o{c['line']}" if c["prop"] not in ("DoubleDouble", "Anytime TD") else "Yes"
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"**{c['player']}**")
                    st.caption(c["event"])
                    edge_txt = f" · +{c.get('edge',0)}% edge" if c.get("edge", 0) >= 1 else ""
                    st.markdown(f"**{c['prop']} {line_txt}**{edge_txt}")
                    # Book prices as a simple row
                    bp = c.get("book_prices", {})
                    if bp:
                        book_line = " · ".join(f"{bk} {px:+d}" for bk, px in sorted(bp.items(), key=lambda x: -x[1]))
                        st.markdown(f"`{book_line}`")
                    if c.get("tags"):
                        st.caption(" ".join(t[1] for t in c["tags"]))
                    st.caption(c.get("why", ""))
                if st.button("Lock best", key=f"lk_{i}_{c['player']}_{c['prop']}_{c['line']}_{c['price']}"):
                    ledger = load_ledger()
                    ledger.append({
                        "ts": datetime.now().isoformat(timespec="minutes"),
                        "sport": c["sport"], "player": c["player"], "prop": c["prop"],
                        "line": c["line"], "price": c["price"], "book": BOOK_FULL.get(c["book"], c["book"]),
                        "event": c["event"], "end": c.get("end"),
                        "bucket": odds_bucket(c["price"]), "edge": c.get("edge"),
                        "result": None,
                    })
                    save_ledger(ledger)
                    st.toast("Locked")

    with tab_tracker:
        ledger = load_ledger()
        if not ledger:
            st.info("Lock props from the board. Tracker shows what cashes by odds, ending, and book.")
            return
        df = pd.DataFrame(ledger)
        st.subheader("Locked")
        st.dataframe(df, use_container_width=True, hide_index=True)
        graded = df[df["result"].notna()]
        if graded.empty:
            st.caption("No graded results yet.")
            return
        for title, col in [("By odds bucket", "bucket"), ("By ending", "end"), ("By book", "book")]:
            st.subheader(title)
            g = graded.groupby(col).agg(n=("result","count"), hits=("result", lambda s: (s=="hit").sum()))
            g["hit%"] = (g["hits"]/g["n"]*100).round(1)
            st.dataframe(g.sort_values("hit%", ascending=False), use_container_width=True)

    with tab_how:
        st.markdown("""
**Board** shows every book that priced the prop. Green pill is the longest price.  

**Edge %** is how much better that longest price is than the field median (implied probability).  

**Hot ending** tags the last two digits that cashed better in the graded data.  

**Why this prop** explains the gap in one line so you know why it surfaced.  

Default filter includes Assists, Points, Rebounds, and Double-Doubles. Lock the ones you like. Tracker breaks out what cashes by odds bucket, ending, and book.
        """)

if __name__ == "__main__":
    main()
