# -*- coding: utf-8 -*-
"""
Girl Magic Odds 2.0 — Clean Chaos
Less top noise. Glossary back. Petty Mode does the filtering. No Compact.
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
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600;700&family=Pacifico&display=swap');
.stApp{background:#0c0c10!important;color:#fff!important;font-family:'Inter',sans-serif!important}
.hero{background:linear-gradient(90deg,#FF3EBF,#C77DFF,#7B2CBF)!important;border-radius:20px;padding:18px 22px;margin-bottom:12px;color:#fff;box-shadow:0 0 28px rgba(255,62,191,.4);animation:pulseBar 6s linear infinite}
@keyframes pulseBar{0%,100%{filter:brightness(1)}50%{filter:brightness(1.12)}}
.hero h1{margin:0;font-size:1.75rem;font-weight:700;font-family:'Inter',sans-serif;text-shadow:0 0 10px rgba(255,215,0,.45)}
.hero p{margin:4px 0 0;opacity:.95;font-size:1.05rem;color:#F5E9FF;font-family:'Pacifico',cursive;text-shadow:0 0 8px rgba(199,125,255,.6)}
button[kind="primary"], .stButton > button[kind="primary"]{background:linear-gradient(90deg,#FF3EBF,#FF7AC4)!important;border:none!important;border-radius:999px!important;font-weight:700!important;min-height:44px}
.card{background:linear-gradient(180deg,rgba(21,21,27,.95) 0%,rgba(16,16,20,.95) 100%);border:1px solid #2a2a33;border-radius:14px;padding:11px 13px;margin-bottom:10px;position:relative;transition:box-shadow .4s ease-in-out,transform .3s}
.card:hover{transform:translateY(-2px);box-shadow:0 0 22px rgba(255,62,191,.55)}
.card.take-card{border-color:#FF3EBF;box-shadow:0 0 16px rgba(255,62,191,.5)}
.card.true-ev-glow{border-color:#FF3EBF;box-shadow:0 0 22px rgba(255,62,191,.75)}
.card.dimmed{opacity:0.65;border-color:#5a4a6a}
.player{font-size:1.15rem;font-weight:700;margin:0;font-family:'Inter',sans-serif}
.meta{color:#aaa;font-size:.65rem;margin:2px 0 4px}
.prop{font-size:.85rem;font-weight:600;color:#FF3EBF;margin-bottom:4px;text-transform:uppercase}
.books{display:flex;flex-wrap:wrap;gap:4px;margin:4px 0}
.bk{background:#0d0d12;border:1px solid #333;border-radius:999px;padding:3px 7px;text-align:center;min-width:50px;font-size:.64rem;font-weight:600;color:#fff}
.bk.best{border-color:#FF3EBF;box-shadow:0 0 8px rgba(255,62,191,.6)}
.true-ev{font-size:.9rem;font-weight:700;color:#FF3EBF;margin:3px 0;text-shadow:0 0 6px rgba(255,62,191,.4)}
.why{font-size:.72rem;color:#e0d4f5;margin-top:4px;line-height:1.3;max-width:90%}
.take-tag{position:absolute;top:6px;right:8px;font-size:.55rem;letter-spacing:.1em;color:#FF3EBF;font-weight:700}
.tag{display:inline-block;background:rgba(199,125,255,.15);color:#F5E9FF;border:1px solid rgba(199,125,255,.4);border-radius:999px;padding:1px 6px;font-size:.55rem;margin:2px 2px 0 0}
.tag.range{background:rgba(255,62,191,.2);border-color:#FF3EBF}
.glossary{font-size:.75rem;color:#ddd;margin-top:20px;padding:12px 14px;background:#111118;border-radius:10px;border:1px solid #2a2a33}
.glossary b{color:#FF3EBF}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
LEDGER = Path("odds_ledger.json")
SHARPNESS = Path("book_sharpness.json")
WEIGHTS_FILE = Path("auto_weights.json")

MY_BOOKS = {
    "fanduel":"FD","draftkings":"DK","betmgm":"MGM","bet365":"365",
    "williamhill_us":"CZR","fanatics":"FAN","espnbet":"SCR","hardrockbet":"HR",
    "hardrockbet_az":"HR","hardrockbet_oh":"HR","hardrockbet_fl":"HR",
    "pinnacle":"PIN","circa":"CIR","bookmaker":"BM",
}
BOOK_FULL = {"FD":"FanDuel","DK":"DraftKings","MGM":"BetMGM","365":"Bet365","CZR":"Caesars","FAN":"Fanatics","SCR":"theScore","HR":"Hard Rock","PIN":"Pinnacle","CIR":"Circa","BM":"Bookmaker"}

BASE_WEIGHTS = {
    "PIN": 3.5, "CIR": 3.0, "BM": 2.8,
    "FD": 2.0, "DK": 1.8, "365": 2.0, "MGM": 1.4,
    "CZR": 1.3, "FAN": 1.2, "SCR": 1.1, "HR": 1.1,
}

GLOSSARY = """
**Glossary**  
- **True EV**: Expected value vs the weighted fair price.  
- **Fair price**: No-vig probability after blending book weights.  
- **EV Gap**: How much longer the best price is vs the median.  
- **Spike**: Chaos score combining gap + movement + volatility.  
- **Volatility**: How far apart the books are right now.  
- **Solo / Cluster**: One book alone vs books clustered.  
- **Weak-spot**: Book that repeatedly hangs soft numbers.  
- **Petty Mode**: Only your preferred line ranges (Assists 3–8, Points 8–15, Rebounds 4–10).  
- **Auto Weights**: The app learns which books are soft and adjusts trust automatically.  
"""

def in_user_range(prop, line):
    if prop == "Assists": return 3 <= line <= 8
    if prop == "Points": return 8 <= line <= 15
    if prop == "Rebounds": return 4 <= line <= 10
    if prop in ("DoubleDouble", "Anytime TD"): return True
    return False

def load_sharpness():
    if SHARPNESS.exists():
        try: return json.loads(SHARPNESS.read_text())
        except: pass
    return {}

def save_sharpness(data):
    try: SHARPNESS.write_text(json.dumps(data, indent=2))
    except: pass

def load_auto_weights():
    if WEIGHTS_FILE.exists():
        try: return json.loads(WEIGHTS_FILE.read_text())
        except: pass
    return BASE_WEIGHTS.copy()

def save_auto_weights(w):
    try: WEIGHTS_FILE.write_text(json.dumps(w, indent=2))
    except: pass

def update_auto_weights(sharp):
    current = load_auto_weights()
    for bk, data in sharp.items():
        total = data.get("total", 0)
        soft = data.get("soft_count", 0)
        if total < 10: continue
        soft_rate = soft / total
        base = BASE_WEIGHTS.get(bk, 1.0)
        if soft_rate > 0.25:
            current[bk] = max(0.8, round(base * 0.75, 2))
        elif soft_rate > 0.15:
            current[bk] = max(0.9, round(base * 0.85, 2))
        else:
            current[bk] = round(min(3.5, base * 1.05), 2)
    save_auto_weights(current)
    return current

def implied(price):
    try:
        p = int(price)
        return 100/(p+100) if p > 0 else abs(p)/(abs(p)+100)
    except: return None

def weighted_fair_prob(book_prices, weights=None):
    if weights is None: weights = load_auto_weights()
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
    fair = sum(weighted) / total_w
    return max(0.08, min(0.75, fair))

def compute_true_ev(best_price, fair_prob):
    if not fair_prob or best_price is None: return None
    try:
        decimal = (best_price / 100 + 1) if best_price > 0 else (100 / abs(best_price) + 1)
        ev = (fair_prob * decimal - 1) * 100
        return round(max(-15, min(18, ev)), 1)
    except: return None

def plain_reason(c):
    tev = c.get("true_ev") or 0
    bk = c.get("book", "")
    if c.get("decision") == "TAKE" and tev >= 3:
        return f"Strong edge. {bk} is hanging a soft number vs the blend."
    if c.get("decision") == "TAKE":
        return f"Books disagree. {bk} is the longest."
    return "Tight. Skip."

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
    if "betmgm" in k or k == "mgm": return "betmgm"
    if "williamhill" in k or "caesar" in k: return "williamhill_us"
    return k

def load_ledger():
    if LEDGER.exists():
        try: return json.loads(LEDGER.read_text())
        except: pass
    return st.session_state.get("ledger", [])

def save_ledger(rows):
    st.session_state["ledger"] = rows
    try: LEDGER.write_text(json.dumps(rows, indent=2))
    except: pass

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
        r = requests.get(f"{ODDS_API_BASE}/sports/{sport_key}/events/{event_id}/odds",
            params={"apiKey": api_key, "regions": "us,us2,uk", "markets": markets, "oddsFormat": "american"}, timeout=20)
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
            if "NBA" in str(sport):
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
                try: price = int(o.get("price"))
                except: continue
                plays.append({"sport": sport, "event": event, "player": player, "prop": prop_type, "line": line, "price": price, "book": short})
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
    spike = ev_gap + (0.3 if vol == "High" else 0.15 if vol == "Medium" else 0.05) * spread
    if spike > 0.25 and vol != "Low": decision = "TAKE"
    elif spike > 0.08: decision = "LEAN"
    else: decision = "PASS"
    return {
        "median": int(med), "longest": longest, "ev_gap": round(ev_gap*100, 1),
        "vol": vol, "move": move, "book_beh": book_beh, "spike": round(spike, 2),
        "decision": decision,
    }, decision

def update_sharpness(cards):
    sharp = load_sharpness()
    for c in cards:
        bk = c.get("book")
        if not bk: continue
        if bk not in sharp: sharp[bk] = {"soft_count": 0, "total": 0, "props": {}}
        sharp[bk]["total"] += 1
        if c.get("decision") == "TAKE" and (c.get("true_ev") or 0) >= 2:
            sharp[bk]["soft_count"] += 1
            prop = c.get("prop", "Other")
            sharp[bk]["props"][prop] = sharp[bk]["props"].get(prop, 0) + 1
    save_sharpness(sharp)
    return sharp

def best_cards(plays, weights=None):
    by = defaultdict(list)
    for p in plays:
        key = (p["sport"], p["player"], p["prop"], round(p["line"], 1), p["event"])
        by[key].append(p)
    cards = []
    sharp = load_sharpness()
    for key, group in by.items():
        best = max(group, key=lambda x: x["price"])
        book_prices = {g["book"]: g["price"] for g in group}
        signals, decision = compute_signals(book_prices, best["price"])
        fair = weighted_fair_prob(book_prices, weights)
        true_ev = compute_true_ev(best["price"], fair)
        petty = in_user_range(best["prop"], best["line"])
        tags = []
        if signals.get("book_beh") == "Solo": tags.append("Solo")
        if signals.get("move") == "Snap": tags.append("Snap")
        if signals.get("vol") == "High": tags.append("Surge")
        bk = best["book"]
        if bk in sharp and sharp[bk]["soft_count"] >= 3:
            tags.append(f"{bk} soft")
        if true_ev and true_ev >= 3: tags.append("True EV")
        if petty:
            tags.append("In range")
        else:
            tags.append("Outside range")
        cards.append({
            **best, "book_prices": book_prices, **signals, "tags": tags,
            "decision": decision,
            "fair_prob": round(fair*100, 1) if fair else None,
            "true_ev": true_ev,
            "one_sided": True,
            "petty_range_match": petty,
            "devig_method": "multiplicative",
        })
    cards.sort(key=lambda x: (-(x.get("true_ev") or -999), -x.get("spike", 0)))
    return cards

def render_softness(sharp):
    if not sharp: return
    rows = []
    for bk, data in sharp.items():
        total = data.get("total", 0)
        soft = data.get("soft_count", 0)
        pct = round((soft / total * 100), 1) if total else 0
        props = data.get("props", {})
        top_prop = max(props, key=props.get) if props else "—"
        rows.append({"Book": bk, "Soft Count": soft, "Total": total, "% Soft": pct, "Top Soft Prop": top_prop})
    if rows:
        df = pd.DataFrame(rows).sort_values("% Soft", ascending=False)
        st.subheader("Book Softness")
        st.dataframe(df, use_container_width=True, hide_index=True)

def main():
    st.markdown('<div class="hero"><h1>✨ Girl Magic Odds 2.0</h1><p>Open the site. Edges appear. You lock them. 💅</p></div>', unsafe_allow_html=True)

    api_key = st.secrets.get("ODDS_API_KEY", "") or st.text_input("Odds API Key", type="password")
    if not api_key:
        st.info("Add your Odds API key.")
        return

    auto_weights = load_auto_weights()

    with st.sidebar:
        st.markdown("### 💅 Book Weights (auto)")
        st.caption("Updated automatically. Override only if you want.")
        live_weights = {}
        for short in sorted(set(list(BASE_WEIGHTS.keys()) + list(BOOK_FULL.keys()))):
            default = auto_weights.get(short, BASE_WEIGHTS.get(short, 1.0))
            live_weights[short] = st.slider(short, 0.5, 4.0, float(default), 0.1, key=f"w_{short}")
        if st.button("Reset weights to auto"):
            save_auto_weights(BASE_WEIGHTS.copy())
            st.rerun()

    c1, c2 = st.columns([1, 4])
    with c1:
        sport = st.radio("Lane", ["NBA 🔮", "NFL 🔥"], horizontal=True)
    with c2:
        if st.button("Pull the chaos 💅", type="primary", use_container_width=True):
            sport_key = "basketball_nba" if "NBA" in str(sport) else "americanfootball_nfl"
            markets = "player_assists,player_assists_alternate,player_points,player_points_alternate,player_rebounds,player_rebounds_alternate,player_double_double" if "NBA" in str(sport) else "player_anytime_td,player_reception_yds,player_reception_yds_alternate"
            with st.spinner("Pulling edges…"):
                events = fetch_events(api_key, sport_key)
                now = datetime.utcnow()
                pregame = [ev for ev in events if ev.get("commence_time") and datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00")).replace(tzinfo=None) > now]
                target = pregame if pregame else events
                all_plays = []
                for ev in target[:15]:
                    data = fetch_odds(api_key, sport_key, ev.get("id"), markets)
                    if data: all_plays.extend(parse_plays(data, sport))
                cards = best_cards(all_plays, live_weights)
                sharp = update_sharpness(cards)
                update_auto_weights(sharp)
                st.session_state["cards"] = cards
                st.session_state["fetched"] = datetime.now().strftime("%H:%M")
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
                                "event": c["event"],
                                "true_ev": c.get("true_ev"),
                                "fair_prob": c.get("fair_prob"),
                                "decision": c.get("decision"),
                                "petty_range_match": c.get("petty_range_match"),
                                "result": None,
                                "clv": None,
                                "locked_price": c["price"],
                                "petty_mode": st.session_state.get("petty_mode", True),
                            })
                            existing.add(key)
                            added += 1
                save_ledger(ledger)
                if added: st.toast(f"Auto-tracked {added} TAKE plays")
                st.toast("Weights auto-tuned")

    cards = st.session_state.get("cards") or []
    if st.session_state.get("fetched"):
        st.caption(f"Board live @ {st.session_state['fetched']} — {len(cards)} props")

    tab_board, tab_tracker = st.tabs(["📊 Board", "🔒 Tracker"])

    with tab_board:
        if not cards:
            st.info("Hit **Pull the chaos**.")
            return

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            simple_mode = st.toggle("✨ Simple Mode", value=st.session_state.get("simple_mode", True))
            st.session_state["simple_mode"] = simple_mode
        with col_b:
            detailed = st.toggle("🔍 Detailed", value=st.session_state.get("detailed", False))
            st.session_state["detailed"] = detailed
        with col_c:
            petty_mode = st.toggle("💅 Petty Mode", value=st.session_state.get("petty_mode", True))
            st.session_state["petty_mode"] = petty_mode

        prop_filter = st.multiselect(
            "Prop Type",
            ["Assists", "Points", "Rebounds", "DoubleDouble", "Anytime TD"],
            default=["Assists", "Points", "Rebounds", "DoubleDouble", "Anytime TD"]
        )

        if simple_mode and petty_mode:
            filtered = [
                c for c in cards
                if c.get("decision") == "TAKE"
                and (c.get("true_ev") or 0) >= 2
                and c.get("petty_range_match")
                and c.get("prop") in prop_filter
            ]
            st.markdown("**Your preferred ranges only.**")
        elif simple_mode:
            filtered = [c for c in cards if c.get("decision") == "TAKE" and (c.get("true_ev") or 0) >= 2 and c.get("prop") in prop_filter]
            st.markdown("**Strongest edges.**")
        else:
            filtered = [c for c in cards if c.get("prop") in prop_filter]
            st.markdown("**All props — preferred ranges highlighted.**")

        if not filtered:
            st.info("No matching edges right now.")
            return

        st.markdown(f"**{len(filtered)} plays ready.**")

        cols = st.columns(2)
        for i, c in enumerate(filtered[:24]):
            line_txt = f"o{c['line']}" if c["prop"] not in ("DoubleDouble", "Anytime TD") else "Yes"
            boxes_html = "".join(
                f'<div class="bk {"best" if bk == c["book"] else ""}"><span>{bk}</span>{px:+d}</div>'
                for bk, px in sorted(c.get("book_prices", {}).items(), key=lambda x: -x[1])
            )
            tags_html = "".join(
                f'<span class="tag {"range" if "range" in t.lower() else ""}">{t}</span>'
                for t in c.get("tags", [])
            ) if not simple_mode else ""
            card_cls = "card"
            if c.get("decision") == "TAKE": card_cls += " take-card"
            if (c.get("true_ev") or 0) >= 3 and c.get("decision") == "TAKE": card_cls += " true-ev-glow"
            if not c.get("petty_range_match") and not simple_mode:
                card_cls += " dimmed"
            take_tag = '<div class="take-tag">TAKE</div>' if c.get("decision") == "TAKE" else ""
            html = (
                f'<div class="{card_cls}">{take_tag}'
                f'<div class="player">{c["player"]}</div>'
                f'<div class="meta">{c["event"]}</div>'
                f'<div class="prop">{c["prop"]} {line_txt}</div>'
                f'<div class="books">{boxes_html}</div>'
                f'{tags_html}'
                f'<div class="true-ev">True EV {c.get("true_ev", "—")}%</div>'
                f'<div class="why">{plain_reason(c)}</div>'
                f'</div>'
            )
            with cols[i % 2]:
                st.markdown(html, unsafe_allow_html=True)
                if detailed:
                    with st.expander("Full breakdown"):
                        st.write(f"**True EV:** {c.get('true_ev')}% (fair {c.get('fair_prob')}%)")
                        st.write(f"**Gap / Spike / Vol:** {c.get('ev_gap')}% / {c.get('spike')} / {c.get('vol')}")
                        st.write(f"**In preferred range:** {c.get('petty_range_match')}")
                        st.json(c.get("book_prices", {}))
                if st.button("Lock 🔒", key=f"lk_{i}_{c['player']}_{c['prop']}_{c['line']}"):
                    ledger = load_ledger()
                    ledger.append({
                        "ts": datetime.now().isoformat(timespec="minutes"),
                        "sport": c["sport"], "player": c["player"], "prop": c["prop"],
                        "line": c["line"], "price": c["price"],
                        "book": BOOK_FULL.get(c["book"], c["book"]),
                        "event": c["event"],
                        "true_ev": c.get("true_ev"),
                        "fair_prob": c.get("fair_prob"),
                        "decision": c.get("decision"),
                        "petty_range_match": c.get("petty_range_match"),
                        "result": None,
                        "clv": None,
                        "locked_price": c["price"],
                        "petty_mode": petty_mode,
                    })
                    save_ledger(ledger)
                    st.toast("Locked.")

        st.markdown(f'<div class="glossary">{GLOSSARY}</div>', unsafe_allow_html=True)

    with tab_tracker:
        ledger = load_ledger()
        sharp = load_sharpness()
        if st.button("Wipe the slate"):
            save_ledger([])
            st.rerun()
        if not ledger:
            st.info("Nothing locked yet.")
        else:
            df = pd.DataFrame(ledger)
            finished = df[df["result"].isin(["hit", "miss"])] if "result" in df.columns else pd.DataFrame()
            hits = (finished["result"] == "hit").sum() if not finished.empty else 0
            st.markdown(f"**You’ve locked {len(df)} plays.** {len(finished)} finished. {hits} hit.")
            st.dataframe(df, use_container_width=True, hide_index=True)
            render_softness(sharp)
        st.markdown(f'<div class="glossary">{GLOSSARY}</div>', unsafe_allow_html=True)

try:
    main()
except Exception as e:
    st.error(f"App error: {e}")
    st.exception(e)
