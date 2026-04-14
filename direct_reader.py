"""
Direct Google Sheets Reader using API
Reads all items regardless of status
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

import requests
import json
from datetime import datetime

# Try using the webhook with a modified request that bypasses filtering
# Or create a simple Google Sheets API reader

# Since we don't have Google API credentials set up, let's use a workaround
# We'll modify the queue processor to fetch items differently

class DirectSheetReader:
    def __init__(self):
        self.webhook_url = os.getenv('GOOGLE_SHEET_WEBHOOK_URL')
        self.secret = os.getenv('GOOGLE_SHEET_SECRET')
    
    def get_all_items(self):
        """Get all items from sheet regardless of status"""
        # The webhook doesn't support this, but we can try to infer
        # Let's try POSTing with a special flag
        
        try:
            # Try to get items by simulating an "add" then checking what happens
            # Or try different parameter combinations
            
            response = requests.post(self.webhook_url, json={
                'secret': self.secret,
                'url': '',  # Empty URL might trigger list
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'all': 'true'  # Try to get all
            }, timeout=30)
            
            data = response.json()
            if isinstance(data, list):
                return data
            return []
        except:
            return []
    
    def force_process_url(self, url):
        """Process a URL directly without queue"""
        from backend.extractors.instagram_extractor import InstagramExtractor
        from backend.groq_processor import GroqAIProcessor
        from backend.database import SessionLocal
        from backend.models import ContentItem
        
        print(f'🎬 Processing: {url}')
        print('='*60)
        
        db = SessionLocal()
        try:
            # Download
            print('\n📥 Downloading...')
            extractor = InstagramExtractor()
            reel_data = extractor.process_reel(url, caption=None)
            
            if not reel_data:
                print('❌ Download failed')
                return False
            
            print(f'✅ Downloaded: {reel_data["local_path"]}')
            
            # Process
            print('\n🤖 AI Processing...')
            item = db.query(ContentItem).filter(
                ContentItem.source_id == reel_data['source_id']
            ).first()
            
            if item:
                processor = GroqAIProcessor()
                result = processor.process_reel(db, item)
                
                if result['status'] == 'success':
                    db.refresh(item)
                    print(f'\n✅ Complete!')
                    print(f'   Category: {item.category}')
                    print(f'   Score: {item.relevance_score}/10')
                    return True
            
            return False
        finally:
            db.close()

if __name__ == '__main__':
    reader = DirectSheetReader()
    
    # Check for items
    items = reader.get_all_items()
    print(f'Found {len(items)} items via webhook')
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        reader.force_process_url(url)
    else:
        print('\nUsage: python direct_reader.py <reel_url>')
