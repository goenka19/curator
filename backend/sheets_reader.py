"""
Direct Google Sheets Reader
Reads Instagram queue directly from Google Sheets API
"""

import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from typing import List, Dict, Optional

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

class GoogleSheetsReader:
    """Reads data directly from Google Sheets"""
    
    def __init__(self):
        self.spreadsheet_id = self._get_spreadsheet_id()
        self.range_name = 'Sheet1!A:H'  # Adjust based on your sheet structure
        self.creds = None
        
    def _get_spreadsheet_id(self) -> str:
        """Extract spreadsheet ID from webhook URL"""
        # The webhook URL contains the spreadsheet ID indirectly
        # For now, you'll need to provide it
        # Format: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
        
        # You can find this in your Google Sheet URL
        sheet_id = os.getenv('GOOGLE_SHEET_ID', '')
        if not sheet_id:
            raise ValueError(
                "Please set GOOGLE_SHEET_ID in .env\n"
                "Find it in your Google Sheet URL:\n"
                "https://docs.google.com/spreadsheets/d/[THIS_IS_THE_ID]/edit"
            )
        return sheet_id
    
    def _get_credentials(self):
        """Get or refresh Google credentials"""
        # Check for existing token
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
        
        # If no valid credentials, need to authenticate
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                print("⚠️  Google authentication required!")
                print("   You'll need to download credentials.json from Google Cloud Console")
                return None
        
        return self.creds
    
    def fetch_queue(self) -> List[Dict]:
        """Fetch all items from the queue"""
        try:
            creds = self._get_credentials()
            if not creds:
                print("❌ Google Sheets authentication not set up")
                print("   Please provide the reel URL directly")
                return []
            
            service = build('sheets', 'v4', credentials=creds)
            sheet = service.spreadsheets()
            
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=self.range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                print('No data found in sheet')
                return []
            
            # Parse headers and data
            headers = values[0]
            items = []
            
            for i, row in enumerate(values[1:], start=2):  # Start at row 2
                if len(row) >= 3:  # Ensure we have minimum data
                    item = {
                        'row_index': i,
                        'timestamp': row[0] if len(row) > 0 else '',
                        'url': row[1] if len(row) > 1 else '',
                        'cleaned_url': row[2] if len(row) > 2 else '',
                        'status': row[3] if len(row) > 3 else 'pending',
                        'retry_count': int(row[4]) if len(row) > 4 and row[4] else 0,
                    }
                    items.append(item)
            
            return items
            
        except Exception as e:
            print(f"❌ Error reading Google Sheet: {e}")
            return []


def setup_google_auth():
    """Guide user through Google authentication setup"""
    print("""
🔧 GOOGLE SHEETS AUTHENTICATION SETUP
=====================================

To read directly from Google Sheets, you need to:

1. Go to https://console.cloud.google.com/
2. Create a new project or select existing
3. Enable Google Sheets API:
   - APIs & Services > Library
   - Search "Google Sheets API"
   - Click Enable

4. Create credentials:
   - APIs & Services > Credentials
   - Create Credentials > OAuth client ID
   - Application type: Desktop app
   - Name: Content Curator
   - Download the JSON file

5. Rename the downloaded file to 'credentials.json' and place it in:
   /Users/ujjwalgoenka/Desktop/Coding/curator/

6. Add to .env:
   GOOGLE_SHEET_ID=your_spreadsheet_id_here
   (Find this in your sheet URL)

7. Run this script once to authenticate

ALTERNATIVE: Just paste reel URLs directly:
   python direct_process.py "https://www.instagram.com/reel/XXX/"
""")


if __name__ == "__main__":
    setup_google_auth()
