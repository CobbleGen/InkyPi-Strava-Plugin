"""
Local testing script for the Strava Summary plugin.

This script mocks the InkyPi environment so you can test the plugin
locally without needing to deploy it to an actual InkyPi device.

Usage:
    1. Set your STRAVA_ACCESS_TOKEN environment variable
    2. Run: python test_local.py
    3. Check the generated output.png image
"""

import os
import sys
from PIL import ImageFont


# Mock the InkyPi dependencies
class MockDeviceConfig:
    """Mock device_config object for local testing"""
    
    def __init__(self, width=400, height=300):
        self.width = width
        self.height = height
        
    def load_env_key(self, key):
        """Load environment variable (like STRAVA_ACCESS_TOKEN)"""
        value = os.environ.get(key)
        if not value:
            print(f"Warning: {key} not found in environment variables")
            print(f"Set it with: $env:{key}='your_token_here' (PowerShell)")
        return value
    
    def get_resolution(self):
        """Return mock display resolution"""
        return (self.width, self.height)
    
    def get_config(self, key):
        """Return mock config value"""
        if key == "orientation":
            return "horizontal"  # Change to "vertical" to test vertical layout
        return None


def mock_get_font(font_name, size):
    """
    Mock the get_font function from utils.app_utils
    
    Falls back to default PIL font if the specific font isn't available.
    For more realistic rendering, install the font or specify a path.
    """
    try:
        # Try to use a common system font
        # On Windows, try Arial or other common fonts
        font_paths = [
            f"C:/Windows/Fonts/arial.ttf",
            f"C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, int(size))
        
        # Fallback to default font
        print(f"Warning: Could not find system font, using default")
        return ImageFont.load_default()
    except Exception as e:
        print(f"Font loading error: {e}, using default")
        return ImageFont.load_default()


# Inject the mock function into the module namespace
sys.modules['utils'] = type(sys)('utils')
sys.modules['utils.app_utils'] = type(sys)('utils.app_utils')
sys.modules['utils.app_utils'].get_font = mock_get_font

sys.modules['plugins'] = type(sys)('plugins')
sys.modules['plugins.base_plugin'] = type(sys)('plugins.base_plugin')
sys.modules['plugins.base_plugin.base_plugin'] = type(sys)('plugins.base_plugin.base_plugin')


class BasePlugin:
    """Mock BasePlugin class"""
    pass


sys.modules['plugins.base_plugin.base_plugin'].BasePlugin = BasePlugin


# Now we can import the actual plugin
from plugin_template import Template


def test_plugin():
    """Run the plugin locally and save the output"""
    
    print("=" * 60)
    print("Testing Strava Summary Plugin Locally")
    print("=" * 60)
    
    # Create mock objects
    mock_device = MockDeviceConfig(width=400, height=300)
    
    # Check for access token
    token = os.environ.get("STRAVA_ACCESS_TOKEN")
    if not token:
        print("\n⚠️  STRAVA_ACCESS_TOKEN not set!")
        print("\nTo set it, run:")
        print("  PowerShell: $env:STRAVA_ACCESS_TOKEN='your_token_here'")
        print("  CMD:        set STRAVA_ACCESS_TOKEN=your_token_here")
        print("  Bash:       export STRAVA_ACCESS_TOKEN='your_token_here'")
        print("\nContinuing anyway (will show error in image)...\n")
    
    # Settings from the web form
    # Change these to test different configurations:
    
    # Option 1: Use OAuth tokens (recommended in production)
    # Fill these in after completing OAuth flow via get_strava_token.py
    settings = {
        "strava_client_id": os.environ.get("STRAVA_CLIENT_ID", ""),
        "strava_client_secret": os.environ.get("STRAVA_CLIENT_SECRET", ""),
        "access_token": os.environ.get("STRAVA_ACCESS_TOKEN_OAUTH", ""),  # From OAuth flow
        "refresh_token": os.environ.get("STRAVA_REFRESH_TOKEN", ""),
        "token_expires_at": os.environ.get("STRAVA_TOKEN_EXPIRES_AT", ""),
        "display_mode": "combined",  # Options: "summary", "calendar", or "combined"
        "time_mode": "current_week",  # Options: "rolling" or "current_week"
        "days_back": 7  # Only used when time_mode is "rolling"
    }
    
    # Option 2: Fall back to simple env variable (for quick testing)
    # If OAuth tokens not set, it will use STRAVA_ACCESS_TOKEN from environment
    
    print(f"\nConfiguration:")
    print(f"  Display size: {mock_device.width}×{mock_device.height}")
    print(f"  Display mode: {settings['display_mode']}")
    print(f"  Time mode: {settings['time_mode']}")
    if settings['time_mode'] == 'rolling':
        print(f"  Days back: {settings['days_back']}")
    else:
        print(f"  Range: This week (Monday-Today)")
    print(f"  Using OAuth tokens: {'Yes' if settings.get('access_token') else 'No (falling back to env)'}")
    print(f"  Fallback token set: {'Yes' if token else 'No'}")
    
    # Create plugin instance
    plugin = Template()
    
    # Generate the image
    print(f"\nGenerating image...")
    try:
        image = plugin.generate_image(settings, mock_device)
        
        # Save to file
        output_path = "output.png"
        image.save(output_path)
        print(f"✓ Image saved to: {output_path}")
        print(f"\nOpen '{output_path}' to view the result!")
        
    except Exception as e:
        print(f"\n✗ Error generating image: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_plugin()
