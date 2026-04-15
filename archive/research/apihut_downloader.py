"""
Instagram Downloader using API Hut
Free API for downloading Instagram reels
"""

import os
import requests
from typing import Optional, Dict

class APIHutInstagramDownloader:
    def __init__(self):
        # Get API key from environment or use free tier
        self.api_key = os.getenv('APIHUT_KEY', 'avatarhubadmin')  # Demo key from docs
        self.base_url = 'https://apihut.in/api'
        
    def download_reel(self, reel_url: str) -> Optional[Dict]:
        """Download Instagram reel using API Hut.
        
        Args:
            reel_url: Instagram reel URL
            
        Returns:
            Dict with download_url, caption, etc. or None if failed
        """
        print(f"📥 Downloading reel: {reel_url}")
        
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
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Success: {result}")
                return result
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 apihut_downloader.py <reel_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    dl = APIHutInstagramDownloader()
    result = dl.download_reel(url)
    
    if result:
        print(f"\n✅ Download URL: {result.get('download_url', 'N/A')}")
    else:
        print("\n❌ Failed to download")
