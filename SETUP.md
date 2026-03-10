# Strava Summary Plugin - Setup Guide

A clean, simple plugin for InkyPi that displays your Strava activity summaries.

## Features

- 📊 Aggregated totals for all activities
- 🏃 Running-specific stats (Run, TrailRun, Treadmill)
- 🚴 Cycling-specific stats (Ride, VirtualRide, MountainBikeRide, etc.)
- 🏊 Swimming stats
- 📅 View last N days OR current week (Monday-Today)
- 🔄 Automatic token refresh (no manual token management!)

## Easy Setup (In InkyPi)

### Step 1: Create a Strava API Application

1. Go to [https://www.strava.com/settings/api](https://www.strava.com/settings/api)
2. Click **"Create an App"** (if you haven't already)
3. Fill in the form:
   - **Application Name**: "InkyPi Display" (or whatever you like)
   - **Category**: Choose something appropriate
   - **Club**: Leave blank
   - **Website**: Your InkyPi URL or `http://localhost`
   - **Authorization Callback Domain**: Your InkyPi domain (e.g., `inkypi.local` or `localhost`)
4. Click **Create**
5. You'll see your **Client ID** and **Client Secret** - keep this page open!

### Step 2: Configure the Plugin

1. In InkyPi, go to your plugin settings page
2. Enter your **Client ID** and **Client Secret** from Strava
3. Click **"Authorize with Strava"**
4. You'll be redirected to Strava - click **"Authorize"**
5. You'll be redirected back to InkyPi
6. Done! The plugin now has access to your activities

### Step 3: Choose Your Display Options

- **Time Range**: 
  - "Last N days" - rolling window (e.g., last 7 days)
  - "This week" - Monday to today
- **Days to look back**: Only shown for "Last N days" mode

## Token Management

The plugin automatically:
- ✅ Stores your access and refresh tokens
- ✅ Checks if tokens are expired before each use
- ✅ Refreshes tokens automatically when needed
- ✅ Shows authorization status in settings

You only need to re-authorize if:
- You revoke access on Strava
- You change your Client ID/Secret

## Local Testing (For Development)

### Quick Test with Environment Variable

```powershell
# Get a token from https://www.strava.com/settings/api
$env:STRAVA_ACCESS_TOKEN='your_token_here'
python test_local.py
```

### Full OAuth Test

```powershell
# Run the OAuth helper
python get_strava_token.py

# Follow the prompts and set the tokens:
$env:STRAVA_CLIENT_ID='your_client_id'
$env:STRAVA_CLIENT_SECRET='your_client_secret'
$env:STRAVA_ACCESS_TOKEN_OAUTH='token_from_script'
$env:STRAVA_REFRESH_TOKEN='refresh_from_script'

# Test the plugin
python test_local.py
```

### Verify Your Token

```powershell
python verify_token.py
```

This will tell you:
- ✓ If your token is valid
- ✓ Your athlete name/ID
- ✓ If it can access activities
- ❌ Specific error if something is wrong

## Installation

```bash
inkypi install strava_summary https://github.com/YOUR_USERNAME/InkyPi-Strava-Summary
```

## Display Shows

```
Strava Summary (This week)

Total:
45.3 km • 3h 42m

Running:
12.5 km • 1h 15m

Cycling:
32.8 km • 2h 27m
```

## Troubleshooting

**"Token expired and refresh failed"**
- Re-authorize in the settings page

**"Cannot access activities (status 401)"**
- Your token doesn't have `activity:read_all` scope
- Re-authorize using the settings page (it requests the correct scopes)

**"Authorization callback domain mismatch"**
- Make sure your Strava app's callback domain matches your InkyPi URL
- Common values: `localhost`, `inkypi.local`, your actual domain

**Token shows as expired in settings**
- This is OK! The plugin auto-refreshes on next run
- Or click "Authorize with Strava" again for a fresh token

## Activity Types Counted

**Running**: Run, TrailRun, Treadmill  
**Cycling**: Ride, VirtualRide, EBikeRide, MountainBikeRide, GravelRide  
**Swimming**: Swim  

All other activities are included in the "Total" but not in sport-specific breakdowns.

## Token Expiration

- Access tokens expire after **6 hours**
- The plugin automatically refreshes them using the refresh token
- Refresh tokens are long-lived (no manual intervention needed)
- If refresh fails, you'll see an error and need to re-authorize

## License

MIT License - See LICENSE.md
