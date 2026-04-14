# Content Curator Vault - Schema and Conventions

## Purpose

This vault is a personal knowledge base for curated content from Twitter/X and Instagram. It uses the LLM Wiki pattern to create a persistent, compounding knowledge graph where insights accumulate and connect over time.

## Architecture

```
curator_vault/
├── CLAUDE.md              # This file - schema and conventions
├── index.md               # Master catalog (updated on every ingest)
├── log.md                 # Chronological activity log
├── raw-sources/           # IMMUTABLE source material
│   ├── twitter/          # Raw tweet exports
│   └── instagram/        # Raw Instagram exports
└── wiki/                  # LLM-generated knowledge base
    ├── summaries/        # Source summaries (one per item)
    ├── entities/         # People, companies, tools
    ├── concepts/         # Topics, frameworks, ideas
    └── synthesis/        # Cross-source pattern analysis
```

## Operations

### Ingest Workflow

When new content arrives:

1. **Read the source** (tweet or reel)
2. **Extract**: key ideas, entities (people/companies/tools), concepts (topics)
3. **Apply pre-filter**: Skip if NBA, memes, engagement bait (use rules.json)
4. **Create summary page** in `/wiki/summaries/`
5. **Update/create entity pages** in `/wiki/entities/` with bi-temporal references
6. **Update/create concept pages** in `/wiki/concepts/` with aggregated knowledge
7. **Generate synthesis** if pattern detected across 3+ sources
8. **Add [[backlinks]]** between related pages
9. **Update index.md** with new entry
10. **Append to log.md**

### Query Workflow

When user asks a question:

1. Read index.md to find relevant pages
2. Read those pages (entity and concept pages)
3. Synthesize answer with [[citations]]
4. If answer is valuable, save as new synthesis page

### Lint Workflow (Weekly)

Health check the wiki:

1. Find orphan pages (no inbound links)
2. Find contradictions between sources
3. Find concepts mentioned but lacking dedicated pages
4. Find stale claims superseded by newer sources
5. Write report to `/wiki/synthesis/lint-report.md`

## Naming Conventions

### File Names

- **Summaries**: `{source}-{id}.md` (e.g., `twitter-1234567890.md`)
- **Entities**: `{Name}.md` (e.g., `Apollo Global.md`, `Naval Ravikant.md`)
- **Concepts**: `{Topic Name}.md` (e.g., `Private Credit.md`, `AI.md`)
- **Synthesis**: `{Pattern}.md` (e.g., `Apollo Global in Private Credit.md`)

### Bi-Temporal References

All references must track BOTH:
- **When said**: Date of original content (tweet/reel date)
- **When learned**: Date ingested into vault

Format:
```markdown
- [[twitter-12345]] (Apr 14, 2025) - "Apollo expanding..."
  - Ingested: 2025-04-14
  - Context: Q1 earnings call
```

## Frontmatter Templates

### Summary Page (Source)

```yaml
---
title: "Tweet Title or First 50 chars"
type: summary
source: twitter | instagram
source_id: "1234567890"
author: "@username"
date: "2025-04-14"          # Original content date
ingested: "2025-04-14"      # When added to vault
tags: [tag1, tag2]
relevance: 8                 # 1-10 score
entities: ["Entity 1", "Entity 2"]
concepts: ["Concept 1", "Concept 2"]
---
```

### Entity Page (Person/Company/Tool)

```yaml
---
title: "Entity Name"
type: entity
entity_type: person | company | book | tool
created: "2025-04-14"
updated: "2025-04-14"
tags: [entity]
---
```

### Concept Page (Topic)

```yaml
---
title: "Concept Name"
type: concept
created: "2025-04-14"
updated: "2025-04-14"
tags: [concept]
related_concepts: ["Related 1", "Related 2"]
---
```

### Synthesis Page (Pattern Analysis)

```yaml
---
title: "Pattern Being Analyzed"
type: synthesis
created: "2025-04-14"
updated: "2025-04-14"
sources_count: 5
entities: ["Entity 1"]
concepts: ["Concept 1"]
tags: [synthesis]
---
```

## Content Rules

### SKIP (Don't Store)

- Basketball / NBA content
- Poker game content (not strategy)
- Jokes / Memes / Engagement bait
- Content with no substance

### KEEP & ANALYZE

| Content Type | Action |
|-------------|--------|
| Finance, economics, companies | High relevance |
| Book recommendations | Save with "should I read it?" analysis |
| Blog/website links | Save to reading list, fetch if external |
| Long videos | Check title, keep link if relevant |
| Poker strategy (math/business) | Keep |
| Inspirational quotes | Keep only exceptional ones |

## Backlink Strategy

### Automatic Link Creation

When processing content:

1. **Extract entities** mentioned → Create/update entity pages
2. **Extract concepts** mentioned → Create/update concept pages
3. **In summary page**: Link to all entities and concepts
   ```markdown
   ## Entities
   [[Apollo Global]] [[Blackstone]]
   
   ## Concepts
   [[Private Credit]] [[Direct Lending]]
   ```

4. **In entity page**: Link back to all sources mentioning it
   ```markdown
   ## References
   - [[twitter-12345]] (Apr 14, 2025) - Context...
   - [[twitter-67890]] (Mar 12, 2025) - Context...
   ```

5. **In concept page**: Link to all sources and related concepts
   ```markdown
   ## Sources
   - [[twitter-12345]]: Apollo expanding...
   
   ## Related Concepts
   [[Alternative Lending]] [[Credit Markets]]
   ```

### Bidirectional Links

Obsidian automatically creates backlinks. If `[[Apollo Global]]` appears in a summary, the Apollo Global entity page will show that summary as a backlink.

## Synthesis Generation

### When to Create

Create a synthesis page when:
- 3+ sources mention the same entity AND concept
- Pattern emerges across multiple time periods
- Contradicting claims need reconciliation

### Synthesis Structure

```markdown
# Synthesis: {Entity} in {Context}

## Key Insight
One-paragraph synthesis of the pattern.

## Timeline
Chronological list of mentions with context.

## Claims Analysis
| Claim | Sources | Status |
|-------|---------|--------|
| Claim 1 | 3 sources | Consistent |
| Claim 2 | 2 sources | Contradictory |

## Related
- Entities: [[Entity 1]] [[Entity 2]]
- Concepts: [[Concept 1]] [[Concept 2]]
```

## Index Format

The index.md is updated on every ingest:

```markdown
## Summaries
| Source | Title | Date | Tags |
|--------|-------|------|------|
| twitter | [[twitter-12345]] | 2025-04-14 | finance, ai |

## Entities
| Name | Type | Mentions |
|------|------|----------|
| [[Apollo Global]] | company | 5 |

## Concepts
| Topic | Sources | Last Updated |
|-------|---------|--------------|
| [[Private Credit]] | 8 | 2025-04-14 |

## Synthesis
| Pattern | Sources | Last Updated |
|---------|---------|--------------|
| [[Apollo in Private Credit]] | 5 | 2025-04-14 |
```

## Log Format

Append-only with consistent prefix:

```markdown
## [2025-04-14 14:30] ingest | twitter-12345: Apollo expanding private credit
- Entities: Apollo Global, Blackstone
- Concepts: Private Credit
- Relevance: 9/10

## [2025-04-14 14:35] ingest | twitter-67890: New AI tool released
- Entities: OpenAI
- Concepts: AI, Productivity
- Relevance: 8/10
```

## Graph View Optimization

For best Obsidian graph visualization:

1. Use consistent `type:` in frontmatter (summary, entity, concept, synthesis)
2. Use `[[Page Name]]` format (spaces allowed)
3. Tag pages appropriately
4. Keep entity/concept pages as hub nodes (many connections)
5. Avoid orphan pages (always link to/from something)

## Tools Integration

### Obsidian Plugins Recommended

- **Dataview**: Query frontmatter for dynamic tables
- **Graph View**: Visualize connections
- **Templater**: Template automation (optional)

### CLI Commands

```bash
# Ingest latest tweets
python backend/cli.py fetch-twitter --limit 10
python backend/cli.py wiki-ingest

# Weekly lint
python backend/cli.py wiki-lint
```

## Version History

- 2025-04-14: Initial schema creation
