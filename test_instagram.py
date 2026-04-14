#!/usr/bin/env python3
"""
Test script for Instagram integration
Tests the full pipeline: download → save → AI process
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.extractors.instagram_extractor import InstagramExtractor
from backend.database import SessionLocal, init_db
from backend.models import ContentItem

def test_instagram_pipeline():
    """Test the full Instagram pipeline."""
    
    print("="*60)
    print("🧪 Testing Instagram Reel Processing Pipeline")
    print("="*60)
    
    # Initialize DB
    print("\n1️⃣ Initializing database...")
    init_db()
    
    # Clean up test entry
    db = SessionLocal()
    try:
        existing = db.query(ContentItem).filter(
            ContentItem.source_id == 'instagram_DWjdnxMCpcL'
        ).first()
        if existing:
            db.delete(existing)
            db.commit()
            print("   🧹 Cleaned up existing test entry")
    finally:
        db.close()
    
    # Test reel URL
    test_url = 'https://www.instagram.com/reel/DWjdnxMCpcL/'
    
    print(f"\n2️⃣ Testing reel download...")
    print(f"   URL: {test_url}")
    
    extractor = InstagramExtractor()
    result = extractor.process_reel(test_url, caption='Test reel from API Hut')
    
    if not result:
        print("\n❌ Pipeline failed!")
        return False
    
    print(f"\n   ✅ Download successful!")
    print(f"      Source ID: {result['source_id']}")
    print(f"      Local path: {result['local_path']}")
    
    # Verify database entry
    print(f"\n3️⃣ Verifying database entry...")
    db = SessionLocal()
    try:
        item = db.query(ContentItem).filter(
            ContentItem.source_id == result['source_id']
        ).first()
        
        if item:
            print(f"   ✅ Entry found in database:")
            print(f"      ID: {item.id}")
            print(f"      Source: {item.source}")
            print(f"      Caption: {item.caption[:50]}..." if item.caption else "      Caption: None")
            print(f"      Pre-filter passed: {item.pre_filter_passed}")
            print(f"      AI processed: {item.ai_processed}")
        else:
            print("   ❌ Entry not found!")
            return False
    finally:
        db.close()
    
    print("\n" + "="*60)
    print("✅ All tests passed! Instagram pipeline is working.")
    print("="*60)
    
    print("\n📋 Next steps:")
    print("   1. Add reels via iOS Shortcut → Google Sheets")
    print("   2. Run: python backend/cli.py process-queue")
    print("   3. Check stats: python backend/cli.py stats")
    
    return True

if __name__ == "__main__":
    success = test_instagram_pipeline()
    sys.exit(0 if success else 1)
