"""
Midnight Scheduler for iCondo Booking Bot
==========================================
Runs the booking bot automatically at midnight every day.

Usage:
    python scheduler.py              # Run as a persistent scheduler
    python scheduler.py --once       # Run once at next midnight, then exit
    python scheduler.py --cron       # Print crontab entry for system scheduling
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta

from bot import run_booking

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"logs/scheduler_{datetime.now().strftime('%Y%m%d')}.log"
        ),
    ],
)
log = logging.getLogger("scheduler")


def seconds_until_midnight():
    """Calculate seconds until the next midnight."""
    now = datetime.now()
    midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return (midnight - now).total_seconds()


def pre_midnight_launch():
    """
    Start the bot ~30 seconds before midnight.
    The bot will log in and be ready, then attempt booking right at midnight.
    """
    # Wait until 30 seconds before midnight
    wait_secs = seconds_until_midnight() - 30
    if wait_secs > 0:
        log.info(
            f"Next booking attempt at midnight. "
            f"Waiting {wait_secs:.0f}s ({wait_secs/3600:.1f}h)..."
        )
        time.sleep(wait_secs)

    log.info("Starting booking bot (pre-midnight launch)...")
    success = run_booking(wait_for_midnight=True)

    if success:
        log.info("Booking successful!")
    else:
        log.error("Booking failed.")

    return success


def run_scheduler():
    """Run the booking bot every night at midnight."""
    os.makedirs("logs", exist_ok=True)
    log.info("=" * 60)
    log.info("iCondo Booking Scheduler Started")
    log.info("=" * 60)
    log.info("Bot will attempt to book tennis courts at each midnight.")

    while True:
        try:
            pre_midnight_launch()
        except Exception as e:
            log.error(f"Scheduler error: {e}")

        # Sleep a bit to avoid double-runs, then loop back to wait for next midnight
        log.info("Sleeping 60s before re-entering wait loop...")
        time.sleep(60)


def print_cron_instructions():
    """Print instructions for setting up a system cron job."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    python_path = sys.executable

    print()
    print("=" * 60)
    print("Cron Setup Instructions")
    print("=" * 60)
    print()
    print("Option 1: Run at 23:59:30 (bot waits for midnight internally)")
    print(f"  59 23 * * * cd {script_dir} && {python_path} bot.py --wait-midnight")
    print()
    print("Option 2: Run exactly at midnight")
    print(f"  0 0 * * * cd {script_dir} && {python_path} bot.py")
    print()
    print("To install, run: crontab -e")
    print("Then paste one of the lines above.")
    print()
    print("Option 3: Use systemd timer (recommended for reliability)")
    print(f"""
Create /etc/systemd/system/icondo-bot.service:
  [Unit]
  Description=iCondo Tennis Court Booking Bot
  After=network.target

  [Service]
  Type=oneshot
  WorkingDirectory={script_dir}
  ExecStart={python_path} bot.py --wait-midnight
  Environment=DISPLAY=:0

  [Install]
  WantedBy=multi-user.target

Create /etc/systemd/system/icondo-bot.timer:
  [Unit]
  Description=Run iCondo bot before midnight

  [Timer]
  OnCalendar=*-*-* 23:59:30
  Persistent=true

  [Install]
  WantedBy=timers.target

Then enable:
  sudo systemctl enable --now icondo-bot.timer
""")


def main():
    parser = argparse.ArgumentParser(description="iCondo Booking Scheduler")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once at next midnight, then exit",
    )
    parser.add_argument(
        "--cron",
        action="store_true",
        help="Print crontab/systemd setup instructions",
    )
    args = parser.parse_args()

    if args.cron:
        print_cron_instructions()
        return

    os.makedirs("logs", exist_ok=True)

    if args.once:
        log.info("Single run mode: will book at next midnight and exit.")
        pre_midnight_launch()
    else:
        run_scheduler()


if __name__ == "__main__":
    main()
