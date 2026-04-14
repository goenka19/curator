import os
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.extractors.base_extractor import BaseExtractor
from backend.filtering.engine import FilteringEngine
from backend.database import SessionLocal, is_duplicate, save_content_item

class TwitterExtractor(BaseExtractor):
    def __init__(self):
        super().__init__(api_name='twitter')
        self.access_token = os.getenv('TWITTER_OAUTH2_ACCESS_TOKEN')
        self.base_url = "https://api.twitter.com/2"
        self.filter_engine = FilteringEngine()

    def fetch_bookmarks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetches Twitter Bookmarks using OAuth 2.0.
        """
        if not self.access_token:
            print("❌ ERROR: TWITTER_OAUTH2_ACCESS_TOKEN not set in .env")
            return []

        limit = self.check_dev_limit(limit)
        print(f"🚀 Syncing Twitter Bookmarks...")

        # 1. Get current user ID
        user_url = f"{self.base_url}/users/me"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        user_resp = requests.get(user_url, headers=headers)
        if user_resp.status_code != 200:
            print(f"❌ Failed to fetch Twitter user: {user_resp.text}")
            return []
            
        user_id = user_resp.json().get('data', {}).get('id')
        
        # 2. Get bookmarks
        bookmark_url = f"{self.base_url}/users/{user_id}/bookmarks"
        params = {
            "tweet.fields": "created_at,text,author_id,attachments",
            "expansions": "author_id",
            "user.fields": "username",
            "max_results": min(limit, 100)
        }
        
        resp = requests.get(bookmark_url, headers=headers, params=params)
        if resp.status_code != 200:
            print(f"❌ Failed to fetch Twitter bookmarks: {resp.text}")
            return []

        data = resp.json()
        tweets = data.get('data', [])
        includes = data.get('includes', {}).get('users', [])
        user_map = {u['id']: u['username'] for u in includes}
        
        all_curated_items = []

        for tweet in tweets:
            tweet_id = tweet['id']
            
            # Deduplication
            db = SessionLocal()
            try:
                if is_duplicate(db, tweet_id):
                    continue
            finally:
                db.close()

            text = tweet.get('text', '')
            author_id = tweet.get('author_id')
            creator = user_map.get(author_id, 'unknown')

            # Apply Filter
            should_pass, reason = self.filter_engine.should_process(text, creator)
            
            item_data = {
                "source": "twitter",
                "source_id": tweet_id,
                "caption": text,
                "creator_username": creator,
                "timestamp": datetime.strptime(tweet['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ") if 'created_at' in tweet else datetime.utcnow(),
                "pre_filter_passed": should_pass,
                "filter_reason": reason,
                "media_url": None  # Twitter text-only for now
            }

            # Save
            db = SessionLocal()
            try:
                save_content_item(db, item_data)
                if should_pass:
                    all_curated_items.append(item_data)
                    print(f"✅ PASSED: [{creator}] {text[:50]}...")
                else:
                    print(f"⏩ SKIPPED: [{creator}] Reason: {reason}")
            finally:
                db.close()

        return all_curated_items
