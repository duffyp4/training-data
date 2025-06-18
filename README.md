# Strava to LLM Feed

This project contains a set of scripts to automatically scrape your Strava activities, format them into a structured, LLM-friendly feed using JSON-LD, and publish it to a Markdown file. This allows language models to easily reason over your latest training data.

The process is managed by a GitHub Action that runs nightly.

## Architecture

1.  **GitHub Action (`.github/workflows/update-strava.yml`)**: Runs on a schedule or manually, setting up the environment.
2.  **Scraper (`scripts/scrape-strava.ts`)**: Uses a persistent Browserbase `contextId` to maintain a logged-in Strava session, scrapes new activities, and saves them to `activities.json`.
3.  **Renderer (`scripts/render-feed.ts`)**: Reads `activities.json`, adds new activities to `index.md`, upgrades existing ones with more detail, and updates `data/last_id.json`.
4.  **Git Push**: The action commits the updated `index.md` and `data/last_id.json` back to the repository.

## One-Time Setup: Creating a Persistent Strava Session

This system uses a persistent Browserbase session to avoid logging in with every run. You must create this session programmatically and log in manually *once*.

**1. Set Environment Variables:**

Before you can create a context, you need to authenticate with Browserbase. Create a `.env` file in the root of this project:

```
BROWSERBASE_API_KEY="your_api_key_here"
BROWSERBASE_PROJECT_ID="your_project_id_here"
```

You can find these values on your [Browserbase dashboard](https://www.browserbase.com/dashboard).

**2. Create the Persistent Context:**

Run the helper script from your terminal. This will contact Browserbase and create a new, empty "cookie jar" for your session.

```bash
npm run create-context
```

The script will print a **Context ID**. Copy this ID—you will need it for the next steps.

**3. Log In to Strava Manually:**

Now you need to "fill the cookie jar" by logging into Strava.

*   Go to the [Browserbase Session Live-View tool](https://www.browserbase.com/sessions/live-view).
*   Enter the **Context ID** you just copied.
*   Make sure the **"Persist session data"** checkbox is **checked**.
*   Click **"Start session"**. A remote browser window will open.
*   In that browser, navigate to `https://www.strava.com` and log in with your credentials.
*   Once you are successfully logged in and can see your dashboard, you can close the browser tab. The session cookies are now saved to your context.

**4. Configure GitHub Secrets:**

Navigate to your GitHub repository's `Settings` > `Secrets and variables` > `Actions` and add the following repository secrets:

*   `BROWSERBASE_API_KEY`: The same key you put in your `.env` file.
*   `BROWSERBASE_PROJECT_ID`: The same project ID you put in your `.env` file.
*   `STRAVA_CONTEXT_ID`: The **Context ID** you generated in step 2.
*   `GOOGLE_API_KEY`: A Google API key, required for the Stagehand model.
*   `STRAVA_EMAIL`: Your Strava account email address.
*   `STRAVA_PASSWORD`: Your Strava account password.

## How It Works

This system uses a dual approach to authentication for maximum reliability:

1.  **Persistent Context (Primary):** The Action first attempts to use the `STRAVA_CONTEXT_ID` to resume a previous session. This is fast and avoids repeated logins.
2.  **Direct Login (Fallback):** If the context is invalid or expired (which can happen), the script detects the Strava login page and uses your `STRAVA_EMAIL` and `STRAVA_PASSWORD` secrets to perform a direct login.

This ensures that even if the session persistence fails, the script can recover and continue its work.

## Usage

### Automatic Runs

The GitHub Action will now run automatically every night, using your persistent, pre-authenticated session.

### Manual Runs

You can manually trigger a run from the "Actions" tab in your GitHub repository.

If the script ever fails due to an authentication error (e.g., Strava logs you out after a long period of inactivity), simply repeat **Step 3: Log In to Strava Manually** using your *existing* `STRAVA_CONTEXT_ID` to refresh the cookies. You do not need to create a new context. 