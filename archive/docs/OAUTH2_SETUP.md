# 🔐 Quick Guide: Get OAuth 2.0 Credentials for Twitter

## ⚠️ Why You Need This
We just tested your current credentials:
- ❌ **OAuth 1.0a tokens** = Not configured (placeholders in .env)
- ❌ **Bearer Token** = App-only auth = **CANNOT access bookmarks** (403 Forbidden)
- ✅ **OAuth 2.0 User Access Token** = **REQUIRED for bookmarks**

## 📋 What You'll Get
After following these steps, you'll have:
1. `TWITTER_CLIENT_ID` - OAuth 2.0 Client ID
2. `TWITTER_CLIENT_SECRET` - OAuth 2.0 Client Secret
3. Then we'll use xurl to get your Access Token automatically

---

## 🚀 Step-by-Step Instructions

### STEP 1: Open Developer Portal
🔗 Visit: **https://developer.x.com/en/portal/dashboard**

### STEP 2: Click Your App
Look for your app name in the dashboard (the one you created with API keys already)

### STEP 3: Find "Settings" or "User Authentication Settings"

**Look for these tabs at the TOP of the page:**
- Projects & Apps
- Keys and tokens
- **Settings** ← Click this one
- Or look for **"User authentication settings"** section

### STEP 4: Enable OAuth 2.0

**If you see a "Set up" button** → Click it!

**If you see "Edit"** → Click that!

You'll see a form. Fill it in:

### 4. Configure OAuth 2.0
Fill in these fields:

**App permissions:**
- ☑ Read (minimum needed for bookmarks)

**Type of App:**
- ☑ Web App, Automated App or Bot

**App info:**
- **Callback URL:** `http://localhost:3000/callback`
- **Website URL:** `http://localhost:3000`

Click **Save**

### 5. Get Client ID & Secret
After saving, go to **"Keys and tokens"** tab

You should now see a new section:
- **OAuth 2.0 Client ID** (visible)
- **OAuth 2.0 Client Secret** (click "Regenerate" or "Generate")

**Copy both values immediately!**

### STEP 6: Copy Client ID & Secret

Go to **"Keys and tokens"** tab

You should now see **NEW sections** (if OAuth 2.0 was just enabled):

**OAuth 2.0 Client ID and Client Secret:**
- `Client ID` - Copy this!
- `Client Secret` - Click "Regenerate" → Copy this immediately!

⚠️ **Important:** Client Secret is shown only once - copy it now!

### STEP 7: Add to Your .env File

Open your `.env` file and add these two new lines at the end:

```bash
# OAuth 2.0 Credentials (required for bookmarks)
TWITTER_CLIENT_ID=paste_your_actual_client_id_here
TWITTER_CLIENT_SECRET=paste_your_actual_client_secret_here
```

**Replace** `paste_your_actual_client_id_here` with the real values!

**Save the file!**

---

## ✅ After You Add Client ID & Secret to .env

Come back and say **"done"** or **"ready"**

Then I'll run these commands for you:
```bash
# Register app with xurl
xurl auth apps add curator-app --client-id <from .env> --client-secret <from .env>

# Authenticate (opens browser automatically!)
xurl auth oauth2

# Test fetching 1 bookmark
xurl bookmarks -n 1

# Extract token and add to .env
```

**Estimated total time:** 10-15 minutes
**Cost:** $0.005 (1 test bookmark)

---

## 🎁 BONUS: Check for Manual Token Generation (EASIEST if available!)

After enabling OAuth 2.0, go to **"Keys and tokens"** tab and look for:

**"OAuth 2.0 Access Token and Secret"** section

If you see a **"Generate"** button there:
1. ✅ Click "Generate"
2. ✅ Copy **Access Token** immediately
3. ✅ Copy **Refresh Token** immediately
4. ✅ Add to .env:
   ```bash
   TWITTER_OAUTH2_ACCESS_TOKEN=paste_access_token_here
   TWITTER_OAUTH2_REFRESH_TOKEN=paste_refresh_token_here
   ```
5. ✅ Say **"manual tokens done"** and **skip xurl entirely!**

**This is the FASTEST option** - 5 minutes instead of 15!

However, not all accounts have this button - if you don't see it, use the xurl method above.
