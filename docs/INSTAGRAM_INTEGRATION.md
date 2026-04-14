# Instagram Reel Integration

This document describes the Instagram reel processing system using API Hut.

## Overview

The system downloads Instagram reels without requiring login using **API Hut** (`apihut.in`). This avoids the checkpoint verification issues that prevented using Instagram's official API or scraping libraries.

## Architecture

```
iOS Shortcut → Google Sheets → Queue Processor → API Hut → Video Download → AI Analysis → Database
```

## Components

### 1. Instagram Extractor (`backend/extractors/instagram_extractor.py`)

Downloads reels using API Hut:
- Extracts shortcode from reel URL
- Calls API Hut to get video download URL
- Downloads video to `data/media/`
- Saves metadata to database

**No login required** - uses free tier API key.

### 2. Queue Processor (`backend/extractors/instagram_queue_processor.py`)

Processes reels from Google Sheets queue:
- Fetches pending reels from Google Sheets
- Downloads each reel using InstagramExtractor
- Runs AI vision analysis
- Updates queue status

### 3. CLI Commands

```bash
# Process Instagram queue
python backend/cli.py process-queue

# Process with limit (DEV_MODE)
python backend/cli.py process-queue --limit 5

# View statistics
python backend/cli.py stats

# Initialize database
python backend/cli.py init
```

## Configuration

### Environment Variables

```env
# API Hut (Instagram downloader - no login required)
APIHUT_KEY=avatarhubadmin  # Free tier demo key

# Google Sheets Integration
GOOGLE_SHEET_WEBHOOK_URL=https://script.google.com/macros/s/...
GOOGLE_SHEET_SECRET=curator_ig_queue_2026

# Media Storage
MEDIA_DOWNLOAD_DIR=data/media
```

### Google Sheets Setup

The Google Sheet "Instagram Queue" has these columns:
- `timestamp` - When reel was added
- `url` - Original URL from iOS
- `cleaned_url` - Cleaned reel URL
- `status` - pending/processing/processed/failed
- `retry_count` - Number of retry attempts
- `processed_at` - When processing completed
- `error_message` - Error details if failed
- `db_id` - Database ID after processing

## Usage

### Manual Testing

```bash
# Test single reel download
python -c "
from backend.extractors.instagram_extractor import InstagramExtractor
extractor = InstagramExtractor()
result = extractor.process_reel('https://www.instagram.com/reel/SHORTCODE/')
print(result)
"
```

### Full Pipeline Test

```bash
python test_instagram.py
```

### Processing Queue

```bash
# Process all pending reels
python backend/cli.py process-queue

# Process max 5 reels (respects DEV_MODE limit)
python backend/cli.py process-queue --limit 5
```

## Data Model

Instagram reels are stored in the same `ContentItem` table as Twitter bookmarks:

| Field | Value Example |
|-------|--------------|
| `source` | "instagram" |
| `source_id` | "instagram_DWjdnxMCpcL" |
| `media_id` | "DWjdnxMCpcL" |
| `caption` | "Instagram reel: DWjdnxMCpcL" (or from share sheet) |
| `creator_username` | null (API doesn't provide this) |
| `media_url` | CDN URL from API Hut |
| `local_path` | "data/media/DWjdnxMCpcL.mp4" |
| `pre_filter_passed` | true (reels skip pre-filter) |
| `ai_processed` | false (until AI runs) |

## Limitations

1. **No metadata** - API Hut provides video only, NOT:
   - Caption text
   - Username/creator
   - Post timestamp
   - Engagement metrics (likes, comments)

2. **Public reels only** - Private reels won't work

3. **Rate limits unknown** - Free tier may have daily limits (estimated 50-100/day)

4. **Video only** - No images/carousels

## Cost

API Hut free tier = **$0**

Only costs are:
- AI vision analysis via OpenRouter (~$0.001-0.003 per reel)

## Troubleshooting

### "Resource does not exist" error
- Reel may be private or deleted
- Try a different public reel

### Rate limiting
- API Hut may return 429 errors if too many requests
- Add delays between requests
- Consider signing up for paid tier if limits are hit

### Video download fails
- CDN URLs expire quickly (JWT tokens)
- Must download immediately after getting URL
- Retry will fetch fresh URL

## Future Improvements

1. **Extract caption from share sheet** - iOS share sheet sometimes includes caption text
2. **Sign up for API Hut paid tier** - Higher rate limits
3. **Add retry logic with exponential backoff** - Handle rate limits better
4. **Process reels in batch** - Download multiple, then AI process
