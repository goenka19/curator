import os
import re
import json
import time
import base64
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from backend.extractors.base_extractor import BaseExtractor
from backend.filtering.engine import FilteringEngine
from backend.database import SessionLocal, is_duplicate, save_content_item

class TwitterExtractor(BaseExtractor):
    def __init__(self):
        super().__init__(api_name='twitter')
        self.access_token = os.getenv('TWITTER_OAUTH2_ACCESS_TOKEN')
        self.base_url = "https://api.twitter.com/2"
        self.filter_engine = FilteringEngine()
        self.raw_sources_path = Path("/Users/ujjwalgoenka/Desktop/Coding/curator/curator_vault/raw-sources/twitter")
        self.raw_sources_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Groq client for media processing
        groq_key = os.getenv('GROQ_API_KEY')
        if groq_key and "your_groq_key" not in groq_key:
            from groq import Groq
            self.groq_client = Groq(api_key=groq_key)
        else:
            self.groq_client = None
            print("⚠️  GROQ_API_KEY not set - media processing will be limited")

    def detect_urls(self, text: str) -> Dict[str, List[str]]:
        """Detect and classify URLs in tweet text."""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        
        classified = {
            'x_articles': [],
            'external': [],
            'youtube': [],
            'other': []
        }
        
        for url in urls:
            if 'x.com/i/article' in url or 'twitter.com/i/article' in url:
                classified['x_articles'].append(url)
            elif 'youtube.com' in url or 'youtu.be' in url:
                classified['youtube'].append(url)
            elif any(domain in url for domain in ['substack.com', 'medium.com', 'blog.', 'newsletter']):
                classified['external'].append(url)
            else:
                classified['other'].append(url)
        
        return classified
    
    def fetch_external_content(self, urls: List[str]) -> List[Dict]:
        """Fetch external articles with Jina AI (free) and summarize with Groq."""
        if not self.groq_client:
            return []
        
        results = []
        
        for url in urls:
            if 'x.com/i/article' in url or 'twitter.com/i/article' in url:
                continue
            
            try:
                print(f"   🔗 Fetching external: {url[:50]}...")
                
                # Jina AI fetch (FREE)
                # Jina AI format: https://r.jina.ai/http://URL or https://r.jina.ai/https://URL
                if url.startswith('https://'):
                    jina_url = f"https://r.jina.ai/{url}"
                else:
                    jina_url = f"https://r.jina.ai/http://{url}"
                response = requests.get(jina_url, timeout=30)
                
                if response.status_code == 429:
                    print("   ⏳ Rate limited, waiting 5s...")
                    time.sleep(5)
                    response = requests.get(jina_url, timeout=30)
                
                if response.status_code == 200:
                    article_text = response.text[:8000]
                    
                    # Summarize with Groq
                    summary_prompt = f"""Summarize this article in 2-3 sentences:

{article_text[:4000]}

Summary:"""
                    
                    summary_resp = self.groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": summary_prompt}],
                        max_tokens=200
                    )
                    
                    results.append({
                        'url': url,
                        'summary': summary_resp.choices[0].message.content,
                        'full_text': article_text[:2000]
                    })
                    print(f"   ✅ Fetched & summarized")
                    time.sleep(0.5)  # Be nice to Jina AI
                    
            except Exception as e:
                print(f"   ⚠️ Failed to fetch {url[:50]}: {e}")
                results.append({
                    'url': url,
                    'summary': f'[Fetch failed: {e}]',
                    'full_text': ''
                })
        
        return results

    def process_image(self, image_url: str, tweet_text: str) -> str:
        """Process image with vision model - high quality analysis."""
        if not self.groq_client:
            return "[Image analysis skipped - GROQ_API_KEY not set]"
        
        try:
            response = requests.get(image_url, timeout=30)
            image_data = base64.b64encode(response.content).decode('utf-8')
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""Analyze this image from a tweet. Tweet text: '{tweet_text}'

Extract and describe:
1. ALL visible text (OCR - transcribe everything readable)
2. What's depicted (charts, diagrams, people, products, etc.)
3. Any URLs, QR codes, handles, or links visible
4. Key information adding context to the tweet
5. If chart/graph, describe the data

Be thorough and specific."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                        }
                    ]
                }
            ]
            
            response = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=messages,
                max_tokens=800,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"   ⚠️ Image processing failed: {e}")
            return f"[Image analysis failed: {e}]"

    def process_short_video(self, video_url: str, duration_sec: float, tweet_text: str) -> Dict:
        """Process short video (< 3 min) with transcription + frame analysis."""
        from backend.utils.media import (
            download_video, extract_audio, extract_frames, 
            cleanup_media, get_video_info
        )
        
        if not self.groq_client:
            return {'error': 'GROQ_API_KEY not set'}
        
        video_path = None
        
        try:
            print(f"   📥 Downloading {duration_sec:.1f}s video...")
            video_path = download_video(video_url, f"tweet_vid_{int(time.time())}")
            if not video_path:
                return {'error': 'Download failed'}
            
            info = get_video_info(video_path)
            print(f"   📊 Video: {info['duration']:.1f}s, {info['size_mb']:.1f} MB")
            
            # Phase 1: Transcription
            print("   🎤 Transcribing audio...")
            audio_path = extract_audio(video_path)
            transcript = ""
            
            if audio_path:
                with open(audio_path, "rb") as audio_file:
                    transcription = self.groq_client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-large-v3-turbo",
                        response_format="text"
                    )
                    transcript = transcription if isinstance(transcription, str) else transcription.text
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            
            # Phase 2: Frame analysis (every 2.5 seconds, cap at 24 frames)
            print("   🎬 Analyzing frames...")
            frames = extract_frames(video_path, interval_seconds=2.5)
            frame_descriptions = []
            
            for frame_path, timestamp in frames[:24]:  # Cap at 24 frames
                try:
                    with open(frame_path, "rb") as f:
                        frame_data = base64.b64encode(f.read()).decode("utf-8")
                    
                    response = self.groq_client.chat.completions.create(
                        model="meta-llama/llama-4-scout-17b-16e-instruct",
                        messages=[{
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"At {timestamp}s: Describe what's visible. List text, UI elements, key visual info."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{frame_data}"}
                                }
                            ]
                        }],
                        max_tokens=150
                    )
                    frame_descriptions.append(f"[{timestamp}s] {response.choices[0].message.content}")
                    
                except Exception as e:
                    print(f"   ⚠️ Frame {timestamp}s failed: {e}")
            
            # Phase 3: Combined analysis
            print("   🧠 Analyzing combined content...")
            visual_notes = "\n".join(frame_descriptions)
            
            prompt = f"""Analyze this short video from a tweet.

TWEET TEXT: {tweet_text}

TRANSCRIPT: {transcript[:2000]}

VISUAL NOTES: {visual_notes[:1500]}

Provide:
1. Summary: What's this video about (2-3 sentences)
2. Key Claims: Specific claims made
3. Key Steps: Any process/tutorial shown
4. Action Items: What should viewer do
5. Relevance Score: 1-10 for tech/business/finance

Return JSON."""
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            cleanup_media(video_path)
            
            return {
                'summary': analysis.get('summary', ''),
                'key_claims': analysis.get('key_claims', []),
                'key_steps': analysis.get('key_steps', []),
                'action_items': analysis.get('action_items', []),
                'relevance_score': analysis.get('relevance_score', 5),
                'transcript': transcript,
                'visual_notes': visual_notes
            }
            
        except Exception as e:
            print(f"   ❌ Video processing failed: {e}")
            if video_path:
                cleanup_media(video_path)
            return {'error': str(e)}

    def process_long_video(self, video_url: str, duration_sec: float, tweet_text: str) -> Dict:
        """Process long video (> 3 min) with transcription only."""
        from backend.utils.media import download_video, extract_audio, cleanup_media
        
        if not self.groq_client:
            return {'error': 'GROQ_API_KEY not set'}
        
        video_path = None
        
        try:
            print(f"   📥 Downloading {duration_sec/60:.1f}min video...")
            video_path = download_video(video_url, f"tweet_longvid_{int(time.time())}")
            if not video_path:
                return {'error': 'Download failed'}
            
            print("   🎤 Extracting & transcribing audio...")
            audio_path = extract_audio(video_path)
            
            if not audio_path:
                return {'error': 'Audio extraction failed'}
            
            with open(audio_path, "rb") as audio_file:
                transcription = self.groq_client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3-turbo",
                    response_format="verbose_json"
                )
                
                full_text = transcription.text if hasattr(transcription, 'text') else transcription.get('text', '')
                segments = []
                
                segs = transcription.segments if hasattr(transcription, 'segments') else transcription.get('segments', [])
                for seg in segs:
                    if isinstance(seg, dict):
                        segments.append({
                            'start': seg.get('start', 0),
                            'end': seg.get('end', 0),
                            'text': seg.get('text', '').strip()
                        })
            
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            print("   🧠 Analyzing transcript...")
            prompt = f"""Analyze this video transcript from a tweet.

TWEET TEXT: {tweet_text}

TRANSCRIPT: {full_text[:3000]}

Provide:
1. Summary: What's this video about
2. Key Claims: Specific claims made
3. Key Steps/Timestamps: Important moments
4. Action Items: What should viewer do
5. Relevance Score: 1-10

Return JSON."""
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            cleanup_media(video_path)
            
            return {
                'summary': analysis.get('summary', ''),
                'key_claims': analysis.get('key_claims', []),
                'key_steps': analysis.get('key_steps', []),
                'action_items': analysis.get('action_items', []),
                'relevance_score': analysis.get('relevance_score', 5),
                'transcript': full_text,
                'transcript_segments': segments[:20]
            }
            
        except Exception as e:
            print(f"   ❌ Long video processing failed: {e}")
            if video_path:
                cleanup_media(video_path)
            return {'error': str(e)}

    def classify_media_only(self, tweet: Dict, data: Dict) -> Dict:
        """Extract media URLs without processing (for batch processing later)."""
        media_results = {
            'images': [],
            'videos': [],
            'analysis_text': ''
        }
        
        attachments = tweet.get('attachments', {})
        media_keys = attachments.get('media_keys', [])
        
        if not media_keys:
            return media_results
        
        for media in data.get('includes', {}).get('media', []):
            if media['media_key'] not in media_keys:
                continue
            
            media_type = media.get('type')
            
            if media_type == 'photo':
                image_url = media.get('url') or media.get('preview_image_url')
                if image_url:
                    media_results['images'].append({
                        'url': image_url,
                        'analysis': None  # Will be processed later
                    })
            
            elif media_type in ['video', 'animated_gif']:
                video_url = None
                variants = media.get('variants', [])
                for variant in variants:
                    if variant.get('content_type') == 'video/mp4':
                        video_url = variant.get('url')
                        break
                
                if video_url:
                    duration_ms = media.get('duration_ms', 0)
                    duration_sec = duration_ms / 1000 if duration_ms else 0
                    
                    video_type = 'short' if (duration_sec <= 180 or media_type == 'animated_gif') else 'long'
                    
                    media_results['videos'].append({
                        'url': video_url,
                        'duration': duration_sec,
                        'type': video_type,
                        'analysis': None  # Will be processed later
                    })
        
        return media_results
    
    def classify_and_process_media(self, tweet: Dict, data: Dict, tweet_text: str) -> Dict:
        """Classify media type and process accordingly."""
        media_results = {
            'images': [],
            'videos': [],
            'analysis_text': ''
        }
        
        attachments = tweet.get('attachments', {})
        media_keys = attachments.get('media_keys', [])
        
        if not media_keys:
            return media_results
        
        for media in data.get('includes', {}).get('media', []):
            if media['media_key'] not in media_keys:
                continue
            
            media_type = media.get('type')
            
            if media_type == 'photo':
                image_url = media.get('url') or media.get('preview_image_url')
                if image_url:
                    print(f"   📸 Processing image...")
                    analysis = self.process_image(image_url, tweet_text)
                    media_results['images'].append({
                        'url': image_url,
                        'analysis': analysis
                    })
                    media_results['analysis_text'] += f"\n\n[Image]: {analysis[:200]}..."
            
            elif media_type in ['video', 'animated_gif']:
                video_url = None
                variants = media.get('variants', [])
                for variant in variants:
                    if variant.get('content_type') == 'video/mp4':
                        video_url = variant.get('url')
                        break
                
                if video_url:
                    duration_ms = media.get('duration_ms', 0)
                    duration_sec = duration_ms / 1000
                    
                    if duration_sec <= 180 or media_type == 'animated_gif':
                        print(f"   🎬 Processing short video ({duration_sec:.1f}s)...")
                        analysis = self.process_short_video(video_url, duration_sec, tweet_text)
                        media_results['videos'].append({
                            'url': video_url,
                            'duration': duration_sec,
                            'type': 'short',
                            'analysis': analysis
                        })
                        if 'summary' in analysis:
                            media_results['analysis_text'] += f"\n\n[Video]: {analysis['summary']}"
                    else:
                        print(f"   🎬 Processing long video ({duration_sec/60:.1f}min)...")
                        analysis = self.process_long_video(video_url, duration_sec, tweet_text)
                        media_results['videos'].append({
                            'url': video_url,
                            'duration': duration_sec,
                            'type': 'long',
                            'analysis': analysis
                        })
                        if 'summary' in analysis:
                            media_results['analysis_text'] += f"\n\n[Video]: {analysis['summary']}"
        
        return media_results

    def process_media_batch(self, db, items: List) -> Dict:
        """Process media for a batch of items (10 at a time)."""
        if not self.groq_client:
            print("⚠️  GROQ_API_KEY not set - skipping media processing")
            return {'processed': 0, 'failed': 0}
        
        stats = {'processed': 0, 'failed': 0, 'images': 0, 'videos': 0}
        
        for item in items:
            if not item.media_url:
                continue
            
            try:
                media_data = json.loads(item.media_url)
                analysis_parts = []
                
                # Process images
                for img in media_data.get('images', []):
                    if 'url' in img and not item.media_analysis:
                        print(f"   📸 Processing image for @{item.creator_username}...")
                        analysis = self.process_image(img['url'], item.caption or '')
                        analysis_parts.append(f"[Image]: {analysis[:300]}...")
                        stats['images'] += 1
                
                # Process videos
                for vid in media_data.get('videos', []):
                    if 'url' in vid and not item.media_analysis:
                        video_type = vid.get('type', 'short')
                        duration = vid.get('duration', 0)
                        
                        if video_type == 'short':
                            print(f"   🎬 Processing short video ({duration:.1f}s)...")
                            analysis = self.process_short_video(vid['url'], duration, item.caption or '')
                        else:
                            print(f"   🎬 Processing long video ({duration/60:.1f}min)...")
                            analysis = self.process_long_video(vid['url'], duration, item.caption or '')
                        
                        if 'summary' in analysis:
                            analysis_parts.append(f"[Video]: {analysis['summary']}")
                        stats['videos'] += 1
                
                # Update item with analysis
                if analysis_parts:
                    item.media_analysis = "\n\n".join(analysis_parts)
                    stats['processed'] += 1
                    
            except Exception as e:
                print(f"   ❌ Media processing failed: {e}")
                stats['failed'] += 1
        
        db.commit()
        return stats

    def save_raw_backup(self, tweet: Dict, creator: str, urls: Dict, media_results: Dict, external_content: List[Dict]) -> str:
        """Save raw tweet to backup folder with media info."""
        tweet_id = tweet['id']
        filename = f"{tweet_id}.md"
        filepath = self.raw_sources_path / filename
        
        if filepath.exists():
            return str(filepath)
        
        text = tweet.get('text', '')
        date = tweet.get('created_at', datetime.utcnow().isoformat())
        
        # Build external links list
        all_urls = urls['external'] + urls['other'] + urls['youtube']
        external_links = all_urls + urls['x_articles']
        
        # Build media info
        media_info = []
        for img in media_results.get('images', []):
            media_info.append(f"- Image: {img['url']}")
        for vid in media_results.get('videos', []):
            media_info.append(f"- Video ({vid['type']}): {vid['url']}")
        
        # Build content parts separately to avoid f-string issues
        media_section = "\n".join(media_info) if media_info else "_No media_"
        links_section = "\n".join(["- " + url for url in external_links]) if external_links else "_No external links_"
        content_section = "\n\n".join(["### " + content['url'] + "\n" + content['summary'][:300] + "..." for content in external_content]) if external_content else "_No external content fetched_"
        
        content = f"""---
tweet_id: "{tweet_id}"
author: "@{creator}"
date: "{date}"
url: "https://x.com/{creator}/status/{tweet_id}"
---

## Tweet Text

{text}

## Media

{media_section}

## External Links

{links_section}

## Fetched Content

{content_section}

## Note

This is a raw backup. Processed version with AI insights is in wiki/summaries/.
"""
        
        filepath.write_text(content, encoding='utf-8')
        return str(filepath)

    def fetch_bookmarks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches Twitter Bookmarks with full media processing."""
        if not self.access_token:
            print("❌ ERROR: TWITTER_OAUTH2_ACCESS_TOKEN not set in .env")
            return []

        limit = self.check_dev_limit(limit)
        print(f"🚀 Syncing Twitter Bookmarks...")

        # Get current user ID
        user_url = f"{self.base_url}/users/me"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        user_resp = requests.get(user_url, headers=headers)
        if user_resp.status_code != 200:
            print(f"❌ Failed to fetch Twitter user: {user_resp.text}")
            return []
        
        user_id = user_resp.json().get('data', {}).get('id')
        
        # Get bookmarks with media
        bookmark_url = f"{self.base_url}/users/{user_id}/bookmarks"
        params = {
            "tweet.fields": "created_at,text,author_id,attachments,entities",
            "expansions": "author_id,attachments.media_keys",
            "user.fields": "username",
            "media.fields": "url,preview_image_url,type,duration_ms,variants",
            "max_results": min(limit, 100)
        }
        
        resp = requests.get(bookmark_url, headers=headers, params=params)
        if resp.status_code != 200:
            print(f"❌ Failed to fetch Twitter bookmarks: {resp.text}")
            return []

        data = resp.json()
        tweets = data.get('data', [])
        includes = data.get('includes', {})
        users = includes.get('users', [])
        user_map = {u['id']: u['username'] for u in users}
        
        all_curated_items = []

        for tweet in tweets:
            tweet_id = tweet['id']
            
            # Deduplication
            db = SessionLocal()
            try:
                if is_duplicate(db, tweet_id):
                    print(f"⏩ SKIP: {tweet_id} already processed")
                    continue
            finally:
                db.close()

            text = tweet.get('text', '')
            author_id = tweet.get('author_id')
            creator = user_map.get(author_id, 'unknown')

            print(f"\n📌 Processing @{creator}: {text[:60]}...")

            # Detect and fetch URLs
            urls = self.detect_urls(text)
            all_urls = urls['external'] + urls['other'] + urls['youtube']
            has_x_article = len(urls['x_articles']) > 0
            has_external = len(all_urls) > 0
            
            # Fetch external content
            external_content = []
            if has_external:
                external_content = self.fetch_external_content(all_urls)
            
            # Classify media only (don't process yet - will do in batches)
            media_results = self.classify_media_only(tweet, data)
            
            # Save raw backup
            backup_path = self.save_raw_backup(tweet, creator, urls, media_results, external_content)
            
            # Apply Filter (pass unless blacklisted)
            should_pass, reason = self.filter_engine.should_process(text, creator)
            
            # X Articles always pass
            if has_x_article and not should_pass:
                should_pass = True
                reason = "X Article - requires manual extraction"
            
            # Build media URL JSON
            media_url_json = json.dumps({
                'images': [{'url': img['url']} for img in media_results['images']],
                'videos': [{'url': vid['url'], 'type': vid['type'], 'duration': vid['duration']} for vid in media_results['videos']]
            })
            
            item_data = {
                "source": "twitter",
                "source_id": tweet_id,
                "caption": text,
                "creator_username": creator,
                "timestamp": datetime.strptime(tweet['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ") if 'created_at' in tweet else datetime.utcnow(),
                "pre_filter_passed": should_pass,
                "filter_reason": reason,
                "media_url": media_url_json,
                "has_x_article": has_x_article,
                "x_article_url": urls['x_articles'][0] if has_x_article else None,
                "external_url": all_urls[0] if all_urls else None,
                "external_links_json": json.dumps(external_content),
                "media_analysis": media_results['analysis_text']
            }

            # Save
            db = SessionLocal()
            try:
                save_content_item(db, item_data)
                if should_pass:
                    all_curated_items.append(item_data)
                    print(f"✅ PASSED: @{creator} - {text[:50]}...")
                    if media_results['images']:
                        print(f"   📸 {len(media_results['images'])} images processed")
                    if media_results['videos']:
                        print(f"   🎬 {len(media_results['videos'])} videos processed")
                    if external_content:
                        print(f"   🔗 {len(external_content)} external articles fetched")
                else:
                    print(f"⏩ FILTERED: @{creator} - {reason}")
            finally:
                db.close()

        return all_curated_items
