#!/usr/bin/env python3
"""
Standalone preview script for the Strava Summary plugin.
Generates a preview image without needing InkyPi hardware or a running server.

Usage:
    python preview.py [options]

    --mode      calendar | summary | combined  (default: calendar)
    --days      Number of days to show         (default: 7)
    --week      Use current week instead of rolling days
    --time-type moving_time | elapsed_time     (default: moving_time)
    --width     Image width in pixels          (default: 600)
    --height    Image height in pixels         (default: 448)
    --output    Output file path               (default: preview.png)
    --no-show   Save image but don't open it

Authentication — choose one (checked in this order):

    1. Auto-refresh (recommended — never expires). Put these in a .env file
       next to this script (or as environment variables):
           STRAVA_CLIENT_ID=<your client id>
           STRAVA_CLIENT_SECRET=<your client secret>
           STRAVA_REFRESH_TOKEN=<your refresh token>
       The script mints a fresh access token on each run and caches it back
       to .env, so it never goes stale.

    2. Static access token (expires 6 hours after it is issued):
           STRAVA_ACCESS_TOKEN=<token>

Install dependencies (if not already installed):
    pip install pillow requests
"""

import argparse
import importlib.util
import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Font helper — used to mock InkyPi's get_font()
# ---------------------------------------------------------------------------

# Candidate system fonts tried in order; first match wins.
_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Arial.ttf",
]

def _get_font(_name, size):
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Patch InkyPi framework imports before loading the plugin module
# ---------------------------------------------------------------------------

sys.modules.setdefault("plugins", MagicMock())
sys.modules.setdefault("plugins.base_plugin", MagicMock())
sys.modules.setdefault("plugins.base_plugin.base_plugin", MagicMock())
sys.modules.setdefault("utils", MagicMock())
utils_mock = MagicMock()
utils_mock.app_utils = MagicMock(get_font=_get_font)
sys.modules.setdefault("utils.app_utils", MagicMock(get_font=_get_font))


# ---------------------------------------------------------------------------
# Load the plugin module directly from file (no package install needed)
# ---------------------------------------------------------------------------

_PLUGIN_FILE = os.path.join(os.path.dirname(__file__), "strava_summary", "strava_summary.py")

spec = importlib.util.spec_from_file_location("strava_plugin", _PLUGIN_FILE)
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)


# ---------------------------------------------------------------------------
# Token loading
# ---------------------------------------------------------------------------

_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

# Refresh a few minutes early so a token never expires mid-request.
_EXPIRY_SKEW_SECONDS = 300


def _read_env_file():
    """Parse the .env file next to this script into a dict (empty if missing)."""
    values = {}
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def _write_env_values(updates):
    """Update/insert key=value pairs in .env, preserving other lines/comments."""
    lines = []
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH) as f:
            lines = f.read().splitlines()

    remaining = dict(updates)
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                out.append(f"{key}={remaining.pop(key)}")
                continue
        out.append(line)

    for key, val in remaining.items():
        out.append(f"{key}={val}")

    with open(_ENV_PATH, "w") as f:
        f.write("\n".join(out) + "\n")


def _env_value(key, file_env):
    """Environment variable wins over the .env file."""
    return os.environ.get(key) or file_env.get(key)


# ---------------------------------------------------------------------------
# Demo data — for tuning layout without hitting the Strava API
# ---------------------------------------------------------------------------

# (day offset from start of period, sport_type, distance in metres, seconds)
# Day 2 deliberately holds three activities: the busiest case the calendar
# columns have to fit. Day 4 is left empty to show the no-activity dash.
_DEMO_ACTIVITIES = [
    (0, "Run", 8200, 2640),
    (1, "Ride", 34500, 4980),
    (2, "Run", 12400, 3900),
    (2, "WeightTraining", 0, 2700),
    (2, "Swim", 1500, 2100),
    (3, "TrailRun", 16800, 6300),
    (5, "Ride", 61200, 8400),
    (6, "Run", 5100, 1560),
]


def _demo_activities(start_date):
    """Build a synthetic activity list spanning the display period."""
    activities = []
    for day_offset, sport_type, distance, seconds in _DEMO_ACTIVITIES:
        day = start_date + timedelta(days=day_offset)
        # Skip days beyond today so week mode looks realistic mid-week.
        if day.date() > datetime.now().date():
            continue
        start = day.replace(hour=7, minute=30, second=0, microsecond=0)
        activities.append({
            "sport_type": sport_type,
            "distance": distance,
            "moving_time": seconds,
            # Elapsed time is a little longer, so --time-type is visibly different.
            "elapsed_time": int(seconds * 1.15),
            "start_date_local": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return activities


def _load_token():
    """Return a valid Strava access token, refreshing automatically if set up."""
    file_env = _read_env_file()

    client_id = _env_value("STRAVA_CLIENT_ID", file_env)
    client_secret = _env_value("STRAVA_CLIENT_SECRET", file_env)
    refresh_token = _env_value("STRAVA_REFRESH_TOKEN", file_env)

    # --- Preferred path: auto-refresh via OAuth refresh token ---------------
    if client_id and client_secret and refresh_token:
        cached_token = _env_value("STRAVA_ACCESS_TOKEN", file_env)
        expires_at = _env_value("STRAVA_TOKEN_EXPIRES_AT", file_env)

        # Reuse the cached access token while it is still comfortably valid.
        if cached_token and expires_at:
            try:
                if int(expires_at) - time.time() > _EXPIRY_SKEW_SECONDS:
                    return cached_token
            except ValueError:
                pass  # malformed expiry — fall through and refresh

        print("Refreshing Strava access token...")
        data = plugin.refresh_access_token(client_id, client_secret, refresh_token)

        # Cache the new token (and rotated refresh token) back to .env.
        _write_env_values({
            "STRAVA_ACCESS_TOKEN": data["access_token"],
            "STRAVA_REFRESH_TOKEN": data["refresh_token"],
            "STRAVA_TOKEN_EXPIRES_AT": str(data["expires_at"]),
        })
        return data["access_token"]

    # --- Fallback: a single static access token (expires after 6 hours) -----
    return _env_value("STRAVA_ACCESS_TOKEN", file_env)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate a local preview image of the Strava Summary plugin."
    )
    parser.add_argument(
        "--mode", choices=["calendar", "summary", "combined"], default="calendar",
        help="Display mode (default: calendar)",
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="Number of rolling days to show (default: 7)",
    )
    parser.add_argument(
        "--week", action="store_true",
        help="Use current week (Mon-today) instead of rolling days",
    )
    parser.add_argument(
        "--time-type", choices=["moving_time", "elapsed_time"], default="moving_time",
        dest="time_type",
        help="Which Strava time field to use (default: moving_time)",
    )
    parser.add_argument(
        "--width", type=int, default=600,
        help="Image width in pixels (default: 600)",
    )
    parser.add_argument(
        "--height", type=int, default=448,
        help="Image height in pixels (default: 448)",
    )
    parser.add_argument(
        "--output", default="preview.png",
        help="Output file path (default: preview.png)",
    )
    parser.add_argument(
        "--no-show", action="store_true",
        help="Save image but do not open it automatically",
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Render sample activities offline (no Strava credentials needed)",
    )
    args = parser.parse_args()

    token = None
    if not args.demo:
        try:
            token = _load_token()
        except Exception as e:
            print(
                f"Error obtaining Strava access token: {e}\n"
                "If you are using auto-refresh, check STRAVA_CLIENT_ID, "
                "STRAVA_CLIENT_SECRET and STRAVA_REFRESH_TOKEN in your .env."
            )
            sys.exit(1)

        if not token:
            print(
                "Error: no Strava credentials found.\n"
                "Add ONE of the following to your .env file:\n"
                "  (recommended) STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN\n"
                "  (or) STRAVA_ACCESS_TOKEN=your_token_here\n"
                "Or run with --demo to render sample data offline."
            )
            sys.exit(1)

    width, height = args.width, args.height
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    try:
        if args.week:
            display_start_date, period_label = plugin.get_current_week_start()
            after_date = display_start_date - timedelta(seconds=1)
        else:
            days_back = args.days
            display_start_date = datetime.now() - timedelta(days=days_back - 1)
            display_start_date = display_start_date.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            after_date = display_start_date - timedelta(seconds=1)
            period_label = f"Last {days_back} Days" if days_back != 1 else "Today"

        if args.demo:
            print(f"Rendering demo data ({period_label})...")
            activities = _demo_activities(display_start_date)
        else:
            print(f"Fetching activities from Strava ({period_label})...")
            activities = plugin.fetch_strava_activities(token, after_date)

        if not activities:
            plugin.render_message(draw, width, height, "No activities found", period_label)
            print("No activities found for this period.")
        else:
            print(f"Fetched {len(activities)} activities. Rendering {args.mode} view...")
            stats = plugin.aggregate_activities(activities, args.time_type)

            if args.mode == "calendar":
                plugin.render_calendar(
                    draw, image, width, height,
                    activities, display_start_date, period_label, args.time_type,
                )
            elif args.mode == "combined":
                plugin.render_combined(
                    draw, image, width, height,
                    stats, activities, display_start_date, period_label, args.time_type,
                )
            else:
                plugin.render_stats(draw, width, height, stats, period_label)

    except Exception as e:
        plugin.render_message(draw, width, height, "Error", str(e))
        print(f"Error: {e}")

    image.save(args.output)
    print(f"Saved -> {args.output}")

    if not args.no_show:
        image.show()


if __name__ == "__main__":
    main()
