# 🎬 yt-auto — Automated YouTube Video Pipeline

> A production-ready, fully-automated YouTube educational video pipeline. It automatically generates and schedules YouTube Shorts and long-form videos with zero ongoing human work except a single tap on your phone to review and publish.

---

## 🌟 How It Works

This system implements a **two-stage architecture** separated by a human checkpoint:

```
[ Stage A: Auto-Generate (Scheduled Cron) ]
   ├── Topic Detection (Gemini 2.5 Flash + Google Search Grounding)
   ├── Script Writing & Grounded Fact-Verification
   ├── Voice Generation (Gemini TTS / Fallback Kokoro CPU)
   ├── Video/Image Retrieval (Pexels / Pixabay / Fallback Pollinations)
   ├── Timing-based Subtitles (faster-whisper word-level timestamps)
   ├── Background Music (MusicGen / Fallback Numpy Synth)
   ├── FFmpeg Assembly & Auto-looping logic
   └── Video Thumbnail Generation (1280x720 overlay)
   └── Saved as a GitHub Action Artifact 📥
        │
        ▼
[ Human Checkpoint ] ◄── Open GitHub mobile app & tap "Run workflow" on Publish
        │
        ▼
[ Stage B: Auto-Publish (workflow_dispatch) ]
   ├── Downloads Artifact from Stage A
   ├── Trims/Validates Metadata & Flags Synthetic Media (May 2026 YouTube Policy)
   └── Uploads & Schedules video on YouTube via Data API v3 🚀
```

---

## 🔑 GitHub Secrets Setup

You must configure the following repository secrets to allow the pipeline to run successfully on GitHub Actions. 
Go to your repository **Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret** and add:

| Secret Name | Required | Description / Value |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | **Yes** | Your Google AI Studio API key. |
| `PEXELS_API_KEY` | **Yes** | Use this default key: `Lc1GBzaPtICzuN6mNAf2mSjgMOVmf4KZX2ZAHIc9GKXTgiHQ1LsuOhle` or generate your own. |
| `PIXABAY_API_KEY`| No | Optional. Get a free video API key at [Pixabay API Docs](https://pixabay.com/api/docs/). |
| `YT_CLIENT_ID` | **Yes** | OAuth 2.0 Web Client ID from your Google Cloud Console. |
| `YT_CLIENT_SECRET`| **Yes** | OAuth 2.0 Client Secret from your Google Cloud Console. |
| `YT_REFRESH_TOKEN`| **Yes** | OAuth 2.0 Refresh Token (authorized for scope `https://www.googleapis.com/auth/youtube`). |

---

## ⚙️ One-Time Setup Instructions

### 1. YouTube OAuth Consent Screen Fix
If your credentials fail with authentication errors, ensure your app is published:
1. Go to the [Google Cloud Console](https://console.cloud.google.com).
2. Navigate to **APIs & Services** ➔ **OAuth consent screen**.
3. Under **Publishing status**, click **Publish App** to move it out of "Testing" mode. This prevents refresh tokens from expiring after 7 days.

### 2. Getting a Refresh Token
If you need to generate a new refresh token:
1. Go to the [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground).
2. Click the gear icon (top right), check **Use your own OAuth credentials**, and input your `YT_CLIENT_ID` and `YT_CLIENT_SECRET`.
3. In Step 1, select the scope `https://www.googleapis.com/auth/youtube` and click **Authorize APIs**.
4. Log in, grant permissions, click **Exchange authorization code for tokens**, and copy the `refresh_token`.

---

## ⏱️ Video Publishing Schedule

The automation is configured around Indian Standard Time (IST):

*   **Short #1:** Uploads daily at **10:00 AM IST** ➔ Schedules to publish at **12:00 PM IST (Noon)**.
*   **Short #2:** Uploads daily at **05:00 PM IST** ➔ Schedules to publish at **07:00 PM IST (Evening)**.
*   **Long-form:** Uploads every Monday at **11:30 AM IST** ➔ Schedules to publish at **02:00 PM IST**.

---

## 📱 How to Publish from Your Phone

1. **Wait for Notification:** When a scheduled Generate workflow finishes, you will see a successful run under the Actions tab.
2. **Review:** (Optional) If you want to review the video, download the artifact from the Github Actions webpage.
3. **Approve & Publish:** 
   * Open the **GitHub mobile app** on your phone.
   * Go to your repository ➔ **Actions** ➔ select **Publish Video to YouTube**.
   * Tap **Run workflow**, choose the format (`short` or `long`), and submit.
   * Stage B will automatically download the correct generated video, upload it, and schedule it on your channel!
