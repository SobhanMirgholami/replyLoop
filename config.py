"""All settings come from environment variables (or a .env file when running locally)."""
import os
from dotenv import load_dotenv

load_dotenv()

# Database: SQLite file locally, Supabase Postgres in production (paste its "Session pooler" URL).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///replyloop.db")

# Long random string. Signs nothing by itself, but encrypts the Instagram tokens stored in the database.
# Keep it the same forever, or saved tokens can't be read and accounts must be reconnected.
SECRET_KEY = os.getenv("SECRET_KEY", "")

# First login. Used only when the database has no users yet; change the password in Settings afterwards.
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# Optional "Sign in with Google". Create an OAuth client (type: Web application) in Google Cloud Console.
# Only emails that already have access (the owner + people added in Settings) can sign in with it.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
# The app's public address, e.g. https://replyloop.onrender.com (Render fills RENDER_EXTERNAL_URL itself).
PUBLIC_URL = (os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")

# Meta app (one app serves all your Instagram accounts)
APP_SECRET = os.getenv("APP_SECRET", "")          # verifies that webhooks really come from Meta
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")      # any string; type the same one in the Meta dashboard
GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v26.0")

# Backup comment checker: every POLL_SECONDS, look at the newest POLL_POSTS posts of each live account
# for comments the webhook missed. 0 turns it off. ~100 API calls/hour per account at the defaults.
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "180"))
POLL_POSTS = int(os.getenv("POLL_POSTS", "5"))

# Optional AI fallback
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "claude-haiku-5-5")
