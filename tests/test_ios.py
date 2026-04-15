#!/usr/bin/env python3
"""Test iOS Shortcut format"""
import os
from dotenv import load_dotenv
load_dotenv()

import requests

webhook_url = os.getenv('GOOGLE_SHEET_WEBHOOK_URL')
secret = os.getenv('GOOGLE_SHEET_SECRET')

print('Testing iOS Shortcut format (GET request)')
print('='*60)

# Simulate exactly how iOS Shortcut sends data
params = {
    'secret': secret,
    'url': 'https://www.instagram.com/reel/IOS_TEST_FIX/',
    'timestamp': '2026-04-15T00:45:00Z'
}

print('\nSending GET request (iOS Shortcut style):')
print('URL: ' + params['url'])

response = requests.get(webhook_url, params=params, timeout=30)
print('\nStatus: ' + str(response.status_code))
print('Response: ' + str(response.json()))

# Now check if it was added
print('\nChecking pending items...')
response2 = requests.post(webhook_url, json={
    'action': 'get_pending',
    'secret': secret
}, timeout=30)

pending = response2.json()
print('Found: ' + str(len(pending)) + ' items')

if pending:
    for item in pending:
        print('  Added: ' + item['cleaned_url'])
else:
    print('  Not added - Apps Script may need redeployment')

print('='*60)
