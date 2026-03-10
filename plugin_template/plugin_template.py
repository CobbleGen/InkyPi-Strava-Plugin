from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image, ImageDraw, ImageFont
from utils.app_utils import get_font
import logging
import requests
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# Activity type groupings for sport-specific totals
RUNNING_TYPES = {'Run', 'TrailRun', 'Treadmill'}
CYCLING_TYPES = {'Ride', 'VirtualRide', 'EBikeRide', 'MountainBikeRide', 'GravelRide'}
SWIMMING_TYPES = {'Swim'}


class Template(BasePlugin):
    """
    Strava Summary Plugin for InkyPi.

    Displays aggregated totals for activities from Strava:
    - Total distance and moving time for all activities
    - Running-specific totals
    - Cycling-specific totals
    - Swimming-specific totals
    """

    def generate_image(self, settings, device_config):
        """
        Generate and return a PIL image displaying Strava activity summaries.

        Args:
            settings (dict): Form values from settings.html (credentials, time_mode, days_back)
            device_config: Device config for loading secrets and resolution

        Returns:
            PIL.Image.Image: The rendered image to be displayed on the device.
        """
        # Get display dimensions
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]
        width, height = dimensions

        # Create image
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)

        try:
            # Get access token (with automatic refresh if needed)
            access_token = self._get_valid_access_token(settings, device_config)
            
            # Load configuration
            display_mode = settings.get("display_mode", "summary")
            time_mode = settings.get("time_mode", "rolling")
            days_back = int(settings.get("days_back", 7))
            
            # Calculate date range based on mode
            if time_mode == "current_week":
                after_date, period_label = get_current_week_start()
            else:
                after_date = datetime.now() - timedelta(days=days_back)
                period_label = f"{days_back}d"

            # Fetch activities from Strava
            activities = fetch_strava_activities(access_token, after_date)

            if not activities:
                render_message(draw, width, height, "No activities found", period_label)
            else:
                # Choose rendering mode
                if display_mode == "calendar":
                    # Calendar view with daily activities
                    render_calendar(draw, image, width, height, activities, after_date, period_label)
                elif display_mode == "combined":
                    # Combined view: summary + calendar
                    stats = aggregate_activities(activities)
                    render_combined(draw, image, width, height, stats, activities, after_date, period_label)
                else:
                    # Summary view with aggregated totals
                    stats = aggregate_activities(activities)
                    render_stats(draw, width, height, stats, period_label)

        except Exception as e:
            logger.error(f"Error fetching Strava data: {e}")
            render_message(draw, width, height, "Strava Error", str(e))

        logger.debug(f"Strava plugin rendered image ({width}×{height})")
        return image

    def _get_valid_access_token(self, settings, device_config):
        """
        Get a valid access token, refreshing if necessary.
        
        Tries in this order:
        1. Token from settings (with automatic refresh)
        2. Token from environment variable (backward compatibility)
        
        Args:
            settings (dict): Plugin settings
            device_config: Device configuration
            
        Returns:
            str: Valid access token
            
        Raises:
            Exception: If no token available or refresh fails
        """
        # Check if we have tokens in settings
        access_token = settings.get("access_token")
        refresh_token = settings.get("refresh_token")
        expires_at = settings.get("token_expires_at")
        
        if access_token and expires_at:
            # Check if token is expired or about to expire (within 5 minutes)
            now = int(datetime.now().timestamp())
            if int(expires_at) > now + 300:
                logger.debug("Using valid access token from settings")
                return access_token
            
            # Token expired, try to refresh
            if refresh_token:
                logger.info("Access token expired, attempting refresh")
                try:
                    new_token = refresh_access_token(
                        settings.get("strava_client_id"),
                        settings.get("strava_client_secret"),
                        refresh_token
                    )
                    
                    # Update settings with new token (note: this may not persist automatically)
                    settings["access_token"] = new_token["access_token"]
                    settings["refresh_token"] = new_token["refresh_token"]
                    settings["token_expires_at"] = new_token["expires_at"]
                    
                    logger.info("Token refreshed successfully")
                    return new_token["access_token"]
                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")
                    raise Exception("Token expired and refresh failed. Please re-authorize.")
        
        # Fall back to environment variable (backward compatibility)
        env_token = device_config.load_env_key("STRAVA_ACCESS_TOKEN")
        if env_token:
            logger.debug("Using access token from environment variable")
            return env_token
        
        # No token available
        raise Exception("No access token configured. Please authorize in settings.")


# ============================================================================
# STRAVA API CLIENT
# ============================================================================

def get_current_week_start():
    """
    Calculate the start of the current week (Monday).
    
    Returns:
        tuple: (start_datetime, label_string)
    """
    now = datetime.now()
    # weekday() returns 0=Monday, 6=Sunday
    days_since_monday = now.weekday()
    monday = now - timedelta(days=days_since_monday)
    # Set to beginning of Monday (00:00:00)
    monday_start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return monday_start, "This week"


def fetch_strava_activities(access_token, after_date):
    """
    Fetch activities from Strava API for the specified time period.

    Args:
        access_token (str): Strava API access token
        after_date (datetime): Start date for fetching activities

    Returns:
        list: List of activity dictionaries from Strava API

    Raises:
        Exception: If API request fails
    """
    if not access_token:
        raise Exception("STRAVA_ACCESS_TOKEN not configured")

    # Convert to Unix timestamp for API
    after_timestamp = int(after_date.timestamp())

    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "after": after_timestamp,
        "per_page": 100  # Fetch up to 100 activities (can be extended with pagination)
    }

    url = "https://www.strava.com/api/v3/athlete/activities"
    response = requests.get(url, headers=headers, params=params, timeout=10)

    if response.status_code != 200:
        error_detail = ""
        try:
            error_data = response.json()
            error_detail = f": {error_data.get('message', '')}"
        except:
            pass
        
        if response.status_code == 401:
            raise Exception(f"Token invalid or expired{error_detail}")
        else:
            raise Exception(f"API returned {response.status_code}{error_detail}")

    activities = response.json()
    logger.info(f"Fetched {len(activities)} activities from Strava")
    return activities


def refresh_access_token(client_id, client_secret, refresh_token):
    """
    Refresh an expired Strava access token.
    
    Args:
        client_id (str): Strava API client ID
        client_secret (str): Strava API client secret
        refresh_token (str): Refresh token
        
    Returns:
        dict: New token data with keys: access_token, refresh_token, expires_at
        
    Raises:
        Exception: If refresh fails
    """
    if not all([client_id, client_secret, refresh_token]):
        raise Exception("Client credentials and refresh token required")
    
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        },
        timeout=10
    )
    
    if response.status_code != 200:
        raise Exception(f"Token refresh failed: {response.status_code}")
    
    return response.json()


# ============================================================================
# AGGREGATION LOGIC
# ============================================================================

def aggregate_activities(activities):
    """
    Aggregate activity data into sport-specific and overall totals.

    Args:
        activities (list): List of Strava activity dictionaries

    Returns:
        dict: Aggregated statistics with keys:
            - total_km, total_time_seconds
            - run_km, run_time_seconds
            - bike_km, bike_time_seconds
            - swim_km, swim_time_seconds
    """
    stats = {
        'total_km': 0.0,
        'total_time_seconds': 0,
        'run_km': 0.0,
        'run_time_seconds': 0,
        'bike_km': 0.0,
        'bike_time_seconds': 0,
        'swim_km': 0.0,
        'swim_time_seconds': 0,
    }

    for activity in activities:
        # Safely extract fields (handle missing data)
        distance_meters = activity.get('distance', 0) or 0
        moving_time = activity.get('moving_time', 0) or 0
        sport_type = activity.get('sport_type') or activity.get('type', '')

        # Add to overall totals
        stats['total_km'] += meters_to_km(distance_meters)
        stats['total_time_seconds'] += moving_time

        # Add to sport-specific totals
        if sport_type in RUNNING_TYPES:
            stats['run_km'] += meters_to_km(distance_meters)
            stats['run_time_seconds'] += moving_time
        elif sport_type in CYCLING_TYPES:
            stats['bike_km'] += meters_to_km(distance_meters)
            stats['bike_time_seconds'] += moving_time
        elif sport_type in SWIMMING_TYPES:
            stats['swim_km'] += meters_to_km(distance_meters)
            stats['swim_time_seconds'] += moving_time

    return stats


def group_activities_by_day(activities, start_date):
    """
    Group activities by day for calendar view.
    
    Args:
        activities (list): List of Strava activity dictionaries
        start_date (datetime): Start date for the period
        
    Returns:
        dict: Dictionary mapping date strings (YYYY-MM-DD) to lists of activity dicts
              Example: {'2026-03-10': [{'type': 'Run', 'duration': 3600}, {'type': 'Bike', 'duration': 7200}]}
    """
    from datetime import datetime
    from collections import defaultdict
    
    # Create dict with empty lists for each day in the range
    days_dict = defaultdict(list)
    
    for activity in activities:
        # Get activity date (use start_date_local if available)
        date_str = activity.get('start_date_local') or activity.get('start_date', '')
        if not date_str:
            continue
            
        # Parse date (format: 2026-03-10T08:30:00Z)
        try:
            activity_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            date_key = activity_date.strftime('%Y-%m-%d')
            
            # Determine activity type icon name
            sport_type = activity.get('sport_type') or activity.get('type', '')
            moving_time = activity.get('moving_time', 0) or 0
            
            if sport_type in RUNNING_TYPES:
                icon_name = 'Run'
            elif sport_type in CYCLING_TYPES:
                icon_name = 'Bike'
            elif sport_type in SWIMMING_TYPES:
                icon_name = 'Swim'
            else:
                continue  # Skip other activity types
            
            # Add activity with duration info
            days_dict[date_key].append({
                'type': icon_name,
                'duration': moving_time
            })
                
        except Exception as e:
            logger.warning(f"Could not parse activity date: {date_str}, {e}")
            continue
    
    return days_dict


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def meters_to_km(meters):
    """Convert meters to kilometers."""
    return meters / 1000.0


def format_duration(seconds):
    """
    Format duration in seconds as human-readable string.

    Args:
        seconds (int): Duration in seconds

    Returns:
        str: Formatted duration like "2h 30m" or "45m"
    """
    if seconds <= 0:
        return "0m"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


# ============================================================================
# RENDERING
# ============================================================================

def load_activity_icon(icon_name, target_height):
    """
    Load and resize an activity icon from the images folder.
    
    Args:
        icon_name (str): Name of the icon (e.g., "Run", "Bike", "Swim")
        target_height (int): Target height for the icon (width scales proportionally)
        
    Returns:
        PIL.Image or None: Resized icon image, or None if not found
    """
    try:
        # Get the path to the images folder relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plugin_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(plugin_dir, "images", f"{icon_name}.png")
        
        if os.path.exists(icon_path):
            icon = Image.open(icon_path)
            
            # Calculate new width to maintain aspect ratio
            aspect_ratio = icon.width / icon.height
            new_width = int(target_height * aspect_ratio)
            
            # Resize maintaining aspect ratio
            icon = icon.resize((new_width, target_height), Image.LANCZOS)
            
            # Keep as RGBA to preserve colors and transparency
            if icon.mode != 'RGBA':
                icon = icon.convert('RGBA')
            return icon
    except Exception as e:
        logger.warning(f"Could not load icon {icon_name}: {e}")
    return None


def render_stats(draw, width, height, stats, period_label):
    """
    Render aggregated Strava statistics on the image with Strava-inspired design.

    Args:
        draw: PIL ImageDraw object
        width (int): Image width
        height (int): Image height
        stats (dict): Aggregated statistics
        period_label (str): Label for the time period (e.g., "7d" or "This week")
    """
    # Get the base image for pasting icons
    image = draw._image
    
    # Strava brand color (converted to grayscale for e-ink: use dark gray for accent)
    strava_accent = "#333333"  # Dark gray works better on e-ink than orange
    text_primary = "black"
    text_secondary = "#666666"
    
    # Font sizes - Strava uses bold numbers with smaller labels
    header_size = int(width * 0.045)
    big_number_size = int(width * 0.08)  # Large, bold numbers
    small_number_size = int(width * 0.05)
    tiny_label_size = int(width * 0.028)
    
    header_font = get_font("Jost", header_size)
    big_font = get_font("Jost", big_number_size)
    number_font = get_font("Jost", small_number_size)
    label_font = get_font("Jost", tiny_label_size)
    
    padding = int(width * 0.04)
    y_pos = padding
    
    # Load and place Strava logo in top right
    logo_height = int(header_size * 1.2)
    strava_logo = load_activity_icon("Strava_Logo", logo_height)
    if strava_logo:
        logo_x = width - padding - strava_logo.width
        image.paste(strava_logo, (logo_x, padding), strava_logo)
    
    # Header with period
    draw.text((padding, y_pos), period_label.upper(), fill=strava_accent, font=header_font)
    y_pos += header_size + int(padding * 0.3)
    
    # Draw a subtle line under header
    line_y = y_pos
    draw.line([(padding, line_y), (width - padding, line_y)], fill="#CCCCCC", width=2)
    y_pos += int(padding * 0.8)
    
    # Main stats section - emphasize total with big numbers
    if stats['total_km'] > 0:
        # Big total distance
        distance_text = f"{stats['total_km']:.1f}"
        draw.text((padding, y_pos), distance_text, fill=text_primary, font=big_font)
        
        # Unit label next to number (baseline aligned)
        bbox = draw.textbbox((0, 0), distance_text, font=big_font)
        text_width = bbox[2] - bbox[0]
        draw.text((padding + text_width + 5, y_pos + big_number_size - tiny_label_size - 5), 
                  "km", fill=text_secondary, font=label_font)
        
        y_pos += big_number_size + int(padding * 0.2)
        
        # Total time below
        time_text = format_duration(stats['total_time_seconds'])
        draw.text((padding, y_pos), time_text, fill=text_secondary, font=number_font)
        y_pos += number_font.size + int(padding * 1.2)
    
    # Activity breakdown - compact grid layout with icons
    activities = []
    if stats['run_km'] > 0:
        activities.append(("Run", "RUN", stats['run_km'], stats['run_time_seconds']))
    if stats['bike_km'] > 0:
        activities.append(("Bike", "RIDE", stats['bike_km'], stats['bike_time_seconds']))
    if stats['swim_km'] > 0:
        activities.append(("Swim", "SWIM", stats['swim_km'], stats['swim_time_seconds']))
    
    if activities:
        # Draw separator line
        draw.line([(padding, y_pos), (width - padding, y_pos)], fill="#CCCCCC", width=1)
        y_pos += int(padding * 0.8)
        
        # Icon size for activities
        icon_size = int(tiny_label_size * 1.5)
        
        # Grid layout for activities
        col_width = (width - 2 * padding) // min(len(activities), 3)
        
        for i, (icon_name, label_text, km, seconds) in enumerate(activities):
            # Calculate position (up to 3 columns)
            col = i % 3
            row = i // 3
            x_pos = padding + (col * col_width)
            current_y = y_pos + (row * int(padding * 3.5))
            
            # Load and place activity icon
            icon = load_activity_icon(icon_name, icon_size)
            if icon:
                image.paste(icon, (x_pos, current_y), icon)
                # Label next to icon
                draw.text((x_pos + icon_size + 5, current_y), label_text, 
                         fill=text_secondary, font=label_font)
                current_y += icon_size + 5
            else:
                # Fallback to text if icon not found
                draw.text((x_pos, current_y), label_text, fill=text_secondary, font=label_font)
                current_y += tiny_label_size + 5
            
            # Distance
            distance = f"{km:.1f}"
            draw.text((x_pos, current_y), distance, fill=text_primary, font=number_font)
            
            # Unit
            bbox = draw.textbbox((0, 0), distance, font=number_font)
            dist_width = bbox[2] - bbox[0]
            draw.text((x_pos + dist_width + 3, current_y + 3), "km", 
                     fill=text_secondary, font=label_font)
            current_y += number_font.size + 3
            
            # Time
            time_str = format_duration(seconds)
            draw.text((x_pos, current_y), time_str, fill=text_secondary, font=label_font)


def render_calendar(draw, image, width, height, activities, start_date, period_label):
    """
    Render a calendar view showing daily activities with icons and durations.
    
    Args:
        draw: PIL ImageDraw object
        image: PIL Image object (for pasting icons)
        width (int): Image width
        height (int): Image height
        activities (list): List of activity dictionaries from Strava
        start_date (datetime): Start date for the calendar
        period_label (str): Label for the time period
    """
    text_primary = "black"
    text_secondary = "#666666"
    
    # Font sizes
    header_size = int(width * 0.045)
    day_label_size = int(width * 0.035)
    date_size = int(width * 0.032)
    duration_size = int(width * 0.025)
    
    header_font = get_font("Jost", header_size)
    day_font = get_font("Jost", day_label_size)
    date_font = get_font("Jost", date_size)
    duration_font = get_font("Jost", duration_size)
    
    padding = int(width * 0.03)
    y_pos = padding
    
    # Load and place Strava logo in top right
    logo_height = int(header_size * 1.2)
    strava_logo = load_activity_icon("Strava_Logo", logo_height)
    if strava_logo:
        logo_x = width - padding - strava_logo.width
        image.paste(strava_logo, (logo_x, padding), strava_logo)
    
    # Header with period
    draw.text((padding, y_pos), period_label.upper(), fill=text_primary, font=header_font)
    y_pos += header_size + int(padding * 0.5)
    
    # Draw separator line
    draw.line([(padding, y_pos), (width - padding, y_pos)], fill="#CCCCCC", width=2)
    y_pos += int(padding * 0.8)
    
    # Group activities by day
    activities_by_day = group_activities_by_day(activities, start_date)
    
    # Generate 7 days starting from start_date
    days = []
    current = start_date
    for i in range(7):
        days.append(current + timedelta(days=i))
    
    # Calculate column width for 7 days
    col_width = (width - 2 * padding) // 7
    icon_size = int(col_width * 0.5)  # Icons sized to fit in column
    icon_size = min(icon_size, int(height * 0.15))  # Cap at 15% of height
    
    # Render each day column
    for i, day in enumerate(days):
        x_pos = padding + (i * col_width)
        current_y = y_pos
        
        # Day of week (Mon, Tue, etc.)
        day_name = day.strftime('%a').upper()
        draw.text((x_pos, current_y), day_name, fill=text_secondary, font=day_font)
        current_y += day_label_size + 3
        
        # Date (10)
        day_number = day.strftime('%d')
        draw.text((x_pos, current_y), day_number, fill=text_primary, font=date_font)
        current_y += date_size + int(padding * 0.5)
        
        # Activity icons for this day
        date_key = day.strftime('%Y-%m-%d')
        day_activities = activities_by_day.get(date_key, [])
        
        if day_activities:
            # Stack icons vertically under the date with duration
            for activity_data in day_activities[:3]:  # Max 3 activities per day
                activity_type = activity_data['type']
                duration = activity_data['duration']
                
                icon = load_activity_icon(activity_type, icon_size)
                if icon:
                    # Center icon in column (calculate center of column)
                    col_center_x = x_pos + (col_width // 2)
                    icon_x = col_center_x - (icon.width // 2)
                    image.paste(icon, (icon_x, current_y), icon)
                    current_y += icon.height + 2
                    
                    # Add duration below icon
                    duration_text = format_duration(duration)
                    bbox = draw.textbbox((0, 0), duration_text, font=duration_font)
                    duration_width = bbox[2] - bbox[0]
                    duration_x = col_center_x - (duration_width // 2)
                    draw.text((duration_x, current_y), duration_text, fill=text_secondary, font=duration_font)
                    current_y += duration_size + 5
        else:
            # Show a dot or dash for no activities
            dash_y = current_y + icon_size // 2
            col_center_x = x_pos + (col_width // 2)
            draw.line([(col_center_x - 5, dash_y), 
                      (col_center_x + 5, dash_y)], 
                     fill="#CCCCCC", width=2)


def render_combined(draw, image, width, height, stats, activities, start_date, period_label):
    """
    Render combined view with summary stats at top and calendar below.
    
    Args:
        draw: PIL ImageDraw object
        image: PIL Image object (for pasting icons)
        width (int): Image width
        height (int): Image height
        stats (dict): Aggregated statistics
        activities (list): List of activity dictionaries from Strava
        start_date (datetime): Start date for the calendar
        period_label (str): Label for the time period
    """
    text_primary = "black"
    text_secondary = "#666666"
    
    # Font sizes - give more space to summary section
    header_size = int(width * 0.045)
    stat_size = int(width * 0.055)
    tiny_size = int(width * 0.032)
    day_label_size = int(width * 0.028)
    duration_size = int(width * 0.022)
    
    header_font = get_font("Jost", header_size)
    stat_font = get_font("Jost", stat_size)
    tiny_font = get_font("Jost", tiny_size)
    day_font = get_font("Jost", day_label_size)
    duration_font = get_font("Jost", duration_size)
    
    padding = int(width * 0.03)
    y_pos = padding
    
    # Load and place Strava logo in top right
    logo_height = int(header_size * 1.2)
    strava_logo = load_activity_icon("Strava_Logo", logo_height)
    if strava_logo:
        logo_x = width - padding - strava_logo.width
        image.paste(strava_logo, (logo_x, padding), strava_logo)
    
    # Header
    draw.text((padding, y_pos), period_label.upper(), fill=text_primary, font=header_font)
    y_pos += header_size + int(padding * 0.4)
    
    # Separator
    draw.line([(padding, y_pos), (width - padding, y_pos)], fill="#CCCCCC", width=1)
    y_pos += int(padding * 0.8)
    
    # Summary stats - more spacious layout
    if stats['total_km'] > 0:
        # Total distance and time on one line
        total_text = f"{stats['total_km']:.1f} km • {format_duration(stats['total_time_seconds'])}"
        draw.text((padding, y_pos), total_text, fill=text_primary, font=stat_font)
        y_pos += stat_size + int(padding * 0.5)
        
        # Activity breakdown - horizontal icons with numbers and more spacing
        activities_summary = []
        if stats['run_km'] > 0:
            activities_summary.append(("Run", stats['run_km'], stats['run_time_seconds']))
        if stats['bike_km'] > 0:
            activities_summary.append(("Bike", stats['bike_km'], stats['bike_time_seconds']))
        if stats['swim_km'] > 0:
            activities_summary.append(("Swim", stats['swim_km'], stats['swim_time_seconds']))
        
        if activities_summary:
            icon_size = int(tiny_size * 1.5)
            x_offset = padding
            
            for activity_icon, km, seconds in activities_summary:
                # Icon
                icon = load_activity_icon(activity_icon, icon_size)
                if icon:
                    image.paste(icon, (x_offset, y_pos), icon)
                    x_offset += icon.width + 4
                
                # Distance
                dist_text = f"{km:.0f}"
                draw.text((x_offset, y_pos + 2), dist_text, fill=text_primary, font=tiny_font)
                bbox = draw.textbbox((0, 0), dist_text, font=tiny_font)
                x_offset += (bbox[2] - bbox[0]) + 3
                
                # Unit
                draw.text((x_offset, y_pos + 4), "km", fill=text_secondary, font=tiny_font)
                x_offset += 35  # More space before next activity
            
            y_pos += icon_size + int(padding * 0.8)
    
    # Separator before calendar
    draw.line([(padding, y_pos), (width - padding, y_pos)], fill="#CCCCCC", width=2)
    y_pos += int(padding * 0.7)
    
    # Calendar section
    # Group activities by day
    activities_by_day = group_activities_by_day(activities, start_date)
    
    # Generate 7 days
    days = []
    current = start_date
    for i in range(7):
        days.append(current + timedelta(days=i))
    
    # Calculate column width for 7 days
    col_width = (width - 2 * padding) // 7
    icon_size = int(col_width * 0.45)
    icon_size = min(icon_size, int((height - y_pos - padding) * 0.25))  # Cap based on remaining space
    
    # Render each day column
    for i, day in enumerate(days):
        x_pos = padding + (i * col_width)
        current_y = y_pos
        
        # Day of week (Mon, Tue, etc.)
        day_name = day.strftime('%a').upper()
        # Center day name in column
        bbox = draw.textbbox((0, 0), day_name, font=day_font)
        day_width = bbox[2] - bbox[0]
        col_center_x = x_pos + (col_width // 2)
        day_x = col_center_x - (day_width // 2)
        draw.text((day_x, current_y), day_name, fill=text_secondary, font=day_font)
        current_y += day_label_size + 2
        
        # Date (10)
        day_number = day.strftime('%d')
        bbox = draw.textbbox((0, 0), day_number, font=day_font)
        date_width = bbox[2] - bbox[0]
        date_x = col_center_x - (date_width // 2)
        draw.text((date_x, current_y), day_number, fill=text_primary, font=day_font)
        current_y += day_label_size + int(padding * 0.3)
        
        # Activity icons for this day
        date_key = day.strftime('%Y-%m-%d')
        day_activities = activities_by_day.get(date_key, [])
        
        if day_activities:
            # Stack icons vertically under the date with duration
            for activity_data in day_activities[:2]:  # Max 2 activities per day in combined view
                activity_type = activity_data['type']
                duration = activity_data['duration']
                
                icon = load_activity_icon(activity_type, icon_size)
                if icon:
                    # Center icon in column
                    icon_x = col_center_x - (icon.width // 2)
                    image.paste(icon, (icon_x, current_y), icon)
                    current_y += icon.height + 1
                    
                    # Add duration below icon
                    duration_text = format_duration(duration)
                    bbox = draw.textbbox((0, 0), duration_text, font=duration_font)
                    duration_width = bbox[2] - bbox[0]
                    duration_x = col_center_x - (duration_width // 2)
                    draw.text((duration_x, current_y), duration_text, fill=text_secondary, font=duration_font)
                    current_y += duration_size + 3
        else:
            # Show a dash for no activities
            dash_y = current_y + icon_size // 2
            draw.line([(col_center_x - 4, dash_y), 
                      (col_center_x + 4, dash_y)], 
                     fill="#CCCCCC", width=2)


def render_message(draw, width, height, line1, line2):
    """
    Render a simple message with Strava-inspired styling (used for errors or empty states).

    Args:
        draw: PIL ImageDraw object
        width (int): Image width
        height (int): Image height
        line1 (str): First line of message (header)
        line2 (str): Second line of message (detail)
    """
    padding = int(width * 0.04)
    title_size = int(width * 0.06)
    subtitle_size = int(width * 0.04)
    
    title_font = get_font("Jost", title_size)
    subtitle_font = get_font("Jost", subtitle_size)
    
    # Draw a border box
    box_padding = padding * 2
    box_top = height // 3
    box_height = int(height * 0.35)
    
    # Light gray box background effect (just borders for e-ink)
    draw.rectangle(
        [(box_padding, box_top), (width - box_padding, box_top + box_height)],
        outline="#999999",
        width=2
    )
    
    # Center first line (title)
    bbox = draw.textbbox((0, 0), line1, font=title_font)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    y = box_top + int(box_height * 0.25)
    
    draw.text((x, y), line1, fill="black", font=title_font)

    # Center second line (subtitle)
    if line2:
        bbox2 = draw.textbbox((0, 0), line2, font=subtitle_font)
        text_width2 = bbox2[2] - bbox2[0]
        x2 = (width - text_width2) // 2
        y2 = y + int(title_size * 1.5)
        draw.text((x2, y2), line2, fill="#666666", font=subtitle_font)
