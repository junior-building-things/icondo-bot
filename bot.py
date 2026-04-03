"""
iCondo Tennis Court Booking Bot
================================
Automates booking of tennis courts at Sky Everton via the iCondo resident portal.

Usage:
    python bot.py              # Book for the furthest available date
    python bot.py --date 2025-01-15  # Book for a specific date
    python bot.py --dry-run    # Run without actually confirming the booking
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────

ICONDO_URL = "https://resident.icondo.asia"
EMAIL = os.getenv("ICONDO_EMAIL", "")
PASSWORD = os.getenv("ICONDO_PASSWORD", "")
PREFERRED_TIMES = os.getenv("PREFERRED_TIMES", "19:00,20:00").split(",")
FACILITY_NAME = os.getenv("FACILITY_NAME", "Tennis Court")
DAYS_AHEAD = int(os.getenv("DAYS_AHEAD", "14"))
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY_MS = int(os.getenv("RETRY_DELAY_MS", "500"))

SCREENSHOT_DIR = "screenshots"

# ── Logging ────────────────────────────────────────────────────────────────────

os.makedirs("logs", exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

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


def screenshot(page, name):
    """Save a screenshot for debugging."""
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{datetime.now().strftime('%H%M%S')}.png")
    page.screenshot(path=path, full_page=True)
    log.info(f"Screenshot saved: {path}")


def wait_until_midnight():
    """Sleep until just before midnight (23:59:59.500) to start booking at 00:00."""
    now = datetime.now()
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    wait_seconds = (midnight - now).total_seconds() - 0.5  # Start 500ms before midnight
    if wait_seconds > 0:
        log.info(f"Waiting {wait_seconds:.1f}s until midnight...")
        time.sleep(wait_seconds)


def login(page):
    """Log in to iCondo resident portal."""
    log.info(f"Navigating to {ICONDO_URL}")
    page.goto(ICONDO_URL, wait_until="networkidle")
    screenshot(page, "01_login_page")

    # Try common login form selectors
    # NOTE: You may need to update these selectors after running intercept.py
    email_selectors = [
        'input[type="email"]',
        'input[name="email"]',
        'input[name="username"]',
        'input[placeholder*="email" i]',
        'input[placeholder*="user" i]',
        "#email",
        "#username",
    ]

    password_selectors = [
        'input[type="password"]',
        'input[name="password"]',
        "#password",
    ]

    submit_selectors = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Login")',
        'button:has-text("Log In")',
        'button:has-text("Sign In")',
        'a:has-text("Login")',
    ]

    email_input = None
    for selector in email_selectors:
        try:
            el = page.wait_for_selector(selector, timeout=3000)
            if el:
                email_input = el
                log.info(f"Found email input: {selector}")
                break
        except PlaywrightTimeout:
            continue

    if not email_input:
        screenshot(page, "01_no_email_field")
        raise RuntimeError(
            "Could not find email/username field. "
            "Run intercept.py first to inspect the login page, "
            "then update the selectors in bot.py."
        )

    password_input = None
    for selector in password_selectors:
        try:
            el = page.wait_for_selector(selector, timeout=3000)
            if el:
                password_input = el
                log.info(f"Found password input: {selector}")
                break
        except PlaywrightTimeout:
            continue

    if not password_input:
        screenshot(page, "01_no_password_field")
        raise RuntimeError("Could not find password field.")

    # Fill credentials
    email_input.fill(EMAIL)
    password_input.fill(PASSWORD)
    screenshot(page, "02_credentials_filled")

    # Submit
    for selector in submit_selectors:
        try:
            btn = page.wait_for_selector(selector, timeout=2000)
            if btn:
                log.info(f"Clicking submit: {selector}")
                btn.click()
                break
        except PlaywrightTimeout:
            continue

    # Wait for navigation after login
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)
    screenshot(page, "03_after_login")
    log.info("Login completed")


def navigate_to_booking(page):
    """Navigate to the facility booking section."""
    # Try common navigation patterns for facility booking
    booking_selectors = [
        'a:has-text("Facility")',
        'a:has-text("Booking")',
        'a:has-text("Book")',
        'button:has-text("Facility")',
        'button:has-text("Booking")',
        '[href*="facility"]',
        '[href*="booking"]',
        'text=Facility Booking',
        'text=Book Facility',
        'text=Facilities',
    ]

    for selector in booking_selectors:
        try:
            el = page.wait_for_selector(selector, timeout=3000)
            if el and el.is_visible():
                log.info(f"Found booking nav: {selector}")
                el.click()
                page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(1)
                screenshot(page, "04_booking_page")
                return
        except PlaywrightTimeout:
            continue

    screenshot(page, "04_no_booking_nav")
    raise RuntimeError(
        "Could not find facility booking navigation. "
        "Run intercept.py to inspect the page structure."
    )


def select_facility(page):
    """Select the tennis court facility."""
    facility_selectors = [
        f'text="{FACILITY_NAME}"',
        f'text={FACILITY_NAME}',
        f'a:has-text("{FACILITY_NAME}")',
        f'button:has-text("{FACILITY_NAME}")',
        f'div:has-text("{FACILITY_NAME}")',
        'text="Tennis"',
        'text=Tennis',
    ]

    for selector in facility_selectors:
        try:
            el = page.wait_for_selector(selector, timeout=3000)
            if el and el.is_visible():
                log.info(f"Found facility: {selector}")
                el.click()
                page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(1)
                screenshot(page, "05_facility_selected")
                return
        except PlaywrightTimeout:
            continue

    screenshot(page, "05_no_facility")
    raise RuntimeError(
        f"Could not find '{FACILITY_NAME}'. "
        "Check the facility name in your .env file."
    )


def select_date(page, target_date):
    """Navigate to and select the target booking date."""
    date_str = target_date.strftime("%Y-%m-%d")
    day_num = target_date.day
    log.info(f"Selecting date: {date_str} (day {day_num})")

    # Try clicking on a date picker or calendar
    date_selectors = [
        f'[data-date="{date_str}"]',
        f'td:has-text("{day_num}")',
        f'div[class*="day"]:has-text("{day_num}")',
        f'button:has-text("{day_num}")',
        f'a:has-text("{day_num}")',
    ]

    # May need to navigate forward in the calendar first
    next_month_selectors = [
        'button[class*="next"]',
        'a[class*="next"]',
        '[aria-label="Next month"]',
        'button:has-text(">")',
        'button:has-text("›")',
        '.fc-next-button',
    ]

    # Check if we need to navigate months
    today = datetime.now()
    months_ahead = (target_date.year - today.year) * 12 + (target_date.month - today.month)

    for _ in range(months_ahead):
        for selector in next_month_selectors:
            try:
                btn = page.wait_for_selector(selector, timeout=2000)
                if btn and btn.is_visible():
                    btn.click()
                    time.sleep(0.5)
                    break
            except PlaywrightTimeout:
                continue

    # Now select the date
    for selector in date_selectors:
        try:
            elements = page.query_selector_all(selector)
            for el in elements:
                text = el.inner_text().strip()
                if text == str(day_num):
                    log.info(f"Clicking date element: {selector}")
                    el.click()
                    page.wait_for_load_state("networkidle", timeout=10000)
                    time.sleep(1)
                    screenshot(page, "06_date_selected")
                    return
        except Exception:
            continue

    screenshot(page, "06_no_date")
    raise RuntimeError(
        f"Could not select date {date_str}. "
        "The calendar structure may differ from expected."
    )


def select_time_slot(page):
    """Select preferred time slot (7pm or 8pm)."""
    for preferred_time in PREFERRED_TIMES:
        # Normalize time display variants
        hour = int(preferred_time.split(":")[0])
        time_variants = [
            preferred_time,                          # 19:00
            f"{hour}:00",                            # 19:00
            f"{hour % 12 or 12}:00 PM",              # 7:00 PM
            f"{hour % 12 or 12}:00PM",               # 7:00PM
            f"{hour % 12 or 12}pm",                  # 7pm
            f"{hour % 12 or 12}:00 pm",              # 7:00 pm
            f"{hour % 12 or 12}.00 PM",              # 7.00 PM
            f"{hour}00",                             # 1900
        ]

        log.info(f"Looking for time slot: {preferred_time} (variants: {time_variants[:3]}...)")

        for variant in time_variants:
            selectors = [
                f'text="{variant}"',
                f'button:has-text("{variant}")',
                f'a:has-text("{variant}")',
                f'td:has-text("{variant}")',
                f'div[class*="slot"]:has-text("{variant}")',
                f'div[class*="time"]:has-text("{variant}")',
            ]

            for selector in selectors:
                try:
                    el = page.wait_for_selector(selector, timeout=1500)
                    if el and el.is_visible():
                        # Check it's not already booked
                        parent = el.evaluate(
                            "el => el.closest('[class*=\"booked\"], [class*=\"unavailable\"], [class*=\"disabled\"]')"
                        )
                        if parent:
                            log.info(f"Slot {variant} is unavailable, trying next...")
                            break

                        log.info(f"Found available slot: {variant}")
                        el.click()
                        time.sleep(1)
                        screenshot(page, "07_time_selected")
                        return preferred_time
                except PlaywrightTimeout:
                    continue

    screenshot(page, "07_no_time_slot")
    raise RuntimeError(
        f"No preferred time slots ({PREFERRED_TIMES}) available. "
        "They may already be booked."
    )


def confirm_booking(page, dry_run=False):
    """Confirm the booking."""
    confirm_selectors = [
        'button:has-text("Confirm")',
        'button:has-text("Book")',
        'button:has-text("Submit")',
        'button:has-text("Reserve")',
        'a:has-text("Confirm")',
        'input[type="submit"]',
    ]

    for selector in confirm_selectors:
        try:
            el = page.wait_for_selector(selector, timeout=3000)
            if el and el.is_visible():
                screenshot(page, "08_before_confirm")

                if dry_run:
                    log.info(f"DRY RUN: Would click confirm button: {selector}")
                    return True

                log.info(f"Clicking confirm: {selector}")
                el.click()
                page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(2)
                screenshot(page, "09_after_confirm")

                # Check for success indicators
                success_indicators = [
                    'text="Success"',
                    'text="Confirmed"',
                    'text="Booked"',
                    'text="successfully"',
                    '[class*="success"]',
                ]
                for indicator in success_indicators:
                    try:
                        if page.wait_for_selector(indicator, timeout=3000):
                            log.info("Booking confirmed successfully!")
                            return True
                    except PlaywrightTimeout:
                        continue

                # If no success indicator found, assume success if no error
                log.info("Booking submitted (no explicit success message detected)")
                return True
        except PlaywrightTimeout:
            continue

    # Sometimes there's a second confirmation (Are you sure?)
    try:
        dialog_confirm = page.wait_for_selector(
            'button:has-text("Yes"), button:has-text("OK"), button:has-text("Confirm")',
            timeout=3000,
        )
        if dialog_confirm:
            if dry_run:
                log.info("DRY RUN: Would confirm dialog")
                return True
            dialog_confirm.click()
            time.sleep(2)
            screenshot(page, "09_dialog_confirmed")
            return True
    except PlaywrightTimeout:
        pass

    screenshot(page, "08_no_confirm")
    raise RuntimeError("Could not find confirmation button.")


def run_booking(target_date=None, dry_run=False, wait_for_midnight=False):
    """Main booking flow."""
    if not EMAIL or not PASSWORD:
        log.error("Set ICONDO_EMAIL and ICONDO_PASSWORD in your .env file")
        sys.exit(1)

    if target_date is None:
        target_date = datetime.now() + timedelta(days=DAYS_AHEAD)

    log.info("=" * 60)
    log.info("iCondo Tennis Court Booking Bot")
    log.info("=" * 60)
    log.info(f"Target date: {target_date.strftime('%Y-%m-%d (%A)')}")
    log.info(f"Preferred times: {PREFERRED_TIMES}")
    log.info(f"Facility: {FACILITY_NAME}")
    log.info(f"Headless: {HEADLESS}")
    log.info(f"Dry run: {dry_run}")

    if wait_for_midnight:
        wait_until_midnight()

    for attempt in range(1, MAX_RETRIES + 1):
        log.info(f"\n--- Attempt {attempt}/{MAX_RETRIES} ---")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=HEADLESS,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = context.new_page()

                login(page)
                navigate_to_booking(page)
                select_facility(page)
                select_date(page, target_date)
                booked_time = select_time_slot(page)
                confirm_booking(page, dry_run=dry_run)

                log.info("=" * 60)
                log.info(
                    f"{'[DRY RUN] ' if dry_run else ''}"
                    f"Booked {FACILITY_NAME} on "
                    f"{target_date.strftime('%Y-%m-%d')} at {booked_time}"
                )
                log.info("=" * 60)

                browser.close()
                return True

        except Exception as e:
            log.error(f"Attempt {attempt} failed: {e}")
            screenshot_name = f"error_attempt_{attempt}"
            try:
                screenshot(page, screenshot_name)
            except Exception:
                pass

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
        help="Run without actually confirming the booking",
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
