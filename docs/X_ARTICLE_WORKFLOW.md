# X Article Workflow

## Overview

X Articles (formerly Twitter Notes) cannot be fetched automatically due to authentication and anti-scraping measures. This workflow handles them specially.

## How It Works

### 1. Automatic Detection

When fetching Twitter bookmarks, the system automatically detects X Articles:

```python
if 'x.com/i/article' in tweet_text:
    mark_as_x_article()
    skip_ai_processing()
    create_special_wiki_page()
```

### 2. Special Wiki Page

For each X Article, the system creates a page like:

```markdown
# X Article - Requires Manual Extraction

**Source:** twitter | **Author:** @username
**Date:** 2026-04-14 | **Ingested:** 2026-04-14

## ⚠️ Manual Extraction Required

This tweet contains an X Article that cannot be fetched automatically.

**X Article URL:** https://x.com/i/article/2042189240558104576

## Action Required

1. Visit the URL above
2. Read the article
3. Copy important insights to: `raw-sources/x-articles/{tweet_id}.md`
4. Run `python backend/cli.py wiki-ingest` to process
```

### 3. Your Manual Workflow

#### Step 1: Browse Your Vault

In Obsidian, you'll see pages tagged with `x-article` and `needs-extraction`.

#### Step 2: Visit the URL

Click the X Article URL in the wiki page.

#### Step 3: Extract Content

Copy the important parts of the article and save to:
```
curator_vault/raw-sources/x-articles/{tweet_id}.md
```

Example content:
```markdown
# Article Title from X

## Key Points
- Main insight 1
- Main insight 2
- Actionable takeaway

## Full Text
[Your extracted content here]

## Source
Original URL: https://x.com/i/article/...
Extracted: 2026-04-14
```

#### Step 4: Re-process (Future Feature)

In the future, you can run:
```bash
python backend/cli.py process-x-articles
```

This will read your manual extractions and create proper wiki pages.

## Current Limitations

1. **No automatic fetching** - X blocks all scrapers
2. **Manual extraction only** - You must copy-paste
3. **No AI processing** - Yet (can be added later for your manual content)

## Why This Approach?

| Approach | Works? | Complexity | Maintenance |
|----------|--------|------------|-------------|
| **Skip X Articles** | ❌ | None | None |
| **Browser automation** | ⚠️ Maybe | High | High |
| **Manual extraction** | ✅ Yes | Low | None |

**Trade-off**: You manually extract high-value X Articles, but get perfect accuracy and zero maintenance burden.

## Future Enhancements

- [ ] Process manual X Article files with AI
- [ ] Create proper wiki pages from manual extractions
- [ ] Extract entities/concepts from your manual content
- [ ] Link manual extractions to original tweets

## File Locations

| Location | Purpose |
|----------|---------|
| `wiki/summaries/x-article-*.md` | Special pages with instructions |
| `raw-sources/x-articles/*.md` | Your manual extractions |
| Database `has_x_article` flag | Tracks which tweets have X Articles |
| Database `x_article_url` | Stores the URL for manual access |

## Commands

```bash
# Fetch bookmarks (auto-detects X Articles)
python backend/cli.py fetch-twitter --limit 10

# AI process (skips X Articles, marks for manual)
python backend/cli.py ai-process --limit 10

# Create wiki pages (creates special X Article pages)
python backend/cli.py wiki-ingest

# Future: Process your manual extractions
python backend/cli.py process-x-articles  # Coming soon
```

## Questions?

See the main README.md or CLAUDE.md for full documentation.
