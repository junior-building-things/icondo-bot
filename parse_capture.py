"""
Parse captured API traffic and generate api_endpoints.json
===========================================================
Analyzes the captured network traffic from intercept.py and creates the
configuration file that bot.py needs.

Usage:
    python parse_capture.py logs/api_capture_*.json
    python parse_capture.py logs/icondo_traffic.txt  # mitmproxy text export
"""

import json
import re
import sys
from pathlib import Path


def parse_json_capture(filepath):
    """Parse JSON capture from intercept.py or manual export."""
    with open(filepath) as f:
        data = json.load(f)

    requests = data.get("requests", [])
    if not requests:
        print("No requests found in capture file.")
        return None

    config = {
        "api_base_url": data.get("api_base_url", ""),
        "endpoints": {},
        "auth": {},
    }

    for req in requests:
        url = req.get("url", "")
        method = req.get("method", "GET")
        url_lower = url.lower()

        # Detect login endpoint
        if any(kw in url_lower for kw in ["login", "auth", "signin"]):
            config["endpoints"]["login"] = {
                "method": method,
                "url": url,
                "body_template": req.get("request_body"),
            }
            # Extract token from response
            resp = req.get("response_body", {})
            if isinstance(resp, dict):
                for key in ["token", "access_token", "jwt", "accessToken", "data"]:
                    if key in resp:
                        token_val = resp[key]
                        if isinstance(token_val, dict) and "token" in token_val:
                            config["auth"]["token_path"] = f"response.{key}.token"
                        else:
                            config["auth"]["token_path"] = f"response.{key}"
                        break

        # Detect facility listing
        elif any(kw in url_lower for kw in ["facilit", "ameniti"]):
            if method == "GET":
                config["endpoints"]["facilities"] = {
                    "method": method,
                    "url": url,
                }

        # Detect available slots
        elif any(kw in url_lower for kw in ["slot", "avail", "schedule", "timeslot"]):
            config["endpoints"]["available_slots"] = {
                "method": method,
                "url": url,
                "params_template": req.get("request_body"),
            }

        # Detect booking creation
        elif any(kw in url_lower for kw in ["book", "reserv"]):
            if method == "POST":
                config["endpoints"]["create_booking"] = {
                    "method": method,
                    "url": url,
                    "body_template": req.get("request_body"),
                }

    return config


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_capture.py <capture_file>")
        print("  Supported formats: .json (from intercept.py)")
        sys.exit(1)

    filepath = sys.argv[1]
    if not Path(filepath).exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    print(f"Parsing: {filepath}")
    config = parse_json_capture(filepath)

    if not config:
        sys.exit(1)

    output = "api_endpoints.json"
    with open(output, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nGenerated: {output}")
    print(json.dumps(config, indent=2))

    # Check what's missing
    required = ["login", "available_slots", "create_booking"]
    found = list(config["endpoints"].keys())
    missing = [ep for ep in required if ep not in found]

    if missing:
        print(f"\nMissing endpoints: {missing}")
        print("You may need to manually add these to api_endpoints.json")
        print("by inspecting the full capture in logs/")
    else:
        print("\nAll required endpoints found! Bot should be ready to use.")


if __name__ == "__main__":
    main()
