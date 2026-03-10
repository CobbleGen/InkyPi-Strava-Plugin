"""
Helper script to get a Strava access token with the correct scopes.

This uses OAuth to authorize your app with activity:read permission.
"""

import os

# Get your app credentials from https://www.strava.com/settings/api
print("=" * 70)
print("Strava Token Generator")
print("=" * 70)
print()
print("First, get your Client ID and Client Secret from:")
print("https://www.strava.com/settings/api")
print()

client_id = input("Enter your Client ID: ").strip()
client_secret = input("Enter your Client Secret: ").strip()

if not client_id or not client_secret:
    print("\n❌ Both Client ID and Client Secret are required!")
    exit(1)

# Generate authorization URL
scopes = "activity:read_all"  # This allows reading all activities
auth_url = (
    f"https://www.strava.com/oauth/authorize?"
    f"client_id={client_id}&"
    f"redirect_uri=http://localhost&"
    f"response_type=code&"
    f"scope={scopes}"
)

print("\n" + "=" * 70)
print("STEP 1: Authorize the app")
print("=" * 70)
print("\n1. Open this URL in your browser:\n")
print(auth_url)
print("\n2. Click 'Authorize'")
print("3. You'll be redirected to localhost (which will fail - that's OK)")
print("4. Copy the 'code' parameter from the URL in your browser")
print("   Example: http://localhost?code=COPY_THIS_PART&scope=...")
print()

authorization_code = input("Paste the authorization code here: ").strip()

if not authorization_code:
    print("\n❌ Authorization code is required!")
    exit(1)

# Exchange code for token
print("\n" + "=" * 70)
print("STEP 2: Exchanging code for access token...")
print("=" * 70)

import requests

response = requests.post(
    "https://www.strava.com/oauth/token",
    data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": authorization_code,
        "grant_type": "authorization_code"
    }
)

if response.status_code == 200:
    token_data = response.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_at = token_data["expires_at"]
    
    print("\n✓ Success! Here's your access token:\n")
    print(f"ACCESS_TOKEN: {access_token}")
    print(f"\nREFRESH_TOKEN: {refresh_token}")
    print(f"EXPIRES_AT: {expires_at}")
    
    print("\n" + "=" * 70)
    print("STEP 3: Set the token in your environment")
    print("=" * 70)
    print("\nRun this command in PowerShell:\n")
    print(f"$env:STRAVA_ACCESS_TOKEN='{access_token}'")
    
    print("\n" + "=" * 70)
    print("Note: This token expires in 6 hours.")
    print("Save the REFRESH_TOKEN to get new access tokens later.")
    print("=" * 70)
    
else:
    print(f"\n❌ Failed to get token (status {response.status_code})")
    try:
        error = response.json()
        print(f"Error: {error}")
    except:
        print(f"Response: {response.text}")
