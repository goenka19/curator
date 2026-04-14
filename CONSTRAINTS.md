# CONSTRAINTS - NEVER VIOLATE THESE

These are HARD CONSTRAINTS that must NEVER be violated under any circumstances.

## 1. Cost Constraints (ABSOLUTE LIMITS)

### Daily Cost Limits
- **Maximum daily cost**: $0.50 USD
- **Alert threshold**: $0.30 USD
- **Action if exceeded**: STOP all API calls immediately, alert user, wait for explicit approval

### Monthly Cost Limits
- **Maximum monthly cost**: $5.00 USD
- **Alert threshold**: $3.00 USD
- **Action if projected to exceed**: STOP automation, alert user, require explicit approval to continue

### Per-Operation Limits
- **Twitter API**: Maximum 100 bookmarks per sync (unless user explicitly overrides)
- **AI Processing**: Maximum 50 items per batch
- **DEV_MODE**: Hard limit of 10 items maximum (cannot be overridden)
- **Cost calculation**: MUST be done BEFORE operation, not after

### Enforcement
```python
# Before EVERY API call:
if DEV_MODE:
    limit = min(limit, MAX_DEV_ITEMS)  # 10 items max

# Before processing:
projected_cost = calculate_projected_cost(items)
if projected_cost > MAX_DAILY_COST_USD:
    raise BudgetExceededError(f"Projected cost ${projected_cost} exceeds daily limit")
```

## 2. API Usage Constraints

### Twitter/X API
- ❌ NEVER call API without checking if item exists first (prevents duplicate charges)
- ❌ NEVER fetch more than 100 items without pagination
- ❌ NEVER ignore rate limits (180 requests / 15 minutes)
- ✅ ALWAYS log costs: `cost = num_tweets * 0.005`
- ✅ ALWAYS deduplicate: check `source_id` exists before API call
- ✅ ALWAYS use pagination properly with `pagination_token`
- ✅ ALWAYS wait 1 second between requests (rate limiting)

### Instagram API
- ❌ NEVER exceed 200 DMs/hour rate limit
- ❌ NEVER call API without checking if message exists first
- ✅ ALWAYS handle rate limit errors (HTTP 429)
- ✅ ALWAYS implement exponential backoff on errors
- ✅ ALWAYS check conversation exists before fetching messages

### AI Processing (OpenRouter/Groq)
- ❌ NEVER process items that failed pre-filter (wastes money)
- ❌ NEVER batch more than 10 items at once
- ❌ NEVER skip pre-filter stage
- ❌ NEVER process items with empty content
- ✅ ALWAYS run pre-filter first
- ✅ ALWAYS check relevance score before saving (skip if < 5)
- ✅ ALWAYS validate JSON response from LLM
- ✅ ALWAYS log token usage and costs

## 3. Development Constraints

### Before Writing ANY Code
- ✅ MUST read existing files before modifying them
- ✅ MUST understand current architecture
- ✅ MUST check PROJECT.md for rules
- ✅ MUST verify you're in DEV_MODE for testing

### Before Modifying Database
- ✅ MUST read models.py completely
- ✅ MUST create migration if changing schema
- ✅ MUST backup database before schema changes
- ❌ NEVER modify database.py without reading it first
- ❌ NEVER delete data without user confirmation

### Code Quality Requirements
- ✅ MUST use type hints on all functions
- ✅ MUST add docstrings to complex functions
- ✅ MUST handle errors with try/except
- ✅ MUST keep functions under 50 lines
- ✅ MUST use logging module (not print)
- ❌ NEVER ignore linter warnings without good reason
- ❌ NEVER commit code with TODO comments (fix or remove)

### Before ANY Commit
- ✅ MUST run: `pytest backend/tests/ -v` (all tests pass)
- ✅ MUST run: `python backend/cli.py stats` (verify costs)
- ✅ MUST check: No duplicate `source_id` in database
- ✅ MUST verify: DEV_MODE setting is correct
- ✅ MUST verify: No hardcoded API keys in code
- ❌ NEVER commit .env file
- ❌ NEVER commit database files (*.db, *.sqlite)

## 4. Security Constraints

### Secrets Management
- ❌ NEVER commit .env file to git
- ❌ NEVER log API keys or tokens (even in debug mode)
- ❌ NEVER expose credentials in error messages
- ❌ NEVER store credentials in code
- ❌ NEVER pass credentials in URL parameters
- ✅ ALWAYS use environment variables via python-dotenv
- ✅ ALWAYS add .env to .gitignore
- ✅ ALWAYS use .env.example as template (no real values)

### API Key Protection
```python
# ❌ WRONG - exposes key
logger.error(f"API error with key {TWITTER_BEARER_TOKEN}")

# ✅ CORRECT - masks key
logger.error(f"API error with key {TWITTER_BEARER_TOKEN[:8]}...")
```

### Data Protection
- ✅ MUST backup database before major operations
- ✅ MUST validate all user input
- ✅ MUST sanitize data before displaying in UI
- ❌ NEVER trust user input
- ❌ NEVER expose internal IDs in public URLs

## 5. Testing Constraints

### Development Testing
- ✅ MUST test with DEV_MODE=true first
- ✅ MUST verify with max 10 items before scaling
- ✅ MUST manually check first 20 AI categorizations
- ✅ MUST verify deduplication works (run sync twice, count should stay same)
- ✅ MUST verify cost calculations are accurate

### Before Production
- ✅ MUST test full pipeline end-to-end
- ✅ MUST verify all API credentials work
- ✅ MUST test error handling (simulate API failures)
- ✅ MUST verify rate limiting works
- ✅ MUST confirm costs are under budget
- ✅ MUST test on small dataset first (10-20 items)

### Continuous Testing
```bash
# Run after every change:
pytest backend/tests/ -v

# Run before every commit:
python backend/cli.py stats
```

## 6. Data Quality Constraints

### Pre-Filter Rules (Immutable)
- **Minimum content length**: 50 characters (cannot be less)
- **Must have**: URL OR media OR valuable keywords
- **Skip patterns**: Spam phrases (hardcoded list)
- **Skip simple retweets**: < 150 characters

### AI Processing Rules
- ✅ ONLY process items that passed pre-filter
- ✅ SKIP items with relevance_score < 5
- ✅ VALIDATE JSON response structure
- ✅ HANDLE LLM errors gracefully (don't crash batch)
- ❌ NEVER save items without key_insight
- ❌ NEVER save items without category

### Database Integrity
- ✅ UNIQUE constraint on source_id (enforced)
- ✅ NOT NULL on required fields
- ✅ Validate data types before insert
- ✅ Use transactions for multi-step operations

## 7. Performance Constraints

### Rate Limiting
```python
# Twitter: Max 180 requests / 15 minutes
# Implement: 1 second between requests

import time
time.sleep(1)  # REQUIRED between API calls
```

### Batch Processing
- **Maximum batch size**: 10 items (AI processing)
- **Delay between batches**: 1 second minimum
- **Timeout per item**: 30 seconds maximum

### Database Queries
- ✅ ALWAYS use indexes on frequently queried columns
- ✅ ALWAYS limit results (use LIMIT clause)
- ✅ ALWAYS paginate large result sets
- ❌ NEVER load entire table into memory
- ❌ NEVER run queries without WHERE clause on large tables

## 8. Violation Response Protocol

If ANY constraint is violated:

1. **STOP immediately** - Do not continue execution
2. **Rollback** - Undo any uncommitted changes
3. **Log violation** - Record what happened and why
4. **Alert user** - Notify with clear error message
5. **Wait** - Do not proceed without explicit user approval

### Example Response
```python
class ConstraintViolationError(Exception):
    """Raised when a hard constraint is violated."""
    pass

def check_daily_budget(cost: float):
    if cost > MAX_DAILY_COST_USD:
        logger.error(f"CONSTRAINT VIOLATION: Daily cost ${cost} exceeds ${MAX_DAILY_COST_USD}")
        raise ConstraintViolationError(
            f"Daily budget exceeded: ${cost} > ${MAX_DAILY_COST_USD}. "
            "Operation aborted. Please review costs and approve before continuing."
        )
```

## 9. Why These Constraints Exist

| Constraint | Reason | Impact if Violated |
|------------|--------|-------------------|
| Cost limits | Prevent budget overruns | Could spend $100+ instead of $5 |
| Deduplication | Prevent duplicate charges | Pay twice for same data |
| Pre-filter | Reduce AI costs 60-70% | Costs increase 3x |
| Rate limits | Prevent API bans | Lose API access |
| Testing | Catch bugs before production | Data corruption, crashes |
| Security | Protect credentials | API keys stolen, account compromise |

## 10. Constraint Checklist

Before making ANY changes, ask yourself:

- [ ] Have I read PROJECT.md?
- [ ] Have I read the files I'm about to modify?
- [ ] Am I in DEV_MODE for testing?
- [ ] Will this operation respect cost limits?
- [ ] Am I deduplicating before API calls?
- [ ] Am I logging costs?
- [ ] Am I handling errors?
- [ ] Have I added tests?
- [ ] Are my API keys in .env (not code)?
- [ ] Will I run tests before committing?

**If you answered "no" to any of these, STOP and fix it first.**

---

## Summary

**These constraints are not suggestions - they are REQUIREMENTS.**

Violating them can result in:
- 💰 Budget overruns (could cost $100+ instead of $5)
- 🚫 API bans (lose access to Twitter/Instagram)
- 🐛 Data corruption (lose your curated content)
- 🔒 Security breaches (API keys exposed)
- ⏰ Wasted time (fixing preventable mistakes)

**When in doubt, ask the user. It's better to ask than to make a costly mistake.**
