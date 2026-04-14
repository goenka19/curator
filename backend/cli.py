import argparse
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for proper imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, SessionLocal, get_db
from backend.ai_processor import AIProcessor
from backend.models import ContentItem, APICostLog
from sqlalchemy import func

def show_stats():
    """Display system statistics and costs."""
    db = SessionLocal()
    try:
        total_items = db.query(ContentItem).count()
        twitter_items = db.query(ContentItem).filter(ContentItem.source == 'twitter').count()
        instagram_items = db.query(ContentItem).filter(ContentItem.source == 'instagram').count()
        ai_processed = db.query(ContentItem).filter(ContentItem.ai_processed == True).count()
        
        # Calculate Costs
        total_cost = db.query(func.sum(APICostLog.cost_usd)).scalar() or 0.0
        
        print("\n" + "="*50)
        print("📊 Content Curator - Statistics")
        print("="*50)
        print(f"Total Items:          {total_items}")
        print(f"   Twitter/X:         {twitter_items}")
        print(f"   Instagram:         {instagram_items}")
        print(f"AI Processed:         {ai_processed}")
        print("-" * 30)
        print(f"Total Monthly Cost:   ${total_cost:.4f}")
        print(f"   Daily Limit:       $0.50")
        print(f"   Monthly Limit:     $5.00")
        print("="*50 + "\n")
    finally:
        db.close()

def process_queue_command(limit=None):
    """Process Instagram queue from Google Sheets."""
    from backend.extractors.instagram_queue_processor import InstagramQueueProcessor
    
    processor = InstagramQueueProcessor()
    stats = processor.process_queue(limit=limit)
    
    return stats['failed'] == 0

def main():
    parser = argparse.ArgumentParser(description="Content Curator CLI")
    parser.add_argument("command", 
                       choices=["init", "stats", "process-queue", "mark"], 
                       help="Command to run")
    parser.add_argument("--id", type=int, help="Item ID for 'mark' command")
    parser.add_argument("--status", choices=["valuable", "trash"], help="Status for 'mark' command")
    parser.add_argument("--limit", type=int, help="Limit number of items (for process-queue)")
    
    args = parser.parse_args()
    
    if args.command == "init":
        init_db()
    elif args.command == "stats":
        show_stats()
    elif args.command == "process-queue":
        success = process_queue_command(limit=args.limit)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
