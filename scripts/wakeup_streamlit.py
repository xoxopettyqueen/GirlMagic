#!/usr/bin/env python3
"""
Visit a Streamlit Community Cloud app with a real browser.
curl is not enough — Streamlit returns a sleeping HTML shell without starting Python.
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright


APP_URL = os.environ.get("STREAMLIT_APP_URL", "").strip()
WAIT_SEC = int(os.environ.get("WAKE_WAIT_SEC", "45"))


def main():
    if not APP_URL:
        print("STREAMLIT_APP_URL is empty", file=sys.stderr)
        sys.exit(1)

    print(f"Opening {APP_URL}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(APP_URL, wait_until="domcontentloaded", timeout=90_000)
        time.sleep(3)

        # Sleeping apps show this button
        wake = page.get_by_role("button", name="Yes, get this app back up!")
        if wake.count() > 0:
            print("App was sleeping — clicking wake")
            wake.first.click()
            page.wait_for_timeout(WAIT_SEC * 1000)
        else:
            print("No sleep button — app already up or loading")
            page.wait_for_timeout(15_000)

        title = page.title()
        print(f"Title: {title}")
        # Touch the page so Streamlit counts a visitor
        page.mouse.move(40, 40)
        page.wait_for_timeout(5_000)
        browser.close()
    print("Wake pass finished")


if __name__ == "__main__":
    main()
