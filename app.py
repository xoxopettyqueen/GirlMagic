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
    if "ledger" in st.session_state:
        return st.session_state["ledger"]
    if LEDGER.exists():
        try:
            data = json.loads(LEDGER.read_text())
            st.session_state["ledger"] = data
            return data
        except: return []
    return []

def save_ledger(rows):
    st.session_state["ledger"] = rows
    try: LEDGER.write_text(json.dumps(rows, indent=2))
    except: pass

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
                    if prop_type!="DoubleDouble" and price<750: continue
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
    st.markdown('<div class="hero"><h1>✨ Girl Magic Odds 2.0</h1><p>Odds Only. Chaos Powered. Plus-Money Forever.</p></div>', unsafe_allow_html=True)

    api_key = st.secrets.get("ODDS_API_KEY","") or st.text_input("Odds API Key", type="password")
    if not api_key:
        st.info("Add ODDS_API_KEY to secrets or paste above.")
        return

    c1, c2 = st.columns([1,4])
    with c1:
        sport = st.radio("Lane", ["NBA 🔮","NFL 🔥"], horizontal=True)
    with c2:
        if st.button("Fetch the Board 💅", type="primary", use_container_width=True):
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
                for ev in target[:12]:
                    data = fetch_odds(api_key, sport_key, ev.get("id"), markets)
                    if data:
                        for b in data.get("bookmakers") or []:
                            book_count += 1
                            for m in b.get("markets") or []:
                                market_count += 1
                        all_plays.extend(parse_plays(data, sport))
                st.session_state["debug_plays"] = len(all_plays)
                st.session_state["debug_books"] = book_count
                st.session_state["debug_markets"] = market_count
                cards = best_cards(all_plays)
                st.session_state["cards"] = cards
                st.session_state["fetched"] = datetime.now().strftime("%H:%M")
                st.session_state["sport"] = sport
                # Auto-track TAKE plays
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
                if added:
                    save_ledger(ledger)
                    st.session_state["last_tracked"] = added
                    st.toast(f"Auto-tracked {added} TAKE plays")
                else:
                    st.session_state["last_tracked"] = 0

    cards = st.session_state.get("cards") or []
    if st.session_state.get("fetched"):
        tracked = st.session_state.get("last_tracked", 0)
        dbg = f"events {st.session_state.get('debug_events',0)} · pregame {st.session_state.get('debug_pregame',0)} · books {st.session_state.get('debug_books',0)} · markets {st.session_state.get('debug_markets',0)} · plays {st.session_state.get('debug_plays',0)}"
        st.caption(f"Fetched {st.session_state['fetched']} · {len(cards)} props · Auto-tracked {tracked} TAKE plays · {dbg}")

    tab_board, tab_tracker, tab_how = st.tabs(["Board","Tracker","How It Works"])

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
            min_odds = st.slider("Min Odds +750", 300, 2000, 750 if "NBA" in str(sport) else 300, 50)

        filtered = [c for c in cards if c.get("prop") in prop_f and c.get("decision") in dec_f and int(c.get("price",0)) >= min_odds]
        filtered.sort(key=lambda x: (-x.get("spike",0), -x.get("ev_gap",0)))
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
        if not ledger:
            st.info("Your reads. Your chaos. Your hit rates. Lock a play from the Board to start.")
        else:
            df = pd.DataFrame(ledger)
            st.subheader("Your Reads. Your Chaos. Your Hit Rates.")
            st.dataframe(df, use_container_width=True, hide_index=True)
            graded = df[df["result"].notna()]
            if graded.empty:
                st.caption("No graded results yet. Once results are marked, hit rates will show below.")
            else:
                for title, col in [("By odds bucket","bucket"),("By ending","end"),("By book","book"),("By movement","move"),("By volatility","vol"),("By decision","decision")]:
                    if col not in graded.columns: continue
                    st.subheader(title)
                    g = graded.groupby(col).agg(n=("result","count"), hits=("result", lambda s: (s=="hit").sum()))
                    g["hit%"] = (g["hits"]/g["n"]*100).round(1)
                    st.bar_chart(g["hit%"])
                    st.dataframe(g.sort_values("hit%", ascending=False), use_container_width=True)

    with tab_how:
        st.markdown("""
        <div style="padding:16px 0;">
          <h3 style="font-family:'Playfair Display',serif;color:#fff;margin-bottom:12px;">How It Works</h3>
          <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;">
            <div style="flex:1;min-width:180px;background:linear-gradient(135deg,#FF4DA6,#9B5FFF);border-radius:16px;padding:14px;color:#fff;">
              <div style="font-size:1.4rem;">🎯</div>
              <div style="font-weight:700;margin-top:6px;">1. Fetch Board</div>
              <div style="font-size:.8rem;opacity:.9;">Pre-game props only.</div>
            </div>
            <div style="flex:1;min-width:180px;background:linear-gradient(135deg,#9B5FFF,#5E4AE3);border-radius:16px;padding:14px;color:#fff;">
              <div style="font-size:1.4rem;">💖</div>
              <div style="font-weight:700;margin-top:6px;">2. Scan for TAKE</div>
              <div style="font-size:.8rem;opacity:.9;">Pink cards with big EV gap and spike.</div>
            </div>
            <div style="flex:1;min-width:180px;background:linear-gradient(135deg,#5E4AE3,#FF4DA6);border-radius:16px;padding:14px;color:#fff;">
              <div style="font-size:1.4rem;">🔒</div>
              <div style="font-weight:700;margin-top:6px;">3. Lock</div>
              <div style="font-size:.8rem;opacity:.9;">Tracker learns what cashes.</div>
            </div>
          </div>
          <h3 style="font-family:'Playfair Display',serif;color:#fff;margin-bottom:12px;">Glossary</h3>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px;">
            <div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;"><b style="color:#FF4DA6;">EV gap</b><br><span style="font-size:.75rem;color:#B3B3C3;">How much better the longest odds are vs the median.</span></div>
            <div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;"><b style="color:#FF4DA6;">Longest price</b><br><span style="font-size:.75rem;color:#B3B3C3;">The best number on the board.</span></div>
            <div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;"><b style="color:#FF4DA6;">Median</b><br><span style="font-size:.75rem;color:#B3B3C3;">The normal price most books agree on.</span></div>
            <div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;"><b style="color:#FF4DA6;">Volatility</b><br><span style="font-size:.75rem;color:#B3B3C3;">How much the odds wiggle. High = chaos.</span></div>
            <div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;"><b style="color:#FF4DA6;">Spike</b><br><span style="font-size:.75rem;color:#B3B3C3;">EV gap + volatility + movement. Big = real edge.</span></div>
            <div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;"><b style="color:#FF4DA6;">Solo</b><br><span style="font-size:.75rem;color:#B3B3C3;">One book stands alone.</span></div>
            <div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;"><b style="color:#FF4DA6;">Cluster</b><br><span style="font-size:.75rem;color:#B3B3C3;">Books agree tightly.</span></div>
            <div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;"><b style="color:#FF4DA6;">Snap</b><br><span style="font-size:.75rem;color:#B3B3C3;">Sudden jump.</span></div>
            <div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;"><b style="color:#FF4DA6;">Drift</b><br><span style="font-size:.75rem;color:#B3B3C3;">Slow movement.</span></div>
            <div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;"><b style="color:#FF4DA6;">Freeze</b><br><span style="font-size:.75rem;color:#B3B3C3;">No movement.</span></div>
            <div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;"><b style="color:#FF4DA6;">TAKE</b><br><span style="font-size:.75rem;color:#B3B3C3;">Bet it.</span></div>
            <div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;"><b style="color:#FF4DA6;">LEAN</b><br><span style="font-size:.75rem;color:#B3B3C3;">Interesting but not must-bet.</span></div>
            <div style="background:#14141A;border:1px solid #262633;border-radius:12px;padding:10px;"><b style="color:#FF4DA6;">PASS</b><br><span style="font-size:.75rem;color:#B3B3C3;">Skip it.</span></div>
          </div>
          <div style="text-align:center;margin-top:20px;color:#CBA6F7;font-size:.8rem;font-style:italic;opacity:.8;">Built for the girls who read odds like poetry.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="text-align:center;margin-top:24px;color:#a78bfa;font-size:.75rem;font-style:italic;">Built for the girls who read odds like poetry.</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
