# iCondo Tennis Court Booking Bot

Automatically books tennis courts at 7 PM or 8 PM at Sky Everton via direct API calls to iCondo. Designed to fire at midnight the instant new slots are released.

## Why Direct API Calls?

iCondo is mobile-app only — no web portal to automate. This bot intercepts the app's API calls once, then uses those same endpoints directly. Direct HTTP calls are **~100x faster** than browser/app automation, giving you the best chance of grabbing slots before anyone else.

## Setup (3 Steps)

### Step 1: Capture the API endpoints (one-time)

You need to intercept the iCondo app's network traffic to discover the API endpoints. The easiest methods:

```bash
python intercept.py
```

This will guide you through setting up a proxy. The recommended approaches:

| Method | Difficulty | Notes |
|--------|-----------|-------|
| **HTTP Toolkit** | Easiest | Auto-configures Android, no cert hassle |
| **Charles Proxy** | Easy | GUI-based, good for Mac/Windows |
| **mitmproxy** | Medium | CLI, this script automates it |

**What to do:**
1. Set up the proxy on your computer
2. Point your phone's WiFi proxy to your computer
3. Open the iCondo app and do a full booking flow (login → select tennis court → pick date/time → book)
4. Save the captured traffic

Then generate the config:

```bash
python parse_capture.py logs/api_capture_*.json
```

This creates `api_endpoints.json` with the exact endpoints, auth flow, and request formats.

### Step 2: Configure credentials

```bash
cp .env.example .env
# Edit .env with your iCondo email and password
```

### Step 3: Test it

```bash
# Dry run — goes through the flow without actually booking
python bot.py --dry-run
```

## Usage

```bash
# Book for the default date (today + 14 days)
python bot.py

# Book for a specific date
python bot.py --date 2025-02-01

# Wait until midnight, then book instantly
python bot.py --wait-midnight

# Dry run (no actual booking)
python bot.py --dry-run
```

## Automated Midnight Scheduling

Courts are released at midnight. The bot logs in and looks up the facility *before* midnight, then fires the booking request the instant the clock hits 00:00.

### Option A: Persistent scheduler

```bash
python scheduler.py          # Runs every midnight
python scheduler.py --once   # Next midnight only
```

### Option B: Cron job

```bash
python scheduler.py --cron   # Prints crontab/systemd setup instructions
```

## How It Works

```
23:59:50  Bot starts, logs into iCondo API, caches facility ID
23:59:59  Waits for midnight...
00:00:00  GET /slots → finds 7PM available → POST /bookings → DONE
```

Total booking time after midnight: **< 1 second** (vs 5-10 seconds with browser automation).

## File Structure

```
├── bot.py                    # Main booking bot (direct API calls)
├── scheduler.py              # Midnight scheduling
├── intercept.py              # Proxy-based API interceptor
├── parse_capture.py          # Converts captured traffic → api_endpoints.json
├── api_endpoints.json        # API config (generated, git-ignored)
├── api_endpoints.example.json # Example API config for reference
├── .env                      # Your credentials (git-ignored)
├── .env.example              # Credential template
├── requirements.txt          # Python dependencies
└── logs/                     # Execution logs (git-ignored)
```

## Troubleshooting

- **"api_endpoints.json not found"**: Run `intercept.py` + `parse_capture.py` first
- **Login fails**: Check credentials in `.env`; the app may use OTP — check the captured login flow
- **Token expired**: The bot logs in fresh each run, so tokens shouldn't expire
- **Slots show as unavailable**: They may genuinely be taken — try running closer to midnight
- **SSL errors during interception**: Make sure the proxy CA cert is installed on your phone
