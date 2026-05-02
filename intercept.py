"""
iCondo Mobile API Interceptor
===============================
Captures the API endpoints used by the iCondo mobile app using mitmproxy.

Setup:
    1. Install mitmproxy: pip install mitmproxy  (or brew install mitmproxy)
    2. Run this script: python intercept.py
    3. Configure your phone's WiFi proxy to point to this computer's IP:8080
    4. Install the mitmproxy CA cert on your phone: visit mitm.it in mobile browser
    5. Open iCondo app and go through the booking flow
    6. All API calls are logged to logs/api_capture_*.json

The captured endpoints and auth tokens can then be used by bot.py for direct API calls.
"""

import json
import os
import signal
import sys
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread


LOG_DIR = "logs"
PROXY_PORT = 8080


class APICapture:
    """Stores captured API requests/responses."""

    def __init__(self):
        self.requests = []
        self.auth_tokens = {}
        self.api_base_url = None

    def add(self, entry):
        self.requests.append(entry)

        # Extract auth tokens
        headers = entry.get("request_headers", {})
        for key, value in headers.items():
            key_lower = key.lower()
            if any(
                t in key_lower
                for t in ["authorization", "token", "x-auth", "cookie", "session"]
            ):
                self.auth_tokens[key] = value

        # Detect API base URL
        url = entry.get("url", "")
        if "icondo" in url.lower() and "/api/" in url.lower():
            parts = url.split("/api/")
            if parts:
                self.api_base_url = parts[0] + "/api"

    def save(self, filepath):
        data = {
            "captured_at": datetime.now().isoformat(),
            "api_base_url": self.api_base_url,
            "auth_tokens": self.auth_tokens,
            "requests": self.requests,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def print_summary(self):
        print(f"\n{'=' * 60}")
        print(f"Captured {len(self.requests)} API requests")
        print(f"{'=' * 60}")

        if self.api_base_url:
            print(f"\nAPI Base URL: {self.api_base_url}")

        if self.auth_tokens:
            print(f"\nAuth headers found:")
            for key, value in self.auth_tokens.items():
                print(f"  {key}: {value[:50]}...")

        # Group by endpoint
        endpoints = {}
        for req in self.requests:
            method = req.get("method", "?")
            url = req.get("url", "")
            key = f"{method} {url}"
            if key not in endpoints:
                endpoints[key] = {"count": 0, "has_body": False}
            endpoints[key]["count"] += 1
            if req.get("request_body"):
                endpoints[key]["has_body"] = True

        if endpoints:
            print(f"\nEndpoints ({len(endpoints)}):")
            for endpoint, info in endpoints.items():
                body_marker = " [+body]" if info["has_body"] else ""
                print(f"  {endpoint}{body_marker}")

        # Highlight booking-related endpoints
        booking_endpoints = [
            req
            for req in self.requests
            if any(
                kw in req.get("url", "").lower()
                for kw in ["book", "facilit", "slot", "reserv", "avail"]
            )
        ]
        if booking_endpoints:
            print(f"\nBooking-related endpoints ({len(booking_endpoints)}):")
            for req in booking_endpoints:
                print(f"  {req['method']} {req['url']}")
                if req.get("request_body"):
                    print(f"    Request:  {json.dumps(req['request_body'])[:200]}")
                if req.get("response_body"):
                    print(f"    Response: {json.dumps(req['response_body'])[:200]}")

            print("\n  >>> Copy the above into api_endpoints.json to configure the bot <<<")


def run_mitmproxy_capture():
    """Run mitmproxy to capture iCondo app traffic."""
    try:
        from mitmproxy import options
        from mitmproxy.tools.dump import DumpMaster
    except ImportError:
        print("mitmproxy is not installed. Falling back to manual capture mode.")
        print("Install it with: pip install mitmproxy")
        print()
        run_manual_capture()
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"api_capture_{timestamp}.json")
    capture = APICapture()

    class ICOndoAddon:
        def response(self, flow):
            url = flow.request.pretty_url
            # Only capture iCondo-related traffic
            if "icondo" not in url.lower():
                return

            entry = {
                "timestamp": datetime.now().isoformat(),
                "method": flow.request.method,
                "url": url,
                "request_headers": dict(flow.request.headers),
                "request_body": None,
                "status_code": flow.response.status_code,
                "response_headers": dict(flow.response.headers),
                "response_body": None,
            }

            # Parse request body
            if flow.request.content:
                try:
                    entry["request_body"] = json.loads(flow.request.content)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    entry["request_body"] = flow.request.content.decode(
                        "utf-8", errors="replace"
                    )

            # Parse response body
            if flow.response.content:
                try:
                    entry["response_body"] = json.loads(flow.response.content)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    entry["response_body"] = flow.response.content.decode(
                        "utf-8", errors="replace"
                    )

            capture.add(entry)

            # Print in real-time
            status = flow.response.status_code
            print(f"  [{status}] {flow.request.method} {url}")
            if entry["request_body"]:
                print(f"         Body: {json.dumps(entry['request_body'])[:150]}")

    import asyncio

    async def start_proxy():
        opts = options.Options(listen_host="0.0.0.0", listen_port=PROXY_PORT)
        master = DumpMaster(opts)
        master.addons.add(ICOndoAddon())

        print(f"mitmproxy listening on 0.0.0.0:{PROXY_PORT}")
        print("Press Ctrl+C to stop.\n")

        try:
            await master.run()
        except KeyboardInterrupt:
            pass
        finally:
            master.shutdown()

        capture.save(log_file)
        capture.print_summary()
        print(f"\nFull capture saved to: {log_file}")

    asyncio.run(start_proxy())


def run_manual_capture():
    """
    Alternative: instructions for using the system mitmproxy CLI directly,
    plus a helper to parse the resulting dump file.
    """
    print("=" * 60)
    print("Manual API Capture Instructions")
    print("=" * 60)
    print()
    print("Since mitmproxy Python module isn't available, use the CLI:")
    print()
    print("  Option A: Use Charles Proxy (GUI, easier)")
    print("    1. Download Charles Proxy from charlesproxy.com")
    print("    2. Enable SSL Proxying for *.icondo.asia")
    print("    3. Set phone WiFi proxy to your computer's IP:8888")
    print("    4. Install Charles CA cert on phone")
    print("    5. Use iCondo app, then export session as JSON")
    print()
    print("  Option B: Use mitmproxy CLI")
    print("    1. Install: brew install mitmproxy (or apt install mitmproxy)")
    print(f"    2. Run:  mitmproxy --listen-port {PROXY_PORT} --save-stream-file logs/icondo_traffic.mitm")
    print("    3. Set phone WiFi proxy to your computer's IP:8080")
    print("    4. Visit mitm.it on phone browser to install CA cert")
    print("    5. Use iCondo app - log in and book a court")
    print("    6. Stop mitmproxy (q, then y)")
    print("    7. Export:  mitmdump -r logs/icondo_traffic.mitm --set flow_detail=3 > logs/icondo_traffic.txt")
    print()
    print("  Option C: Use HTTP Toolkit (easiest, no cert install needed on Android)")
    print("    1. Download HTTP Toolkit from httptoolkit.com")
    print("    2. Click 'Android device via ADB'")
    print("    3. It auto-configures your phone's proxy and certs")
    print("    4. Use iCondo app, all traffic appears in the UI")
    print("    5. Export the session")
    print()
    print("After capturing, save the API calls to logs/api_capture.json")
    print("in this format:")
    print("""
{
  "api_base_url": "https://api.icondo.asia/api",
  "auth_tokens": {
    "Authorization": "Bearer eyJ..."
  },
  "requests": [
    {
      "method": "POST",
      "url": "https://api.icondo.asia/api/auth/login",
      "request_body": {"email": "...", "password": "..."},
      "response_body": {"token": "..."}
    },
    {
      "method": "GET",
      "url": "https://api.icondo.asia/api/facilities",
      "response_body": [{"id": 1, "name": "Tennis Court"}]
    },
    {
      "method": "POST",
      "url": "https://api.icondo.asia/api/bookings",
      "request_body": {"facility_id": 1, "date": "2025-01-15", "time_slot": "19:00"},
      "response_body": {"booking_id": 123, "status": "confirmed"}
    }
  ]
}
""")
    print("Then run: python parse_capture.py logs/api_capture.json")
    print("to auto-generate your api_endpoints.json config.")


def main():
    print("=" * 60)
    print("iCondo Mobile API Interceptor")
    print("=" * 60)
    print()
    print("This tool captures the API calls the iCondo app makes")
    print("so the bot can call them directly (fastest possible booking).")
    print()

    # Get local IP for proxy config
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "YOUR_COMPUTER_IP"

    print(f"Your computer's IP: {local_ip}")
    print(f"Proxy port: {PROXY_PORT}")
    print()
    print("Phone setup:")
    print(f"  1. Connect phone to same WiFi as this computer")
    print(f"  2. Set WiFi proxy: {local_ip}:{PROXY_PORT}")
    print(f"  3. Visit http://mitm.it on phone browser to install CA cert")
    print(f"  4. Open iCondo app and do a full booking flow")
    print()

    run_mitmproxy_capture()


if __name__ == "__main__":
    main()
