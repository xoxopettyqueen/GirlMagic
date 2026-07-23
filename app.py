"""
Girl Magic Odds ✨
Final – DK ends in 10 + 00, MGM 00/25/50/75
"""

import streamlit as st
import pandas as pd
import requests
from collections import defaultdict

st.set_page_config(page_title="Girl Magic Odds ✨", page_icon="💖", layout="wide")

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a0a1f 0%, #2d1b3d 50%, #1f0f2e 100%);
        color: #fce7f3;
    }
    h1, h2, h3 { color: #f9a8d4 !important; }
    .stButton > button {
        background: linear-gradient(90deg, #ec4899, #a855f7) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
    }
    .card {
        background: #2a1435;
        border: 1px solid #f472b6;
        border-radius: 12px;
        padding: 14px 18px;
        margin: 10px 0;
        color: #fdf2f8;
    }
    .dk { border-left: 6px solid #00a3e0; }
    .mgm { border-left: 6px solid #c4a35a; }
    .match { border-left: 6px solid #f472b6; }
    .digit { border-left: 6px solid #a855f7; }
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

    if "point" in df.columns:
        df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()

    results = []

    # DraftKings ends in 10 or 00
    for _, row in df.iterrows():
        if "draftkings" in str(row["book"]).lower():
            last = last_two(row["price"])
            if last in (0, 10):          # ← 00 and 10
                results.append({
                    "type": "dk",
                    "label": row["player"],
                    "reason": f"DraftKings ends in {last:02d} → {format_odds(row['price'])}",
                    "event": row["event"],
                    "css": "dk"
                })

    # BetMGM 00 / 25 / 50 / 75
    for _, row in df.iterrows():
        if "betmgm" in str(row["book"]).lower():
            last = last_two(row["price"])
            if last in (0, 25, 50, 75):
                results.append({
                    "type": "mgm",
                    "label": row["player"],
                    "reason": f"BetMGM ends in {last:02d} → {format_odds(row['price'])}",
                    "event": row["event"],
                    "css": "mgm"
                })

    # Exact matching odds (any books)
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

    # ========== BETMGM EXACT MATCH / GROUPS ==========
    mgm_df = df[df["book"].str.lower().str.contains("betmgm|mgm", na=False)].copy()

    for event, event_group in mgm_df.groupby("event"):
        # Exact price groups
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

        # 00/25/50/75 ending groups
        ending_groups = defaultdict(list)
        for _, row in event_group.iterrows():
            d = last_two(row["price"])
            if d in (0, 25, 50, 75):
                ending_groups[d].append(row["player"])

        for d, players in ending_groups.items():
            unique_players = sorted(set(players))
            if len(unique_players) >= 2:
                results.append({
                    "type": "mgm_exact",
                    "label": " + ".join(unique_players),
                    "reason": f"BetMGM {d:02d}s group ({len(unique_players)} players)",
                    "event": event,
                    "css": "mgm"
                })

    # Matching 25/50/75 across books
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        if len(group) < 2: continue
        digits = defaultdict(list)
        for _, row in group.iterrows():
            d = last_two(row["price"])
            if d in (25, 50, 75):
                digits[d].append(row["book"])
        for d, bks in digits.items():
            if len(bks) >= 2:
                results.append({
                    "type": "digit",
                    "label": player,
                    "reason": f"Matching {d}s → {', '.join(bks)}",
                    "event": group["event"].iloc[0],
                    "css": "digit"
                })

    # Name patterns
    players = list(df["player"].dropna().unique())

    # Same initials
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

    # Cross initials
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

    # Same last name
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

    # Same first name
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
    st.caption("Clean • Simple • Ready for the girls")

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

    # ========== TABS ==========
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "🎯 DK 00/10",
        "🎰 MGM 00/25/50/75",
        "🤝 Exact Match",
        "⭐ MGM Exact Match",
        "🔢 Matching 25/50/75",
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

    show_tab(tab1, "dk")
    show_tab(tab2, "mgm")
    show_tab(tab3, "match")
    show_tab(tab4, "mgm_exact")
    show_tab(tab5, "digit")
    show_tab(tab6, "same_init")
    show_tab(tab7, "cross")
    show_tab(tab8, "last")
    show_tab(tab9, "first")

    with tab10:
        st.subheader("📖 Girl Magic Glossary")
        st.markdown("""
**🎯 DraftKings 00 / 10**  
DraftKings endings in 00 (the live 1100s, 2100s, etc.) and 10.

**🎰 BetMGM 00 / 25 / 50 / 75**  
BetMGM classic endings.

**🤝 Exact Matching Odds**  
Two or more books have the exact same price on the same player.

**⭐ MGM Exact Match**  
Two or more players on the same game share the exact same price (or same 00/25/50/75 ending) on BetMGM.  
Shows pairs and groups of 3+.

**🔢 Matching 25s / 50s / 75s**  
Different books landing on the same 25, 50, or 75 ending.

**💅 Same Initials**  
Players who share the same first + last initial.

**🔄 Cross Initials**  
One player’s last initial matches another player’s first initial.

**👩‍👧 Same Last Name**  
Players who share a last name.

**👯 Same First Name**  
Players who share a first name.
        """)

    st.caption("💖 Girl Magic • Made for you & the girls")

if __name__ == "__main__":
    main()
