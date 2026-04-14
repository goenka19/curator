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
from backend.filtering.engine import FilteringEngine
from backend.obsidian_wiki import ObsidianWiki
from sqlalchemy import func

def show_stats():
    """Display system statistics and costs."""
    db = SessionLocal()
    try:
        total_items = db.query(ContentItem).count()
        twitter_items = db.query(ContentItem).filter(ContentItem.source == 'twitter').count()
        instagram_items = db.query(ContentItem).filter(ContentItem.source == 'instagram').count()
        ai_processed = db.query(ContentItem).filter(ContentItem.ai_processed == True).count()
        obsidian_synced = db.query(ContentItem).filter(ContentItem.obsidian_synced == True).count()
        
        # Calculate Costs
        total_cost = db.query(func.sum(APICostLog.cost_usd)).scalar() or 0.0
        
        print("\n" + "="*50)
        print("📊 Content Curator - Statistics")
        print("="*50)
        print(f"Total Items:          {total_items}")
        print(f"   Twitter/X:         {twitter_items}")
        print(f"   Instagram:         {instagram_items}")
        print(f"AI Processed:         {ai_processed}")
        print(f"Obsidian Synced:      {obsidian_synced}")
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

def fetch_twitter_command(limit=10):
    """Fetch Twitter bookmarks with pre-filtering."""
    from backend.extractors.twitter_extractor import TwitterExtractor
    from backend.database import log_api_cost
    
    print(f"🐦 Fetching up to {limit} Twitter bookmarks...")
    print(f"   DEV_MODE: {os.getenv('DEV_MODE', 'false')}")
    
    extractor = TwitterExtractor()
    items = extractor.fetch_bookmarks(limit=limit)
    
    # Log cost
    db = SessionLocal()
    try:
        cost = len(items) * 0.005  # $0.005 per tweet
        log_api_cost(db, 'twitter', 'fetch_bookmarks', len(items), cost)
        
        print(f"\n✅ Fetched {len(items)} bookmarks")
        print(f"   Cost: ${cost:.4f}")
        
        # Show what passed filter
        passed = [i for i in items if i.get('pre_filter_passed')]
        print(f"   Passed pre-filter: {len(passed)}")
        print(f"   Filtered out: {len(items) - len(passed)}")
        
        return len(items)
    finally:
        db.close()

def prefilter_command():
    """Run pre-filter on unfiltered items."""
    print("🔍 Running pre-filter on unfiltered items...")
    
    db = SessionLocal()
    try:
        # Get items that haven't been filtered yet
        items = db.query(ContentItem).filter(
            ContentItem.pre_filter_passed == False,
            ContentItem.filter_reason == None
        ).all()
        
        if not items:
            print("   No unfiltered items found")
            return 0
        
        filter_engine = FilteringEngine()
        passed_count = 0
        filtered_count = 0
        
        for item in items:
            should_pass, reason = filter_engine.should_process(
                item.caption or '',
                item.creator_username
            )
            
            item.pre_filter_passed = should_pass
            item.filter_reason = reason if not should_pass else None
            
            if should_pass:
                passed_count += 1
            else:
                filtered_count += 1
        
        db.commit()
        
        print(f"\n✅ Pre-filter complete")
        print(f"   Passed: {passed_count}")
        print(f"   Filtered: {filtered_count}")
        print(f"   Filter rate: {filtered_count/(passed_count+filtered_count)*100:.1f}%")
        
        return passed_count
    finally:
        db.close()

def ai_process_command(limit=10):
    """Process filtered items with AI (Groq)."""
    import json
    import requests
    
    print(f"🤖 AI processing up to {limit} items with Groq...")
    
    db = SessionLocal()
    try:
        # Get items that passed filter but not yet AI processed
        items = db.query(ContentItem).filter(
            ContentItem.pre_filter_passed == True,
            ContentItem.ai_processed == False
        ).limit(limit).all()
        
        if not items:
            print("   No items to process")
            return 0
        
        groq_key = os.getenv('GROQ_API_KEY')
        if not groq_key:
            print("   ❌ GROQ_API_KEY not set")
            return 0
        
        processed_count = 0
        
        for item in items:
            print(f"\n   Processing: {item.source_id}")
            
            # Special handling for X Articles - skip AI, mark for manual extraction
            if item.has_x_article:
                print(f"   📄 X Article detected - skipping AI, marking for manual extraction")
                item.ai_processed = True
                item.ai_insight = f"**X Article**: Requires manual extraction from {item.x_article_url}"
                item.relevance_score = 7  # Default to pass filter
                item.category = "x-article"
                item.entities_json = "[]"
                item.concepts_json = "[]"
                processed_count += 1
                continue
            
            # Extract value with strict relevance criteria
            prompt = f"""Analyze this content for KNOWLEDGE VALUE. Be extremely critical.

Content: {item.caption or ''}
Source: {item.source}

REJECT and mark low relevance (1-3) if:
- Just vanity metrics (likes, stars, views, followers)
- Pure news without analysis or insight
- Entertainment/memes with no learning value
- Generic motivational content
- Surface-level observations

ACCEPT and extract ONLY if:
- Teaches a concept, framework, or mental model
- Provides actionable advice or strategies
- Changes how to think about a topic
- Contains specific, reference-able insights
- Explains WHY or HOW something works

Return JSON:
{{
  "title": "3-7 word descriptive title about the core insight (NOT about virality)",
  "core_message": "One sentence: what is this actually about?",
  "key_insight": "What did you learn? Be specific. No fluff.",
  "actionable": "What should the reader DO with this info?",
  "entities": [{{"name": "significant person/company/tool only", "type": "person|company|book|tool"}}],
  "concepts": ["specific topics/frameworks worth researching"],
  "relevance_score": 1-10 (be harsh: 7+ only if truly valuable),
  "category": "finance|strategy|productivity|tech|psychology|other"
}}

Remember: The user curates for QUALITY, not quantity. Be selective."""
            
            headers = {
                'Authorization': f'Bearer {groq_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                'model': 'llama-3.3-70b-versatile',
                'messages': [{'role': 'user', 'content': prompt}],
                'response_format': {'type': 'json_object'},
                'max_tokens': 500
            }
            
            try:
                resp = requests.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if resp.status_code == 200:
                    result = resp.json()['choices'][0]['message']['content']
                    data = json.loads(result)
                    
                    # Skip low-relevance content (user wants 7+ only)
                    relevance = data.get('relevance_score', 5)
                    if relevance < 7:
                        print(f"   ⏩ SKIPPED: Low relevance ({relevance}/10)")
                        item.ai_processed = True  # Mark as processed to skip
                        item.relevance_score = relevance
                        continue
                    
                    # Update item with high-quality extraction
                    item.entities_json = json.dumps(data.get('entities', []))
                    item.concepts_json = json.dumps(data.get('concepts', []))
                    
                    # Store title for wiki naming
                    title = data.get('title', 'Untitled')
                    
                    # Build rich insight from structured fields
                    insight_parts = [
                        f"**Core Message**: {data.get('core_message', '')}",
                        f"**Key Insight**: {data.get('key_insight', '')}",
                        f"**Actionable**: {data.get('actionable', '')}"
                    ]
                    item.ai_insight = "\n\n".join(insight_parts)
                    
                    # Store title in key_points temporarily for wiki naming
                    item.key_points = title
                    
                    item.relevance_score = relevance
                    item.category = data.get('category', 'other')
                    item.ai_processed = True
                    
                    processed_count += 1
                    print(f"   ✅ High value ({relevance}/10): {title[:50]}...")
                    print(f"      Entities: {len(data.get('entities', []))}, Concepts: {len(data.get('concepts', []))}")
                else:
                    print(f"   ❌ Groq API error: {resp.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        db.commit()
        
        print(f"\n✅ AI processing complete")
        print(f"   Processed: {processed_count}")
        
        return processed_count
    finally:
        db.close()

def wiki_ingest_command(vault_path=None):
    """Ingest AI-processed items into Obsidian wiki."""
    if not vault_path:
        vault_path = "/Users/ujjwalgoenka/Desktop/Coding/curator/curator_vault"
    
    print(f"📝 Ingesting to Obsidian wiki at {vault_path}...")
    
    db = SessionLocal()
    try:
        # Get items that are AI processed but not wiki synced
        items = db.query(ContentItem).filter(
            ContentItem.ai_processed == True,
            ContentItem.obsidian_synced == False,
            ContentItem.pre_filter_passed == True
        ).all()
        
        if not items:
            print("   No items to ingest")
            return 0
        
        wiki = ObsidianWiki(vault_path)
        ingested_count = 0
        
        for item in items:
            print(f"\n   Ingesting: {item.source_id}")
            
            try:
                # Convert to wiki dict
                wiki_item = item.to_wiki_dict()
                
                # Ingest
                created_files = wiki.ingest_item(wiki_item)
                
                # Mark as synced
                item.obsidian_synced = True
                item.obsidian_path = created_files[0] if created_files else None
                
                ingested_count += 1
                print(f"   ✅ Created {len(created_files)} pages")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        db.commit()
        
        print(f"\n✅ Wiki ingest complete")
        print(f"   Ingested: {ingested_count} items")
        
        return ingested_count
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Content Curator CLI")
    parser.add_argument("command", 
                       choices=["init", "stats", "process-queue", "fetch-twitter", "pre-filter", "ai-process", "wiki-ingest", "mark"], 
                       help="Command to run")
    parser.add_argument("--id", type=int, help="Item ID for 'mark' command")
    parser.add_argument("--status", choices=["valuable", "trash"], help="Status for 'mark' command")
    parser.add_argument("--limit", type=int, help="Limit number of items")
    parser.add_argument("--vault", type=str, help="Obsidian vault path (for wiki-ingest)")
    
    args = parser.parse_args()
    
    if args.command == "init":
        init_db()
    elif args.command == "stats":
        show_stats()
    elif args.command == "process-queue":
        success = process_queue_command(limit=args.limit)
        sys.exit(0 if success else 1)
    elif args.command == "fetch-twitter":
        limit = args.limit or 10
        if os.getenv('DEV_MODE') == 'true':
            limit = min(limit, int(os.getenv('MAX_DEV_ITEMS', 10)))
        fetch_twitter_command(limit=limit)
    elif args.command == "pre-filter":
        prefilter_command()
    elif args.command == "ai-process":
        limit = args.limit or 10
        ai_process_command(limit=limit)
    elif args.command == "wiki-ingest":
        wiki_ingest_command(vault_path=args.vault)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
