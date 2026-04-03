# iCondo Tennis Court Booking Bot

Automatically books tennis courts at Sky Everton via the iCondo resident portal. Designed to run at midnight when new slots are released.

## Setup

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env with your iCondo login and preferences
```

### 3. Discover the page structure (required first run)

Since iCondo has no public API, you need to run the interceptor once to see how the site works. This opens a real browser — log in and navigate through the booking flow manually:

```bash
python intercept.py
```

This will:
- Open a browser to `resident.icondo.asia`
- Log all API calls to `logs/network_*.json`
- Print key API endpoints it finds

After running this, check the screenshots and logs, then update the CSS selectors in `bot.py` if the defaults don't match the actual page structure.

### 4. Test the bot (dry run)

```bash
python bot.py --dry-run
```

This goes through the full flow without clicking the final confirm button. Check `screenshots/` for visual proof of each step.

### 5. Run for real

```bash
# Book for the default date (today + DAYS_AHEAD)
python bot.py

# Book for a specific date
python bot.py --date 2025-02-01

# Wait until midnight, then book immediately
python bot.py --wait-midnight
```

## Automated Scheduling

### Option A: Persistent scheduler (simplest)

```bash
python scheduler.py
```

Runs continuously, booking at each midnight.

### Option B: Cron job

```bash
python scheduler.py --cron   # Shows crontab setup instructions
```

### Option C: One-shot (next midnight only)

```bash
python scheduler.py --once
```

## How It Works

1. **Pre-midnight**: The bot logs into iCondo ~30s before midnight and navigates to the booking page
2. **At midnight**: It immediately selects the target date and preferred time slot (7 PM first, then 8 PM as fallback)
3. **Confirmation**: It clicks the confirm/book button and saves screenshots as proof
4. **Retries**: If booking fails, it retries up to `MAX_RETRIES` times

## File Structure

```
├── bot.py           # Main booking automation
├── scheduler.py     # Midnight scheduling (cron, systemd, or persistent)
├── intercept.py     # Network interceptor for discovering API endpoints
├── .env.example     # Configuration template
├── .env             # Your credentials (git-ignored)
├── requirements.txt # Python dependencies
├── screenshots/     # Booking proof screenshots (git-ignored)
└── logs/            # Execution logs (git-ignored)
```

## Customizing Selectors

The bot uses generic CSS selectors that should work with most iCondo portal layouts. If they don't match your portal, update the selector lists in these functions in `bot.py`:

- `login()` — email, password, and submit button selectors
- `navigate_to_booking()` — navigation menu selectors
- `select_facility()` — facility name matching
- `select_date()` — calendar/date picker selectors
- `select_time_slot()` — time slot display format
- `confirm_booking()` — confirmation button selectors

## Troubleshooting

- **Screenshots**: Check `screenshots/` after each run for visual debugging
- **Logs**: Check `logs/` for detailed execution logs
- **Selectors not matching**: Run `intercept.py` to see the actual page structure
- **Login fails**: Verify credentials in `.env`; iCondo may use OTP — if so, you'll need to handle that manually or add OTP support
