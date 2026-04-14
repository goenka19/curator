"""
Wiki Linting System
Checks for: orphan pages, contradictions, gaps, synthesis opportunities
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict

class WikiLinter:
    """Lints the Obsidian wiki for issues and opportunities."""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.wiki_path = self.vault_path / "wiki"
        self.issues = []
        self.synthesis_opportunities = []
        self.contradictions = []
        
    def lint(self) -> Dict:
        """Run full lint check."""
        print("🔍 Running wiki lint...")
        
        # Find all pages
        all_pages = self._get_all_pages()
        print(f"   Found {len(all_pages)} total pages")
        
        # Check for orphans
        orphans = self._find_orphans(all_pages)
        
        # Check for gaps (concepts mentioned but no page)
        gaps = self._find_gaps(all_pages)
        
        # Find synthesis opportunities
        synthesis = self._find_synthesis_opportunities(all_pages)
        
        # Check for contradictions
        contradictions = self._find_contradictions(all_pages)
        
        # Generate report
        report = self._generate_report(orphans, gaps, synthesis, contradictions)
        
        return report
    
    def _get_all_pages(self) -> List[Path]:
        """Get all markdown pages in wiki."""
        pages = []
        for folder in ['summaries', 'entities', 'concepts', 'synthesis']:
            folder_path = self.wiki_path / folder
            if folder_path.exists():
                pages.extend(folder_path.glob('*.md'))
        return pages
    
    def _extract_links(self, content: str) -> Set[str]:
        """Extract all [[wiki links]] from content."""
        links = set()
        # Match [[Page Name]] or [[Page Name|Display Text]]
        pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
        matches = re.findall(pattern, content)
        for match in matches:
            links.add(match.strip())
        return links
    
    def _find_orphans(self, pages: List[Path]) -> List[str]:
        """Find pages with no inbound links."""
        print("   Checking for orphan pages...")
        
        # Build link graph
        all_links = defaultdict(set)
        page_names = set()
        
        for page in pages:
            page_name = page.stem
            page_names.add(page_name)
            content = page.read_text(encoding='utf-8')
            links = self._extract_links(content)
            for link in links:
                all_links[link].add(page_name)
        
        # Find orphans (pages with no inbound links except self)
        orphans = []
        for page_name in page_names:
            inbound = all_links.get(page_name, set())
            # Remove self-references
            inbound = inbound - {page_name}
            if len(inbound) == 0:
                orphans.append(page_name)
        
        return orphans
    
    def _find_gaps(self, pages: List[Path]) -> List[str]:
        """Find concepts mentioned in summaries but missing dedicated pages."""
        print("   Checking for knowledge gaps...")
        
        # Get existing concept pages
        concept_pages = set()
        concepts_folder = self.wiki_path / "concepts"
        if concepts_folder.exists():
            concept_pages = {p.stem for p in concepts_folder.glob('*.md')}
        
        # Get mentioned concepts from summaries
        mentioned_concepts = set()
        summaries_folder = self.wiki_path / "summaries"
        if summaries_folder.exists():
            for summary in summaries_folder.glob('*.md'):
                content = summary.read_text(encoding='utf-8')
                # Extract from frontmatter concepts field
                concepts_match = re.search(r'concepts: (\[.*?\])', content)
                if concepts_match:
                    try:
                        concepts = json.loads(concepts_match.group(1))
                        mentioned_concepts.update(concepts)
                    except:
                        pass
        
        # Find gaps
        gaps = mentioned_concepts - concept_pages
        return list(gaps)
    
    def _find_synthesis_opportunities(self, pages: List[Path]) -> List[Dict]:
        """Find patterns across multiple sources."""
        print("   Finding synthesis opportunities...")
        
        # Track entity-concept pairs
        entity_concept_pairs = defaultdict(list)
        concept_sources = defaultdict(list)
        
        summaries_folder = self.wiki_path / "summaries"
        if not summaries_folder.exists():
            return []
        
        for summary in summaries_folder.glob('*.md'):
            content = summary.read_text(encoding='utf-8')
            
            # Extract entities and concepts
            entities = []
            concepts = []
            
            entities_match = re.search(r'entities: (\[.*?\])', content)
            concepts_match = re.search(r'concepts: (\[.*?\])', content)
            
            if entities_match:
                try:
                    entities = json.loads(entities_match.group(1))
                except:
                    pass
            
            if concepts_match:
                try:
                    concepts = json.loads(concepts_match.group(1))
                except:
                    pass
            
            # Track pairs
            for entity in entities:
                entity_name = entity if isinstance(entity, str) else entity.get('name', '')
                for concept in concepts:
                    pair = (entity_name, concept)
                    entity_concept_pairs[pair].append(summary.stem)
            
            # Track concept-only
            for concept in concepts:
                concept_sources[concept].append(summary.stem)
        
        # Find opportunities (3+ sources)
        opportunities = []
        
        # Entity + Concept pairs
        for (entity, concept), sources in entity_concept_pairs.items():
            if len(sources) >= 3:
                opportunities.append({
                    'type': 'entity_concept',
                    'entity': entity,
                    'concept': concept,
                    'sources': sources,
                    'count': len(sources)
                })
        
        # Concept-only (5+ sources for broader patterns)
        for concept, sources in concept_sources.items():
            if len(sources) >= 5:
                opportunities.append({
                    'type': 'concept_only',
                    'concept': concept,
                    'sources': sources,
                    'count': len(sources)
                })
        
        return opportunities
    
    def _find_contradictions(self, pages: List[Path]) -> List[Dict]:
        """Find contradictory claims across sources."""
        print("   Checking for contradictions...")
        
        # This is a simplified version - full implementation would need NLP
        # For now, flag if same entity has very different sentiment/tone
        
        entity_sentiments = defaultdict(list)
        
        summaries_folder = self.wiki_path / "summaries"
        if not summaries_folder.exists():
            return []
        
        for summary in summaries_folder.glob('*.md'):
            content = summary.read_text(encoding='utf-8')
            
            # Extract entities
            entities_match = re.search(r'entities: (\[.*?\])', content)
            if entities_match:
                try:
                    entities = json.loads(entities_match.group(1))
                    # Simple sentiment check
                    summary_lower = content.lower()
                    
                    for entity in entities:
                        entity_name = entity if isinstance(entity, str) else entity.get('name', '')
                        
                        # Very simple polarity detection
                        positive = ['good', 'great', 'excellent', 'success', 'growth', 'profit']
                        negative = ['bad', 'fail', 'loss', 'risk', 'problem', 'issue']
                        
                        pos_count = sum(1 for p in positive if p in summary_lower)
                        neg_count = sum(1 for n in negative if n in summary_lower)
                        
                        if pos_count > neg_count:
                            sentiment = 'positive'
                        elif neg_count > pos_count:
                            sentiment = 'negative'
                        else:
                            sentiment = 'neutral'
                        
                        entity_sentiments[entity_name].append({
                            'source': summary.stem,
                            'sentiment': sentiment,
                            'date': self._extract_date(content)
                        })
                except:
                    pass
        
        # Find contradictions (same entity, different sentiments)
        contradictions = []
        for entity, sentiments in entity_sentiments.items():
            if len(sentiments) >= 2:
                # Check for mixed sentiments
                unique_sentiments = set(s['sentiment'] for s in sentiments)
                if len(unique_sentiments) > 1 and 'neutral' not in unique_sentiments:
                    contradictions.append({
                        'entity': entity,
                        'sentiments': sentiments,
                        'issue': f"Mixed sentiment: {', '.join(unique_sentiments)}"
                    })
        
        return contradictions
    
    def _extract_date(self, content: str) -> str:
        """Extract date from content."""
        date_match = re.search(r'date: "(\d{4}-\d{2}-\d{2})"', content)
        if date_match:
            return date_match.group(1)
        return 'unknown'
    
    def _generate_report(self, orphans: List[str], gaps: List[str], 
                        synthesis: List[Dict], contradictions: List[Dict]) -> Dict:
        """Generate lint report."""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'orphan_pages': len(orphans),
                'knowledge_gaps': len(gaps),
                'synthesis_opportunities': len(synthesis),
                'contradictions': len(contradictions)
            },
            'orphans': orphans,
            'gaps': gaps,
            'synthesis_opportunities': synthesis,
            'contradictions': contradictions
        }
        
        # Write report
        report_date = datetime.now().strftime('%Y-%m-%d')
        report_path = self.wiki_path / "synthesis" / f"lint-report-{report_date}.md"
        
        content = f"""# Lint Report - {report_date}

## Summary

- **Orphan Pages**: {len(orphans)}
- **Knowledge Gaps**: {len(gaps)}
- **Synthesis Opportunities**: {len(synthesis)}
- **Contradictions**: {len(contradictions)}

---

## Orphan Pages (No Inbound Links)

{self._format_list(orphans) if orphans else "_No orphan pages found._"}

---

## Knowledge Gaps

Concepts mentioned but missing dedicated pages:

{self._format_list(gaps) if gaps else "_No gaps found._"}

---

## Synthesis Opportunities

{self._format_synthesis(synthesis) if synthesis else "_No synthesis opportunities yet (need 3+ sources)._"}

---

## Contradictions

{self._format_contradictions(contradictions) if contradictions else "_No contradictions found._"}

---

## Recommended Actions

1. {{orphans|length}} orphan pages need more links
2. {{gaps|length}} concept pages should be created
3. {{synthesis|length}} synthesis pages can be auto-generated
4. {{contradictions|length}} contradictions need review

*Run `python backend/cli.py wiki-generate-synthesis` to auto-create synthesis pages*
"""
        
        report_path.write_text(content, encoding='utf-8')
        print(f"   📄 Report saved: {report_path}")
        
        return report
    
    def _format_list(self, items: List[str]) -> str:
        """Format list for markdown."""
        return '\n'.join([f"- [[{item}]]" for item in items])
    
    def _format_synthesis(self, opportunities: List[Dict]) -> str:
        """Format synthesis opportunities."""
        lines = []
        for opp in opportunities:
            if opp['type'] == 'entity_concept':
                lines.append(f"### {opp['entity']} + {opp['concept']}")
                lines.append(f"- **Sources**: {opp['count']} items")
                lines.append(f"- **Pages**: {', '.join([f'[[{s}]]' for s in opp['sources'][:5]])}")
            else:
                lines.append(f"### {opp['concept']} (Concept-only)")
                lines.append(f"- **Sources**: {opp['count']} items")
            lines.append("")
        return '\n'.join(lines)
    
    def _format_contradictions(self, contradictions: List[Dict]) -> str:
        """Format contradictions."""
        lines = []
        for contra in contradictions:
            lines.append(f"### [[{contra['entity']}]]")
            lines.append(f"**Issue**: {contra['issue']}")
            for s in contra['sentiments']:
                lines.append(f"- {s['date']}: {s['sentiment']} in [[{s['source']}]]")
            lines.append("")
        return '\n'.join(lines)


if __name__ == "__main__":
    import sys
    vault_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/ujjwalgoenka/Desktop/Coding/curator/curator_vault"
    
    linter = WikiLinter(vault_path)
    report = linter.lint()
    
    print("\n" + "="*50)
    print("Lint Complete!")
    print("="*50)
    print(f"Orphan Pages: {report['summary']['orphan_pages']}")
    print(f"Knowledge Gaps: {report['summary']['knowledge_gaps']}")
    print(f"Synthesis Opportunities: {report['summary']['synthesis_opportunities']}")
    print(f"Contradictions: {report['summary']['contradictions']}")
