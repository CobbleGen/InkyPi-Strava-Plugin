"""
Test calendar view with mock activity data (no Strava API needed)
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# Mock the InkyPi dependencies
sys.modules['utils'] = type(sys)('utils')
sys.modules['utils.app_utils'] = type(sys)('utils.app_utils')

def mock_get_font(font_name, size):
    """Mock font loading"""
    try:
        font_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, int(size))
        return ImageFont.load_default()
    except:
        return ImageFont.load_default()

sys.modules['utils.app_utils'].get_font = mock_get_font

sys.modules['plugins'] = type(sys)('plugins')
sys.modules['plugins.base_plugin'] = type(sys)('plugins.base_plugin')
sys.modules['plugins.base_plugin.base_plugin'] = type(sys)('plugins.base_plugin.base_plugin')

class BasePlugin:
    pass

sys.modules['plugins.base_plugin.base_plugin'].BasePlugin = BasePlugin

# Import the render functions
from plugin_template import render_calendar

# Create mock activities for the past week
def create_mock_activities():
    """Generate mock activities for testing calendar view"""
    activities = []
    now = datetime.now()
    
    # Get Monday of this week
    days_since_monday = now.weekday()
    monday = now - timedelta(days=days_since_monday)
    
    # Create activities for the week
    # Monday: Run
    activities.append({
        'start_date_local': (monday + timedelta(hours=8)).isoformat(),
        'sport_type': 'Run',
        'distance': 5000,
        'moving_time': 1800
    })
    
    # Tuesday: Bike
    activities.append({
        'start_date_local': (monday + timedelta(days=1, hours=17)).isoformat(),
        'sport_type': 'Ride',
        'distance': 25000,
        'moving_time': 3600
    })
    
    # Wednesday: Run + Swim
    activities.append({
        'start_date_local': (monday + timedelta(days=2, hours=7)).isoformat(),
        'sport_type': 'Run',
        'distance': 8000,
        'moving_time': 2400
    })
    activities.append({
        'start_date_local': (monday + timedelta(days=2, hours=18)).isoformat(),
        'sport_type': 'Swim',
        'distance': 1500,
        'moving_time': 1200
    })
    
    # Thursday: Rest day (no activities)
    
    # Friday: Bike + Run
    activities.append({
        'start_date_local': (monday + timedelta(days=4, hours=6)).isoformat(),
        'sport_type': 'Ride',
        'distance': 40000,
        'moving_time': 5400
    })
    activities.append({
        'start_date_local': (monday + timedelta(days=4, hours=19)).isoformat(),
        'sport_type': 'TrailRun',
        'distance': 6000,
        'moving_time': 2100
    })
    
    # Saturday: Run
    activities.append({
        'start_date_local': (monday + timedelta(days=5, hours=9)).isoformat(),
        'sport_type': 'Run',
        'distance': 12000,
        'moving_time': 3600
    })
    
    # Sunday (today): Bike
    if now.weekday() == 6:  # If today is Sunday
        activities.append({
            'start_date_local': (monday + timedelta(days=6, hours=10)).isoformat(),
            'sport_type': 'Ride',
            'distance': 30000,
            'moving_time': 4200
        })
    
    return activities, monday


print("=" * 60)
print("Testing Calendar View with Mock Data")
print("=" * 60)

# Create test image
width, height = 400, 300
image = Image.new("RGB", (width, height), "white")
draw = ImageDraw.Draw(image)

# Generate mock data
activities, start_date = create_mock_activities()
print(f"\nGenerated {len(activities)} mock activities")
print(f"Week starting: {start_date.strftime('%Y-%m-%d (%A)')}")

# Render calendar
render_calendar(draw, image, width, height, activities, start_date, "This Week")

# Save
output_path = "test_calendar.png"
image.save(output_path)
print(f"\n✓ Calendar view saved to: {output_path}")
print(f"Open '{output_path}' to see the weekly calendar!\n")
print("=" * 60)
