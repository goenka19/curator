# Archive

This directory contains files that are no longer actively used in production but are kept for reference.

## Directory Structure

### `backend/`
Backend code that was replaced or deprecated:
- `ai_processor.py` - Old AI processor (functionality moved inline to cli.py)
- `sheets_reader.py` - Google Sheets direct reader (replaced by webhook approach)

### `scripts/`
One-time and debug scripts:
- `oauth2_authenticate.py` - **KEEP** - Twitter OAuth 2.0 setup for future re-authentication
- `direct_process.py` - Manual reel processing (use `cli.py process-queue` instead)
- `direct_reader.py` - Google Sheets debugging script
- `verify_process.py` - Processing verification with detailed output
- `debug_sheets.py` - Queue debugging utilities
- `migrate_db.py` - One-time database migration (already applied)

### `research/`
Exploration and research scripts:
- `check_apihut.py` - Playwright scraper for API Hut documentation
- `apihut_downloader.py` - Early API Hut downloader prototype (merged into instagram_extractor.py)

### `docs/`
Old documentation:
- `OAUTH2_SETUP.md` - One-time OAuth setup guide
- `instagram.md` - Early integration notes
- `INSTAGRAM_MESSAGING_PRODUCT.md` - Product specification
- `blog.md` - Blog content about the project

## Important Files to Keep

### `oauth2_authenticate.py`
**Do not delete!** This script is needed for future Twitter re-authentication when the OAuth 2.0 token expires. To use:
```bash
cd backend
source venv/bin/activate
cd ..
python archive/scripts/oauth2_authenticate.py
```

## Cleanup

These files are kept for reference but could be deleted if you need to free up space:
- `research/` - Only needed if debugging API Hut issues
- `docs/` - Old documentation (current docs are in `/docs/`)
- `backend/` - Superseded code

**Never delete without reviewing first!**
