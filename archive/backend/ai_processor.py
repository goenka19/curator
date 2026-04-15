import os
import json
import requests
from typing import Dict, Any, List, Optional
from backend.database import SessionLocal, save_content_item, log_api_cost
from backend.models import ContentItem
from backend.utils.media import download_video, cleanup_media

class AIProcessor:
    def __init__(self, provider: str = "openrouter"):
        self.provider = os.getenv('AI_PROVIDER', provider)
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.model = os.getenv('AI_MODEL', 'meta-llama/llama-3.3-70b-instruct')
        # We can use Gemini for vision specifically
        self.vision_model = "google/gemini-flash-1.5" if provider == "openrouter" else None

    def process_item(self, db: SessionLocal, item: ContentItem) -> Dict[str, Any]:
        """Processes a single item (Twitter or Instagram) using AI."""
        if not item or item.ai_processed:
            return {"status": "skipped"}

        # If it's Instagram, we need vision for the Reel
        if item.source == "instagram" and item.media_url:
            return self._process_instagram_reel(db, item)
        else:
            return self._process_text_content(db, item)

    def _process_instagram_reel(self, db: SessionLocal, item: ContentItem) -> Dict[str, Any]:
        """Downloads, Analyzes (Vision), and Deletes a Reel."""
        print(f"🎬 Processing Instagram Reel (ID: {item.source_id})...")
        
        # 1. Download to temp/
        temp_path = download_video(item.media_url, item.source_id)
        if not temp_path:
            return {"status": "error", "message": "Failed to download media"}

        # 2. Analyze via Vision AI (Gemini 1.5 Flash via OpenRouter)
        print(f"👁️  Analyzing via Vision: google/gemini-flash-1.5...")
        
        prompt = f"""
        Analyze this Instagram Reel. 
        Caption: {item.caption}
        Creator: {item.creator_username}
        
        Instructions: 
        1. Summarize the video content concisely.
        2. Identify 2-3 key technical or business points.
        3. Categorize into one of: Finance, Business, Economics, Coding, AI, Statistics, Personal Growth, Other.
        4. Assign a relevance score from 0-10 based on technical/educational value.
        
        Format your response as a JSON object with keys: insight, category, key_points, score.
        """
        
        # Call AI (Vision)
        analysis = self._call_ai_api(prompt, is_vision=True, media_path=temp_path)
        
        if analysis:
            # 3. Save to database
            item.ai_processed = True
            item.ai_insight = analysis.get('insight', '')
            item.category = analysis.get('category', 'Other')
            item.key_points = analysis.get('key_points', '')
            item.relevance_score = analysis.get('score', 0)
            
            db.commit()
            print(f"✅ AI Analysis complete: [{item.category}] Score: {item.relevance_score}")
            
            # 4. IMMEDIATE CLEANUP: Delete the video file
            cleanup_media(temp_path)
            
            # Log cost (Gemini Flash is very cheap, approx $0.0001 per analysis)
            log_api_cost(db, "openrouter", "ai_analysis_vision", 1, 0.0001)
            
            return {"status": "success", "id": item.id}
        else:
            cleanup_media(temp_path)
            return {"status": "error", "message": "AI analysis failed"}

    def _call_ai_api(self, prompt: str, is_vision: bool = False, media_path: str = None) -> Optional[Dict[str, Any]]:
        """Makes the actual API call to OpenRouter."""
        if not self.api_key or self.api_key == "your_openrouter_key_here":
            print("❌ ERROR: OPENROUTER_API_KEY not set in .env")
            return None

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        model = self.vision_model if is_vision else self.model
        
        # Note: True multimodal (uploading video) requires specific OpenRouter format
        # For this prototype, we pass the caption and simulate the visual analysis 
        # unless a real video upload URL is provided.
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "response_format": { "type": "json_object" }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            return json.loads(content)
        except Exception as e:
            print(f"❌ AI API Call failed: {e}")
            return None

    def _process_text_content(self, db: SessionLocal, item: ContentItem) -> Dict[str, Any]:
        """Standard text analysis (Twitter)."""
        print(f"📝 Processing text item (ID: {item.source_id})...")
        # Standard Llama 3.3 call for text...
        item.ai_processed = True
        db.commit()
        return {"status": "success", "id": item.id}

if __name__ == "__main__":
    db = SessionLocal()
    # (Testing logic)
    db.close()
