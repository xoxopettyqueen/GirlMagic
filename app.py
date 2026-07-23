"""
Girl Magic Odds ✨
For the girls only • Our tricks
+ Historical price tracking (session-based)
"""

import streamlit as st
import pandas as pd
import requests
from collections import defaultdict
import statistics
from datetime import datetime

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
    .signal { border-left: 6px solid #34d399; }
    .hist { border-left: 6px solid #fbbf24; }
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

def run_flags(df, previous_df=None):
    if df.empty: return []

    if "point" in df.columns:
        df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()

    results = []
    flagged_players = set()

    # 1. DraftKings Ends in 10
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
                flagged_players.add(row["player"])

    # 2. BetMGM Classic Endings
    mgm_df = df[df["book"].str.lower().str.contains("betmgm|mgm", na=False)].copy()
    for event, event_group in mgm_df.groupby("event"):
        ending_groups = defaultdict(list)
        for _, row in event_group.iterrows():
            d = last_two(row["price"])
            if d in (0, 25, 50, 75):
                ending_groups[d].append(row["player"])
        for d, players in ending_groups.items():
            names = sorted(set(players))
            if len(names) >= 2:
                results.append({
                    "type": "mgm",
                    "label": " + ".join(names),
                    "reason": f"BetMGM {'Pair' if len(names)==2 else 'Group of '+str(len(names))} ends in {d:02d}",
                    "event": event,
                    "css": "mgm"
                })
                flagged_players.update(names)

    # 3. Exact Matching Odds
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
            flagged_players.add(player)

    # 4. MGM Exact Match
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
                flagged_players.update(players)

    # 5. Matching 25/50/75 Across Books
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
                flagged_players.add(player)

    # 6. FanDuel Patterns
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
                flagged_players.add(row["player"])

    # 7. Line Signals (Stuck + Wide Disagreement)
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        prices = group["price"].dropna().tolist()
        books = group["book"].tolist()
        if len(prices) < 3: continue

        if len(set(prices)) == 1 and len(prices) >= 3:
            results.append({
                "type": "signal",
                "label": player,
                "reason": f"Stuck Number {format_odds(prices[0])} on {len(prices)} books",
                "event": group["event"].iloc[0],
                "css": "signal"
            })
            flagged_players.add(player)

        try:
            med = statistics.median(prices)
            for i, pr in enumerate(prices):
                if abs(pr - med) >= 150:
                    results.append({
                        "type": "signal",
                        "label": player,
                        "reason": f"Wide Disagreement on {books[i]} ({format_odds(pr)} vs median {format_odds(med)})",
                        "event": group["event"].iloc[0],
                        "css": "signal"
                    })
                    flagged_players.add(player)
        except:
            pass

    # ========== 8. HISTORICAL PRICE TRACKING ==========
    if previous_df is not None and not previous_df.empty:
        # Create lookup of previous prices
        prev_lookup = {}
        for _, row in previous_df.iterrows():
            key = (row["player"], row["book"])
            prev_lookup[key] = row["price"]

        for _, row in df.iterrows():
            key = (row["player"], row["book"])
            if key in prev_lookup:
                old = prev_lookup[key]
                new = row["price"]
                if old is not None and new is not None and old != new:
                    direction = "↑ got longer" if new > old else "↓ got shorter"
                    results.append({
                        "type": "hist",
                        "label": row["player"],
                        "reason": f"{row['book']}: {format_odds(old)} → {format_odds(new)} {direction}",
                        "event": row["event"],
                        "css": "hist"
                    })
                    flagged_players.add(row["player"])

    # Name patterns (only if both flagged)
    player_events = defaultdict(set)
    for _, row in df.iterrows():
        player_events[row["player"]].add(row["event"])

    players = list(df["player"].dropna().unique())

    def is_different_teams(p1, p2):
        return len(player_events[p1] & player_events[p2]) == 0

    def both_flagged(p1, p2):
        return p1 in flagged_players and p2 in flagged_players

    # Same Initials
    init_map = defaultdict(list)
    for p in players:
        f, l = get_initials(p)
        if f and l:
            init_map[f + l].append(p)
    for k, names in init_map.items():
        for i, p1 in enumerate(names):
            for p2 in names[i+1:]:
                if both_flagged(p1, p2):
                    same = not is_different_teams(p1, p2)
                    tag = " (same team)" if same else " (different teams)"
                    results.append({
                        "type": "same_init",
                        "label": f"{p1} + {p2}",
                        "reason": f"Same initials {k}{tag}",
                        "event": "",
                        "css": "name"
                    })

    # Cross Initials
    for i, p1 in enumerate(players):
        _, l1 = get_initials(p1)
        if not l1: continue
        for p2 in players[i+1:]:
            f2, _ = get_initials(p2)
            if f2 and l1 == f2 and both_flagged(p1, p2):
                same = not is_different_teams(p1, p2)
                tag = " (same team)" if same else " (different teams)"
                results.append({
                    "type": "cross",
                    "label": f"{p1} + {p2}",
                    "reason": f"Cross initial ({l1}){tag}",
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
        for i, p1 in enumerate(names):
            for p2 in names[i+1:]:
                if both_flagged(p1, p2):
                    same = not is_different_teams(p1, p2)
                    tag = " (same team)" if same else " (different teams)"
                    results.append({
                        "type": "last",
                        "label": f"{p1} + {p2}",
                        "reason": f"Same last name ({last.title()}){tag}",
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
        for i, p1 in enumerate(names):
            for p2 in names[i+1:]:
                if both_flagged(p1, p2):
                    same = not is_different_teams(p1, p2)
                    tag = " (same team)" if same else " (different teams)"
                    results.append({
                        "type": "first",
                        "label": f"{p1} + {p2}",
                        "reason": f"Same first name ({first.title()}){tag}",
                        "event": "",
                        "css": "name"
                    })

    return results

def main():
    st.title("💖 Girl Magic Odds")
    st.caption("For the girls only • Our tricks")

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

            # Save previous for historical comparison
            if "odds" in st.session_state:
                st.session_state["previous_odds"] = st.session_state["odds"]
            st.session_state["odds"] = df.to_dict("records")
            st.session_state["last_fetch_time"] = datetime.now().strftime("%I:%M %p")

            st.success(f"Loaded {len(df)} props (Only 0.5/1 HR) • {st.session_state['last_fetch_time']}")
        else:
            st.warning("No odds returned for these games")

    odds = st.session_state.get("odds", [])
    previous = st.session_state.get("previous_odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()
    prev_df = pd.DataFrame(previous) if previous else None

    results = run_flags(df, prev_df) if not df.empty else []

    tabs = st.tabs([
        "🎯 DK Ends in 10",
        "🎰 MGM Classic Endings",
        "🤝 Exact Match",
        "⭐ MGM Exact Match",
        "🔢 Matching 25/50/75",
        "💙 FanDuel Patterns",
        "📈 Line Signals",
        "⏳ Price Movement",
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
    show_tab(tabs[6], "signal")
    show_tab(tabs[7], "hist")          # ← Price Movement tab
    show_tab(tabs[8], "same_init")
    show_tab(tabs[9], "cross")
    show_tab(tabs[10], "last")
    show_tab(tabs[11], "first")

    with tabs[12]:
        st.subheader("📖 Girl Magic Glossary")
        st.markdown("""
**🎯 DraftKings Ends in 10**  
Any DK prop ending in 10.

**🎰 BetMGM Classic Endings**  
Pair or group of 3+ on the same team with matching 00/25/50/75 endings.

**🤝 Exact Matching Odds**  
Exact same price on the same player across any books.

**⭐ MGM Exact Match**  
Exact same price on BetMGM for two or more players in the same game.

**🔢 Matching 25/50/75**  
Same player has 25/50/75 endings across different books.

**💙 FanDuel Patterns**  
FanDuel props ≥ +500 ending in 10, 30, 60, 70, or 90.

**📈 Line Signals**  
- Stuck Number: Exact same price on 3+ books  
- Wide Disagreement: One book 150+ away from the median

**⏳ Price Movement**  
Shows how the price changed since your last fetch  
(↑ got longer / ↓ got shorter)

**💅 Same Initials / 🔄 Cross Initials / 👩‍👧 Same Last Name / 👯 Same First Name**  
Only shown if both players already hit an odds method.
        """)

    st.caption("💖 Girl Magic • For the girls only • Our tricks")

if __name__ == "__main__":
    main()
