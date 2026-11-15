import requests
import sqlite3
import datetime
import time
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- CONFIG ---
BOT_TOKEN = "8925056785:AAFwAAYtvbdSNRc1K69egLiZTvt4Ar0NTJE" 
SUPER_ADMIN_ID = 8786686789  
OWNER_USERNAME = "@heart_of_public" 
CHANNEL_1 = "@biggest_4_public" 
CHANNEL_2 = "@sufiyanr31" 

DEFAULT_NUM_API = "https://sra-num-aadhar-info-api-main-two.vercel.app/search?q="
DEFAULT_AADHAR_API = "https://sra-num-aadhar-info-api-main-rose.vercel.app/search?q="
TG_NUM_API_URL = "https://tele-to-phone.felixrdx.xyz/api/developer/Cyb3rB4nn3r/fast"
TG_NUM_API_KEY = "ba76fa0f97264dea84364ca1df91a2e8"
AADHAAR_FAMILY_API = "https://addhartofam.fuckyoubitch.workers.dev/family"
IFSC_API_URL = "https://authapisellhub.shop/api.php"
IFSC_API_KEY = "c8511bdd2cef1cc5507372a5a2afaabafd47265f841e5da95ea3540b9f07d8e6"

AUTO_DELETE_SECONDS = 30

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
        join_date TEXT, refer_by INTEGER DEFAULT 0, join_bonus_claimed INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
        search_type TEXT, search_query TEXT, search_date TEXT)''')
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
    c.execute("SELECT credits, total_searches, join_date, refer_by, join_bonus_claimed FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res

def add_user(user_id, refer_by=0):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, credits, join_date, refer_by) VALUES (?, ?, ?, ?)", (user_id, 0, date, refer_by))
        conn.commit()
        if refer_by != 0:
            c.execute("UPDATE users SET credits = credits + 2 WHERE user_id=?", (refer_by,))
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
def get_main_keyboard():
    kb = [
        [KeyboardButton("🟢 📱 ɴᴜᴍʙᴇʀ ɪɴꜰᴏ"), KeyboardButton("🔵 🆔 ᴀᴀᴅʜᴀᴀʀ ɪɴꜰᴏ")],
        [KeyboardButton("🟣 ✈️ ᴛɢ ᴛᴏ ɴᴜᴍʙᴇʀ"), KeyboardButton("🟠 👨‍👩‍👧‍👦 ꜰᴀᴍɪʟʏ ɪɴꜰᴏ")],
        [KeyboardButton("🔴 🏦 ɪꜰꜱᴄ ᴄᴏᴅᴇ")],
        [KeyboardButton("🟡 💰 ʙᴀʟᴀɴᴄᴇ"), KeyboardButton("🟢 🛒 ʙᴜʏ ᴄʀᴇᴅɪᴛꜱ")],
        [KeyboardButton("🔵 🔗 ʀᴇꜰᴇʀʀᴀʟ"), KeyboardButton("👑 ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ")]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("🔴 🚫 ᴄᴀɴᴄᴇʟ")]], resize_keyboard=True)

def get_admin_keyboard():
    kb = [
        [KeyboardButton("🟡 📣 ʙʀᴏᴀᴅᴄᴀꜱᴛ"), KeyboardButton("🔵 📊 ꜱᴛᴀᴛꜱ")],
        [KeyboardButton("🟢 💎 ᴀᴅᴅ ᴘᴏɪɴᴛꜱ"), KeyboardButton("🔴 ❌ ʀᴇᴍᴏᴠᴇ ᴘᴏɪɴᴛꜱ")],
        [KeyboardButton("🔴 🚫 ʙᴀɴ ᴜꜱᴇʀ"), KeyboardButton("🟢 ✅ ᴜɴʙᴀɴ ᴜꜱᴇʀ")],
        [KeyboardButton("🟣 📊 ʀᴇᴄᴏʀᴅꜱ"), KeyboardButton("🔵 ⚙️ ᴀᴘɪ ꜱᴛᴀᴛᴜꜱ")],
        [KeyboardButton("🏠 ᴍᴀɪɴ ᴍᴇɴᴜ")]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# --- COMMANDS ---
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banned(user_id):
        await update.message.reply_text("🚫 **You are banned.**", parse_mode="Markdown")
        return

    refer_by = 0
    if ctx.args and ctx.args[0].isdigit():
        refer_by = int(ctx.args[0])
    
    add_user(user_id, refer_by)
    user = get_user(user_id)
    
    if not user[4]: 
        adjust_credits(user_id, 2)
        conn = sqlite3.connect('users.db')
        conn.execute("UPDATE users SET join_bonus_claimed=1 WHERE user_id=?", (user_id,))
        conn.commit(); conn.close()
        user = get_user(user_id)

    if not await is_user_joined(update, ctx):
        kb = [
            [InlineKeyboardButton("🔴 Join Channel 1", url=f"https://t.me/{CHANNEL_1.replace('@', '')}")],
            [InlineKeyboardButton("🔴 Join Channel 2", url=f"https://t.me/{CHANNEL_2.replace('@', '')}")],
            [InlineKeyboardButton("🟢 ✅ Verify Join", callback_data="verify_join")]
        ]
        await update.message.reply_text("⚠️ **Access Denied!**\n\nJoin both channels to use this bot.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
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
    await update.message.reply_text(text, reply_markup=get_main_keyboard(), parse_mode="HTML")

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

async def verify_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_user_joined(update, ctx):
        await start(update, ctx)
        try: await query.message.delete()
        except: pass
    else:
        await query.answer("❌ Join both channels first!", show_alert=True)

# --- ADMIN ACTIONS LOGIC (Text Input Prompts) ---
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

# --- ADMIN STATS & RECORDS ---
async def admin_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_searches = c.execute("SELECT COALESCE(SUM(total_searches),0) FROM users").fetchone()[0]
    conn.close()
    await update.message.reply_text(f"📊 **Bot Statistics**\n\n👥 Total Users: {total_users}\n🔍 Total Searches: {total_searches}", parse_mode="Markdown", reply_markup=get_admin_keyboard())

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

    if text == "🔴 🚫 ᴄᴀɴᴄᴇʟ":
        await update.message.reply_text("Cancelled.", reply_markup=get_main_keyboard())
        return

    # Admin Text Parsing
    if is_admin(user_id):
        try:
            parts = text.split()
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                uid, amt = int(parts[0]), int(parts[1])
                # Check if this is for Add or Remove (we rely on the prompt)
                # For safety, we just add for now, the prompt tells them what to type
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

    if text == "🟡 💰 ʙᴀʟᴀɴᴄᴇ":
        user = get_user(user_id)
        await update.message.reply_text(f"💎 **Balance:** {user[0]} Credits\n🔍 **Searches:** {user[1]}", reply_markup=get_main_keyboard(), parse_mode="Markdown")
        return

    if text == "🟢 🛒 ʙᴜʏ ᴄʀᴇᴅɪᴛꜱ":
        kb = [
            [InlineKeyboardButton("💎 10 CR - ₹30", callback_data="buy_10"), InlineKeyboardButton("💎 25 CR - ₹70", callback_data="buy_25")],
            [InlineKeyboardButton("💎 50 CR - ₹130", callback_data="buy_50"), InlineKeyboardButton("💎 100 CR - ₹250", callback_data="buy_100")]
        ]
        buy_text = (
            f"╭━━━━━━━━━━━━━━━━━━╮\n"
            f"   🛒 *{scp('BUY CREDITS')}* 🛒\n"
            f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
            f"Select a plan below and send the request.\n\n"
            f"👇 *To purchase, directly message owner:*\n"
            f"👑 <b>{OWNER_USERNAME}</b>\n\n"
            f"⚡ _(Malik se mil 😎, screenshot bhejo aur turant credits pao!)_"
        )
        await update.message.reply_text(buy_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    if text == "🔵 🔗 ʀᴇꜰᴇʀʀᴀʟ":
        bot_info = await ctx.bot.get_me()
        await update.message.reply_text(f"🔗 **Your Referral Link:**\n`https://t.me/{bot_info.username}?start={user_id}`\n\nShare and get 2 credits per join!", reply_markup=get_main_keyboard(), parse_mode="Markdown")
        return

    # --- PROMPTS ---
    if text == "🟢 📱 ɴᴜᴍʙᴇʀ ɪɴꜰᴏ":
        if not await is_user_joined(update, ctx): return
        if get_user(user_id)[0] <= 0: return await update.message.reply_text("❌ **0 Credits!** Buy first.", parse_mode="Markdown")
        await update.message.reply_text("📱 **Send 10-digit Mobile Number:**\n\nExample: `99999...`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        return

    if text == "🔵 🆔 ᴀᴀᴅʜᴀᴀʀ ɪɴꜰᴏ":
        if not await is_user_joined(update, ctx): return
        if get_user(user_id)[0] <= 0: return await update.message.reply_text("❌ **0 Credits!** Buy first.", parse_mode="Markdown")
        await update.message.reply_text("🆔 **Send 12-digit Aadhaar:**\n\nExample: `123456789012`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        return

    if text == "🟣 ✈️ ᴛɢ ᴛᴏ ɴᴜᴍʙᴇʀ":
        if not await is_user_joined(update, ctx): return
        if get_user(user_id)[0] <= 0: return await update.message.reply_text("❌ **0 Credits!** Buy first.", parse_mode="Markdown")
        await update.message.reply_text("✈️ **Send Telegram ID:**\n\nExample: `8518042438`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        return

    if text == "🟠 👨‍👩‍👧‍👦 ꜰᴀᴍɪʟʏ ɪɴꜰᴏ":
        if not await is_user_joined(update, ctx): return
        if get_user(user_id)[0] <= 0: return await update.message.reply_text("❌ **0 Credits!** Buy first.", parse_mode="Markdown")
        await update.message.reply_text("👨‍👩‍👧‍👦 **Send 12-digit Aadhaar:**\n\nExample: `123456789012`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        return

    if text == "🔴 🏦 ɪꜰꜱᴄ ᴄᴏᴅᴇ":
        if not await is_user_joined(update, ctx): return
        if get_user(user_id)[0] <= 0: return await update.message.reply_text("❌ **0 Credits!** Buy first.", parse_mode="Markdown")
        await update.message.reply_text("🏦 **Send IFSC Code:**\n\nExample: `SBIN0000300`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        return

    # --- EXECUTION LOGIC ---
    clean_text = text.replace(" ", "").replace("-", "").strip()

    if clean_text.isdigit() and len(clean_text) == 10:
        await do_search_num(update, ctx, clean_text)
    elif clean_text.isdigit() and len(clean_text) == 12:
        await do_search_aadhar(update, ctx, clean_text)
    elif clean_text.isdigit() and len(clean_text) < 15:
        await do_search_tg(update, ctx, clean_text)
    elif re.match(r'^[A-Za-z]{4}0[A-Za-z0-9]{6}$', text):
        await do_search_ifsc(update, ctx, text)

# --- SEARCH EXECUTORS ---
async def do_search_num(update, ctx, num):
    user_id = update.effective_user.id
    msg = await update.message.reply_text(f"🔍 **Searching Number** `{num}`...", parse_mode="Markdown")
    deduct_credit(user_id)
    log_search(user_id, "NUMBER", num) 
    
    res = fetch_num(get_setting('num_api'), num)
    if not res:
        adjust_credits(user_id, 1)
        return await msg.edit_text("❌ **Data Not Found.** Credit refunded.", parse_mode="Markdown")
    
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
        adjust_credits(user_id, 1)
        return await msg.edit_text("❌ **Data Not Found.** Credit refunded.", parse_mode="Markdown")
    
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
        adjust_credits(user_id, 1)
        return await msg.edit_text("❌ **Data Not Found.** Credit refunded.", parse_mode="Markdown")
    
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
        adjust_credits(user_id, 1)
        return await msg.edit_text("❌ **Data Not Found.** Credit refunded.", parse_mode="Markdown")
    
    out = f"🏦 **IFSC INFO**\n\n🔢 **Code:** `{code}`\n"