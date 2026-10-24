# -*- coding: utf-8 -*-
"""
Girl Magic Odds 2.0
Pure odds engine. EV gap, volatility, spike, TAKE/LEAN/PASS.
No stats. No projections. Just the books and the gaps.
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
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600;700&family=Oswald:wght@500&display=swap');
.stApp{background:#0B0B0F;color:#fff;font-family:'Inter',sans-serif}
.hero{background:linear-gradient(90deg,#FF4DA6,#9B5FFF,#5E4AE3);border-radius:24px;padding:18px 22px;margin-bottom:14px;color:#fff;box-shadow:0 0 24px rgba(0,0,0,.6)}
.hero h1{margin:0;font-size:1.7rem;font-weight:700;font-family:'Playfair Display',serif;text-shadow:0 0 12px rgba(255,77,166,.7);animation:shimmerText 3s ease-in-out infinite}
.hero p{margin:4px 0 0;opacity:.85;font-size:.78rem;color:#F5E9FF;font-style:italic}
@keyframes shimmerText{0%{text-shadow:0 0 8px rgba(255,77,166,.4)}50%{text-shadow:0 0 16px rgba(255,77,166,.9)}100%{text-shadow:0 0 8px rgba(255,77,166,.4)}}
button[kind="primary"], .stButton > button[kind="primary"]{background:linear-gradient(90deg,#FF4DA6,#FF7AC4)!important;border:none!important;border-radius:999px!important;font-weight:600!important;box-shadow:0 0 16px rgba(255,77,166,.7)!important;color:#fff!important}
button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover{box-shadow:0 0 20px rgba(255,77,166,.9)!important}
.stTabs [data-baseweb="tab-list"]{gap:8px}
.stTabs [data-baseweb="tab"]{background:#14141A;border-radius:999px;padding:6px 14px;color:#CBA6F7}
.stTabs [aria-selected="true"]{background:linear-gradient(90deg,#FF4DA6,#9B5FFF)!important;color:#fff!important}
.card{background:#14141A;border:1px solid #262633;border-radius:16px;padding:12px 14px;margin-bottom:12px;position:relative;transition:box-shadow .2s,transform .2s}
.card:hover{transform:translateY(-2px);box-shadow:0 12px 28px rgba(0,0,0,.8)}
.card.take-card{border-color:rgba(255,77,166,.7);box-shadow:0 0 18px rgba(255,77,166,.4)}
.player{font-size:1.05rem;font-weight:700;margin:0;font-family:'Playfair Display',serif}
.meta{color:#B3B3C3;font-size:.68rem;margin:2px 0 6px;font-style:italic}
.prop{font-size:.9rem;font-weight:600;color:#FF4DA6;margin-bottom:6px;text-transform:uppercase}
.books{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0}
.bk{background:#0F0F14;border:1px solid #262633;border-radius:999px;padding:4px 8px;text-align:center;min-width:60px;font-size:.7rem;font-weight:600;font-family:'Oswald',sans-serif}
.bk.best{border-color:#FF4DA6;box-shadow:0 0 10px rgba(255,77,166,.7)}
.bk span{display:block;font-size:.55rem;color:#CBA6F7}
.tag{display:inline-block;background:rgba(203,166,247,.18);color:#F5E9FF;border:1px solid rgba(203,166,247,.6);border-radius:999px;padding:2px 8px;font-size:.6rem;font-weight:600;margin:2px 3px 0 0}
.decision{display:inline-block;border-radius:999px;padding:4px 12px;font-size:.72rem;font-weight:700;margin-top:6px}
.take{background:linear-gradient(90deg,#FF4DA6,#FF7AC4);color:#fff;box-shadow:0 0 14px rgba(255,77,166,.7)}
.lean{background:#9B5FFF;color:#fff}
.pass{background:#4b5563;color:#fff}
.why{font-size:.66rem;color:#B3B3C3;margin-top:6px}
.why b{color:#FF4DA6}
.take-tag{position:absolute;top:8px;right:10px;font-size:.58rem;letter-spacing:.12em;color:#FF4DA6;font-weight:700;text-transform:uppercase}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
LEDGER = Path("odds_ledger.json")

MY_BOOKS = {
    "fanduel":"FD","draftkings":"DK","betmgm":"MGM","bet365":"365",
    "williamhill_us":"CZR","fanatics":"FAN","espnbet":"SCR","hardrockbet":"HR",
    "hardrockbet_az":"HR","hardrockbet_oh":"HR","hardrockbet_fl":"HR",
}
BOOK_FULL = {"FD":"FanDuel","DK":"DraftKings","MGM":"BetMGM","365":"Bet365","CZR":"Caesars","FAN":"Fanatics","SCR":"theScore","HR":"Hard Rock"}

HOT_ENDS = {5,10,25,30,35,40,55,65,75,80,85,90}
NBA_SKIP = {"nikola jokic","trae young","tyrese haliburton","luka doncic","james harden","jalen brunson","damian lillard","stephen curry","lamelo ball","cade cunningham","scoot henderson","chris paul"}

def last_two(p):
    try: return abs(int(p)) % 100
    except: return None

def implied(price):
    try:
        p = int(price)
        return 100/(p+100) if p>0 else abs(p)/(abs(p)+100)
    except: return None

def normalize_book(key):
    k = str(key or "").lower()
    if "bet365" in k: return "bet365"
    if "fanatic" in k: return "fanatics"
    if "hardrock" in k: return "hardrockbet"
    if "espnbet" in k or "score" in k: return "espnbet"
    if "draftking" in k: return "draftkings"
    if "fanduel" in k: return "fanduel"
    if "betmgm" in k or k=="mgm": return "betmgm"
    if "williamhill" in k or "caesar" in k: return "williamhill_us"
    return k

def load_ledger():
    # Prefer browser localStorage if available, else session, else file
    browser = st.session_state.get("_browser_ledger")
    if browser is not None:
        return browser
    sess = st.session_state.get("ledger", [])
    file_data = []
    if LEDGER.exists():
        try:
            file_data = json.loads(LEDGER.read_text())
        except: file_data = []
    best = file_data if len(file_data) > len(sess) else sess
    st.session_state["ledger"] = best
    return best

def save_ledger(rows):
    st.session_state["ledger"] = rows
    st.session_state["_browser_ledger"] = rows
    try: LEDGER.write_text(json.dumps(rows, indent=2))
    except: pass
    # Push to browser localStorage
    st.components.v1.html(f"""
    <script>
    try {{
        localStorage.setItem('gmo_ledger', {json.dumps(json.dumps(rows))});
    }} catch(e) {{}}
    </script>
    """, height=0)

def restore_browser_ledger():
    # Pull from localStorage on first load
    if "_browser_checked" in st.session_state:
        return
    st.session_state["_browser_checked"] = True
    st.components.v1.html("""
    <script>
    try {
        const data = localStorage.getItem('gmo_ledger');
        if (data) {
            window.parent.postMessage({type:'gmo_ledger', data: JSON.parse(data)}, '*');
        }
    } catch(e) {}
    </script>
    """, height=0)

def auto_grade_nba(ledger):
    """Grade NBA plays using ESPN public box scores. No extra API key."""
    if not ledger:
        return ledger, 0
    graded = 0
    try:
        # Get recent finished games from scoreboard
        r = requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard", timeout=15)
        if r.status_code != 200:
            return ledger, 0
        events = r.json().get("events") or []
        # Build player stat lookup from finished games
        player_stats = {}
        for ev in events:
            status = (ev.get("status") or {}).get("type", {}).get("completed")
            if not status:
                continue
            eid = ev.get("id")
            if not eid:
                continue
            try:
                sr = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={eid}", timeout=15)
                if sr.status_code != 200:
                    continue
                box = sr.json().get("boxscore") or {}
                for team in box.get("players") or []:
                    for stat_group in team.get("statistics") or []:
                        labels = [x.lower() for x in (stat_group.get("labels") or [])]
                        for ath in stat_group.get("athletes") or []:
                            name = (ath.get("athlete") or {}).get("displayName") or ""
                            stats = ath.get("stats") or []
                            if not name or not stats:
                                continue
                            # Map common labels
                            sdict = {}
                            for i, lab in enumerate(labels):
                                if i < len(stats):
                                    try:
                                        sdict[lab] = float(stats[i]) if stats[i] not in ("", "-") else 0
                                    except:
                                        sdict[lab] = 0
                            player_stats[name.lower()] = sdict
            except:
                continue
        # Grade ledger rows
        for row in ledger:
            if row.get("result") or "NBA" not in str(row.get("sport", "")):
                continue
            player = (row.get("player") or "").lower()
            if not player:
                continue
            # Find matching player
            match = None
            for pname, sdict in player_stats.items():
                if player in pname or pname in player:
                    match = sdict
                    break
            if not match:
                continue
            prop = row.get("prop")
            line = float(row.get("line") or 0)
            val = None
            if prop == "Assists":
                val = match.get("ast") or match.get("assists")
            elif prop == "Points":
                val = match.get("pts") or match.get("points")
            elif prop == "Rebounds":
                val = match.get("reb") or match.get("rebounds")
            elif prop == "DoubleDouble":
                pts = match.get("pts") or match.get("points") or 0
                reb = match.get("reb") or match.get("rebounds") or 0
                ast = match.get("ast") or match.get("assists") or 0
                val = sum(1 for v in (pts, reb, ast) if v >= 10)
            if val is None:
                row["result"] = "PENDING"
                continue
            hit = (val > line) if prop != "DoubleDouble" else (val >= 2)
            row["result"] = "hit" if hit else "miss"
            row["graded_at"] = datetime.now().isoformat(timespec="minutes")
            graded += 1
    except:
        pass
    return ledger, graded

@st.cache_data(ttl=120)
def fetch_events(api_key, sport_key):
    try:
        r = requests.get(f"{ODDS_API_BASE}/sports/{sport_key}/events", params={"apiKey":api_key}, timeout=15)
        if r.status_code==200: return r.json() or []
    except: pass
    return []

@st.cache_data(ttl=90)
def fetch_odds(api_key, sport_key, event_id, markets):
    try:
        r = requests.get(f"{ODDS_API_BASE}/sports/{sport_key}/events/{event_id}/odds",
            params={"apiKey":api_key,"regions":"us,us2,uk","markets":markets,"oddsFormat":"american"}, timeout=20)
        if r.status_code==200: return r.json()
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
                if "assists" in mkey: prop_type="Assists"
                elif "points" in mkey and "rebounds" not in mkey and "assists" not in mkey: prop_type="Points"
                elif "rebounds" in mkey and "points" not in mkey and "assists" not in mkey: prop_type="Rebounds"
                elif "double_double" in mkey: prop_type="DoubleDouble"
            else:
                if "anytime_td" in mkey: prop_type="Anytime TD"
                elif "reception_yds" in mkey or "receiving_yds" in mkey: prop_type="Rec Yards"
            if not prop_type: continue
            for o in market.get("outcomes") or []:
                oname = str(o.get("name") or "").lower()
                if prop_type in ("DoubleDouble","Anytime TD"):
                    if oname not in ("yes","over"): continue
                    player = o.get("description") or o.get("name")
                    line = 0.5 if prop_type=="Anytime TD" else 1.0
                else:
                    if oname != "over": continue
                    player = o.get("description")
                    line = o.get("point")
                    if line is None: continue
                    try: line=float(line)
                    except: continue
                if not player or str(player).lower() in ("yes","no","over","under"): continue
                if "NBA" in str(sport) and prop_type=="Assists" and any(x in str(player).lower() for x in NBA_SKIP): continue
                try: price=int(o.get("price"))
                except: continue
                if "NBA" in str(sport):
                    if prop_type=="Assists" and not (2.5<=line<=6.5): continue
                    if prop_type=="Points" and not (8.0<=line<=15.0): continue
                    if prop_type=="Rebounds" and not (5.0<=line<=8.0): continue
                    if prop_type!="DoubleDouble" and price<300: continue
                    if prop_type=="DoubleDouble" and price<400: continue
                else:
                    if prop_type=="Anytime TD" and price<300: continue
                    if prop_type=="Rec Yards" and not (1.0<=line<=15.0): continue
                    if prop_type=="Rec Yards" and price<300: continue
                plays.append({"sport":sport,"event":event,"player":player,"prop":prop_type,"line":line,"price":price,"book":short})
    return plays

def compute_signals(book_prices, best_price):
    prices = list(book_prices.values())
    if not prices: return {}, "PASS"
    med = sorted(prices)[len(prices)//2]
    longest = max(prices)
    ev_gap = (longest - med) / med if med else 0
    # Approximate volatility and movement from current disagreement (no history yet)
    spread = (max(prices) - min(prices)) / med if med else 0
    vol = "High" if spread > 0.4 else "Medium" if spread > 0.15 else "Low"
    move = "Snap" if spread > 0.5 else "Drift" if spread > 0.2 else "Freeze"
    book_beh = "Solo" if len(prices) <= 2 or (longest - med) / med > 0.6 else "Cluster"
    spike = ev_gap + (0.3 if vol=="High" else 0.15 if vol=="Medium" else 0.05) * spread
    if spike > 0.25 and vol != "Low": decision = "TAKE"
    elif spike > 0.08: decision = "LEAN"
    else: decision = "PASS"
    return {
        "median": int(med), "longest": longest, "ev_gap": round(ev_gap*100,1),
        "vol": vol, "move": move, "book_beh": book_beh, "spike": round(spike,2),
        "decision": decision,
    }, decision

def best_cards(plays):
    by = defaultdict(list)
    for p in plays:
        key = (p["sport"], p["player"], p["prop"], round(p["line"],1), p["event"])
        by[key].append(p)
    cards = []
    for key, group in by.items():
        best = max(group, key=lambda x: x["price"])
        book_prices = {g["book"]: g["price"] for g in group}
        signals, decision = compute_signals(book_prices, best["price"])
        end = last_two(best["price"])
        tags = []
        if signals.get("book_beh")=="Solo": tags.append("Solo")
        if signals.get("book_beh")=="Cluster": tags.append("Cluster")
        if signals.get("move")=="Snap": tags.append("Snap")
        if signals.get("move")=="Drift": tags.append("Drift")
        if signals.get("move")=="Freeze": tags.append("Freeze")
        if signals.get("vol")=="High": tags.append("Surge")
        if end in HOT_ENDS: tags.append(f"Hot {end:02d}")
        cards.append({**best, "book_prices":book_prices, **signals, "end":end, "tags":tags, "decision":decision})
    cards.sort(key=lambda x: (-x.get("spike",0), -x.get("ev_gap",0)))
    return cards

def odds_bucket(price):
    if price < 600: return "+300–599"
    if price < 1500: return "+600–1499"
    if price < 4000: return "+1500–3999"
    return "+4000+"

def main():
    restore_browser_ledger()
    st.markdown('<div class="hero"><h1>✨ Girl Magic Odds 2.0</h1><p>Odds Only. Chaos Powered. Plus-Money Forever.</p></div>', unsafe_allow_html=True)
    st.markdown("""<div style="display:flex;gap:6px;justify-content:center;margin-bottom:10px;font-size:.65rem;color:#CBA6F7;">
    <span style="background:#14141A;border:1px solid #FF4DA6;border-radius:999px;padding:3px 8px;">1. Pull the chaos</span>
    <span style="background:#14141A;border:1px solid #9B5FFF;border-radius:999px;padding:3px 8px;">2. Scan TAKEs</span>
    <span style="background:#14141A;border:1px solid #5E4AE3;border-radius:999px;padding:3px 8px;">3. Tracker learns</span>
    <span style="background:#14141A;border:1px solid #F5C451;border-radius:999px;padding:3px 8px;">4. See what cooked</span>
    </div>""", unsafe_allow_html=True)

    api_key = st.secrets.get("ODDS_API_KEY","") or st.text_input("Odds API Key", type="password")
    if not api_key:
        st.info("Add ODDS_API_KEY to secrets or paste above.")
        return

    c1, c2 = st.columns([1,4])
    with c1:
        sport = st.radio("Lane", ["NBA 🔮","NFL 🔥"], horizontal=True)
    with c2:
        if st.button("Pull the chaos 💅", type="primary", use_container_width=True, help="Pull the latest edges. Plus-money only."):
            sport_key = "basketball_nba" if "NBA" in str(sport) else "americanfootball_nfl"
            markets = "player_assists,player_assists_alternate,player_points,player_points_alternate,player_rebounds,player_rebounds_alternate,player_double_double" if "NBA" in str(sport) else "player_anytime_td,player_reception_yds,player_reception_yds_alternate"
            with st.spinner("Cooking your edges… hold on queen."):
                events = fetch_events(api_key, sport_key)
                st.session_state["debug_events"] = len(events)
                now = datetime.utcnow()
                pregame = []
                for ev in events:
                    ct = ev.get("commence_time")
                    if not ct: continue
                    try:
                        t = datetime.fromisoformat(ct.replace("Z","+00:00")).replace(tzinfo=None)
                        if t > now:
                            pregame.append(ev)
                    except: continue
                st.session_state["debug_pregame"] = len(pregame)
                # If no pre-game, fall back to all events so we can see data
                target = pregame if pregame else events
                all_plays = []
                book_count = 0
                market_count = 0
                sample = []
                for ev in target[:12]:
                    data = fetch_odds(api_key, sport_key, ev.get("id"), markets)
                    if data:
                        for b in data.get("bookmakers") or []:
                            book_count += 1
                            for m in b.get("markets") or []:
                                market_count += 1
                                bk_key = normalize_book(b.get("key"))
                                if bk_key in MY_BOOKS:
                                    for o in (m.get("outcomes") or [])[:2]:
                                        if len(sample) < 8:
                                            sample.append(f"{bk_key} {m.get('key')} {o.get('description')} {o.get('point')} @ {o.get('price')}")
                        all_plays.extend(parse_plays(data, sport))
                st.session_state["debug_plays"] = len(all_plays)
                st.session_state["debug_books"] = book_count
                st.session_state["debug_markets"] = market_count
                st.session_state["debug_sample"] = sample
                cards = best_cards(all_plays)
                st.session_state["cards"] = cards
                st.session_state["fetched"] = datetime.now().strftime("%H:%M")
                st.session_state["sport"] = sport
                # Auto-track TAKE plays — only append, never clear
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
                                "event": c["event"], "end": c.get("end"),
                                "bucket": odds_bucket(c["price"]),
                                "ev_gap": c.get("ev_gap"), "spike": c.get("spike"),
                                "vol": c.get("vol"), "move": c.get("move"),
                                "decision": c.get("decision"), "result": None
                            })
                            existing.add(key)
                            added += 1
                # Always save so the file stays current
                save_ledger(ledger)
                st.session_state["last_tracked"] = added
                # Auto-grade any finished games
                ledger, graded_n = auto_grade_nba(ledger)
                if graded_n:
                    save_ledger(ledger)
                    st.toast(f"Auto-graded {graded_n} plays")
                if added:
                    st.toast(f"Auto-tracked {added} TAKE plays")

    cards = st.session_state.get("cards") or []
    if st.session_state.get("fetched"):
        tracked = st.session_state.get("last_tracked", 0)
        dbg = f"events {st.session_state.get('debug_events',0)} · pregame {st.session_state.get('debug_pregame',0)} · books {st.session_state.get('debug_books',0)} · markets {st.session_state.get('debug_markets',0)} · plays {st.session_state.get('debug_plays',0)}"
        st.caption(f"Board pulled at {st.session_state['fetched']} — fresh edges only · {len(cards)} props · Tracking your chaos in real time 💅")
        sample = st.session_state.get("debug_sample") or []
        if sample:
            st.caption("Sample: " + " | ".join(sample))

    tab_board, tab_tracker, tab_how = st.tabs(["📊 Board","🔒 Tracker","💖 How It Works"])

    with tab_board:
        if not cards:
            st.info("Hit Fetch, baddie. The edges are waiting.")
            return
        f1,f2,f3 = st.columns(3)
        with f1:
            props = sorted({c["prop"] for c in cards})
            prop_f = st.multiselect("Prop", props, default=props)
        with f2:
            dec_f = st.multiselect("Decision", ["TAKE","LEAN","PASS"], default=["TAKE","LEAN"])
        with f3:
            min_odds = st.slider("Min Odds +300", 200, 2000, 300 if "NBA" in str(sport) else 200, 50)
        all_tags = sorted({t for c in cards for t in c.get("tags",[])})
        tag_f = st.multiselect("Tags", all_tags, default=[], help="Filter by Solo, Snap, Surge, Cluster, etc. Leave empty to show all.")

        filtered = [c for c in cards if c.get("prop") in prop_f and c.get("decision") in dec_f and int(c.get("price",0)) >= min_odds]
        if tag_f:
            filtered = [c for c in filtered if any(t in c.get("tags",[]) for t in tag_f)]
        filtered.sort(key=lambda x: (-x.get("spike",0), -x.get("ev_gap",0)))
        # TAKE Density
        vol_w = {"High": 1.0, "Medium": 0.7, "Low": 0.4}
        takes = [c for c in filtered if c.get("decision") == "TAKE"]
        weighted = 0.0
        for c in takes:
            ev = (c.get("ev_gap") or 0) / 100.0
            spike = c.get("spike") or 0
            vw = vol_w.get(c.get("vol"), 0.4)
            weighted += (ev * 0.5 + spike * 0.3) * vw
        density = (weighted / len(filtered) * 100) if filtered else 0
        if density > 25:
            status = "🔥 Hot Board — Books are panicking. Run it."
            mood = "Hot Board"
        elif density >= 10:
            status = "💅 Balanced Chaos — Edges exist, pick your battles."
            mood = "Balanced Chaos"
        else:
            status = "❄️ Cold Board — Books are comfy. Skip or wait."
            mood = "Cold Board"
        st.markdown(f"**TAKE Density: {density:.1f}%** · {status}")
        if density > 20:
            st.success(f"⚡ Edge Alert — TAKE Density spiked to {density:.0f}%. Chaos is live.")
        st.markdown(f"**{len(filtered)}** props · TAKE = big gap + movement. LEAN = softer. PASS = tight.")

        if not filtered:
            st.info("No props match.")
            return

        cols = st.columns(2)
        for i, c in enumerate(filtered[:24]):
            line_txt = f"o{c['line']}" if c["prop"] not in ("DoubleDouble","Anytime TD") else "Yes"
            tags_html = "".join(f'<span class="tag">{t}</span>' for t in c.get("tags",[]))
            boxes = []
            for bk, px in sorted(c.get("book_prices",{}).items(), key=lambda x: -x[1]):
                cls = "bk best" if bk == c["book"] else "bk"
                boxes.append(f'<div class="{cls}"><span>{bk}</span>{px:+d}</div>')
            boxes_html = "".join(boxes)
            dec_cls = c.get("decision","PASS").lower()
            with cols[i % 2]:
                card_cls = "card take-card" if c.get("decision")=="TAKE" else "card"
                take_tag = '<div class="take-tag">TAKE</div>' if c.get("decision")=="TAKE" else ""
                vol_icon = "⚡" if c.get("vol")=="High" else "✨" if c.get("vol")=="Medium" else ""
                move_icon = "💥" if c.get("move")=="Snap" else "🌙" if "Solo" in str(c.get("tags",[])) else ""
                vibe = "Run it." if c.get("decision")=="TAKE" else "Cute, but not worth the chaos." if c.get("decision")=="LEAN" else "Dead energy. Skip."
                html = (
                    f'<div class="{card_cls}">'
                    f'{take_tag}'
                    f'<div class="player">{c["player"]}</div>'
                    f'<div class="meta">{c["event"]}</div>'
                    f'<div class="prop">{c["prop"]} {line_txt}</div>'
                    f'<div class="books">{boxes_html}</div>'
                    f'{tags_html}'
                    f'<div class="why"><b>EV {c.get("ev_gap",0)}%</b> · <b>Spike {c.get("spike",0)}</b> · {vol_icon}{c.get("vol","")} · {move_icon}{c.get("move","")}</div>'
                    f'<div class="why" style="font-size:.62rem;opacity:.8;">{vibe}</div>'
                    f'<div class="decision {dec_cls}">{c.get("decision","PASS")} {"💖" if c.get("decision")=="TAKE" else "💜" if c.get("decision")=="LEAN" else "🩶"}</div>'
                    f'</div>'
                )
                st.markdown(html, unsafe_allow_html=True)
                if st.button("Lock 🔒", key=f"lk_{i}_{c['player']}_{c['prop']}_{c['line']}_{c['price']}"):
                    ledger = load_ledger()
                    ledger.append({"ts":datetime.now().isoformat(timespec="minutes"), "sport":c["sport"], "player":c["player"], "prop":c["prop"], "line":c["line"], "price":c["price"], "book":BOOK_FULL.get(c["book"],c["book"]), "event":c["event"], "end":c.get("end"), "bucket":odds_bucket(c["price"]), "ev_gap":c.get("ev_gap"), "spike":c.get("spike"), "vol":c.get("vol"), "move":c.get("move"), "decision":c.get("decision"), "result":None})
                    save_ledger(ledger)
                    st.toast("Locked")

    with tab_tracker:
        ledger = load_ledger()
        # Auto-grade on every Tracker load
        ledger, graded_n = auto_grade_nba(ledger)
        if graded_n:
            save_ledger(ledger)
            st.toast(f"Auto-graded {graded_n} plays")
        # Plays stay in your browser. No download needed.
        if st.button("Reset All Data 🧹"):
            save_ledger([])
            st.toast("Ledger cleared")
            st.rerun()
        if not ledger:
            st.info("Games still cooking — results drop soon 🔥")
        else:
            df = pd.DataFrame(ledger)
            st.subheader("Your Reads. Your Chaos. Your Hit Rates.")
            graded = df[df["result"].isin(["hit","miss"])]
            takes = len(df)
            hits = (graded["result"] == "hit").sum() if not graded.empty else 0
            misses = (graded["result"] == "miss").sum() if not graded.empty else 0
            hit_rate = (hits / len(graded) * 100) if len(graded) else 0
            density = (takes / max(takes, 1) * 100) if takes else 0
            vol_w = {"High": 1.0, "Medium": 0.7, "Low": 0.4}
            hit_chaos = 0.0
            total_chaos = 0.0
            for _, r in graded.iterrows():
                chaos = (r.get("ev_gap") or 0) * (r.get("spike") or 0) * vol_w.get(r.get("vol"), 0.4)
                total_chaos += chaos
                if r.get("result") == "hit":
                    hit_chaos += chaos
            w_hit = (hit_chaos / total_chaos * 100) if total_chaos else 0
            # Mini metric cards
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"""<div style="background:#14141A;border:1px solid #FF4DA6;border-radius:12px;padding:10px;text-align:center;">
                <div style="font-size:.7rem;color:#CBA6F7;">Hit Rate</div>
                <div style="font-size:1.4rem;font-weight:700;color:#F5C451;">{hit_rate:.0f}%</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div style="background:#14141A;border:1px solid #9B5FFF;border-radius:12px;padding:10px;text-align:center;">
                <div style="font-size:.7rem;color:#CBA6F7;">Weighted</div>
                <div style="font-size:1.4rem;font-weight:700;color:#CBA6F7;">{w_hit:.0f}%</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div style="background:#14141A;border:1px solid #FF4DA6;border-radius:12px;padding:10px;text-align:center;">
                <div style="font-size:.7rem;color:#CBA6F7;">TAKE Density</div>
                <div style="font-size:1.4rem;font-weight:700;color:#FF4DA6;">{density:.0f}%</div></div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;text-align:center;">
                <div style="font-size:.7rem;color:#CBA6F7;">TAKEs</div>
                <div style="font-size:1.4rem;font-weight:700;color:#fff;">{takes}</div></div>""", unsafe_allow_html=True)
            st.markdown(f"**{takes} TAKEs | {hits} HITs | {misses} MISSes → Hit Rate {hit_rate:.0f}% 💥**")
            # Chaos Meter
            chaos_score = min(100, density + (w_hit * 0.3))
            meter_color = "#FF4DA6" if chaos_score > 50 else "#9B5FFF" if chaos_score > 25 else "#4b5563"
            st.markdown(f"""<div style="margin:8px 0;">
            <div style="font-size:.75rem;color:#CBA6F7;margin-bottom:4px;">Chaos Meter</div>
            <div style="background:#262633;border-radius:999px;height:10px;overflow:hidden;">
            <div style="width:{chaos_score:.0f}%;height:100%;background:{meter_color};border-radius:999px;"></div>
            </div></div>""", unsafe_allow_html=True)
            # Volatility mix
            if "vol" in df.columns and not df.empty:
                vol_counts = df["vol"].value_counts()
                st.caption(f"🌪 Vol mix: High {vol_counts.get('High',0)} · Medium {vol_counts.get('Medium',0)} · Low {vol_counts.get('Low',0)}")
            rename = {
                "ts": "🕒 When Chaos Hit",
                "sport": "🏀 Lane",
                "player": "Player",
                "prop": "🎯 Prop",
                "line": "📈 Line",
                "price": "💸 Odds",
                "book": "Book",
                "event": "Matchup",
                "end": "Result Time",
                "bucket": "Odds Bucket",
                "ev_gap": "🔥 Edge %",
                "spike": "⚡ Spike",
                "vol": "🌪 Vol",
                "move": "💥 Move",
                "decision": "💖 Call",
                "result": "🎉 Result",
            }
            st.dataframe(df.rename(columns=rename), use_container_width=True, hide_index=True)
            if graded.empty:
                st.caption("Games still cooking — results drop soon 🔥")
            else:
                # Movement Hit Rate
                if "move" in graded.columns:
                    st.subheader("Movement Hit Rate")
                    g = graded.groupby("move").agg(n=("result","count"), hits=("result", lambda s: (s=="hit").sum()))
                    g["hit%"] = (g["hits"]/g["n"]*100).round(1)
                    st.bar_chart(g["hit%"])
                    st.dataframe(g.sort_values("hit%", ascending=False), use_container_width=True)
                # Book Hit Rate
                if "book" in graded.columns:
                    st.subheader("Book Hit Rate")
                    g = graded.groupby("book").agg(n=("result","count"), hits=("result", lambda s: (s=="hit").sum()))
                    g["hit%"] = (g["hits"]/g["n"]*100).round(1)
                    st.bar_chart(g["hit%"])
                    st.dataframe(g.sort_values("hit%", ascending=False), use_container_width=True)
                # EV Gap Hit Rate
                if "ev_gap" in graded.columns:
                    st.subheader("EV Gap Hit Rate")
                    graded["ev_bucket"] = pd.cut(graded["ev_gap"].fillna(0), bins=[-1,20,40,60,100,1000], labels=["0-20%","20-40%","40-60%","60-100%","100%+"])
                    g = graded.groupby("ev_bucket", observed=False).agg(n=("result","count"), hits=("result", lambda s: (s=="hit").sum()))
                    g["hit%"] = (g["hits"]/g["n"]*100).round(1)
                    st.bar_chart(g["hit%"])
                    st.dataframe(g, use_container_width=True)
                # Remaining breakdowns
                for title, col in [("By odds bucket","bucket"),("By ending","end"),("By volatility","vol"),("By decision","decision")]:
                    if col not in graded.columns: continue
                    st.subheader(title)
                    g = graded.groupby(col).agg(n=("result","count"), hits=("result", lambda s: (s=="hit").sum()))
                    g["hit%"] = (g["hits"]/g["n"]*100).round(1)
                    st.bar_chart(g["hit%"])
                    st.dataframe(g.sort_values("hit%", ascending=False), use_container_width=True)

    with tab_how:
        st.markdown("### How It Works")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**1. Fetch Board**")
            st.caption("Pre-game props only.")
        with c2:
            st.markdown("**2. Scan for TAKE**")
            st.caption("Pink cards with big EV gap and spike.")
        with c3:
            st.markdown("**3. Lock**")
            st.caption("Tracker learns what cashes.")
        st.markdown("### Glossary")
        st.markdown("""
- **EV gap**: How disrespectful the longest odds are compared to the rest.
- **Spike**: The chaos score. EV + movement + volatility.
- **Volatility**: How shaky the books are. High vol = books nervous.
- **Solo**: One book is out here alone. Rebels = edges.
- **Cluster**: Books holding hands. No edge.
- **Snap**: Sudden jump. Someone flinched.
- **Surge**: Strong move. Energy building.
- **Freeze**: No movement. Dead energy.
- **TAKE**: Run it. This is your play.
- **LEAN**: Cute but optional.
- **PASS**: Skip. No edge.
        """)


try:
    main()
except Exception as e:
    st.error(f"App error: {e}")
    st.exception(e)
