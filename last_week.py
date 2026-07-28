#!/usr/bin/env python3
"""
Generate a summary image for a completed week, named after that week so the
images stack up in date order as an archive.

Usage:
    python last_week.py                  # last week, combined view
    python last_week.py --mode summary   # totals only
    python last_week.py --elevation      # include climbing
    python last_week.py --weeks-ago 3    # three weeks back, for backfilling
    python last_week.py --dir weeks      # write into a folder
    python last_week.py --landscape      # on its side, like the e-ink panel
    python last_week.py --demo           # sample data, no credentials needed

Images are upright (448x600) by default, since these are meant to be saved and
looked at rather than shown on a panel. Use --landscape, or --width/--height,
for other shapes.

Weeks run Monday to Sunday, and only completed weeks are offered - the current
week is still in progress, so use `python preview.py --week` for that.

Output is named like strava-2026-W30.png (ISO year and week), so the files
sort chronologically. Pass --output to override.

Credentials come from .env exactly as preview.py uses them; run
get_strava_token.py once to set that up.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

import preview  # sits alongside this script; brings in the plugin renderers


def week_bounds(weeks_ago=1):
    """
    Bounds of a completed week, counting back from the current one.

    Args:
        weeks_ago (int): 1 is the week just gone, 2 the one before it

    Returns:
        tuple: (monday, next_monday) where next_monday is an exclusive end
    """
    now = datetime.now()
    this_monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    monday = this_monday - timedelta(weeks=weeks_ago)
    return monday, monday + timedelta(days=7)


def week_label(monday, sunday, weeks_ago):
    """Human label for the image header, e.g. 'Last week' or '20 - 26 Jul'."""
    if weeks_ago == 1:
        return "Last week"
    if monday.month == sunday.month:
        return f"{monday.day} - {sunday.day} {sunday:%b}"
    return f"{monday.day} {monday:%b} - {sunday.day} {sunday:%b}"


def week_filename(monday):
    """ISO-week filename so images sort chronologically: strava-2026-W30.png"""
    iso_year, iso_week, _ = monday.isocalendar()
    return f"strava-{iso_year}-W{iso_week:02d}.png"


def main():
    parser = argparse.ArgumentParser(
        description="Generate a summary image for a completed week.")
    parser.add_argument(
        "--weeks-ago", type=int, default=1, dest="weeks_ago",
        help="How many weeks back (default: 1, the week just gone)",
    )
    parser.add_argument(
        "--mode", choices=["combined", "summary", "calendar"], default="combined",
        help="Display mode (default: combined)",
    )
    parser.add_argument(
        "--time-type", choices=["moving_time", "elapsed_time"], default="moving_time",
        dest="time_type", help="Which Strava time field to use (default: moving_time)",
    )
    parser.add_argument("--elevation", action="store_true",
                        help="Include elevation gain")
    parser.add_argument("--width", type=int, default=448, help="Image width (default: 448)")
    parser.add_argument("--height", type=int, default=600, help="Image height (default: 600)")
    parser.add_argument("--landscape", action="store_true",
                        help="Render on its side instead of upright (swaps width and height)")
    parser.add_argument("--output", help="Output path (default: strava-YYYY-Www.png)")
    parser.add_argument("--dir", dest="directory", default=".",
                        help="Directory to write into (default: current directory)")
    parser.add_argument("--no-show", action="store_true",
                        help="Save the image but do not open it")
    parser.add_argument("--demo", action="store_true",
                        help="Render sample data offline (no credentials needed)")
    args = parser.parse_args()

    if args.weeks_ago < 1:
        print("Error: --weeks-ago must be 1 or more; the current week is not finished yet.\n"
              "For the week in progress, run:  python preview.py --week")
        sys.exit(1)

    monday, next_monday = week_bounds(args.weeks_ago)
    sunday = next_monday - timedelta(days=1)
    label = week_label(monday, sunday, args.weeks_ago)

    if args.output:
        output = args.output
    else:
        output = os.path.join(args.directory, week_filename(monday))
        if args.directory != ".":
            os.makedirs(args.directory, exist_ok=True)

    # Upright by default; these are saved and looked at, not shown on a panel
    width, height = min(args.width, args.height), max(args.width, args.height)
    if args.landscape:
        width, height = height, width

    print(f"Week of {monday:%Y-%m-%d} to {sunday:%Y-%m-%d}")

    # "after" is exclusive, so step back a second to include Monday 00:00:00;
    # "before" keeps the following week out of a closed window.
    preview.render_image(
        mode=args.mode,
        time_type=args.time_type,
        width=width,
        height=height,
        output=output,
        show=not args.no_show,
        demo=args.demo,
        elevation=args.elevation,
        period=(monday, monday - timedelta(seconds=1), next_monday, label),
    )


if __name__ == "__main__":
    main()
