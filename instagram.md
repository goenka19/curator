# Instagram Integration Status & History

## 🎯 The Goal
To autonomously aggregate, filter, and analyze Instagram Reels shared between a Main and Spare account. The system must use the **Official Instagram API** (Native/Instagram Login flow) to read DMs, extract Reel links, download them for Vision AI analysis, and immediately delete the files to stay within the $5/month budget and storage constraints.

---

## 🛠️ What has been Implemented (The Foundation)

### 1. Database & "Golden Rules" (`backend/models.py`, `backend/database.py`)
- **Deduplication:** A robust check using `is_duplicate()` ensures we never process the same message ID twice, preventing wasted API costs.
- **Cost Logging:** Every AI operation and API call is logged in `api_cost_logs` to track the $5/month budget in real-time.
- **Unified Schema:** `ContentItem` handles both Twitter bookmarks and Instagram DM extracts.

### 2. Media Handling & AI Pipeline (`backend/utils/media.py`, `backend/ai_processor.py`)
- **Auto-Cleanup:** Implemented `download_video` and `cleanup_video`. The system is hardcoded to `os.remove()` the video file the *instant* the AI finishes analysis.
- **Vision AI:** Configured `AIProcessor` to use **Gemini 1.5 Flash** (via OpenRouter) for multimodal analysis of Reels, which is extremely cost-effective (~$0.0001 per analysis).

### 3. Webhook Infrastructure (`backend/scripts/verify_webhook.py`)
- **Handshake Success:** Set up a local server using `localtunnel`/`serveo` that successfully passed Meta's `hub.challenge` verification for the Instagram Webhook.

---

## ⚠️ The "Fucked Up" Part (The Blockers & Saga)

### The API Deadlock
We are currently stuck at the "fetching" stage for Instagram. Despite multiple attempts and configuration changes, the API is not returning the expected data.

- **Current Behavior:** The `InstagramExtractor` queries `graph.instagram.com/v25.0/me/conversations` using a valid `IGAA...` User Access Token.
- **The Result:** The API returns `200 OK` but with an empty data array: `{"data": []}`.
- **The Frustration:**
    - "Allow access to messages" is **ON** in the Instagram app settings.
    - Both accounts (Main and Spare) are registered as **Testers**.
    - The DM thread is in the **Primary** inbox.
    - Previous advice suggested that reading DMs in "Development Mode" is impossible and that we should abandon the official API. **This was rejected.** Accessing DMs in dev mode for tester accounts is a documented feature; we are simply missing the correct endpoint, scope, or parameter configuration.

### The Flip-Flopping Advice
1. **Initial Plan:** Use the official API to fetch DMs.
2. **The Build:** Rewired the extractor to use the Native Instagram API (`graph.instagram.com`) instead of the Facebook Graph API (`graph.facebook.com`).
3. **The Pivot:** When the data came back empty, the previous agent claimed it "would not work" and suggested scraping or manual exports. 
4. **Current Stance:** We are returning to the official API because it **should** work for tester accounts. The current blocker is likely a missing `fields` expansion or the need to query the specific Business Account ID instead of `/me/`.

---

## 📊 Technical Details (Current State)

| Parameter | Value |
| --- | --- |
| **App ID** | `2663989863972260` |
| **Business ID** | `17841409408194132` |
| **Token Type** | Native Instagram (`IGAA...`) |
| **API Version** | `v25.0` |
| **Endpoint** | `https://graph.instagram.com/v25.0/me/conversations` |
| **Scopes Needed** | `instagram_manage_messages`, `instagram_basic` |

---

## 🚀 Immediate Next Steps
1. **Verify Token Scopes:** Use the Token Debugger to ensure `instagram_manage_messages` is actually active on the `IGAA...` token.
2. **Endpoint Testing:** Test if `/v25.0/{ig_user_id}/conversations` works better than `/me/conversations`.
3. **Message Unrolling:** Ensure the `fields` parameter is correctly requesting `messages{id,message,created_time}` to avoid empty results.
