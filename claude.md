# Content Curator - Claude Code Instructions

**READ THIS FILE FIRST BEFORE DOING ANYTHING**

This file contains critical instructions for Claude Code. You MUST read and follow these instructions for EVERY operation in this project.

## Project Type: AI-Powered Content Curation System

**Budget:** $5/month maximum | **Current monthly cost:** $0.25-0.30 expected

**WARNING: API calls cost money. Always check DEV_MODE before making API calls.**

---

## CRITICAL RULES - NEVER VIOLATE

### 0. NEVER GUESS - ALWAYS BE CERTAIN (HIGHEST PRIORITY)

**Before telling the user ANYTHING:**
- ❌ **NEVER guess** or assume information
- ❌ **NEVER make up** URLs, API endpoints, or documentation links
- ❌ **NEVER state something as fact** unless you have verified it with:
  - Official documentation (via WebFetch/WebSearch)
  - Reading actual code files
  - Testing with real API calls
  - Clear sources that you can cite

**ALWAYS:**
- ✅ **Search official documentation** before answering technical questions
- ✅ **Read files** before claiming what they contain
- ✅ **Test assumptions** before presenting them as solutions
- ✅ **Cite sources** with actual URLs when providing information
- ✅ **Ask for clarification** if requirements are unclear
- ✅ **Admit uncertainty** - say "I don't know, let me check" instead of guessing

**Example - WRONG:**
```
"Twitter API uses OAuth 1.0a for bookmarks. Just generate the tokens from the portal."
(This was a GUESS - turned out to be wrong, wasted user's time)
```

**Example - CORRECT:**
```
"Let me search the official X API documentation to verify the authentication method for bookmarks..."
*Uses WebSearch to find official docs*
"According to the official documentation, bookmarks require OAuth 2.0 User Context.
Source: https://docs.x.com/x-api/posts/bookmarks/introduction"
```

**If you're not 100% certain:**
1. Search official documentation (WebSearch/WebFetch)
2. Read relevant code files
3. Ask the user for clarification
4. Test your hypothesis before presenting it
5. **NEVER present guesses as facts**

**This rule overrides everything else. A delayed but accurate answer is infinitely better than a fast but wrong answer that costs the user time and money.**

---

### 1. Cost Protection (ABSOLUTE PRIORITY)

**Before EVERY API call:**
```python
if DEV_MODE:  # Check this FIRST
    limit = min(limit, MAX_DEV_ITEMS)  # Hard limit: 10 items

# Calculate cost BEFORE calling API
projected_cost = calculate_cost(items)
if projected_cost > MAX_DAILY_COST_USD:
    STOP and alert user
```

**Cost Limits:**
- Daily maximum: $0.50 USD
- Monthly maximum: $5.00 USD
- DEV_MODE maximum: 10 items (cannot override)

**ALWAYS log costs:**
```python
log_api_cost(db, api_name='twitter', operation='fetch_bookmarks',
             items_count=len(items), cost_usd=cost)
```

### 2. Deduplication (Prevent Duplicate Charges)

**Before EVERY data fetch:**
```python
# ❌ WRONG - might fetch duplicates and waste money
items = twitter_extractor.fetch_bookmarks(limit=100)

# ✅ CORRECT - check existence first
if not item_exists(db, f"twitter_{tweet_id}"):
    # Only then fetch
```

**Why:** Twitter API charges $0.005 per tweet. Fetching duplicates = paying twice.

### 3. Pre-Filter Before AI (60-70% Cost Reduction)

**ALWAYS run pre-filter before AI processing:**
```python
# ❌ WRONG - processes everything, expensive
processor.process_batch(db, all_items)

# ✅ CORRECT - filter first, then process
pre_filter.process_batch(db, all_items)
items_to_process = db.query(ContentItem).filter(
    ContentItem.pre_filter_passed == True,
    ContentItem.ai_processed == False
).all()
processor.process_batch(db, items_to_process)
```

**Why:** Pre-filter reduces items by 60-70%, saving $0.07/month or more.

### 4. Read Before Modify

**Before modifying ANY file:**
```python
# ✅ REQUIRED - read first
with open('backend/models.py') as f:
    current_content = f.read()
    # Now understand what's there before changing it
```

**Critical files to ALWAYS read first:**
- `backend/models.py` - Database schema
- `backend/database.py` - Database operations
- `backend/config.py` - Configuration
- Any file you plan to modify

### 5. Testing Before Commits

**Before EVERY commit, run ALL of these:**
```bash
# 1. Run tests
pytest backend/tests/ -v

# 2. Check costs
python backend/cli.py stats

# 3. Verify no duplicates
sqlite3 curator.db "SELECT source_id, COUNT(*) FROM content_items GROUP BY source_id HAVING COUNT(*) > 1"

# 4. Check DEV_MODE
echo $DEV_MODE  # Should be 'true' in development
```

**If any fail: DO NOT COMMIT. Fix first.**

---

## Architecture Quick Reference

```
┌─────────────┐
│  Twitter/X  │  ($0.005/tweet)
│  Instagram  │  (FREE)
└──────┬──────┘
       │ Fetch with deduplication
       ▼
┌─────────────┐
│ Pre-Filter  │  (60-70% reduction, FREE)
│ Rules-based │
└──────┬──────┘
       │ Only ~30-40% pass
       ▼
┌─────────────┐
│ AI Process  │  ($0.88/1M tokens)
│ Llama 3.3   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   SQLite    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Next.js    │
│  Dashboard  │
└─────────────┘
```

---

## File Structure & Purposes

```
backend/
├── config.py              # Environment variables, constants
├── models.py             # Database schema - READ FIRST BEFORE MODIFYING
├── database.py           # Database ops - READ FIRST BEFORE MODIFYING
├── extractors/
│   ├── twitter_extractor.py   # Twitter API ($0.005/tweet)
│   └── instagram_extractor.py # Instagram API (FREE)
├── pre_filter.py         # Rule-based filtering (saves 60-70% cost)
├── ai_processor.py       # AI categorization (costs money)
├── prompts.py            # LLM prompts
├── api.py                # FastAPI server
├── cli.py                # Command-line interface
└── tests/                # Tests - MUST pass before commit

frontend/
└── src/
    ├── app/              # Next.js pages
    └── components/       # React components

docs/
├── claude.md            # THIS FILE - READ FIRST ALWAYS
├── PROJECT.md           # Detailed architecture
├── CONSTRAINTS.md       # Hard limits
└── DEVELOPMENT.md       # Workflows
```

---

## Common Operations & How to Do Them Safely

### Fetching Twitter Bookmarks

```python
# ✅ CORRECT way
from backend.database import SessionLocal
from backend.extractors.twitter_extractor import TwitterExtractor
from backend.config import DEV_MODE, MAX_DEV_ITEMS

db = SessionLocal()

# 1. Check DEV_MODE
limit = 100
if DEV_MODE:
    limit = MAX_DEV_ITEMS  # Hard limit: 10

# 2. Create extractor
extractor = TwitterExtractor()

# 3. Fetch (already includes deduplication inside)
items = extractor.fetch_bookmarks(db, limit=limit)

# 4. Save
for item in items:
    db.add(item)
db.commit()

# 5. Verify cost was logged
# Check api_cost_logs table

db.close()
```

### Running Pre-Filter

```python
# ✅ CORRECT way
from backend.pre_filter import PreFilter
from backend.models import ContentItem

db = SessionLocal()

# Get unfiltered items
items = db.query(ContentItem).filter(
    ContentItem.pre_filter_passed == False,
    ContentItem.pre_filter_reason == None
).all()

# Run filter (FREE - no API costs)
filter = PreFilter()
passed, filtered = filter.process_batch(db, items)

print(f"Passed: {passed}, Filtered: {filtered} ({filtered/(passed+filtered)*100:.1f}% reduction)")

db.close()
```

### Processing with AI

```python
# ✅ CORRECT way
from backend.ai_processor import AIProcessor

db = SessionLocal()

# Get items that passed pre-filter (NOT all items!)
items = db.query(ContentItem).filter(
    ContentItem.pre_filter_passed == True,  # REQUIRED
    ContentItem.ai_processed == False
).limit(10).all()  # Limit to 10 per batch

if not items:
    print("No items to process")
else:
    processor = AIProcessor()
    stats = processor.process_batch(db, items)
    print(f"Processed: {stats['processed']}, Cost: ${stats['cost_usd']:.4f}")

db.close()
```

---

## Before Making Changes

Ask yourself:

1. **Have I read claude.md?** (this file)
2. **Have I read the files I'm about to modify?**
3. **Am I in DEV_MODE?** (check: `echo $DEV_MODE`)
4. **Will this cost money?** (API calls or AI processing)
5. **Am I deduplicating?** (checking for existing items)
6. **Am I logging costs?** (using log_api_cost())
7. **Am I running pre-filter before AI?** (saves money)
8. **Do I have tests?** (required before commit)

**If you answered "no" to any of these, STOP and fix it first.**

---

## Cost Tracking - Check After Every Operation

```bash
# Check current costs
python backend/cli.py stats

# Expected output:
# Total Items:          X
# Pre-filtered (pass):  Y (30-40%)
# AI Processed:         Z
#
# Cost Breakdown:
# twitter:        $0.XX
# instagram:      $0.00
# openrouter:     $0.XX
# TOTAL:          $0.XX
```

**If costs look wrong, STOP and investigate before continuing.**

---

## Development Workflow

```bash
# 1. Activate environment
cd backend
source venv/bin/activate

# 2. Make changes (after reading existing files!)

# 3. Test immediately
pytest backend/tests/ -v

# 4. Check costs
python backend/cli.py stats

# 5. Commit
git add [specific files]
git commit -m "feat: description - TESTED"
```

---

## Emergency: If Costs Spike

```bash
# 1. STOP everything immediately
# 2. Set DEV_MODE to prevent further charges
echo "DEV_MODE=true" >> .env
echo "MAX_DEV_ITEMS=0" >> .env

# 3. Check what happened
python backend/cli.py stats
sqlite3 curator.db "SELECT * FROM api_cost_logs ORDER BY cost_usd DESC LIMIT 20"

# 4. Alert user
# 5. Wait for explicit approval before continuing
```

---

## What Makes This Project Special

1. **Cost-optimized**: Pre-filter saves 60-70% on AI costs
2. **Multi-source**: Twitter + Instagram in one system
3. **Smart deduplication**: Never pay for same data twice
4. **Real-time cost tracking**: Know exactly what you're spending
5. **Budget protection**: Hard limits prevent overruns

---

## Files You Should NEVER Modify Without Reading First

Listed in `.claudeignore`:
- `.env` - Contains secrets
- `curator.db` - Database file
- `models.py` - Must read before changing schema
- `database.py` - Must understand before modifying
- `CONSTRAINTS.md` - Hard rules
- Any file in `backups/` or `data/production/`

---

## Summary: The Golden Rules

1. **Always check DEV_MODE** before API calls
2. **Always deduplicate** before fetching data
3. **Always pre-filter** before AI processing
4. **Always log costs** for every API call
5. **Always read files** before modifying them
6. **Always test** before committing
7. **Never violate** cost limits
8. **Never skip** deduplication
9. **Never process** items that failed pre-filter
10. **Never commit** without running tests

---

## Questions or Unclear?

1. Check `PROJECT.md` for detailed architecture
2. Check `CONSTRAINTS.md` for hard limits
3. Check `DEVELOPMENT.md` for workflows
4. **Ask the user** - better to ask than make a costly mistake

---

**This file (claude.md) must be read at the start of EVERY Claude Code session.**

**If you're unsure about anything, ASK THE USER FIRST.**

**Cost overruns are expensive mistakes - prevention is worth the extra time.**
