import requests
import sqlite3
import datetime
import time
import asyncio
import re
import os
import qrcode
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- TERA CONFIG ---
BOT_TOKEN = "8925056785:AAG9nWFNuFgRWPOGIvIsILdkDeweX1APzuU" 
SUPER_ADMIN_ID = 8786686789  
OWNER_USERNAME = "@heart_of_public" 
CHANNEL_1 = "@biggest_4_public" 
CHANNEL_2 = "@sufiyanr31" 

# --- PAYMENT CONFIG ---
UPI_ID = "trillionadillllxyz@fam" 
UPI_NAME = "Mohammad Adil"
SRC_PRICE = 1499

# --- APIs ---
DEFAULT_NUM_API = "https://sra-num-aadhar-info-api-main-two.vercel.app/search?q="
DEFAULT_AADHAR_API = "https://sra-num-aadhar-info-api-main-rose.vercel.app/search?q="
TG_NUM_API_URL = "https://tele-to-phone.felixrdx.xyz/api/developer/Cyb3rB4nn3r/fast"
TG_NUM_API_KEY = "ba76fa0f97264dea84364ca1df91a2e8"

AUTO_DELETE_SECONDS = 30

# --- PLANS ---
PLANS = {
    "10": {"credits": 10, "price": 30},
    "25": {"credits": 25, "price": 70},
    "50": {"credits": 50, "price": 130},
    "100": {"credits": 100, "price": 250},
}

# --- TEXT FORMATTING ---
SMALL_CAPS_MAP = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ꜰ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ꜰ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ',
    'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ', 'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
}
def scp(text): return ''.join(SMALL_CAPS_MAP.get(ch, ch) for ch in str(text))
LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━"

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, credits INTEGER, total_searches INTEGER DEFAULT 0, join_date TEXT, refer_by INTEGER DEFAULT 0, join_bonus_claimed INTEGER DEFAULT 0, has_referred INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS search_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, search_type TEXT, search_query TEXT, search_date TEXT)''')
    conn.commit()
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (SUPER_ADMIN_ID,))
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('num_api', ?)", (DEFAULT_NUM_API,))
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('aadhar_api', ?)", (DEFAULT_AADHAR_API,))
    conn.commit(); conn.close()
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

async def is_user_joined(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id): return True
    try:
        m1 = await ctx.bot.get_chat_member(chat_id=CHANNEL_1, user_id=user_id)
        m2 = await ctx.bot.get_chat_member(chat_id=CHANNEL_2, user_id=user_id)
        return m1.status in ['member', 'administrator', 'creator'] and m2.status in ['member', 'administrator', 'creator']
    except: return False 

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

# --- KEYBOARDS ---
def get_main_keyboard(user_id):
    kb = [
        [KeyboardButton("🟢 📱 NUMBER INFO"), KeyboardButton("🔵 🆔 AADHAAR INFO")],
        [KeyboardButton("🟣 ✈️ TG TO NUMBER"), KeyboardButton("🟠 👨‍👩‍👧‍👦 FAMILY INFO")],
        [KeyboardButton("🟡 💰 BALANCE"), KeyboardButton("🟢 🛒 BUY CREDITS")],
        [KeyboardButton("💻 ʙᴜʏ sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ"), KeyboardButton("🔵 🔗 REFERRAL")]
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
        [KeyboardButton("🏠 MAIN MENU")]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

async def send_no_credit_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🛒 Buy Credits Now", callback_data="buy_credits")]]
    text = f"❌ **0 Credits!**\n\nPehle credit buy kar fir search kar ladle 😎🤌"
    if update.callback_query: await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- COMMANDS ---
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banned(user_id): return await update.message.reply_text("🚫 **You are banned.**", parse_mode="Markdown")
    refer_by = int(ctx.args[0]) if ctx.args and ctx.args[0].isdigit() else 0
    add_user(user_id, refer_by)
    user = get_user(user_id)

    if not await is_user_joined(update, ctx):
        kb = [[InlineKeyboardButton("🔴 Join Channel 1", url=f"https://t.me/{CHANNEL_1.replace('@', '')}")], [InlineKeyboardButton("🔴 Join Channel 2", url=f"https://t.me/{CHANNEL_2.replace('@', '')}")], [InlineKeyboardButton("🟢 ✅ VERIFY JOIN", callback_data="verify_join")]]
        return await update.message.reply_text(f"⚠️ *{scp('ACCESS DENIED')}* ⚠️\n\nBhai pehle dono channel join kar, fir verify kar. Uske baad hi bot chalega!", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    text = (f"🔥 *{scp('PREMIUM OSINT BOT')}* 🔥\n\n✨ *{scp('Welcome')}, {update.effective_user.first_name}!*\n\n⭐ *{scp('User ID')}:* `{user_id}`\n💎 *{scp('Credits')}:* {user[0]}\n👑 *{scp('Owner')}:* <b>{OWNER_USERNAME}</b>\n\n{LINE}\n⚡ *{scp('Cost')}:* 1 {scp('Credit/Search')}\n\n👇 *{scp('Use buttons below to start')}*")
    await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")

async def verify_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if await is_user_joined(update, ctx):
        await query.message.delete(); await start(update, ctx)
    else: await query.answer("❌ Bhai pehle dono channel join kar, fir verify kar!", show_alert=True)

async def admin_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        kb = [[InlineKeyboardButton("🟢 💬 Message Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]]
        await update.message.reply_text("👑 *CONTACT ADMIN* 👑\n\nClick below to message the owner.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await update.message.reply_text("⚙️ **Admin Control Panel**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

# --- ADMIN ACTIONS ---
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
    ctx.user_data['awaiting_broadcast'] = True
    await update.message.reply_text("📣 **Broadcast**\n\nType the message to send to all users.", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

async def admin_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_searches = c.execute("SELECT COALESCE(SUM(total_searches),0) FROM users").fetchone()[0]
    conn.close()
    await update.message.reply_text(f"📊 **Bot Statistics**\n\n👥 Total Users: {total_users}\n🔍 Total Searches: {total_searches}", parse_mode="Markdown", reply_markup=get_admin_keyboard())

async def admin_records(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("SELECT user_id, COUNT(id) FROM search_history GROUP BY user_id ORDER BY COUNT(id) DESC LIMIT 20")
    users = c.fetchall(); conn.close()
    if not users: return await update.message.reply_text("❌ **No search records found.**", parse_mode="Markdown")
    text, kb = "🟣 *SEARCH RECORDS* 🟣\n\n", []
    for uid, count in users:
        text += f"👤 ID: `{uid}` - {count} Searches\n"
        kb.append([InlineKeyboardButton(f"🔍 See {uid}'s History", callback_data=f"history_{uid}")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def admin_api_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    msg = await update.message.reply_text("⚙️ **Checking APIs...**")
    num_status, aadhar_status = "🔴 Down", "🔴 Down"
    try:
        if requests.get(f"{get_setting('num_api')}9876543210", timeout=15).status_code == 200: num_status = "🟢 Online"
    except: pass
    try:
        if requests.get(f"{get_setting('aadhar_api')}123456789012", timeout=15).status_code == 200: aadhar_status = "🟢 Online"
    except: pass
    await msg.edit_text(f"⚙️ *API STATUS* ⚙️\n\n📱 *Number API:* {num_status}\n🆔 *Aadhar API:* {aadhar_status}", parse_mode="Markdown")

# --- BROADCAST LOGIC ---
async def process_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    msg = update.message
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall(); conn.close()
    
    success, failed = 0, 0
    status = await update.message.reply_text(f"📣 Broadcasting to {len(users)} users...")
    
    for (uid,) in users:
        try:
            await msg.copy(chat_id=uid)
            success += 1
            await asyncio.sleep(0.1)
        except Exception:
            failed += 1
            
    await status.edit_text(f"✅ **Broadcast Complete!**\n\nSent: {success}\nFailed: {failed}", parse_mode="Markdown")

# --- HANDLE TEXT ---
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if is_banned(user_id): return

    if is_admin(user_id) and ctx.user_data.get('awaiting_broadcast'):
        ctx.user_data['awaiting_broadcast'] = False
        return await process_broadcast(update, ctx)

    if is_admin(user_id) and ctx.user_data.get('manual_add_id'):
        target_id = ctx.user_data.get('manual_add_id')
        try:
            amt = int(text.strip())
            adjust_credits(target_id, amt)
            await update.message.reply_text(f"✅ Added {amt} credits to User `{target_id}`!", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
            try: await ctx.bot.send_message(target_id, f"✅ **Payment Approved!**\n\n{amt} Credits added to your account.", parse_mode="Markdown")
            except: pass
            del ctx.user_data['manual_add_id']
        except:
            await update.message.reply_text("❌ Invalid Amount. Send a valid number.", reply_markup=get_admin_keyboard())
        return

    if text in ["🔴 🚫 CANCEL", "🏠 MAIN MENU"]:
        return await start(update, ctx)

    if is_admin(user_id):
        try:
        ...