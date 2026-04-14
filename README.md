# Content Curator

Personal content curation system that extracts and organizes saved content from Twitter/X and Instagram using AI.

## Features

- 📱 **Multi-source**: Twitter bookmarks + Instagram DMs
- 🤖 **AI categorization**: 7 categories using Llama 3.3 70B
- 💰 **Cost-optimized**: Pre-filter reduces AI costs by 60-70%
- 📊 **Dashboard**: Beautiful Next.js web interface
- 🔍 **Search**: Full-text search across all content
- 💵 **Budget tracking**: Real-time cost monitoring

**Monthly cost:** $0.25-0.30 (well under $5 budget)

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Twitter Developer Account (pay-per-use tier)
- Instagram Business/Creator Account + Meta App
- OpenRouter or Groq API key

### Installation

```bash
# Clone repository
git clone [your-repo-url]
cd curator

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Initialize database
python -c "from backend.database import init_db; init_db()"

# Frontend setup
cd ../frontend
npm install
```

### Usage

```bash
# Sync content
python backend/cli.py daily-sync

# Check stats
python backend/cli.py stats

# Run dashboard
cd backend && uvicorn api:app --reload --port 8000
cd frontend && npm run dev
# Visit: http://localhost:3000
```

## Documentation

- **claude.md** - Claude Code instructions (READ FIRST)
- **PROJECT.md** - Architecture and development rules
- **CONSTRAINTS.md** - Hard limits and constraints
- **DEVELOPMENT.md** - Development workflow

## Architecture

```
┌─────────────┐
│   Twitter   │
│   Instagram │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Pre-Filter  │ (60-70% reduction)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ AI Process  │ (Llama 3.3 70B)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   SQLite    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Dashboard  │ (Next.js)
└─────────────┘
```

## Cost Breakdown

| Component | Monthly Cost |
|-----------|-------------|
| Twitter API | $0.25 |
| Instagram API | $0.00 (free) |
| AI Processing | $0.03-0.05 |
| **Total** | **$0.28-0.30** |

## License

MIT
