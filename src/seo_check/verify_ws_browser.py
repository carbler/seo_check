from playwright.sync_api import sync_playwright
import sys

def verify_browser_ws():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        messages = []
        page.on("console", lambda msg: messages.append(msg.text))

        # Ensure report dir exists so page loads
        import os
        os.makedirs("reports/test_browser_ws", exist_ok=True)

        # Open page (accessing via 127.0.0.1 directly to match server)
        # Note: If the user accesses via 0.0.0.0, our JS replacement logic triggers.
        # Let's test that replacement logic by accessing via 0.0.0.0 if possible?
        # Playwright might not like 0.0.0.0. Let's try.
        try:
            page.goto("http://127.0.0.1:8000/report/test_browser_ws")
            page.wait_for_timeout(2000) # Wait for WS connection

            # Check logs
            connected = False
            for m in messages:
                print(f"LOG: {m}")
                if "WebSocket Connected" in m:
                    connected = True

            if connected:
                print("SUCCESS: WebSocket connected in browser.")
            else:
                print("FAILURE: WebSocket did not connect.")
                sys.exit(1)

        except Exception as e:
            print(f"Browser Test Error: {e}")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    verify_browser_ws()
