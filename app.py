"""
Girl Magic – Forced Debug
Shows raw text + length so we can see what’s coming back
"""

import streamlit as st
import requests

st.set_page_config(page_title="Girl Magic Debug", page_icon="💖", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #1a0a1f 0%, #2d1b3d 50%, #1f0f2e 100%); color: #fce7f3; }
    h1, h2, h3 { color: #f9a8d4 !important; }
    .stButton > button {
        background: linear-gradient(90deg, #ec4899, #a855f7) !important;
        color: white !important; border: none !important; border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

API_BASE = "https://api.sportsgameodds.com/v2"

def get_api_key():
    key = st.secrets.get("SGO_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("SportsGameOdds API Key", type="password", value="45f0d5c343e08038b9c867e3f8663649")
    return key

def main():
    st.title("💖 Forced Debug Mode")
    st.write("This will show the raw response text so we can see what’s actually coming back.")

    api_key = get_api_key()
    if not api_key:
        st.warning("No key")
        st.stop()

    if st.button("Force Fetch 💫", type="primary"):
        params = {
            "apiKey": api_key,
            "leagueID": "MLB",
            "oddsAvailable": "true",
            "limit": 3
        }

        try:
            r = requests.get(f"{API_BASE}/events", params=params, timeout=30)
            st.write(f"**Status:** {r.status_code}")
            st.write(f"**Response length:** {len(r.text)} characters")

            # Always show the first 4000 characters of the raw response
            st.subheader("Raw Response (first 4000 chars)")
            st.code(r.text[:4000], language="json")

            if len(r.text) > 4000:
                st.write(f"... (truncated, total {len(r.text)} characters)")

        except Exception as e:
            st.error(f"Request completely failed: {e}")

if __name__ == "__main__":
    main()
