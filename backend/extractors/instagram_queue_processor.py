"""
Instagram Queue Processor
Fetches reels from Google Sheets queue and processes them using API Hut
"""

import os
import re
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from backend.extractors.instagram_extractor import InstagramExtractor
from backend.groq_processor import GroqAIProcessor
from backend.database import SessionLocal, is_duplicate


@dataclass
class QueueItem:
    """Represents an item in the Google Sheets queue."""
    row_index: int  # Row number in sheet (for updating)
    url: str
    cleaned_url: str
    retry_count: int


class InstagramQueueProcessor:
    """
    Processes Instagram reels from Google Sheets queue.
    """
    
    def __init__(self):
        self.webhook_url = os.getenv('GOOGLE_SHEET_WEBHOOK_URL')
        self.webhook_secret = os.getenv('GOOGLE_SHEET_SECRET')
        self.extractor = InstagramExtractor()
        self.ai_processor = GroqAIProcessor()
        self.max_retries = int(os.getenv('QUEUE_MAX_RETRIES', 2))
    
    def fetch_queue(self) -> List[QueueItem]:
        """
        Fetch pending items from Google Sheets queue.
        The webhook returns the queue when POSTing with secret.
        
        Returns:
            List of QueueItem with pending status
        """
        if not self.webhook_url:
            print("❌ GOOGLE_SHEET_WEBHOOK_URL not set")
            return []
        
        print("📋 Fetching queue from Google Sheets...")
        
        try:
            # POST to webhook returns all pending items
            payload = {
                'secret': self.webhook_secret,
                'url': '',  # Empty URL to just fetch queue
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to fetch queue: HTTP {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return []
            
            # Response is a list of pending items
            data = response.json()
            
            if isinstance(data, list):
                items = []
                for row in data:
                    items.append(QueueItem(
                        row_index=row.get('rowIndex', 0),
                        url=row.get('url', ''),
                        cleaned_url=row.get('cleaned_url', ''),
                        retry_count=int(row.get('retry_count', 0))
                    ))
                
                print(f"   Found {len(items)} pending items")
                return items
            else:
                print(f"   Unexpected response format: {data}")
                return []
            
        except Exception as e:
            print(f"❌ Error fetching queue: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def update_queue_status(self, row_index: int, status: str, 
                           error_message: Optional[str] = None,
                           db_id: Optional[str] = None) -> bool:
        """
        Update item status in Google Sheets.
        Note: The webhook might not support this - we may need to track status locally.
        
        Args:
            row_index: Row number in the sheet
            status: New status ('processed', 'failed', 'retrying')
            error_message: Optional error message
            db_id: Optional database ID
            
        Returns:
            True if successful
        """
        # For now, just log the status update
        # The webhook may not support status updates
        print(f"   📝 Status update (row {row_index}): {status}")
        return True
    
    def process_item(self, item: QueueItem) -> bool:
        """
        Process a single queue item.
        
        Args:
            item: QueueItem to process
            
        Returns:
            True if successful
        """
        print(f"\n🎬 Processing: {item.cleaned_url}")
        
        # Check retry count
        if item.retry_count >= self.max_retries:
            print(f"   ⚠️ Max retries ({self.max_retries}) exceeded, marking as failed")
            self.update_queue_status(
                item.row_index, 
                'failed', 
                error_message='Max retries exceeded'
            )
            return False
        
        # Check if already in database (deduplication)
        shortcode = self.extractor.extract_shortcode(item.cleaned_url)
        if shortcode:
            source_id = f"instagram_{shortcode}"
            db = SessionLocal()
            try:
                if is_duplicate(db, source_id):
                    print(f"   ⏩ Already in database, skipping")
                    self.update_queue_status(item.row_index, 'processed')
                    return True
            finally:
                db.close()
        
        # Step 1: Download the reel
        reel_data = self.extractor.process_reel(item.cleaned_url, caption=None)
        
        if not reel_data:
            # Update retry count
            new_retry = item.retry_count + 1
            self.update_queue_status(
                item.row_index,
                'retrying' if new_retry < self.max_retries else 'failed',
                error_message='Download failed'
            )
            return False
        
        # Step 2: Process with AI (vision analysis)
        print(f"   🤖 Running AI analysis...")
        
        try:
            db = SessionLocal()
            try:
                # Find the saved item
                from backend.models import ContentItem
                content_item = db.query(ContentItem).filter(
                    ContentItem.source_id == reel_data['source_id']
                ).first()
                
                if content_item and content_item.local_path:
                    # Run AI processor on video
                    result = self.ai_processor.process_reel(db, content_item)
                    print(f"   ✅ AI processed: {result['status']}")
                    
                    # Refresh to get updated data
                    db.refresh(content_item)
                    
                    # Update queue as processed
                    self.update_queue_status(
                        item.row_index,
                        'processed',
                        db_id=str(content_item.id)
                    )
                    
                    print(f"   ✅ Complete! Category: {content_item.category}")
                    return True
                else:
                    raise Exception("Content item not found or no local path")
                    
            finally:
                db.close()
                
        except Exception as e:
            print(f"   ❌ AI processing failed: {e}")
            self.update_queue_status(
                item.row_index,
                'retrying',
                error_message=f'AI processing failed: {str(e)}'
            )
            return False
    
    def process_queue(self, limit: Optional[int] = None) -> Dict:
        """
        Process all pending items in the queue.
        
        Args:
            limit: Maximum items to process (None for all)
            
        Returns:
            Dict with statistics
        """
        # Check DEV_MODE
        dev_mode = os.getenv('DEV_MODE', 'true').lower() == 'true'
        if dev_mode and limit is None:
            max_dev = int(os.getenv('MAX_DEV_ITEMS', 10))
            print(f"🛠️ DEV_MODE: Limiting to {max_dev} items")
            limit = max_dev
        
        # Fetch queue
        items = self.fetch_queue()
        
        if not items:
            print("\n✨ No pending items in queue")
            return {'processed': 0, 'failed': 0, 'skipped': 0}
        
        if limit:
            items = items[:limit]
            print(f"   Processing first {limit} items")
        
        # Process each item
        stats = {'processed': 0, 'failed': 0, 'skipped': 0}
        
        for item in items:
            # Process the item
            success = self.process_item(item)
            if success:
                stats['processed'] += 1
            else:
                stats['failed'] += 1
        
        print(f"\n📊 Queue Processing Complete:")
        print(f"   Processed: {stats['processed']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Skipped: {stats['skipped']}")
        
        return stats


if __name__ == "__main__":
    import sys
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    processor = InstagramQueueProcessor()
    
    # Get limit from args
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    
    stats = processor.process_queue(limit=limit)
    
    # Exit with error code if any failed
    sys.exit(0 if stats['failed'] == 0 else 1)
