#!/usr/bin/env python3
"""
Debug Google Sheets queue - see all items including their status
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json

webhook_url = os.getenv('GOOGLE_SHEET_WEBHOOK_URL')
secret = os.getenv('GOOGLE_SHEET_SECRET')

print('🔍 DEBUGGING GOOGLE SHEETS QUEUE')
print('='*60)

# Try to get ALL items (not just pending) by checking different approaches

# Approach 1: Try action=list_all
print('\n1. Trying action=list_all')
try:
    response = requests.post(webhook_url, json={
        'action': 'list_all',
        'secret': secret
    }, timeout=30)
    print(f'   Status: {response.status_code}')
    data = response.json()
    print(f'   Response: {json.dumps(data, indent=2)[:1000]}')
except Exception as e:
    print(f'   Error: {e}')

# Approach 2: Check if there's a different sheet or range issue
print('\n2. Checking sheet name and range')
print(f'   Webhook: {webhook_url[:60]}...')
print(f'   Secret: {secret[:15]}...')

# The webhook returns [] which means either:
# - No items with status='pending' AND retry_count < 2
# - Sheet name is wrong (should be 'Queue')
# - Column indexing is off

print('\n3. Possible issues:')
print('   - Items might have status != "pending"')
print('   - Items might have retry_count >= 2')
print('   - Sheet name might not be "Queue"')
print('   - Webhook might be checking wrong columns')

print('\n' + '='*60)
print('SOLUTION:')
print('The webhook only returns items where:')
print('  - Column D (status) = "pending"')
print('  - Column E (retry_count) < 2')
print('\nPlease check your Google Sheet:')
print('1. Open "Instagram Queue" sheet')
print('2. Look at column D (status) - should say "pending"')
print('3. Look at column E (retry_count) - should be 0 or 1')
print('4. Check the sheet tab name at bottom - should be "Queue"')
