"""
Obsidian Wiki Integration
Handles: page creation, index updates, cross-referencing, synthesis generation
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session

class ObsidianWiki:
    """Manages Obsidian vault operations for content curation."""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.wiki_path = self.vault_path / "wiki"
        self.raw_path = self.vault_path / "raw-sources"
        
    def _slugify(self, text: str) -> str:
        """Convert text to filename-safe slug while preserving readability."""
        # Keep spaces for Obsidian readability, just remove problematic chars
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        return text.strip()
    
    def _slugify_title(self, title: str) -> str:
        """Convert title to filename-safe slug."""
        # Remove special chars, keep spaces for readability in title
        slug = re.sub(r'[<>:"/\\|?*]', '', title)
        # Limit length
        return slug[:80].strip()
    
    def create_summary_page(self, item: dict) -> str:
        """Create a summary page for processed content with descriptive title."""
        source = item['source']
        source_id = item['id']
        title = item.get('title', 'Untitled')
        
        # Check if this is an X Article that needs manual extraction
        has_x_article = item.get('has_x_article', False)
        x_article_url = item.get('x_article_url')
        
        # Use descriptive title for filename (NOT twitter-12345)
        if has_x_article and x_article_url:
            filename_base = "x-article-needs-extraction"
        else:
            filename_base = self._slugify_title(title)
        if not filename_base:
            filename_base = f"{source}-{source_id}"
        filename = f"{filename_base}.md"
        filepath = self.wiki_path / "summaries" / filename
        
        # Extract entities and concepts for linking
        entities = item.get('entities', [])
        concepts = item.get('concepts', [])
        
        # Build entity links (only names, not full objects)
        entity_links = " ".join([f"[[{e if isinstance(e, str) else e.get('name', 'Unknown')}]]" for e in entities]) if entities else "None"
        concept_links = " ".join([f"[[{c}]]" for c in concepts]) if concepts else "None"
        
        # Truncate original text (don't store full transcript)
        original = item.get('original_text', '')
        if len(original) > 300:
            original = original[:300] + "... [truncated]"
        
        # Special handling for X Articles
        if has_x_article and x_article_url:
            content = f"""---
title: X Article - Requires Manual Extraction
type: summary
source: {source}
source_id: "{source_id}"
author: "{item.get('author', 'unknown')}"
date: "{item.get('date', datetime.now().strftime('%Y-%m-%d'))}"
ingested: "{datetime.now().strftime('%Y-%m-%d')}"
tags: ["x-article", "needs-extraction"]
relevance: {item.get('relevance_score', 5)}
entities: {json.dumps([e if isinstance(e, str) else e.get('name') for e in entities])}
concepts: {json.dumps(concepts)}
---

# X Article - Requires Manual Extraction

**Source:** {source} | **Author:** {item.get('author', 'unknown')}
**Date:** {item.get('date', 'unknown')} | **Ingested:** {datetime.now().strftime('%Y-%m-%d')}

## ⚠️ Manual Extraction Required

This tweet contains an X Article that cannot be fetched automatically.

**X Article URL:** {x_article_url}

## Action Required

1. Visit the URL above
2. Read the article
3. Copy important insights to: `raw-sources/x-articles/{source_id}.md`
4. Run `python backend/cli.py wiki-ingest` to process

## Tweet Context

{original}

## Entities

{entity_links}

## Concepts

{concept_links}

## Related
<!-- Auto-populated by cross-reference -->
"""
        else:
            content = f"""---
title: {title[:80]}
type: summary
source: {source}
source_id: "{source_id}"
author: "{item.get('author', 'unknown')}"
date: "{item.get('date', datetime.now().strftime('%Y-%m-%d'))}"
ingested: "{datetime.now().strftime('%Y-%m-%d')}"
tags: {json.dumps(item.get('tags', []))}
relevance: {item.get('relevance_score', 5)}
entities: {json.dumps([e if isinstance(e, str) else e.get('name') for e in entities])}
concepts: {json.dumps(concepts)}
---

# {title[:80]}

**Source:** {source} | **Author:** {item.get('author', 'unknown')}
**Date:** {item.get('date', 'unknown')} | **Ingested:** {datetime.now().strftime('%Y-%m-%d')}

## Insight

{item.get('summary', 'No summary available.')}

## Source

{original}

## Entities

{entity_links}

## Concepts

{concept_links}

## Related
<!-- Auto-populated by cross-reference -->
"""
        
        # Atomic write to prevent corruption
        temp_path = filepath.with_suffix('.tmp')
        temp_path.write_text(content, encoding='utf-8')
        temp_path.replace(filepath)
        
        return str(filepath)
    
    def update_entity_page(self, entity_name: str, entity_type: str, source_ref: str, 
                          context: str = "", source_date: str = None) -> str:
        """Create or update an entity page with bi-temporal references."""
        filename = self._slugify(entity_name) + ".md"
        filepath = self.wiki_path / "entities" / filename
        
        today = datetime.now().strftime('%Y-%m-%d')
        source_date = source_date or today
        
        if filepath.exists():
            # Update existing page
            content = filepath.read_text(encoding='utf-8')
            
            # Check if already referenced
            if source_ref in content:
                return str(filepath)
            
            # Add new bi-temporal reference
            reference_entry = f"- [[{source_ref}]] ({source_date}) - {context[:100]}{'...' if len(context) > 100 else ''}\n  - Ingested: {today}\n"
            
            # Insert after "## References"
            if "## References" in content:
                content = content.replace(
                    "## References\n",
                    f"## References\n{reference_entry}"
                )
            else:
                content += f"\n## References\n{reference_entry}"
            
            # Update frontmatter date
            content = re.sub(
                r'updated: "\d{4}-\d{2}-\d{2}"',
                f'updated: "{today}"',
                content
            )
            
            temp_path = filepath.with_suffix('.tmp')
            temp_path.write_text(content, encoding='utf-8')
            temp_path.replace(filepath)
            
        else:
            # Create new entity page
            content = f"""---
title: "{entity_name}"
type: entity
entity_type: {entity_type}
created: "{today}"
updated: "{today}"
tags: [entity]
---

# {entity_name}

**Type:** {entity_type}

## About
<!-- AI-generated description will appear here -->

## References

- [[{source_ref}]] ({source_date}) - {context[:100]}{'...' if len(context) > 100 else ''}
  - Ingested: {today}

## Related Entities
<!-- Auto-populated -->

## Related Concepts
<!-- Auto-populated -->
"""
            filepath.write_text(content, encoding='utf-8')
        
        return str(filepath)
    
    def update_concept_page(self, concept_name: str, source_ref: str, 
                           snippet: str = "", source_date: str = None) -> str:
        """Create or update a concept page with aggregated knowledge."""
        filename = self._slugify(concept_name) + ".md"
        filepath = self.wiki_path / "concepts" / filename
        
        today = datetime.now().strftime('%Y-%m-%d')
        source_date = source_date or today
        
        if filepath.exists():
            content = filepath.read_text(encoding='utf-8')
            
            # Check if already referenced
            if source_ref in content:
                return str(filepath)
            
            # Add new source reference
            source_entry = f"- [[{source_ref}]] ({source_date}): {snippet[:100]}{'...' if len(snippet) > 100 else ''}\n"
            
            if "## Sources" in content:
                content = content.replace(
                    "## Sources\n",
                    f"## Sources\n{source_entry}"
                )
            else:
                content += f"\n## Sources\n{source_entry}"
            
            # Update date
            content = re.sub(
                r'updated: "\d{4}-\d{2}-\d{2}"',
                f'updated: "{today}"',
                content
            )
            
            temp_path = filepath.with_suffix('.tmp')
            temp_path.write_text(content, encoding='utf-8')
            temp_path.replace(filepath)
            
        else:
            # Create concept page with initial content from source
            overview = f"**What is {concept_name}?**\n\n"
            if snippet:
                overview += f"Based on: {snippet[:200]}{'...' if len(snippet) > 200 else ''}\n\n"
            overview += f"*{concept_name} is a topic mentioned in curated content. This page aggregates knowledge about it over time.*"
            
            content = f"""---
title: "{concept_name}"
type: concept
created: "{today}"
updated: "{today}"
tags: [concept]
related_concepts: []
---

# {concept_name}

## Overview

{overview}

## Key Principles
<!-- Will be populated as more sources mention this concept -->

## Sources

- [[{source_ref}]] ({source_date}): {snippet[:150]}{'...' if len(snippet) > 150 else ''}

## Related Concepts
<!-- Auto-populated as connections emerge -->

## Related Entities
<!-- Auto-populated -->
"""
            filepath.write_text(content, encoding='utf-8')
        
        return str(filepath)
    
    def update_index(self, item: dict, page_path: str):
        """Add entry to index.md."""
        index_path = self.wiki_path / "index.md"
        
        if not index_path.exists():
            return
        
        content = index_path.read_text(encoding='utf-8')
        page_ref = Path(page_path).stem
        
        # Add to Summaries table
        entry = f"| {item['source']} | [[{page_ref}]] | {item.get('date', datetime.now().strftime('%Y-%m-%d'))} | {', '.join(item.get('tags', []))} | {item.get('relevance_score', 5)} |\n"
        
        marker = "<!-- Auto-populated by ingest -->"
        if marker in content and entry.strip() not in content:
            content = content.replace(
                f"{marker}\n",
                f"{entry}{marker}\n",
                1  # Only replace first occurrence (Summaries section)
            )
            index_path.write_text(content, encoding='utf-8')
    
    def update_entity_index(self, entity_name: str, entity_type: str, mention_count: int = 1):
        """Update entity count in index."""
        index_path = self.wiki_path / "index.md"
        
        if not index_path.exists():
            return
        
        content = index_path.read_text(encoding='utf-8')
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Check if entity already in index
        if f"[[{entity_name}]]" in content:
            # Update mention count (requires parsing table - skip for now)
            pass
        else:
            # Add new entity entry
            entry = f"| [[{entity_name}]] | {entity_type} | {mention_count} | {today} |\n"
            
            # Find Entities section marker
            sections = content.split("## Entities")
            if len(sections) > 1:
                marker = "<!-- Auto-populated by ingest -->"
                if marker in sections[1]:
                    sections[1] = sections[1].replace(
                        f"{marker}\n",
                        f"{entry}{marker}\n",
                        1
                    )
                    content = "## Entities".join(sections)
                    index_path.write_text(content, encoding='utf-8')
    
    def update_concept_index(self, concept_name: str, source_count: int = 1):
        """Update concept count in index."""
        index_path = self.wiki_path / "index.md"
        
        if not index_path.exists():
            return
        
        content = index_path.read_text(encoding='utf-8')
        today = datetime.now().strftime('%Y-%m-%d')
        
        if f"[[{concept_name}]]" in content:
            return
        
        entry = f"| [[{concept_name}]] | {source_count} | {today} | |\n"
        
        sections = content.split("## Concepts")
        if len(sections) > 1:
            marker = "<!-- Auto-populated by ingest -->"
            if marker in sections[1]:
                sections[1] = sections[1].replace(
                    f"{marker}\n",
                    f"{entry}{marker}\n",
                    1
                )
                content = "## Concepts".join(sections)
                index_path.write_text(content, encoding='utf-8')
    
    def append_log(self, operation: str, description: str, details: dict = None):
        """Append to activity log."""
        log_path = self.wiki_path / "log.md"
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        entry = f"\n## [{timestamp}] {operation} | {description}\n"
        
        if details:
            for key, value in details.items():
                if isinstance(value, list):
                    entry += f"- {key}: {', '.join(value)}\n"
                else:
                    entry += f"- {key}: {value}\n"
        
        with open(log_path, "a", encoding='utf-8') as f:
            f.write(entry)
    
    def ingest_item(self, item: dict) -> List[str]:
        """Full ingest workflow for a single item."""
        created_files = []
        
        try:
            # 1. Create summary page
            page_path = self.create_summary_page(item)
            page_ref = Path(page_path).stem
            created_files.append(page_path)
            
            # 2. Update/create entity pages
            for entity in item.get('entities', []):
                if isinstance(entity, dict):
                    entity_name = entity.get('name', 'Unknown')
                    entity_type = entity.get('type', 'unknown')
                else:
                    entity_name = entity
                    entity_type = 'unknown'
                
                entity_path = self.update_entity_page(
                    entity_name, 
                    entity_type, 
                    page_ref,
                    context=item.get('summary', '')[:200],
                    source_date=item.get('date')
                )
                self.update_entity_index(entity_name, entity_type)
                if entity_path not in created_files:
                    created_files.append(entity_path)
            
            # 3. Update/create concept pages
            for concept in item.get('concepts', []):
                concept_path = self.update_concept_page(
                    concept, 
                    page_ref,
                    snippet=item.get('summary', '')[:200],
                    source_date=item.get('date')
                )
                self.update_concept_index(concept)
                if concept_path not in created_files:
                    created_files.append(concept_path)
            
            # 4. Update index
            self.update_index(item, page_path)
            
            # 5. Log activity
            self.append_log(
                "ingest",
                f"{item['source']}-{item['id']}: {item.get('title', 'Untitled')[:50]}",
                details={
                    "Entities": [e.get('name', e) if isinstance(e, dict) else e for e in item.get('entities', [])],
                    "Concepts": item.get('concepts', []),
                    "Relevance": item.get('relevance_score', 5)
                }
            )
            
            return created_files
            
        except Exception as e:
            self.append_log("error", f"Failed to ingest {item.get('id', 'unknown')}: {str(e)}")
            raise


if __name__ == "__main__":
    # Test the module
    wiki = ObsidianWiki("/Users/ujjwalgoenka/Desktop/Coding/curator/curator_vault")
    
    test_item = {
        'id': '12345',
        'source': 'twitter',
        'title': 'Apollo Global expanding private credit',
        'author': '@finance_guru',
        'date': '2025-04-14',
        'original_text': 'Apollo Global is expanding their private credit business...',
        'summary': 'Apollo Global is expanding operations in private credit markets.',
        'key_points': '- Expansion announced\n- Focus on direct lending',
        'entities': [{'name': 'Apollo Global', 'type': 'company'}],
        'concepts': ['Private Credit', 'Direct Lending'],
        'tags': ['finance', 'private-credit'],
        'relevance_score': 9
    }
    
    files = wiki.ingest_item(test_item)
    print(f"Created files: {files}")
