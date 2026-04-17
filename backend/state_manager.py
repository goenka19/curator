"""
State Manager for Curator Dashboard
Handles all state tracking, persistence, and recovery
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import fcntl
import time

CURATOR_DIR = Path.home() / ".curator"
STATE_FILE = CURATOR_DIR / "state.json"
STATE_BACKUP = CURATOR_DIR / "state.json.bak"
COST_FILE = CURATOR_DIR / "cost_tracker.json"
COST_BACKUP = CURATOR_DIR / "cost_tracker.json.bak"
PROCESSED_BOOKMARKS = CURATOR_DIR / "processed_bookmarks.json"
LAST_RUN_FILE = CURATOR_DIR / "last_run.txt"

@dataclass
class TwitterState:
    mode: str = "backlog"  # "backlog", "live", or "auto"
    manual_override: bool = False
    last_fetch: Optional[str] = None
    last_bookmark_id: Optional[str] = None
    total_processed: int = 0
    backlog_remaining: int = 0
    backlog_total: int = 0
    auto_fetch_enabled: bool = False
    weekly_fetch_day: str = "sunday"
    cost_this_month: float = 0.0

@dataclass
class InstagramState:
    last_check: Optional[str] = None
    queue_processed_today: int = 0
    total_processed: int = 0

@dataclass
class VaultState:
    last_scan: Optional[str] = None
    pages_count: int = 0
    last_new_page: Optional[str] = None
    known_pages: Dict[str, str] = None  # path -> hash
    
    def __post_init__(self):
        if self.known_pages is None:
            self.known_pages = {}

@dataclass
class DailyRunState:
    last_run: Optional[str] = None
    today_count: int = 0
    consecutive_runs: int = 0

@dataclass
class FlagsState:
    first_run_complete: bool = False
    backlog_complete: bool = False
    manual_override: bool = False

@dataclass
class CostMilestones:
    notified_1_dollar: bool = False
    notified_2_dollars: bool = False
    notified_4_dollars: bool = False

@dataclass
class CostTracker:
    twitter_monthly_total: float = 0.0
    instagram_monthly_total: float = 0.0
    last_reset: str = ""
    milestones: CostMilestones = None
    
    def __post_init__(self):
        if self.milestones is None:
            self.milestones = CostMilestones()
        if not self.last_reset:
            self.last_reset = datetime.now().isoformat()

@dataclass
class SystemState:
    version: str = "1.0"
    initialized: str = ""
    twitter: TwitterState = None
    instagram: InstagramState = None
    vault: VaultState = None
    daily_run: DailyRunState = None
    flags: FlagsState = None
    
    def __post_init__(self):
        if not self.initialized:
            self.initialized = datetime.now().isoformat()
        if self.twitter is None:
            self.twitter = TwitterState()
        if self.instagram is None:
            self.instagram = InstagramState()
        if self.vault is None:
            self.vault = VaultState()
        if self.daily_run is None:
            self.daily_run = DailyRunState()
        if self.flags is None:
            self.flags = FlagsState()

class StateManager:
    """Manages all curator state with atomic writes and backups."""
    
    def __init__(self):
        self._ensure_directory()
        self._lock_file = None
    
    def _ensure_directory(self):
        """Create curator directory if it doesn't exist."""
        CURATOR_DIR.mkdir(parents=True, exist_ok=True)
        (CURATOR_DIR / "logs").mkdir(exist_ok=True)
    
    def _acquire_lock(self):
        """Acquire file lock to prevent concurrent access."""
        lock_path = CURATOR_DIR / ".lock"
        self._lock_file = open(lock_path, "w")
        fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX)
    
    def _release_lock(self):
        """Release file lock."""
        if self._lock_file:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
            self._lock_file.close()
            self._lock_file = None
    
    def load_state(self) -> SystemState:
        """Load state with fallback to backup or defaults."""
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    return self._dict_to_state(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  State file corrupted: {e}")
            print("   Trying backup...")
        
        # Try backup
        try:
            if STATE_BACKUP.exists():
                with open(STATE_BACKUP, 'r') as f:
                    data = json.load(f)
                    print("✅ Restored from backup")
                    return self._dict_to_state(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Backup also corrupted: {e}")
        
        # Return fresh state
        print("🆕 Creating fresh state")
        return SystemState()
    
    def save_state(self, state: SystemState):
        """Save state atomically with backup."""
        self._acquire_lock()
        try:
            # Backup existing
            if STATE_FILE.exists():
                shutil.copy(STATE_FILE, STATE_BACKUP)
            
            # Write to temp file
            temp_file = STATE_FILE.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(self._state_to_dict(state), f, indent=2, default=str)
            
            # Atomic rename
            temp_file.replace(STATE_FILE)
            
            # Also update simple last_run file (redundancy)
            if state.daily_run and state.daily_run.last_run:
                with open(LAST_RUN_FILE, 'w') as f:
                    f.write(state.daily_run.last_run)
                    
        finally:
            self._release_lock()
    
    def load_cost_tracker(self) -> CostTracker:
        """Load cost tracker with fallback."""
        try:
            if COST_FILE.exists():
                with open(COST_FILE, 'r') as f:
                    data = json.load(f)
                    return CostTracker(**data)
        except (json.JSONDecodeError, IOError):
            pass
        
        # Try backup
        try:
            if COST_BACKUP.exists():
                with open(COST_BACKUP, 'r') as f:
                    data = json.load(f)
                    return CostTracker(**data)
        except:
            pass
        
        return CostTracker()
    
    def save_cost_tracker(self, tracker: CostTracker):
        """Save cost tracker atomically."""
        self._acquire_lock()
        try:
            # Backup
            if COST_FILE.exists():
                shutil.copy(COST_FILE, COST_BACKUP)
            
            # Write
            temp_file = COST_FILE.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(asdict(tracker), f, indent=2)
            
            temp_file.replace(COST_FILE)
        finally:
            self._release_lock()
    
    def load_processed_bookmarks(self) -> set:
        """Load set of processed bookmark IDs."""
        try:
            if PROCESSED_BOOKMARKS.exists():
                with open(PROCESSED_BOOKMARKS, 'r') as f:
                    return set(json.load(f))
        except:
            pass
        return set()
    
    def save_processed_bookmarks(self, bookmarks: set):
        """Save processed bookmark IDs."""
        with open(PROCESSED_BOOKMARKS, 'w') as f:
            json.dump(list(bookmarks), f)
    
    def add_processed_bookmark(self, bookmark_id: str):
        """Add a single bookmark to processed set."""
        bookmarks = self.load_processed_bookmarks()
        bookmarks.add(bookmark_id)
        self.save_processed_bookmarks(bookmarks)
    
    def check_monthly_reset(self, tracker: CostTracker) -> CostTracker:
        """Reset cost tracker if new month."""
        today = datetime.now()
        last_reset = datetime.fromisoformat(tracker.last_reset)
        
        if today.month != last_reset.month or today.year != last_reset.year:
            print(f"🗓️  New month detected! Resetting cost counters.")
            tracker.twitter_monthly_total = 0.0
            tracker.instagram_monthly_total = 0.0
            tracker.last_reset = today.isoformat()
            
            # Reset milestones
            tracker.milestones = CostMilestones()
            
            self.save_cost_tracker(tracker)
        
        return tracker
    
    def should_run_today(self, state: SystemState) -> bool:
        """Check if dashboard should run today."""
        if not state.daily_run or not state.daily_run.last_run:
            return True
        
        last_run = datetime.fromisoformat(state.daily_run.last_run)
        now = datetime.now()
        hours_since = (now - last_run).total_seconds() / 3600
        
        # Must be at least 20 hours since last run
        if hours_since < 20:
            return False
        
        return True
    
    def validate_timestamps(self, state: SystemState) -> SystemState:
        """Fix clock anomalies."""
        now = datetime.now()
        
        if state.daily_run.last_run:
            last_run = datetime.fromisoformat(state.daily_run.last_run)
            if last_run > now:
                print(f"⚠️  Clock anomaly: last_run is in future!")
                print("   Resetting to 24 hours ago")
                state.daily_run.last_run = (now - timedelta(hours=24)).isoformat()
                self.save_state(state)
        
        return state
    
    def _state_to_dict(self, state: SystemState) -> dict:
        """Convert state to dictionary."""
        return asdict(state)
    
    def _dict_to_state(self, data: dict) -> SystemState:
        """Convert dictionary to state object."""
        # Handle nested dataclasses
        if 'twitter' in data:
            data['twitter'] = TwitterState(**data['twitter'])
        if 'instagram' in data:
            data['instagram'] = InstagramState(**data['instagram'])
        if 'vault' in data:
            vault_data = data['vault']
            if 'known_pages' not in vault_data:
                vault_data['known_pages'] = {}
            data['vault'] = VaultState(**vault_data)
        if 'daily_run' in data:
            data['daily_run'] = DailyRunState(**data['daily_run'])
        if 'flags' in data:
            data['flags'] = FlagsState(**data['flags'])
        
        return SystemState(**data)
    
    def reset_all(self):
        """Reset all state to defaults."""
        print("🔄 Resetting all state to defaults...")
        
        # Backup current
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = CURATOR_DIR / f"reset_backup_{timestamp}"
        backup_dir.mkdir(exist_ok=True)
        
        for f in [STATE_FILE, STATE_BACKUP, COST_FILE, COST_BACKUP, PROCESSED_BOOKMARKS]:
            if f.exists():
                shutil.copy(f, backup_dir / f.name)
        
        # Create fresh
        fresh_state = SystemState()
        fresh_tracker = CostTracker()
        
        self.save_state(fresh_state)
        self.save_cost_tracker(fresh_tracker)
        self.save_processed_bookmarks(set())
        
        print(f"✅ State reset. Backup saved to: {backup_dir}")
        return fresh_state, fresh_tracker

# Singleton instance
_state_manager = None

def get_state_manager() -> StateManager:
    """Get singleton state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
