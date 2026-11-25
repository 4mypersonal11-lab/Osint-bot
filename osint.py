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

# --- RAILWAY VARIABLES ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "8786686789"))
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@heart_of_public")
CHANNEL_1 = os.getenv("CHANNEL_1", "@biggest_4_public")
CHANNEL_2 = os.getenv("CHANNEL_2", "@sufiyanr31")
UPI_ID = os.getenv("UPI_ID", "trillionadillllxyz@fam")
UPI_NAME = os.getenv("UPI_NAME", "Mohammad Adil")
SRC_PRICE = int(os.getenv("SRC_PRICE", "1499"))
TG_NUM_API_URL = os.getenv("TG_NUM_API_URL", "https://tele-to-phone.felixrdx.xyz/api/developer/Cyb3rB4nn3r/fast")
TG_NUM_API_KEY = os.getenv("TG_NUM_API_KEY", "ba76fa0f97264dea84364ca1df91a2e8")
DEFAULT_NUM_API = os.getenv("DEFAULT_NUM_API", "https://sra-num-aadhar-info-api-main-two.vercel.app/search?q=")
DEFAULT_AADHAR_API = os.getenv("DEFAULT_AADHAR_API", "https://sra-num-aadhar-info-api-main-rose.vercel.app/search?q=")
AUTO_DELETE_SECONDS = int(os.getenv("AUTO_DELETE_SECONDS", "30"))

# --- PLANS ---
PLANS = {
    "10": {"credits": 10, "price": 30},
    "25": {"credits": 25, "price": 70},
    "50": {"credits": 50, "price": 130},
    "100": {"credits": 100, "price": 250},
}

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, credits INTEGER, total_searches INTEGER DEFAULT 0, join_date TEXT, refer_by INTEGER DEFAULT 0, join_bonus_claimed INTEGER DEFAULT 0, has_referred INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS search_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, search_type TEXT, search_query TEXT, search_date TEXT)''')
    conn.commit()
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (SUPER_ADMIN_ID,))
    conn.commit(); conn.close()
init_db()

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
    conn.close()

def adjust_credits(user_id, amount):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
    conn.commit(); conn.close()

def deduct_credit(user_id):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("UPDATE users SET credits = credits - 1, total_searches = total_searches + 1 WHERE user_id=? AND credits > 0", (user_id,))
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
        [KeyboardButton("🏠 MAIN MENU")]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# --- START COMMAND ---
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banned(user_id): return await update.message.reply_text("🚫 Banned.", parse_mode="Markdown")
    add_user(user_id)
    user = get_user(user_id)

    if not await is_user_joined(update, ctx):
        kb = [[InlineKeyboardButton("🔴 Join Channel 1", url=f"https://t.me/{CHANNEL_1.replace('@', '')}")], [InlineKeyboardButton("🔴 Join Channel 2", url=f"https://t.me/{CHANNEL_2.replace('@', '')}")], [InlineKeyboardButton("✅ VERIFY", callback_data="verify_join")]]
        return await update.message.reply_text("⚠️ Join both channels first!", reply_markup=InlineKeyboardMarkup(kb))

    text = f"🔥 *PREMIUM OSINT BOT* 🔥\n\n⭐ *User ID:* `{user_id}`\n💎 *Credits:* {user[0]}\n👑 *Owner:* {OWNER_USERNAME}"
    await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")

# --- BUTTON HANDLER ---
async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "verify_join":
        if await is_user_joined(update, ctx):
            await query.message.delete(); await start(update, ctx)
        else: await query.answer("Join first!", show_alert=True)

    elif data.startswith("buy_"):
        plan = PLANS.get(data.split("_")[1])
        if plan:
            upi_url = f"upi://pay?pa={UPI_ID}&pn={UPI_NAME.replace(' ', '%20')}&am={plan['price']}&cu=INR"
            qr = qrcode.make(upi_url)
            bio = BytesIO(); qr.save(bio, 'PNG'); bio.seek(0)
            kb = [[InlineKeyboardButton("📸 Send Screenshot", callback_data=f"ss_{plan['credits']}_{plan['price']}")]]
            await query.message.reply_photo(photo=bio, caption=f"Pay ₹{plan['price']} for {plan['credits']} Credits.", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("ss_"):
        _, cr, pr = data.split("_")
        ctx.user_data['awaiting_screenshot'] = {"credits": cr, "price": pr}
        await query.message.reply_text("📸 Send payment screenshot now.", reply_markup=get_cancel_keyboard())

    elif data.startswith("approve_"):
        _, uid, cr = data.split("_")
        adjust_credits(int(uid), int(cr))
        await query.edit_message_caption(caption=f"✅ Approved! {cr} credits added to `{uid}`.")

    elif data.startswith("reject_"):
        _, uid = data.split("_")
        await query.edit_message_caption(caption=f"❌ Rejected for `{uid}`.")

# --- TEXT HANDLER ---
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if is_banned(user_id): return

    if text in ["🔴 🚫 CANCEL", "🏠 MAIN MENU"]: return await start(update, ctx)

    if text == "🟡 💰 BALANCE":
        user = get_user(user_id)
        return await update.message.reply_text(f"💎 Balance: {user[0]} Credits", reply_markup=get_main_keyboard(user_id))

    if text == "🟢 🛒 BUY CREDITS":
        kb = [[InlineKeyboardButton("💎 10 CR - ₹30", callback_data="buy_10")]]
        return await update.message.reply_text("🛒 Select plan:", reply_markup=InlineKeyboardMarkup(kb))

    # (Baaki search logic yahan aayega, par main isko short rakha hai spam hatane ke liye)

# --- SCREENSHOT HANDLER ---
async def handle_screenshot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = ctx.user_data.get('awaiting_screenshot')
    if not data: return
    del ctx.user_data['awaiting_screenshot']
    photo_file_id = update.message.photo[-1].file_id
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"approve_{update.effective_user.id}_{data['credits']}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_{update.effective_user.id}")]])
    await ctx.bot.send_photo(chat_id=SUPER_ADMIN_ID, photo=photo_file_id, caption=f"Screenshot from {update.effective_user.id}", reply_markup=kb)

# --- FORCE CLEAN DESCRIPTION (Anti-Hijack) ---
async def clear_spam(application: Application):
    try:
        # Ye bot start hote hi kisi bhi gande link ko hamesha ke liye hata dega
        await application.bot.set_my_description(description="Welcome to Premium OSINT Bot!")
        await application.bot.set_my_short_description(short_description="Premium OSINT Bot")
        print("[*] Description cleaned safely.")
    except Exception as e:
        print(f"Error: {e}")

# --- MAIN ---
def main():
    # post_init use karke bot start hote hi description clear kar rahe hain
    app = Application.builder().token(BOT_TOKEN).post_init(clear_spam).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()

if __name__ == "__main__":
    main()
