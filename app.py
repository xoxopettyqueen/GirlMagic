# -*- coding: utf-8 -*-
"""Girl Magic Odds 2.0 — full app, SportsGameOdds feed."""
import json, re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Girl Magic Odds 2.0", page_icon="✨", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
.stApp{background:#0c0c10!important;color:#fff!important;font-family:'Inter',sans-serif!important}
.hero{background:linear-gradient(90deg,#FF3EBF,#C77DFF,#7B2CBF);border-radius:20px;padding:18px 22px;margin-bottom:12px;color:#fff;box-shadow:0 0 28px #ff3ebf66}
.hero h1{margin:0;font-size:1.8rem;font-weight:800}
.hero p{margin:4px 0 0;color:#ffeaf6}
.gm{background:#16121e;border:1px solid #c77dff;border-radius:16px;padding:14px;margin-bottom:10px}
.gm-name{font-size:1.1rem;font-weight:800}
.gm-sub{color:#cbb6e0;font-size:.75rem;margin-bottom:6px}
.gm-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:8px 0}
.gm-grid div{background:#21182c;border-radius:10px;padding:6px;text-align:center}
.gm-grid span{display:block;font-size:.6rem;color:#cbb6e0}
.gm-grid b{display:block;font-size:1rem}
.mtag{background:#21182c;border:1px solid #8b6bb5;border-radius:999px;padding:3px 8px;font-size:.62rem;margin:2px}
.game-header{color:#ffb3ea;font-weight:700;margin:14px 0 6px}
.glossary{background:#14141c;border:1px solid #ff00cc66;border-radius:16px;padding:16px;line-height:1.6}
</style>
""", unsafe_allow_html=True)

SGO = "https://api.sportsgameodds.com/v2"
BDL = "https://api.balldontlie.io/nba/v1"
LEDGER = Path("odds_ledger.json")
MY_BOOKS = {"fanduel":"FD","draftkings":"DK","betmgm":"MGM","bet365":"365","williamhill_us":"CZR","fanatics":"FAN","espnbet":"SCR","hardrockbet":"HR","pinnacle":"PIN","circa":"CIR","bookmaker":"BM"}
BASE_WEIGHTS = {"PIN":3.5,"CIR":3.0,"BM":2.8,"FD":2.0,"DK":1.8,"365":2.0,"MGM":1.4,"CZR":1.3,"FAN":1.2,"SCR":1.1,"HR":1.1}
GLOSSARY = """
<strong>Be a better bettor.</strong> Hunt the true value. Catch the books sleeping at the wheel.<br><br>
<strong>True EV</strong> — the longest price against the blended fair number.<br>
<strong>Gap</strong> — how far the long number stands from the pack.<br>
<strong>Soft book</strong> — the one hanging the longest number.<br>
<strong>How to use it</strong><br>
1. Pull the board.<br>
2. Gap over 20% means one book is way longer than the pack.<br>
3. Edge over 3% is the juice.<br>
4. Lock it. After the games, run the receipts.
"""

def secret(name):
    try:
        return st.secrets.get(name, "") or ""
    except Exception:
        return ""

def implied(price):
    try:
        p = int(price)
        return 100/(p+100) if p > 0 else abs(p)/(abs(p)+100)
    except Exception:
        return None

def load_json(path, default):
    if path.exists():
        try: return json.loads(path.read_text())
        except Exception: pass
    return default

def save_json(path, data):
    try: path.write_text(json.dumps(data, indent=2))
    except Exception: pass

def load_ledger():
    rows = load_json(LEDGER, None)
    return st.session_state.get("ledger", []) if rows is None else rows

def save_ledger(rows):
    st.session_state["ledger"] = rows
    save_json(LEDGER, rows)

def normalize_book(key):
    k = str(key or "").lower()
    for needle, name in (("pinnacle","pinnacle"),("circa","circa"),("bookmaker","bookmaker"),("bet365","bet365"),("fanatic","fanatics"),("hardrock","hardrockbet"),("espnbet","espnbet"),("score","espnbet"),("draftking","draftkings"),("fanduel","fanduel"),("betmgm","betmgm"),("williamhill","williamhill_us"),("caesar","williamhill_us")):
        if needle in k: return name
    return k

def weighted_fair(book_prices):
    weighted, total = [], 0.0
    for bk, price in (book_prices or {}).items():
        w = float(BASE_WEIGHTS.get(bk, 1.0))
        imp = implied(price)
        if imp:
            weighted.append(imp * w); total += w
    if not weighted or not total: return None
    return max(0.05, min(0.85, sum(weighted)/total))

def true_ev(price, fair):
    if not fair or price is None: return None
    try:
        dec = (price/100+1) if int(price) > 0 else (100/abs(int(price))+1)
        return round(max(-20, min(80, (fair*dec-1)*100)), 1)
    except Exception:
        return None

def parse_sgo(ev, sport):
    teams = ev.get("teams") or {}
    away = ((teams.get("away") or {}).get("names") or {}).get("long") or ""
    home = ((teams.get("home") or {}).get("names") or {}).get("long") or ""
    event = f"{away} @ {home}"
    plays = []
    for odd in (ev.get("odds") or {}).values():
        if odd.get("statEntityID") in ("all", "home", "away", None): continue
        if odd.get("sideID") not in ("over", "yes"): continue
        stat = odd.get("statID") or ""
        prop = {"points":"Points","assists":"Assists","rebounds":"Rebounds","receiving_yards":"Rec Yards"}.get(stat)
        if "touchdown" in stat: prop = "Anytime TD"
        if not prop: continue
        pid = odd.get("playerID") or odd.get("statEntityID") or ""
        name = " ".join(w.capitalize() for w in pid.split("_")[:-2]) or pid
        for bk, row in (odd.get("byBookmaker") or {}).items():
            short = MY_BOOKS.get(normalize_book(bk))
            if not short: continue
            try: price = int(str(row.get("odds")).replace("+",""))
            except Exception: continue
            line = row.get("overUnder")
            try: line = float(line) if line is not None else (0.5 if prop == "Anytime TD" else None)
            except Exception: line = None
            if line is None: continue
            plays.append({"sport":sport,"event":event,"player":name,"prop":prop,"line":line,"price":price,"book":short})
    return plays

def best_cards(plays):
    by = defaultdict(list)
    for p in plays:
        by[(p["sport"], p["player"], p["prop"], round(float(p["line"]),1), p["event"])].append(p)
    cards = []
    for group in by.values():
        best = max(group, key=lambda x: x["price"])
        prices = {g["book"]: g["price"] for g in group}
        vals = list(prices.values())
        med = sorted(vals)[len(vals)//2]
        gap = round((best["price"]-med)/med*100, 1) if med else 0
        fair = weighted_fair(prices)
        tev = true_ev(best["price"], fair)
        cards.append({**best, "book_prices":prices, "median":int(med), "ev_gap":gap, "true_ev":tev})
    cards.sort(key=lambda x: -(x.get("true_ev") or -999))
    return cards

def glow_card(c):
    books = "".join(f'<span class="mtag">{bk} {px:+d}</span>' for bk, px in sorted(c.get("book_prices",{}).items(), key=lambda z: -z[1])[:5])
    return (
        f'<div class="gm"><div class="gm-name">{c.get("player")}</div>'
        f'<div class="gm-sub">{c.get("prop")} o{c.get("line")} · {c.get("event")}</div>'
        f'<div class="gm-grid">'
        f'<div><span>Best</span><b>{c.get("price"):+d}</b></div>'
        f'<div><span>Pack</span><b>{c.get("median"):+d}</b></div>'
        f'<div><span>Gap</span><b>{c.get("ev_gap")}%</b></div>'
        f'<div><span>Edge</span><b>{c.get("true_ev")}%</b></div></div>'
        f'<div>{books}</div>'
        f'<div class="gm-sub">{c.get("book")} is longest versus the blend.</div></div>'
    )

def grade_nba(ledger, key):
    if not key: return ledger, "Add BALLDONTLIE_API_KEY to secrets."
    updated = 0
    for row in ledger:
        if row.get("sport") != "NBA" or row.get("result") in ("HIT","MISS"): continue
        # name search then recent games
        try:
            r = requests.get(f"{BDL}/players", headers={"Authorization": key}, params={"search": row.get("player")}, timeout=15)
            data = r.json().get("data") or []
            if not data: continue
            pid = data[0].get("id")
            for back in range(4):
                day = (datetime.now(timezone.utc)-timedelta(days=back)).strftime("%Y-%m-%d")
                g = requests.get(f"{BDL}/games", headers={"Authorization": key}, params={"dates[]": day}, timeout=15).json().get("data") or []
                for game in g:
                    s = requests.get(f"{BDL}/stats", headers={"Authorization": key}, params={"player_ids[]": pid, "game_ids[]": game.get("id")}, timeout=15).json().get("data") or []
                    if not s: continue
                    stat = s[0]
                    actual = {"Points": stat.get("pts"), "Rebounds": stat.get("reb"), "Assists": stat.get("ast")}.get(row.get("prop"))
                    if actual is None: continue
                    row["result"] = "HIT" if float(actual) >= float(row.get("line") or 0) else "MISS"
                    row["player_stat"] = actual
                    updated += 1
                    break
                if row.get("result"): break
        except Exception:
            continue
    return ledger, f"Graded {updated}."

def main():
    st.markdown('<div class="hero"><h1>Girl Magic Odds 2.0</h1><p>SportsGameOdds feed. Be a better bettor. Catch the books slippin.</p></div>', unsafe_allow_html=True)
    sgo = secret("SPORTSGAMEODDS_API_KEY")
    bdl = secret("BALLDONTLIE_API_KEY")
    sport = st.radio("Lane", ["NBA", "NFL"], horizontal=True)
    if st.button("Pull the board", type="primary", use_container_width=True):
        if not sgo:
            st.session_state["note"] = "Add SPORTSGAMEODDS_API_KEY to secrets."
            st.session_state[f"cards_{sport}"] = []
        else:
            with st.spinner("Pulling SportsGameOdds…"):
                league = "NBA" if sport == "NBA" else "NFL"
                odds_ids = "points-PLAYER_ID-game-ou-over,assists-PLAYER_ID-game-ou-over,rebounds-PLAYER_ID-game-ou-over" if sport == "NBA" else "receiving_yards-PLAYER_ID-game-ou-over"
                r = requests.get(f"{SGO}/events", params={"apiKey": sgo, "leagueID": league, "oddsAvailable": "true", "oddIDs": odds_ids, "limit": 15}, timeout=30)
                plays = []
                if r.status_code == 200:
                    for ev in (r.json() or {}).get("data") or []:
                        plays.extend(parse_sgo(ev, sport))
                    note = f"SGO {r.status_code} · {len(plays)} prices"
                else:
                    note = f"SGO {r.status_code}: {(r.text or '')[:80]}"
                cards = best_cards(plays)
                st.session_state[f"cards_{sport}"] = cards
                st.session_state["note"] = note + f" · {len(cards)} cards"
    cards = st.session_state.get(f"cards_{sport}") or []
    if st.session_state.get("note"):
        st.warning(st.session_state["note"])
    board, tracker, glossary = st.tabs(["Board", "Tracker", "What this means"])
    with board:
        if not cards:
            st.info("Pull the board.")
        else:
            min_odds = st.slider("Min odds", -200, 5000, 100, 50)
            shown = [c for c in cards if (c.get("price") or 0) >= min_odds][:40]
            st.markdown(f"**{len(shown)} plays.**")
            by = defaultdict(list)
            for c in shown: by[c.get("event")].append(c)
            for game, rows in by.items():
                st.markdown(f'<div class="game-header">{game}</div>', unsafe_allow_html=True)
                cols = st.columns(2)
                for i, c in enumerate(rows):
                    with cols[i%2]:
                        st.markdown(glow_card(c), unsafe_allow_html=True)
                        if st.button("Lock", key=f"lk_{sport}_{game}_{i}_{c['player']}_{c['line']}"):
                            led = load_ledger()
                            led.append({"ts": datetime.now().isoformat(timespec="minutes"), **{k: c.get(k) for k in ("sport","player","prop","line","price","book","event","true_ev","ev_gap")}, "result": None})
                            save_ledger(led)
                            st.toast("Locked")
    with tracker:
        led = load_ledger()
        c1, c2 = st.columns(2)
        if c1.button("Clear the slate"):
            save_ledger([]); st.rerun()
        if c2.button("Run the receipts") and sport == "NBA":
            led, msg = grade_nba(led, bdl)
            save_ledger(led); st.success(msg)
        mine = [r for r in led if r.get("sport") == sport]
        hits = sum(1 for r in mine if r.get("result") == "HIT")
        misses = sum(1 for r in mine if r.get("result") == "MISS")
        st.markdown(f"**{len(mine)} locked · {hits} hit · {misses} miss**")
        for r in mine[:30]:
            st.markdown(f"{r.get('player')} {r.get('prop')} {r.get('line')} · {r.get('price')} {r.get('book')} · {r.get('result') or 'LOCKED'}")
    with glossary:
        st.markdown(f'<div class="glossary">{GLOSSARY}</div>', unsafe_allow_html=True)

try:
    main()
except Exception as e:
    st.error(f"App error: {e}")
    st.exception(e)
