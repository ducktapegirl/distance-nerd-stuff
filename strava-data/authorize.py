#!/usr/bin/env python3
"""
Strava OAuth bootstrap — first-time authorization.

Run this once to create the local token file that fetch.py refreshes from then
on:

    uv run python strava-data/authorize.py

It opens a browser for the Strava consent screen, captures the callback on
localhost:8000, exchanges the code for tokens, and saves them to the same token
file fetch.py reads (strava-data/.strava_tokens.json). fetch.py itself only
*refreshes* an existing token — this is the only path that creates one from
scratch.

Requires STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET in strava-data/.env
(copy .env.example and fill in your credentials from
https://www.strava.com/settings/api).
"""

import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

# Reuse fetch.py's credential + token-file handling so there is one source of
# truth for where tokens live and which .env is read.
from fetch import CLIENT_ID, CLIENT_SECRET, TOKEN_URL, save_tokens

AUTH_URL = "https://www.strava.com/oauth/authorize"
REDIRECT_URI = "http://localhost:8000/callback"


def authorize_via_browser():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise SystemExit(
            "Missing STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET.\n"
            "Copy strava-data/.env.example to strava-data/.env and fill in your credentials."
        )

    auth_code = {"value": None}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            auth_code["value"] = params.get("code", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Authorized! You can close this tab.</h2>")

        def log_message(self, *args):
            pass  # suppress request logs

    params = urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": "activity:read_all",
    })
    url = f"{AUTH_URL}?{params}"
    print("\nOpening Strava authorization in your browser...")
    print(f"If it doesn't open automatically, visit:\n  {url}\n")
    webbrowser.open(url)

    server = HTTPServer(("localhost", 8000), CallbackHandler)
    server.handle_request()  # wait for exactly one callback

    code = auth_code["value"]
    if not code:
        raise SystemExit("Authorization failed — no code received.")

    resp = requests.post(TOKEN_URL, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    save_tokens(resp.json())
    print("Authorized successfully. Token saved.\n")


if __name__ == "__main__":
    authorize_via_browser()
