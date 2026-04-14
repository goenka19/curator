# Weekly Linting & Synthesis System

## Overview

Automated weekly health checks and pattern recognition for your Obsidian wiki.

## Commands

### Weekly Lint Check

```bash
python backend/cli.py wiki-lint
```

**What it checks:**
1. **Orphan Pages** - Pages with no inbound links
2. **Knowledge Gaps** - Concepts mentioned but no dedicated page
3. **Synthesis Opportunities** - Patterns across 3+ sources
4. **Contradictions** - Conflicting claims about same entity

**Output:**
- Console summary
- Report saved to `wiki/synthesis/lint-report-YYYY-MM-DD.md`

### Generate Synthesis Pages

```bash
python backend/cli.py wiki-generate-synthesis
```

**Auto-creates:**
- Entity + Concept syntheses (3+ sources)
- Concept-only syntheses (5+ sources)
- Contradictions documentation

**Example:**
```markdown
# Andrej Karpathy on LLM Mistakes

## Timeline
| Date | Source | Key Insight |
|------|--------|-------------|
| 2026-04-12 | [[twitter-123]] | LLMs over-engineer |
| 2026-04-10 | [[instagram-456]] | LLMs ignore patterns |
| 2026-03-28 | [[twitter-789]] | LLMs add dependencies |

## Claim Analysis
✅ Consistent: Sources agree on core pattern
```

## Synthesis Triggers

| Pattern | Sources Required | Auto-Create |
|---------|-----------------|-------------|
| Entity + Concept | 3+ | Yes |
| Concept Only | 5+ | Yes |
| Contradictions | 2+ (different sentiments) | Yes |

## Raw Tweet Backup

**Location:** `curator_vault/raw-sources/twitter/{tweet_id}.md`

**Contains:**
- Tweet text
- Author and date
- External URLs (links only, not fetched)
- Reference to processed wiki version

**Example:**
```markdown
---
tweet_id: "12345"
author: "@username"
date: "2026-04-12"
url: "https://x.com/..."
---

## Tweet Text
Original tweet content...

## External Links (Not Fetched)
- https://substack.com/article...

## Note
External content NOT stored here. See wiki/summaries/ for processed version.
```

## Weekly Workflow

### Automated (Monday 9 AM)
```bash
# Add to crontab
0 9 * * 1 cd /path/to/curator && python backend/cli.py wiki-lint
0 9 * * 1 cd /path/to/curator && python backend/cli.py wiki-generate-synthesis
```

### Manual Review
1. Check `wiki/synthesis/lint-report-*.md`
2. Review generated synthesis pages
3. Resolve any flagged contradictions
4. Create missing concept pages from gaps list

## Folder Structure

```
curator_vault/
├── raw-sources/
│   ├── twitter/           # Raw tweet backups
│   ├── instagram/         # Raw reel metadata
│   └── x-articles/        # Your manual extractions
├── wiki/
│   ├── summaries/         # Processed items
│   ├── entities/          # People/companies
│   ├── concepts/          # Topics
│   └── synthesis/         # Pattern analysis
│       ├── lint-report-*.md
│       ├── {Entity} on {Concept}.md
│       ├── Understanding {Concept}.md
│       └── Contradictions *.md
```

## Features

### Orphan Detection
Finds pages with no backlinks:
- Entity pages never referenced
- Concept pages not linked
- Summary pages isolated

### Knowledge Gap Detection
Finds mentions without pages:
- Concept in frontmatter but no `concepts/{name}.md`
- Suggests new pages to create

### Pattern Recognition
Detects synthesis opportunities:
- Same entity mentioned across multiple topics
- Same concept from different sources
- Evolution of claims over time

### Contradiction Detection
Simple sentiment analysis:
- Positive vs negative mentions
- Flags for manual review
- Creates contradiction report

## Configuration

### Adjust Thresholds

Edit `backend/synthesis_generator.py`:
```python
# Entity + Concept synthesis
if len(sources) >= 3:  # Change threshold

# Concept-only synthesis
if len(sources) >= 5:  # Change threshold
```

### Custom Lint Checks

Add to `backend/wiki_linter.py`:
```python
def _custom_check(self, pages):
    # Your custom logic
    pass
```

## Future Enhancements

- [ ] Email/notification for critical contradictions
- [ ] Graph visualization of orphan pages
- [ ] AI-powered contradiction resolution suggestions
- [ ] Trend analysis (what topics are growing)
- [ ] Export lint reports to PDF

## Questions?

See main README.md or run:
```bash
python backend/cli.py --help
```
