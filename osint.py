import os
import re
import sqlite3
import datetime
import asyncio
import urllib.parse
from io import BytesIO

import requests
import qrcode
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

load_dotenv()

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@owner")
CHANNEL_1 = os.getenv("CHANNEL_1", "@ch1")
CHANNEL_2 = os.getenv("CHANNEL_2", "@ch2")

UPI_ID = os.getenv("UPI_ID", "")
UPI_NAME = os.getenv("UPI_NAME", "")
SRC_PRICE = int(os.getenv("SRC_PRICE", "1499"))

TG_NUM_API_URL = os.getenv("TG_NUM_API_URL", "")
TG_NUM_API_KEY = os.getenv("TG_NUM_API_KEY", "")
AADHAAR_FAMILY_API = os.getenv("AADHAAR_FAMILY_API", "")
IFSC_API_URL = os.getenv("IFSC_API_URL", "")
IFSC_API_KEY = os.getenv("IFSC_API_KEY", "")

DEFAULT_NUM_API = os.getenv("DEFAULT_NUM_API", "")
DEFAULT_AADHAR_API = os.getenv("DEFAULT_AADHAR_API", "")
AUTO_DELETE_SECONDS = int(os.getenv("AUTO_DELETE_SECONDS", "30"))

PLANS = {
    "10": {"credits": 10, "price": 30, "label": "10 Points"},
    "25": {"credits": 25, "price": 70, "label": "25 Points"},
    "50": {"credits": 50, "price": 130, "label": "50 Points"},
    "100": {"credits": 100, "price": 250, "label": "100 Points"},
}

SMALL_CAPS_MAP = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ꜰ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ꜰ', 'G': 'ɢ',
    'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ',
    'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ', 'U': 'ᴜ',
    'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
}
def scp(text): return ''.join(SMALL_CAPS_MAP.get(ch, ch) for ch in str(text))
LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━"

# --- DB ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, credits INTEGER, total_searches INTEGER DEFAULT 0,
        join_date TEXT, refer_by INTEGER DEFAULT 0, join_bonus_claimed INTEGER DEFAULT 0,
        has_referred INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        search_type TEXT, search_query TEXT, search_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS src_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        status TEXT DEFAULT 'pending', created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pending_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan_key TEXT,
        status TEXT DEFAULT 'waiting_screenshot', created_at TEXT)''')
    conn.commit()
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (SUPER_ADMIN_ID,))
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('num_api', ?)", (DEFAULT_NUM_API,))
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('aadhar_api', ?)", (DEFAULT_AADHAR_API,))
    conn.commit()
    conn.close()
init_db()

def get_setting(key):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    val = c.fetchone(); conn.close()
    return val[0] if val else ""

def get_user(user_id):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("SELECT credits, total_searches, join_date, refer_by, join_bonus_claimed, has_referred FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone(); conn.close(); return res

def add_user(user_id, refer_by=0):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, credits, join_date, refer_by, join_bonus_claimed) VALUES (?, ?, ?, ?, 1)", (user_id, 2, date, refer_by))
        conn.commit()
        if refer_by != 0:
            c.execute("SELECT has_referred FROM users WHERE user_id=?", (refer_by,))
            ref_status = c.fetchone()
            if ref_status and ref_status[0] == 0:
                c.execute("UPDATE users SET credits = credits + 2, has_referred = 1 WHERE user_id=?", (refer_by,))
                c.execute("UPDATE users SET credits = credits + 2 WHERE user_id=?", (user_id,))
                conn.commit()
    conn.close()

def adjust_credits(user_id, amount):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
    conn.commit(); conn.close()

def deduct_credit(user_id):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("UPDATE users SET credits = credits - 1, total_searches = total_searches + 1 WHERE user_id=? AND credits > 0", (user_id,))
    conn.commit(); conn.close()

def log_search(user_id, search_type, query):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO search_history (user_id, search_type, search_query, search_date) VALUES (?, ?, ?, ?)", (user_id, search_type, query, date))
    conn.commit(); conn.close()

def is_admin(user_id):
    if user_id == SUPER_ADMIN_ID: return True
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("SELECT user_id FROM admins WHERE user_id=?", (user_id,))
    res = c.fetchone(); conn.close(); return bool(res)

def is_banned(user_id):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("SELECT user_id FROM banned_users WHERE user_id=?", (user_id,))
    res = c.fetchone(); conn.close(); return bool(res)

# --- PAYMENT HELPERS ---
def create_pending_payment(user_id, plan_key):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("INSERT INTO pending_payments (user_id, plan_key, created_at) VALUES (?, ?, ?)",
              (user_id, plan_key, datetime.datetime.now().isoformat()))
    pid = c.lastrowid
    conn.commit(); conn.close(); return pid

def set_pending_screenshot(pid):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("UPDATE pending_payments SET status='waiting_admin' WHERE id=?", (pid,))
    conn.commit(); conn.close()

def get_pending_payment(pid):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("SELECT user_id, plan_key, status FROM pending_payments WHERE id=?", (pid,))
    res = c.fetchone(); conn.close(); return res

def set_payment_status(pid, status):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("UPDATE pending_payments SET status=? WHERE id=?", (status, pid))
    conn.commit(); conn.close()

# --- UPI QR ---
def generate_upi_qr(upi_id, payee_name, amount, note=""):
    params = {"pa": upi_id, "pn": payee_name, "am": str(amount), "cu": "INR"}
    if note: params["tn"] = note
    upi_string = "upi://pay?" + urllib.parse.urlencode(params).replace("+", "%20")
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(upi_string); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return buf, upi_string

# --- FORCE JOIN ---
async def is_user_joined(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id): return True
    try:
        m1 = await ctx.bot.get_chat_member(chat_id=CHANNEL_1, user_id=user_id)
        m2 = await ctx.bot.get_chat_member(chat_id=CHANNEL_2, user_id=user_id)
        return m1.status in ['member','administrator','creator'] and m2.status in ['member','administrator','creator']
    except: return False

async def auto_delete_message(ctx, chat_id, message_id):
    await asyncio.sleep(AUTO_DELETE_SECONDS)
    try: await ctx.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except: pass

# --- API ---
def fetch_num(api_url, query):
    try:
        r = requests.get(f"{api_url}{query}", timeout=60).json()
        return r if r.get("success") and r.get("count", 0) > 0 else None
    except: return None

def fetch_tg(tg_id):
    try:
        r = requests.get(f"{TG_NUM_API_URL}?key={TG_NUM_API_KEY}&userid={tg_id}", timeout=25).json()
        return r if r.get("status") == True else None
    except: return None

def fetch_family(aadhar):
    try:
        r = requests.get(f"{AADHAAR_FAMILY_API}?id={aadhar}", timeout=25).json()
        return r if r.get("details", {}).get("rd") == "Success" else None
    except: return None

def fetch_ifsc(ifsc):
    try:
        r = requests.get(f"{IFSC_API_URL}?api_key={IFSC_API_KEY}&service=ifsc_info&input={ifsc}", timeout=25).json()
        return r if r.get("success") == True else None
    except: return None

# --- KEYBOARDS ---
def get_main_keyboard(user_id):
    kb = [
        [KeyboardButton("🟢 📱 NUMBER INFO"), KeyboardButton("🔵 🆔 AADHAAR INFO")],
        [KeyboardButton("🟣 ✈️ TG TO NUMBER"), KeyboardButton("🟠 👨‍👩‍👧‍👦 FAMILY INFO")],
        [KeyboardButton("🔴 🏦 IFSC CODE")],
        [KeyboardButton("🟡 💰 BALANCE"), KeyboardButton("🟢 🛒 BUY CREDITS")],
        [KeyboardButton("💻 ʙᴜʏ sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ"), KeyboardButton("🔵 🔗 REFERRAL")],
    ]
    if is_admin(user_id): kb.append([KeyboardButton("👑 ADMIN PANEL")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("🔴 🚫 CANCEL")]], resize_keyboard=True)

def get_admin_keyboard():
    kb = [
        [KeyboardButton("🟡 📣 BROADCAST"), KeyboardButton("🔵 📊 STATS")],
        [KeyboardButton("🟢 💎 ADD POINTS"), KeyboardButton("🔴 ❌ REMOVE POINTS")],
        [KeyboardButton("♾️ UNLIMITED CREDITS")],
        [KeyboardButton("🔴 🚫 BAN USER"), KeyboardButton("🟢 ✅ UNBAN USER")],
        [KeyboardButton("🟣 📊 RECORDS"), KeyboardButton("🔵 ⚙️ API STATUS")],
        [KeyboardButton("💻 sʀᴄ ʀᴇǫᴜᴇsᴛs"), KeyboardButton("🟠 🔗 CHANGE API")],
        [KeyboardButton("🏠 MAIN MENU")],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

async def send_no_credit_msg(update, ctx):
    kb = [
        [InlineKeyboardButton("💎 10 CR - ₹30", callback_data="buy_10")],
        [InlineKeyboardButton("💎 25 CR - ₹70", callback_data="buy_25")],
        [InlineKeyboardButton("💎 50 CR - ₹130", callback_data="buy_50")],
        [InlineKeyboardButton("💎 100 CR - ₹250", callback_data="buy_100")],
    ]
    text = "❌ **0 Credits!**\n\nPehle credit buy kar fir search kar ladle 😎🤌\n\n👇 *Select a plan below:*"
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- COMMANDS ---
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banned(user_id):
        await update.message.reply_text("🚫 **You are banned.**", parse_mode="Markdown"); return
    refer_by = 0
    if ctx.args and ctx.args[0].isdigit(): refer_by = int(ctx.args[0])
    add_user(user_id, refer_by)
    user = get_user(user_id)
    if not await is_user_joined(update, ctx):
        kb = [
            [InlineKeyboardButton("🔴 Join Channel 1", url=f"https://t.me/{CHANNEL_1.replace('@', '')}")],
            [InlineKeyboardButton("🔴 Join Channel 2", url=f"https://t.me/{CHANNEL_2.replace('@', '')}")],
            [InlineKeyboardButton("🟢 ✅ VERIFY JOIN", callback_data="verify_join")],
        ]
        await update.message.reply_text(
            f"╭━━━━━━━━━━━━━━━━━━╮\n   ⚠️ *{scp('ACCESS DENIED')}* ⚠️\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
            f"Bhai pehle dono channel join kar, fir verify kar. Uske baad hi bot chalega!",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return
    text = (
        f"╭━━━━━━━━━━━━━━━━━━╮\n   🔥 *{scp('PREMIUM OSINT BOT')}* 🔥\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
        f"✨ *{scp('Welcome')}, {update.effective_user.first_name}!*\n\n"
        f"⭐ *{scp('User ID')}:* `{user_id}`\n💎 *{scp('Credits')}:* {user[0]}\n"
        f"👑 *{scp('Owner')}:* <b>{OWNER_USERNAME}</b>\n\n{LINE}\n"
        f"🛡️ *{scp('Services')}:*\n• 📱 {scp('Number Info')}\n• 🆔 {scp('Aadhaar Info')}\n"
        f"• ✈️ {scp('TG to Number')}\n• 👨‍👩‍👧‍👦 {scp('Family Info')}\n• 🏦 {scp('IFSC Code')}\n\n{LINE}\n"
        f"⚡ *{scp('Cost')}:* 1 {scp('Credit/Search')}\n\n👇 *{scp('Use buttons below to start')}*"
    )
    await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")

async def verify_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_user_joined(update, ctx):
        try: await query.message.delete()
        except: pass
        await start(update, ctx)
    else:
        await query.answer("❌ Bhai pehle dono channel join kar, fir verify kar!", show_alert=True)

async def admin_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        kb = [[InlineKeyboardButton("🟢 💬 Message Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]]
        await update.message.reply_text(
            f"╭━━━━━━━━━━━━━━━━━━╮\n   👑 *{scp('CONTACT ADMIN')}* 👑\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
            f"Click the button below to directly message the owner.",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text("⚙️ **Admin Control Panel**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

# --- ADMIN PROMPTS ---
async def admin_add_credits_start(update, ctx):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("💎 **Add Credits**\nFormat: `USER_ID AMOUNT`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

async def admin_remove_credits_start(update, ctx):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("❌ **Remove Credits**\nFormat: `USER_ID AMOUNT`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

async def admin_ban_start(update, ctx):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("🚫 **Ban User**\nFormat: `USER_ID`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

async def admin_unban_start(update, ctx):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("✅ **Unban User**\nFormat: `USER_ID`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

async def admin_broadcast_start(update, ctx):
    if not is_admin(update.effective_user.id): return
    ctx.user_data['awaiting_broadcast'] = True
    await update.message.reply_text("📣 **Broadcast**\n\nType the message to send to all users.", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

async def admin_change_api_start(update, ctx):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("🔗 **API Settings**\n\n`setnumapi URL`\n`setaadharapi URL`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

async def admin_stats(update, ctx):
    if not is_admin(update.effective_user.id): return
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_searches = c.execute("SELECT COALESCE(SUM(total_searches),0) FROM users").fetchone()[0]
    conn.close()
    await update.message.reply_text(f"📊 **Bot Statistics**\n\n👥 Total Users: {total_users}\n🔍 Total Searches: {total_searches}", parse_mode="Markdown", reply_markup=get_admin_keyboard())

async def admin_records(update, ctx):
    if not is_admin(update.effective_user.id): return
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("SELECT user_id, COUNT(id) FROM search_history GROUP BY user_id ORDER BY COUNT(id) DESC LIMIT 20")
    users = c.fetchall(); conn.close()
    if not users:
        await update.message.reply_text("❌ **No search records found.**", parse_mode="Markdown"); return
    text = f"╭━━━━━━━━━━━━━━━━━━╮\n   🟣 *{scp('SEARCH RECORDS')}* 🟣\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
    kb = []
    for uid, count in users:
        text += f"👤 ID: `{uid}` - {count} Searches\n"
        kb.append([InlineKeyboardButton(f"🔍 See {uid}'s History", callback_data=f"history_{uid}")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def admin_api_status(update, ctx):
    if not is_admin(update.effective_user.id): return
    msg = await update.message.reply_text("⚙️ **Checking APIs Status...**", parse_mode="Markdown")
    num_status = "🔴 Down"; aadhar_status = "🔴 Down"
    try:
        r = requests.get(f"{get_setting('num_api')}9876543210", timeout=15)
        if r.status_code == 200: num_status = "🟢 Online"
    except: pass
    try:
        r = requests.get(f"{get_setting('aadhar_api')}123456789012", timeout=15)
        if r.status_code == 200: aadhar_status = "🟢 Online"
    except: pass
    text = (
        f"╭━━━━━━━━━━━━━━━━━━╮\n   ⚙️ *{scp('API STATUS')}* ⚙️\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
        f"📱 *Number API:* {num_status}\n🆔 *Aadhar API:* {aadhar_status}\n\n🔄 _Ping Check Complete_"
    )
    await msg.edit_text(text, parse_mode="Markdown")

# --- SCREENSHOT UPLOAD ---
async def ask_screenshot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_key = query.data.split("_")[1]
    user_id = update.effective_user.id
    pid = create_pending_payment(user_id, plan_key)
    ctx.user_data['pending_pid'] = pid
    plan = PLANS[plan_key]
    await query.message.reply_text(
        f"📤 **Ab apna payment screenshot bhejo.**\n\n"
        f"Plan: {plan['credits']} Credits (₹{plan['price']})\n\n"
        f"Screenshot bhejte hi owner ko chala jayega verify ke liye.",
        parse_mode="Markdown")

async def handle_screenshot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pid = ctx.user_data.get('pending_pid')
    if not pid:
        await update.message.reply_text("⚠️ Pehle koi plan select karo (Buy Credits me jaakar).")
        return
    payment = get_pending_payment(pid)
    if not payment:
        await update.message.reply_text("⚠️ Payment record nahi mila. Dobara try karo.")
        return
    p_user_id, plan_key, status = payment
    if p_user_id != user_id:
        await update.message.reply_text("⚠️ Ye payment aapki nahi hai.")
        return
    set_pending_screenshot(pid)
    plan = PLANS[plan_key]
    kb = [
        [InlineKeyboardButton("✅ Approve & Add Credits", callback_data=f"approve_{pid}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{pid}")],
    ]
    caption = (
        f"💰 **NEW PAYMENT SCREENSHOT**\n\n"
        f"👤 User ID: `{user_id}`\n"
        f"💎 Plan: {plan['credits']} Credits\n"
        f"💵 Amount: ₹{plan['price']}\n"
        f"🆔 Payment ID: `{pid}`"
    )
    await update.message.reply_text("✅ Screenshot mil gaya! Owner verify karega, thoda wait karo.")
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("SELECT user_id FROM admins"); admins = [row[0] for row in c.fetchall()]; conn.close()
    admins.append(SUPER_ADMIN_ID); admins = list(set(admins))
    for admin_id in admins:
        try:
            await ctx.bot.send_photo(chat_id=admin_id, photo=update.message.photo[-1].file_id,
                                     caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except Exception as e:
            print(f"Admin {admin_id} send error: {e}")
    ctx.user_data['pending_pid'] = None

# --- MESSAGE HANDLER ---
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if is_banned(user_id): return

    if text in ["🔴 🚫 CANCEL", "🏠 MAIN MENU"]:
        ctx.user_data['awaiting_broadcast'] = False
        await start(update, ctx); return

    # Broadcast
    if is_admin(user_id) and ctx.user_data.get('awaiting_broadcast'):
        ctx.user_data['awaiting_broadcast'] = False
        conn = sqlite3.connect('users.db'); c = conn.cursor()
        c.execute("SELECT user_id FROM users"); all_users = [row[0] for row in c.fetchall()]; conn.close()
        sent = 0; failed = 0
        for uid in all_users:
            try:
                await ctx.bot.send_message(chat_id=uid, text=text)
                sent += 1
            except: failed += 1
        await update.message.reply_text(f"📣 **Broadcast done!**\n✅ Sent: {sent}\n❌ Failed: {failed}", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
        return

    # Admin commands
    if is_admin(user_id):
        if text == "👑 ADMIN PANEL": await admin_command(update, ctx); return
        elif text == "♾️ UNLIMITED CREDITS":
            adjust_credits(user_id, 9999999)
            await update.message.reply_text("♾️ **Unlimited Credits Added!**", reply_markup=get_admin_keyboard()); return
        elif text == "🟠 🔗 CHANGE API": await admin_change_api_start(update, ctx); return
        elif text == "🟣 📊 RECORDS": await admin_records(update, ctx); return
        elif text == "🔵 📊 STATS": await admin_stats(update, ctx); return
        elif text == "🔵 ⚙️ API STATUS": await admin_api_status(update, ctx); return
        elif text == "🟢 💎 ADD POINTS": await admin_add_credits_start(update, ctx); return
        elif text == "🔴 ❌ REMOVE POINTS": await admin_remove_credits_start(update, ctx); return
        elif text == "🔴 🚫 BAN USER": await admin_ban_start(update, ctx); return
        elif text == "🟢 ✅ UNBAN USER": await admin_unban_start(update, ctx); return
        elif text == "🟡 📣 BROADCAST": await admin_broadcast_start(update, ctx); return

        # API change commands
        if text.startswith("setnumapi "):
            new_url = text.split(" ", 1)[1].strip()
            conn = sqlite3.connect('users.db'); c = conn.cursor()
            c.execute("UPDATE settings SET value=? WHERE key='num_api'", (new_url,)); conn.commit(); conn.close()
            await update.message.reply_text(f"✅ Number API updated to:\n`{new_url}`", reply_markup=get_admin_keyboard(), parse_mode="Markdown"); return
        if text.startswith("setaadharapi "):
            new_url = text.split(" ", 1)[1].strip()
            conn = sqlite3.connect('users.db'); c = conn.cursor()
            c.execute("UPDATE settings SET value=? WHERE key='aadhar_api'", (new_url,)); conn.commit(); conn.close()
            await update.message.reply_text(f"✅ Aadhar API updated to:\n`{new_url}`", reply_markup=get_admin_keyboard(), parse_mode="Markdown"); return

        # Admin text parsing (only when in admin flow, safer)
        if text.startswith("ADD ") or text.startswith("REMOVE ") or text.startswith("BAN ") or text.startswith("UNBAN "):
            parts = text.split()
            try:
                if parts[0] == "ADD" and len(parts) == 3:
                    uid, amt = int(parts[1]), int(parts[2]); adjust_credits(uid, amt)
                    await update.message.reply_text(f"✅ Added {amt} credits to `{uid}`", reply_markup=get_admin_keyboard(), parse_mode="Markdown"); return
                if parts[0] == "REMOVE" and len(parts) == 3:
                    uid, amt = int(parts[1]), int(parts[2]); adjust_credits(uid, -amt)
                    await update.message.reply_text(f"❌ Removed {amt} credits from `{uid}`", reply_markup=get_admin_keyboard(), parse_mode="Markdown"); return
                if parts[0] == "BAN" and len(parts) == 2:
                    uid = int(parts[1])
                    conn = sqlite3.connect('users.db'); conn.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (uid,)); conn.commit(); conn.close()
                    await update.message.reply_text(f"🚫 User `{uid}` banned.", reply_markup=get_admin_keyboard(), parse_mode="Markdown"); return
                if parts[0] == "UNBAN" and len(parts) == 2:
                    uid = int(parts[1])
                    conn = sqlite3.connect('users.db'); conn.execute("DELETE FROM banned_users WHERE user_id=?", (uid,)); conn.commit(); conn.close()
                    await update.message.reply_text(f"✅ User `{uid}` unbanned.", reply_markup=get_admin_keyboard(), parse_mode="Markdown"); return
            except: pass

    if text == "🟡 💰 BALANCE":
        user = get_user(user_id)
        await update.message.reply_text(f"💎 **Balance:** {user[0]} Credits\n🔍 **Searches:** {user[1]}", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown"); return

    if text == "🟢 🛒 BUY CREDITS":
        kb = [
            [InlineKeyboardButton("💎 10 CR - ₹30", callback_data="buy_10")],
            [InlineKeyboardButton("💎 25 CR - ₹70", callback_data="buy_25")],
            [InlineKeyboardButton("💎 50 CR - ₹130", callback_data="buy_50")],
            [InlineKeyboardButton("💎 100 CR - ₹250", callback_data="buy_100")],
        ]
        buy_text = (
            f"╭━━━━━━━━━━━━━━━━━━╮\n   🛒 *{scp('BUY CREDITS')}* 🛒\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
            f"Select a plan below:\n• 💎 10 Credits = ₹30\n• 💎 25 Credits = ₹70\n• 💎 50 Credits = ₹130\n• 💎 100 Credits = ₹250\n\n"
            f"👇 *To purchase, click a plan:*"
        )
        await update.message.reply_text(buy_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"); return

    if text == "💻 ʙᴜʏ sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ":
        conn = sqlite3.connect('users.db')
        conn.execute("INSERT INTO src_requests (user_id, created_at) VALUES (?, ?)", (user_id, datetime.datetime.now().isoformat()))
        conn.commit(); conn.close()
        kb = [[InlineKeyboardButton("💬 Message Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]]
        src_text = (
            f"╭━━━━━━━━━━━━━━━━━━╮\n   💻 *{scp('BUY SOURCE CODE')}* 💻\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
            f"Get the full source code!\n\n👑 **Price:** ₹{SRC_PRICE}\n\n👇 *Click below to message Owner:*"
        )
        await update.message.reply_text(src_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"); return

    if text == "🔵 🔗 REFERRAL":
        bot_info = await ctx.bot.get_me()
        user = get_user(user_id)
        if user[5] == 1:
            await update.message.reply_text("⚠️ **Aap ek hi ID ko refer kar sakte hain.**", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")
        else:
            await update.message.reply_text(f"🔗 **Your Referral Link:**\n`https://t.me/{bot_info.username}?start={user_id}`\n\nShare and get 2 credits per join!", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")
        return

    if text in ["🟢 📱 NUMBER INFO", "🔵 🆔 AADHAAR INFO", "🟣 ✈️ TG TO NUMBER", "🟠 👨‍👩‍👧‍👦 FAMILY INFO", "🔴 🏦 IFSC CODE"]:
        if not await is_user_joined(update, ctx): return
        if get_user(user_id)[0] <= 0:
            await send_no_credit_msg(update, ctx); return
        prompts = {
            "🟢 📱 NUMBER INFO": "📱 **Send 10-digit Mobile Number:**",
            "🔵 🆔 AADHAAR INFO": "🆔 **Send 12-digit Aadhaar:**",
            "🟣 ✈️ TG TO NUMBER": "✈️ **Send Telegram ID:**",
            "🟠 👨‍👩‍👧‍👦 FAMILY INFO": "👨‍👩‍👧‍👦 **Send 12-digit Aadhaar:**",
            "🔴 🏦 IFSC CODE": "🏦 **Send IFSC Code:**",
        }
        await update.message.reply_text(prompts[text], reply_markup=get_cancel_keyboard(), parse_mode="Markdown"); return

    # Direct input search
    clean_text = text.replace(" ", "").replace("-", "").strip()
    if clean_text.isdigit() and len(clean_text) == 10:
        if get_user(user_id)[0] <= 0: await send_no_credit_msg(update, ctx); return
        await do_search_num(update, ctx, clean_text)
    elif clean_text.isdigit() and len(clean_text) == 12:
        if get_user(user_id)[0] <= 0: await send_no_credit_msg(update, ctx); return
        await do_search_aadhar(update, ctx, clean_text)
    elif clean_text.isdigit() and len(clean_text) < 15:
        if get_user(user_id)[0] <= 0: await send_no_credit_msg(update, ctx); return
        await do_search_tg(update, ctx, clean_text)
    elif re.match(r'^[A-Za-z]{4}0[A-Za-z0-9]{6}$', text):
        if get_user(user_id)[0] <= 0: await send_no_credit_msg(update, ctx); return
        await do_search_ifsc(update, ctx, text)

# --- SEARCH EXECUTORS ---
async def do_search_num(update, ctx, num):
    user_id = update.effective_user.id
    msg = await update.message.reply_text(f"🔍 **Searching Number** `{num}`...", parse_mode="Markdown")
    deduct_credit(user_id); log_search(user_id, "NUMBER", num)
    res = fetch_num(get_setting('num_api'), num)
    if not res: return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    out = f"🕵️‍♂️ **DATA FOUND**\n**Number:** `{num}`\n\n"
    for i, r in enumerate(res['results'][:3], 1):
        out += f"👤 **Record {i}**\n▪️ **Name:** {r.get('name')}\n▪️ **Father:** {r.get('fathersName')}\n▪️ **Aadhar:** {r.get('aadharNumber')}\n▪️ **Address:** {r.get('address')}\n\n"
    out += f"💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in {AUTO_DELETE_SECONDS}s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

async def do_search_aadhar(update, ctx, num):
    user_id = update.effective_user.id
    msg = await update.message.reply_text(f"🔍 **Searching Aadhar** `{num}`...", parse_mode="Markdown")
    deduct_credit(user_id); log_search(user_id, "AADHAR", num)
    res = fetch_num(get_setting('aadhar_api'), num)
    if not res: return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    out = f"🕵️‍♂️ **AADHAR FOUND**\n\n"
    for i, r in enumerate(res['results'][:3], 1):
        out += f"👤 **Record {i}**\n▪️ **Name:** {r.get('name')}\n▪️ **Mobile:** {r.get('phoneNumber')}\n▪️ **Address:** {r.get('address')}\n\n"
    out += f"💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in {AUTO_DELETE_SECONDS}s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

async def do_search_tg(update, ctx, tid):
    user_id = update.effective_user.id
    msg = await update.message.reply_text(f"✈️ **Searching TG ID** `{tid}`...", parse_mode="Markdown")
    deduct_credit(user_id); log_search(user_id, "TELEGRAM_ID", tid)
    res = fetch_tg(tid)
    if not res: return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    out = f"✈️ **TG DATA FOUND**\n🆔 **TG ID:** `{tid}`\n\n"
    for p in res.get("phone", [])[:5]:
        out += f"📱 `{p.get('country_code')}{p.get('number')}` ({p.get('country')})\n"
    out += f"\n💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in {AUTO_DELETE_SECONDS}s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

async def do_search_ifsc(update, ctx, code):
    user_id = update.effective_user.id
    msg = await update.message.reply_text(f"🏦 **Searching IFSC** `{code}`...", parse_mode="Markdown")
    deduct_credit(user_id); log_search(user_id, "IFSC", code)
    res = fetch_ifsc(code)
    if not res: return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    out = f"🏦 **IFSC INFO**\n\n🔢 **Code:** `{code}`\n"
    for _, v in res.get("data", {}).items():
        out += f"🏛️ **Bank:** {v.get('bank')}\n🏢 **Branch:** {v.get('branch')}\n📍 **Address:** {v.get('address')}\n"; break
    out += f"\n💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in {AUTO_DELETE_SECONDS}s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

# --- BUTTON HANDLER ---
async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "verify_join":
        await verify_join(update, ctx); return

    if data.startswith("buy_"):
        plan = data.split("_")[1]
        if plan in PLANS:
            price = PLANS[plan]["price"]; credits = PLANS[plan]["credits"]
            note = f"Plan {credits} Credits"
            qr_buffer, upi_string = generate_upi_qr(UPI_ID, UPI_NAME, price, note)
            chat_id = query.message.chat_id
            kb = [
                [InlineKeyboardButton("📤 Upload Payment Screenshot", callback_data=f"screenshot_{plan}")],
                [InlineKeyboardButton("💬 Message Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}?text=I%20want%20to%20buy%20{credits}%20Credits")],
            ]
            caption = (
                f"╭━━━━━━━━━━━━━━━━━━╮\n   💰 *{scp('PAYMENT')}* 💰\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
                f"💎 **Plan:** {credits} Credits\n💵 **Amount:** ₹{price}\n"
                f"🏦 **UPI ID:** `{UPI_ID}`\n👤 **Name:** {UPI_NAME}\n\n"
                f"1️⃣ Neeche QR scan karo (amount ₹{price} auto bhara hoga)\n"
                f"2️⃣ PIN daal kar pay karo\n3️⃣ Phir 'Upload Payment Screenshot' dabao\n\n"
                f"⚠️ _Amount change mat karna, warna reject ho jayega_"
            )
            try: await query.message.delete()
            except: pass
            await ctx.bot.send_photo(chat_id=chat_id, photo=qr_buffer, caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            await ctx.bot.send_message(chat_id=chat_id, text=f"🔗 **QR scan na ho to ye link copy karke UPI app me paste karo:**\n\n`{upi_string}`", parse_mode="Markdown")
        return

    if data.startswith("screenshot_"):
        await ask_screenshot(update, ctx); return

    if data.startswith("approve_"):
        if not is_admin(user_id):
            await query.answer("Sirf admin kar sakta hai.", show_alert=True); return
        pid = int(data.split("_")[1])
        payment = get_pending_payment(pid)
        if not payment:
            await query.answer("Payment nahi mila.", show_alert=True); return
        p_user_id, plan_key, status = payment
        if status != 'waiting_admin':
            await query.answer("Ye payment pehle process ho chuka hai.", show_alert=True); return
        plan = PLANS[plan_key]
        adjust_credits(p_user_id, plan['credits'])
        set_payment_status(pid, 'approved')
        try:
            await ctx.bot.send_message(chat_id=p_user_id,
                text=f"✅ **Payment Approved!**\n\n💎 {plan['credits']} Credits added to your account.\nAb search kar sakte ho!",
                parse_mode="Markdown")
        except: pass
        try:
            await query.message.edit_caption(caption=(query.message.caption or "") + "\n\n✅ **APPROVED**", parse_mode="Markdown")
        except: pass
        await query.answer("Credits added!"); return

    if data.startswith("reject_"):
        if not is_admin(user_id):
            await query.answer("Sirf admin.", show_alert=True); return
        pid = int(data.split("_")[1])
        payment = get_pending_payment(pid)
        if not payment:
            await query.answer("Nahi mila.", show_alert=True); return
        p_user_id, plan_key, status = payment
        set_payment_status(pid, 'rejected')
        try:
            await ctx.bot.send_message(chat_id=p_user_id, text="❌ **Payment Reject ho gaya.**\nOwner se contact karo: " + OWNER_USERNAME, parse_mode="Markdown")
        except: pass
        try:
            await query.message.edit_caption(caption=(query.message.caption or "") + "\n\n❌ **REJECTED**", parse_mode="Markdown")
        except: pass
        await query.answer("Rejected."); return

    if data.startswith("history_"):
        target_uid = data.split("_")[1]
        conn = sqlite3.connect('users.db'); c = conn.cursor()
        c.execute("SELECT search_type, search_query, search_date FROM search_history WHERE user_id=? ORDER BY id DESC LIMIT 15", (target_uid,))
        history = c.fetchall(); conn.close()
        if not history:
            await query.answer("No history found.", show_alert=True); return
        text = f"╭━━━━━━━━━━━━━━━━━━╮\n   🟣 *{scp('HISTORY')}* 🟣\n╰━━━━━━━━━━━━━━━━━━╯\n\n👤 User ID: `{target_uid}`\n\n"
        for h in history:
            text += f"🔹 **{h[0]}:** `{h[1]}`\n   📅 _{h[2]}_\n\n"
        await query.message.edit_text(text, parse_mode="Markdown"); return

# --- MAIN ---
def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN missing in .env"); return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    app.add_handler(MessageHandler(filters.Regex("^🟢 💎 ADD POINTS$"), admin_add_credits_start))
    app.add_handler(MessageHandler(filters.Regex("^🔴 ❌ REMOVE POINTS$"), admin_remove_credits_start))
    app.add_handler(MessageHandler(filters.Regex("^🔴 🚫 BAN USER$"), admin_ban_start))
    app.add_handler(MessageHandler(filters.Regex("^🟢 ✅ UNBAN USER$"), admin_unban_start))
    app.add_handler(MessageHandler(filters.Regex("^🟡 📣 BROADCAST$"), admin_broadcast_start))
    app.add_handler(MessageHandler(filters.Regex("^🔵 📊 STATS$"), admin_stats))
    app.add_handler(MessageHandler(filters.Regex("^🟣 📊 RECORDS$"), admin_records))
    app.add_handler(MessageHandler(filters.Regex("^🔵 ⚙️ API STATUS$"), admin_api_status))
    app.add_handler(MessageHandler(filters.Regex("^🟠 🔗 CHANGE API$"), admin_change_api_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("[*] Ultimate Pro Max Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()