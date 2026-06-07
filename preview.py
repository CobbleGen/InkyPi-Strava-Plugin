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

Access token — provide one of:
    1. Environment variable:  STRAVA_ACCESS_TOKEN=<token>
    2. A .env file next to this script with:  STRAVA_ACCESS_TOKEN=<token>

Install dependencies (if not already installed):
    pip install pillow requests
"""

import argparse
import importlib.util
import os
import sys
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

def _load_token():
    token = os.environ.get("STRAVA_ACCESS_TOKEN")
    if token:
        return token

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("STRAVA_ACCESS_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")

    return None


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
        help="Use current week (Mon–today) instead of rolling days",
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
    args = parser.parse_args()

    token = _load_token()
    if not token:
        print(
            "Error: STRAVA_ACCESS_TOKEN not found.\n"
            "Set the environment variable or add it to a .env file:\n"
            "  STRAVA_ACCESS_TOKEN=your_token_here"
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

        print(f"Fetching activities from Strava ({period_label})…")
        activities = plugin.fetch_strava_activities(token, after_date)

        if not activities:
            plugin.render_message(draw, width, height, "No activities found", period_label)
            print("No activities found for this period.")
        else:
            print(f"Fetched {len(activities)} activities. Rendering {args.mode} view…")
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
    print(f"Saved → {args.output}")

    if not args.no_show:
        image.show()


if __name__ == "__main__":
    main()
