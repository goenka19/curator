#!/usr/bin/env python3
"""
Process reel with full verification
"""

import os
import sys
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.extractors.instagram_extractor import InstagramExtractor
from backend.groq_processor import GroqAIProcessor
from backend.database import SessionLocal
from backend.models import ContentItem

def main():
    print('🎬 MANUAL REEL PROCESSING WITH VERIFICATION')
    print('='*60)
    
    # Get URL from command line or input
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input('Enter Instagram reel URL: ').strip()
    
    if not url:
        print('No URL provided.')
        return
    
    print(f'\nProcessing: {url}')
    print('='*60)
    
    # Check initial state
    print('\n📊 INITIAL STATE:')
    result = subprocess.run(['du', '-sh', 'data/media/', 'backend/temp/'], 
                          capture_output=True, text=True)
    print(result.stdout)
    
    db = SessionLocal()
    
    try:
        # Step 1: Download
        print('\n📥 Step 1: Downloading...')
        extractor = InstagramExtractor()
        reel_data = extractor.process_reel(url, caption=None)
        
        if not reel_data:
            print('❌ Download failed')
            return
        
        print(f'✅ Downloaded to: {reel_data["local_path"]}')
        
        # Check file exists
        if os.path.exists(reel_data['local_path']):
            size = os.path.getsize(reel_data['local_path'])
            print(f'   File size: {size / 1024 / 1024:.1f} MB')
        
        # Step 2: AI Processing
        print('\n🤖 Step 2: AI Processing...')
        item = db.query(ContentItem).filter(
            ContentItem.source_id == reel_data['source_id']
        ).first()
        
        if item:
            processor = GroqAIProcessor()
            result = processor.process_reel(db, item)
            print(f'\n✅ Processing complete: {result["status"]}')
            
            # Refresh to get data
            db.refresh(item)
            
            # Show results
            print('\n' + '='*60)
            print('📊 COLLECTED DATA:')
            print('='*60)
            print(f'Reel ID: {item.media_id}')
            print(f'Category: {item.category}')
            print(f'Relevance: {item.relevance_score}/10')
            print()
            
            if item.key_points:
                data = json.loads(item.key_points)
                print('TRANSCRIPT (first 300 chars):')
                transcript_text = data['transcript']['full_text'][:300] if data['transcript']['full_text'] else 'No transcript'
                print(transcript_text + '...')
                print()
                print(f"FRAMES ANALYZED: {len(data['visual_notes']['frames'])}")
                print(f"LINKS DETECTED: {data['visual_notes']['detected_links']}")
                print()
                print('ANALYSIS:')
                analysis = data['detailed_analysis']
                summary = analysis['summary'][:200] if analysis.get('summary') else 'No summary'
                print(f'  Summary: {summary}...')
                tags = ', '.join(analysis.get('tags', []))
                print(f'  Tags: {tags}')
                claims_count = len(analysis.get('key_claims', []))
                print(f'  Claims: {claims_count}')
            
            # Step 3: Verify deletion
            print('\n' + '='*60)
            print('🗑️  DELETION VERIFICATION:')
            print('='*60)
            
            video_exists = os.path.exists(reel_data['local_path'])
            audio_path = reel_data['local_path'].replace('.mp4', '.mp3')
            audio_exists = os.path.exists(audio_path)
            frames_dir = reel_data['local_path'].replace('.mp4', '_frames')
            frames_exists = os.path.exists(frames_dir)
            
            print(f"Video file exists: {video_exists} {'❌' if video_exists else '✅ Deleted'}")
            print(f"Audio file exists: {audio_exists} {'❌' if audio_exists else '✅ Deleted'}")
            print(f"Frames dir exists: {frames_exists} {'❌' if frames_exists else '✅ Deleted'}")
            
            # Check total space used
            print('\n📊 FINAL STATE:')
            result = subprocess.run(['du', '-sh', 'data/media/', 'backend/temp/'], 
                                  capture_output=True, text=True)
            print(result.stdout)
            
            if not video_exists and not audio_exists and not frames_exists:
                print('\n✅ ALL FILES PERMANENTLY DELETED - 0 bytes used!')
            else:
                print('\n⚠️  SOME FILES STILL EXIST')
        
    finally:
        db.close()

if __name__ == '__main__':
    main()
