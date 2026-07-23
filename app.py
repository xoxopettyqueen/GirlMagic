"""
Girl Magic Odds Model ✨
Powered by SharpAPI – fixed version
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

API_BASE = "https://api.sharpapi.io/api/v1"
PREFERRED_BOOKS = ["fanduel", "draftkings", "betmgm", "bet365", "caesars", "williamhill"]

def get_api_key():
    key = st.secrets.get("SHARP_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("SharpAPI Key 🔑", type="password")
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

def fetch_odds(api_key, league="mlb"):
    headers = {"X-API-Key": api_key}
    try:
        r = requests.get(f"{API_BASE}/odds", params={"league": league}, headers=headers, timeout=20)
        if r.status_code != 200:
            st.warning(f"SharpAPI {r.status_code}: {r.text[:250]}")
            return []
        data = r.json()
        return data if isinstance(data, list) else data.get("data", data.get("odds", []))
    except Exception as e:
        st.error(f"Fetch error: {e}")
        return []

def normalize_sharp_data(raw):
    rows = []
    if not raw:
        return rows

    items = raw if isinstance(raw, list) else [raw]

    for item in items:
        event_name = (
            item.get("event_name")
            or item.get("name")
            or f"{item.get('away_team', '')} @ {item.get('home_team', '')}".strip(" @")
            or "Unknown Event"
        )

        # Try several common shapes
        books = (
            item.get("bookmakers")
            or item.get("odds")
            or item.get("sportsbooks")
            or item.get("books")
            or []
        )

        if isinstance(books, dict):
            books = [{"book": k, **v} for k, v in books.items()]

        if not isinstance(books, list):
            books = [books] if books else []

        for book_data in books:
            if not isinstance(book_data, dict):
                continue

            book_name = (
                book_data.get("book")
                or book_data.get("sportsbook")
                or book_data.get("key")
                or book_data.get("name")
                or "unknown"
            )

            markets = (
                book_data.get("markets")
                or book_data.get("outcomes")
                or [book_data]
            )

            if not isinstance(markets, list):
                markets = [markets]

            for market in markets:
                if not isinstance(market, dict):
                    continue

                market_key = (
                    market.get("key")
                    or market.get("market")
                    or market.get("name")
                    or "prop"
                )

                outcomes = market.get("outcomes", [market])
                if not isinstance(outcomes, list):
                    outcomes = [outcomes]

                for o in outcomes:
                    if not isinstance(o, dict):
                        continue

                    player = (
                        o.get("description")
                        or o.get("player")
                        or o.get("name")
                        or o.get("participant")
                    )
                    price = o.get("price") or o.get("odds") or o.get("american")
                    point = o.get("point") or o.get("line")

                    if player and price is not None:
                        rows.append({
                            "event": event_name,
                            "book": str(book_name).lower(),
                            "market": str(market_key).lower(),
                            "player": str(player),
                            "price": price,
                            "point": point,
                        })
    return rows

def run_girl_math(df):
    if df.empty:
        return []

    # Make sure required columns exist
    for col in ["player", "book", "price", "event"]:
        if col not in df.columns:
            df[col] = ""

    scores = defaultdict(lambda: {"score": 0, "reasons": [], "players": set(), "event": ""})

    # Digit & book-specific flags
    for _, row in df.iterrows():
        p = row["player"]
        if not p:
            continue
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
            except:
                pass

    # Exact match + matching digits
    if "player" in df.columns and "point" in df.columns:
        for (player, point), group in df.groupby(["player", "point"], dropna=False):
            if len(group) < 2:
                continue
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
                    if d is not None:
                        digits[d].append(books[i])
                for d, bks in digits.items():
                    if len(bks) >= 2:
                        scores[player]["score"] += 4
                        scores[player]["reasons"].append(f"Matching digits ({d:02d}) – {', '.join(bks)}")
                        scores[player]["players"].add(player)
                        scores[player]["event"] = event

    # Over / Under priced
    if "player" in df.columns and "point" in df.columns:
        for (player, point), group in df.groupby(["player", "point"], dropna=False):
            prices = group["price"].dropna().tolist()
            if len(prices) < 3:
                continue
            try:
                med = statistics.median(prices)
            except:
                continue
            for _, row in group.iterrows():
                if row["price"] is None:
                    continue
                diff = row["price"] - med
                if abs(diff) >= 100:
                    label = "Underpriced" if diff > 0 else "Overpriced"
                    scores[player]["score"] += 2
                    scores[player]["reasons"].append(
                        f"{label} on {row['book']} ({format_odds(row['price'])} vs {format_odds(med)})"
                    )
                    scores[player]["players"].add(player)
                    scores[player]["event"] = row.get("event", "")

    # Name / Initial patterns
    players = list(df["player"].dropna().unique()) if "player" in df.columns else []
    init_map = defaultdict(list)
    for p in players:
        f, l = get_initials(p)
        if f and l:
            init_map[f + l].append(p)
    for k, names in init_map.items():
        if len(names) >= 2:
            key = " + ".join(sorted(names))
            scores[key]["score"] += 3
            scores[key]["reasons"].append(f"Same initials {k}")
            scores[key]["players"].update(names)

    for i, p1 in enumerate(players):
        f1, l1 = get_initials(p1)
        if not l1:
            continue
        for p2 in players[i + 1:]:
            f2, _ = get_initials(p2)
            if f2 and l1 == f2:
                key = " + ".join(sorted([p1, p2]))
                scores[key]["score"] += 3
                scores[key]["reasons"].append(f"Cross initial ({l1})")
                scores[key]["players"].update([p1, p2])

    results = []
    for key, data in scores.items():
        if data["score"] <= 0:
            continue
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
    st.caption("Powered by SharpAPI • Pure odds tricks")

    api_key = get_api_key()
    if not api_key:
        st.warning("Add your SharpAPI key in Secrets or the sidebar")
        st.stop()

    with st.sidebar:
        st.header("Settings")
        max_show = st.slider("Max results", 5, 40, 20)

    if st.button("Fetch MLB Odds from SharpAPI 💫", type="primary"):
        with st.spinner("Pulling from SharpAPI..."):
            raw = fetch_odds(api_key, league="mlb")
            rows = normalize_sharp_data(raw)
            st.session_state["odds"] = rows
            if rows:
                books = sorted(set(r["book"] for r in rows))
                st.success(f"Loaded {len(rows)} rows")
                st.write("**Books returned:**", ", ".join(books))
                preferred = [b for b in books if is_preferred(b)]
                if preferred:
                    st.success(f"Preferred books found: {', '.join(preferred)}")
                else:
                    st.warning("Preferred books not present in this response")
            else:
                st.warning("No usable odds returned. The free tier may be limited or the response shape is different.")

    odds = st.session_state.get("odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()

    results = run_girl_math(df) if not df.empty else []

    tab1, tab2, tab3 = st.tabs(["💅 Odds Magic", "📊 Girl Math Flags", "👑 Queen of the Digits"])

    with tab1:
        st.subheader("💅 Odds Magic")
        if not results:
            st.info("Click the fetch button above")
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

    st.caption("💖 Girl Magic × SharpAPI")

if __name__ == "__main__":
    main()
