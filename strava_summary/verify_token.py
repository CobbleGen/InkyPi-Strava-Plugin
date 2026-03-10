"""
Quick script to verify your Strava access token.

This will test if your token is valid and show you what permissions it has.
"""

import os
import requests

# Get token from environment
token = os.environ.get("STRAVA_ACCESS_TOKEN")

if not token:
    print("❌ STRAVA_ACCESS_TOKEN not set in environment")
    print("\nSet it with:")
    print("  $env:STRAVA_ACCESS_TOKEN='your_token_here'")
    exit(1)

print("=" * 60)
print("Verifying Strava Access Token")
print("=" * 60)
print(f"\nToken: {token[:10]}...{token[-4:] if len(token) > 14 else ''}")

# Test 1: Get athlete info
print("\n1. Testing token with /athlete endpoint...")
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("https://www.strava.com/api/v3/athlete", headers=headers)

if response.status_code == 200:
    athlete = response.json()
    print(f"   ✓ Token valid!")
    print(f"   Athlete: {athlete.get('firstname')} {athlete.get('lastname')}")
    print(f"   ID: {athlete.get('id')}")
else:
    print(f"   ❌ Token invalid (status {response.status_code})")
    try:
        error = response.json()
        print(f"   Error: {error.get('message', 'Unknown error')}")
    except:
        print(f"   Response: {response.text}")
    exit(1)

# Test 2: Get activities
print("\n2. Testing activities endpoint...")
response = requests.get(
    "https://www.strava.com/api/v3/athlete/activities",
    headers=headers,
    params={"per_page": 5}
)

if response.status_code == 200:
    activities = response.json()
    print(f"   ✓ Can access activities!")
    print(f"   Found {len(activities)} recent activities")
    if activities:
        print(f"\n   Most recent:")
        for act in activities[:3]:
            activity_type = act.get('sport_type') or act.get('type', 'Unknown')
            distance_km = act.get('distance', 0) / 1000
            print(f"     - {act.get('name')}: {activity_type}, {distance_km:.1f} km")
else:
    print(f"   ❌ Cannot access activities (status {response.status_code})")
    try:
        error = response.json()
        print(f"   Error: {error.get('message', 'Unknown error')}")
    except:
        print(f"   Response: {response.text}")

print("\n" + "=" * 60)
print("Token verification complete!")
print("=" * 60)
