<img src="assets/banner1.svg" alt="sobhan" width="100%">

<div align="center">

# 💬 ReplyLoop

### Answers Instagram comments, sends DMs, and keeps everything in one inbox

![Status](https://img.shields.io/badge/status-in%20development-orange?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Starlette](https://img.shields.io/badge/Starlette-1.0-009688?style=for-the-badge)
![Instagram](https://img.shields.io/badge/Instagram%20API-E4405F?style=for-the-badge&logo=instagram&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white)
![Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=black)
![Claude](https://img.shields.io/badge/Claude%20AI-D97757?style=for-the-badge&logo=anthropic&logoColor=white)

**🇮🇷 فارسی (RTL) · 🇬🇧 English · ☀️ Light · 🌙 Dark · 📱 Installable app**

</div>

---

## 💡 Why I built this

When a post asks people to comment a keyword ("لینک لطفا") to get a link, someone has to answer every one of those comments and send every DM by hand. Miss a few and those people are gone.

So I built my own private helper. It **answers comments on posts and reels**, **sends the DM** (optionally only to followers, with an "I'm following ✅" button), and shows every step in an **inbox**. It handles several Instagram accounts and installs on Android and iPhone like a normal app. 📲

```
someone comments on a post
  → this post's automations (top to bottom, first match wins)
  → automations for every post
  → AI reply (optional)
  → public reply and/or DM  ·  followers-only: DM with a button → they tap → follower? details : button again
```

---

## ✨ Features

### 🤖 Automations
- 📝 **Per post** automations, ordered with arrows (the first match wins), plus automations for **every post**
- 🔤 Keywords in **Persian, English or Turkish**, separated by a comma (the Persian comma ، works too); ي/ی and ك/ک count as the same letter
- 💌 **Public reply and/or DM**, with a **followers-only** mode: a DM with a button, then the details once they follow
- 🧠 Optional **AI reply** when no keyword matches
- 🧪 New accounts start in **Test mode**: the bot decides and logs everything but sends nothing, until you **Go live**

### 📥 Inbox
- 🗂️ Every comment and what happened, step by step
- 🔍 Filters for *Waiting*, *DM sent*, *Errors*…
- 🎮 **Simulate comment** and simulate a button tap, to test without Instagram

### 📊 Insights (7 or 30 days, per account)
- 👀 **Account:** views, reach, interactions, accounts engaged, link taps, net follows, a followers chart, reach per day and audience (countries, cities, age, gender; Instagram needs 100+ followers for audience and follows data)
- 🎬 **Posts & Reels:** your latest 25 ranked by views, reach, engagement, saves or shares, plus Reels watch time
- ⏳ **Stories:** Instagram deletes story stats after 24 hours, so the app saves them every hour while a story is live. History starts the day you connect, and stories with under 5 viewers have no stats.
- 📈 **Bot impact:** comments answered, DMs delivered, and how many people followed because of the follow button, per automation
- 🕒 Numbers are organic only and can be up to 48 hours behind. Instagram data is cached (account 1h, posts 3h, audience 24h); use *Refresh from Instagram* for the latest. The follower chart fills in day by day from a daily snapshot.

### 🌐 Language
- 🇮🇷 Opens in **Persian** (right-to-left) by default, with everyday wording ("پست‌ها و ریلزها", "دایرکت", "فالوورها"), **English digits** and **Shamsi dates**
- 🇬🇧 Switch to English on the sign-in page or in **Settings → Appearance → Language** (saved per phone or browser)
- ✏️ The ready-made follower DM texts start in Persian; change them in Settings or per automation
- 📄 The privacy page stays in English because Meta's reviewers read it

---

## 🔒 Security

- 🚪 **Only people you add can sign in.** There's no sign-up, and Google sign-in only works for emails on your list.
- 👥 **Roles** (*Settings → People with access*):
  - 👑 **Owner** (you, `ADMIN_EMAIL`): everything, including connecting or removing Instagram accounts, switching test/live and managing people
  - ✏️ **Editor:** automations, settings, inbox, insights, simulating comments
  - 👁️ **View only:** can look at everything, can't change anything
- 🔐 **Two-step login** (*Settings → Two-step login*): after the password (or Google), a 6-digit code from an authenticator app (Google Authenticator, Microsoft Authenticator, 1Password…). Turning it on signs out your other devices. You get 10 one-time **backup codes**: save them.
  - Someone you added lost their phone? *People with access →* the key icon resets their two-step login.
  - **You** lost your phone and your backup codes? On Render, add `RESET_2FA_EMAIL` = your email, let it redeploy, sign in with your password, then **delete `RESET_2FA_EMAIL`** and turn two-step login on again.
- 📱 **Signed-in devices** (*Settings*): see every phone and browser signed in to your login, and sign any of them out.
- 🧂 Passwords are hashed with scrypt. Sessions are HttpOnly cookies. 5 wrong passwords or codes lock that email/IP for 15 minutes.
- 🗝️ Instagram tokens and two-step secrets are encrypted with `SECRET_KEY`. **Never change `SECRET_KEY`**, or you'll need to reconnect accounts and set up two-step login again.
- ✅ Webhooks are only accepted when signed by Meta with your `APP_SECRET`.
- 🙈 Never share `.env`, your Supabase URL or tokens. Change the starting password in *Settings → Your password*.

---

## 🗂️ Structure

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

---

## 🚀 Getting started

### 1️⃣ Try it on your computer (10 minutes)

You need Python 3.11+.

```bash
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

Open **http://localhost:8000**, sign in, tap **Try a demo account**, open the pistachio reel and type `لینک لطفا` in **Try a comment** → **Simulate comment**. You'll land in the inbox, where you can simulate the person tapping the button as a follower or not.

> 💡 On your computer the data is saved in `replyloop.db`. Phones only install apps from `https://` addresses, which is what step 2 is for.

### 2️⃣ Put it online for free (about 30 minutes, once)

You'll use three free services: **GitHub** (stores the code), **Supabase** (the database) and **Render** (runs the app).

**🐙 GitHub**
1. Create a **private** repository and push this project to it. `.env` and `replyloop.db` are ignored on purpose, so your passwords never end up on GitHub.

**🗄️ Supabase (database)**
1. supabase.com → **New project**. Pick a region close to you (e.g. *Frankfurt*). Set a **database password** and save it.
2. Top bar **Connect** → **Session pooler** → copy the URI. It looks like `postgresql://postgres.abcd:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres`. Replace `[YOUR-PASSWORD]` with your database password. This is your `DATABASE_URL`. (Use the *Session pooler*, not *Direct connection*: Render can't reach the direct one.)

The app creates its tables by itself on first start.

**☁️ Render (runs the app)**
1. render.com → sign up with GitHub → **New** → **Blueprint** → choose your repo.
2. Render reads `render.yaml` and asks for:
   - `DATABASE_URL`: from Supabase
   - `ADMIN_EMAIL` / `ADMIN_PASSWORD`: your login
   - `APP_SECRET`, `ANTHROPIC_API_KEY`, `PRIVACY_CONTACT`: leave empty for now (step 4)

   `SECRET_KEY` and `VERIFY_TOKEN` are generated for you.
3. **Apply**. The first deploy takes a few minutes. Your app gets an address like `https://replyloop-xxxx.onrender.com`.

**⏰ Keep it awake**

Render's free plan puts the app to sleep after 15 minutes without visitors, and waking up takes about a minute. That's too slow for a bot, so ping it: at cron-job.org create a cronjob for `https://replyloop-xxxx.onrender.com/health` every **10 minutes**. (750 free hours a month on Render covers running all month.)

**🔑 Sign in with Google (optional, ~10 minutes)**
1. **console.cloud.google.com** → create a project (e.g. *replyloop*).
2. **APIs & Services → OAuth consent screen**: app name *replyloop*, your email as support and developer contact, audience **External**, scopes **openid** and **email** only. In **Testing** mode, add every Gmail that will sign in under **Test users**, or press **Publish app** (no Google review is needed for these scopes).
3. **Credentials → Create credentials → OAuth client ID** → **Web application**. Under **Authorized redirect URIs** add `https://replyloop-xxxx.onrender.com/auth/google/callback`, and `http://localhost:8000/auth/google/callback` for testing on your computer.
4. Copy the **Client ID** and **Client secret** into Render → your service → **Environment** as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. Never paste them into chat or GitHub.
5. A **Continue with Google** button appears on the sign-in page. Your Google email must match `ADMIN_EMAIL` or a person you added.

> 💡 The button only shows when both values are set. With a custom domain, set `PUBLIC_URL` to it and use that address in step 3. On an iPhone home-screen app, Google opens in a small browser window first; if it doesn't come back into the app, sign in with your password once there. You stay signed in for 30 days.

### 3️⃣ Install it on your phone

Open your `https://…onrender.com` address on the phone and sign in.

- 🤖 **Android (Chrome):** ⋮ menu → **Install app** (or **Add to Home screen**). *Settings → Install on your phone* also shows an Install button.
- 🍎 **iPhone (Safari, not Chrome):** Share button → **Add to Home Screen**.

It opens full-screen with the ReplyLoop icon, and updates arrive automatically. To add other phones, go to *Settings → People with access → Add person* (owner only). Give them the address, their email and a password (or leave it empty so they use **Continue with Google**). Anyone you remove is signed out everywhere.

### 4️⃣ Connect your Instagram accounts

Each account must be an Instagram **Professional** account (Business or Creator) and **public** (Meta only sends comment notifications for public accounts).

1. **developers.facebook.com** → **My Apps** → **Create app** → type **Business**.
2. **Add product → Instagram → API setup with Instagram login**.
3. Request `instagram_business_basic`, `instagram_business_manage_comments`, `instagram_business_manage_messages` and `instagram_business_manage_insights` (for Insights).
4. **Generate access tokens** → **Add account** → sign in with each Instagram account → **Generate token** → copy.
5. In ReplyLoop: account menu (top right) → **Connect an Instagram account** → paste the token. Tokens are stored encrypted and refreshed automatically before they expire (60 days).
6. **Webhooks** (*Configure webhooks* on the same page):
   - Callback URL: `https://replyloop-xxxx.onrender.com/webhook`
   - Verify token: the `VERIFY_TOKEN` value from Render → **Environment**
   - Subscribe to **comments**, **messages**, **messaging_postbacks**
7. **App secret**: Meta → **App settings → Basic → App secret** → copy into Render as `APP_SECRET`. Also set `PRIVACY_CONTACT` (an email or @handle).
8. **Make the Meta app Live**: use `https://replyloop-xxxx.onrender.com/privacy` as the *Privacy Policy URL*, then switch **App mode → Live**.
9. Test with a second Instagram account while yours is in **Test mode** and check the inbox. When it looks right: **Go live**.

> ⚠️ **About Meta's access levels:** Meta's docs disagree. One page says apps for accounts you own need only **Standard Access**; the webhook page says comment and message webhooks need **Advanced Access** and **Business Verification**. So a **backup checker** looks for new comments on your 5 newest posts every 3 minutes (`POLL_SECONDS`, `POLL_POSTS`) and answers anything the webhook missed. The followers-only **button** still needs the messages webhook; if taps never reach the inbox, Meta wants Advanced Access (App Review). Normal DMs and public replies keep working.

---

## 🗺️ Roadmap

- [x] Roles: Owner, Editor, View only
- [x] Two-step login with backup codes
- [x] Signed-in devices list

---

## 📜 License

Free to use **with credit**. See [LICENSE.md](LICENSE.md).

<div align="center">

Made with ☕ and late nights in Istanbul by **[Sobhan Mirgholami (Co$mo)](https://sobhan-cosmo.vercel.app)**

</div>
