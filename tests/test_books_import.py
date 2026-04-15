#!/usr/bin/env python3
"""
Test script for books importer
Tests parsing and processing of 1-2 highlights
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.extractors.books_extractor import BooksExtractor, generate_slug
from backend.books_importer import BooksImporter

def test_extractor():
    """Test the CSV extraction."""
    print("="*60)
    print("🧪 Testing Books Extractor")
    print("="*60)
    
    extractor = BooksExtractor()
    books, highlights = extractor.extract_all()
    
    if not books:
        print("❌ No books found in export.csv")
        return False
    
    if not highlights:
        print("❌ No highlights found in export2.csv")
        return False
    
    print(f"\n✅ Found {len(books)} books:")
    for book in books:
        count = len([h for h in highlights if h.book_id == book.id])
        print(f"   - {book.title} by {book.author} ({count} highlights)")
    
    print(f"\n✅ Found {len(highlights)} total highlights")
    
    # Test slug generation
    print("\n📝 Sample slugs:")
    for h in highlights[:3]:
        slug = generate_slug(h.content)
        preview = h.content[:60] + "..." if len(h.content) > 60 else h.content
        print(f"   {slug}")
        print(f"      From: {h.book.title if h.book else 'Unknown'}")
        print(f"      Preview: {preview}")
        print()
    
    return True

def test_ai_processing():
    """Test AI processing on one highlight."""
    print("="*60)
    print("🧪 Testing AI Processing (1 highlight)")
    print("="*60)
    
    extractor = BooksExtractor()
    books, highlights = extractor.extract_all()
    
    if not highlights:
        print("❌ No highlights to process")
        return False
    
    # Get first highlight with a book
    highlight = None
    for h in highlights:
        if h.book:
            highlight = h
            break
    
    if not highlight:
        print("❌ No highlights with book data")
        return False
    
    print(f"\nProcessing highlight from: {highlight.book.title}")
    print(f"Content: {highlight.content[:100]}...")
    print()
    
    importer = BooksImporter()
    ai_data = importer.process_highlight_with_ai(
        highlight.content,
        highlight.book.title,
        highlight.book.author
    )
    
    print("\n🤖 AI Results:")
    print(f"   Relevance: {ai_data.get('relevance_score')}/10")
    print(f"   Category: {ai_data.get('category')}")
    print(f"   Insight: {ai_data.get('core_insight', 'N/A')[:100]}...")
    print(f"   Entities: {[e.get('name') for e in ai_data.get('entities', [])]}")
    print(f"   Concepts: {ai_data.get('concepts', [])}")
    
    return True

def test_page_creation():
    """Test creating one highlight page."""
    print("\n" + "="*60)
    print("🧪 Testing Page Creation (1 highlight)")
    print("="*60)
    
    extractor = BooksExtractor()
    books, highlights = extractor.extract_all()
    
    if not highlights:
        print("❌ No highlights to process")
        return False
    
    # Get first highlight with a book
    highlight = None
    for h in highlights:
        if h.book:
            highlight = h
            break
    
    if not highlight:
        print("❌ No highlights with book data")
        return False
    
    importer = BooksImporter()
    
    # Basic AI data for testing
    ai_data = {
        'core_insight': 'Test insight',
        'entities': [{'name': 'Test Author', 'type': 'person'}],
        'concepts': ['Test Concept'],
        'relevance_score': 8,
        'category': 'test'
    }
    
    print(f"\nCreating page for: {highlight.content[:50]}...")
    filepath = importer.create_highlight_page(highlight, ai_data)
    
    if os.path.exists(filepath):
        print(f"✅ Created: {filepath}")
        
        # Show content preview
        with open(filepath, 'r') as f:
            content = f.read()
            print("\n📄 Page preview:")
            print(content[:500])
            print("...")
    else:
        print("❌ File not created")
        return False
    
    return True

def main():
    print("📚 Book Importer Test Suite")
    print()
    
    # Test 1: Extraction
    if not test_extractor():
        print("\n❌ Extractor test failed")
        return 1
    
    # Test 2: AI Processing
    if not test_ai_processing():
        print("\n❌ AI processing test failed")
        return 1
    
    # Test 3: Page Creation
    if not test_page_creation():
        print("\n❌ Page creation test failed")
        return 1
    
    print("\n" + "="*60)
    print("✅ All tests passed!")
    print("="*60)
    print("\nReady to run full import:")
    print("   python backend/cli.py import-books")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
