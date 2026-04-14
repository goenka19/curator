# Content Curator - Project Documentation

## Architecture

**Backend:** Python FastAPI + SQLAlchemy + SQLite
**Frontend:** Next.js 14 + Tailwind CSS + Shadcn/ui
**AI:** Llama 3.3 70B via OpenRouter or Groq
**Data Sources:** Twitter/X Bookmarks + Instagram DMs

## System Flow

```
Data Collection → Pre-Filter (60-70% reduction) → AI Processing → SQLite → Web Dashboard
```

1. **Data Collection**: Fetch from Twitter/X and Instagram APIs
2. **Pre-Filter**: Rule-based filtering to reduce AI costs
3. **AI Processing**: Categorize and extract insights (only on pre-filtered items)
4. **Storage**: SQLite database with unified schema
5. **Dashboard**: Next.js web interface for browsing and search

## Critical Rules for Development

### ❌ NEVER / ✅ ALWAYS Format

#### Database Operations
- ❌ NEVER modify `models.py` or `database.py` without reading them first
- ❌ NEVER run raw SQL queries (use SQLAlchemy ORM only)
- ❌ NEVER delete data without user confirmation
- ✅ ALWAYS use SQLAlchemy ORM for all database operations
- ✅ ALWAYS handle unique constraint violations (duplicates)
- ✅ ALWAYS use transactions for multi-step operations
- ✅ ALWAYS check if item exists before creating (deduplication)

#### API Integration
- ❌ NEVER hardcode API keys (use .env file only)
- ❌ NEVER make API calls without checking DEV_MODE first
- ❌ NEVER skip deduplication before fetching data
- ❌ NEVER ignore rate limits
- ✅ ALWAYS check DEV_MODE before making API calls
- ✅ ALWAYS track costs for each API call in database
- ✅ ALWAYS handle rate limits with exponential backoff
- ✅ ALWAYS deduplicate before fetching (check source_id exists)
- ✅ ALWAYS log API errors with full context

#### Cost Management
- ❌ NEVER process items that failed pre-filter (wastes money)
- ❌ NEVER batch more than 10 items in AI processing
- ❌ NEVER call Twitter API without deduplication first
- ❌ NEVER skip cost logging
- ✅ ALWAYS log costs to api_cost_logs table
- ✅ ALWAYS check budget limits before processing
- ✅ ALWAYS respect DEV_MODE limits (max 10 items)
- ✅ ALWAYS run pre-filter before AI processing

#### Code Quality
- ❌ NEVER commit code without tests
- ❌ NEVER use print() for logging (use logging module)
- ❌ NEVER ignore type hints
- ✅ ALWAYS use type hints in Python functions
- ✅ ALWAYS handle exceptions with try/except
- ✅ ALWAYS log errors with context (not just error message)
- ✅ ALWAYS keep functions under 50 lines
- ✅ AVOID premature optimization

#### Security
- ❌ NEVER commit .env file to git
- ❌ NEVER log API keys or tokens (even in debug mode)
- ❌ NEVER expose credentials in error messages
- ✅ ALWAYS use environment variables for secrets
- ✅ ALWAYS add .env to .gitignore
- ✅ ALWAYS validate user input at API boundaries

## File Structure

```
curator/
├── backend/
│   ├── __init__.py
│   ├── config.py              # Load .env, configuration constants
│   ├── models.py              # SQLAlchemy models - READ FIRST BEFORE MODIFYING
│   ├── database.py            # DB operations - READ FIRST BEFORE MODIFYING
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base_extractor.py  # Shared extraction logic
│   │   ├── twitter_extractor.py  # X API integration
│   │   └── instagram_extractor.py  # Instagram API integration
│   ├── pre_filter.py          # Rule-based filtering
│   ├── ai_processor.py        # AI classification with LLM
│   ├── prompts.py             # LLM prompt templates
│   ├── api.py                 # FastAPI server and endpoints
│   ├── scheduler.py           # Automated daily sync
│   ├── monitor.py             # Cost tracking and alerts
│   ├── cli.py                 # Manual CLI commands
│   ├── requirements.txt       # Python dependencies
│   └── tests/
│       ├── __init__.py
│       ├── test_pre_filter.py
│       ├── test_ai_processor.py
│       └── test_extractors.py
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx       # Main dashboard page
│   │   │   ├── layout.tsx     # App layout
│   │   │   └── api/
│   │   │       └── items/route.ts  # API routes
│   │   ├── components/
│   │   │   ├── ContentCard.tsx     # Display single item
│   │   │   ├── CategoryTabs.tsx    # 7 category tabs
│   │   │   ├── SourceFilter.tsx    # Twitter/Instagram/All
│   │   │   ├── SearchBar.tsx       # Full-text search
│   │   │   └── StatsPanel.tsx      # Cost dashboard
│   │   └── lib/
│   │       └── api.ts          # Frontend API client
│   └── package.json
├── docs/                       # Additional documentation
├── scripts/                    # Utility scripts
├── logs/                       # Application logs
├── claude.md                   # Claude Code instructions - READ FIRST
├── PROJECT.md                  # This file - Architecture details
├── CONSTRAINTS.md              # Hard constraints - NEVER VIOLATE
├── DEVELOPMENT.md              # Development workflow
├── README.md                   # Project overview
├── .env.example                # Environment variables template
├── .env                        # Actual secrets (NEVER COMMIT)
├── .gitignore                  # Git exclusions
└── .claudeignore               # Files Claude should never modify
```

## Testing Requirements

### Before ANY Commit

You MUST run all of these and they MUST pass:

1. **Run tests**: `pytest backend/tests/ -v`
2. **Check cost tracking**: `python backend/cli.py stats`
3. **Verify database integrity**:
   ```bash
   sqlite3 curator.db "PRAGMA integrity_check"
   sqlite3 curator.db "SELECT COUNT(*) FROM content_items"
   ```
4. **Check for duplicates**:
   ```bash
   sqlite3 curator.db "SELECT source_id, COUNT(*) FROM content_items GROUP BY source_id HAVING COUNT(*) > 1"
   ```
5. **Verify DEV_MODE**: `echo $DEV_MODE` (should be 'true' in development)

### Before Production Deployment

1. All dev tests pass
2. Manual verification of 20 AI categorizations (accuracy check)
3. Cost projection is under budget ($5/month)
4. Deduplication verified (run sync twice, count should not increase)
5. Rate limiting tested and working
6. Error handling verified (simulate API failures)

## Cost Constraints (CRITICAL)

### Budget Limits
- **Daily maximum**: $0.50 USD
- **Monthly maximum**: $5.00 USD
- **Per-batch maximum**: 50 items

### Cost Tracking
- Every API call MUST be logged to `api_cost_logs` table
- Dashboard must display real-time cost tracking
- Alerts when costs exceed 60% of limits

### Development Safety
- DEV_MODE=true limits to 10 items maximum
- All API calls check DEV_MODE first
- Costs are calculated and logged even in DEV_MODE

## Common Pitfalls to Avoid

### 🚨 High Priority (Can Cost Money)
1. Processing all items without pre-filter → Costs spiral
2. Not deduplicating before API calls → Duplicate charges
3. Ignoring rate limits → API bans
4. Running in production with DEV_MODE=false without testing
5. Not logging costs → Budget overruns unnoticed

### ⚠️ Medium Priority (Can Break Things)
1. Modifying database models without migration
2. No error handling → Crashes on API errors
3. Hardcoded test data in production code
4. Committing .env file with real credentials
5. Ignoring type hints → Runtime errors

### ℹ️ Low Priority (Code Quality)
1. Functions over 50 lines → Hard to maintain
2. No docstrings on complex functions
3. Using print() instead of logging
4. Not handling edge cases

## Development Workflow

1. **Read**: Always read existing code before modifying
2. **Plan**: Understand what you're changing and why
3. **Implement**: Make changes incrementally
4. **Test**: Test immediately after each change
5. **Verify**: Run full test suite
6. **Commit**: Commit with descriptive message

## Emergency Procedures

### If Costs Spike
```bash
# Immediately set DEV_MODE
echo "DEV_MODE=true" >> .env
echo "MAX_DEV_ITEMS=0" >> .env

# Check what happened
python backend/cli.py stats
sqlite3 curator.db "SELECT * FROM api_cost_logs ORDER BY cost_usd DESC LIMIT 20"
```

### If Database Corrupts
```bash
# Check integrity
sqlite3 curator.db "PRAGMA integrity_check"

# Restore from backup (must set up backups first)
cp backups/curator.db.latest curator.db
```

### If API Gets Banned
```bash
# Check rate limits in API response
# Wait for reset period (15 min for Twitter, 1 hour for Instagram)
# Implement exponential backoff
# Contact API support if needed
```

## Questions? Issues?

1. Check CONSTRAINTS.md for hard limits
2. Check DEVELOPMENT.md for workflows
3. Check existing code in similar files
4. Ask user for clarification

**Remember: It's better to ask than to make a costly mistake!**
