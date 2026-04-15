"""
Books Extractor
Parses book exports from CSV files
"""

import csv
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Book:
    """Represents a book from the export."""
    id: int
    title: str
    author: str
    cover_url: Optional[str]
    created_at: str


@dataclass
class Highlight:
    """Represents a highlight from a book."""
    id: int
    book_id: int
    content: str
    location: str
    created_at: str
    book: Optional[Book] = None


class BooksExtractor:
    """Extracts books and highlights from CSV exports."""
    
    def __init__(self, books_file: str = "export.csv", highlights_file: str = "export2.csv"):
        self.books_file = Path(books_file)
        self.highlights_file = Path(highlights_file)
    
    def extract_books(self) -> List[Book]:
        """Parse books from export.csv"""
        books = []
        
        if not self.books_file.exists():
            print(f"❌ Books file not found: {self.books_file}")
            return books
        
        with open(self.books_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                book = Book(
                    id=int(row['id']),
                    title=row['title'],
                    author=row['author'],
                    cover_url=row.get('cover_url') or None,
                    created_at=row['created_at']
                )
                books.append(book)
        
        return books
    
    def extract_highlights(self) -> List[Highlight]:
        """Parse highlights from export2.csv"""
        highlights = []
        
        if not self.highlights_file.exists():
            print(f"❌ Highlights file not found: {self.highlights_file}")
            return highlights
        
        with open(self.highlights_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Clean up content (remove extra whitespace)
                content = row['content'].strip()
                if content:
                    highlight = Highlight(
                        id=int(row['id']),
                        book_id=int(row['book_id']),
                        content=content,
                        location=row.get('location', ''),
                        created_at=row['created_at']
                    )
                    highlights.append(highlight)
        
        return highlights
    
    def link_highlights_to_books(self, books: List[Book], highlights: List[Highlight]) -> List[Highlight]:
        """Link each highlight to its book."""
        book_map = {book.id: book for book in books}
        
        for highlight in highlights:
            highlight.book = book_map.get(highlight.book_id)
        
        return highlights
    
    def extract_all(self) -> Tuple[List[Book], List[Highlight]]:
        """Extract and link all data."""
        print("📚 Extracting books and highlights...")
        
        books = self.extract_books()
        print(f"   Found {len(books)} books")
        
        highlights = self.extract_highlights()
        print(f"   Found {len(highlights)} highlights")
        
        highlights = self.link_highlights_to_books(books, highlights)
        
        # Report unlinked highlights
        unlinked = [h for h in highlights if h.book is None]
        if unlinked:
            print(f"   ⚠️  {len(unlinked)} highlights without matching books")
        
        return books, highlights


def generate_slug(text: str, max_words: int = 6) -> str:
    """Generate a URL-friendly slug from highlight text."""
    import re
    
    # Remove special characters, keep only alphanumeric and spaces
    cleaned = re.sub(r'[^\w\s]', '', text)
    
    # Split into words and take first N
    words = cleaned.split()[:max_words]
    
    # Join with hyphens, lowercase
    slug = '-'.join(words).lower()
    
    # Limit length
    if len(slug) > 60:
        slug = slug[:60].rsplit('-', 1)[0]
    
    return slug


if __name__ == "__main__":
    extractor = BooksExtractor()
    books, highlights = extractor.extract_all()
    
    print("\n📖 Books:")
    for book in books:
        book_highlights = [h for h in highlights if h.book_id == book.id]
        print(f"   {book.title} by {book.author} - {len(book_highlights)} highlights")
    
    print("\n📝 Sample highlights:")
    for h in highlights[:3]:
        slug = generate_slug(h.content)
        print(f"   [{h.book.title if h.book else 'Unknown'}] {slug}")
        print(f"      {h.content[:100]}...")
        print()
