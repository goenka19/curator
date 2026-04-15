#!/usr/bin/env python3
"""
Simple test script to verify Twitter API credentials work.
This is a temporary test file - will be replaced by proper extractors later.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_twitter_credentials():
    """Test if Twitter API credentials are valid."""

    # Get credentials from environment
    bearer_token = os.getenv('TWITTER_BEARER_TOKEN')

    if not bearer_token or bearer_token == 'your_bearer_token_here':
        print("❌ ERROR: TWITTER_BEARER_TOKEN not set in .env file")
        print("   Please edit .env and add your actual Bearer Token")
        return False

    # Test endpoint - get authenticated user info (FREE - no cost)
    url = "https://api.twitter.com/2/users/me"
    headers = {
        "Authorization": f"Bearer {bearer_token}"
    }

    print("🔍 Testing Twitter API connection...")
    print(f"   Endpoint: {url}")
    print(f"   Bearer Token: {bearer_token[:20]}... (truncated for security)")
    print()

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            user_data = data.get('data', {})
            print("✅ SUCCESS! Twitter API credentials are valid")
            print(f"   Authenticated as: @{user_data.get('username')}")
            print(f"   User ID: {user_data.get('id')}")
            print(f"   Name: {user_data.get('name')}")
            print()
            print("🎉 You can now access your Twitter bookmarks!")
            return True

        elif response.status_code == 401:
            print("❌ ERROR: Unauthorized (401)")
            print("   Your Bearer Token is invalid or expired")
            print("   Please check your Twitter Developer Portal and get a new token")
            print()
            print(f"   Response: {response.text}")
            return False

        elif response.status_code == 403:
            print("❌ ERROR: Forbidden (403)")
            print("   Your app doesn't have the right permissions")
            print("   Make sure you have 'Read' permissions enabled")
            print()
            print(f"   Response: {response.text}")
            return False

        else:
            print(f"❌ ERROR: Unexpected status code {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Network error occurred")
        print(f"   {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Twitter API Credential Test")
    print("=" * 60)
    print()

    success = test_twitter_credentials()

    print()
    print("=" * 60)
    if success:
        print("✅ Next step: We can now build the Twitter extractor")
    else:
        print("❌ Please fix the credential issues above before continuing")
    print("=" * 60)
