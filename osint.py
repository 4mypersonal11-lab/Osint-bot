import requests
import sqlite3
import datetime
import time
import asyncio
import re
import os
import json
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

    if text in ["🔴 🚫 CANCEL", "🏠 MAIN MENU"]:
        return await start(update, ctx)

    if is_admin(user_id):
        try:
            parts = text.split()
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                adjust_credits(int(parts[0]), int(parts[1]))
                return await update.message.reply_text(f"✅ Added {parts[1]} credits to `{parts[0]}`", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
            elif len(parts) == 1 and parts[0].isdigit() and ctx.user_data.get('awaiting_ban'):
                ctx.user_data['awaiting_ban'] = False
                conn = sqlite3.connect('users.db')
                conn.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (int(parts[0]),))
                conn.commit(); conn.close()
                return await update.message.reply_text(f"🚫 User `{parts[0]}` banned.", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
        except: pass

    if text == "🟡 💰 BALANCE":
        user = get_user(user_id)
        return await update.message.reply_text(f"💎 **Balance:** {user[0]} Credits\n🔍 **Searches:** {user[1]}", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")

    # --- BUY CREDITS ---
    if text == "🟢 🛒 BUY CREDITS":
        kb = [
            [InlineKeyboardButton("💎 10 CR - ₹30", callback_data="buy_10"), InlineKeyboardButton("💎 25 CR - ₹70", callback_data="buy_25")],
            [InlineKeyboardButton("💎 50 CR - ₹130", callback_data="buy_50"), InlineKeyboardButton("💎 100 CR - ₹250", callback_data="buy_100")],
            [InlineKeyboardButton("👑 Contact Owner (Custom)", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}?text=I%20want%20custom%20credits")]
        ]
        return await update.message.reply_text("🛒 **BUY CREDITS**\n\nSelect a plan below:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    if text == "💻 ʙᴜʏ sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ":
        conn = sqlite3.connect('users.db')
        conn.execute("INSERT INTO src_requests (user_id, created_at) VALUES (?, ?)", (user_id, datetime.datetime.now().isoformat()))
        conn.commit(); conn.close()
        kb = [[InlineKeyboardButton("💬 Message Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]]
        return await update.message.reply_text(f"💻 **BUY SOURCE CODE** 💻\n\nPrice: ₹{SRC_PRICE}\n\n👇 Click below to message Owner:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    if text == "🔵 🔗 REFERRAL":
        bot_info = await ctx.bot.get_me()
        user = get_user(user_id)
        if user[5] == 1: return await update.message.reply_text("⚠️ **Aap ek hi ID ko refer kar sakte hain.**", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")
        else: return await update.message.reply_text(f"🔗 **Your Referral Link:**\n`https://t.me/{bot_info.username}?start={user_id}`\n\nShare and get 2 credits per join!", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")

    # --- PROMPTS ---
    if text in ["🟢 📱 NUMBER INFO", "🔵 🆔 AADHAAR INFO", "🟣 ✈️ TG TO NUMBER", "🟠 👨‍👩‍👧‍👦 FAMILY INFO"]:
        if not await is_user_joined(update, ctx): return
        if get_user(user_id)[0] <= 0: return await send_no_credit_msg(update, ctx)
        msg = {
            "🟢 📱 NUMBER INFO": "📱 **Send 10-digit Mobile Number:**\nExample: `9999911111`",
            "🔵 🆔 AADHAAR INFO": "🆔 **Send 12-digit Aadhaar:**\nExample: `123456789012`",
            "🟣 ✈️ TG TO NUMBER": "✈️ **Send Telegram ID:**\nExample: `8518042438`",
            "🟠 👨‍👩‍👧‍👦 FAMILY INFO": "👨‍👩‍👧‍👦 **Send 12-digit Aadhaar:**\nExample: `123456789012`"
        }[text]
        return await update.message.reply_text(msg, reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

    # --- ADMIN BUTTONS ---
    if is_admin(user_id):
        if text == "👑 ADMIN PANEL": return await admin_command(update, ctx)
        elif text == "♾️ UNLIMITED CREDITS":
            adjust_credits(user_id, 9999999)
            return await update.message.reply_text("♾️ **Unlimited Credits Added!**", reply_markup=get_admin_keyboard())
        elif text == "🟣 📊 RECORDS": return await admin_records(update, ctx)
        elif text == "🔵 📊 STATS": return await admin_stats(update, ctx)
        elif text == "🔵 ⚙️ API STATUS": return await admin_api_status(update, ctx)
        elif text == "🟢 💎 ADD POINTS": return await admin_add_credits_start(update, ctx)
        elif text == "🔴 ❌ REMOVE POINTS": return await admin_remove_credits_start(update, ctx)
        elif text == "🔴 🚫 BAN USER": 
            ctx.user_data['awaiting_ban'] = True
            return await admin_ban_start(update, ctx)
        elif text == "🟢 ✅ UNBAN USER": return await admin_unban_start(update, ctx)
        elif text == "🟡 📣 BROADCAST": return await admin_broadcast_start(update, ctx)

    # --- EXECUTION LOGIC ---
    clean_text = text.replace(" ", "").replace("-", "").strip()
    
    if clean_text.isdigit() and len(clean_text) == 10: await do_search_num(update, ctx, clean_text)
    elif clean_text.isdigit() and len(clean_text) == 12: await do_search_aadhar(update, ctx, clean_text)
    elif clean_text.isdigit() and len(clean_text) < 15: await do_search_tg(update, ctx, clean_text)

# --- SEARCH EXECUTORS ---
async def do_search_num(update, ctx, num):
    user_id = update.effective_user.id
    if get_user(user_id)[0] <= 0: return await send_no_credit_msg(update, ctx)
    msg = await update.message.reply_text(f"🔍 **Searching Number** `{num}`...", parse_mode="Markdown")
    deduct_credit(user_id); log_search(user_id, "NUMBER", num) 
    res = fetch_num(get_setting('num_api'), num)
    if not res: return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    out = f"🕵️‍♂️ **DATA FOUND**\n**Number:** `{num}`\n\n"
    for i, r in enumerate(res['results'][:3], 1):
        out += f"👤 **Record {i}**\n▪️ **Name:** {r.get('name')}\n▪️ **Father:** {r.get('fathersName')}\n▪️ **Aadhar:** {r.get('aadharNumber')}\n▪️ **Address:** {r.get('address')}\n\n"
    out += f"💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in 30s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

async def do_search_aadhar(update, ctx, num):
    user_id = update.effective_user.id
    if get_user(user_id)[0] <= 0: return await send_no_credit_msg(update, ctx)
    msg = await update.message.reply_text(f"🔍 **Searching Aadhar** `{num}`...", parse_mode="Markdown")
    deduct_credit(user_id); log_search(user_id, "AADHAR", num)
    res = fetch_num(get_setting('aadhar_api'), num)
    if not res: return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    out = f"🕵️‍♂️ **AADHAR FOUND**\n\n"
    for i, r in enumerate(res['results'][:3], 1):
        out += f"👤 **Record {i}**\n▪️ **Name:** {r.get('name')}\n▪️ **Mobile:** {r.get('phoneNumber')}\n▪️ **Address:** {r.get('address')}\n\n"
    out += f"💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in 30s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

async def do_search_tg(update, ctx, tid):
    user_id = update.effective_user.id
    if get_user(user_id)[0] <= 0: return await send_no_credit_msg(update, ctx)
    msg = await update.message.reply_text(f"✈️ **Searching TG ID** `{tid}`...", parse_mode="Markdown")
    deduct_credit(user_id); log_search(user_id, "TELEGRAM_ID", tid)
    res = fetch_tg(tid)
    if not res: return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    out = f"✈️ **TG DATA FOUND**\n🆔 **TG ID:** `{tid}`\n\n"
    for p in res.get("phone", [])[:5]: out += f"📱 `{p.get('country_code')}{p.get('number')}` ({p.get('country')})\n"
    out += f"\n💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in 30s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

# --- BUTTON CALLBACKS ---
async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    data = query.data; user_id = update.effective_user.id

    if data == "verify_join": await verify_join(update, ctx)
    elif data.startswith("buy_"):
        plan = PLANS.get(data.split("_")[1])
        if plan:
            upi_url = f"upi://pay?pa={UPI_ID}&pn={UPI_NAME.replace(' ', '%20')}&am={plan['price']}&cu=INR&tn=Buy%20Credits"
            qr = qrcode.make(upi_url)
            bio = BytesIO(); qr.save(bio, 'PNG'); bio.seek(0)
            
            kb = [[InlineKeyboardButton("📸 Upload Screenshot", callback_data=f"ss_{plan['credits']}_{plan['price']}")], [InlineKeyboardButton("👑 Contact Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}?text=I%20paid%20for%20{plan['credits']}%20credits")]]
            await query.message.reply_photo(photo=bio, caption=f"💰 **PAYMENT** 💰\n\n💎 **Plan:** {plan['credits']} Credits\n💵 **Amount:** ₹{plan['price']}\n\n👇 Scan QR & Pay, then upload screenshot.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    
    elif data.startswith("ss_"):
        _, cr, pr = data.split("_")
        ctx.user_data['awaiting_screenshot'] = {"credits": cr, "price": pr}
        await query.message.reply_text("📸 **Please upload your payment screenshot now.**", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        
    elif data.startswith("history_"):
        target_uid = data.split("_")[1]
        conn = sqlite3.connect('users.db'); c = conn.cursor()
        c.execute("SELECT search_type, search_query, search_date FROM search_history WHERE user_id=? ORDER BY id DESC LIMIT 15", (target_uid,))
        history = c.fetchall(); conn.close()
        if not history: return await query.answer("No history found for this user.", show_alert=True)
        text = f"🟣 *HISTORY* 🟣\n\n👤 User ID: `{target_uid}`\n\n"
        for h in history: text += f"🔹 **{h[0]}:** `{h[1]}`\n   📅 _{h[2]}_\n\n"
        await query.message.edit_text(text, parse_mode="Markdown")

# --- SCREENSHOT & APPROVAL ---
async def handle_screenshot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = ctx.user_data.get('awaiting_screenshot')
    if not data: return

    del ctx.user_data['awaiting_screenshot']
    photo_file_id = update.message.photo[-1].file_id
    user_name = update.effective_user.username or update.effective_user.first_name
    
    admin_msg = f"🧾 **NEW PAYMENT SCREENSHOT**\n\n👤 User: {user_name}\n🆔 ID: `{user_id}`\n💎 Plan: {data['credits']} Credits\n💵 Amount: ₹{data['price']}\n\n👇 Please verify payment."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"app_{user_id}_{data['credits']}"), InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_id}")]])
    
    try:
        await ctx.bot.send_photo(chat_id=SUPER_ADMIN_ID, photo=photo_file_id, caption=admin_msg, reply_markup=kb, parse_mode="Markdown")
        await update.message.reply_text("✅ **Screenshot sent to admin!**\n\nWait for approval, credits will be added soon.", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending to admin: {e}", parse_mode="Markdown")

# --- ADMIN CALLBACKS (Approve / Reject) ---
async def admin_approval_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    data = query.data
    
    if data.startswith("app_"):
        _, uid, cr = data.split("_")
        adjust_credits(int(uid), int(cr))
        try: await ctx.bot.send_message(int(uid), f"✅ **Payment Approved!**\n\n{cr} Credits added to your account.", parse_mode="Markdown")
        except: pass
        await query.edit_message_caption(caption=f"✅ **APPROVED**\nUser: `{uid}`\nCredits: {cr}", reply_markup=None, parse_mode="Markdown")
        
    elif data.startswith("rej_"):
        _, uid = data.split("_")
        kb = [[InlineKeyboardButton("👑 Contact Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]]
        try: await ctx.bot.send_message(int(uid), "❌ **Payment Rejected**\n\nContact owner for help.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
        await query.edit_message_caption(caption=f"❌ **REJECTED**\nUser: `{uid}`", reply_markup=None, parse_mode="Markdown")

# --- APP SETUP ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CallbackQueryHandler(admin_approval_handler, pattern="^(app_|rej_)"))
    
    app.add_handler(MessageHandler(filters.Regex("^🟢 💎 ADD POINTS$"), admin_add_credits_start))
    app.add_handler(MessageHandler(filters.Regex("^🔴 ❌ REMOVE POINTS$"), admin_remove_credits_start))
    app.add_handler(MessageHandler(filters.Regex("^🔴 🚫 BAN USER$"), admin_ban_start))
    app.add_handler(MessageHandler(filters.Regex("^🟢 ✅ UNBAN USER$"), admin_unban_start))
    app.add_handler(MessageHandler(filters.Regex("^🟡 📣 BROADCAST$"), admin_broadcast_start))
    app.add_handler(MessageHandler(filters.Regex("^🔵 📊 STATS$"), admin_stats))
    app.add_handler(MessageHandler(filters.Regex("^🟣 📊 RECORDS$"), admin_records))
    app.add_handler(MessageHandler(filters.Regex("^🔵 ⚙️ API STATUS$"), admin_api_status))
    
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("[*] Ultimate Pro Max Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
