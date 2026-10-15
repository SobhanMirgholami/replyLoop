# replyloop

Your private Instagram helper. It answers comments on your posts and reels, sends DMs (optionally only to followers,
with an "I'm following ✅" button), and shows everything in an inbox. It handles several Instagram accounts,
has a light and a dark theme, and installs on Android and iPhone like a normal app.

```
someone comments on a post
  → this post's automations (top to bottom, first match wins)
  → automations for every post
  → AI reply (optional)
  → public reply and/or DM  ·  followers-only: DM with a button → they tap → follower? details : button again
```

---

## Step 1 · Try it on your computer (10 minutes)

You need Python 3.11+.

```bash
cd replyloop
python -m venv .venv
# Windows: .venv\Scripts\activate     Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
```

Open `.env` and fill in:
- `SECRET_KEY`: run `python -c "import secrets; print(secrets.token_hex(32))"` and paste the result
- `ADMIN_EMAIL` and `ADMIN_PASSWORD` (at least 10 characters): your login

Start it:

```bash
uvicorn app:app --reload
```

Open **http://localhost:8000**, sign in, tap **Try a demo account**, open the pistachio reel and type
`لینک لطفا` in **Try a comment** → **Simulate comment**. You'll land in the inbox, where you can simulate
the person tapping the button as a follower or not.

> On your computer the data is saved in `replyloop.db`. You can't install it on your phone from here
> (phones only install apps from `https://` addresses), which is what Step 2 is for.

---

## Step 2 · Put it online for free (about 30 minutes, once)

You'll use three free services: **GitHub** (stores the code), **Supabase** (the database), **Render** (runs the app).

### 2a · GitHub
1. Create a free account at github.com → **New repository** → name it `replyloop` → **Private** → Create.
2. Upload the project: either drag the files in on the website (**uploading an existing file**), or:
   ```bash
   git init && git add . && git commit -m "replyloop"
   git branch -M main
   git remote add origin https://github.com/<you>/replyloop.git
   git push -u origin main
   ```
   `.env` and `replyloop.db` are ignored on purpose, so your passwords never end up on GitHub.

### 2b · Supabase (database)
1. supabase.com → sign up → **New project**. Pick a region close to you (e.g. *Frankfurt*).
   Set a **database password** and save it somewhere.
2. When it's ready: top bar **Connect** → **Session pooler** → copy the URI. It looks like
   `postgresql://postgres.abcd:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres`.
   Replace `[YOUR-PASSWORD]` with your database password. This is your `DATABASE_URL`.
   (Use the *Session pooler*, not *Direct connection*: Render can't reach the direct one.)

The app creates its tables by itself on first start.

### 2c · Render (runs the app)
1. render.com → sign up with GitHub → **New** → **Blueprint** → choose your `replyloop` repo.
2. Render reads `render.yaml` and asks for these values:
   - `DATABASE_URL`: from 2b
   - `ADMIN_EMAIL` / `ADMIN_PASSWORD`: your login
   - `APP_SECRET`, `ANTHROPIC_API_KEY`, `PRIVACY_CONTACT`: leave empty for now (Step 4)
   `SECRET_KEY` and `VERIFY_TOKEN` are generated for you.
3. **Apply**. The first deploy takes a few minutes. Your app gets an address like
   `https://replyloop-xxxx.onrender.com`.

### 2d · Keep it awake
Render's free plan puts the app to sleep after 15 minutes without visitors, and waking up takes about a minute.
That's too slow for a bot, so ping it:
1. cron-job.org → free account → **Create cronjob**
2. URL: `https://replyloop-xxxx.onrender.com/health` · every **10 minutes** → Save.

(750 free hours a month on Render covers running all month.)

### 2e · Sign in with Google (optional, ~10 minutes)
Lets you (and people you add) sign in with a Google account instead of typing a password.
Only Gmail addresses that already have access work, so it's still private.
1. Go to **console.cloud.google.com** → create a project (any name, e.g. *replyloop*).
2. **APIs & Services → OAuth consent screen** (also called *Google Auth Platform → Branding*): app name *replyloop*,
   your email as support and developer contact. Audience: **External**. Add the scopes **openid** and **email** only.
   You can leave it in **Testing** mode: then add every Gmail that will sign in under **Test users**
   (you + the people you add). Or press **Publish app**; with only these basic scopes no Google review is needed.
3. **Credentials → Create credentials → OAuth client ID** → type **Web application**.
   Under **Authorized redirect URIs** add exactly: `https://replyloop-xxxx.onrender.com/auth/google/callback`
   (your Render address). For testing on your computer, also add `http://localhost:8000/auth/google/callback`.
4. Copy the **Client ID** and **Client secret** into Render → your service → **Environment**:
   `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` → Save (Render redeploys). Never paste them into chat or GitHub.
5. Open the app: a **Continue with Google** button appears on the sign-in page. Your Google email must be the same as
   `ADMIN_EMAIL` (or a person you added in Settings).

Notes: the button only shows when both values are set. If you use a custom domain instead of `onrender.com`,
set `PUBLIC_URL` to it and use that address in step 3. On an iPhone home-screen app, Google opens in a small browser
window first; if it doesn't come back into the app, sign in with your password once there. You stay signed in for 30 days.

---

## Step 3 · Install it on your phone, then on other phones

Open your `https://…onrender.com` address on the phone and sign in.

- **Android (Chrome):** ⋮ menu → **Install app** (or **Add to Home screen**). In the app, *Settings → Install on your phone* also shows an Install button.
- **iPhone (Safari, not Chrome):** Share button → **Add to Home Screen**.

It gets the replyloop icon and opens full-screen without browser bars. Updates arrive automatically: there's no store.

**Other phones:** in the app, *Settings → People with access → Add person* (owner only). Give them the address,
their email and the password you set (or leave the password empty and they use **Continue with Google** with that Gmail); they sign in and install the same way. Anyone you remove is signed out everywhere.
There's no public sign-up, so nobody else can get in.

---

## Step 4 · Connect your Instagram accounts

Each account must be an Instagram **Professional** account (Business or Creator) and **public**
(Meta only sends comment notifications for public accounts).

1. **developers.facebook.com** → **My Apps** → **Create app** → type **Business**.
2. In the app: **Add product → Instagram → API setup with Instagram login**.
3. **Permissions** to request: `instagram_business_basic`, `instagram_business_manage_comments`, `instagram_business_manage_messages`,
   and `instagram_business_manage_insights` (for the Insights tab).
4. **Generate access tokens** → **Add account** → sign in with each of your Instagram accounts → **Generate token** → copy.
5. In replyloop: account menu (top right) → **Connect an Instagram account** → paste the token.
   Repeat for each account. Tokens are stored encrypted and refreshed automatically before they expire (60 days).
6. **Webhooks** (same Instagram setup page → *Configure webhooks*):
   - Callback URL: `https://replyloop-xxxx.onrender.com/webhook`
   - Verify token: the `VERIFY_TOKEN` value from Render (Render → your service → **Environment**)
   - Subscribe to: **comments**, **messages**, **messaging_postbacks**
7. **App secret**: Meta → **App settings → Basic → App secret** → copy into Render as `APP_SECRET`.
   Also set `PRIVACY_CONTACT` (an email or @handle) → **Save changes** (Render redeploys).
8. **Make the Meta app Live**: Meta asks for a *Privacy Policy URL* first. Use
   `https://replyloop-xxxx.onrender.com/privacy` (the app serves this page). Then switch **App mode → Live**.
9. In replyloop, test with a second Instagram account: comment on your post while the account is in **Test mode**
   and check the inbox. When it looks right: **Go live**.

### About Meta's access levels (read this)
Meta's docs disagree with each other. One page says apps used only for accounts you own need just
**Standard Access**. The webhook page says comment and message webhooks need **Advanced Access** and
**Business Verification**. So replyloop doesn't rely on comment webhooks alone:

- A **backup checker** looks for new comments on your 5 newest posts every 3 minutes (`POLL_SECONDS`, `POLL_POSTS`)
  and answers anything the webhook missed. It works with Standard Access. Worst case, replies arrive a few minutes late.
- The followers-only **button** still needs the messages webhook to learn about taps. If taps never reach the
  inbox, that's the sign Meta wants Advanced Access for your app (App Review). Normal DMs and public replies keep working.

---

## Language (فارسی / English)

- The app opens in **Persian** (right-to-left) by default. Switch to English on the sign-in page or in **Settings → Appearance → Language**. The choice is saved per phone/browser.
- Persian mode uses everyday Persian ("پست‌ها و ریلزها", "دایرکت", "فالوورها"), **English digits**, and **Shamsi dates**.
- The ready-made follower DM texts (headline, button, "not following yet" message) start in Persian. Change them any time in Settings or per automation.
- Keywords can be Persian, English or Turkish. Separate them with a comma — the Persian comma (،) works too. ي/ی and ك/ک are treated as the same letter.
- The privacy page stays in English because Meta's reviewers read it.

## Everyday use
- **Posts**: tap a post to give it its own automations. Use the arrows to set their order (the first match wins).
- **Automations**: rules for every post.
- **Inbox**: every comment and what happened, step by step. Filters for *Waiting*, *DM sent*, *Errors*…
- **Insights** (7 or 30 days, per account):
  - *Account*: views, reach, interactions, accounts engaged, link taps, net follows, followers chart, reach per day, audience
    (countries, cities, age, gender; Instagram needs 100+ followers for audience and follows data).
  - *Posts & Reels*: your latest 25 ranked by views, reach, engagement, saves or shares (+ Reels watch time).
  - *Stories*: Instagram deletes story stats after 24 hours, so the app saves them every hour while a story is live.
    History starts the day you connect; older stories can't be recovered. Stories with under 5 viewers have no stats.
  - *Bot impact*: comments answered, DMs delivered, and how many people followed because of the follow button, per automation.
  - Numbers are organic only and can be up to 48 hours behind. Instagram data is cached (account 1h, posts 3h, audience 24h);
    use *Refresh from Instagram* for the latest.
  - Your follower chart is built by the app from a daily snapshot, so it fills in day by day after connecting.
- **Settings**: Test/Live per account, AI, ignore list, the default follower messages, theme, people, password.
- New accounts start in **Test mode**: the bot decides and logs everything, but sends nothing.

## Files
| File | What it does |
|---|---|
| `app.py` | Web server: pages, login, API, webhook |
| `bot.py` | Decides replies, runs the follower-button flow, refreshes tokens, backup checker |
| `store.py` · `db.py` | Database (SQLite on your computer, Supabase Postgres online) |
| `google_auth.py` | Sign in with Google (only for emails that already have access) |
| `twofa.py` · `qr.py` | Two-step login codes, backup codes, and the setup QR code |
| `security.py` | Password hashing, sessions, login rate limit, token encryption |
| `instagram.py` | Instagram API calls |
| `rules.py` · `ai.py` | Keyword matching (Turkish/Persian-aware) and the AI fallback |
| `insights.py` | Insights: Instagram stats with caching, hourly story saving, bot impact, demo data |
| `i18n.py` · `static/i18n.js` | Persian wording for server messages and app screens (edit to change any word) |
| `static/` | The app you see: `index.html`, `app.js`, `app.css`, icons, `sw.js` + `manifest.webmanifest` (installable app) |
| `render.yaml` | One-click Render setup |

## Security notes
- **Only people you add can sign in.** There's no sign-up; Google sign-in also only works for emails on your list.
- **Roles** (*Settings → People with access*):
  - **Owner** (you, `ADMIN_EMAIL`): everything, including connecting/removing Instagram accounts, switching test/live and managing people.
  - **Editor:** automations, settings, inbox, insights, simulating comments.
  - **View only:** can look at everything, can't change anything.
- **Two-step login** (*Settings → Two-step login*): after the password (or Google), a 6-digit code from an authenticator app
  (Google Authenticator, Microsoft Authenticator, 1Password…). Turning it on signs out your other devices.
  You get 10 one-time **backup codes**: save them. Each code from the app works only once.
  - Someone you added lost their phone? *People with access →* key icon resets their two-step login.
  - **You** lost your phone and your backup codes? On Render, add the environment variable `RESET_2FA_EMAIL` = your email,
    let it redeploy, sign in with your password, then **delete `RESET_2FA_EMAIL`** and turn two-step login on again.
- **Signed-in devices** (*Settings*): see every phone/browser signed in to your login, and sign any of them out.
- Passwords are hashed (scrypt). Sessions are HttpOnly cookies. 5 wrong passwords or codes lock that email/IP for 15 minutes.
- Instagram tokens and two-step secrets are encrypted with `SECRET_KEY`. **Never change `SECRET_KEY`**, or you'll need to
  reconnect accounts and set up two-step login again.
- Webhooks are only accepted when signed by Meta with your `APP_SECRET`.
- Never share `.env`, your Supabase URL or tokens. Change the starting password in *Settings → Your password*.
