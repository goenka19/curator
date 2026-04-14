import os
from typing import Dict, Any, List
from backend.database import SessionLocal, log_api_cost

class BaseExtractor:
    def __init__(self, api_name: str):
        self.api_name = api_name
        self.dev_mode = os.getenv('DEV_MODE', 'true').lower() == 'true'
        self.max_dev_items = int(os.getenv('MAX_DEV_ITEMS', 10))

    def log_cost(self, operation: str, items_count: int, cost: float = 0.0):
        """Standard method to log costs across all extractors."""
        db = SessionLocal()
        try:
            log_api_cost(db, self.api_name, operation, items_count, cost)
        finally:
            db.close()

    def check_dev_limit(self, limit: int) -> int:
        """Apply DEV_MODE limits."""
        if self.dev_mode:
            print(f"🛠️  DEV_MODE active: Limiting fetch to {self.max_dev_items} items.")
            return min(limit, self.max_dev_items)
        return limit
