import os
import re
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

    def detect_urls(self, text: str) -> Dict[str, List[str]]:
        """Detect and classify URLs in tweet text."""
        # URL pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        
        classified = {
            'x_articles': [],
            'external': [],
            'youtube': [],
            'other': []
        }
        
        for url in urls:
            if 'x.com/i/article' in url or 'twitter.com/i/article' in url:
                classified['x_articles'].append(url)
            elif 'youtube.com' in url or 'youtu.be' in url:
                classified['youtube'].append(url)
            elif any(domain in url for domain in ['substack.com', 'medium.com', 'blog.', 'newsletter']):
                classified['external'].append(url)
            else:
                classified['other'].append(url)
        
        return classified

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

            # Detect URLs
            urls = self.detect_urls(text)
            has_x_article = len(urls['x_articles']) > 0
            has_external = len(urls['external']) > 0
            
            # Apply Filter
            should_pass, reason = self.filter_engine.should_process(text, creator)
            
            # Special handling: X Articles pass filter but need manual extraction
            if has_x_article and not should_pass:
                should_pass = True
                reason = "X Article - requires manual extraction"
            
            item_data = {
                "source": "twitter",
                "source_id": tweet_id,
                "caption": text,
                "creator_username": creator,
                "timestamp": datetime.strptime(tweet['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ") if 'created_at' in tweet else datetime.utcnow(),
                "pre_filter_passed": should_pass,
                "filter_reason": reason,
                "media_url": None,  # Twitter text-only for now
                "has_x_article": has_x_article,
                "x_article_url": urls['x_articles'][0] if has_x_article else None,
                "external_url": urls['external'][0] if has_external else None
            }

            # Save
            db = SessionLocal()
            try:
                save_content_item(db, item_data)
                if should_pass:
                    all_curated_items.append(item_data)
                    if has_x_article:
                        print(f"✅ PASSED: [{creator}] X Article detected - {text[:40]}...")
                    else:
                        print(f"✅ PASSED: [{creator}] {text[:50]}...")
                else:
                    print(f"⏩ SKIPPED: [{creator}] Reason: {reason}")
            finally:
                db.close()

        return all_curated_items
