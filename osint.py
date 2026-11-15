import requests
import sqlite3
import datetime
import time
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- TERA CONFIG ---
BOT_TOKEN = "8925056785:AAHfyM8UIpdOdbnenQbeik4JF-Z74HGaIpQ" 
SUPER_ADMIN_ID = 8786686789  
OWNER_USERNAME = "@heart_of_public" # Tera asli username
CHANNEL_1 = "@biggest_4_public" 
CHANNEL_2 = "@sufiyanr31" 
c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
# --- APIs ---
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
LINE_THIN = "─────────────────────"

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
            c.execute("UPDATE users SET credits = credits + 1 WHERE user_id=?", (refer_by,))
            c.execute("UPDATE users SET credits = credits + 1 WHERE user_id=?", (user_id,))
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
        [KeyboardButton("📱 ɴᴜᴍʙᴇʀ ɪɴꜰᴏ"), KeyboardButton("🆔 ᴀᴀᴅʜᴀᴀʀ ɪɴꜰᴏ")],
        [KeyboardButton("✈️ ᴛɢ ᴛᴏ ɴᴜᴍʙᴇʀ"), KeyboardButton("👨‍👩‍👧‍👦 ꜰᴀᴍɪʟʏ ɪɴꜰᴏ")],
        [KeyboardButton("🏦 ɪꜰꜱᴄ ᴄᴏᴅᴇ")],
        [KeyboardButton("💰 ʙᴀʟᴀɴᴄᴇ"), KeyboardButton("🛒 ʙᴜʏ ᴄʀᴇᴅɪᴛꜱ")],
        [KeyboardButton("🔗 ʀᴇꜰᴇʀʀᴀʟ"), KeyboardButton("👑 ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ")]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("🚫 ᴄᴀɴᴄᴇʟ")]], resize_keyboard=True)

def get_admin_keyboard():
    kb = [
        [KeyboardButton("📣 ʙʀᴏᴀᴅᴄᴀꜱᴛ"), KeyboardButton("📊 ꜱᴛᴀᴛꜱ")],
        [KeyboardButton("💎 ᴀᴅᴅ ᴘᴏɪɴᴛꜱ"), KeyboardButton("❌ ʀᴇᴍᴏᴠᴇ ᴘᴏɪɴᴛꜱ")],
        [KeyboardButton("🚫 ʙᴀɴ ᴜꜱᴇʀ"), KeyboardButton("✅ ᴜɴʙᴀɴ ᴜꜱᴇʀ")],
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

    # Yahan underscore fix karne ke liye <b> tag use kiya hai
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

async def verify_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_user_joined(update, ctx):
        await start(update, ctx)
        try: await query.message.delete()
        except: pass
    else:
        await query.answer("❌ Join both channels first!", show_alert=True)

# --- SEARCH HANDLERS ---
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if is_banned(user_id): return

    if text == "🚫 ᴄᴀɴᴄᴇʟ":
        await update.message.reply_text("Cancelled.", reply_markup=get_main_keyboard())
        return

    if text == "💰 ʙᴀʟᴀɴᴄᴇ":
        user = get_user(user_id)
        await update.message.reply_text(f"💎 **Balance:** {user[0]} Credits\n🔍 **Searches:** {user[1]}", reply_markup=get_main_keyboard(), parse_mode="Markdown")
        return

    if text == "🛒 ʙᴜʏ ᴄʀᴇᴅɪᴛꜱ":
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
        # Yahan bhi HTML parse mode use kiya hai
        await update.message.reply_text(buy_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    if text == "🔗 ʀᴇꜰᴇʀʀᴀʟ":
        bot_info = await ctx.bot.get_me()
        await update.message.reply_text(f"🔗 **Your Referral Link:**\n`https://t.me/{bot_info.username}?start={user_id}`\n\nShare and get 1 credit per join!", reply_markup=get_main_keyboard(), parse_mode="Markdown")
        return

    # --- PROMPTS ---
    if text == "📱 ɴᴜᴍʙᴇʀ ɪɴꜰᴏ":
        if not await is_user_joined(update, ctx): return
        if get_user(user_id)[0] <= 0: return await update.message.reply_text("❌ **0 Credits!** Buy first.", parse_mode="Markdown")
        await update.message.reply_text("📱 **Send 10-digit Mobile Number:**", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        return

    if text == "🆔 ᴀᴀᴅʜᴀᴀʀ ɪɴꜰᴏ":
        if not await is_user_joined(update, ctx): return
        if get_user(user_id)[0] <= 0: return await update.message.reply_text("❌ **0 Credits!** Buy first.", parse_mode="Markdown")
        await update.message.reply_text("🆔 **Send 12-digit Aadhaar:**", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        return

    if text == "✈️ ᴛɢ ᴛᴏ ɴᴜᴍʙᴇʀ":
        if not await is_user_joined(update, ctx): return
        if get_user(user_id)[0] <= 0: return await update.message.reply_text("❌ **0 Credits!** Buy first.", parse_mode="Markdown")
        await update.message.reply_text("✈️ **Send Telegram ID:**", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        return

    if text == "👨‍👩‍👧‍👦 ꜰᴀᴍɪʟʏ ɪɴꜰᴏ":
        if not await is_user_joined(update, ctx): return
        if get_user(user_id)[0] <= 0: return await update.message.reply_text("❌ **0 Credits!** Buy first.", parse_mode="Markdown")
        await update.message.reply_text("👨‍👩‍👧‍👦 **Send 12-digit Aadhaar:**", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        return

    if text == "🏦 ɪꜰꜱᴄ ᴄᴏᴅᴇ":
        if not await is_user_joined(update, ctx): return
        if get_user(user_id)[0] <= 0: return await update.message.reply_text("❌ **0 Credits!** Buy first.", parse_mode="Markdown")
        await update.message.reply_text("🏦 **Send IFSC Code:**", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
        return

    # --- EXECUTION LOGIC ---
    if text.isdigit() and len(text) == 10:
        await do_search_num(update, ctx, text)
    elif text.isdigit() and len(text) == 12:
        await do_search_aadhar(update, ctx, text)
    elif text.isdigit() and len(text) < 15:
        await do_search_tg(update, ctx, text)
    elif re.match(r'^[A-Za-z]{4}0[A-Za-z0-9]{6}$', text):
        await do_search_ifsc(update, ctx, text)

# --- SEARCH EXECUTORS ---
async def do_search_num(update, ctx, num):
    user_id = update.effective_user.id
    msg = await update.message.reply_text(f"🔍 **Searching Number** `{num}`...", parse_mode="Markdown")
    deduct_credit(user_id)
    
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
    
    res = fetch_ifsc(code)
    if not res:
        adjust_credits(user_id, 1)
        return await msg.edit_text("❌ **Data Not Found.** Credit refunded.", parse_mode="Markdown")
    
    out = f"🏦 **IFSC INFO**\n\n🔢 **Code:** `{code}`\n"
    bank_data = res.get("data", {})
    for k, v in bank_data.items():
        out += f"🏛️ **Bank:** {v.get('bank')}\n🏢 **Branch:** {v.get('branch')}\n📍 **Address:** {v.get('address')}\n"
        break
    
    out += f"\n💳 **Left:** {get_user(user_id)[0]}\n⏱️ _Auto-deletes in 30s_"
    await msg.edit_text(out, parse_mode="Markdown")
    asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))

# --- ADMIN PANEL ---
async def admin_panel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("⚙️ **Admin Control Panel**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

# --- BUTTON CALLBACKS ---
async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "verify_join":
        await verify_join(update, ctx)
    elif data.startswith("buy_"):
        points = data.split("_")[1]
        prices = {"10": 30, "25": 70, "50": 130, "100": 250}
        price = prices.get(points, 0)
        
        await query.message.edit_text(
            f"✅ **Request Sent!**\n\n💎 **Plan:** {points} Credits\n💰 **Price:** ₹{price}\n\n"
            f"Contact <b>{OWNER_USERNAME}</b> to pay and get credits.", 
            parse_mode="HTML"
        )
        try:
            await ctx.bot.send_message(
                SUPER_ADMIN_ID, 
                f"🔔 **New Buy Request!**\nUser ID: `{user_id}`\nPlan: {points} CR\nPrice: ₹{price}", 
                parse_mode="Markdown"
            )
        except: pass

# --- APP SETUP ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("[*] Ultimate Pro Max Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
