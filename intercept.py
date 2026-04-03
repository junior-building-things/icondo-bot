"""
Network Interceptor for iCondo
===============================
Run this FIRST to discover iCondo's API endpoints.
It opens a browser where you manually log in and book a court.
All API calls are logged so we can automate them later.

Usage:
    python intercept.py
"""

import json
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

ICONDO_URL = "https://resident.icondo.asia"
LOG_DIR = "logs"


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"network_{timestamp}.json")
    captured_requests = []

    print("=" * 60)
    print("iCondo Network Interceptor")
    print("=" * 60)
    print()
    print("A browser will open. Please:")
    print("  1. Log in to iCondo")
    print("  2. Navigate to facility booking")
    print("  3. Book a tennis court (or go through the flow)")
    print("  4. Close the browser when done")
    print()
    print(f"All API calls will be saved to: {log_file}")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        def on_request(request):
            url = request.url
            # Skip static assets
            if any(
                ext in url
                for ext in [".png", ".jpg", ".css", ".woff", ".svg", ".ico"]
            ):
                return

            entry = {
                "timestamp": datetime.now().isoformat(),
                "method": request.method,
                "url": url,
                "headers": dict(request.headers),
                "post_data": request.post_data,
            }
            captured_requests.append(entry)

            if "api" in url.lower() or "book" in url.lower() or "facilit" in url.lower():
                print(f"  [API] {request.method} {url}")
                if request.post_data:
                    print(f"        Body: {request.post_data[:200]}")

        def on_response(response):
            url = response.url
            if "api" in url.lower() or "book" in url.lower() or "facilit" in url.lower():
                print(f"  [RES] {response.status} {url}")

        page = context.new_page()
        page.on("request", on_request)
        page.on("response", on_response)

        page.goto(ICONDO_URL)
        print("Browser opened. Interact with iCondo now...")
        print("Close the browser window when done.\n")

        # Wait for user to close the browser
        try:
            page.wait_for_event("close", timeout=0)
        except Exception:
            pass

        try:
            context.close()
            browser.close()
        except Exception:
            pass

    # Save captured requests
    with open(log_file, "w") as f:
        json.dump(captured_requests, f, indent=2, default=str)

    print(f"\nCaptured {len(captured_requests)} requests.")
    print(f"Saved to: {log_file}")

    # Print summary of API endpoints found
    api_calls = [
        r for r in captured_requests
        if "api" in r["url"].lower()
        or "book" in r["url"].lower()
        or "facilit" in r["url"].lower()
    ]
    if api_calls:
        print(f"\nKey API endpoints found ({len(api_calls)}):")
        for call in api_calls:
            print(f"  {call['method']} {call['url']}")


if __name__ == "__main__":
    main()
