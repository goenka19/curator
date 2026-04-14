import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
try:
    from .models import Base, ContentItem, APICostLog
except ImportError:
    from backend.models import Base, ContentItem, APICostLog

# Load DB URL from .env (defaults to local sqlite)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./curator.db')

# Create engine (sqlite-specific configuration)
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    print(f"🔄 Initializing database: {DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully.")

def get_db():
    """Generator for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_duplicate(db: Session, source_id: str) -> bool:
    """Checks if an item with this source_id already exists in the DB."""
    return db.query(ContentItem).filter(ContentItem.source_id == source_id).first() is not None

def save_content_item(db: Session, data: dict) -> ContentItem:
    """Saves a new ContentItem or updates an existing one."""
    item = db.query(ContentItem).filter(ContentItem.source_id == data['source_id']).first()
    if not item:
        item = ContentItem(**data)
        db.add(item)
    else:
        for key, value in data.items():
            if key in data:
                setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

def log_api_cost(db: Session, api_name: str, operation: str, items_count: int, cost_usd: float):
    """Logs the cost of an API operation."""
    log = APICostLog(
        api_name=api_name,
        operation=operation,
        items_count=items_count,
        cost_usd=cost_usd,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()


def is_duplicate(db: Session, source_id: str) -> bool:
    """Checks if an item with this source_id already exists in the DB."""
    return db.query(ContentItem).filter(ContentItem.source_id == source_id).first() is not None

def save_content_item(db: Session, data: dict) -> ContentItem:
    """Saves a new ContentItem or updates an existing one."""
    item = db.query(ContentItem).filter(ContentItem.source_id == data['source_id']).first()
    if not item:
        item = ContentItem(**data)
        db.add(item)
    else:
        for key, value in data.items():
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

def log_api_cost(db: Session, api_name: str, operation: str, items_count: int, cost_usd: float):
    """Logs the cost of an API operation."""
    log = APICostLog(
        api_name=api_name,
        operation=operation,
        items_count=items_count,
        cost_usd=cost_usd,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()

if __name__ == "__main__":
    init_db()
