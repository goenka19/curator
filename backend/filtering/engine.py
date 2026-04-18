import json
import re
from typing import Dict, Any, List, Optional

class FilteringEngine:
    def __init__(self, rules_path: str = "backend/filtering/rules.json"):
        self.rules_path = rules_path
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        try:
            with open(self.rules_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Warning: Could not load rules from {self.rules_path}: {e}")
            return {}

    def fuzzy_match(self, text: str, keywords: List[str]) -> bool:
        """Check if any of the keywords are present in the text (fuzzy matching)."""
        text = text.lower()
        for kw in keywords:
            if kw.lower() in text:
                return True
        return False

    def is_engagement_bait(self, caption: str) -> bool:
        """Check if the caption contains common engagement-bait phrases."""
        triggers = self.rules.get("engagement_bait", {}).get("triggers", [])
        return self.fuzzy_match(caption, triggers)

    def should_process(self, text: str, creator_info: Optional[str] = None) -> (bool, str):
        """
        Determines if a piece of content should be processed by AI.
        Returns: (should_process, reason)
        """
        if not text and not creator_info:
            return False, "Empty content"

        # 1. Blacklist Check (Auto-Reject)
        blacklist = self.rules.get("blacklist", {}).get("keywords", [])
        if self.fuzzy_match(text, blacklist):
            return False, "Blacklist keyword found in text"

        # 2. Minimum Length Check
        min_len = self.rules.get("min_caption_length", 5)
        if len(text) < min_len:
            # If text is too short, we check if it's a known high-value creator
            if creator_info:
                high_val_creators = self.rules.get("creator_reputation", {}).get("high_value_keywords", [])
                if self.fuzzy_match(creator_info, high_val_creators):
                    return True, "High-value creator despite short caption"
            return False, f"Caption too short (len={len(text)})"

        # 3. Whitelist Check (Auto-Pass)
        whitelist = self.rules.get("whitelist", {}).get("keywords", [])
        if self.fuzzy_match(text, whitelist):
            return True, "Whitelist keyword found in text"

        # 4. Contextual Check (Engagement Bait vs Creator Reputation)
        is_bait = self.is_engagement_bait(text)
        if is_bait:
            if creator_info:
                # If it's bait, but the creator is known for value, we might still process it
                high_val_creators = self.rules.get("creator_reputation", {}).get("high_value_keywords", [])
                if self.fuzzy_match(creator_info, high_val_creators):
                    return True, "High-value creator despite engagement bait"
            return False, "Engagement bait/copypasta detected"

        # 5. Creator Reputation Check (Blacklist for creators)
        if creator_info:
            low_val_creators = self.rules.get("creator_reputation", {}).get("low_value_keywords", [])
            if self.fuzzy_match(creator_info, low_val_creators):
                return False, "Low-value creator reputation"

        # 6. Default fallback
        # Pass unless explicitly blacklisted - ensures high recall
        return True, "Passed - no blacklist match"

if __name__ == "__main__":
    # Test the engine
    engine = FilteringEngine()
    test_cases = [
        ("This is a great reel about finance and private credit", "invest_daily"),
        ("Check out this nba highlight", "sports_center"),
        ("This is a short quote from a book recommendation", "book_lover"),
        ("Follow for more thoughts?", "daily_memes"),
        ("Follow for more thoughts?", "finance_pro"),
        ("Python coding for ai", "dev_guy")
    ]
    
    for text, creator in test_cases:
        pass_filter, reason = engine.should_process(text, creator)
        print(f"Text: {text[:40]}... | Creator: {creator} | Pass: {pass_filter} | Reason: {reason}")
