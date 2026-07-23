"""
Girl Magic Odds Model ✨
Powered by SportsGameOdds
Clean odds tricks + Girl Math only
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
    .score-badge { color: #f9a8d4; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

API_BASE = "https://api.sportsgameodds.com/v2"
PREFERRED_BOOKS = ["fanduel", "draftkings", "betmgm", "bet365", "caesars", "williamhill"]

def get_api_key():
    key = st.secrets.get("SGO_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("SportsGameOdds API Key 🔑", type="password")
    return key

def is_preferred(book):
    if not book: return False
    return any(p in str(book).lower() for p in PREFERRED_BOOKS)

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
    """Fetch MLB events with odds"""
    params = {
        "apiKey": api_key,
        "leagueID": "MLB",
        "oddsAvailable": "true",
        "limit": 15
    }
    try:
        r = requests.get(f"{API_BASE}/events", params=params, timeout=25)
        if r.status_code != 200:
            st.warning(f"SportsGameOdds {r.status_code}: {r.text[:300]}")
            return []
        data = r.json()
        return data.get("data", data) if isinstance(data, dict) else data
    except Exception as e:
        st.error(f"Error: {e}")
        return []

def normalize_sgo_data(events):
    """Flatten SportsGameOdds response into clean rows"""
    rows = []
    if not events:
        return rows

    for event in events if isinstance(events, list) else [events]:
        if not isinstance(event, dict):
            continue

        away = event.get("awayTeam", {}).get("name") or event.get("away_team") or event.get("teams", {}).get("away", {}).get("name") or ""
        home = event.get("homeTeam", {}).get("name") or event.get("home_team") or event.get("teams", {}).get("home", {}).get("name") or ""
        event_name = f"{away} @ {home}".strip(" @") or event.get("name") or "Unknown"

        # Odds can be nested in different places
        odds_list = (
            event.get("odds")
            or event.get("bookmakers")
            or event.get("markets")
            or []
        )

        if isinstance(odds_list, dict):
            odds_list = list(odds_list.values())

        for odd in odds_list if isinstance(odds_list, list) else []:
            if not isinstance(odd, dict):
                continue

            book = (
                odd.get("bookmaker")
                or odd.get("sportsbook")
                or odd.get("book")
                or odd.get("source")
                or "unknown"
            )

            market = odd.get("marketName") or odd.get("market") or odd.get("betType") or "prop"
            player = odd.get("playerName") or odd.get("player") or odd.get("participant") or odd.get("name")
            price = odd.get("price") or odd.get("odds") or odd.get("americanOdds") or odd.get("american")
            point = odd.get("line") or odd.get("point") or odd.get("handicap")

            # Sometimes outcomes are nested
            outcomes = odd.get("outcomes") or odd.get("prices") or [odd]
            if not isinstance(outcomes, list):
                outcomes = [outcomes]

            for o in outcomes:
                if not isinstance(o, dict):
                    continue
                p_name = o.get("playerName") or o.get("player") or o.get("name") or player
                p_price = o.get("price") or o.get("odds") or o.get("american") or price
                p_point = o.get("line") or o.get("point") or point

                if p_name and p_price is not None:
                    rows.append({
                        "event": event_name,
                        "book": str(book).lower(),
                        "market": str(market).lower(),
                        "player": str(p_name),
                        "price": p_price,
                        "point": p_point,
                    })

    return rows

def run_girl_math(df):
    if df.empty:
        return []

    for col in ["player", "book", "price", "event"]:
        if col not in df.columns:
            df[col] = ""

    scores = defaultdict(lambda: {"score": 0, "reasons": [], "players": set(), "event": ""})

    for _, row in df.iterrows():
        p = row["player"]
        if not p: continue
        price = row["price"]
        book = str(row["book"]).lower()
        event = row.get("event", "")
        last = last_two(price)

        if "betmgm" in book or "mgm" in book:
            if last in (25, 50, 75):
                scores[p]["score"] += 3
                scores[p]["reasons"].append(f"BetMGM ends in {last}")
                scores[p]["players"].add(p)
                scores[p]["event"] = event

        if "draftkings" in book or "dk" in book:
            if last == 10:
                scores[p]["score"] += 3
                scores[p]["reasons"].append("DraftKings ends in 10")
                scores[p]["players"].add(p)
                scores[p]["event"] = event

        if "bet365" in book:
            try:
                if abs(int(price)) == 850:
                    scores[p]["score"] += 3
                    scores[p]["reasons"].append("Bet365 +850 Club")
                    scores[p]["players"].add(p)
                    scores[p]["event"] = event
            except: pass

    # Exact + matching digits
    if "player" in df.columns:
        for (player, point), group in df.groupby(["player", "point"], dropna=False):
            if len(group) < 2: continue
            prices = group["price"].dropna().tolist()
            books = group["book"].tolist()
            event = group["event"].iloc[0] if "event" in group.columns and len(group) else ""

            if len(set(prices)) == 1:
                scores[player]["score"] += 5
                scores[player]["reasons"].append(f"Exact match {format_odds(prices[0])} across {', '.join(books)}")
                scores[player]["players"].add(player)
                scores[player]["event"] = event
            else:
                digits = defaultdict(list)
                for i, pr in enumerate(prices):
                    d = last_two(pr)
                    if d is not None: digits[d].append(books[i])
                for d, bks in digits.items():
                    if len(bks) >= 2:
                        scores[player]["score"] += 4
                        scores[player]["reasons"].append(f"Matching digits ({d:02d}) – {', '.join(bks)}")
                        scores[player]["players"].add(player)
                        scores[player]["event"] = event

    # Over/Under
    if "player" in df.columns:
        for (player, point), group in df.groupby(["player", "point"], dropna=False):
            prices = group["price"].dropna().tolist()
            if len(prices) < 3: continue
            try: med = statistics.median(prices)
            except: continue
            for _, row in group.iterrows():
                if row["price"] is None: continue
                diff = row["price"] - med
                if abs(diff) >= 100:
                    label = "Underpriced" if diff > 0 else "Overpriced"
                    scores[player]["score"] += 2
                    scores[player]["reasons"].append(f"{label} on {row['book']} ({format_odds(row['price'])} vs {format_odds(med)})")
                    scores[player]["players"].add(player)
                    scores[player]["event"] = row.get("event", "")

    # Initials
    players = list(df["player"].dropna().unique()) if "player" in df.columns else []
    init_map = defaultdict(list)
    for p in players:
        f, l = get_initials(p)
        if f and l: init_map[f+l].append(p)
    for k, names in init_map.items():
        if len(names) >= 2:
            key = " + ".join(sorted(names))
            scores[key]["score"] += 3
            scores[key]["reasons"].append(f"Same initials {k}")
            scores[key]["players"].update(names)

    for i, p1 in enumerate(players):
        _, l1 = get_initials(p1)
        if not l1: continue
        for p2 in players[i+1:]:
            f2, _ = get_initials(p2)
            if f2 and l1 == f2:
                key = " + ".join(sorted([p1, p2]))
                scores[key]["score"] += 3
                scores[key]["reasons"].append(f"Cross initial ({l1})")
                scores[key]["players"].update([p1, p2])

    results = []
    for key, data in scores.items():
        if data["score"] <= 0: continue
        is_pair = " + " in key
        results.append({
            "label": key,
            "score": data["score"] + (2 if is_pair else 0),
            "reasons": list(set(data["reasons"])),
            "event": data.get("event", ""),
            "is_pair": is_pair
        })
    return sorted(results, key=lambda x: x["score"], reverse=True)

def main():
    st.title("💖 Girl Magic Odds Model")
    st.caption("Powered by SportsGameOdds • Pure odds tricks")

    api_key = get_api_key()
    if not api_key:
        st.warning("Add your SportsGameOdds API key")
        st.stop()

    with st.sidebar:
        st.header("Settings")
        max_show = st.slider("Max results", 5, 40, 20)

    if st.button("Fetch MLB Odds 💫", type="primary"):
        with st.spinner("Pulling from SportsGameOdds..."):
            events = fetch_events(api_key)
            rows = normalize_sgo_data(events)
            st.session_state["odds"] = rows
            if rows:
                books = sorted(set(r["book"] for r in rows))
                st.success(f"Loaded {len(rows)} rows")
                st.write("**Books returned:**", ", ".join(books) if books else "none")
                preferred = [b for b in books if is_preferred(b)]
                if preferred:
                    st.success(f"Preferred books found: {', '.join(preferred)}")
                else:
                    st.warning("Preferred books not present")
            else:
                st.warning("No usable odds returned. Free tier may be limited or response shape different.")

    odds = st.session_state.get("odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()
    results = run_girl_math(df) if not df.empty else []

    tab1, tab2, tab3 = st.tabs(["💅 Odds Magic", "📊 Girl Math Flags", "👑 Queen of the Digits"])

    with tab1:
        st.subheader("💅 Odds Magic")
        if not results:
            st.info("Click the fetch button")
        else:
            for r in results[:max_show]:
                reasons = " • ".join(r["reasons"][:5])
                st.markdown(
                    f'<div class="magic-card">'
                    f'<b>{r["label"]}</b> <span class="score-badge">Score {r["score"]}</span><br>'
                    f'<small>{r.get("event","")}</small><br>{reasons}'
                    f'</div>', unsafe_allow_html=True
                )

    with tab2:
        st.subheader("📊 All Flags")
        if not results:
            st.info("No flags yet")
        else:
            for r in results:
                st.markdown(
                    f'<div class="magic-card"><b>{r["label"]}</b> — {r["score"]}<br>{" • ".join(r["reasons"])}</div>',
                    unsafe_allow_html=True
                )

    with tab3:
        st.subheader("👑 Queen of the Digits")
        digit_results = [r for r in results if any(
            any(x in reason.lower() for x in ["digit", "ends in", "850", "exact match", "25", "50", "75", "10"])
            for reason in r["reasons"]
        )]
        if not digit_results:
            st.info("No digit patterns found")
        else:
            for r in digit_results:
                st.markdown(
                    f'<div class="magic-card"><b>{r["label"]}</b><br>{" • ".join(r["reasons"])}</div>',
                    unsafe_allow_html=True
                )

    st.caption("💖 Girl Magic × SportsGameOdds")

if __name__ == "__main__":
    main()
