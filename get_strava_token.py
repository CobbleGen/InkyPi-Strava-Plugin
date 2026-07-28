#!/usr/bin/env python3
"""
One-time Strava OAuth helper.

Runs the full authorization-code flow and writes a working refresh token
(with activity:read_all scope) straight into your .env file, so preview.py
can mint fresh access tokens automatically from then on.

Usage:
    python get_strava_token.py

    # If port 8000 is taken, or your Strava callback domain differs:
    python get_strava_token.py --port 8721

Requirements:
    - Your Strava app's "Authorization Callback Domain" (on
      https://www.strava.com/settings/api) must be set to:  localhost
    - STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .env (or you'll be prompted)
    - pip install requests
"""

import argparse
import http.server
import os
import sys
import threading
import urllib.parse
import webbrowser

import requests

SCOPE = "activity:read_all"
_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")


# ---------------------------------------------------------------------------
# .env helpers (same format preview.py uses)
# ---------------------------------------------------------------------------

def _read_env_file():
    values = {}
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def _write_env_values(updates):
    lines = []
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH) as f:
            lines = f.read().splitlines()

    remaining = dict(updates)
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                out.append(f"{key}={remaining.pop(key)}")
                continue
        out.append(line)

    for key, val in remaining.items():
        out.append(f"{key}={val}")

    with open(_ENV_PATH, "w") as f:
        f.write("\n".join(out) + "\n")


# ---------------------------------------------------------------------------
# Tiny local server to catch the OAuth redirect
# ---------------------------------------------------------------------------

class _CodeCatcher(http.server.BaseHTTPRequestHandler):
    code = None
    error = None

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _CodeCatcher.code = params.get("code", [None])[0]
        _CodeCatcher.error = params.get("error", [None])[0]
        granted = params.get("scope", [""])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        if _CodeCatcher.code and "activity:read_all" in granted:
            msg = "Authorization complete. You can close this tab and return to the terminal."
        elif _CodeCatcher.code:
            msg = ("Authorized, but the 'activity:read_all' permission was NOT granted. "
                   "Re-run and tick that box on Strava's screen.")
        else:
            msg = f"Authorization failed: {_CodeCatcher.error or 'unknown error'}."
        self.wfile.write(f"<html><body style='font-family:sans-serif'><h3>{msg}</h3></body></html>".encode())

    def log_message(self, *args):
        pass  # silence default request logging


def main():
    parser = argparse.ArgumentParser(description="Get a Strava refresh token via OAuth.")
    parser.add_argument("--port", type=int, default=8000,
                        help="Local port for the redirect listener (default: 8000)")
    parser.add_argument("--no-browser", action="store_true",
                        help="Print the auth URL instead of opening a browser")
    args = parser.parse_args()

    env = _read_env_file()
    client_id = os.environ.get("STRAVA_CLIENT_ID") or env.get("STRAVA_CLIENT_ID")
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET") or env.get("STRAVA_CLIENT_SECRET")

    if not client_id:
        client_id = input("Strava Client ID: ").strip()
    if not client_secret:
        client_secret = input("Strava Client Secret: ").strip()
    if not client_id or not client_secret:
        print("Error: Client ID and Client Secret are required.")
        sys.exit(1)

    redirect_uri = f"http://localhost:{args.port}"
    auth_url = (
        "https://www.strava.com/oauth/authorize?"
        + urllib.parse.urlencode({
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "approval_prompt": "force",
            "scope": SCOPE,
        })
    )

    # Start the redirect listener before opening the browser.
    try:
        server = http.server.HTTPServer(("localhost", args.port), _CodeCatcher)
    except OSError as e:
        print(f"Error: could not bind to port {args.port} ({e}).")
        print("Try a different port:  python get_strava_token.py --port 8721")
        sys.exit(1)

    print("\nMake sure your Strava app's 'Authorization Callback Domain' is set to: localhost")
    print("\nOpening Strava authorization in your browser...")
    print("(On the Strava screen, leave the 'View data about your activities' box ticked.)\n")
    print(auth_url + "\n")
    if not args.no_browser:
        webbrowser.open(auth_url)

    # Serve a single request (the redirect), then stop.
    t = threading.Thread(target=server.handle_request)
    t.start()
    print(f"Waiting for authorization on {redirect_uri} ...")
    t.join(timeout=300)
    server.server_close()

    if _CodeCatcher.error:
        print(f"\nAuthorization was denied or failed: {_CodeCatcher.error}")
        sys.exit(1)
    if not _CodeCatcher.code:
        print("\nTimed out waiting for authorization (5 min). Please re-run.")
        sys.exit(1)

    print("Got authorization code. Exchanging it for tokens...")
    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": _CodeCatcher.code,
            "grant_type": "authorization_code",
        },
        timeout=(5, 15),
    )

    if resp.status_code != 200:
        detail = ""
        try:
            body = resp.json()
            errors = body.get("errors")
            if errors:
                detail = " - " + "; ".join(
                    f"{e.get('resource', '?')}.{e.get('field', '?')}: {e.get('code', '?')}"
                    for e in errors
                )
            elif body.get("message"):
                detail = f" - {body['message']}"
        except ValueError:
            detail = f" - {resp.text[:200]}" if resp.text else ""
        print(f"\nToken exchange failed: {resp.status_code}{detail}")
        print("Double-check your Client ID and Client Secret.")
        sys.exit(1)

    data = resp.json()
    granted = data.get("scope") or ""
    refresh_token = data["refresh_token"]

    _write_env_values({
        "STRAVA_CLIENT_ID": str(client_id),
        "STRAVA_CLIENT_SECRET": str(client_secret),
        "STRAVA_REFRESH_TOKEN": refresh_token,
        "STRAVA_ACCESS_TOKEN": data["access_token"],
        "STRAVA_TOKEN_EXPIRES_AT": str(data["expires_at"]),
    })

    print("\n Success! Tokens written to .env")
    print(f"   Refresh token: {refresh_token[:8]}...")
    if "activity:read_all" not in granted:
        print("\n WARNING: 'activity:read_all' was not granted (scope: "
              f"{granted or 'none'}). Activity reads will fail with 401.")
        print("   Re-run and make sure the activity box is ticked on Strava's screen.")
    else:
        print("\nYou can now run:  python preview.py --mode combined --week")


if __name__ == "__main__":
    main()
