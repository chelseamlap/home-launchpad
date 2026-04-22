# Google Setup Guide

This guide walks you through connecting Google Calendar and Google Sheets to your Home Launchpad dashboard. Calendar and Sheets use separate authentication methods so you can set up each independently.

| Service | Auth Method | What It Does |
|---|---|---|
| **Google Calendar** | OAuth2 (your personal login) | Shows your events on the Today and Calendar tabs |
| **Google Sheets** | Service Account (a bot account) | Reads your budget spreadsheet on the Money tab |

> **Why two methods?** OAuth2 lets the dashboard act as *you* — it sees all your calendars. The service account is a separate bot identity that can only see files you explicitly share with it. This keeps your budget sheet access locked down to one folder, and makes it easy to share the setup with other people without sharing your personal Google login.

---

## Part 1: Google Cloud Project

Both Calendar and Sheets need a Google Cloud project. You only need one project for everything.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top → **New Project**
3. Name it something like `Home Launchpad` → **Create**
4. Make sure your new project is selected in the dropdown

### Enable the APIs

From your project dashboard:

1. Go to **APIs & Services → Library** (left sidebar)
2. Search for and enable each of these:
   - **Google Calendar API**
   - **Google Sheets API**

### Set up the OAuth consent screen

This is required before you can create any credentials:

1. Go to **APIs & Services → OAuth consent screen**
2. Choose **External** → **Create**
3. Fill in the required fields:
   - App name: `Home Launchpad`
   - User support email: your email
   - Developer contact email: your email
4. Click **Save and Continue** through the remaining steps (you can skip scopes and test users for now)
5. On the summary page, click **Publish App** — this prevents your tokens from expiring every 7 days

> **Note:** Since this app only uses `calendar.readonly`, Google won't require a full verification review. You may see a "This app isn't verified" warning during sign-in — that's fine, click "Advanced" → "Go to Home Launchpad" to proceed.

---

## Part 2: Google Calendar (OAuth2)

### Create OAuth credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Name: `Home Launchpad`
5. Click **Create**
6. Click **Download JSON**
7. Rename the downloaded file to `client_secret.json`
8. Place it in your Home Launchpad project root:
   ```
   home-launchpad/
   ├── client_secret.json   ← here
   ├── app.py
   └── ...
   ```

### Run the OAuth flow

On the machine where the dashboard runs:

```bash
cd ~/git-repo/home-launchpad && python3 setup_google_oauth.py
```

A browser window opens. Sign in with your Google account and grant Calendar access. The token is saved to `data/google_token.json`.

> **On a headless Pi?** You'll need to run this from a machine with a browser first, then copy the token file to the Pi:
> ```bash
> scp data/google_token.json your-username@your-pi-ip:~/git-repo/home-launchpad/data/
> ```

### Select calendars

After connecting, go to **Home > Google Calendars** on the dashboard to pick which calendars to display (primary, family, shared, etc.).

---

## Part 3: Google Sheets (Service Account)

The budget/bills tab uses a **service account** — a bot identity that can only access sheets you explicitly share with it. This means:

- It can't see your other Google Drive files
- You control exactly which folder it has access to
- Each person who sets up the dashboard creates their own service account
- No personal Google login is stored for Sheets access

### Create a service account

1. In your Google Cloud project, go to **IAM & Admin → Service Accounts**
2. Click **Create Service Account**
3. Name: `home-launchpad-sheets`
4. Click **Create and Continue**
5. Skip the optional permissions and access steps → **Done**
6. You'll see your new service account in the list. Click on it.
7. Go to the **Keys** tab
8. Click **Add Key → Create new key → JSON → Create**
9. A JSON file downloads automatically
10. Rename it to `google_service_account.json`
11. Place it in your data folder:
    ```
    home-launchpad/
    └── data/
        └── google_service_account.json   ← here
    ```

> **Keep this file private.** It's already gitignored, but don't share it or commit it. Each person needs their own.

### Create a Drive folder and share it

1. In [Google Drive](https://drive.google.com/), create a new folder (e.g., `Home Launchpad`)
2. Open the folder
3. Click **Share**
4. Paste the service account email address — it looks like:
   ```
   home-launchpad-sheets@your-project-id.iam.gserviceaccount.com
   ```
   (You can find this on the Service Accounts page in Google Cloud Console)
5. Give it **Viewer** access → **Send**

### Create your budget spreadsheet

Create a new Google Sheet **inside that shared folder** with two tabs:

**Tab 1: "Budget"**

| Category | Budget | Spent |
|---|---|---|
| Groceries | 800 | 523.45 |
| Dining | 400 | 287.00 |
| Home | 300 | 150.00 |

**Tab 2: "Bills"**

| Bill Name | Amount | Due Date |
|---|---|---|
| Mortgage | 2400 | 2026-04-15 |
| Electric | 185 | 2026-04-10 |
| Internet | 75 | 2026-04-12 |

Due dates should be in `YYYY-MM-DD` format. Bills within the next 7 days show up on the Money tab.

### Get the Sheet ID

Copy the Sheet ID from the URL:

```
https://docs.google.com/spreadsheets/d/THIS_PART_IS_THE_ID/edit
```

Enter this in the dashboard under **Home > Settings > Google Sheet ID**.

### Verify it works

Visit `http://localhost:5000/api/health` — you should see:

```json
"sheets": {"ok": true, "auth": "service_account"}
```

If it says `ok: false`, double-check:
- The `google_service_account.json` file is in `data/`
- The spreadsheet is inside the shared folder
- The service account email has Viewer access to the folder

---

## Troubleshooting

### "Token has been expired or revoked" (Calendar)

Your OAuth token expired. Re-run the setup:

```bash
rm data/google_token.json && python3 setup_google_oauth.py
```

### "No service account key" (Sheets)

The file `data/google_service_account.json` is missing. Download a new key from Google Cloud Console → IAM & Admin → Service Accounts → your account → Keys → Add Key.

### "HttpError 403: The caller does not have permission" (Sheets)

The service account doesn't have access to the spreadsheet. Make sure:
1. The spreadsheet is inside the folder you shared
2. The folder is shared with the service account email (not your personal email)

### "HttpError 404: Requested entity was not found" (Sheets)

The Sheet ID in your settings is wrong. Double-check you copied the right part of the URL.

### Calendar works but Sheets doesn't (or vice versa)

They use completely separate credentials — one being broken doesn't affect the other. Check the specific section above for the one that's not working.

---

## For Developers: How It Works

- **Calendar**: `server/google_auth.py` manages OAuth2 tokens. `server/google_calendar.py` calls the Calendar API. Token stored at `data/google_token.json`.
- **Sheets**: `server/google_sheets.py` loads a service account from `data/google_service_account.json` and calls the Sheets API. No OAuth flow needed — the service account key file is all it needs.
- **Scopes**: Calendar uses `calendar.readonly`. Sheets uses `spreadsheets.readonly` (scoped to the service account, which can only see what's shared with it).
