# -*- coding: utf-8 -*-
"""
Girl Magic Odds 2.0 — positive EV, not a price-gap costume.

A number is +EV only when:
1. We have both sides (Over/Under or Yes/No) on at least two books.
2. Each book is de-vigged (multiplicative).
3. Those fair probs are blended by book weight.
4. The best price beats that fair price.

A book hanging +500 while everyone else is +400 is a disagreement.
It is not automatically +EV.
"""
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Girl Magic Odds 2.0", page_icon="✨", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Pacifico&display=swap');
.stApp{background:#0c0c10!important;color:#fff!important;font-family:'Inter',sans-serif!important}
.hero{background:linear-gradient(90deg,#FF3EBF,#C77DFF,#7B2CBF)!important;border-radius:20px;padding:18px 22px;margin-bottom:12px;color:#fff;box-shadow:0 0 28px rgba(255,62,191,.4)}
.hero h1{margin:0;font-size:1.75rem;font-weight:700}
.hero p{margin:4px 0 0;opacity:.95;font-size:1.02rem;color:#F5E9FF;font-family:'Pacifico',cursive}
button[kind="primary"], .stButton > button[kind="primary"]{background:linear-gradient(90deg,#FF3EBF,#FF7AC4)!important;border:none!important;border-radius:999px!important;font-weight:700!important;min-height:44px}
.card{background:linear-gradient(180deg,rgba(21,21,27,.95) 0%,rgba(16,16,20,.95) 100%);border:1px solid #2a2a33;border-radius:14px;padding:11px 13px;margin-bottom:10px;position:relative}
.card.take-card{border-color:#FF3EBF;box-shadow:0 0 16px rgba(255,62,191,.5)}
.card.true-ev-glow{border-color:#FF3EBF;box-shadow:0 0 22px rgba(255,62,191,.75)}
.card.dimmed{opacity:0.65;border-color:#5a4a6a}
.player{font-size:1.15rem;font-weight:700;margin:0}
.meta{color:#aaa;font-size:.65rem;margin:2px 0 4px}
.prop{font-size:.85rem;font-weight:600;color:#FF3EBF;margin-bottom:4px;text-transform:uppercase}
.books{display:flex;flex-wrap:wrap;gap:4px;margin:4px 0}
.bk{background:#0d0d12;border:1px solid #333;border-radius:999px;padding:3px 7px;text-align:center;min-width:50px;font-size:.64rem;font-weight:600;color:#fff}
.bk.best{border-color:#FF3EBF;box-shadow:0 0 8px rgba(255,62,191,.6)}
.true-ev{font-size:.9rem;font-weight:700;color:#FF3EBF;margin:3px 0}
.score{font-size:.8rem;font-weight:700;color:#FFD700;margin:2px 0}
.why{font-size:.72rem;color:#e0d4f5;margin-top:4px;line-height:1.3}
.take-tag{position:absolute;top:6px;right:8px;font-size:.55rem;letter-spacing:.1em;color:#FF3EBF;font-weight:700}
.tag{display:inline-block;background:rgba(199,125,255,.15);color:#F5E9FF;border:1px solid rgba(199,125,255,.4);border-radius:999px;padding:1px 6px;font-size:.55rem;margin:2px 2px 0 0}
.tag.range{background:rgba(255,62,191,.2);border-color:#FF3EBF}
.glossary{font-size:.85rem;color:#e8e0f0;margin-top:10px;padding:18px 20px;background:linear-gradient(180deg,#121218 0%,#0e0e14 100%);border-radius:12px;border:1px solid #2a2a33;line-height:1.7}
.glossary strong{color:#FF3EBF}
.softness-title{font-size:1.1rem;font-weight:700;color:#fff;margin:18px 0 8px}
.game-header{font-size:1.05rem;font-weight:700;color:#FF3EBF;margin:18px 0 8px;border-bottom:1px solid #2a2a33;padding-bottom:4px}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
LEDGER = Path("odds_ledger.json")
SHARPNESS = Path("book_sharpness.json")
WEIGHTS_FILE = Path("auto_weights.json")

MY_BOOKS = {
    "fanduel": "FD", "draftkings": "DK", "betmgm": "MGM", "bet365": "365",
    "williamhill_us": "CZR", "fanatics": "FAN", "espnbet": "SCR",
    "hardrockbet": "HR", "hardrockbet_az": "HR", "hardrockbet_oh": "HR", "hardrockbet_fl": "HR",
    "pinnacle": "PIN", "circa": "CIR", "bookmaker": "BM",
}
BOOK_FULL = {
    "FD": "FanDuel", "DK": "DraftKings", "MGM": "BetMGM", "365": "Bet365",
    "CZR": "Caesars", "FAN": "Fanatics", "SCR": "theScore", "HR": "Hard Rock",
    "PIN": "Pinnacle", "CIR": "Circa", "BM": "Bookmaker",
}
ALL_BOOK_CODES = sorted(set(BOOK_FULL.keys()))
SHARP_BOOKS = {"PIN", "CIR", "BM"}
BASE_WEIGHTS = {
    "PIN": 3.5, "CIR": 3.0, "BM": 2.8,
    "FD": 1.6, "DK": 1.5, "365": 1.4, "MGM": 1.2,
    "CZR": 1.1, "FAN": 1.0, "SCR": 1.0, "HR": 1.0,
}

GLOSSARY = """
<strong>Glossary</strong><br><br>
<strong>True EV</strong> — (fair probability × decimal odds) − 1. Positive means the best price pays more than the de-vigged blend says it should.<br>
<strong>Fair price</strong> — Both sides of the market, vig pulled off each book, then blended by weight. Not the average of the Over prices.<br>
<strong>No de-vig</strong> — We only saw one side. That card is a price disagreement, not +EV. It will not green.<br>
<strong>Soft disagreement</strong> — Real de-vig, but no Pinnacle / Circa / Bookmaker in the blend. It can still be a lead. It is not a sharp-closing edge.<br>
<strong>TAKE</strong> — De-vigged, at least two books, True EV at least 2%, best price longer than fair.<br>
<strong>LEAN</strong> — De-vigged and EV at least 0.5%. Optional.<br>
<strong>PASS</strong> — No real edge, or we could not de-vig.<br>
<strong>CLV</strong> — Locked price vs the price at close. Positive means you beat the close.<br>
"""


def secret(name):
    try:
        return st.secrets.get(name, "") or ""
    except Exception:
        return ""


def implied(price):
    try:
        p = int(price)
    except Exception:
        return None
    if p == 0:
        return None
    if p > 0:
        return 100 / (p + 100)
    return abs(p) / (abs(p) + 100)


def to_decimal(price):
    try:
        p = int(price)
    except Exception:
        return None
    if p > 0:
        return 1 + p / 100.0
    if p < 0:
        return 1 + 100 / abs(p)
    return None


def prob_to_american(prob):
    try:
        p = float(prob)
    except Exception:
        return None
    if p <= 0.01 or p >= 0.99:
        return None
    if p >= 0.5:
        return int(round(-100 * p / (1 - p)))
    return int(round(100 * (1 - p) / p))


def devig(over_imp, under_imp):
    if not over_imp or not under_imp:
        return None
    total = over_imp + under_imp
    if total <= 1.0:
        return over_imp
    return over_imp / total


def in_user_range(prop, line):
    try:
        line = float(line)
    except Exception:
        return False
    if prop == "Assists":
        return 3 <= line <= 8
    if prop == "Points":
        return 8 <= line <= 15
    if prop == "Rebounds":
        return 4 <= line <= 10
    return prop in ("DoubleDouble", "Anytime TD")


def line_ok(prop, line):
    try:
        line = float(line)
    except Exception:
        return True
    if prop == "Points":
        return line <= 40
    if prop == "Rebounds":
        return line <= 20
    if prop == "Assists":
        return line <= 16
    if prop == "Rec Yards":
        return line <= 120
    return True


def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return default


def save_json(path, data):
    try:
        path.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def load_sharpness():
    return load_json(SHARPNESS, {})


def load_auto_weights():
    saved = load_json(WEIGHTS_FILE, {})
    out = BASE_WEIGHTS.copy()
    out.update(saved or {})
    return out


def save_auto_weights(w):
    save_json(WEIGHTS_FILE, w)


def normalize_book(key):
    k = str(key or "").lower()
    if "pinnacle" in k:
        return "pinnacle"
    if "circa" in k:
        return "circa"
    if "bookmaker" in k:
        return "bookmaker"
    if "bet365" in k:
        return "bet365"
    if "fanatic" in k:
        return "fanatics"
    if "hardrock" in k:
        return "hardrockbet"
    if "espnbet" in k or "score" in k:
        return "espnbet"
    if "draftking" in k:
        return "draftkings"
    if "fanduel" in k:
        return "fanduel"
    if "betmgm" in k or k == "mgm":
        return "betmgm"
    if "williamhill" in k or "caesar" in k:
        return "williamhill_us"
    return k


def load_ledger():
    rows = load_json(LEDGER, None)
    if rows is None:
        return st.session_state.get("ledger", [])
    return rows


def save_ledger(rows):
    st.session_state["ledger"] = rows
    save_json(LEDGER, rows)


@st.cache_data(ttl=120)
def fetch_events(api_key, sport_key):
    try:
        r = requests.get(
            f"{ODDS_API_BASE}/sports/{sport_key}/events",
            params={"apiKey": api_key},
            timeout=15,
        )
        if r.status_code == 200:
            return r.json() or []
    except Exception:
        pass
    return []


@st.cache_data(ttl=90)
def fetch_odds(api_key, sport_key, event_id, markets):
    try:
        r = requests.get(
            f"{ODDS_API_BASE}/sports/{sport_key}/events/{event_id}/odds",
            params={
                "apiKey": api_key,
                "regions": "us,us2,eu,uk",
                "markets": markets,
                "oddsFormat": "american",
            },
            timeout=20,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _prop_from_market(mkey, sport):
    mkey = (mkey or "").lower()
    if sport == "NBA":
        if "double_double" in mkey:
            return "DoubleDouble"
        if "assist" in mkey:
            return "Assists"
        if "rebound" in mkey and "point" not in mkey:
            return "Rebounds"
        if "point" in mkey and "rebound" not in mkey and "assist" not in mkey:
            return "Points"
        return None
    if "anytime_td" in mkey or "goal_scorer" in mkey:
        return "Anytime TD"
    if "reception_yds" in mkey or "receiving_yds" in mkey:
        return "Rec Yards"
    return None


def _side_and_player(outcome, prop):
    name = str(outcome.get("name") or "").strip()
    desc = str(outcome.get("description") or "").strip()
    low_name = name.lower()
    low_desc = desc.lower()
    blob = f"{low_name} {low_desc}"
    if prop in ("DoubleDouble", "Anytime TD"):
        if low_name in ("yes", "over") or "yes" in low_name:
            return "over", desc or name
        if low_name in ("no", "under") or low_name == "no":
            return "under", desc or name
        return None, None
    if low_name in ("over", "o") or blob.startswith("over"):
        return "over", desc or name
    if low_name in ("under", "u") or blob.startswith("under"):
        return "under", desc or name
    return None, None


def _line_of(outcome, prop, blob):
    if prop == "Anytime TD":
        return 0.5
    if prop == "DoubleDouble":
        return 1.0
    point = outcome.get("point")
    if point is not None:
        try:
            return float(point)
        except Exception:
            pass
    m = re.search(r"(\d+\.?\d*)", blob)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def parse_plays(data, sport):
    if not data:
        return []
    event = f"{data.get('away_team')} @ {data.get('home_team')}"
    plays = []
    for book in data.get("bookmakers") or []:
        bk = normalize_book(book.get("key"))
        if bk not in MY_BOOKS:
            continue
        short = MY_BOOKS[bk]
        for market in book.get("markets") or []:
            prop = _prop_from_market(market.get("key"), sport)
            if not prop:
                continue
            for o in market.get("outcomes") or []:
                side, player = _side_and_player(o, prop)
                if not side or not player:
                    continue
                if str(player).lower() in ("yes", "no", "over", "under", "o", "u"):
                    continue
                blob = f"{o.get('name') or ''} {o.get('description') or ''}"
                line = _line_of(o, prop, blob)
                if line is None:
                    continue
                try:
                    price = int(o.get("price"))
                except Exception:
                    continue
                plays.append({
                    "sport": sport,
                    "event": event,
                    "player": player,
                    "prop": prop,
                    "line": line,
                    "side": side,
                    "price": price,
                    "book": short,
                })
    return plays


def best_cards(plays, weights=None):
    weights = weights or load_auto_weights()
    grouped = defaultdict(list)
    for p in plays:
        key = (p["sport"], p["player"], p["prop"], round(float(p["line"]), 1), p["event"])
        grouped[key].append(p)
    cards = []
    for key, group in grouped.items():
        overs = [g for g in group if g["side"] == "over"]
        unders = [g for g in group if g["side"] == "under"]
        if not overs:
            continue
        over_px = {}
        under_px = {}
        for g in overs:
            prev = over_px.get(g["book"])
            if prev is None or g["price"] > prev:
                over_px[g["book"]] = g["price"]
        for g in unders:
            prev = under_px.get(g["book"])
            if prev is None or g["price"] > prev:
                under_px[g["book"]] = g["price"]
        best_book = max(over_px, key=lambda b: over_px[b])
        best_price = over_px[best_book]
        devigged = {}
        for bk, opx in over_px.items():
            upx = under_px.get(bk)
            if upx is None:
                continue
            fair_side = devig(implied(opx), implied(upx))
            if fair_side:
                devigged[bk] = fair_side
        fair = None
        if devigged:
            num = den = 0.0
            for bk, prob in devigged.items():
                w = float(weights.get(bk, 1.0) or 1.0)
                num += prob * w
                den += w
            fair = num / den if den else None
        true_ev = None
        if fair:
            dec = to_decimal(best_price)
            if dec:
                true_ev = round((fair * dec - 1) * 100, 1)
        has_sharp = any(bk in SHARP_BOOKS for bk in devigged)
        n_devig = len(devigged)
        if n_devig < 2 or true_ev is None:
            decision = "PASS"
            quality = "no de-vig"
        elif true_ev >= 2:
            decision = "TAKE"
            quality = "sharp blend" if has_sharp else "soft disagreement"
        elif true_ev >= 0.5:
            decision = "LEAN"
            quality = "sharp blend" if has_sharp else "soft disagreement"
        else:
            decision = "PASS"
            quality = "priced in"
        prices = list(over_px.values())
        med = sorted(prices)[len(prices) // 2]
        spread = (max(prices) - min(prices)) / abs(med) if med else 0
        tags = []
        if quality == "no de-vig":
            tags.append("No de-vig")
        elif has_sharp:
            tags.append("Sharp in blend")
        else:
            tags.append("Soft books only")
        if n_devig:
            tags.append(f"{n_devig} de-vig")
        if len(over_px) <= 2:
            tags.append("Thin")
        sample = next(g for g in overs if g["book"] == best_book)
        petty = in_user_range(sample["prop"], sample["line"])
        tags.append("In range" if petty else "Outside range")
        fair_am = prob_to_american(fair) if fair else None
        cards.append({
            **{k: sample[k] for k in ("sport", "event", "player", "prop", "line")},
            "price": best_price,
            "book": best_book,
            "book_prices": over_px,
            "under_prices": under_px,
            "decision": decision,
            "true_ev": true_ev,
            "fair_prob": round(fair * 100, 1) if fair else None,
            "fair_american": fair_am,
            "quality": quality,
            "n_devig": n_devig,
            "has_sharp": has_sharp,
            "tags": tags,
            "petty_range_match": petty,
            "spread": round(spread, 2),
            "score": round(max(0, true_ev or 0), 1),
        })
    cards.sort(key=lambda x: (x.get("event") or "", -(x.get("true_ev") or -999)))
    return cards


def plain_reason(c):
    tev = c.get("true_ev")
    bk = c.get("book") or ""
    fair = c.get("fair_american")
    if c.get("quality") == "no de-vig":
        return "One side only. This is a price gap, not +EV."
    if c.get("decision") == "TAKE":
        extra = "" if c.get("has_sharp") else " No sharp book in the blend."
        return f"{bk} {c.get('price'):+d} vs fair {fair:+d}. Edge {tev}%." + extra
    if c.get("decision") == "LEAN":
        return f"Small edge. {bk} {c.get('price'):+d} vs fair {fair:+d}."
    if tev is not None and fair is not None:
        return f"Priced in. Fair is {fair:+d}, best is {c.get('price'):+d}."
    return "No edge."


def _espn_json(url, params=None):
    try:
        r = requests.get(url, params=params or {}, timeout=12)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def _name_hit(a, b):
    a = re.sub(r"[^a-z]", "", str(a or "").lower())
    b = re.sub(r"[^a-z]", "", str(b or "").lower())
    return bool(a and b and (a == b or a in b or b in a))


def grade_nba(ledger):
    pending = [
        r for r in ledger
        if r.get("sport") == "NBA" and r.get("result") in (None, "—", "")
        and r.get("prop") in ("Assists", "Points", "Rebounds", "DoubleDouble")
    ]
    updated = 0
    for days_back in range(0, 3):
        day = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y%m%d")
        board = _espn_json(
            "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
            {"dates": day},
        )
        for ev in board.get("events") or []:
            comp = (ev.get("competitions") or [{}])[0]
            state = ((comp.get("status") or {}).get("type") or {}).get("state")
            if state != "post":
                continue
            box = _espn_json(
                "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary",
                {"event": ev.get("id")},
            )
            players = []
            for team in ((box.get("boxscore") or {}).get("players") or []):
                for block in team.get("statistics") or []:
                    labels = [str(x).lower() for x in (block.get("labels") or block.get("names") or [])]
                    for ath in block.get("athletes") or []:
                        nm = ((ath.get("athlete") or {}).get("displayName")) or ""
                        stats = ath.get("stats") or []
                        row = {}
                        for i, lab in enumerate(labels):
                            if i < len(stats):
                                row[lab] = stats[i]
                        players.append((nm, row))
            for rec in pending:
                if rec.get("result") in ("HIT", "MISS"):
                    continue
                hit = next((row for nm, row in players if _name_hit(rec.get("player"), nm)), None)
                if not hit:
                    continue
                def num(keys):
                    for k in keys:
                        if k in hit:
                            try:
                                return float(str(hit[k]).split("-")[0])
                            except Exception:
                                pass
                    return None
                pts = num(["pts", "points"]) or 0
                reb = num(["reb", "rebounds"]) or 0
                ast = num(["ast", "assists"]) or 0
                prop = rec.get("prop")
                line = float(rec.get("line") or 0)
                actual = {"Points": pts, "Rebounds": reb, "Assists": ast}.get(prop)
                if prop == "DoubleDouble":
                    actual = 1 if sum(1 for x in (pts, reb, ast) if x >= 10) >= 2 else 0
                    line = 1
                if actual is None:
                    continue
                rec["result"] = "HIT" if actual >= line else "MISS"
                rec["player_stat"] = actual
                updated += 1
    save_ledger(ledger)
    return updated


def grade_nfl(ledger):
    pending = [
        r for r in ledger
        if r.get("sport") == "NFL" and r.get("result") in (None, "—", "")
        and r.get("prop") == "Anytime TD"
    ]
    updated = 0
    for days_back in range(0, 4):
        day = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y%m%d")
        board = _espn_json(
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
            {"dates": day},
        )
        for ev in board.get("events") or []:
            comp = (ev.get("competitions") or [{}])[0]
            state = ((comp.get("status") or {}).get("type") or {}).get("state")
            if state != "post":
                continue
            box = _espn_json(
                "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary",
                {"event": ev.get("id")},
            )
            scorers = []
            for team in ((box.get("boxscore") or {}).get("players") or []):
                for block in team.get("statistics") or []:
                    name = str(block.get("name") or "").lower()
                    if "touchdown" not in name and name not in ("scoring", "rushing", "receiving"):
                        continue
                    labels = [str(x).lower() for x in (block.get("labels") or [])]
                    for ath in block.get("athletes") or []:
                        nm = ((ath.get("athlete") or {}).get("displayName")) or ""
                        stats = ath.get("stats") or []
                        td = 0
                        for i, lab in enumerate(labels):
                            if i < len(stats) and "td" in lab:
                                try:
                                    td += float(stats[i])
                                except Exception:
                                    pass
                        if td > 0 or "touchdown" in name:
                            scorers.append(nm)
            if not scorers:
                continue
            for rec in pending:
                if rec.get("result") in ("HIT", "MISS"):
                    continue
                rec["result"] = "HIT" if any(_name_hit(rec.get("player"), n) for n in scorers) else "MISS"
                updated += 1
    save_ledger(ledger)
    return updated


def render_softness(cards):
    if not cards:
        return
    rows = []
    for bk in ALL_BOOK_CODES:
        takes = [c for c in cards if c.get("book") == bk and c.get("decision") == "TAKE"]
        priced = [c for c in cards if bk in (c.get("book_prices") or {})]
        if not priced:
            continue
        rows.append({
            "Book": BOOK_FULL.get(bk, bk),
            "TAKE count": len(takes),
            "On slate": len(priced),
        })
    if not rows:
        return
    df = pd.DataFrame(rows).sort_values("TAKE count", ascending=False)
    st.markdown('<div class="softness-title">Who is hanging the long number</div>', unsafe_allow_html=True)
    st.caption("This is who had the best price on a real +EV card. It is not proof the book is soft.")
    st.bar_chart(df.set_index("Book")[["TAKE count"]], use_container_width=True, color="#FF3EBF")


def main():
    st.markdown(
        '<div class="hero"><h1>✨ Girl Magic Odds 2.0</h1>'
        '<p>De-vig first. Then the edge. A long number is not a model.</p></div>',
        unsafe_allow_html=True,
    )
    api_key = secret("ODDS_API_KEY") or st.text_input("Odds API Key", type="password")
    if not api_key:
        st.info("Add your Odds API key.")
        return
    auto_weights = load_auto_weights()
    with st.sidebar:
        st.markdown("### Book weights")
        st.caption("Pinnacle, Circa, and Bookmaker should stay heavy. They are the sharp side.")
        live_weights = {}
        for short in sorted(BASE_WEIGHTS):
            default = float(auto_weights.get(short, BASE_WEIGHTS[short]))
            live_weights[short] = st.slider(short, 0.5, 4.0, default, 0.1, key=f"w_{short}")
        if st.button("Reset weights"):
            save_auto_weights(BASE_WEIGHTS.copy())
            st.rerun()
    sport_choice = st.radio("Lane", ["NBA", "NFL"], horizontal=True)
    if st.button("Pull the board", type="primary", use_container_width=True):
        sport_key = "basketball_nba" if sport_choice == "NBA" else "americanfootball_nfl"
        markets = (
            "player_assists,player_assists_alternate,player_points,player_points_alternate,"
            "player_rebounds,player_rebounds_alternate,player_double_double"
            if sport_choice == "NBA"
            else "player_anytime_td,player_reception_yds,player_reception_yds_alternate"
        )
        with st.spinner(f"Pulling {sport_choice}…"):
            events = fetch_events(api_key, sport_key)
            now = datetime.now(timezone.utc)
            pregame = []
            for ev in events:
                raw = ev.get("commence_time") or ""
                try:
                    start = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    if start > now:
                        pregame.append(ev)
                except Exception:
                    continue
            target = pregame or events
            plays = []
            for ev in target[:24]:
                data = fetch_odds(api_key, sport_key, ev.get("id"), markets)
                if data:
                    plays.extend(parse_plays(data, sport_choice))
            cards = best_cards(plays, live_weights)
            st.session_state[f"cards_{sport_choice}"] = cards
            st.session_state["fetched"] = datetime.now().strftime("%H:%M")
            st.session_state["last_sport"] = sport_choice
            st.toast(f"{len(cards)} priced props. {sum(1 for c in cards if c['decision']=='TAKE')} real TAKE.")
    cards = st.session_state.get(f"cards_{sport_choice}") or []
    if st.session_state.get("fetched") and st.session_state.get("last_sport") == sport_choice:
        real = sum(1 for c in cards if c.get("n_devig", 0) >= 2)
        st.caption(f"{sport_choice} @ {st.session_state['fetched']} — {len(cards)} props, {real} with a real de-vig")
    tab_board, tab_tracker, tab_glossary = st.tabs(["Board", "Tracker", "Glossary"])
    with tab_board:
        if not cards:
            st.info("Pull the board.")
        else:
            c1, c2, c3 = st.columns(3)
            simple = c1.toggle("Simple — TAKE only", value=True)
            detailed = c2.toggle("Show the why", value=False)
            petty = c3.toggle("Petty ranges", value=False)
            f1, f2, f3 = st.columns(3)
            props = ["Assists", "Points", "Rebounds", "DoubleDouble"] if sport_choice == "NBA" else ["Anytime TD", "Rec Yards"]
            prop_filter = f1.multiselect("Prop", props, default=props)
            decision_filter = f2.multiselect("Call", ["TAKE", "LEAN", "PASS"], default=["TAKE", "LEAN"])
            min_ev = f3.slider("Min True EV %", -10.0, 30.0, 0.0, 0.5)
            o1, o2 = st.columns(2)
            min_odds = o1.number_input("Min odds", value=-150, step=10)
            max_odds = o2.number_input("Max odds", value=2000, step=50)
            book_filter = st.multiselect("Best-price book", ALL_BOOK_CODES, default=ALL_BOOK_CODES, format_func=lambda x: BOOK_FULL.get(x, x))
            filtered = [c for c in cards if c.get("prop") in prop_filter and line_ok(c.get("prop"), c.get("line"))]
            if petty:
                filtered = [c for c in filtered if c.get("petty_range_match")]
            if simple:
                filtered = [c for c in filtered if c.get("decision") == "TAKE"]
            filtered = [c for c in filtered if c.get("decision") in decision_filter]
            filtered = [c for c in filtered if (c.get("true_ev") or -999) >= min_ev]
            filtered = [c for c in filtered if min_odds <= (c.get("price") or 0) <= max_odds]
            filtered = [c for c in filtered if c.get("book") in book_filter]
            if not filtered:
                st.info("Nothing clears these filters. Drop Simple or lower Min odds — real edges are often shorter than +500.")
            else:
                sharp_n = sum(1 for c in filtered if c.get("has_sharp"))
                st.markdown(f"**{len(filtered)} plays.** {sharp_n} have a sharp book in the blend.")
                by_game = defaultdict(list)
                for c in filtered:
                    by_game[c.get("event") or "Unknown"].append(c)
                for game, game_cards in by_game.items():
                    st.markdown(f'<div class="game-header">{game}</div>', unsafe_allow_html=True)
                    cols = st.columns(2)
                    for i, c in enumerate(game_cards):
                        line_txt = "Yes" if c["prop"] in ("DoubleDouble", "Anytime TD") else f"o{c['line']}"
                        boxes = "".join(
                            f'<div class="bk {"best" if bk == c["book"] else ""}"><span>{bk}</span>{px:+d}</div>'
                            for bk, px in sorted(c.get("book_prices", {}).items(), key=lambda x: -x[1])
                        )
                        tags = "".join(f'<span class="tag">{t}</span>' for t in c.get("tags") or [])
                        cls = "card"
                        if c.get("decision") == "TAKE":
                            cls += " take-card"
                        if (c.get("true_ev") or 0) >= 3 and c.get("has_sharp"):
                            cls += " true-ev-glow"
                        fair = c.get("fair_american")
                        fair_txt = f"{fair:+d}" if isinstance(fair, int) else "—"
                        tev = c.get("true_ev")
                        tev_txt = f"{tev}%" if tev is not None else "—"
                        html = (
                            f'<div class="{cls}">'
                            f'<div class="player">{c["player"]}</div>'
                            f'<div class="meta">{c["event"]}</div>'
                            f'<div class="prop">{c["prop"]} {line_txt}</div>'
                            f'<div class="books">{boxes}</div>{tags}'
                            f'<div class="true-ev">{c.get("decision")} · EV {tev_txt} · fair {fair_txt}</div>'
                            f'<div class="why">{plain_reason(c)}</div></div>'
                        )
                        with cols[i % 2]:
                            st.markdown(html, unsafe_allow_html=True)
                            if detailed:
                                with st.expander("Why"):
                                    st.write(plain_reason(c))
                                    st.write(f"De-vigged books: {c.get('n_devig')} · sharp: {c.get('has_sharp')}")
                            if st.button("Lock", key=f"lk_{sport_choice}_{i}_{c['player']}_{c['prop']}_{c['line']}"):
                                ledger = load_ledger()
                                ledger.append({
                                    "ts": datetime.now().isoformat(timespec="minutes"),
                                    "sport": c["sport"], "player": c["player"], "prop": c["prop"],
                                    "line": c["line"], "price": c["price"],
                                    "book": BOOK_FULL.get(c["book"], c["book"]),
                                    "event": c["event"], "true_ev": c.get("true_ev"),
                                    "fair_prob": c.get("fair_prob"), "fair_american": c.get("fair_american"),
                                    "decision": c.get("decision"), "quality": c.get("quality"),
                                    "result": None,
                                })
                                save_ledger(ledger)
                                st.toast("Locked.")
                render_softness(filtered)
    with tab_tracker:
        ledger = load_ledger()
        if st.button("Wipe tracker"):
            save_ledger([])
            st.rerun()
        if st.button("Grade what we can"):
            with st.spinner("Checking finals…"):
                n = grade_nba(ledger) if sport_choice == "NBA" else grade_nfl(ledger)
            st.success(f"Graded {n}.")
            st.rerun()
        mine = [r for r in ledger if r.get("sport") == sport_choice]
        if not mine:
            st.info("Nothing locked on this lane.")
        else:
            hits = sum(1 for r in mine if r.get("result") == "HIT")
            misses = sum(1 for r in mine if r.get("result") == "MISS")
            st.markdown(f"**{len(mine)} locked · {hits} hit · {misses} miss**")
            cols = st.columns(2)
            for i, r in enumerate(mine[:40]):
                res = r.get("result") or "—"
                cls = "card" + (" true-ev-glow" if res == "HIT" else " dimmed" if res == "MISS" else "")
                html = (
                    f'<div class="{cls}"><div class="player">{r.get("player")}</div>'
                    f'<div class="meta">{r.get("event")}</div>'
                    f'<div class="prop">{r.get("prop")} {r.get("line")}</div>'
                    f'<div class="true-ev">{r.get("book")} {r.get("price")} · EV {r.get("true_ev")}% · {res}</div></div>'
                )
                with cols[i % 2]:
                    st.markdown(html, unsafe_allow_html=True)
    with tab_glossary:
        st.markdown(f'<div class="glossary">{GLOSSARY}</div>', unsafe_allow_html=True)
        st.caption("If Pinnacle is missing from the pull, the EU region on your Odds API key is off. The board will say so.")


try:
    main()
except Exception as e:
    st.error(f"App error: {e}")
    st.exception(e)
