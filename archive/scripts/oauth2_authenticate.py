#!/usr/bin/env python3
"""
Twitter OAuth 2.0 Authentication Script
Handles PKCE flow and saves token to .env
"""

import os
import hashlib
import base64
import secrets
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, parse_qs, urlparse
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OAuth 2.0 Configuration
CLIENT_ID = os.getenv('TWITTER_CLIENT_ID')
CLIENT_SECRET = os.getenv('TWITTER_CLIENT_SECRET')
REDIRECT_URI = 'http://127.0.0.1:8080/callback'
SCOPES = ['tweet.read', 'users.read', 'bookmark.read', 'offline.access']

# Twitter OAuth URLs
AUTH_URL = 'https://twitter.com/i/oauth2/authorize'
TOKEN_URL = 'https://api.twitter.com/2/oauth2/token'

# Global variables for OAuth flow
code_verifier = None
authorization_code = None


def generate_pkce_pair():
    """Generate PKCE code verifier and code challenge."""
    global code_verifier

    # Generate code verifier (43-128 characters)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
    code_verifier = code_verifier.replace('=', '')  # Remove padding

    # Generate code challenge (SHA256 hash of verifier)
    challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(challenge).decode('utf-8')
    code_challenge = code_challenge.replace('=', '')  # Remove padding

    return code_verifier, code_challenge


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass

    def do_GET(self):
        """Handle GET request from OAuth callback."""
        global authorization_code

        # Parse the callback URL
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if 'code' in params:
            authorization_code = params['code'][0]

            # Send success response to browser
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
                <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: #1DA1F2;">Success!</h1>
                    <p>Authorization successful. You can close this window.</p>
                    <p>Return to your terminal to complete the setup.</p>
                </body>
                </html>
            ''')
        elif 'error' in params:
            error = params['error'][0]
            error_desc = params.get('error_description', ['Unknown error'])[0]

            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f'''
                <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: #E0245E;">Error</h1>
                    <p>{error}: {error_desc}</p>
                    <p>Return to your terminal and try again.</p>
                </body>
                </html>
            '''.encode())
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Invalid callback')


def exchange_code_for_token(auth_code, code_verifier):
    """Exchange authorization code for access token."""
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI,
        'code_verifier': code_verifier,
        'client_id': CLIENT_ID,
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    # Use Basic Auth with client_id and client_secret
    auth = (CLIENT_ID, CLIENT_SECRET)

    response = requests.post(TOKEN_URL, data=data, headers=headers, auth=auth)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Token exchange failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None


def save_token_to_env(token_data):
    """Save access token to .env file."""
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')

    if not access_token:
        print("❌ No access token in response")
        return False

    # Read current .env
    with open('.env', 'r') as f:
        lines = f.readlines()

    # Update or add tokens
    updated = False
    refresh_updated = False

    with open('.env', 'w') as f:
        for line in lines:
            if line.startswith('TWITTER_OAUTH2_ACCESS_TOKEN='):
                f.write(f'TWITTER_OAUTH2_ACCESS_TOKEN={access_token}\n')
                updated = True
            elif line.startswith('TWITTER_OAUTH2_REFRESH_TOKEN='):
                if refresh_token:
                    f.write(f'TWITTER_OAUTH2_REFRESH_TOKEN={refresh_token}\n')
                    refresh_updated = True
                else:
                    f.write(line)
            else:
                f.write(line)

        # Add if not found
        if not updated:
            f.write(f'\n# OAuth 2.0 Access Token\nTWITTER_OAUTH2_ACCESS_TOKEN={access_token}\n')

        if refresh_token and not refresh_updated:
            f.write(f'TWITTER_OAUTH2_REFRESH_TOKEN={refresh_token}\n')

    print(f"✅ Access token saved to .env")
    if refresh_token:
        print(f"✅ Refresh token saved to .env")

    return True


def main():
    """Main OAuth 2.0 flow."""
    print("=" * 70)
    print("Twitter OAuth 2.0 Authentication")
    print("=" * 70)
    print()

    # Check credentials
    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ ERROR: TWITTER_CLIENT_ID or TWITTER_CLIENT_SECRET not set in .env")
        return

    print(f"Client ID: {CLIENT_ID[:20]}...")
    print(f"Redirect URI: {REDIRECT_URI}")
    print()

    # Generate PKCE pair
    verifier, challenge = generate_pkce_pair()
    print("✅ Generated PKCE code challenge")

    # Build authorization URL
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': ' '.join(SCOPES),
        'state': secrets.token_urlsafe(16),
        'code_challenge': challenge,
        'code_challenge_method': 'S256',
    }

    auth_url = f"{AUTH_URL}?{urlencode(params)}"

    print("\n🌐 Opening browser for authorization...")
    print("   If browser doesn't open, visit this URL:")
    print(f"   {auth_url[:80]}...")
    print()

    # Open browser
    webbrowser.open(auth_url)

    # Start local server to catch callback
    print("🔄 Starting local server on 127.0.0.1:8080...")
    print("   Waiting for authorization...")
    print()

    server = HTTPServer(('127.0.0.1', 8080), OAuthCallbackHandler)

    # Handle one request (the callback)
    server.handle_request()

    if not authorization_code:
        print("\n❌ No authorization code received")
        return

    print("✅ Authorization code received")
    print("\n🔄 Exchanging code for access token...")

    # Exchange code for token
    token_data = exchange_code_for_token(authorization_code, verifier)

    if not token_data:
        print("\n❌ Failed to get access token")
        return

    print("✅ Access token received")

    # Save to .env
    if save_token_to_env(token_data):
        print("\n🎉 Authentication complete!")
        print("\nNext step:")
        print("  python tests/test_twitter_bookmarks.py")
    else:
        print("\n❌ Failed to save token")


if __name__ == '__main__':
    main()
