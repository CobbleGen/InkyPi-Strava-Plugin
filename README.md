# InkyPi Strava Summary Plugin

A beautiful, feature-rich plugin for [InkyPi](https://github.com/fatihak/InkyPi) that displays your Strava activity summaries on e-ink displays.

## Features

✨ **Three Display Modes:**
- **Summary**: Aggregated totals with activity breakdown
- **Calendar**: 7-day visual calendar showing daily activities
- **Combined**: Summary stats + calendar in one view (default)

🏃 **Activity Tracking:**
- Running (Run, TrailRun, Treadmill)
- Cycling (Ride, VirtualRide, MountainBikeRide, GravelRide, EBikeRide)
- Swimming (Swim)

📅 **Flexible Time Ranges:**
- Last N days (rolling window)
- Current week (Monday to today)

🔐 **Easy OAuth Setup:**
- One-click authorization in settings
- Automatic token refresh
- No manual token management needed

## Screenshot

![Example of Strava Summary Plugin](./example.png)

## Installation

Install the plugin using the InkyPi CLI:

```bash
inkypi install strava_summary https://github.com/CobbleGen/InkyPi-Strava-Plugin
```

## Setup

### Step 1: Create a Strava API Application

1. Go to [https://www.strava.com/settings/api](https://www.strava.com/settings/api)
2. Click **"Create an App"**
3. Fill in the form:
   - **Application Name**: "InkyPi Display" (or your choice)
   - **Category**: Choose something appropriate
   - **Website**: Your InkyPi URL or `http://localhost`
   - **Authorization Callback Domain**: Your InkyPi domain (e.g., `inkypi.local` or `192.168.1.x`)
4. Click **Create**
5. Note your **Client ID** and **Client Secret**

### Step 2: Configure the Plugin

1. In InkyPi, add the Strava Summary plugin
2. Go to plugin settings
3. Enter your **Client ID** and **Client Secret**
4. Click **"Authorize with Strava"**
5. Authorize the app on Strava's page
6. You'll be redirected back automatically

### Step 3: Choose Display Options

- **Display Mode**: Summary, Calendar, or Combined
- **Time Range**: Rolling days or Current week
- **Days to look back**: Set for rolling mode (default: 7)

That's it! The plugin will automatically refresh your data and handle token expiration.

## Display Examples

### Summary Mode
Shows total distance, time, and breakdown by activity type.

### Calendar Mode
Visual 7-day calendar with activity icons for each day.

### Combined Mode (Default)
Compact summary stats at the top with a weekly calendar below - the best of both worlds!

## Troubleshooting

**"Token expired and refresh failed"**
- Re-authorize in the settings page
- Check that your Client ID and Secret are correct

**"Cannot access activities (status 401)"**
- Your token doesn't have the required permissions
- Re-authorize using the settings page (it requests `activity:read_all` scope)

**"Authorization callback domain mismatch"**
- Ensure your Strava app's callback domain matches your InkyPi URL
- Common values: `localhost`, `inkypi.local`, or your Pi's IP address

**No activities showing**
- Check that you have activities in the selected time period
- Verify the time range settings (rolling vs. current week)

## Activity Types

The plugin tracks these activity types:

**Running**: Run, TrailRun, Treadmill  
**Cycling**: Ride, VirtualRide, EBikeRide, MountainBikeRide, GravelRide  
**Swimming**: Swim  

Other activity types are included in totals but not shown in sport-specific breakdowns.

## Technical Details

- **Language**: Python 3
- **Dependencies**: requests, Pillow (installed automatically)
- **API**: Strava API v3
- **Authentication**: OAuth 2.0 with automatic token refresh
- **Token Expiration**: Access tokens expire after 6 hours (auto-refreshed)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Credits

Built for [InkyPi](https://github.com/fatihak/InkyPi) by the community.

Strava and the Strava logo are trademarks of Strava, Inc.
