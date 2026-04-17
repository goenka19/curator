"""
Curator Dashboard
Main dashboard logic for displaying stats, new items, and insights
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import hashlib

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.state_manager import get_state_manager, SystemState, CostTracker
from backend.database import SessionLocal, get_db
from backend.models import ContentItem
from sqlalchemy import func

VAULT_PATH = Path("/Users/ujjwalgoenka/Desktop/Coding/curator/curator_vault")
WIKI_PATH = VAULT_PATH / "wiki"

class Dashboard:
    """Main dashboard class."""
    
    def __init__(self):
        self.state_mgr = get_state_manager()
        self.state = self.state_mgr.load_state()
        self.cost_tracker = self.state_mgr.load_cost_tracker()
        self.db = SessionLocal()
        
        # Validate and fix timestamps
        self.state = self.state_mgr.validate_timestamps(self.state)
        
        # Check monthly reset
        self.cost_tracker = self.state_mgr.check_monthly_reset(self.cost_tracker)
    
    def __del__(self):
        """Cleanup database connection."""
        if hasattr(self, 'db'):
            self.db.close()
    
    def should_run(self) -> Tuple[bool, str]:
        """Check if dashboard should run now."""
        # Check if already ran today
        if not self.state_mgr.should_run_today(self.state):
            last_run = datetime.fromisoformat(self.state.daily_run.last_run)
            hours_ago = (datetime.now() - last_run).total_seconds() / 3600
            return False, f"Last run was {hours_ago:.1f} hours ago"
        
        return True, "OK"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current stats from database."""
        try:
            total_items = self.db.query(ContentItem).count()
            twitter_items = self.db.query(ContentItem).filter(ContentItem.source == 'twitter').count()
            instagram_items = self.db.query(ContentItem).filter(ContentItem.source == 'instagram').count()
            ai_processed = self.db.query(ContentItem).filter(ContentItem.ai_processed == True).count()
            
            # Count books (from vault, not DB)
            books_path = WIKI_PATH / "books"
            books_count = len(list(books_path.glob("*.md"))) if books_path.exists() else 0
            
            # Count entities and concepts
            entities_path = WIKI_PATH / "entities"
            entities_count = len(list(entities_path.glob("*.md"))) if entities_path.exists() else 0
            
            concepts_path = WIKI_PATH / "concepts"
            concepts_count = len(list(concepts_path.glob("*.md"))) if concepts_path.exists() else 0
            
            return {
                'total_db_items': total_items,
                'twitter_items': twitter_items,
                'instagram_items': instagram_items,
                'ai_processed': ai_processed,
                'books': books_count,
                'entities': entities_count,
                'concepts': concepts_count,
                'total_vault_pages': books_count + entities_count + concepts_count
            }
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {
                'total_db_items': 0, 'twitter_items': 0, 'instagram_items': 0,
                'ai_processed': 0, 'books': 0, 'entities': 0, 'concepts': 0,
                'total_vault_pages': 0
            }
    
    def get_new_items_since_last_run(self) -> Dict[str, List[Any]]:
        """Get items added since last dashboard run."""
        if not self.state.daily_run.last_run:
            return {'twitter': [], 'instagram': [], 'vault': []}
        
        last_run = datetime.fromisoformat(self.state.daily_run.last_run)
        
        # Database items
        new_twitter = self.db.query(ContentItem).filter(
            ContentItem.source == 'twitter',
            ContentItem.created_at > last_run
        ).all()
        
        new_instagram = self.db.query(ContentItem).filter(
            ContentItem.source == 'instagram',
            ContentItem.created_at > last_run
        ).all()
        
        # Vault items (check file mtimes)
        new_vault_pages = self._get_new_vault_pages(last_run)
        
        return {
            'twitter': new_twitter,
            'instagram': new_instagram,
            'vault': new_vault_pages
        }
    
    def _get_new_vault_pages(self, since: datetime) -> List[Path]:
        """Get vault pages modified since timestamp."""
        new_pages = []
        
        for subdir in ['books', 'entities', 'concepts']:
            path = WIKI_PATH / subdir
            if not path.exists():
                continue
            
            for page in path.glob("*.md"):
                mtime = datetime.fromtimestamp(page.stat().st_mtime)
                if mtime > since:
                    new_pages.append(page)
        
        return new_pages
    
    def scan_vault_for_connections(self) -> List[Dict[str, Any]]:
        """Find concept pages that link to 2+ books."""
        connections = []
        
        concepts_path = WIKI_PATH / "concepts"
        if not concepts_path.exists():
            return connections
        
        for concept_file in concepts_path.glob("*.md"):
            try:
                content = concept_file.read_text()
                # Find all [[Book Title]] links
                import re
                book_links = re.findall(r'\[\[(.*?)\]\]', content)
                
                # Filter to actual books (check if file exists in books/)
                valid_books = []
                for link in book_links:
                    book_file = WIKI_PATH / "books" / f"{link}.md"
                    if book_file.exists():
                        valid_books.append(link)
                
                if len(valid_books) >= 2:
                    connections.append({
                        'concept': concept_file.stem,
                        'books': valid_books,
                        'book_count': len(valid_books)
                    })
            except Exception as e:
                continue
        
        # Sort by number of connections
        connections.sort(key=lambda x: x['book_count'], reverse=True)
        return connections
    
    def find_gaps(self) -> Dict[str, Any]:
        """Find missing entity pages, orphans, dead links."""
        gaps = {
            'missing_entities': [],
            'orphan_pages': [],
            'dead_links': []
        }
        
        # Find mentioned entities without pages
        # (This is a simplified version - full implementation would parse all pages)
        mentioned_entities = set()
        existing_entities = set()
        
        # Get existing entities
        entities_path = WIKI_PATH / "entities"
        if entities_path.exists():
            existing_entities = {f.stem for f in entities_path.glob("*.md")}
        
        # Parse books for mentions (simplified)
        books_path = WIKI_PATH / "books"
        if books_path.exists():
            for book_file in books_path.glob("*.md"):
                try:
                    content = book_file.read_text()
                    # Find [[Entity Name]] that aren't in existing_entities
                    import re
                    links = re.findall(r'\[\[(.*?)\]\]', content)
                    for link in links:
                        # Skip if it's a book or concept
                        if link not in existing_entities:
                            # Check if it's in books/ or concepts/
                            if not (WIKI_PATH / "books" / f"{link}.md").exists():
                                if not (WIKI_PATH / "concepts" / f"{link}.md").exists():
                                    mentioned_entities.add(link)
                except:
                    continue
        
        gaps['missing_entities'] = list(mentioned_entities - existing_entities)[:10]  # Top 10
        
        return gaps
    
    def check_cost_milestones(self) -> List[str]:
        """Check if cost milestones reached and notify."""
        notifications = []
        total = self.cost_tracker.twitter_monthly_total + self.cost_tracker.instagram_monthly_total
        
        if total >= 4.00 and not self.cost_tracker.milestones.notified_4_dollars:
            notifications.append("🛑 Cost Alert: $4.00 reached this month! Approaching $5 limit.")
            self.cost_tracker.milestones.notified_4_dollars = True
            self.state_mgr.save_cost_tracker(self.cost_tracker)
        
        elif total >= 2.00 and not self.cost_tracker.milestones.notified_2_dollars:
            notifications.append("⚠️  Cost Alert: $2.00 reached this month.")
            self.cost_tracker.milestones.notified_2_dollars = True
            self.state_mgr.save_cost_tracker(self.cost_tracker)
        
        elif total >= 1.00 and not self.cost_tracker.milestones.notified_1_dollar:
            notifications.append("ℹ️  Cost Notice: $1.00 reached this month.")
            self.cost_tracker.milestones.notified_1_dollar = True
            self.state_mgr.save_cost_tracker(self.cost_tracker)
        
        return notifications
    
    def maybe_switch_twitter_mode(self) -> Optional[str]:
        """Check if should switch from backlog to live mode."""
        if self.state.twitter.mode != "backlog":
            return None
        
        if self.state.twitter.manual_override:
            return None
        
        if self.state.twitter.backlog_remaining > 0:
            return None
        
        # Check user activity (last 7 days)
        if self.state.daily_run.last_run:
            last_run = datetime.fromisoformat(self.state.daily_run.last_run)
            days_since = (datetime.now() - last_run).days
            if days_since > 7:
                return None
        
        # All conditions met - switch to live
        self.state.twitter.mode = "live"
        self.state.twitter.auto_fetch_enabled = True
        self.state.flags.backlog_complete = True
        self.state_mgr.save_state(self.state)
        
        return "🎉 Backlog complete! Switched to LIVE mode. Weekly fetches enabled."
    
    def add_cost(self, source: str, amount: float):
        """Add cost to tracker."""
        if source == 'twitter':
            self.cost_tracker.twitter_monthly_total += amount
        elif source == 'instagram':
            self.cost_tracker.instagram_monthly_total += amount
        
        self.state_mgr.save_cost_tracker(self.cost_tracker)
    
    def render_dashboard(self, check_new_content: bool = True):
        """Render the full dashboard."""
        now = datetime.now()
        
        print("\n" + "╔" + "═" * 68 + "╗")
        print("║" + " " * 15 + f"📊 CURATOR DASHBOARD - {now.strftime('%Y-%m-%d %H:%M')}" + " " * 16 + "║")
        print("╚" + "═" * 68 + "╝")
        
        # Last run info
        if self.state.daily_run.last_run:
            last_run = datetime.fromisoformat(self.state.daily_run.last_run)
            hours_ago = (now - last_run).total_seconds() / 3600
            print(f"\n⏱️  LAST CHECK: {hours_ago:.1f} hours ago ({last_run.strftime('%Y-%m-%d %H:%M')})")
        else:
            print("\n⏱️  LAST CHECK: Never (first run)")
        
        # Stats
        stats = self.get_stats()
        print("\n📈 OVERALL STATS")
        print("─" * 70)
        print(f"Total DB Items:        {stats['total_db_items']}")
        print(f"├─ Twitter/X:          {stats['twitter_items']}")
        print(f"├─ Instagram:          {stats['instagram_items']}")
        print(f"└─ AI Processed:       {stats['ai_processed']}")
        print()
        print(f"Vault Pages:           {stats['total_vault_pages']}")
        print(f"├─ Books:              {stats['books']}")
        print(f"├─ Entities:           {stats['entities']}")
        print(f"└─ Concepts:           {stats['concepts']}")
        
        # Cost
        total_cost = self.cost_tracker.twitter_monthly_total + self.cost_tracker.instagram_monthly_total
        print()
        print(f"💰 COSTS THIS MONTH")
        print(f"   Twitter:    ${self.cost_tracker.twitter_monthly_total:.4f}")
        print(f"   Instagram:  ${self.cost_tracker.instagram_monthly_total:.4f}")
        print(f"   TOTAL:      ${total_cost:.4f} / $5.00 limit")
        
        # New items since last run
        print("\n🆕 NEW SINCE LAST CHECK")
        print("─" * 70)
        new_items = self.get_new_items_since_last_run()
        
        if new_items['twitter']:
            print(f"🐦 Twitter: {len(new_items['twitter'])} new")
            for item in new_items['twitter'][:3]:
                print(f"   └─ @{item.creator_username}: {item.caption[:50]}...")
        else:
            print("🐦 Twitter: 0 new items")
        
        if new_items['instagram']:
            print(f"\n📸 Instagram: {len(new_items['instagram'])} new")
            for item in new_items['instagram'][:3]:
                print(f"   └─ Reel: {item.caption[:50]}...")
        else:
            print("📸 Instagram: 0 new items")
        
        if new_items['vault']:
            print(f"\n📚 Vault: {len(new_items['vault'])} new pages")
            for page in new_items['vault'][:3]:
                print(f"   └─ {page.name}")
        else:
            print("📚 Vault: 0 new pages")
        
        # Check for new content if requested
        if check_new_content:
            print("\n🔍 CHECKING FOR NEW CONTENT...")
            print("   (This may take a moment...)")
            # Content checking happens outside this function
        
        # Connections
        print("\n🔗 TOP CONNECTIONS")
        print("─" * 70)
        connections = self.scan_vault_for_connections()
        
        if connections:
            for conn in connections[:5]:
                print(f"✨ {conn['concept']}")
                print(f"   └─ Links {conn['book_count']} books: {', '.join(conn['books'][:3])}")
        else:
            print("   No multi-book connections found yet")
        
        # Gaps
        print("\n⚠️  GAPS & MISSING")
        print("─" * 70)
        gaps = self.find_gaps()
        
        if gaps['missing_entities']:
            print(f"Missing Entity Pages ({len(gaps['missing_entities'])}):")
            for entity in gaps['missing_entities'][:5]:
                print(f"   ❌ {entity}")
        else:
            print("✅ No missing entity pages detected")
        
        # Cost milestones
        print("\n📢 NOTIFICATIONS")
        print("─" * 70)
        notifications = self.check_cost_milestones()
        
        if notifications:
            for notif in notifications:
                print(notif)
        else:
            print("   No notifications")
        
        # Mode info
        print("\n🎛️  SYSTEM MODE")
        print("─" * 70)
        print(f"   Twitter Mode: {self.state.twitter.mode.upper()}")
        if self.state.twitter.mode == "backlog":
            print(f"   └─ Backlog: {self.state.twitter.backlog_remaining} items remaining")
            print(f"   └─ Auto-switch when complete: {'ON' if not self.state.twitter.manual_override else 'OFF (manual)'}")
        else:
            print(f"   └─ Weekly fetch: {self.state.twitter.weekly_fetch_day}")
            print(f"   └─ Auto-fetch: {'ON' if self.state.twitter.auto_fetch_enabled else 'OFF'}")
        
        # Recommended actions
        print("\n🎯 RECOMMENDED ACTIONS")
        print("─" * 70)
        actions = []
        
        if gaps['missing_entities']:
            actions.append(f"Create {len(gaps['missing_entities'])} missing entity pages")
        
        if self.state.twitter.mode == "backlog" and self.state.twitter.backlog_remaining > 0:
            actions.append("Process Twitter backlog (manual review needed)")
        
        if total_cost > 4.50:
            actions.append("⚠️  Cost limit approaching - monitor closely")
        
        if not actions:
            print("   All caught up! 🎉")
        else:
            for i, action in enumerate(actions, 1):
                print(f"   {i}. {action}")
        
        # Footer
        print("\n" + "═" * 70)
        print("Commands: dashboard | twitter-mode | cost-status | dashboard-reset")
        print("═" * 70 + "\n")
    
    def finish_run(self):
        """Update state after successful run."""
        now = datetime.now().isoformat()
        
        self.state.daily_run.last_run = now
        self.state.daily_run.today_count += 1
        self.state.daily_run.consecutive_rruns = getattr(self.state.daily_run, 'consecutive_runs', 0) + 1
        
        # Check for mode switch
        switch_msg = self.maybe_switch_twitter_mode()
        if switch_msg:
            print(f"\n{switch_msg}")
        
        self.state_mgr.save_state(self.state)

# Convenience function
def get_dashboard() -> Dashboard:
    """Get dashboard instance."""
    return Dashboard()
