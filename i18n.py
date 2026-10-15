"""Translates the server's messages (errors, warnings) for the dashboard.
The dashboard sends its language in the X-Lang header: "fa" (default) or "en".
Persian here is everyday, spoken-style Persian, not formal/written Persian."""
import contextvars
import re

LANG: contextvars.ContextVar[str] = contextvars.ContextVar("lang", default="fa")

FIELDS = {
    "Email": "ایمیل", "Name": "اسم", "Public reply": "جواب زیر کامنت", "DM": "دایرکت", "Headline": "پیام اول",
    "Button text": "متن دکمه", "Not-following message": "پیام «هنوز فالو نکرده»", "Post info": "اطلاعات پست",
    "Brand voice": "لحن برند", "First message": "پیام اول", "Check-failed message": "پیام «چک نشد»",
    "Comment": "کامنت", "Username": "یوزرنیم", "Access token": "توکن دسترسی",
}

EXACT = {
    "Bad request": "درخواست اشتباهه.",
    "Invalid JSON": "درخواست اشتباهه.",
    "Please sign in.": "اول وارد شو.",
    "Only the owner can do this.": "فقط مالک می‌تونه این کار رو بکنه.",
    "Account not found.": "این اکانت پیدا نشد.",
    "Too many attempts. Wait 15 minutes and try again.": "دفعه‌های زیادی امتحان کردی. 15 دقیقه صبر کن و دوباره امتحان کن.",
    "Wrong email or password.": "ایمیل یا رمز اشتباهه.",
    "Your current password is wrong.": "رمز فعلیت اشتباهه.",
    "Use at least 10 characters.": "رمز باید حداقل 10 کاراکتر باشه.",
    "Enter a valid email.": "یه ایمیل درست وارد کن.",
    "That email already has access.": "این ایمیل از قبل دسترسی داره.",
    "You can't remove yourself.": "نمی‌تونی خودت رو حذف کنی.",
    "User not found.": "این نفر پیدا نشد.",
    "You have view-only access.": "تو فقط اجازه‌ی دیدن داری.",
    "This sign-in expired. Start again.": "وقت ورود تموم شد. از اول وارد شو.",
    "Too many wrong codes. Start again.": "چند بار کد اشتباه زدی. از اول وارد شو.",
    "That code isn't right. Check your authenticator app and try again.": "این کد درست نیست. اپ Authenticator رو چک کن و دوباره بزن.",
    "Choose a role.": "یه نقش انتخاب کن.",
    "The owner's access can't be changed here.": "دسترسی مالک رو اینجا نمیشه عوض کرد.",
    "Set SECRET_KEY on the server before turning on two-step login.": "قبل از روشن کردن ورود دو مرحله‌ای، SECRET_KEY رو روی سرور تنظیم کن.",
    "Two-step login is already on.": "ورود دو مرحله‌ای از قبل روشنه.",
    "Start the setup again.": "راه‌اندازی رو از اول شروع کن.",
    "Turn on two-step login first.": "اول ورود دو مرحله‌ای رو روشن کن.",
    "To sign out this device, use Sign out.": "برای خروج از همین دستگاه، از دکمه‌ی «خروج» استفاده کن.",
    "Device not found.": "این دستگاه پیدا نشد.",
    "Add at least one keyword.": "حداقل یه کلمه کلیدی اضافه کن.",
    "Add a public reply, a DM, or both.": "یه جواب زیر کامنت، یه دایرکت یا هر دو رو اضافه کن.",
    "The demo account can't go live.": "اکانت دمو نمی‌تونه فعال بشه.",
    "This account's token can't be read. Reconnect it first.": "توکن این اکانت خونده نمیشه. اول دوباره وصلش کن.",
    "This account's token can't be read. Reconnect it in Settings.": "توکن این اکانت خونده نمیشه. از تنظیمات دوباره وصلش کن.",
    "Set APP_SECRET and VERIFY_TOKEN on the server before going live.": "قبل از فعال کردن، APP_SECRET و VERIFY_TOKEN رو روی سرور تنظیم کن.",
    "Rule not found.": "این اتوماسیون پیدا نشد.",
    "ids must be a list of rule ids.": "درخواست اشتباهه.",
    "Not found.": "پیدا نشد.",
    "Simulation only works in test mode.": "شبیه‌سازی فقط تو حالت تست کار می‌کنه.",
    "This comment isn't waiting for a tap.": "این کامنت منتظر زدن دکمه نیست.",
    "days must be 7 or 30.": "بازه باید 7 یا 30 روز باشه.",
    "This token doesn't belong to an Instagram professional account.": "این توکن مال یه اکانت حرفه‌ای (Business یا Creator) اینستاگرام نیست.",
    "Saved token can't be read (SECRET_KEY changed?). Reconnect the account.":
        "توکن ذخیره‌شده خونده نمیشه (شاید SECRET_KEY عوض شده). اکانت رو دوباره وصل کن.",
    "Instagram didn't allow reading insights. Generate a new token with the instagram_business_manage_insights "
    "permission and reconnect the account in Settings.":
        "اینستاگرام اجازه خوندن آمار رو نداد. یه توکن جدید با دسترسی instagram_business_manage_insights بساز و از تنظیمات اکانت رو دوباره وصل کن.",
}

PATTERNS = [
    (r"^(.+) must be text\.$", lambda m: f"{_f(m[1])} باید متن باشه."),
    (r"^(.+) is required\.$", lambda m: f"{_f(m[1])} رو خالی نذار."),
    (r"^(.+) is too long \(max (\d+) characters\)\.$", lambda m: f"{_f(m[1])} خیلی طولانیه (حداکثر {m[2]} کاراکتر)."),
    (r"^(.+) must be true or false\.$", lambda m: "درخواست اشتباهه."),
    (r"^(.+) must be a list of text\.$", lambda m: "درخواست اشتباهه."),
    (r"^Too many or too long items in (.+)\.$", lambda m: "تعداد کلمه‌ها یا طولشون زیاده."),
    (r"^Instagram: (.+)$", lambda m: f"اینستاگرام: {m[1]}"),
    (r"^Connected, but turning on webhooks failed: (.+)\. Check the webhook setup in your Meta app\.$",
     lambda m: f"وصل شد، ولی روشن کردن وبهوک‌ها خطا داد: {m[1]}. تنظیمات وبهوک رو تو اپ متا چک کن."),
    (r"^Token refresh failed: (.+)$", lambda m: f"تمدید توکن خطا داد: {m[1]}"),
    (r"^Checking for new comments failed: (.+)$", lambda m: f"چک کردن کامنت‌های جدید خطا داد: {m[1]}"),
    (r"^Couldn't load posts from Instagram: (.+)$", lambda m: f"پست‌ها از اینستاگرام گرفته نشدن: {m[1]}"),
]
_COMPILED = [(re.compile(p, re.S), fn) for p, fn in PATTERNS]


def _f(name: str) -> str:
    return FIELDS.get(name, name)


def tr(text):
    """Translates a server message into the current request's language (Persian by default)."""
    if not text or not isinstance(text, str) or LANG.get() != "fa":
        return text
    if text in EXACT:
        return EXACT[text]
    for pat, fn in _COMPILED:
        m = pat.match(text)
        if m:
            return fn(m)
    return text


def set_from_header(value: str | None):
    LANG.set("en" if (value or "").lower().startswith("en") else "fa")
