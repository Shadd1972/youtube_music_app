"""Visit the deployed Streamlit app; wake it if it has gone to sleep.

Streamlit Community Cloud puts apps to sleep after a period without real
visits, and a plain HTTP ping does not count as a visit. This script loads
the page in a headless browser, clicks the "get this app back up" button
when the sleep screen is shown, and fails loudly if the app never renders.
"""

import sys
import time

from playwright.sync_api import sync_playwright

URL = "https://personal-ai-dj.streamlit.app/"
HERO_TEXT = "Personal AI DJ"
DEADLINE_SECONDS = 8 * 60


def body_text(page):
    # Streamlit Community Cloud serves the app inside an iframe, so collect
    # text from every frame, not just the host page.
    out = []
    for frame in page.frames:
        try:
            out.append(frame.inner_text("body", timeout=5_000))
        except Exception:
            pass
    return "\n".join(out)


def main():
    deadline = time.time() + DEADLINE_SECONDS
    woke = False
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=90_000)
        while time.time() < deadline:
            page.wait_for_timeout(5_000)
            body = body_text(page)
            if HERO_TEXT in body:
                print("App is up" + (" (woken by this run)" if woke else ""))
                browser.close()
                return 0
            if "Oh no." in body or "Error running app" in body:
                print("ERROR: app is crashing on boot", file=sys.stderr)
                browser.close()
                return 1
            wake_button = page.locator("button", has_text="back up")
            if wake_button.count() > 0:
                wake_button.first.click()
                woke = True
                print("App was asleep; clicked the wake button, waiting for boot...")
                page.wait_for_timeout(20_000)
            else:
                try:
                    page.reload(wait_until="domcontentloaded", timeout=90_000)
                except Exception:
                    pass
        print("ERROR: app did not render within the deadline", file=sys.stderr)
        browser.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
