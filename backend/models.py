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
    
    # Meta tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
