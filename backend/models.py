from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class ContentItem(Base):
    """
    Unified model for both Twitter and Instagram content.
    """
    __tablename__ = 'content_items'

    id = Column(Integer, primary_key=True)
    source = Column(String(50), nullable=False)  # 'twitter' or 'instagram'
    source_id = Column(String(255), unique=True, nullable=False)  # e.g., tweet_id or dm_mid
    media_id = Column(String(255), nullable=True)  # The ID of the Reel or Media itself
    
    # Metadata
    caption = Column(Text, nullable=True)
    creator_username = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Media handling (Temporary)
    media_url = Column(Text, nullable=True)  # Temp CDN link
    local_path = Column(String(512), nullable=True)  # Local path for vision analysis
    
    # Filter Status
    pre_filter_passed = Column(Boolean, default=False)
    filter_reason = Column(String(255), nullable=True)
    
    # AI Results
    ai_processed = Column(Boolean, default=False)
    ai_insight = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    relevance_score = Column(Integer, nullable=True)
    key_points = Column(Text, nullable=True)
    
    # Obsidian Sync Tracking
    obsidian_synced = Column(Boolean, default=False)
    obsidian_path = Column(String(512), nullable=True)
    entities_json = Column(Text, nullable=True)  # JSON string of extracted entities
    concepts_json = Column(Text, nullable=True)  # JSON string of extracted concepts
    
    # Meta tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_wiki_dict(self):
        """Convert to dict for wiki ingestion."""
        import json
        
        # Use stored title (from AI) or generate from insight
        if self.key_points and len(self.key_points) < 100:
            # key_points stores the title for high-value items
            title = self.key_points
        elif self.ai_insight:
            title = self.ai_insight.split('\n')[0][:60] if '\n' in self.ai_insight else self.ai_insight[:60]
        else:
            title = 'Untitled'
        
        return {
            'id': self.source_id,
            'source': self.source,
            'title': title,
            'author': self.creator_username or 'unknown',
            'date': self.timestamp.strftime('%Y-%m-%d') if self.timestamp else datetime.now().strftime('%Y-%m-%d'),
            'original_text': self.caption or '',
            'summary': self.ai_insight or '',
            'key_points': '',  # Now stored in summary
            'entities': json.loads(self.entities_json) if self.entities_json else [],
            'concepts': json.loads(self.concepts_json) if self.concepts_json else [],
            'tags': [self.category] if self.category else [],
            'relevance_score': self.relevance_score or 5,
        }

class APICostLog(Base):
    """
    Tracks cost of every API call to ensure we stay under budget ($5/month).
    """
    __tablename__ = 'api_cost_logs'

    id = Column(Integer, primary_key=True)
    api_name = Column(String(50), nullable=False)  # 'twitter', 'instagram', 'openrouter'
    operation = Column(String(100), nullable=False) # 'fetch_bookmarks', 'ai_analysis'
    items_count = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Preference(Base):
    """
    Stores system-level preferences and learning feedback.
    """
    __tablename__ = 'preferences'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
