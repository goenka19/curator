"""
Books Importer
Imports book highlights into Obsidian wiki with AI processing
"""

import os
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from backend.extractors.books_extractor import BooksExtractor, generate_slug
from backend.obsidian_wiki import ObsidianWiki


class BooksImporter:
    """Imports book highlights into the Obsidian vault."""
    
    def __init__(self, vault_path: str = None):
        if vault_path is None:
            vault_path = "/Users/ujjwalgoenka/Desktop/Coding/curator/curator_vault"
        
        self.vault_path = Path(vault_path)
        self.wiki = ObsidianWiki(vault_path)
        self.groq_key = os.getenv('GROQ_API_KEY')
        
        # Paths for wiki content
        self.highlights_path = self.vault_path / "wiki" / "highlights"
        self.books_path = self.vault_path / "wiki" / "books"
        
        self.highlights_path.mkdir(parents=True, exist_ok=True)
        self.books_path.mkdir(parents=True, exist_ok=True)
    
    def process_highlight_with_ai(self, content: str, book_title: str, author: str) -> Dict:
        """Process a highlight with Groq AI to extract insights."""
        if not self.groq_key:
            print("   ⚠️  GROQ_API_KEY not set, using basic processing")
            return self._basic_processing(content)
        
        prompt = f"""Analyze this book highlight for KNOWLEDGE VALUE. Be extremely selective.

Highlight: {content}
Book: {book_title}
Author: {author}

REJECT and mark low relevance (1-3) if:
- Generic motivational content without specific insight
- Pure entertainment with no learning value
- Common knowledge stated plainly

ACCEPT and extract ONLY if:
- Changes how to think about a topic
- Contains specific, reference-able insights
- Explains WHY or HOW something works
- Connects concepts in a novel way

Return JSON:
{{
  "core_insight": "One sentence: what is the key takeaway?",
  "entities": [{{"name": "person/company/book mentioned", "type": "person|company|book"}}],
  "concepts": ["specific topics/frameworks/mental models"],
  "relevance_score": 1-10 (be harsh: 7+ only if truly valuable),
  "category": "wealth|psychology|business|productivity|philosophy|other"
}}

Remember: Extract specific concepts that could link to other knowledge."""

        max_retries = 3
        base_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                headers = {
                    'Authorization': f'Bearer {self.groq_key}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'model': 'llama-3.3-70b-versatile',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'response_format': {'type': 'json_object'},
                    'max_tokens': 500,
                    'temperature': 0.3
                }
                
                response = requests.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()['choices'][0]['message']['content']
                    data = json.loads(result)
                    
                    # Ensure required fields exist
                    return {
                        'core_insight': data.get('core_insight', ''),
                        'entities': data.get('entities', []),
                        'concepts': data.get('concepts', []),
                        'relevance_score': data.get('relevance_score', 5),
                        'category': data.get('category', 'other')
                    }
                elif response.status_code == 429:
                    # Rate limit - wait and retry
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(delay)
                        continue
                    else:
                        print(f"   ⚠️  Rate limit (429) after {max_retries} retries")
                        return self._basic_processing(content)
                else:
                    print(f"   ❌ Groq API error: {response.status_code}")
                    return self._basic_processing(content)
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    import time
                    time.sleep(base_delay)
                    continue
                else:
                    print(f"   ❌ AI processing error: {e}")
                    return self._basic_processing(content)
        
        return self._basic_processing(content)
    
    def _basic_processing(self, content: str) -> Dict:
        """Fallback processing without AI."""
        return {
            'core_insight': '',
            'entities': [],
            'concepts': [],
            'relevance_score': 7,
            'category': 'other'
        }
    
    def create_highlight_page(self, highlight, ai_data: Dict) -> str:
        """Create a wiki page for a highlight."""
        slug = generate_slug(highlight.content)
        filename = f"{slug}.md"
        filepath = self.highlights_path / filename
        
        # Skip if already exists
        if filepath.exists():
            print(f"   ⏩ Highlight page exists: {filename}")
            return str(filepath)
        
        book_title = highlight.book.title if highlight.book else "Unknown"
        author = highlight.book.author if highlight.book else "Unknown"
        
        # Format entities
        entities_md = ""
        if ai_data.get('entities'):
            for entity in ai_data['entities']:
                name = entity.get('name', '')
                if name:
                    # Create safe wiki link
                    safe_name = name.replace('|', '').strip()
                    entities_md += f"- [[{safe_name}]]\n"
        
        # Format concepts
        concepts_md = ""
        if ai_data.get('concepts'):
            for concept in ai_data['concepts']:
                if concept:
                    # Create safe wiki link
                    safe_concept = concept.replace('|', '').strip()
                    concepts_md += f"- [[{safe_concept}]]\n"
        
        # Build page content
        content = f"""---
type: highlight
source: book
book: "[[{book_title}]]"
author: "[[{author}]]"
location: "{highlight.location}"
relevance: {ai_data.get('relevance_score', 5)}/10
category: {ai_data.get('category', 'other')}
learned_date: {datetime.now().strftime('%Y-%m-%d')}
---

> "{highlight.content}"
"""
        
        # Add core insight if available
        if ai_data.get('core_insight'):
            content += f"""
## Insight

{ai_data['core_insight']}
"""
        
        content += f"""
## Source

From: [[{book_title}]] by [[{author}]]
"""
        
        # Add entities section
        if entities_md:
            content += f"""
## Entities

{entities_md}
"""
        
        # Add concepts section
        if concepts_md:
            content += f"""
## Concepts

{concepts_md}
"""
        
        # Write file
        filepath.write_text(content, encoding='utf-8')
        return str(filepath)
    
    def create_book_page(self, book, highlights: List) -> str:
        """Create a wiki page for a book with READABLE highlights."""
        # Create safe filename
        safe_title = book.title.replace('/', '-').replace(':', '').strip()
        filename = f"{safe_title}.md"
        filepath = self.books_path / filename
        
        # Collect all highlights content (readable format)
        highlights_content = []
        all_concepts = set()
        all_entities = set()
        
        for i, highlight in enumerate(highlights, 1):
            slug = generate_slug(highlight.content)
            
            # Create readable highlight entry with full text
            highlight_entry = f"""### {i}. {highlight.location}

> {highlight.content}

→ [[{slug}|View extracted concepts & connections]]
"""
            highlights_content.append(highlight_entry)
        
        # Build page content
        content = f"""---
type: book
author: "[[{book.author}]]"
read_date: {book.created_at[:10] if book.created_at else 'Unknown'}
total_highlights: {len(highlights)}
source: books
---

# {book.title}

**Author:** [[{book.author}]]  
**Highlights:** {len(highlights)}  
**Read:** {book.created_at[:10] if book.created_at else 'Unknown'}

"""
        
        # Add cover image if available
        if book.cover_url:
            content += f"![Cover]({book.cover_url})\n\n"
        
        content += f"## Highlights ({len(highlights)})\n\n"
        content += "\n---\n\n".join(highlights_content)
        content += "\n"
        
        # Write file
        filepath.write_text(content, encoding='utf-8')
        return str(filepath)
    
    def import_all(self) -> Dict:
        """Import all books and highlights."""
        print("📚 Starting book import...")
        print("="*60)
        
        # Extract data
        extractor = BooksExtractor()
        books, highlights = extractor.extract_all()
        
        if not books or not highlights:
            print("❌ No data to import")
            return {'highlights_created': 0, 'books_created': 0}
        
        stats = {
            'highlights_created': 0,
            'books_created': 0,
            'ai_processed': 0,
            'errors': 0
        }
        
        # Process highlights
        print(f"\n📝 Processing {len(highlights)} highlights...")
        for i, highlight in enumerate(highlights, 1):
            if highlight.book is None:
                print(f"   ⏩ [{i}/{len(highlights)}] Skipping - no book match")
                continue
            
            try:
                print(f"   🧠 [{i}/{len(highlights)}] AI processing...", end=" ")
                ai_data = self.process_highlight_with_ai(
                    highlight.content,
                    highlight.book.title,
                    highlight.book.author
                )
                stats['ai_processed'] += 1
                print(f"Score: {ai_data.get('relevance_score', 5)}/10")
                
                # Create highlight page
                self.create_highlight_page(highlight, ai_data)
                stats['highlights_created'] += 1
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                stats['errors'] += 1
        
        # Create book pages
        print(f"\n📖 Creating {len(books)} book pages...")
        for book in books:
            book_highlights = [h for h in highlights if h.book_id == book.id]
            if book_highlights:
                self.create_book_page(book, book_highlights)
                stats['books_created'] += 1
                print(f"   ✅ {book.title} ({len(book_highlights)} highlights)")
        
        # Update vault index
        print("\n🔄 Updating vault index...")
        self._update_index(books)
        
        print("\n" + "="*60)
        print("✅ Import complete!")
        print(f"   Highlights created: {stats['highlights_created']}")
        print(f"   Books created: {stats['books_created']}")
        print(f"   AI processed: {stats['ai_processed']}")
        print(f"   Errors: {stats['errors']}")
        
        return stats
    
    def _update_index(self, books: List):
        """Update the vault index with books section."""
        index_path = self.vault_path / "index.md"
        
        if not index_path.exists():
            return
        
        content = index_path.read_text(encoding='utf-8')
        
        # Check if books section already exists
        if "## Books" in content:
            return
        
        # Add books section
        books_section = f"""
## Books

{len(books)} books imported with highlights:

"""
        for book in books:
            books_section += f"- [[{book.title}]] by [[{book.author}]]\n"
        
        content += books_section
        index_path.write_text(content, encoding='utf-8')
        print("   ✅ Added books section to index")


if __name__ == "__main__":
    importer = BooksImporter()
    stats = importer.import_all()
    print(f"\nCreated {stats['highlights_created']} highlights and {stats['books_created']} books")
