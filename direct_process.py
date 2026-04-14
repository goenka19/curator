"""
Direct Reel Processor
Processes a reel by URL directly without Google Sheets queue
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.extractors.instagram_extractor import InstagramExtractor
from backend.groq_processor import GroqAIProcessor
from backend.database import SessionLocal
from backend.models import ContentItem

def process_reel_direct(url: str):
    """Process a reel directly by URL"""
    
    print(f"🎬 Processing reel directly: {url}")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # Step 1: Download
        print("\n📥 Step 1: Downloading reel...")
        extractor = InstagramExtractor()
        reel_data = extractor.process_reel(url, caption=None)
        
        if not reel_data:
            print("❌ Download failed")
            return False
        
        print(f"✅ Downloaded: {reel_data['source_id']}")
        
        # Step 2: Get the saved item
        item = db.query(ContentItem).filter(
            ContentItem.source_id == reel_data['source_id']
        ).first()
        
        if not item:
            print("❌ Item not found in database")
            return False
        
        # Step 3: AI Processing
        print("\n🤖 Step 2: AI Processing with Groq...")
        processor = GroqAIProcessor()
        result = processor.process_reel(db, item)
        
        if result['status'] == 'success':
            print("\n" + "="*60)
            print("✅ PROCESSING COMPLETE!")
            print("="*60)
            
            # Refresh to get updated data
            db.refresh(item)
            
            print(f"\n📊 Results:")
            print(f"   Category: {item.category}")
            print(f"   Relevance: {item.relevance_score}/10")
            print(f"   AI Insight: {item.ai_insight[:200]}..." if item.ai_insight else "   No insight")
            
            return True
        else:
            print(f"❌ AI processing failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python direct_process.py <reel_url>")
        print("Example: python direct_process.py https://www.instagram.com/reel/ABC123/")
        sys.exit(1)
    
    url = sys.argv[1]
    success = process_reel_direct(url)
    sys.exit(0 if success else 1)
