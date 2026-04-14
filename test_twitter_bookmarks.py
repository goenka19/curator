#!/usr/bin/env python3
"""
Test script to verify Twitter API can access bookmarks.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_twitter_bookmarks():
    """Test if we can access Twitter bookmarks."""

    # Use OAuth 2.0 access token (required for bookmarks)
    access_token = os.getenv('TWITTER_OAUTH2_ACCESS_TOKEN')

    if not access_token:
        print("❌ ERROR: TWITTER_OAUTH2_ACCESS_TOKEN not set")
        print("   Run: python oauth2_authenticate.py")
        return False

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    print("🔍 Step 1: Getting your user ID...")

    # First, get the authenticated user's ID
    try:
        me_response = requests.get(
            "https://api.twitter.com/2/users/me",
            headers=headers
        )

        if me_response.status_code != 200:
            print(f"❌ Failed to get user ID: {me_response.status_code}")
            print(f"   Response: {me_response.text}")
            return False

        user_id = me_response.json()['data']['id']
        print(f"   ✅ User ID: {user_id}")
        print()

    except Exception as e:
        print(f"❌ Error getting user ID: {e}")
        return False

    # Now fetch bookmarks using the user ID
    print("🔍 Step 2: Fetching your bookmarks...")
    print(f"   This will fetch your 5 most recent bookmarks")
    print(f"   Cost: $0.025 (5 tweets × $0.005)")
    print()

    url = f"https://api.twitter.com/2/users/{user_id}/bookmarks"
    params = {
        "max_results": 5,
        "tweet.fields": "created_at,author_id,text"
    }

    try:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            bookmarks = data.get('data', [])
            print(f"✅ SUCCESS! Retrieved {len(bookmarks)} bookmarks")
            print()

            if bookmarks:
                print("Sample bookmarks:")
                for i, tweet in enumerate(bookmarks[:3], 1):
                    text = tweet.get('text', '')[:60]
                    print(f"   {i}. {text}...")
            else:
                print("   (You have no bookmarks yet)")

            print()
            print("🎉 Twitter API is working! You can access your bookmarks!")
            return True

        elif response.status_code == 401:
            print("❌ ERROR: Unauthorized (401)")
            print("   Your OAuth 2.0 access token is invalid or expired")
            print()
            print("   Run: python oauth2_authenticate.py")
            print()
            print(f"   Response: {response.text}")
            return False

        elif response.status_code == 403:
            error_data = response.json()
            print("❌ ERROR: Forbidden (403)")
            print(f"   {error_data.get('detail', 'Unknown error')}")
            print()
            print("   Your OAuth 2.0 token may not have the required scopes.")
            print("   Try re-authenticating: python oauth2_authenticate.py")
            print()
            print(f"   Full response: {response.text}")
            return False

        else:
            print(f"❌ ERROR: Status code {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("Twitter Bookmarks API Test")
    print("=" * 70)
    print()

    success = test_twitter_bookmarks()

    print()
    print("=" * 70)
    if success:
        print("✅ Ready to build the content curator!")
    else:
        print("❌ Need to fix authentication setup")
    print("=" * 70)
