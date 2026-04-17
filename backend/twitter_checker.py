"""
Smart Twitter Checker
Checks for new bookmarks with minimal API cost ($0.025 for 5-tweet sample)
"""

import os
import sys
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.state_manager import get_state_manager
from backend.extractors.twitter_extractor import TwitterExtractor

class SmartTwitterChecker:
    """Smart checker that minimizes API costs."""
    
    def __init__(self):
        self.state_mgr = get_state_manager()
        self.state = self.state_mgr.load_state()
        self.extractor = TwitterExtractor()
    
    def check_for_new_bookmarks(self, sample_size: int = 5) -> Dict[str, Any]:
        """
        Check if new bookmarks exist by sampling recent ones.
        Cost: $0.005 × sample_size (default: $0.025)
        
        Returns:
            {
                'has_new': bool,
                'new_count': int,
                'sample_size': int,
                'cost': float,
                'message': str,
                'new_ids': list,
                'error': str or None
            }
        """
        result = {
            'has_new': False,
            'new_count': 0,
            'sample_size': sample_size,
            'cost': sample_size * 0.005,
            'message': '',
            'new_ids': [],
            'error': None
        }
        
        # Check if we have access token
        if not self.extractor.access_token:
            result['error'] = "No Twitter access token configured"
            return result
        
        try:
            # Fetch small sample
            print(f"🐦 Sampling {sample_size} recent bookmarks (${result['cost']:.3f})...")
            
            # Use dev limit to be safe
            original_limit = os.getenv('MAX_DEV_ITEMS', '50')
            os.environ['MAX_DEV_ITEMS'] = str(sample_size)
            
            try:
                sample = self.extractor.fetch_bookmarks(limit=sample_size)
            finally:
                os.environ['MAX_DEV_ITEMS'] = original_limit
            
            if not sample:
                result['message'] = "No bookmarks found in sample"
                return result
            
            # Load processed set
            processed = self.state_mgr.load_processed_bookmarks()
            
            # Check for new ones
            new_ids = []
            for item in sample:
                tweet_id = item.get('source_id') or item.get('id')
                if tweet_id and tweet_id not in processed:
                    new_ids.append(tweet_id)
            
            result['new_ids'] = new_ids
            result['new_count'] = len(new_ids)
            
            if new_ids:
                result['has_new'] = True
                result['message'] = f"Found {len(new_ids)} new bookmark(s) in sample of {len(sample)}"
            else:
                result['has_new'] = False
                result['message'] = f"No new bookmarks (checked {len(sample)} most recent)"
            
            # Record cost
            from backend.dashboard import get_dashboard
            dashboard = get_dashboard()
            dashboard.add_cost('twitter', result['cost'])
            
        except Exception as e:
            result['error'] = str(e)
            result['message'] = f"Error checking bookmarks: {e}"
        
        return result
    
    def smart_fetch_decision(self) -> Dict[str, Any]:
        """
        Smart decision on whether to fetch bookmarks.
        Considers mode, cost limits, and checks for new content.
        """
        result = {
            'should_fetch': False,
            'reason': '',
            'mode': self.state.twitter.mode,
            'cost': 0.0,
            'check_result': None
        }
        
        # Check cost limits first
        from backend.dashboard import get_dashboard
        dashboard = get_dashboard()
        total_cost = dashboard.cost_tracker.twitter_monthly_total + dashboard.cost_tracker.instagram_monthly_total
        
        if total_cost >= 5.00:
            result['reason'] = "Monthly cost limit reached ($5.00)"
            return result
        
        if total_cost >= 4.50:
            result['reason'] = "Approaching monthly limit (90% used)"
            return result
        
        # Check mode
        if self.state.twitter.mode == "backlog":
            result['reason'] = f"Backlog mode: {self.state.twitter.backlog_remaining} items remaining. Process backlog first."
            return result
        
        if self.state.twitter.mode == "live":
            # Check if weekly fetch due
            if not self._is_weekly_fetch_due():
                result['reason'] = "Weekly fetch not due yet"
                return result
            
            # Sample check first
            check = self.check_for_new_bookmarks(sample_size=5)
            result['check_result'] = check
            result['cost'] = check['cost']
            
            if check['error']:
                result['reason'] = f"Check failed: {check['error']}"
                return result
            
            if not check['has_new']:
                result['reason'] = "No new bookmarks detected in sample"
                return result
            
            # New bookmarks found!
            result['should_fetch'] = True
            result['reason'] = f"Found {check['new_count']} new bookmark(s). Ready to fetch all."
        
        return result
    
    def _is_weekly_fetch_due(self) -> bool:
        """Check if weekly fetch is due."""
        if not self.state.twitter.last_fetch:
            return True
        
        last_fetch = datetime.fromisoformat(self.state.twitter.last_fetch)
        days_since = (datetime.now() - last_fetch).days
        
        # Fetch if 7+ days since last
        return days_since >= 7
    
    def get_mode_info(self) -> Dict[str, Any]:
        """Get current mode information."""
        return {
            'mode': self.state.twitter.mode,
            'backlog_remaining': self.state.twitter.backlog_remaining,
            'backlog_total': self.state.twitter.backlog_total,
            'manual_override': self.state.twitter.manual_override,
            'auto_fetch_enabled': self.state.twitter.auto_fetch_enabled,
            'weekly_fetch_day': self.state.twitter.weekly_fetch_day,
            'last_fetch': self.state.twitter.last_fetch,
            'last_bookmark_id': self.state.twitter.last_bookmark_id,
            'total_processed': self.state.twitter.total_processed
        }
    
    def set_mode(self, mode: str, manual: bool = True) -> str:
        """
        Set Twitter mode.
        
        Args:
            mode: 'backlog', 'live', or 'auto'
            manual: If True, sets manual_override flag
        """
        valid_modes = ['backlog', 'live', 'auto']
        
        if mode not in valid_modes:
            return f"Invalid mode. Choose from: {', '.join(valid_modes)}"
        
        old_mode = self.state.twitter.mode
        self.state.twitter.mode = mode
        
        if mode == 'live':
            self.state.twitter.auto_fetch_enabled = True
        elif mode == 'backlog':
            self.state.twitter.auto_fetch_enabled = False
        
        if manual:
            self.state.twitter.manual_override = True
        
        self.state_mgr.save_state(self.state)
        
        if manual:
            return f"✅ Twitter mode changed: {old_mode} → {mode} (manual override set)"
        else:
            return f"✅ Twitter mode changed: {old_mode} → {mode}"
    
    def unset_manual_override(self) -> str:
        """Remove manual override, allow auto-switching."""
        self.state.twitter.manual_override = False
        self.state_mgr.save_state(self.state)
        return "✅ Manual override removed. Auto-switching enabled."

# Convenience function
def get_twitter_checker() -> SmartTwitterChecker:
    """Get Twitter checker instance."""
    return SmartTwitterChecker()
