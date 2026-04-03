"""
iCondo Tennis Court Booking Bot
================================
Books tennis courts at Sky Everton via direct API calls to iCondo.
Much faster than browser automation — critical when slots are released at midnight.

Usage:
    python bot.py                      # Book for the furthest available date
    python bot.py --date 2025-01-15    # Book for a specific date
    python bot.py --dry-run            # Show what would be booked without confirming
    python bot.py --wait-midnight      # Wait until midnight, then book instantly
"""

import argparse
import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────

EMAIL = os.getenv("ICONDO_EMAIL", "")
PASSWORD = os.getenv("ICONDO_PASSWORD", "")
PREFERRED_TIMES = os.getenv("PREFERRED_TIMES", "19:00,20:00").split(",")
FACILITY_NAME = os.getenv("FACILITY_NAME", "Tennis Court")
DAYS_AHEAD = int(os.getenv("DAYS_AHEAD", "14"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY_MS = int(os.getenv("RETRY_DELAY_MS", "500"))

ENDPOINTS_FILE = "api_endpoints.json"

# ── Logging ────────────────────────────────────────────────────────────────────

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"logs/bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)
log = logging.getLogger("icondo-bot")


# ── API Client ─────────────────────────────────────────────────────────────────


class ICondoAPI:
    """Direct API client for iCondo — no browser needed."""

    def __init__(self, endpoints_config):
        self.config = endpoints_config
        self.base_url = endpoints_config.get("api_base_url", "")
        self.endpoints = endpoints_config.get("endpoints", {})
        self.token = None
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": (
                "iCondo/3.0.0 (iPhone; iOS 17.0; Scale/3.00)"
            ),
        }

    def _request(self, method, url, body=None):
        """Make an HTTP request and return parsed JSON response."""
        headers = dict(self.headers)
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                response_body = resp.read().decode("utf-8")
                try:
                    return json.loads(response_body)
                except json.JSONDecodeError:
                    return {"raw": response_body}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            log.error(f"HTTP {e.code}: {method} {url}")
            log.error(f"Response: {error_body[:500]}")
            raise
        except urllib.error.URLError as e:
            log.error(f"Connection error: {method} {url} — {e.reason}")
            raise

    def login(self, email, password):
        """Authenticate and store the session token."""
        endpoint = self.endpoints.get("login", {})
        url = endpoint.get("url", f"{self.base_url}/auth/login")
        method = endpoint.get("method", "POST")

        # Build login body from template or defaults
        body_template = endpoint.get("body_template", {})
        body = dict(body_template) if body_template else {}

        # Fill in credentials — try common field names
        credential_fields = {
            "email": email,
            "username": email,
            "user_email": email,
            "password": password,
            "user_password": password,
        }
        if body:
            for key in body:
                if key.lower() in credential_fields:
                    body[key] = credential_fields[key.lower()]
        else:
            body = {"email": email, "password": password}

        log.info(f"Logging in as {email}...")
        resp = self._request(method, url, body)

        # Extract token from response
        token_path = self.config.get("auth", {}).get("token_path", "")
        self.token = self._extract_token(resp, token_path)

        if not self.token:
            # Try common token locations
            for path in [
                "token",
                "access_token",
                "accessToken",
                "data.token",
                "data.access_token",
                "data.accessToken",
                "result.token",
            ]:
                self.token = self._extract_token(resp, path)
                if self.token:
                    break

        if self.token:
            log.info(f"Login successful (token: {self.token[:20]}...)")
        else:
            log.warning(
                "Login response received but could not extract token. "
                "Check api_endpoints.json auth.token_path"
            )
            log.debug(f"Response: {json.dumps(resp)[:300]}")

        return resp

    def _extract_token(self, data, path):
        """Extract a value from nested dict using dot notation path."""
        if not path or not isinstance(data, dict):
            return None
        # Strip leading "response." if present
        path = path.removeprefix("response.")
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current if isinstance(current, str) else None

    def get_facilities(self):
        """Get list of available facilities."""
        endpoint = self.endpoints.get("facilities", {})
        url = endpoint.get("url", f"{self.base_url}/facilities")
        method = endpoint.get("method", "GET")

        log.info("Fetching facilities...")
        resp = self._request(method, url)

        # Handle various response formats
        if isinstance(resp, list):
            return resp
        if isinstance(resp, dict):
            for key in ["data", "facilities", "result", "results", "items"]:
                if key in resp and isinstance(resp[key], list):
                    return resp[key]
        return [resp]

    def find_facility_id(self, facility_name):
        """Find the facility ID for a given name."""
        facilities = self.get_facilities()

        for facility in facilities:
            if not isinstance(facility, dict):
                continue
            name = facility.get("name", "") or facility.get("title", "") or ""
            if facility_name.lower() in name.lower():
                fid = (
                    facility.get("id")
                    or facility.get("facility_id")
                    or facility.get("facilityId")
                )
                log.info(f"Found facility: {name} (id={fid})")
                return fid

        available = [
            f.get("name", f.get("title", "?"))
            for f in facilities
            if isinstance(f, dict)
        ]
        raise RuntimeError(
            f"Facility '{facility_name}' not found. Available: {available}"
        )

    def get_available_slots(self, facility_id, date):
        """Get available time slots for a facility on a given date."""
        endpoint = self.endpoints.get("available_slots", {})
        url = endpoint.get("url", f"{self.base_url}/facilities/{facility_id}/slots")
        method = endpoint.get("method", "GET")
        date_str = date.strftime("%Y-%m-%d")

        # Replace path parameters
        url = url.replace("{facility_id}", str(facility_id))
        url = url.replace("{date}", date_str)

        if method == "GET":
            # Add date as query parameter
            separator = "&" if "?" in url else "?"
            if date_str not in url:
                url = f"{url}{separator}date={date_str}"
            log.info(f"Fetching slots: {url}")
            resp = self._request(method, url)
        else:
            params = endpoint.get("params_template", {})
            body = dict(params) if params else {}
            # Fill in facility_id and date
            for key in body:
                kl = key.lower()
                if "facility" in kl or "id" in kl:
                    body[key] = facility_id
                if "date" in kl:
                    body[key] = date_str
            if not body:
                body = {"facility_id": facility_id, "date": date_str}
            log.info(f"Fetching slots: {method} {url}")
            resp = self._request(method, url, body)

        # Parse slots from response
        if isinstance(resp, list):
            return resp
        if isinstance(resp, dict):
            for key in [
                "data",
                "slots",
                "timeslots",
                "time_slots",
                "available",
                "result",
                "results",
            ]:
                if key in resp and isinstance(resp[key], list):
                    return resp[key]
        return [resp]

    def create_booking(self, facility_id, date, time_slot):
        """Create a booking for the given facility, date, and time."""
        endpoint = self.endpoints.get("create_booking", {})
        url = endpoint.get("url", f"{self.base_url}/bookings")
        method = endpoint.get("method", "POST")
        date_str = date.strftime("%Y-%m-%d")

        # Replace path parameters
        url = url.replace("{facility_id}", str(facility_id))

        # Build request body from template or defaults
        body_template = endpoint.get("body_template", {})
        body = dict(body_template) if body_template else {}

        if body:
            # Fill template values
            for key in body:
                kl = key.lower()
                if "facility" in kl or kl == "id":
                    body[key] = facility_id
                elif "date" in kl:
                    body[key] = date_str
                elif "time" in kl or "slot" in kl:
                    body[key] = time_slot
        else:
            body = {
                "facility_id": facility_id,
                "date": date_str,
                "time_slot": time_slot,
            }

        log.info(f"Creating booking: {method} {url}")
        log.info(f"  Body: {json.dumps(body)}")
        return self._request(method, url, body)


# ── Booking Logic ──────────────────────────────────────────────────────────────


def load_endpoints():
    """Load API endpoint configuration."""
    if not os.path.exists(ENDPOINTS_FILE):
        log.error(f"{ENDPOINTS_FILE} not found!")
        log.error("Run intercept.py first to capture iCondo's API endpoints,")
        log.error("then run parse_capture.py to generate this file.")
        sys.exit(1)

    with open(ENDPOINTS_FILE) as f:
        return json.load(f)


def find_best_slot(slots, preferred_times):
    """Find the best available slot matching preferred times."""
    for preferred in preferred_times:
        hour = int(preferred.split(":")[0])
        minute = int(preferred.split(":")[1]) if ":" in preferred else 0

        # Generate time string variants to match against
        variants = [
            preferred,                              # 19:00
            f"{hour}:{minute:02d}",                 # 19:00
            f"{hour % 12 or 12}:{minute:02d} PM",   # 7:00 PM
            f"{hour % 12 or 12}:{minute:02d}PM",    # 7:00PM
            f"{hour % 12 or 12}:{minute:02d} pm",   # 7:00 pm
            f"{hour % 12 or 12}pm",                 # 7pm
            f"{hour % 12 or 12}.{minute:02d} PM",   # 7.00 PM
            f"{hour:02d}:{minute:02d}",             # 19:00
            f"{hour:02d}{minute:02d}",              # 1900
        ]

        for slot in slots:
            if not isinstance(slot, dict):
                continue

            # Check if slot is available
            status = (
                slot.get("status", "")
                or slot.get("availability", "")
                or slot.get("state", "")
            ).lower()
            if status in ("booked", "unavailable", "reserved", "full", "disabled"):
                continue

            is_available = slot.get("available", slot.get("is_available", True))
            if is_available is False or is_available == 0:
                continue

            # Match time
            slot_time = (
                slot.get("time", "")
                or slot.get("start_time", "")
                or slot.get("startTime", "")
                or slot.get("time_slot", "")
                or slot.get("slot", "")
                or slot.get("label", "")
                or str(slot.get("hour", ""))
            )

            slot_time_str = str(slot_time).strip()
            for variant in variants:
                if variant.lower() in slot_time_str.lower() or slot_time_str == variant:
                    log.info(f"Found matching slot: {slot_time_str} (matched '{variant}')")
                    return slot

    return None


def wait_until_midnight():
    """Sleep until just before midnight to start booking at 00:00:00."""
    now = datetime.now()
    midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    # Start 200ms before midnight (API calls are fast, no browser overhead)
    wait_seconds = (midnight - now).total_seconds() - 0.2
    if wait_seconds > 0:
        log.info(f"Waiting {wait_seconds:.1f}s until midnight...")
        time.sleep(wait_seconds)
    log.info(f"GO! Current time: {datetime.now().strftime('%H:%M:%S.%f')}")


def run_booking(target_date=None, dry_run=False, wait_for_midnight=False):
    """Main booking flow using direct API calls."""
    if not EMAIL or not PASSWORD:
        log.error("Set ICONDO_EMAIL and ICONDO_PASSWORD in your .env file")
        sys.exit(1)

    if target_date is None:
        target_date = datetime.now() + timedelta(days=DAYS_AHEAD)

    log.info("=" * 60)
    log.info("iCondo Tennis Court Booking Bot (API Mode)")
    log.info("=" * 60)
    log.info(f"Target date:     {target_date.strftime('%Y-%m-%d (%A)')}")
    log.info(f"Preferred times: {PREFERRED_TIMES}")
    log.info(f"Facility:        {FACILITY_NAME}")
    log.info(f"Dry run:         {dry_run}")

    endpoints = load_endpoints()
    api = ICondoAPI(endpoints)

    # Step 1: Login (do this BEFORE midnight so we're authenticated and ready)
    api.login(EMAIL, PASSWORD)

    # Step 2: Find facility ID (cache this so it's instant at midnight)
    facility_id = api.find_facility_id(FACILITY_NAME)
    log.info(f"Facility ID: {facility_id}")

    # Step 3: Wait for midnight if requested
    if wait_for_midnight:
        wait_until_midnight()

    # Step 4: Book with retries
    for attempt in range(1, MAX_RETRIES + 1):
        log.info(f"\n--- Attempt {attempt}/{MAX_RETRIES} ---")
        try:
            # Get available slots
            start_time = time.time()
            slots = api.get_available_slots(facility_id, target_date)
            elapsed = (time.time() - start_time) * 1000
            log.info(f"Got {len(slots)} slots in {elapsed:.0f}ms")

            # Find preferred slot
            slot = find_best_slot(slots, PREFERRED_TIMES)
            if not slot:
                log.warning(f"No preferred slots available. All slots: ")
                for s in slots[:10]:
                    log.warning(f"  {s}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_MS / 1000)
                    continue
                raise RuntimeError("No preferred time slots available")

            # Extract time slot identifier
            slot_time = (
                slot.get("time")
                or slot.get("start_time")
                or slot.get("startTime")
                or slot.get("time_slot")
                or slot.get("slot")
                or slot.get("id")
            )

            if dry_run:
                log.info(f"DRY RUN: Would book {FACILITY_NAME} on "
                         f"{target_date.strftime('%Y-%m-%d')} at {slot_time}")
                log.info(f"Slot details: {json.dumps(slot)}")
                return True

            # Create booking
            start_time = time.time()
            result = api.create_booking(facility_id, target_date, slot_time)
            elapsed = (time.time() - start_time) * 1000
            log.info(f"Booking response in {elapsed:.0f}ms: {json.dumps(result)[:300]}")

            log.info("=" * 60)
            log.info(
                f"BOOKED: {FACILITY_NAME} on "
                f"{target_date.strftime('%Y-%m-%d')} at {slot_time}"
            )
            log.info("=" * 60)
            return True

        except urllib.error.HTTPError as e:
            log.error(f"Attempt {attempt} failed: HTTP {e.code}")
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY_MS / 1000
                log.info(f"Retrying in {delay}s...")
                time.sleep(delay)
        except Exception as e:
            log.error(f"Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY_MS / 1000
                log.info(f"Retrying in {delay}s...")
                time.sleep(delay)

    log.error("All booking attempts failed.")
    return False


def main():
    parser = argparse.ArgumentParser(description="iCondo Tennis Court Booking Bot")
    parser.add_argument(
        "--date",
        type=str,
        help="Target date (YYYY-MM-DD). Default: today + DAYS_AHEAD",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be booked without confirming",
    )
    parser.add_argument(
        "--wait-midnight",
        action="store_true",
        help="Wait until midnight before attempting to book",
    )
    args = parser.parse_args()

    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")

    success = run_booking(
        target_date=target_date,
        dry_run=args.dry_run,
        wait_for_midnight=args.wait_midnight,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
