# Instagram DM Bot Product - Future Plan

**Status:** Future project - After personal tool is complete
**Last Updated:** April 13, 2026
**Research Verified:** All claims backed by official Meta documentation

---

## Product Vision

A consumer app that allows users to DM an Instagram bot account with reels/posts + text commands, receiving AI-processed responses.

**Example Use Cases:**
- Recipe reel → "transcribe and email me" → Receive transcribed recipe via email
- Tutorial video → "save to Notion" → Auto-saved with summary to Notion workspace
- Product reel → "add to shopping list" → Items extracted and added to list
- Fitness reel → "analyze form" → AI feedback on exercise technique

---

## Technical Feasibility - VERIFIED ✅

### What Instagram Messaging API Supports:

**1. Receive Shared Reels/Posts via DM** ✅
When user DMs a reel to your bot account, webhook payload includes:
```json
{
  "attachments": [
    {
      "type": "ig_reel",
      "payload": {
        "url": "https://instagram.com/reel/ABC123/",
        "title": "Caption text...",
        "video_id": "17895695668004550"
      }
    }
  ]
}
```

**2. Receive Text Commands** ✅
```json
{
  "message": "transcribe this and email me"
}
```

**3. Send Reply DMs** ✅
- Text messages
- Images, videos, files
- Rich templates (buttons, quick replies)

**4. Real-time Webhooks** ✅
Instant notification when DM received - no polling needed.

---

## Architecture

```
User DMs @YourBot
  - Shares Instagram reel
  - Adds text command: "transcribe and email me"
        ↓
Meta Webhook → Your Server (FastAPI)
  - Receives: reel URL, command text, sender ID
        ↓
Backend Processing:
  1. Download reel video (temp)
  2. AI Processing:
     - Transcribe audio (Whisper API)
     - Extract visual elements (GPT-4 Vision)
     - Summarize content
  3. Parse command ("email", "notion", "calendar", etc.)
  4. Execute action
  5. Delete video file
        ↓
Reply to User via Instagram DM:
  "✓ Transcribed recipe emailed to you@email.com"
  [Attach formatted recipe PDF]
```

---

## Requirements

### Meta/Instagram Setup:
1. **Instagram Professional Account** (Business or Creator) for bot
2. **Facebook Page** linked to Instagram account
3. **Meta Developer App** with permissions:
   - `instagram_basic`
   - `instagram_manage_messages` (requires Advanced Access)
4. **App Review** - Submit for Advanced Access (~3-7 days)

### Infrastructure:
1. **Webhook Server** - HTTPS endpoint (Railway, Render, Fly.io)
2. **Database** - Store user preferences, command history
3. **Queue System** - Handle async processing (Celery/Redis or similar)
4. **AI Services:**
   - Whisper API (transcription) - ~$0.006/minute
   - GPT-4 Vision (visual analysis) - ~$0.01-0.03/request
   - Or local models to reduce costs

---

## Decision: Build Later

**Reason:** Personal tool validates core technology (AI processing) with zero infrastructure costs. Once that's proven, expanding to consumer product is straightforward.

**Timeline:** Start Phase 2 after 2 weeks of using personal tool.
