# Content Curator Vault - Schema and Conventions

## Purpose

This vault is a personal knowledge base for curated content from Twitter/X, Instagram, and Books. It uses the LLM Wiki pattern to create a persistent, compounding knowledge graph where insights accumulate and connect over time.

## Architecture (Updated 2026-04-15)

```
curator_vault/
├── CLAUDE.md              # This file - schema and conventions
├── index.md               # Master catalog (updated on every ingest)
├── hot.md                 # Recent context cache (session persistence)
├── log.md                 # Chronological activity log
├── raw-sources/           # IMMUTABLE source material
│   ├── twitter/          # Raw tweet exports (minimal)
│   └── instagram/        # Raw Instagram exports (minimal)
├── wiki/                  # LLM-generated knowledge base
│   ├── books/            # Book pages with ALL highlights (readable)
│   ├── entities/         # People, companies (linked to books)
│   ├── concepts/         # Topics, frameworks, ideas (connect books)
│   └── highlights/       # EMPTY - removed (too noisy)
├── skills/               # claude-obsidian plugin skills
├── commands/             # claude-obsidian plugin commands
└── agents/               # claude-obsidian plugin agents
```

## Key Design Decisions

### Book-First Architecture

**REMOVED:** 700+ individual highlight pages (too noisy, unmaintainable)

**KEPT:** 12 book pages with ALL highlights readable in one place

**ADDED:** Shared entity/concept pages that connect multiple books

This creates a cleaner graph:
- Books → contain highlights (readable)
- Entities/Concepts → link to multiple books (connections)
- No orphan pages
- Dense linking between related ideas

## Operations

### Book Import Workflow

1. Parse CSV exports (books + highlights)
2. Create book pages with full highlights readable
3. Extract recurring entities and concepts
4. Create shared entity/concept pages ONLY for high-value connections
5. Update index.md, hot.md, log.md
6. Books automatically link to entities/concepts via [[backlinks]]

### Twitter/Instagram Ingest Workflow

1. Fetch bookmarks via API (with deduplication)
2. Pre-filter content (skip NBA, memes, etc.)
3. AI process valuable content
4. Create summary page in wiki/summaries/
5. Update/create entity and concept pages
6. Link to existing concepts (unify with books!)
7. Update index.md, hot.md, log.md

### Query Workflow

When you ask a question:

1. Read hot.md first (recent context cache)
2. Read index.md to find relevant pages
3. Read entity/concept pages for aggregated knowledge
4. Read book pages for detailed highlights
5. Synthesize answer with [[citations]]
6. If valuable, save as new synthesis page

### Lint Workflow (Weekly)

Health check the wiki:

1. Find orphan pages (no inbound links)
2. Find dead links (broken [[references]])
3. Find concepts mentioned but lacking dedicated pages
4. Find books without entity/concept connections
5. Write report to vault root or log.md

## File Naming Conventions

### Books
- `{Book-Title}.md` - e.g., `The-Psychology-of-Money.md`
- Full title preserved for readability
- Special chars replaced with hyphens

### Entities
- `{Name}.md` - e.g., `Morgan-Housel.md`, `Nike.md`
- Person or organization
- Links to books they're mentioned in

### Concepts
- `{Topic-Name}.md` - e.g., `Risk-Management.md`, `Deep-Work.md`
- Recurring ideas across multiple sources
- Aggregates insights from all books/tweets mentioning them

## Frontmatter Templates

### Book Page
```yaml
---
type: book
author: "[[Author Name]]"
read_date: YYYY-MM-DD
total_highlights: N
source: books
---
```

### Entity Page
```yaml
---
type: entity
entity_type: person | company | book
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
---
```

### Concept Page
```yaml
---
type: concept
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
related_concepts: []
---
```

## Backlink Strategy

### Books → Entities/Concepts
Book pages mention entities/concepts using [[wikilinks]]:
```markdown
[[Morgan Housel]] discusses [[risk management]] in his book...
```

### Entities/Concepts → Books
Entity/concept pages link back to all books mentioning them:
```markdown
## References
- [[The Psychology of Money]] - 58 highlights on risk
```

### Bidirectional Links
Obsidian automatically creates backlinks, so:
- If `[[Morgan Housel]]` appears in a book, the Morgan Housel page shows that book as a backlink
- Graph view shows the connection automatically

## Content Rules

### SKIP (Don't Store)

- Basketball / NBA content
- Poker game content (not strategy)
- Jokes / Memes / Engagement bait
- Content with no substance
- Generic motivational quotes without specific insight

### KEEP & ANALYZE

| Content Type | Action |
|-------------|--------|
| Finance, economics, companies | High relevance |
| Book highlights | Import with AI extraction |
| Blog/website links | Save to reading list |
| Long videos | Check title, keep link if relevant |
| Investment strategies | Keep |
| Exceptional quotes | Keep only if truly insightful |

## Graph View Optimization

For best Obsidian graph visualization:

1. Use consistent `type:` in frontmatter (book, entity, concept)
2. Use `[[Page Name]]` format (spaces allowed)
3. Tag pages appropriately
4. Keep entity/concept pages as hub nodes (many connections)
5. Book pages should connect to multiple entities/concepts
6. Avoid orphan pages (always link to/from something)

## Cost Control (Unique to This System)

- Daily API limit: $0.50
- Monthly API limit: $5.00
- Pre-filter before AI: 60-70% cost reduction
- Deduplication: Never pay for same data twice
- DEV_MODE: Limit to 10 items in development
- Log all API costs: curator.db tracks every call

## Integration with claude-obsidian

This vault now uses claude-obsidian plugin for:
- `/wiki` - Setup and scaffolding
- `/save` - Save conversations to wiki
- `/autoresearch` - Web research loop
- `skills/wiki/` - Ingest, query, lint operations
- `commands/` - Structured command interface

Custom additions:
- `backend/` - Python backend for Twitter/Instagram/Book ingestion
- Cost tracking and budget protection
- Source-specific extractors (Twitter API, Instagram, CSV)

## Version History

- 2026-04-15: Major refactor - removed 700+ highlight pages, added claude-obsidian integration, created proper entity/concept architecture
- 2026-04-15: Initial book import (12 books, 715 highlights)
- 2026-04-14: Initial vault setup
