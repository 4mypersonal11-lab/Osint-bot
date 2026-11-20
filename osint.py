import requests
import sqlite3
import datetime
import time
import asyncio
import re
import os
import json
import xml.etree.ElementTree as ET
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- TERA CONFIG ---
BOT_TOKEN = "8925056785:AAGlI7iIew5bfcrxFebmhg00-0DD8b9NnR8" 
SUPER_ADMIN_ID = 8786686789  
OWNER_USERNAME = "@heart_of_public" 
CHANNEL_1 = "@biggest_4_public" 
CHANNEL_2 = "@sufiyanr31" 

# --- PAYMENT CONFIG ---
UPI_ID = "trillionadillllxyz@fam" 
UPI_NAME = "Mohammad Adil"
SRC_PRICE = 1499

# --- TERI APIs ---
DEFAULT_NUM_API = "https://sra-num-aadhar-info-api-main-two.vercel.app/search?q="
DEFAULT_AADHAR_API = "https://sra-num-aadhar-info-api-main-rose.vercel.app/search?q="
TG_NUM_API_URL = "https://tele-to-phone.felixrdx.xyz/api/developer/Cyb3rB4nn3r/fast"
TG_NUM_API_KEY = "ba76fa0f97264dea84364ca1df91a2e8"
AADHAAR_FAMILY_API = "https://addhartofam.fuckyoubitch.workers.dev/family"
IFSC_API_URL = "https://authapisellhub.shop/api.php"
IFSC_API_KEY = "c8511bdd2cef1cc5507372a5a2afaabafd47265f841e5da95ea3540b9f07d8e6"

# --- VEHICLE API CONFIG ---
VEHICLE_UPSTREAM = "https://horizon.policyboss.com:5443/quote/vehicle_info_loggedin"
SECRET_KEY = "SECRET-HZ07QRWY-JIBT-XRMQ-ZP95-J0RWP3DYRACW"
CLIENT_KEY = "CLIENT-CNTP6NYE-CU9N-DUZW-CSPI-SH1IS4DOVHB9"
SOURCE = "PB-BETA"
VEHICLE_COST = 1 # Vehicle info ka 1 credit katega

AUTO_DELETE_SECONDS = 30

# --- NEW PLANS ---
PLANS = {
    "num_10": {"type": "Number Info", "credits": 10, "price": 50},
    "num_25": {"type": "Number Info", "credits": 25, "price": 125},
    "num_50": {"type": "Number Info", "credits": 50, "price": 249},
    "num_100": {"type": "Number Info", "credits": 100, "price": 399},
    "veh_10": {"type": "Vehicle Info", "credits": 10, "price": 50},
    "veh_25": {"type": "Vehicle Info", "credits": 25, "price": 125},
    "veh_50": {"type": "Vehicle Info", "credits": 50, "price": 249},
    "veh_100": {"type": "Vehicle Info", "credits": 100, "price": 399},
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
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def deduct_credit(user_id, amount=1):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits - ?, total_searches = total_searches + 1 WHERE user_id=? AND credits >= ?", (amount, user_id, amount))
    conn.commit()
    conn.close()

def log_search(user_id, search_type, query):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO search_history (user_id, search_type, search_query, search_date) VALUES (?, ?, ?, ?)", (user_id, search_type, query, date))
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

def fetch_ifsc(ifsc):
    try:
        r = requests.get(f"{IFSC_API_URL}?api_key={IFSC_API_KEY}&service=ifsc_info&input={ifsc}", timeout=25).json()
        return r if r.get("success") == True else None
    except: return None

# --- VEHICLE API HELPERS ---
_local = threading.local()
REGEX_STRIP = re.compile(r"[\s\-]+")

def _session() -> requests.Session:
    s = getattr(_local, "sess", None)
    if s is None:
        s = requests.Session()
        s.headers.update({
            "Content-Type": "application/json;charset=utf-8", "Accept": "application/json",
            "Origin": "https://www.policyboss.com", "Referer": "https://www.policyboss.com/car-insurance",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        })
        s.cookies.set("source", SOURCE)
        _local.sess = s
    return s

def normalize_number(number: str) -> str:
    return REGEX_STRIP.sub("", number or "").upper()

def generate_all_variants(number: str):
    n = normalize_number(number)
    variants = []
    def add(v):
        v = normalize_number(v)
        if v and v not in variants: variants.append(v)
    add(n)
    m_bh = re.match(r"^(\d{2})BH(\d{1,4})([A-Z]{1,2})$", n)
    if m_bh:
        yy, num, series = m_bh.groups()
        add(f"{yy}BH{num}{series}")
        add(f"{yy}BH{num.zfill(4)}{series}")
        if len(series) == 2: add(f"{yy}BH{num}{series[0]}")
        else:
            for c in "ABCDEFGHJKLMNPQRSTUVWXYZ": add(f"{yy}BH{num}{series}{c}")
    m_std = re.match(r"^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{1,4})$", n)
    if m_std:
        st, rto, ser, num = m_std.groups()
        for rto_v in {rto, rto.zfill(2)}:
            for num_v in {num, num.zfill(4)}:
                if ser: add(f"{st}{rto_v}{ser}{num_v}")
                else:
                    for c in "ABCDEFGHJKLMNPQRSTUVWXYZ": add(f"{st}{rto_v}{c}{num_v}")
    return variants

def clean_upstream(raw: dict) -> dict:
    junk = {"Ip_Address", "Calling_Source", "Product_Id_Request", "Ss_Id", "Channel", "Is_LM", "FastLaneId", "Match_Mode", "FastlaneResponse", "FastlaneResponse_Obj"}
    no_vahan = raw.get("0") == "N" or all(k.isdigit() for k in list(raw)[:6])
    out = {k: v for k, v in raw.items() if k not in junk and not k.isdigit()}
    out["found"] = not no_vahan and bool(out.get("Make_Name"))
    return out

def fetch_vehicle_info(number: str):
    variants = generate_all_variants(number)
    for v in variants[:10]:
        payload = {"secret_key": SECRET_KEY, "client_key": CLIENT_KEY, "RegistrationNumber": v, "product_id": 1, "ss_id": 0, "source": SOURCE, "session_id": ""}
        try:
            resp = _session().post(VEHICLE_UPSTREAM, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                result = clean_upstream(data)
                if result.get("found"):
                    return result, v
        except: pass
    return None, None

# --- KEYBOARDS ---
def get_main_keyboard(user_id):
    kb = [
        [KeyboardButton("🟢 📱 NUMBER INFO"), KeyboardButton("🔵 🆔 AADHAAR INFO")],
        [KeyboardButton("🟣 ✈️ TG TO NUMBER"), KeyboardButton("🟠 👨‍👩‍👧‍👦 FAMILY INFO")],
        [KeyboardButton("🔴 🏦 IFSC CODE"), KeyboardButton("🚗 🚘 VEHICLE INFO")],
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
        [InlineKeyboardButton("📱 Number Info Credits", callback_data="buy_cat_num")],
        [InlineKeyboardButton("🚗 Vehicle Info Credits", callback_data="buy_cat_veh")],
        [InlineKeyboardButton("👑 Contact Owner (Custom)", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}?text=I%20want%20to%20buy%20custom%20credits")]
    ]
    text = (
        f"❌ **0 Credits!**\n\n"
        f"Pehle credit buy kar fir search kar ladle 😎🤌\n\n"
        f"👇 *Select your required category:*"
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
    if ctx.args and ctx.args[0].isdigit(): refer_by = int(ctx.args[0])
    
    add_user(user_id, refer_by)
    user = get_user(user_id)

    if not await is_user_joined(update, ctx):
        kb = [
            [InlineKeyboardButton("🔴 Join Channel 1", url=f"https://t.me/{CHANNEL_1.replace('@', '')}")],
            [InlineKeyboardButton("🔴 Join Channel 2", url=f"https://t.me/{CHANNEL_2.replace('@', '')}")],
            [InlineKeyboardButton("🟢 ✅ VERIFY JOIN", callback_data="verify_join")]
        ]
        await update.message.reply_text(f"╭━━━━━━━━━━━━━━━━━━╮\n   ⚠️ *{scp('ACCESS DENIED')}* ⚠️\n╰━━━━━━━━━━━━━━━━━━╯\n\nBhai pehle dono channel join kar, fir verify kar. Uske baad hi bot chalega!", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    text = (
        f"╭━━━━━━━━━━━━━━━━━━╮\n   🔥 *{scp('PREMIUM OSINT BOT')}* 🔥\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
        f"✨ *{scp('Welcome')}, {update.effective_user.first_name}!*\n\n"
        f"⭐ *{scp('User ID')}:* `{user_id}`\n"
        f"💎 *{scp('Credits')}:* {user[0]}\n"
        f"👑 *{scp('Owner')}:* <b>{OWNER_USERNAME}</b>\n\n"
        f"{LINE}\n"
        f"🛡️ *{scp('Services')}:*\n• 📱 {scp('Number Info')}\n• 🚗 {scp('Vehicle Info')}\n• 🆔 {scp('Aadhaar Info')}\n• ✈️ {scp('TG to Number')}\n• 👨‍👩‍👧‍👦 {scp('Family Info')}\n• 🏦 {scp('IFSC Code')}\n\n"
        f"{LINE}\n⚡ *{scp('Cost')}:* 1 {scp('Credit/Search')}\n\n👇 *{scp('Use buttons below to start')}*"
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
        text = f"╭━━━━━━━━━━━━━━━━━━╮\n   👑 *{scp('CONTACT ADMIN')}* 👑\n╰━━━━━━━━━━━━━━━━━━╯\n\nClick the button below to directly message the owner for credits or help."
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
    
    text = f"╭━━━━━━━━━━━━━━━━━━╮\n   ⚙️ *{scp('API STATUS')}* ⚙️\n╰━━━━━━━━━━━━━━━━━━╯\n\n📱 *Number API:* {num_status}\n🆔 *Aadhar API:* {aadhar_status}\n\n🔄 _Ping Check Complete_"
    await msg.edit_text(text, parse_mode="Markdown")

# --- HANDLE TEXT INPUTS (Admin & User) ---
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if is_banned(user_id): return

    if text == "🔴 🚫 CANCEL" or text == "🏠 MAIN MENU":
        await start(update, ctx)
        return

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
            [InlineKeyboardButton("📱 Number Info Credits", callback_data="buy_cat_num")],
            [InlineKeyboardButton("🚗 Vehicle Info Credits", callback_data="buy_cat_veh")],
            [InlineKeyboardButton("👑 Contact Owner (Custom)", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}?text=I%20want%20to%20buy%20custom%20credits")]
        ]
        buy_text = f"╭━━━━━━━━━━━━━━━━━━╮\n   🛒 *{scp('BUY CREDITS')}* 🛒\n╰━━━━━━━━━━━━━━━━━━╯\n\nFirst select which credits you want to buy:\n👇 *Select Category:*"
        await update.message.reply_text(buy_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    # --- BUY SOURCE CODE LOGIC ---
    if text == "💻 ʙᴜʏ sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ":
        conn = sqlite3.connect('users.db')
        conn.execute("INSERT INTO src_requests (user_id, created_at) VALUES (?, ?)", (user_id, datetime.datetime.now().isoformat()))
        conn.commit(); conn.close()
        
        kb = [[InlineKeyboardButton("💬 Message Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]]
        src_text = f"╭━━━━━━━━━━━━━━━━━━╮\n   💻 *{scp('BUY SOURCE CODE')}* 💻\n╰━━━━━━━━━━━━━━━━━━╯\n\nGet the full source code of this bot!\n\n👑 **Price:** ₹{SRC_PRICE}\n\n👇 *Click below to message Owner:*"
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

    # --- PROMPTS ---
    if text in ["🟢 📱 NUMBER INFO", "🔵 🆔 AADHAAR INFO", "🟣 ✈️ TG TO NUMBER", "🟠 👨‍👩‍👧‍👦 FAMILY INFO", "🔴 🏦 IFSC CODE", "🚗 🚘 VEHICLE INFO"]:
        if not await is_user_joined(update, ctx): return
        
        cost = VEHICLE_COST if text == "🚗 🚘 VEHICLE INFO" else 1
        if get_user(user_id)[0] < cost:
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
        elif text == "🚗 🚘 VEHICLE INFO":
            await update.message.reply_text("🚗 **Send Vehicle Number:**\n\nExample: `MH12AB1234`", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
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
    elif re.match(r'^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{1,4}$', clean_text) or 'BH' in clean_text:
        # Vehicle format check
        await do_search_vehicle(update, ctx, clean_text)

# --- SEARCH EXECUTORS ---
async def do_search_num(update, ctx, num):
    user_id = update.effective_user.id
    if get_user(user_id)[0] < 1: return await send_no_credit_msg(update, ctx)
    
    msg = await update.message.reply_text(f"🔍 **Searching Number** `{num}`...", parse_mode="Markdown")
    deduct_credit(user_id)
    log_search(user_id, "NUMBER", num) 
    
    res = fetch_num(get_setting('num_api'), num)
    if not res: return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    
    out = f"🕵️‍♂️ **DATA FOUND**\n**Number:** `{num}`\n\n"
    for i, r in enumerate(res['results'][:3], 1):
        out += f"👤 **Record {i}**\n▪️ **Name:** {r.get('name')}\n▪️ **Father:** {r.get('fathersName')}\n▪️ **Aadhar:** {r.get('aadharNumber')}\n▪️ **Address:** {r.get('address')}\n\n"
    out += f"💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in 30s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

async def do_search_vehicle(update, ctx, num):
    user_id = update.effective_user.id
    if get_user(user_id)[0] < VEHICLE_COST: return await send_no_credit_msg(update, ctx)
    
    msg = await update.message.reply_text(f"🚗 **Searching Vehicle** `{num}`...\n_Please wait, trying formats._", parse_mode="Markdown")
    deduct_credit(user_id, VEHICLE_COST)
    log_search(user_id, "VEHICLE", num)
    
    result, matched = fetch_vehicle_info(num)
    if not result:
        return await msg.edit_text(f"❌ **Vehicle Not Found** for `{num}`.", parse_mode="Markdown")
    
    out = f"🚗 **VEHICLE INFO FOUND**\n**Matched As:** `{matched}`\n\n"
    fields = [
        ("Make_Name", "Company"), ("Model_Name", "Model"), ("Vehicle_Model", "Variant"),
        ("Fuel_Type", "Fuel"), ("Registration_Date", "Reg. Date"), ("Vehicle_Age", "Age"),
        ("Vehicle_Color", "Color"), ("Chassis_Number", "Chassis No."), ("Engine_Number", "Engine No."),
        ("Cubic_Capacity", "CC"), ("Seating_Capacity", "Seating"), ("Vehicle_Type", "Type"),
        ("RTO_Code", "RTO Code"), ("RTO_Location", "RTO Location"), ("State", "State"),
        ("Owner_Name", "Owner"), ("Insurance_Company", "Ins. Co."), ("Policy_Expiry_Date", "Policy Expiry")
    ]
    for key, label in fields:
        if key in result and result[key] not in (None, "", "NA", "null"):
            out += f"▪️ **{label}:** `{result[key]}`\n"
            
    out += f"\n💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in 30s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

async def do_search_aadhar(update, ctx, num):
    user_id = update.effective_user.id
    if get_user(user_id)[0] < 1: return await send_no_credit_msg(update, ctx)
    msg = await update.message.reply_text(f"🔍 **Searching Aadhar** `{num}`...", parse_mode="Markdown")
    deduct_credit(user_id)
    log_search(user_id, "AADHAR", num)
    
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
    if get_user(user_id)[0] < 1: return await send_no_credit_msg(update, ctx)
    msg = await update.message.reply_text(f"✈️ **Searching TG ID** `{tid}`...", parse_mode="Markdown")
    deduct_credit(user_id)
    log_search(user_id, "TELEGRAM_ID", tid)
    
    res = fetch_tg(tid)
    if not res: return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    
    out = f"✈️ **TG DATA FOUND**\n🆔 **TG ID:** `{tid}`\n\n"
    phones = res.get("phone", [])
    for p in phones[:5]: out += f"📱 `{p.get('country_code')}{p.get('number')}` ({p.get('country')})\n"
    out += f"\n💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in 30s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

async def do_search_ifsc(update, ctx, code):
    user_id = update.effective_user.id
    if get_user(user_id)[0] < 1: return await send_no_credit_msg(update, ctx)
    msg = await update.message.reply_text(f"🏦 **Searching IFSC** `{code}`...", parse_mode="Markdown")
    deduct_credit(user_id)
    log_search(user_id, "IFSC", code)
    
    res = fetch_ifsc(code)
    if not res: return await msg.edit_text("❌ **Data Not Found.**", parse_mode="Markdown")
    
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
        
    elif data == "buy_cat_num":
        kb = [
            [InlineKeyboardButton("💎 10 CR - ₹50", callback_data="buy_num_10"), InlineKeyboardButton("💎 25 CR - ₹125", callback_data="buy_num_25")],
            [InlineKeyboardButton("💎 50 CR - ₹249", callback_data="buy_num_50"), InlineKeyboardButton("💎 100 CR - ₹399", callback_data="buy_num_100")],
            [InlineKeyboardButton("👑 Contact Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}?text=I%20want%20custom%20Number%20Info%20credits")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_buy")]
        ]
        await query.message.edit_text("📱 **Number Info Credits Plans:**\n\nSelect a plan to buy:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        
    elif data == "buy_cat_veh":
        kb = [
            [InlineKeyboardButton("💎 10 CR - ₹50", callback_data="buy_veh_10"), InlineKeyboardButton("💎 25 CR - ₹125", callback_data="buy_veh_25")],
            [InlineKeyboardButton("💎 50 CR - ₹249", callback_data="buy_veh_50"), InlineKeyboardButton("💎 100 CR - ₹399", callback_data="buy_veh_100")],
            [InlineKeyboardButton("👑 Contact Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}?text=I%20want%20custom%20Vehicle%20Info%20credits")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_buy")]
        ]
        await query.message.edit_text("🚗 **Vehicle Info Credits Plans:**\n\nSelect a plan to buy:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        
    elif data == "back_buy":
        kb = [
            [InlineKeyboardButton("📱 Number Info Credits", callback_data="buy_cat_num")],
            [InlineKeyboardButton("🚗 Vehicle Info Credits", callback_data="buy_cat_veh")],
            [InlineKeyboardButton("👑 Contact Owner (Custom)", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}?text=I%20want%20custom%20credits")]
        ]
        await query.message.edit_text("🛒 **BUY CREDITS**\n\nFirst select which credits you want to buy:\n👇 *Select Category:*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("buy_num_") or data.startswith("buy_veh_"):
        plan_key = data.replace("buy_", "")
        if plan_key in PLANS:
            plan = PLANS[plan_key]
            msg_text = f"I want to buy {plan['credits']} {plan['type']} Credits for ₹{plan['price']}"
            kb = [[InlineKeyboardButton("💬 Pay & Message Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}?text={msg_text.replace(' ', '%20')}")]]
            pay_text = f"╭━━━━━━━━━━━━━━━━━━╮\n   💰 *{scp('PAYMENT')}* 💰\n╰━━━━━━━━━━━━━━━━━━╯\n\n💎 **Plan:** {plan['credits']} {plan['type']} Credits\n💵 **Amount:** ₹{plan['price']}\n\n👇 *Click below to pay & message owner:*"
            await query.message.edit_text(pay_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            
    elif data.startswith("history_"):
        target_uid = data.split("_")[1]
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT search_type, search_query, search_date FROM search_history WHERE user_id=? ORDER BY id DESC LIMIT 15", (target_uid,))
        history = c.fetchall()
        conn.close()

        if not history: return await query.answer("No history found for this user.", show_alert=True)

        text = f"╭━━━━━━━━━━━━━━━━━━╮\n   🟣 *{scp('HISTORY')}* 🟣\n╰━━━━━━━━━━━━━━━━━━╯\n\n👤 User ID: `{target_uid}`\n\n"
        for h in history: text += f"🔹 **{h[0]}:** `{h[1]}`\n   📅 _{h[2]}_\n\n"
        await query.message.edit_text(text, parse_mode="Markdown")

# --- APP SETUP ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    
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
