"""
Synthesis Generator
Auto-creates synthesis pages from patterns across sources
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from collections import defaultdict

class SynthesisGenerator:
    """Generates synthesis pages from patterns in wiki."""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.wiki_path = self.vault_path / "wiki"
        self.synthesis_path = self.wiki_path / "synthesis"
        self.synthesis_path.mkdir(exist_ok=True)
    
    def generate_all(self) -> List[str]:
        """Generate all synthesis pages from opportunities."""
        print("🧬 Generating synthesis pages...")
        
        created_pages = []
        
        # Find opportunities
        opportunities = self._find_opportunities()
        
        # Generate entity-concept syntheses
        for opp in opportunities:
            if opp['type'] == 'entity_concept':
                page_path = self._generate_entity_concept_synthesis(opp)
                if page_path:
                    created_pages.append(page_path)
            elif opp['type'] == 'concept_only':
                page_path = self._generate_concept_synthesis(opp)
                if page_path:
                    created_pages.append(page_path)
        
        # Generate contradiction pages
        contradictions = self._find_contradictions()
        if contradictions:
            page_path = self._generate_contradictions_page(contradictions)
            if page_path:
                created_pages.append(page_path)
        
        print(f"   Created {len(created_pages)} synthesis pages")
        return created_pages
    
    def _find_opportunities(self) -> List[Dict]:
        """Find synthesis opportunities (same as linter)."""
        entity_concept_pairs = defaultdict(list)
        concept_sources = defaultdict(list)
        
        summaries_folder = self.wiki_path / "summaries"
        if not summaries_folder.exists():
            return []
        
        for summary in summaries_folder.glob('*.md'):
            content = summary.read_text(encoding='utf-8')
            
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
            
            for entity in entities:
                entity_name = entity if isinstance(entity, str) else entity.get('name', '')
                for concept in concepts:
                    pair = (entity_name, concept)
                    entity_concept_pairs[pair].append({
                        'source': summary.stem,
                        'date': self._extract_date(content),
                        'insight': self._extract_insight(content)
                    })
            
            for concept in concepts:
                concept_sources[concept].append({
                    'source': summary.stem,
                    'date': self._extract_date(content),
                    'insight': self._extract_insight(content)
                })
        
        opportunities = []
        
        # Entity + Concept (3+ sources)
        for (entity, concept), sources in entity_concept_pairs.items():
            if len(sources) >= 3:
                opportunities.append({
                    'type': 'entity_concept',
                    'entity': entity,
                    'concept': concept,
                    'sources': sources,
                    'count': len(sources)
                })
        
        # Concept-only (5+ sources)
        for concept, sources in concept_sources.items():
            if len(sources) >= 5:
                opportunities.append({
                    'type': 'concept_only',
                    'concept': concept,
                    'sources': sources,
                    'count': len(sources)
                })
        
        return opportunities
    
    def _find_contradictions(self) -> List[Dict]:
        """Find contradictions (same as linter)."""
        entity_claims = defaultdict(list)
        
        summaries_folder = self.wiki_path / "summaries"
        if not summaries_folder.exists():
            return []
        
        for summary in summaries_folder.glob('*.md'):
            content = summary.read_text(encoding='utf-8')
            
            entities_match = re.search(r'entities: (\[.*?\])', content)
            if entities_match:
                try:
                    entities = json.loads(entities_match.group(1))
                    summary_lower = content.lower()
                    
                    for entity in entities:
                        entity_name = entity if isinstance(entity, str) else entity.get('name', '')
                        
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
                        
                        entity_claims[entity_name].append({
                            'source': summary.stem,
                            'sentiment': sentiment,
                            'date': self._extract_date(content)
                        })
                except:
                    pass
        
        contradictions = []
        for entity, claims in entity_claims.items():
            if len(claims) >= 2:
                unique_sentiments = set(c['sentiment'] for c in claims)
                if len(unique_sentiments) > 1 and 'neutral' not in unique_sentiments:
                    contradictions.append({
                        'entity': entity,
                        'claims': claims
                    })
        
        return contradictions
    
    def _generate_entity_concept_synthesis(self, opp: Dict) -> str:
        """Generate synthesis page for entity-concept pair."""
        entity = opp['entity']
        concept = opp['concept']
        sources = opp['sources']
        
        # Create filename
        filename = f"{entity} on {concept}.md"
        filepath = self.synthesis_path / filename
        
        # Check if already exists
        if filepath.exists():
            return None
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Build timeline table
        timeline = []
        for src in sorted(sources, key=lambda x: x['date']):
            timeline.append(f"| {src['date']} | [[{src['source']}]] | {src['insight'][:80]}... |")
        
        # Check for consistency
        insights = [s['insight'] for s in sources]
        consistent = self._check_consistency(insights)
        
        content = f"""---
title: "{entity} on {concept}"
type: synthesis
created: "{today}"
updated: "{today}"
entity: "{entity}"
concept: "{concept}"
sources_count: {len(sources)}
tags: [synthesis]
---

# {entity} on {concept}

Auto-generated synthesis from {len(sources)} sources mentioning {entity} in the context of {concept}.

## Key Pattern

{self._generate_pattern_summary(entity, concept, sources)}

## Timeline of Mentions

| Date | Source | Key Insight |
|------|--------|-------------|
{chr(10).join(timeline)}

## Claim Analysis

{consistent}

## Related

- Entity: [[{entity}]]
- Concept: [[{concept}]]
- Sources: {', '.join([f"[[{s['source']}]]" for s in sources[:3]])}{'...' if len(sources) > 3 else ''}

---

*Generated on {today} | Last updated: {today}*
"""
        
        filepath.write_text(content, encoding='utf-8')
        print(f"   ✅ Created: {filename}")
        return str(filepath)
    
    def _generate_concept_synthesis(self, opp: Dict) -> str:
        """Generate synthesis page for concept-only."""
        concept = opp['concept']
        sources = opp['sources']
        
        filename = f"Understanding {concept}.md"
        filepath = self.synthesis_path / filename
        
        if filepath.exists():
            return None
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get unique insights
        insights = [s['insight'] for s in sources if s['insight']]
        unique_insights = list(set(insights))[:5]  # Top 5 unique
        
        content = f"""---
title: "Understanding {concept}"
type: synthesis
created: "{today}"
updated: "{today}"
concept: "{concept}"
sources_count: {len(sources)}
tags: [synthesis]
---

# Understanding {concept}

Synthesis of {len(sources)} sources discussing {concept}.

## Overview

{concept} appears across multiple curated sources, indicating it is a significant topic worth understanding deeply.

## Key Insights from Sources

{chr(10).join([f"- {insight[:100]}..." for insight in unique_insights])}

## Sources

{chr(10).join([f"- [[{s['source']}]] ({s['date']}): {s['insight'][:60]}..." for s in sources[:10]])}

## Related Concepts

<!-- Will be populated as connections emerge -->

---

*Generated on {today} | Last updated: {today}*
"""
        
        filepath.write_text(content, encoding='utf-8')
        print(f"   ✅ Created: {filename}")
        return str(filepath)
    
    def _generate_contradictions_page(self, contradictions: List[Dict]) -> str:
        """Generate page documenting contradictions."""
        filename = f"Contradictions {datetime.now().strftime('%Y-%m-%d')}.md"
        filepath = self.synthesis_path / filename
        
        if filepath.exists():
            # Update existing
            pass
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        sections = []
        for contra in contradictions:
            entity = contra['entity']
            sections.append(f"### [[{entity}]]")
            
            for claim in contra['claims']:
                emoji = "✅" if claim['sentiment'] == 'positive' else "⚠️" if claim['sentiment'] == 'negative' else "➖"
                sections.append(f"- {emoji} {claim['date']} in [[{claim['source']}]]: {claim['sentiment']} sentiment")
            
            sections.append("\n**Resolution Needed**: Review these conflicting perspectives.\n")
        
        content = f"""---
title: "Detected Contradictions"
type: synthesis
created: "{today}"
updated: "{today}"
tags: [synthesis, contradictions]
---

# Detected Contradictions

The following entities have conflicting or contradictory mentions across sources.

## Summary

- **Total Contradictions**: {len(contradictions)}
- **Entities Affected**: {', '.join([f"[[{c['entity']}]]" for c in contradictions])}

---

{chr(10).join(sections)}

---

## Next Steps

1. Review each contradiction
2. Determine if they represent:
   - Temporal changes (entity evolved over time)
   - Contextual differences (different situations)
   - Genuine disagreements (sources conflict)
3. Update synthesis pages with resolution

*Detected on {today}*
"""
        
        filepath.write_text(content, encoding='utf-8')
        print(f"   ✅ Created: {filename}")
        return str(filepath)
    
    def _extract_date(self, content: str) -> str:
        """Extract date from frontmatter."""
        match = re.search(r'date: "(\d{4}-\d{2}-\d{2})"', content)
        return match.group(1) if match else 'unknown'
    
    def _extract_insight(self, content: str) -> str:
        """Extract key insight from content."""
        # Look for insight section
        match = re.search(r'## Insight\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if match:
            insight = match.group(1).strip()
            # Remove markdown bold
            insight = re.sub(r'\*\*', '', insight)
            return insight[:200]
        return "No insight extracted"
    
    def _check_consistency(self, insights: List[str]) -> str:
        """Check if insights are consistent."""
        if len(insights) < 2:
            return "_Insufficient data for consistency check._"
        
        # Simple check: do insights share keywords?
        words_sets = [set(insight.lower().split()) for insight in insights]
        common_words = set.intersection(*words_sets)
        
        if len(common_words) > 3:
            return f"✅ **Consistent**: Sources share common themes ({', '.join(list(common_words)[:3])}...)"
        else:
            return "⚠️ **Mixed**: Sources discuss different aspects or perspectives"
    
    def _generate_pattern_summary(self, entity: str, concept: str, sources: List[Dict]) -> str:
        """Generate a summary of the pattern."""
        insights = [s['insight'] for s in sources if s['insight']]
        
        if not insights:
            return f"Multiple sources mention {entity} in the context of {concept}."
        
        # Find common words across insights
        words_sets = [set(insight.lower().split()) for insight in insights]
        common = set.intersection(*words_sets) if words_sets else set()
        
        if common:
            return f"{entity} is consistently associated with {concept} across {len(sources)} sources, particularly regarding {', '.join(list(common)[:3])}."
        else:
            return f"{entity} appears in {len(sources)} different contexts related to {concept}, suggesting a broad relationship."


if __name__ == "__main__":
    import sys
    vault_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/ujjwalgoenka/Desktop/Coding/curator/curator_vault"
    
    generator = SynthesisGenerator(vault_path)
    created = generator.generate_all()
    
    print(f"\n✅ Synthesis generation complete!")
    print(f"   Created {len(created)} pages")
    for page in created:
        print(f"   - {Path(page).name}")
