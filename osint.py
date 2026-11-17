import requests
import sqlite3
import datetime
import time
import asyncio
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- TERA CONFIG ---
BOT_TOKEN = "8925056785:AAFwAAYtvbdSNRc1K69egLiZTvt4Ar0NTJE" 
SUPER_ADMIN_ID = 8786686789  
OWNER_USERNAME = "@heart_of_public" 
CHANNEL_1 = "@biggest_4_public" 
CHANNEL_2 = "@sufiyanr31" 

# --- PAYMENT CONFIG ---
UPI_ID = "trillionadillllxyz@fam" 
UPI_NAME = "Mohammad adil"
PAYMENT_VERIFY_API = "https://dugu-payment-verify.vercel.app/api/verify"
SRC_PRICE = 1499

# --- TERI APIs ---
DEFAULT_NUM_API = "https://sra-num-aadhar-info-api-main-two.vercel.app/search?q="
DEFAULT_AADHAR_API = "https://sra-num-aadhar-info-api-main-rose.vercel.app/search?q="
TG_NUM_API_URL = "https://tele-to-phone.felixrdx.xyz/api/developer/Cyb3rB4nn3r/fast"
TG_NUM_API_KEY = "ba76fa0f97264dea84364ca1df91a2e8"
AADHAAR_FAMILY_API = "https://addhartofam.fuckyoubitch.workers.dev/family"
IFSC_API_URL = "https://authapisellhub.shop/api.php"
IFSC_API_KEY = "c8511bdd2cef1cc5507372a5a2afaabafd47265f841e5da95ea3540b9f07d8e6"

AUTO_DELETE_SECONDS = 30

# --- PLANS ---
PLANS = {
    "10": {"credits": 10, "price": 30, "label": "10 Points"},
    "25": {"credits": 25, "price": 70, "label": "25 Points"},
    "50": {"credits": 50, "price": 130, "label": "50 Points"},
    "100": {"credits": 100, "price": 250, "label": "100 Points"}
}

# --- TEXT FORMATTING ---
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
def scp(text):
    return ''.join(SMALL_CAPS_MAP.get(ch, ch) for ch in str(text))

LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━"

# --- DATABASE SETUP ---
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
    c.execute('''CREATE TABLE IF NOT EXISTS payment_txns (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, txn_id TEXT UNIQUE, 
        amount REAL, points REAL, status TEXT DEFAULT 'pending')''')
    conn.commit()
    
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (SUPER_ADMIN_ID,))
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('num_api', ?)", (DEFAULT_NUM_API,))
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('aadhar_api', ?)", (DEFAULT_AADHAR_API,))
    conn.commit()
    conn.close()
init_db()

# --- DB HELPERS ---
def get_setting(key):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    val = c.fetchone()
    conn.close()
    return val[0] if val else ""

def get_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT credits, total_searches, join_date, refer_by, join_bonus_claimed, has_referred FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res

def add_user(user_id, refer_by=0):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, credits, join_date, refer_by, join_bonus_claimed) VALUES (?, ?, ?, ?, 1)", (user_id, 0, date, refer_by))
        conn.commit()
        # Naye user ko welcome bonus 2 credits direct de rahe hain, par claimed=1 set kar rahe hain
        adjust_credits(user_id, 2)
        
        if refer_by != 0:
            c.execute("SELECT has_referred FROM users WHERE user_id=?", (refer_by,))
            ref_status = c.fetchone()
            if ref_status and ref_status[0] == 0:
                c.execute("UPDATE users SET credits = credits + 2, has_referred = 1 WHERE user_id=?", (refer_by,))
                c.execute("UPDATE users SET credits = credits + 2 WHERE user_id=?", (user_id,))
                conn.commit()
    conn.close()

def adjust_credits(user_id, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def deduct_credit(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits - 1, total_searches = total_searches + 1 WHERE user_id=? AND credits > 0", (user_id,))
    conn.commit()
    conn.close()

def log_search(user_id, search_type, query):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO search_history (user_id, search_type, search_query, search_date) VALUES (?, ?, ?, ?)", 
              (user_id, search_type, query, date))
    conn.commit()
    conn.close()

def is_admin(user_id):
    if user_id == SUPER_ADMIN_ID: return True
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM admins WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return bool(res)

def is_banned(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM banned_users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return bool(res)

# --- FORCE JOIN CHECK ---
async def is_user_joined(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id): return True
    try:
        m1 = await ctx.bot.get_chat_member(chat_id=CHANNEL_1, user_id=user_id)
        m2 = await ctx.bot.get_chat_member(chat_id=CHANNEL_2, user_id=user_id)
        return m1.status in ['member', 'administrator', 'creator'] and m2.status in ['member', 'administrator', 'creator']
    except:
        return False 

# --- AUTO DELETE ---
async def auto_delete_message(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    await asyncio.sleep(AUTO_DELETE_SECONDS)
    try: await ctx.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except: pass

# --- API FETCHERS ---
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
        [KeyboardButton("💻 ʙᴜʏ sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ"), KeyboardButton("🔵 🔗 REFERRAL")]
    ]
    if is_admin(user_id):
        kb.append([KeyboardButton("👑 ADMIN PANEL")])
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
        [KeyboardButton("🏠 MAIN MENU")]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# --- CREDIT 0 MESSAGE HELPER ---
async def send_no_credit_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("💎 1 Day - ₹10", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}?text=I%20want%20to%20buy%20the%20₹10%20plan%20(1%20Day)")],
        [InlineKeyboardButton("💎 1 Week - ₹79", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}?text=I%20want%20to%20buy%20the%20₹79%20plan%20(1%20Week)")],
        [InlineKeyboardButton("💎 1 Month - ₹299", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}?text=I%20want%20to%20buy%20the%20₹299%20plan%20(1%20Month)")]
    ]
    text = (
        f"❌ **0 Credits!**\n\n"
        f"Pehle credit buy kar fir search kar ladle 😎🤌\n\n"
        f"👇 *Select a plan below:*"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- COMMANDS ---
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banned(user_id):
        await update.message.reply_text("🚫 **You are banned.**", parse_mode="Markdown")
        return

    refer_by = 0
    if ctx.args and ctx.args[0].isdigit():
        refer_by = int(ctx.args[0])
    
    # Yahan add_user me hi bonus add ho raha hai, baar-baar start pe nahi
    add_user(user_id, refer_by)
    user = get_user(user_id)

    if not await is_user_joined(update, ctx):
        kb = [
            [InlineKeyboardButton("🔴 Join Channel 1", url=f"https://t.me/{CHANNEL_1.replace('@', '')}")],
            [InlineKeyboardButton("🔴 Join Channel 2", url=f"https://t.me/{CHANNEL_2.replace('@', '')}")],
            [InlineKeyboardButton("🟢 ✅ VERIFY JOIN", callback_data="verify_join")]
        ]
        await update.message.reply_text(
            f"╭━━━━━━━━━━━━━━━━━━╮\n"
            f"   ⚠️ *{scp('ACCESS DENIED')}* ⚠️\n"
            f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
            f"Bhai pehle dono channel join kar, fir verify kar. Uske baad hi bot chalega!",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    text = (
        f"╭━━━━━━━━━━━━━━━━━━╮\n"
        f"   🔥 *{scp('PREMIUM OSINT BOT')}* 🔥\n"
        f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
        f"✨ *{scp('Welcome')}, {update.effective_user.first_name}!*\n\n"
        f"⭐ *{scp('User ID')}:* `{user_id}`\n"
        f"💎 *{scp('Credits')}:* {user[0]}\n"
        f"👑 *{scp('Owner')}:* <b>{OWNER_USERNAME}</b>\n\n"
        f"{LINE}\n"
        f"🛡️ *{scp('Services')}:*\n"
        f"• 📱 {scp('Number Info')}\n"
        f"• 🆔 {scp('Aadhaar Info')}\n"
        f"• ✈️ {scp('TG to Number')}\n"
        f"• 👨‍👩‍👧‍👦 {scp('Family Info')}\n"
        f"• 🏦 {scp('IFSC Code')}\n\n"
        f"{LINE}\n"
        f"⚡ *{scp('Cost')}:* 1 {scp('Credit/Search')}\n\n"
        f"👇 *{scp('Use buttons below to start')}*"
    )
    await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")

async def verify_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_user_joined(update, ctx):
        await query.message.delete()
        await start(update, ctx)
    else:
        await query.answer("❌ Bhai pehle dono channel join kar, fir verify kar!", show_alert=True)

async def admin_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        text = (
            f"╭━━━━━━━━━━━━━━━━━━╮\n"
            f"   👑 *{scp('CONTACT ADMIN')}* 👑\n"
            f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
            f"Click the button below to directly message the owner for credits or help."
        )
        kb = [[InlineKeyboardButton("🟢 💬 Message Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text("⚙️ **Admin Control Panel**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

# --- ADMIN ACTIONS LOGIC ---
async def admin_add_credits_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("💎 **Add Credits**\n\nFormat: `USER_ID AMOUNT`\nExample: `12345678 50`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

async def admin_remove_credits_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("❌ **Remove Credits**\n\nFormat: `USER_ID AMOUNT`\nExample: `12345678 20`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

async def admin_ban_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("🚫 **Ban User**\n\nFormat: `USER_ID`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

async def admin_unban_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("✅ **Unban User**\n\nFormat: `USER_ID`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

async def admin_broadcast_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("📣 **Broadcast**\n\nType the message to send to all users.", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

async def admin_change_api_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("🔗 **API Settings**\n\nTo change Number API: `setnumapi URL`\nTo change Aadhar API: `setaadharapi URL`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

# --- ADMIN STATS & RECORDS ---
async def admin_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_searches = c.execute("SELECT COALESCE(SUM(total_searches),0) FROM users").fetchone()[0]
    total_revenue = c.execute("SELECT COALESCE(SUM(amount),0) FROM payment_txns WHERE status='approved'").fetchone()[0]
    conn.close()
    await update.message.reply_text(f"📊 **Bot Statistics**\n\n👥 Total Users: {total_users}\n🔍 Total Searches: {total_searches}\n💰 Revenue: ₹{total_revenue}", parse_mode="Markdown", reply_markup=get_admin_keyboard())

async def admin_records(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("""SELECT user_id, COUNT(id) FROM search_history GROUP BY user_id ORDER BY COUNT(id) DESC LIMIT 20""")
    users = c.fetchall()
    conn.close()

    if not users:
        await update.message.reply_text("❌ **No search records found.**", parse_mode="Markdown")
        return

    text = f"╭━━━━━━━━━━━━━━━━━━╮\n   🟣 *{scp('SEARCH RECORDS')}* 🟣\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
    kb = []
    for uid, count in users:
        text += f"👤 ID: `{uid}` - {count} Searches\n"
        kb.append([InlineKeyboardButton(f"🔍 See {uid}'s History", callback_data=f"history_{uid}")])
        
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def admin_api_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    msg = await update.message.reply_text("⚙️ **Checking APIs Status...**", parse_mode="Markdown")
    num_status = "🔴 Down"
    aadhar_status = "🔴 Down"
    
    try:
        r = requests.get(f"{get_setting('num_api')}9876543210", timeout=15)
        if r.status_code == 200: num_status = "🟢 Online"
    except: pass
    
    try:
        r = requests.get(f"{get_setting('aadhar_api')}123456789012", timeout=15)
        if r.status_code == 200: aadhar_status = "🟢 Online"
    except: pass
    
    text = (
        f"╭━━━━━━━━━━━━━━━━━━╮\n"
        f"   ⚙️ *{scp('API STATUS')}* ⚙️\n"
        f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
        f"📱 *Number API:* {num_status}\n"
        f"🆔 *Aadhar API:* {aadhar_status}\n\n"
        f"🔄 _Ping Check Complete_"
    )
    await msg.edit_text(text, parse_mode="Markdown")

# --- HANDLE TEXT INPUTS (Admin) ---
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if is_banned(user_id): return

    if text == "🔴 🚫 CANCEL" or text == "🏠 MAIN MENU":
        await start(update, ctx)
        return

    # Admin Text Parsing
    if is_admin(user_id):
        try:
            parts = text.split()
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                uid, amt = int(parts[0]), int(parts[1])
                adjust_credits(uid, amt)
                await update.message.reply_text(f"✅ Added {amt} credits to `{uid}`", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
                return
            elif len(parts) == 1 and parts[0].isdigit():
                uid = int(parts[0])
                conn = sqlite3.connect('users.db')
                conn.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (uid,))
                conn.commit(); conn.close()
                await update.message.reply_text(f"🚫 User `{uid}` banned.", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
                return
        except: pass

    if text == "🟡 💰 BALANCE":
        user = get_user(user_id)
        await update.message.reply_text(f"💎 **Balance:** {user[0]} Credits\n🔍 **Searches:** {user[1]}", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")
        return

    # --- BUY CREDITS LOGIC ---
    if text == "🟢 🛒 BUY CREDITS":
        kb = [
            [InlineKeyboardButton("💎 10 CR - ₹30", callback_data="buy_10")],
            [InlineKeyboardButton("💎 25 CR - ₹70", callback_data="buy_25")],
            [InlineKeyboardButton("💎 50 CR - ₹130", callback_data="buy_50")],
            [InlineKeyboardButton("💎 100 CR - ₹250", callback_data="buy_100")]
        ]
        buy_text = (
            f"╭━━━━━━━━━━━━━━━━━━╮\n"
            f"   🛒 *{scp('BUY CREDITS')}* 🛒\n"
            f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
            f"Select a plan below:\n"
            f"• 💎 10 Credits = ₹30\n"
            f"• 💎 25 Credits = ₹70\n"
            f"• 💎 50 Credits = ₹130\n"
            f"• 💎 100 Credits = ₹250\n\n"
            f"👇 *To purchase, click a plan:*"
        )
        await update.message.reply_text(buy_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    # --- BUY SOURCE CODE LOGIC ---
    if text == "💻 ʙᴜʏ sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ":
        conn = sqlite3.connect('users.db')
        conn.execute("INSERT INTO src_requests (user_id, created_at) VALUES (?, ?)", (user_id, datetime.datetime.now().isoformat()))
        conn.commit(); conn.close()
        
        kb = [[InlineKeyboardButton("💬 Message Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]]
        src_text = (
            f"╭━━━━━━━━━━━━━━━━━━╮\n"
            f"   💻 *{scp('BUY SOURCE CODE')}* 💻\n"
            f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
            f"Get the full source code of this bot!\n\n"
            f"👑 **Price:** ₹{SRC_PRICE}\n\n"
            f"👇 *Click below to message Owner:*"
        )
        await update.message.reply_text(src_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    if text == "🔵 🔗 REFERRAL":
        bot_info = await ctx.bot.get_me()
        user = get_user(user_id)
        if user[5] == 1:
            await update.message.reply_text("⚠️ **Aap ek hi ID ko refer kar sakte hain.**\nDusra referral code claim karne ke liye nayi ID aani padegi!", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")
        else:
            await update.message.reply_text(f"🔗 **Your Referral Link:**\n`https://t.me/{bot_info.username}?start={user_id}`\n\nShare and get 2 credits per join!", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")
        return

    # --- PROMPTS (Strict Credit Check with Plans) ---
    if text in ["🟢 📱 NUMBER INFO", "🔵 🆔 AADHAAR INFO", "🟣 ✈️ TG TO NUMBER", "🟠 👨‍👩‍👧‍👦 FAMILY INFO", "🔴 🏦 IFSC CODE"]:
        if not await is_user_joined(update, ctx): return
        
        if get_user(user_id)[0] <= 0:
            await send_no_credit_msg(update, ctx)
            return

        if text == "🟢 📱 NUMBER INFO":
            await update.message.reply_text("📱 **Send 10-digit Mobile Number:**\n\nExample: `99999...`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        elif text == "🔵 🆔 AADHAAR INFO":
            await update.message.reply_text("🆔 **Send 12-digit Aadhaar:**\n\nExample: `123456789012`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        elif text == "🟣 ✈️ TG TO NUMBER":
            await update.message.reply_text("✈️ **Send Telegram ID:**\n\nExample: `8518042438`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        elif text == "🟠 👨‍👩‍👧‍👦 FAMILY INFO":
            await update.message.reply_text("👨‍👩‍👧‍👦 **Send 12-digit Aadhaar:**\n\nExample: `123456789012`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        elif text == "🔴 🏦 IFSC CODE":
            await update.message.reply_text("🏦 **Send IFSC Code:**\n\nExample: `SBIN0000300`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        return

    # --- ADMIN BUTTON TEXT HANDLERS ---
    if is_admin(user_id):
        if text == "👑 ADMIN PANEL": await admin_command(update, ctx)
        elif text == "♾️ UNLIMITED CREDITS":
            adjust_credits(user_id, 9999999)
            await update.message.reply_text("♾️ **Unlimited Credits Added!**", reply_markup=get_admin_keyboard())
        elif text == "🟠 🔗 CHANGE API": await admin_change_api_start(update, ctx)
        elif text == "🟣 📊 RECORDS": await admin_records(update, ctx)
        elif text == "🔵 📊 STATS": await admin_stats(update, ctx)
        elif text == "🔵 ⚙️ API STATUS": await admin_api_status(update, ctx)
        elif text == "🟢 💎 ADD POINTS": await admin_add_credits_start(update, ctx)
        elif text == "🔴 ❌ REMOVE POINTS": await admin_remove_credits_start(update, ctx)
        elif text == "🔴 🚫 BAN USER": await admin_ban_start(update, ctx)
        elif text == "🟢 ✅ UNBAN USER": await admin_unban_start(update, ctx)
        elif text == "🟡 📣 BROADCAST": await admin_broadcast_start(update, ctx)
        return

    # --- EXECUTION LOGIC (Agar user direct number bhejta hai) ---
    clean_text = text.replace(" ", "").replace("-", "").strip()

    if clean_text.isdigit() and len(clean_text) == 10:
        if get_user(user_id)[0] <= 0:
            await send_no_credit_msg(update, ctx)
            return
        await do_search_num(update, ctx, clean_text)
    elif clean_text.isdigit() and len(clean_text) == 12:
        if get_user(user_id)[0] <= 0:
            await send_no_credit_msg(update, ctx)
            return
        await do_search_aadhar(update, ctx, clean_text)
    elif clean_text.isdigit() and len(clean_text) < 15:
        if get_user(user_id)[0] <= 0:
            await send_no_credit_msg(update, ctx)
            return
        await do_search_tg(update, ctx, clean_text)
    elif re.match(r'^[A-Za-z]{4}0[A-Za-z0-9]{6}$', text):
        if get_user(user_id)[0] <= 0:
            await send_no_credit_msg(update, ctx)
            return
        await do_search_ifsc(update, ctx, text)

# --- SEARCH EXECUTORS ---
async def do_search_num(update, ctx, num):
    user_id = update.effective_user.id
    msg = await update.message.reply_text(f"🔍 **Searching Number** `{num}`...", parse_mode="Markdown")
    deduct_credit(user_id)
    log_search(user_id, "NUMBER", num) 
    
    res = fetch_num(get_setting('num_api'), num)
    if not res:
        return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    
    out = f"🕵️‍♂️ **DATA FOUND**\n**Number:** `{num}`\n\n"
    for i, r in enumerate(res['results'][:3], 1):
        out += f"👤 **Record {i}**\n▪️ **Name:** {r.get('name')}\n▪️ **Father:** {r.get('fathersName')}\n▪️ **Aadhar:** {r.get('aadharNumber')}\n▪️ **Address:** {r.get('address')}\n\n"
    
    out += f"💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in 30s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

async def do_search_aadhar(update, ctx, num):
    user_id = update.effective_user.id
    msg = await update.message.reply_text(f"🔍 **Searching Aadhar** `{num}`...", parse_mode="Markdown")
    deduct_credit(user_id)
    log_search(user_id, "AADHAR", num)
    
    res = fetch_num(get_setting('aadhar_api'), num)
    if not res:
        return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    
    out = f"🕵️‍♂️ **AADHAR FOUND**\n\n"
    for i, r in enumerate(res['results'][:3], 1):
        out += f"👤 **Record {i}**\n▪️ **Name:** {r.get('name')}\n▪️ **Mobile:** {r.get('phoneNumber')}\n▪️ **Address:** {r.get('address')}\n\n"
    
    out += f"💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in 30s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

async def do_search_tg(update, ctx, tid):
    user_id = update.effective_user.id
    msg = await update.message.reply_text(f"✈️ **Searching TG ID** `{tid}`...", parse_mode="Markdown")
    deduct_credit(user_id)
    log_search(user_id, "TELEGRAM_ID", tid)
    
    res = fetch_tg(tid)
    if not res:
        return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    
    out = f"✈️ **TG DATA FOUND**\n🆔 **TG ID:** `{tid}`\n\n"
    phones = res.get("phone", [])
    for p in phones[:5]:
        out += f"📱 `{p.get('country_code')}{p.get('number')}` ({p.get('country')})\n"
    
    out += f"\n💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in 30s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

async def do_search_ifsc(update, ctx, code):
    user_id = update.effective_user.id
    msg = await update.message.reply_text(f"🏦 **Searching IFSC** `{code}`...", parse_mode="Markdown")
    deduct_credit(user_id)
    log_search(user_id, "IFSC", code)
    
    res = fetch_ifsc(code)
    if not res:
        return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    
    out = f"🏦 **IFSC INFO**\n\n🔢 **Code:** `{code}`\n"
    bank_data = res.get("data", {})
    for k, v in bank_data.items():
        out += f"🏛️ **Bank:** {v.get('bank')}\n🏢 **Branch:** {v.get('branch')}\n📍 **Address:** {v.get('address')}\n"
        break
    
    out += f"\n💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in 30s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

# --- BUTTON CALLBACKS ---
async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "verify_join":
        await verify_join(update, ctx)
    elif data.startswith("buy_"):
        plan = data.split("_")[1]
        if plan in PLANS:
            price = PLANS[plan]["price"]
            credits = PLANS[plan]["credits"]
            
            pay_text = (
                f"╭━━━━━━━━━━━━━━━━━━╮\n"
                f"   💰 *{scp('PAYMENT')}* 💰\n"
                f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
                f"💎 **Plan:** {credits} Credits\n"
                f"💵 **Amount:** ₹{price}\n\n"
                f"👇 **Scan QR or Pay to UPI:**\n"
                f"🆔 `{UPI_ID}`\n"
                f"👤 Name: {UPI_NAME}\n\n"
                f"⚠️ *After paying, send UTR/Txn ID here.*"
            )
            await query.message.edit_text(pay_text, parse_mode="Markdown")
            
            # Prompt for UTR
            msg = await ctx.bot.send_message(user_id, f"✍️ **Please send UTR / Txn ID for {credits} Credits:**")
            
    elif data.startswith("history_"):
        target_uid = data.split("_")[1]
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT search_type, search_query, search_date FROM search_history WHERE user_id=? ORDER BY id DESC LIMIT 15", (target_uid,))
        history = c.fetchall()
        conn.close()

        if not history:
            await query.answer("No history found for this user.", show_alert=True)
            return

        text = f"╭━━━━━━━━━━━━━━━━━━╮\n   🟣 *{scp('HISTORY')}* 🟣\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
        text += f"👤 User ID: `{target_uid}`\n\n"
        for h in history:
            text += f"🔹 **{h[0]}:** `{h[1]}`\n   📅 _{h[2]}_\n\n"
        
        await query.message.edit_text(text, parse_mode="Markdown")

# --- APP SETUP ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Admin Keyboard Handlers
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