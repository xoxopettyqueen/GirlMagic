"""
Girl Magic ✨
Only 0.5 HR + Clear flags + Name patterns
Matching digits restricted to 25/50/75 only
"""

import streamlit as st
import pandas as pd
import requests
from collections import defaultdict
import statistics

st.set_page_config(page_title="Girl Magic Odds ✨", page_icon="💖", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #1a0a1f 0%, #2d1b3d 50%, #1f0f2e 100%); color: #fce7f3; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #2a1435, #1c0d24); border-right: 1px solid #a855f7; }
    h1, h2, h3 { color: #f9a8d4 !important; }
    .stButton > button {
        background: linear-gradient(90deg, #ec4899, #a855f7) !important;
        color: white !important; border: none !important; border-radius: 12px !important; font-weight: 600 !important;
    }
    .magic-card {
        background: #2a1435; border: 1px solid #f472b6; border-radius: 12px;
        padding: 14px 18px; margin: 10px 0; color: #fdf2f8;
    }
    .flag-dk { border-left: 5px solid #00a3e0; }
    .flag-mgm { border-left: 5px solid #c4a35a; }
    .flag-match { border-left: 5px solid #f472b6; }
    .flag-digit { border-left: 5px solid #a855f7; }
    .flag-price { border-left: 5px solid #34d399; }
    .flag-name { border-left: 5px solid #f9a8d4; }
</style>
""", unsafe_allow_html=True)

API_BASE = "https://api.the-odds-api.com/v4"
REGIONS = "us,us2"

def get_api_key():
    key = st.secrets.get("ODDS_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("Odds API Key 🔑", type="password")
    return key

def format_odds(p):
    if p is None: return "-"
    try: return f"{int(p):+d}"
    except: return str(p)

def last_two(p):
    try: return abs(int(p)) % 100
    except: return None

def get_initials(name):
    parts = str(name).strip().split()
    if not parts: return None, None
    first = parts[0][0].upper() if parts[0] else None
    last = parts[-1][0].upper() if len(parts) > 1 else None
    return first, last

def fetch_events(api_key):
    try:
        r = requests.get(f"{API_BASE}/sports/baseball_mlb/events", params={"apiKey": api_key}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Events error: {e}")
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
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

def flatten(data):
    if not data: return []
    rows = []
    for book in data.get("bookmakers", []):
        for market in book.get("markets", []):
            for o in market.get("outcomes", []):
                if o.get("name", "").lower() != "over":
                    continue
                rows.append({
                    "event": f"{data.get('away_team')} @ {data.get('home_team')}",
                    "book": book.get("key", "unknown"),
                    "player": o.get("description"),
                    "price": o.get("price"),
                    "point": o.get("point"),
                })
    return rows

def run_girl_math(df):
    if df.empty:
        return []

    # STRICT only lowest line (0.5 / 1)
    if "point" in df.columns:
        df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()

    results = []

    # DraftKings ends in 10
    for _, row in df.iterrows():
        book = str(row["book"]).lower()
        if "draftkings" in book or "dk" in book:
            if last_two(row["price"]) == 10:
                results.append({
                    "type": "dk10",
                    "label": row["player"],
                    "reason": f"DraftKings ends in 10 → {format_odds(row['price'])}",
                    "event": row.get("event", ""),
                    "css": "flag-dk"
                })

    # BetMGM 25/50/75
    for _, row in df.iterrows():
        book = str(row["book"]).lower()
        if "betmgm" in book or "mgm" in book:
            last = last_two(row["price"])
            if last in (25, 50, 75):
                results.append({
                    "type": "mgm",
                    "label": row["player"],
                    "reason": f"BetMGM ends in {last} → {format_odds(row['price'])}",
                    "event": row.get("event", ""),
                    "css": "flag-mgm"
                })

    # Exact matching odds
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        if len(group) < 2: continue
        prices = group["price"].dropna().tolist()
        books = group["book"].tolist()
        if len(set(prices)) == 1:
            results.append({
                "type": "exact",
                "label": player,
                "reason": f"Exact match {format_odds(prices[0])} across {', '.join(books)}",
                "event": group["event"].iloc[0] if len(group) else "",
                "css": "flag-match"
            })

    # Matching last two digits — ONLY 25 / 50 / 75
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        if len(group) < 2: continue
        digits = defaultdict(list)
        for _, row in group.iterrows():
            d = last_two(row["price"])
            if d is not None:
                digits[d].append(row["book"])
        for d, bks in digits.items():
            if d in (25, 50, 75) and len(bks) >= 2:          # ← restricted here
                results.append({
                    "type": "digit",
                    "label": player,
                    "reason": f"Matching {d:02d}s → {', '.join(bks)}",
                    "event": group["event"].iloc[0] if len(group) else "",
                    "css": "flag-digit"
                })

    # Over/Under priced
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        prices = group["price"].dropna().tolist()
        if len(prices) < 3: continue
        try:
            med = statistics.median(prices)
        except:
            continue
        for _, row in group.iterrows():
            if row["price"] is None: continue
            diff = row["price"] - med
            if abs(diff) >= 100:
                label = "Underpriced" if diff > 0 else "Overpriced"
                results.append({
                    "type": "price",
                    "label": player,
                    "reason": f"{label} on {row['book']} ({format_odds(row['price'])} vs med {format_odds(med)})",
                    "event": row.get("event", ""),
                    "css": "flag-price"
                })

    # ===== GIRL MATH NAME PATTERNS =====
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
                "css": "flag-name"
            })

    # Cross initials
    for i, p1 in enumerate(players):
        f1, l1 = get_initials(p1)
        if not l1: continue
        for p2 in players[i+1:]:
            f2, l2 = get_initials(p2)
            if f2 and l1 == f2:
                results.append({
                    "type": "cross_init",
                    "label": f"{p1} + {p2}",
                    "reason": f"Cross initial ({l1} → {f2})",
                    "event": "",
                    "css": "flag-name"
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
                "type": "same_last",
                "label": " + ".join(sorted(names)),
                "reason": f"Same last name ({last.title()})",
                "event": "",
                "css": "flag-name"
            })

    return results

def main():
    st.title("💖 Girl Magic Odds Model")
    st.caption("Only 0.5 HR • Matching digits = 25/50/75 only")

    api_key = get_api_key()
    if not api_key:
        st.warning("Add your Odds API key in Secrets")
        st.stop()

    if st.button("Load MLB Games 💫", type="primary"):
        st.session_state["events"] = fetch_events(api_key)

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load MLB Games**")
        st.stop()

    options = {f"{e.get('away_team')} @ {e.get('home_team')}": e["id"] for e in events}
    chosen = st.multiselect("Select games", list(options.keys()))

    if st.button("Fetch Odds 💖", type="primary") and chosen:
        all_rows = []
        prog = st.progress(0)
        for i, label in enumerate(chosen):
            data = fetch_odds(api_key, options[label])
            all_rows.extend(flatten(data))
            prog.progress((i+1)/len(chosen))

        if all_rows:
            df_temp = pd.DataFrame(all_rows)
            if "point" in df_temp.columns:
                df_temp = df_temp.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()
                all_rows = df_temp.to_dict("records")

            books = sorted(set(r["book"] for r in all_rows))
            st.success(f"Loaded {len(all_rows)} rows (Only 0.5/1 HR)")
            st.write("**Books:**", ", ".join(books))
            st.session_state["odds"] = all_rows
        else:
            st.warning("No odds returned")

    odds = st.session_state.get("odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()
    results = run_girl_math(df) if not df.empty else []

    # ===== SECTIONS =====
    st.subheader("🎯 DraftKings Ends in 10")
    items = [x for x in results if x["type"] == "dk10"]
    for r in items:
        st.markdown(f'<div class="magic-card {r["css"]}"><b>{r["label"]}</b><br>{r["reason"]}<br><small>{r["event"]}</small></div>', unsafe_allow_html=True)
    if not items: st.caption("None")

    st.subheader("🎰 BetMGM 25 / 50 / 75")
    items = [x for x in results if x["type"] == "mgm"]
    for r in items:
        st.markdown(f'<div class="magic-card {r["css"]}"><b>{r["label"]}</b><br>{r["reason"]}<br><small>{r["event"]}</small></div>', unsafe_allow_html=True)
    if not items: st.caption("None")

    st.subheader("🤝 Exact Matching Odds")
    items = [x for x in results if x["type"] == "exact"]
    for r in items:
        st.markdown(f'<div class="magic-card {r["css"]}"><b>{r["label"]}</b><br>{r["reason"]}<br><small>{r["event"]}</small></div>', unsafe_allow_html=True)
    if not items: st.caption("None")

    st.subheader("🔢 Matching 25s / 50s / 75s")
    items = [x for x in results if x["type"] == "digit"]
    for r in items:
        st.markdown(f'<div class="magic-card {r["css"]}"><b>{r["label"]}</b><br>{r["reason"]}<br><small>{r["event"]}</small></div>', unsafe_allow_html=True)
    if not items: st.caption("None")

    st.subheader("💰 Overpriced / Underpriced")
    items = [x for x in results if x["type"] == "price"]
    for r in items:
        st.markdown(f'<div class="magic-card {r["css"]}"><b>{r["label"]}</b><br>{r["reason"]}<br><small>{r["event"]}</small></div>', unsafe_allow_html=True)
    if not items: st.caption("None")

    st.subheader("💅 Girl Math – Same Initials")
    items = [x for x in results if x["type"] == "same_init"]
    for r in items:
        st.markdown(f'<div class="magic-card {r["css"]}"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
    if not items: st.caption("None")

    st.subheader("🔄 Girl Math – Cross Initials")
    items = [x for x in results if x["type"] == "cross_init"]
    for r in items:
        st.markdown(f'<div class="magic-card {r["css"]}"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
    if not items: st.caption("None")

    st.subheader("👩‍👧 Girl Math – Same Last Name")
    items = [x for x in results if x["type"] == "same_last"]
    for r in items:
        st.markdown(f'<div class="magic-card {r["css"]}"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
    if not items: st.caption("None")

    st.caption("💖 Girl Magic • Only 0.5 HR • Matching digits = 25/50/75 only")

if __name__ == "__main__":
    main()
