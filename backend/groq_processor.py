
"""
Groq-Powered AI Processor for Instagram Reels
Complete pipeline: Transcription -> Vision Analysis -> Fact Check -> Tags
"""

import os
import json
import base64
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from groq import Groq
from backend.database import SessionLocal, log_api_cost
from backend.models import ContentItem
from backend.utils.media import (
    download_video, extract_audio, extract_frames, 
    cleanup_media, get_video_info
)


class GroqAIProcessor:
    """
    Processes Instagram reels using Groq API
    """
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key or "your_groq_key" in self.api_key:
            raise ValueError("GROQ_API_KEY not set properly in .env")
        
        self.client = Groq(api_key=self.api_key)
        
        # Model configuration
        self.whisper_model = "whisper-large-v3-turbo"
        self.vision_model = "meta-llama/llama-4-scout-17b-16e-instruct"
        self.analysis_model = "llama-3.3-70b-versatile"
        
        # Frame sampling interval (2.5 seconds - balance between detail and speed)
        self.frame_interval = 2.5
        self.max_duration = 180
    
    def process_reel(self, db: SessionLocal, item: ContentItem) -> Dict[str, Any]:
        """Complete reel processing pipeline"""
        if not item or item.ai_processed:
            return {"status": "skipped", "reason": "already_processed"}
        
        if not item.local_path:
            return {"status": "error", "reason": "no_local_path"}
        
        video_path = item.local_path
        
        print(f"\n{'='*60}")
        print(f"🎬 Processing Reel: {item.media_id}")
        print(f"{'='*60}")
        
        info = get_video_info(video_path)
        if not info["exists"]:
            return {"status": "error", "reason": "video_not_found"}
        
        print(f"📊 Video: {info['duration']:.1f}s, {info['size_mb']:.1f} MB")
        
        try:
            # Phase 1: Transcription
            print(f"\n📝 Phase 1: Audio Transcription")
            transcript_data = self._transcribe_video(video_path)
            
            # Phase 2: Visual Analysis
            print(f"\n👁️  Phase 2: Visual Analysis")
            visual_data = self._analyze_frames(video_path)
            
            # Phase 3: Content Analysis
            print(f"\n🧠 Phase 3: Content Analysis")
            analysis = self._analyze_content(
                transcript=transcript_data,
                visual_notes=visual_data,
                caption=item.caption
            )
            
            # Phase 4: Save
            print(f"\n💾 Phase 4: Saving Results")
            self._save_analysis(db, item, transcript_data, visual_data, analysis)
            
            # Cleanup
            cleanup_media(video_path)
            
            # Log cost
            cost = self._estimate_cost(info["duration"], len(visual_data.get("frames", [])))
            log_api_cost(db, "groq", "reel_analysis", 1, cost)
            
            print(f"\n✅ Complete! Category: {analysis.get('category')} | Score: {analysis.get('relevance_score')}/10")
            
            return {
                "status": "success",
                "id": item.id,
                "category": analysis.get("category"),
                "relevance_score": analysis.get("relevance_score")
            }
            
        except Exception as e:
            print(f"\n❌ Processing failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "reason": str(e)}
    
    def _transcribe_video(self, video_path: str) -> Dict[str, Any]:
        """Extract audio and transcribe"""
        audio_path = extract_audio(video_path)
        if not audio_path:
            return {"full_text": "", "segments": [], "language": "en"}
        
        try:
            print(f"   🎤 Transcribing...")
            
            with open(audio_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model=self.whisper_model,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            # Handle both object and dict responses
            if isinstance(transcription, dict):
                full_text = transcription.get("text", "")
                segments_data = transcription.get("segments", [])
            else:
                full_text = transcription.text if hasattr(transcription, "text") else ""
                segments_data = transcription.segments if hasattr(transcription, "segments") else []
            
            segments = []
            for seg in segments_data:
                if isinstance(seg, dict):
                    segments.append({
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                        "text": seg.get("text", "").strip()
                    })
                else:
                    segments.append({
                        "start": getattr(seg, "start", 0),
                        "end": getattr(seg, "end", 0),
                        "text": getattr(seg, "text", "").strip()
                    })
            
            if os.path.exists(audio_path): os.remove(audio_path)
            
            print(f"   ✅ Transcribed: {len(full_text)} chars, {len(segments)} segments")
            
            return {
                "full_text": full_text,
                "segments": segments,
                "language": getattr(transcription, "language", "en")
            }
            
        except Exception as e:
            print(f"   ⚠️  Transcription failed: {e}")
            if os.path.exists(audio_path): os.remove(audio_path)
            return {"full_text": "", "segments": [], "language": "en"}
    
    def _analyze_frames(self, video_path: str) -> Dict[str, Any]:
        """Extract and analyze frames"""
        frames = extract_frames(video_path, interval_seconds=self.frame_interval)
        
        if not frames:
            return {"frames": [], "detected_links": [], "visual_notes": ""}
        
        all_links = []
        frame_descriptions = []
        frames_to_analyze = frames  # Analyze ALL frames, no cap
        
        print(f"   🔍 Analyzing {len(frames_to_analyze)} frames...")
        
        for frame_path, timestamp in frames_to_analyze:
            try:
                with open(frame_path, "rb") as f:
                    frame_data = base64.b64encode(f.read()).decode("utf-8")
                
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"At {timestamp}s in this Instagram reel: List any URLs, @mentions, or text visible on screen. Be concise."
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{frame_data}"}
                            }
                        ]
                    }
                ]
                
                response = self.client.chat.completions.create(
                    model=self.vision_model,
                    messages=messages,
                    max_tokens=200
                )
                
                content = response.choices[0].message.content
                frame_descriptions.append(f"[{timestamp}s] {content}")
                
                # Extract links from content
                urls = re.findall(r'http[s]?://[^\s<>"{}|\\^`\[\]]+', content)
                mentions = re.findall(r'@\w+', content)
                all_links.extend(urls)
                all_links.extend(mentions)
                
            except Exception as e:
                print(f"   ⚠️  Frame analysis error: {e}")
        
        visual_notes = "\n".join(frame_descriptions)
        unique_links = list(set(all_links))
        
        print(f"   ✅ Found {len(unique_links)} links/mentions")
        
        return {
            "frames": frames,
            "detected_links": unique_links,
            "visual_notes": visual_notes
        }
    
    def _analyze_content(self, transcript: Dict, visual_notes: Dict, caption: Optional[str]) -> Dict:
        """Analyze content, fact check, and generate tags"""
        
        full_transcript = transcript.get("full_text", "")[:3000]
        visual_text = visual_notes.get("visual_notes", "")[:1000]
        
        prompt = f"""Analyze this Instagram reel content.

CAPTION: {caption or "None"}

TRANSCRIPT:
{full_transcript}

VISUAL NOTES:
{visual_text}

DETECTED LINKS: {", ".join(visual_notes.get("detected_links", []))}

TASKS:
1. SUMMARY: Provide a 2-3 sentence summary of what the reel is about

2. KEY CLAIMS: Extract 2-4 specific claims made in the video. For each claim:
   - State the claim clearly
   - Provide fact-check assessment: verified/partially_verified/questionable/unverified
   - Add brief context or notes

3. RELEVANCE ASSESSMENT:
   - Score 0-10 (how valuable is this for someone interested in tech/business/productivity)
   - Explain why in 1 sentence

4. CATEGORY: Choose ONE primary category:
   - AI/Machine Learning
   - Programming/Coding
   - Business/Entrepreneurship
   - Productivity/Tools
   - Finance/Investing
   - Marketing/Growth
   - Design/Creative
   - Other

5. TAGS: Generate 5-8 specific tags (keywords) for this content

6. KEY STEPS/PROCESS: If the reel explains a process, method, or steps, extract them explicitly:
   - List the numbered steps (Step 1, Step 2, Step 3, etc.)
   - Include specific details for each step
   - Note any important setup requirements

7. ACTION ITEMS: List 3-5 specific, actionable items someone should take based on this reel:
   - Include the key steps mentioned above
   - Add any setup or configuration actions
   - Make them concrete and executable

Format as JSON:
{{
  "summary": "...",
  "key_claims": [
    {{"claim": "...", "fact_check": "...", "notes": "..."}}
  ],
  "relevance_score": 8,
  "relevance_reason": "...",
  "category": "...",
  "tags": ["tag1", "tag2", ...],
  "key_steps": ["Step 1: ...", "Step 2: ...", "Step 3: ..."],
  "action_items": ["Specific action 1", "Specific action 2", ...]
}}
"""
        
        try:
            print(f"   🤖 Analyzing content with Llama 3.3...")
            
            response = self.client.chat.completions.create(
                model=self.analysis_model,
                messages=[
                    {"role": "system", "content": "You are an expert content analyst. Analyze Instagram reels for educational/technical value. Be objective and thorough."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            analysis = json.loads(content)
            
            print(f"   ✅ Analysis complete")
            print(f"      Claims found: {len(analysis.get('key_claims', []))}")
            print(f"      Tags: {', '.join(analysis.get('tags', [])[:3])}...")
            
            return analysis
            
        except Exception as e:
            print(f"   ⚠️  Analysis failed: {e}")
            # Return basic analysis as fallback
            return {
                "summary": "Analysis failed, manual review needed",
                "key_claims": [],
                "relevance_score": 5,
                "relevance_reason": "Unable to analyze",
                "category": "Other",
                "tags": ["uncategorized"],
                "action_items": []
            }
    
    def _save_analysis(self, db: SessionLocal, item: ContentItem, 
                       transcript: Dict, visual_notes: Dict, analysis: Dict):
        """Save all analysis results to database"""
        
        # Store transcript and visual data as JSON
        import json
        
        # Build rich insight from analysis
        insight_parts = []
        insight_parts.append(f"SUMMARY: {analysis.get('summary', '')}")
        
        if analysis.get('key_steps'):
            insight_parts.append("\n\nKEY STEPS:")
            for step in analysis['key_steps']:
                insight_parts.append(f"- {step}")
        
        if analysis.get('key_claims'):
            insight_parts.append("\n\nKEY CLAIMS:")
            for claim in analysis['key_claims']:
                insight_parts.append(f"- {claim['claim']}")
                insight_parts.append(f"  Fact check: {claim.get('fact_check', 'unknown')}")
        
        if analysis.get('action_items'):
            insight_parts.append("\n\nACTION ITEMS:")
            for action in analysis['action_items']:
                insight_parts.append(f"- {action}")
        
        full_insight = "\n".join(insight_parts)
        
        # Update item
        item.ai_processed = True
        item.ai_insight = full_insight[:4000]  # Limit length
        item.category = analysis.get("category", "Other")
        item.relevance_score = analysis.get("relevance_score", 5)
        item.key_points = json.dumps({
            "transcript": transcript,
            "visual_notes": visual_notes,
            "detailed_analysis": analysis
        })
        
        db.commit()
        print(f"   ✅ Saved to database")
    
    def _estimate_cost(self, duration_seconds: float, num_frames: int) -> float:
        """Estimate API cost for processing"""
        # Whisper: ~$0.04 per hour of audio
        whisper_cost = (duration_seconds / 3600) * 0.04
        
        # Vision: ~$0.18 per 1M tokens, assume 200 tokens per frame
        vision_tokens = num_frames * 200
        vision_cost = (vision_tokens / 1_000_000) * 0.18
        
        # Analysis: ~$0.59 per 1M tokens, assume 3K input + 1K output
        analysis_tokens = 4000
        analysis_cost = (analysis_tokens / 1_000_000) * 0.59
        
        total = whisper_cost + vision_cost + analysis_cost
        return round(total, 4)


if __name__ == "__main__":
    print("Groq AI Processor - Import and use in your application")
    print("Usage: processor = GroqAIProcessor()")
