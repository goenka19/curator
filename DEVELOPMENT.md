# Development Workflow

## Daily Development Cycle

### 1. Before Starting Work
```bash
# Activate virtual environment
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate

# Pull latest code
git pull

# Check current state
python cli.py stats
```

### 2. Making Changes

**ALWAYS follow this order:**

1. **Read** existing files first
   ```bash
   # If modifying models.py:
   cat backend/models.py
   # If modifying database.py:
   cat backend/database.py
   ```

2. **Make changes** incrementally
   - One feature at a time
   - Keep functions under 50 lines
   - Add type hints
   - Handle errors

3. **Test immediately**
   ```bash
   # Run tests
   pytest backend/tests/ -v

   # Test specific component
   python -c "from backend.extractors.twitter_extractor import TwitterExtractor; print('✅ Import works')"
   ```

4. **Verify cost tracking**
   ```bash
   python backend/cli.py stats
   # Check that costs are logged correctly
   ```

5. **Commit**
   ```bash
   git add [specific files]
   git commit -m "feat: [what you built] - TESTED"
   ```

### 3. Testing Checklist

Before committing, verify:

- [ ] All tests pass: `pytest backend/tests/`
- [ ] No hardcoded secrets
- [ ] Type hints added to new functions
- [ ] Error handling in place
- [ ] Costs logged for API calls
- [ ] DEV_MODE respected
- [ ] No duplicates created in database

### 4. Cost Verification

After every API call:
```bash
# Check costs
python backend/cli.py stats

# Expected output should show:
# - Accurate cost per API
# - Correct item counts
# - No unexpected charges
```

## Component Development Order

**Follow this sequence:**

1. **Database Models** (`models.py`)
   - Define schema
   - Test with: `python -c "from backend.models import Base; print('✅')"`

2. **Database Operations** (`database.py`)
   - CRUD operations
   - Test with: `python -c "from backend.database import init_db; init_db()"`

3. **Config** (`config.py`)
   - Load environment variables
   - Test with: `python -c "from backend.config import *; print('✅')"`

4. **Extractors** (`extractors/`)
   - Twitter first, then Instagram
   - Test each with: `python backend/cli.py sync-twitter --limit 5`

5. **Pre-Filter** (`pre_filter.py`)
   - Rule-based filtering
   - Test with: `python backend/cli.py run-prefilter`

6. **AI Processor** (`ai_processor.py`)
   - LLM integration
   - Test with: `python backend/cli.py process-ai --limit 3`

7. **CLI** (`cli.py`)
   - Command interface
   - Test each command manually

8. **API** (`api.py`)
   - FastAPI endpoints
   - Test with: `curl http://localhost:8000/items`

9. **Frontend**
   - After backend is complete and tested

## Common Commands

```bash
# Database
python -c "from backend.database import init_db; init_db()"
sqlite3 curator.db ".schema"
sqlite3 curator.db "SELECT COUNT(*) FROM content_items"

# Extractors
python backend/cli.py sync-twitter --limit 10
python backend/cli.py sync-instagram --limit 10

# Processing
python backend/cli.py run-prefilter
python backend/cli.py process-ai --limit 5

# Stats
python backend/cli.py stats

# Full pipeline
python backend/cli.py daily-sync

# Testing
pytest backend/tests/ -v
pytest backend/tests/test_pre_filter.py -v

# Development server
cd backend && uvicorn api:app --reload --port 8000
cd frontend && npm run dev
```

## Debugging

### Database Issues
```bash
# Check schema
sqlite3 curator.db ".schema content_items"

# Check for duplicates
sqlite3 curator.db "SELECT source_id, COUNT(*) FROM content_items GROUP BY source_id HAVING COUNT(*) > 1"

# Check costs
sqlite3 curator.db "SELECT * FROM api_cost_logs ORDER BY timestamp DESC LIMIT 10"
```

### API Issues
```bash
# Test Twitter API
curl "https://api.twitter.com/2/users/me" -H "Authorization: Bearer $TWITTER_BEARER_TOKEN"

# Test Instagram API
curl "https://graph.instagram.com/me/accounts?access_token=$INSTAGRAM_ACCESS_TOKEN"
```

### Cost Issues
```bash
# Check if DEV_MODE is on
echo $DEV_MODE  # Should be 'true' during development

# Review cost logs
sqlite3 curator.db "SELECT api_name, SUM(cost_usd), COUNT(*) FROM api_cost_logs GROUP BY api_name"
```

## Emergency Procedures

### Cost Overrun
```bash
# Immediately stop all automation
# Set MAX_DEV_ITEMS=0 in .env
echo "MAX_DEV_ITEMS=0" >> .env

# Check what happened
python backend/cli.py stats
sqlite3 curator.db "SELECT * FROM api_cost_logs ORDER BY cost_usd DESC LIMIT 20"
```

### Database Corruption
```bash
# Backup database
cp curator.db curator.db.backup

# Check integrity
sqlite3 curator.db "PRAGMA integrity_check"

# If corrupted, restore from backup
# (Implement backup strategy in Phase 7)
```

### API Ban/Rate Limit
```bash
# Wait for rate limit to reset
# For Twitter: 15-minute windows
# For Instagram: 1-hour windows

# Check rate limit status in API response headers
# Implement exponential backoff in code
```
