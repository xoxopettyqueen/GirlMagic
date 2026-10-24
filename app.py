# -*- coding: utf-8 -*-
"""
Girl Magic Odds 2.0
Open the site. It shows the edges. You lock them.
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
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;600;700&family=Pacifico&display=swap');
.stApp{background:#121212!important;background-image:radial-gradient(circle at 20% 30%,rgba(255,62,191,.08) 0%,transparent 50%),radial-gradient(circle at 80% 70%,rgba(199,125,255,.08) 0%,transparent 50%)!important;color:#fff!important;font-family:'Inter',sans-serif!important}
.hero{background:linear-gradient(90deg,#FF3EBF,#C77DFF,#7B2CBF)!important;border-radius:24px;padding:18px 22px;margin-bottom:14px;color:#fff;box-shadow:0 0 30px rgba(255,62,191,.4);animation:shimmerText 5s ease-in-out infinite}
.hero h1{margin:0;font-size:1.7rem;font-weight:700;font-family:'Playfair Display',serif;text-shadow:0 0 12px rgba(255,62,191,.8)}
.hero p{margin:4px 0 0;opacity:.9;font-size:.85rem;color:#F5E9FF;font-family:'Pacifico',cursive}
@keyframes shimmerText{0%,100%{filter:brightness(1)}50%{filter:brightness(1.2)}}
button[kind="primary"], .stButton > button[kind="primary"]{background:linear-gradient(90deg,#FF3EBF,#FF7AC4)!important;border:none!important;border-radius:999px!important;font-weight:700!important;box-shadow:0 0 20px rgba(255,62,191,.7)!important;color:#fff!important;padding:12px 24px!important}
.card{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:16px;padding:12px 14px;margin-bottom:12px;position:relative;transition:box-shadow .2s,transform .2s}
.card:hover{transform:translateY(-3px);box-shadow:0 12px 28px rgba(0,0,0,.8)}
.card.take-card{border-color:#FF3EBF;box-shadow:0 0 22px rgba(255,62,191,.6);animation:takePulse 3s ease-in-out infinite}
.card.true-ev-glow{border-color:#FF3EBF;box-shadow:0 0 28px rgba(255,62,191,.85);animation:takePulse 2.2s ease-in-out infinite}
@keyframes takePulse{0%,100%{box-shadow:0 0 18px rgba(255,62,191,.4)}50%{box-shadow:0 0 32px rgba(255,62,191,.9)}}
.player{font-size:1.05rem;font-weight:700;margin:0;font-family:'Playfair Display',serif}
.meta{color:#aaa;font-size:.68rem;margin:2px 0 6px}
.prop{font-size:.9rem;font-weight:600;color:#FF3EBF;margin-bottom:6px;text-transform:uppercase}
.books{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0}
.bk{background:#0f0f0f;border:1px solid #333;border-radius:999px;padding:4px 8px;text-align:center;min-width:60px;font-size:.7rem;font-weight:600}
.bk.best{border-color:#FF3EBF;box-shadow:0 0 10px rgba(255,62,191,.7)}
.tag{display:inline-block;background:rgba(199,125,255,.18);color:#F5E9FF;border:1px solid rgba(199,125,255,.6);border-radius:999px;padding:2px 8px;font-size:.6rem;font-weight:600;margin:2px 3px 0 0}
.decision{display:inline-block;border-radius:999px;padding:4px 12px;font-size:.72rem;font-weight:700;margin-top:6px}
.take{background:linear-gradient(90deg,#FF3EBF,#FF7AC4);color:#fff;box-shadow:0 0 14px rgba(255,62,191,.7)}
.lean{background:#C77DFF;color:#fff}
.pass{background:#444;color:#fff}
.why{font-size:.72rem;color:#F5E9FF;margin-top:6px}
.true-ev{font-size:.85rem;font-weight:700;color:#FF3EBF;margin:4px 0}
.take-tag{position:absolute;top:8px;right:10px;font-size:.58rem;letter-spacing:.12em;color:#FF3EBF;font-weight:700;text-transform:uppercase}
</style>
""", unsafe_allow_html=True)
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
LEDGER = Path("odds_ledger.json")
MY_BOOKS = {
    "fanduel":"FD","draftkings":"DK","betmgm":"MGM","bet365":"365",
    "williamhill_us":"CZR","fanatics":"FAN","espnbet":"SCR","hardrockbet":"HR",
    "hardrockbet_az":"HR","hardrockbet_oh":"HR","hardrockbet_fl":"HR",
    "pinnacle":"PIN","circa":"CIR","bookmaker":"BM",
}
BOOK_FULL = {"FD":"FanDuel","DK":"DraftKings","MGM":"BetMGM","365":"Bet365","CZR":"Caesars","FAN":"Fanatics","SCR":"theScore","HR":"Hard Rock","PIN":"Pinnacle","CIR":"Circa","BM":"Bookmaker"}
DEFAULT_WEIGHTS = {
    "PIN": 3.5, "CIR": 3.0, "BM": 2.8,
    "FD": 2.0, "DK": 1.8, "365": 2.0, "MGM": 1.4,
    "CZR": 1.3, "FAN": 1.2, "SCR": 1.1, "HR": 1.1,
}
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
def weighted_fair_prob(book_prices, weights=None):
    if weights is None: weights = DEFAULT_WEIGHTS
    weighted = []
    total_w = 0.0
    for bk, price in book_prices.items():
        w = weights.get(bk, 1.0)
        if w <= 0: continue
        imp = implied(price)
        if imp and 0 < imp < 1:
            weighted.append(imp * w)
            total_w += w
    if not weighted or total_w == 0: return None
    return max(0.03, min(0.97, sum(weighted) / total_w))
def compute_true_ev(best_price, fair_prob):
    if not fair_prob or best_price is None: return None
    try:
        decimal = (best_price / 100 + 1) if best_price > 0 else (100 / abs(best_price) + 1)
        return round((fair_prob * decimal - 1) * 100, 1)
    except: return None
def plain_reason(c):
    tev = c.get("true_ev") or 0
    if c.get("decision") == "TAKE" and tev >= 3:
        return "Strong edge. Books disagree and the fair price likes it. Run it."
    if c.get("decision") == "TAKE":
        return "Books are paying more than they should. Worth locking."
    if c.get("decision") == "LEAN":
        return "Soft edge. Only if you already like the play."
    return "Tight. Skip for now."
def normalize_book(key):
    k = str(key or "").lower()
    if "pinnacle" in k: return "pinnacle"
    if "circa" in k: return "circa"
    if "bookmaker" in k: return "bookmaker"
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
    browser = st.session_state.get("_browser_ledger")
    if browser is not None: return browser
    sess = st.session_state.get("ledger", [])
    file_data = []
    if LEDGER.exists():
        try: file_data = json.loads(LEDGER.read_text())
        except: file_data = []
    best = file_data if len(file_data) > len(sess) else sess
    st.session_state["ledger"] = best
    return best
def save_ledger(rows):
    st.session_state["ledger"] = rows
    st.session_state["_browser_ledger"] = rows
    try: LEDGER.write_text(json.dumps(rows, indent=2))
    except: pass
    st.components.v1.html(f"""
    <script>
    try {{ localStorage.setItem('gmo_ledger', {json.dumps(json.dumps(rows))}); }} catch(e) {{}}
    </script>
    """, height=0)
def restore_browser_ledger():
    if "_browser_checked" in st.session_state: return
    st.session_state["_browser_checked"] = True
    st.components.v1.html("""
    <script>
    try {
        const data = localStorage.getItem('gmo_ledger');
        if (data) window.parent.postMessage({type:'gmo_ledger', data: JSON.parse(data)}, '*');
    } catch(e) {}
    </script>
    """, height=0)
def auto_grade_nba(ledger):
    if not ledger: return ledger, 0
    graded = 0
    try:
        r = requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard", timeout=15)
        if r.status_code != 200: return ledger, 0
        events = r.json().get("events") or []
        player_stats = {}
        for ev in events:
            if not (ev.get("status") or {}).get("type", {}).get("completed"): continue
            eid = ev.get("id")
            if not eid: continue
            try:
                sr = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={eid}", timeout=15)
                if sr.status_code != 200: continue
                box = sr.json().get("boxscore") or {}
                for team in box.get("players") or []:
                    for stat_group in team.get("statistics") or []:
                        labels = [x.lower() for x in (stat_group.get("labels") or [])]
                        for ath in stat_group.get("athletes") or []:
                            name = (ath.get("athlete") or {}).get("displayName") or ""
                            stats = ath.get("stats") or []
                            if not name or not stats: continue
                            sdict = {}
                            for i, lab in enumerate(labels):
                                if i < len(stats):
                                    try: sdict[lab] = float(stats[i]) if stats[i] not in ("", "-") else 0
                                    except: sdict[lab] = 0
                            player_stats[name.lower()] = sdict
            except: continue
        for row in ledger:
            if row.get("result") or "NBA" not in str(row.get("sport", "")): continue
            player = (row.get("player") or "").lower()
            if not player: continue
            match = next((s for p, s in player_stats.items() if player in p or p in player), None)
            if not match: continue
            prop = row.get("prop")
            line = float(row.get("line") or 0)
            val = None
            if prop == "Assists": val = match.get("ast") or match.get("assists")
            elif prop == "Points": val = match.get("pts") or match.get("points")
            elif prop == "Rebounds": val = match.get("reb") or match.get("rebounds")
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
    except: pass
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
                    if prop_type=="Assists" and not (3.0<=line<=7.0): continue
                    if prop_type=="Points" and not (8.0<=line<=15.5): continue
                    if prop_type=="Rebounds" and not (4.0<=line<=10.0): continue
                    if prop_type!="DoubleDouble" and price<200: continue
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
def best_cards(plays, weights=None):
    by = defaultdict(list)
    for p in plays:
        key = (p["sport"], p["player"], p["prop"], round(p["line"],1), p["event"])
        by[key].append(p)
    cards = []
    for key, group in by.items():
        best = max(group, key=lambda x: x["price"])
        book_prices = {g["book"]: g["price"] for g in group}
        signals, decision = compute_signals(book_prices, best["price"])
        fair = weighted_fair_prob(book_prices, weights)
        true_ev = compute_true_ev(best["price"], fair)
        end = last_two(best["price"])
        tags = []
        if signals.get("book_beh")=="Solo": tags.append("Solo")
        if signals.get("book_beh")=="Cluster": tags.append("Cluster")
        if signals.get("move")=="Snap": tags.append("Snap")
        if signals.get("move")=="Drift": tags.append("Drift")
        if signals.get("move")=="Freeze": tags.append("Freeze")
        if signals.get("vol")=="High": tags.append("Surge")
        if end in HOT_ENDS: tags.append(f"Hot {end:02d}")
        if true_ev and true_ev >= 3: tags.append("True EV")
        cards.append({
            **best, "book_prices":book_prices, **signals, "end":end, "tags":tags,
            "decision":decision,
            "fair_prob": round(fair*100,1) if fair else None,
            "true_ev": true_ev,
        })
    cards.sort(key=lambda x: (-(x.get("true_ev") or -999), -x.get("spike",0)))
    return cards
def odds_bucket(price):
    if price < 600: return "+300–599"
    if price < 1500: return "+600–1499"
    if price < 4000: return "+1500–3999"
    return "+4000+"
def main():
    restore_browser_ledger()
    st.markdown('<div class="hero"><h1>✨ Girl Magic Odds 2.0</h1><p>Open the site. Edges appear. You lock them. 💅</p></div>', unsafe_allow_html=True)
    if "seen_onboard" not in st.session_state:
        st.info("👋 Open → Pull the chaos → Lock the glowing pink cards. That’s it. Flip Simple Mode off if you want every detail.")
        if st.button("Got it, let’s go"):
            st.session_state["seen_onboard"] = True
            st.rerun()
    api_key = st.secrets.get("ODDS_API_KEY","") or st.text_input("Odds API Key", type="password")
    if not api_key:
        st.info("Add your Odds API key above or in secrets.")
        return
    with st.sidebar:
        st.markdown("### 💅 Book Weights")
        st.caption("Higher = trust more. Leave alone if you want.")
        live_weights = {}
        for short in sorted(set(list(DEFAULT_WEIGHTS.keys()) + list(BOOK_FULL.keys()))):
            default = DEFAULT_WEIGHTS.get(short, 1.0)
            live_weights[short] = st.slider(short, 0.0, 5.0, float(default), 0.1, key=f"w_{short}")
    c1, c2 = st.columns([1,4])
    with c1:
        sport = st.radio("Lane", ["NBA 🔮","NFL 🔥"], horizontal=True)
    with c2:
        if st.button("Pull the chaos 💅", type="primary", use_container_width=True):
            sport_key = "basketball_nba" if "NBA" in str(sport) else "americanfootball_nfl"
            markets = "player_assists,player_assists_alternate,player_points,player_points_alternate,player_rebounds,player_rebounds_alternate,player_double_double" if "NBA" in str(sport) else "player_anytime_td,player_reception_yds,player_reception_yds_alternate"
            with st.spinner("Cooking your edges…"):
                events = fetch_events(api_key, sport_key)
                now = datetime.utcnow()
                pregame = [ev for ev in events if ev.get("commence_time") and datetime.fromisoformat(ev["commence_time"].replace("Z","+00:00")).replace(tzinfo=None) > now]
                target = pregame if pregame else events
                all_plays = []
                for ev in target[:20]:
                    data = fetch_odds(api_key, sport_key, ev.get("id"), markets)
                    if data: all_plays.extend(parse_plays(data, sport))
                cards = best_cards(all_plays, live_weights)
                st.session_state["cards"] = cards
                st.session_state["fetched"] = datetime.now().strftime("%H:%M")
                st.session_state["sport"] = sport
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
                                "true_ev": c.get("true_ev"), "fair_prob": c.get("fair_prob"),
                                "vol": c.get("vol"), "move": c.get("move"),
                                "decision": c.get("decision"), "result": None
                            })
                            existing.add(key)
                            added += 1
                save_ledger(ledger)
                if added: st.toast(f"Auto-tracked {added} TAKE plays")
                ledger, graded_n = auto_grade_nba(ledger)
                if graded_n:
                    save_ledger(ledger)
                    st.toast(f"Auto-graded {graded_n} plays")
    cards = st.session_state.get("cards") or []
    if st.session_state.get("fetched"):
        st.caption(f"Board live @ {st.session_state['fetched']} — {len(cards)} props")
    tab_board, tab_tracker, tab_how = st.tabs(["📊 Board","🔒 Tracker","💖 How It Works"])
    with tab_board:
        if not cards:
            st.info("Hit **Pull the chaos**. The edges will show up here.")
            return
        simple_mode = st.toggle("✨ Simple Mode (recommended)", value=True)
        if simple_mode:
            filtered = [c for c in cards if c.get("decision") == "TAKE" and (c.get("true_ev") or 0) >= 2]
            st.markdown("**Showing only the strongest edges.** Glowing pink = lock it.")
        else:
            f1, f2, f3 = st.columns(3)
            with f1:
                props = sorted({c["prop"] for c in cards})
                prop_f = st.multiselect("Prop", props, default=props)
            with f2:
                dec_f = st.multiselect("Decision", ["TAKE","LEAN","PASS"], default=["TAKE","LEAN"])
            with f3:
                min_odds = st.slider("Min Odds", 200, 2000, 300 if "NBA" in str(sport) else 200, 50)
            min_true_ev = st.slider("Min True EV %", -10.0, 20.0, -5.0, 0.5)
            filtered = [c for c in cards if c.get("prop") in prop_f and c.get("decision") in dec_f and int(c.get("price",0)) >= min_odds and (c.get("true_ev") or -999) >= min_true_ev]
            filtered.sort(key=lambda x: (-(x.get("true_ev") or -999), -x.get("spike",0)))
        if not filtered:
            st.info("No strong edges right now. Books are tight. Pull again in a bit.")
            return
        st.markdown(f"**{len(filtered)} plays ready.**")
        cols = st.columns(2)
        for i, c in enumerate(filtered[:24]):
            line_txt = f"o{c['line']}" if c["prop"] not in ("DoubleDouble","Anytime TD") else "Yes"
            boxes_html = "".join(
                f'<div class="bk {"best" if bk == c["book"] else ""}"><span>{bk}</span>{px:+d}</div>'
                for bk, px in sorted(c.get("book_prices",{}).items(), key=lambda x: -x[1])
            )
            card_cls = "card"
            if c.get("decision") == "TAKE": card_cls += " take-card"
            if (c.get("true_ev") or 0) >= 3 and c.get("decision") == "TAKE": card_cls += " true-ev-glow"
            take_tag = '<div class="take-tag">TAKE</div>' if c.get("decision") == "TAKE" else ""
            true_ev_html = f'<div class="true-ev">True EV {c.get("true_ev","—")}%</div>' if c.get("true_ev") is not None else ""
            html = (
                f'<div class="{card_cls}">{take_tag}'
                f'<div class="player">{c["player"]}</div>'
                f'<div class="meta">{c["event"]}</div>'
                f'<div class="prop">{c["prop"]} {line_txt}</div>'
                f'<div class="books">{boxes_html}</div>'
                f'{true_ev_html}'
                f'<div class="why">{plain_reason(c)}</div>'
                f'</div>'
            )
            with cols[i % 2]:
                st.markdown(html, unsafe_allow_html=True)
                if st.button("Lock 🔒", key=f"lk_{i}_{c['player']}_{c['prop']}_{c['line']}"):
                    ledger = load_ledger()
                    ledger.append({
                        "ts": datetime.now().isoformat(timespec="minutes"),
                        "sport": c["sport"], "player": c["player"], "prop": c["prop"],
                        "line": c["line"], "price": c["price"],
                        "book": BOOK_FULL.get(c["book"], c["book"]),
                        "event": c["event"], "true_ev": c.get("true_ev"),
                        "decision": c.get("decision"), "result": None
                    })
                    save_ledger(ledger)
                    st.toast("Locked. Check Tracker to see how it does.")
    with tab_tracker:
        ledger = load_ledger()
        ledger, graded_n = auto_grade_nba(ledger)
        if graded_n:
            save_ledger(ledger)
            st.toast(f"Auto-graded {graded_n} plays")
        if st.button("Wipe the slate"):
            save_ledger([])
            st.rerun()
        if not ledger:
            st.info("Nothing locked yet. Pull the chaos and lock some plays.")
        else:
            df = pd.DataFrame(ledger)
            graded = df[df["result"].isin(["hit","miss"])] if "result" in df.columns else pd.DataFrame()
            hits = (graded["result"] == "hit").sum() if not graded.empty else 0
            total_graded = len(graded)
            hit_rate = (hits / total_graded * 100) if total_graded else 0
            st.markdown(f"**You’ve locked {len(df)} plays.** {total_graded} finished. **{hit_rate:.0f}% hit.**")
            st.dataframe(df, use_container_width=True, hide_index=True)
    with tab_how:
        st.markdown("""
        ### How it works
        1. Hit **Pull the chaos**.
        2. The glowing pink cards are the strongest edges.
        3. Hit **Lock** on the ones you want.
        4. Check the Tracker later.
        **True EV** = how much better the price is than the blended fair price.  
        **TAKE** = the books are disagreeing hard.  
        When both are good, that’s the play.
        """)
try:
    main()
except Exception as e:
    st.error(f"App error: {e}")
    st.exception(e)
