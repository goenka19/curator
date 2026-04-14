"""
Instagram Reel Extractor using API Hut
Downloads reels from Instagram without login required
"""

import os
import re
import requests
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
from backend.extractors.base_extractor import BaseExtractor
from backend.database import SessionLocal, is_duplicate, save_content_item, log_api_cost


class InstagramExtractor(BaseExtractor):
    """
    Extracts Instagram reels using API Hut (no login required).
    """
    
    def __init__(self):
        super().__init__(api_name='instagram')
        # Get API key from environment or use free tier demo key
        self.api_key = os.getenv('APIHUT_KEY', 'avatarhubadmin')
        self.base_url = 'https://apihut.in/api'
        self.download_dir = Path(os.getenv('MEDIA_DOWNLOAD_DIR', 'data/media'))
        self.download_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_shortcode(self, url: str) -> Optional[str]:
        """Extract shortcode from Instagram reel URL."""
        patterns = [
            r'instagram\.com/reel/([A-Za-z0-9_-]+)',
            r'instagram\.com/reels/([A-Za-z0-9_-]+)',
            r'instagr\.am/p/([A-Za-z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def download_reel(self, reel_url: str) -> Optional[Dict]:
        """
        Download Instagram reel using API Hut.
        
        Returns:
            Dict with:
                - success: bool
                - shortcode: str
                - video_url: str (direct download URL)
                - thumbnail_url: str (optional)
                - local_path: str (downloaded file path)
                - error: str (if failed)
        """
        shortcode = self.extract_shortcode(reel_url)
        if not shortcode:
            return {'success': False, 'error': 'Invalid Instagram URL', 'shortcode': None}
        
        # Check deduplication
        source_id = f"instagram_{shortcode}"
        db = SessionLocal()
        try:
            if is_duplicate(db, source_id):
                print(f"⏩ SKIP: Reel {shortcode} already exists in database")
                return {'success': False, 'error': 'Already exists', 'shortcode': shortcode}
        finally:
            db.close()
        
        print(f"📥 Downloading reel: {shortcode}")
        
        # Call API Hut
        endpoint = f"{self.base_url}/download/videos"
        headers = {
            'X-Avatar-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        data = {
            'type': 'instagram',
            'video_url': reel_url
        }
        
        try:
            response = requests.post(endpoint, json=data, headers=headers, timeout=60)
            
            if response.status_code != 200:
                error_msg = f"API Hut HTTP {response.status_code}: {response.text}"
                print(f"   ❌ {error_msg}")
                return {'success': False, 'error': error_msg, 'shortcode': shortcode}
            
            result = response.json()
            
            if result.get('success') != 1:
                error_msg = f"API Hut error: {result}"
                print(f"   ❌ {error_msg}")
                return {'success': False, 'error': error_msg, 'shortcode': shortcode}
            
            # Extract video URL from response
            video_data = result.get('data', [])
            if not video_data:
                return {'success': False, 'error': 'No video data in response', 'shortcode': shortcode}
            
            video_url = video_data[0].get('url')
            thumbnail_url = video_data[0].get('thumbnail')
            
            if not video_url:
                return {'success': False, 'error': 'No video URL in response', 'shortcode': shortcode}
            
            print(f"   ✅ Got video URL from API Hut")
            
            # Download the actual video file
            local_path = self._download_video(video_url, shortcode)
            
            if not local_path:
                return {'success': False, 'error': 'Failed to download video file', 'shortcode': shortcode}
            
            # Log cost (API Hut free tier = $0)
            self.log_cost('download_reel', 1, 0.0)
            
            return {
                'success': True,
                'shortcode': shortcode,
                'video_url': video_url,
                'thumbnail_url': thumbnail_url,
                'local_path': local_path
            }
            
        except requests.exceptions.Timeout:
            error_msg = "Request timeout (60s)"
            print(f"   ❌ {error_msg}")
            return {'success': False, 'error': error_msg, 'shortcode': shortcode}
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {'success': False, 'error': error_msg, 'shortcode': shortcode}
    
    def _download_video(self, video_url: str, shortcode: str) -> Optional[str]:
        """Download video file from CDN URL."""
        try:
            print(f"   📥 Downloading video file...")
            
            response = requests.get(video_url, stream=True, timeout=120)
            if response.status_code != 200:
                print(f"   ❌ Failed to download video: HTTP {response.status_code}")
                return None
            
            # Save to file
            file_path = self.download_dir / f"{shortcode}.mp4"
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = file_path.stat().st_size
            print(f"   ✅ Saved: {file_path} ({file_size / 1024 / 1024:.1f} MB)")
            
            return str(file_path)
            
        except Exception as e:
            print(f"   ❌ Failed to download video: {e}")
            return None
    
    def process_reel(self, reel_url: str, caption: Optional[str] = None) -> Optional[Dict]:
        """
        Full pipeline: Download reel and save to database.
        
        Args:
            reel_url: Instagram reel URL
            caption: Optional caption text (from share sheet)
            
        Returns:
            Dict with item data or None if failed
        """
        # Download the reel
        download_result = self.download_reel(reel_url)
        
        if not download_result['success']:
            return None
        
        shortcode = download_result['shortcode']
        source_id = f"instagram_{shortcode}"
        
        # Prepare item data
        item_data = {
            'source': 'instagram',
            'source_id': source_id,
            'media_id': shortcode,
            'caption': caption or f"Instagram reel: {shortcode}",
            'creator_username': None,  # API Hut doesn't provide this
            'timestamp': datetime.utcnow(),
            'media_url': download_result['video_url'],
            'local_path': download_result['local_path'],
            'pre_filter_passed': True,  # Instagram reels skip pre-filter
            'filter_reason': None,
            'ai_processed': False
        }
        
        # Save to database
        db = SessionLocal()
        try:
            save_content_item(db, item_data)
            print(f"   ✅ Saved to database: {source_id}")
            return item_data
        finally:
            db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 instagram_extractor.py <reel_url> [caption]")
        sys.exit(1)
    
    url = sys.argv[1]
    caption = sys.argv[2] if len(sys.argv) > 2 else None
    
    extractor = InstagramExtractor()
    result = extractor.process_reel(url, caption)
    
    if result:
        print(f"\n✅ Success!")
        print(f"   Shortcode: {result['media_id']}")
        print(f"   Local path: {result['local_path']}")
    else:
        print("\n❌ Failed to process reel")
