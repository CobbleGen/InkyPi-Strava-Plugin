"""
Quick test to verify icon rendering with mock data (no Strava API needed)
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

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
from plugin_template import render_stats, load_activity_icon

# Test icon loading
print("Testing icon loading...")
print("=" * 60)

icons = ["Run", "Bike", "Swim", "Strava_Logo"]
for icon_name in icons:
    icon = load_activity_icon(icon_name, 32)
    if icon:
        print(f"✓ {icon_name}.png loaded successfully ({icon.width}x{icon.height})")
    else:
        print(f"✗ {icon_name}.png failed to load")

print("\n" + "=" * 60)
print("Rendering test image with mock stats...")
print("=" * 60)

# Create test image
width, height = 400, 300
image = Image.new("RGB", (width, height), "white")
draw = ImageDraw.Draw(image)

# Mock stats
stats = {
    'total_km': 45.3,
    'total_time_seconds': 13320,  # 3h 42m
    'run_km': 12.5,
    'run_time_seconds': 4500,  # 1h 15m
    'bike_km': 32.8,
    'bike_time_seconds': 8820,  # 2h 27m
    'swim_km': 0.5,
    'swim_time_seconds': 900,  # 15m
}

# Render
render_stats(draw, width, height, stats, "This Week")

# Save
output_path = "test_icons.png"
image.save(output_path)
print(f"\n✓ Test image saved to: {output_path}")
print(f"Open '{output_path}' to see the icons!\n")
print("=" * 60)
