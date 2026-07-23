"""
Petty’s Odds-Tricks System
Strict rules – no ambiguity
"""

import streamlit as st
import pandas as pd
import requests
from collections import defaultdict

st.set_page_config(page_title="Girl Magic Odds ✨", page_icon="💖", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #1a0a1f 0%, #2d1b3d 50%, #1f0f2e 100%); color: #fce7f3; }
    h1, h2, h3 { color: #f9a8d4 !important; }
    .stButton > button {
        background: linear-gradient(90deg, #ec4899, #a855f7) !important;
        color: white !important; border: none !important; border-radius: 12px !important; font-weight: 600 !important;
    }
    .card {
        background: #2a1435; border: 1px solid #f472b6; border-radius: 12px;
        padding: 14px 18px; margin: 10px 0; color: #fdf2f8;
    }
    .dk { border-left: 6px solid #00a3e0; }
    .mgm { border-left: 6px solid #c4a35a; }
    .match { border-left: 6px solid #f472b6; }
    .digit { border-left: 6px solid #a855f7; }
    .fd { border-left: 6px solid #1493ff; }
    .name { border-left: 6px solid #f9a8d4; }
</style>
""", unsafe_allow_html=True)

API_BASE = "https://api.the-odds-api.com/v4"
REGIONS = "us,us2"

def get_api_key():
    key = st.secrets.get("ODDS_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("Odds API Key", type="password")
    return key

def format_odds(p):
    try: return f"{int(p):+d}"
    except: return str(p)

def last_two(p):
    try: return abs(int(p)) % 100
    except: return None

def get_initials(name):
    parts = str(name).strip().split()
    if len(parts) < 2: return None, None
    return parts[0][0].upper(), parts[-1][0].upper()

def fetch_events(api_key):
    try:
        r = requests.get(f"{API_BASE}/sports/baseball_mlb/events", params={"apiKey": api_key}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(str(e))
        return []

def fetch_odds(api_key, event_id):
    params = {
        "apiKey": api_key,
        "regions": REGIONS,
        "markets": "batter_home_runs",
        "oddsFormat": "american"
    }
    try:
        r = requests.get(f"{API_BASE}/sports/baseball_mlb/events/{event_id}/odds", params=params, timeout=20)
        if r.status_code != 200: return None
        return r.json()
    except:
        return None

def flatten(data):
    if not data: return []
    rows = []
    event = f"{data.get('away_team')} @ {data.get('home_team')}"
    for book in data.get("bookmakers", []):
        for market in book.get("markets", []):
            for o in market.get("outcomes", []):
                if o.get("name", "").lower() != "over": continue
                rows.append({
                    "event": event,
                    "book": book.get("key", ""),
                    "player": o.get("description"),
                    "price": o.get("price"),
                    "point": o.get("point"),
                })
    return rows

def run_flags(df):
    if df.empty: return []

    # Only lowest line
    if "point" in df.columns:
        df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()

    results = []

    # ========== 1. DraftKings Ends in 10 ==========
    for _, row in df.iterrows():
        if "draftkings" in str(row["book"]).lower():
            if last_two(row["price"]) == 10:
                results.append({
                    "type": "dk",
                    "label": row["player"],
                    "reason": f"DraftKings ends in 10 → {format_odds(row['price'])}",
                    "event": row["event"],
                    "css": "dk"
                })

    # ========== 2. BetMGM Classic Endings (Pair first, then Group of 3) ==========
    mgm_df = df[df["book"].str.lower().str.contains("betmgm|mgm", na=False)].copy()

    for event, event_group in mgm_df.groupby("event"):
        # Group by ending
        ending_groups = defaultdict(list)
        for _, row in event_group.iterrows():
            d = last_two(row["price"])
            if d in (0, 25, 50, 75):
                ending_groups[d].append({
                    "player": row["player"],
                    "price": row["price"]
                })

        for d, players in ending_groups.items():
            unique = {}
            for p in players:
                unique[p["player"]] = p["price"]
            names = sorted(unique.keys())

            if len(names) == 2:
                # Pair Match (primary)
                results.append({
                    "type": "mgm",
                    "label": " + ".join(names),
                    "reason": f"BetMGM Pair Match ends in {d:02d}",
                    "event": event,
                    "css": "mgm"
                })
            elif len(names) >= 3:
                # Group of Three (fallback)
                results.append({
                    "type": "mgm",
                    "label": " + ".join(names),
                    "reason": f"BetMGM Group of {len(names)} ends in {d:02d}",
                    "event": event,
                    "css": "mgm"
                })

    # ========== 3. Exact Matching Odds (Any Book) ==========
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        if len(group) < 2: continue
        prices = group["price"].dropna().tolist()
        books = group["book"].tolist()
        if len(set(prices)) == 1:
            results.append({
                "type": "match",
                "label": player,
                "reason": f"Exact match {format_odds(prices[0])} → {', '.join(books)}",
                "event": group["event"].iloc[0],
                "css": "match"
            })

    # ========== 4. MGM Exact Match (separate) ==========
    for event, event_group in mgm_df.groupby("event"):
        for price, price_group in event_group.groupby("price"):
            players = sorted(price_group["player"].unique().tolist())
            if len(players) >= 2:
                results.append({
                    "type": "mgm_exact",
                    "label": " + ".join(players),
                    "reason": f"BetMGM Exact Match {format_odds(price)} ({len(players)} players)",
                    "event": event,
                    "css": "mgm"
                })

    # ========== 5. Matching 25/50/75 Across Books ==========
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        if len(group) < 2: continue
        digits = defaultdict(list)
        for _, row in group.iterrows():
            d = last_two(row["price"])
            if d in (25, 50, 75):
                digits[d].append(row["book"])
        for d, bks in digits.items():
            if len(set(bks)) >= 2:
                results.append({
                    "type": "digit",
                    "label": player,
                    "reason": f"Matching {d}s across books → {', '.join(set(bks))}",
                    "event": group["event"].iloc[0],
                    "css": "digit"
                })

    # ========== 6. FanDuel Pattern Endings (≥ +500, ends in 10/30/60/70/90) ==========
    for _, row in df.iterrows():
        if "fanduel" in str(row["book"]).lower():
            price = abs(int(row["price"])) if row["price"] else 0
            last = last_two(row["price"])
            if price >= 500 and last in (10, 30, 60, 70, 90):
                results.append({
                    "type": "fd",
                    "label": row["player"],
                    "reason": f"FanDuel ≥+500 ends in {last:02d} → {format_odds(row['price'])}",
                    "event": row["event"],
                    "css": "fd"
                })

    # ========== 7–10. Name Patterns ==========
    players = list(df["player"].dropna().unique())

    # Same Initials
    init_map = defaultdict(list)
    for p in players:
        f, l = get_initials(p)
        if f and l:
            init_map[f + l].append(p)
    for k, names in init_map.items():
        if len(names) >= 2:
            results.append({
                "type": "same_init",
                "label": " + ".join(sorted(names)),
                "reason": f"Same initials {k}",
                "event": "",
                "css": "name"
            })

    # Cross Initials
    for i, p1 in enumerate(players):
        _, l1 = get_initials(p1)
        if not l1: continue
        for p2 in players[i+1:]:
            f2, _ = get_initials(p2)
            if f2 and l1 == f2:
                results.append({
                    "type": "cross",
                    "label": f"{p1} + {p2}",
                    "reason": f"Cross initial ({l1})",
                    "event": "",
                    "css": "name"
                })

    # Same Last Name
    last_map = defaultdict(list)
    for p in players:
        parts = str(p).split()
        if len(parts) >= 2:
            last_map[parts[-1].lower()].append(p)
    for last, names in last_map.items():
        if len(names) >= 2:
            results.append({
                "type": "last",
                "label": " + ".join(sorted(names)),
                "reason": f"Same last name ({last.title()})",
                "event": "",
                "css": "name"
            })

    # Same First Name
    first_map = defaultdict(list)
    for p in players:
        parts = str(p).split()
        if parts:
            first_map[parts[0].lower()].append(p)
    for first, names in first_map.items():
        if len(names) >= 2:
            results.append({
                "type": "first",
                "label": " + ".join(sorted(names)),
                "reason": f"Same first name ({first.title()})",
                "event": "",
                "css": "name"
            })

    return results

def main():
    st.title("💖 Girl Magic Odds")
    st.caption("Petty’s Odds-Tricks System – Strict Rules")

    api_key = get_api_key()
    if not api_key:
        st.warning("Add your Odds API key in Secrets")
        st.stop()

    if st.button("① Load Games", type="primary"):
        st.session_state["events"] = fetch_events(api_key)

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games** to start")
        st.stop()

    options = {f"{e.get('away_team')} @ {e.get('home_team')}": e["id"] for e in events}
    chosen = st.multiselect("② Select games", list(options.keys()))

    if st.button("③ Fetch Odds", type="primary") and chosen:
        all_rows = []
        progress = st.progress(0)
        for i, label in enumerate(chosen):
            data = fetch_odds(api_key, options[label])
            all_rows.extend(flatten(data))
            progress.progress((i + 1) / len(chosen))

        if all_rows:
            df = pd.DataFrame(all_rows)
            df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()
            st.session_state["odds"] = df.to_dict("records")
            st.success(f"Loaded {len(df)} props (Only 0.5/1 HR)")
        else:
            st.warning("No odds returned for these games")

    odds = st.session_state.get("odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()
    results = run_flags(df) if not df.empty else []

    tabs = st.tabs([
        "🎯 DK Ends in 10",
        "🎰 MGM Classic Endings",
        "🤝 Exact Match (Any Book)",
        "⭐ MGM Exact Match",
        "🔢 Matching 25/50/75",
        "💙 FanDuel Patterns",
        "💅 Same Initials",
        "🔄 Cross Initials",
        "👩‍👧 Same Last Name",
        "👯 Same First Name",
        "📖 Glossary"
    ])

    def show_tab(tab, typ):
        with tab:
            items = [r for r in results if r["type"] == typ]
            if not items:
                st.info("None right now")
                return
            for r in items:
                st.markdown(
                    f'<div class="card {r["css"]}">'
                    f'<b>{r["label"]}</b><br>{r["reason"]}<br>'
                    f'<small>{r.get("event","")}</small></div>',
                    unsafe_allow_html=True
                )

    show_tab(tabs[0], "dk")
    show_tab(tabs[1], "mgm")
    show_tab(tabs[2], "match")
    show_tab(tabs[3], "mgm_exact")
    show_tab(tabs[4], "digit")
    show_tab(tabs[5], "fd")
    show_tab(tabs[6], "same_init")
    show_tab(tabs[7], "cross")
    show_tab(tabs[8], "last")
    show_tab(tabs[9], "first")

    with tabs[10]:
        st.subheader("📖 Petty’s Odds-Tricks Glossary")
        st.markdown("""
**🎯 DraftKings Ends in 10**  
Any DK prop ending in 10. Solo flag only.

**🎰 BetMGM Classic Endings**  
- Pair Match (primary): two players, same team, same ending (00/25/50/75)  
- Group of Three (fallback): three+ players, same team, same ending

**🤝 Exact Matching Odds**  
Exact same price on the same player across any books.

**⭐ MGM Exact Match**  
Exact same price on BetMGM for two or more players in the same game.

**🔢 Matching 25/50/75**  
Same player has 25/50/75 endings across different books.

**💙 FanDuel Patterns**  
FanDuel props ≥ +500 that end in 10, 30, 60, 70, or 90.

**💅 Same Initials**  
Same first + last initial.

**🔄 Cross Initials**  
One player’s last initial = another player’s first initial.

**👩‍👧 Same Last Name**  
Exact same last name.

**👯 Same First Name**  
Exact same first name.
        """)

    st.caption("💖 Girl Magic • Petty’s Odds-Tricks System")

if __name__ == "__main__":
    main()
