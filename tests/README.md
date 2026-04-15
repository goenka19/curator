# Test Scripts

This directory contains standalone test scripts for verifying different parts of the Content Curator system.

**Note:** These are standalone scripts, not a proper pytest test suite. They can be run individually to test specific functionality.

## Available Tests

### `test_filtering.py`
Tests the filtering engine with various Twitter bookmark examples.
```bash
python tests/test_filtering.py
```

### `test_instagram.py`
Tests the full Instagram reel processing pipeline (download → save → AI process).
```bash
python tests/test_instagram.py
```

### `test_ios.py`
Tests the iOS Shortcut integration with Google Sheets webhook.
```bash
python tests/test_ios.py
```

### `test_twitter_api.py`
Tests if Twitter API credentials (Bearer Token) are valid.
```bash
python tests/test_twitter_api.py
```

### `test_twitter_bookmarks.py`
Tests OAuth 2.0 authentication and fetches actual Twitter bookmarks.
```bash
python tests/test_twitter_bookmarks.py
```

## Usage

All tests require the virtual environment to be activated:

```bash
cd backend
source venv/bin/activate
cd ..
python tests/<test_name>.py
```

## Notes

- Tests may incur API costs (Twitter API costs $0.005 per tweet)
- DEV_MODE environment variable is respected
- Some tests require credentials in `.env` file
