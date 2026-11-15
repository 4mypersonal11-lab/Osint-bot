import requests
import sqlite3
import datetime
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- CONFIG ---
BOT_TOKEN = "8925056785:AAFND7fUvLnX5M5hYXmzxZyNl9Uc7_h5AKs"
SUPER_ADMIN_ID = 8786686789  
CHANNEL_1 = "@biggest_4_public" 
CHANNEL_2 = "@sufiyanr31"  
ADMIN_USERNAME = "@Heart_of_public"

QR_CODE_FILE_ID = "https://i.ibb.co/6PZ8Z9Q/upi-qr.png" 

DEFAULT_NUM_API = "https://sra-num-aadhar-info-api-main-two.vercel.app/search?q="
DEFAULT_AADHAR_API = "https://sra-num-aadhar-info-api-main-rose.vercel.app/search?q="

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, 
        credits INTEGER, 
        total_searches INTEGER DEFAULT 0,
        join_date TEXT,
        refer_by INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit()
    
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (SUPER_ADMIN_ID,))
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('num_api', ?)", (DEFAULT_NUM_API,))
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('aadhar_api', ?)", (DEFAULT_AADHAR_API,))
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    val = c.fetchone()
    conn.close()
    return val[0] if val else ""

def set_setting(key, value):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT credits, total_searches, join_date, refer_by FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res

def add_user(user_id, refer_by=0):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, credits, join_date, refer_by) VALUES (?, ?, ?, ?)", (user_id, 10, date, refer_by))
        conn.commit()
        
        if refer_by != 0:
            c.execute("UPDATE users SET credits = credits + 2 WHERE user_id=?", (refer_by,))
            c.execute("UPDATE users SET credits = credits + 2 WHERE user_id=?", (user_id,))
            conn.commit()
    conn.close()

def update_credits(user_id, amount, action='add'):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if action == 'add':
        c.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
    else:
        c.execute("UPDATE users SET credits = credits - ? WHERE user_id = ? AND credits >= ?", (amount, user_id, amount))
    conn.commit()
    conn.close()

def increment_search(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET total_searches = total_searches + 1, credits = credits - 1 WHERE user_id=?", (user_id,))
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

def get_all_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

# --- DOUBLE FORCE JOIN CHECK ---
async def is_user_joined(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member1 = await ctx.bot.get_chat_member(chat_id=CHANNEL_1, user_id=user_id)
        is_in_c1 = member1.status in ['member', 'administrator', 'creator']
        
        member2 = await ctx.bot.get_chat_member(chat_id=CHANNEL_2, user_id=user_id)
        is_in_c2 = member2.status in ['member', 'administrator', 'creator']
        
        return is_in_c1 and is_in_c2
    except Exception as e:
        print(f"Force Join Error: {e}")
        return False 

# --- AUTO DELETE FUNCTION ---
async def auto_delete_message(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    await asyncio.sleep(60)
    try:
        await ctx.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

# --- API FETCH FUNCTION WITH RETRY ---
def fetch_api_data(api_url, query):
    response = None
    for attempt in range(3):
        try:
            r = requests.get(f"{api_url}{query}", timeout=90)
            if r.status_code == 200:
                response = r.json()
                break
        except requests.exceptions.RequestException:
            time.sleep(2)
    return response

# --- USER COMMANDS ---
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    refer_by = 0
    if ctx.args and ctx.args[0].startswith("ref"):
        try: refer_by = int(ctx.args[0].replace("ref", ""))
        except: pass

    add_user(user_id, refer_by)
    
    if not await is_user_joined(update, ctx):
        keyboard = [
            [InlineKeyboardButton("🔴 Join Channel 1", url=f"https://t.me/{CHANNEL_1.replace('@', '')}")],
            [InlineKeyboardButton("🔴 Join Channel 2", url=f"https://t.me/{CHANNEL_2.replace('@', '')}")],
            [InlineKeyboardButton("🟢 ✅ Verify Join", callback_data="verify_join")]
        ]
        await update.message.reply_text(
            "⚠️ <b>Access Denied!</b>\n\nYou must join <b>BOTH</b> our official channels to use this bot.",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
        )
        return

    keyboard = [
        [InlineKeyboardButton("🟢 📱 Search Number", callback_data="search_num"), InlineKeyboardButton("🔵 🆔 Search Aadhar", callback_data="search_aadhar")],
        [InlineKeyboardButton("🟡 👤 My Profile", callback_data="my_profile"), InlineKeyboardButton("🟢 💳 Buy Credits", callback_data="buy_credits")],
        [InlineKeyboardButton("🔴 🎁 Refer & Earn", callback_data="refer_earn")]
    ]
    await update.message.reply_text(
        f"🕵️‍♂️ <b>OSINT Pro Bot</b>\n\n"
        f"Welcome to the most advanced OSINT bot!\n"
        f"Select an option below to get started.",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
    )

# --- PROFILE COMMAND (Yahan fix kar diya hai) ---
async def user_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    if not user_data:
        await update.message.reply_text("Please /start the bot first.")
        return
    
    credits, searches, join_date, _ = user_data
    text = (
        f"👤 <b>Your Profile</b>\n\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"💳 <b>Credits:</b> {credits}\n"
        f"🔍 <b>Total Searches:</b> {searches}\n"
        f"📅 <b>Joined:</b> {join_date}"
    )
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# --- ADMIN PANEL ---
async def admin_panel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
        
    keyboard = [
        [InlineKeyboardButton("🟢 ➕ Add Credit 💳", callback_data="adm_add_credit"), InlineKeyboardButton("🔴 ➖ Remove Credit 💳", callback_data="adm_rem_credit")],
        [InlineKeyboardButton("🟡 📢 Broadcast", callback_data="adm_broadcast"), InlineKeyboardButton("🔵 👥 User List", callback_data="adm_users")],
        [InlineKeyboardButton("🟣 🔗 Number API", callback_data="adm_num_api"), InlineKeyboardButton("🟠 🔗 Aadhar API", callback_data="adm_aadhar_api")],
        [InlineKeyboardButton("🟢 👑 Add Admin", callback_data="adm_add_admin"), InlineKeyboardButton("🔴 🚫 Remove Admin", callback_data="adm_rem_admin")],
        [InlineKeyboardButton("⚙️ API Status Check", callback_data="adm_api_status")]
    ]
    await update.message.reply_text("⚙️ <b>Admin Control Panel</b>\nSelect an action:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# --- MAIN MESSAGE HANDLER ---
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if is_admin(user_id) and ':' in text:
        parts = text.split(':', 1)
        action = parts[0].strip().lower()
        value = parts[1].strip()
        
        if action == "addcredit":
            try:
                uid, amt = value.split()
                update_credits(int(uid), int(amt), 'add')
                await update.message.reply_text(f"✅ Added {amt} credits to {uid}")
                return
            except: pass
        elif action == "remcredit":
            try:
                uid, amt = value.split()
                update_credits(int(uid), int(amt), 'remove')
                await update.message.reply_text(f"✅ Removed {amt} credits from {uid}")
                return
            except: pass
        elif action == "setnumapi":
            set_setting('num_api', value)
            await update.message.reply_text("✅ Number API Updated!")
            return
        elif action == "setaadharapi":
            set_setting('aadhar_api', value)
            await update.message.reply_text("✅ Aadhar API Updated!")
            return
        elif action == "addadmin":
            try:
                conn = sqlite3.connect('users.db')
                conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (int(value),))
                conn.commit(); conn.close()
                await update.message.reply_text(f"✅ User {value} is now Admin!")
                return
            except: pass
        elif action == "remadmin":
            try:
                conn = sqlite3.connect('users.db')
                conn.execute("DELETE FROM admins WHERE user_id=?", (int(value),))
                conn.commit(); conn.close()
                await update.message.reply_text(f"✅ Admin {value} removed!")
                return
            except: pass
        elif action == "broadcast":
            users = get_all_users()
            success = 0
            msg = await update.message.reply_text("⏳ Broadcasting...")
            for u in users:
                try:
                    await ctx.bot.send_message(chat_id=u, text=f"📢 <b>Announcement:</b>\n\n{value}", parse_mode="HTML")
                    success += 1
                except: pass
            await msg.edit_text(f"✅ Broadcast sent to {success} users.")
            return

    if text.startswith('/'): return
    
    if not await is_user_joined(update, ctx):
        keyboard = [
            [InlineKeyboardButton("🔴 Join Channel 1", url=f"https://t.me/{CHANNEL_1.replace('@', '')}")],
            [InlineKeyboardButton("🔴 Join Channel 2", url=f"https://t.me/{CHANNEL_2.replace('@', '')}")],
            [InlineKeyboardButton("🟢 ✅ Verify Join", callback_data="verify_join")]
        ]
        await update.message.reply_text(
            "⚠️ <b>You must join our channels first!</b>",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
        )
        return

    user_data = get_user(user_id)
    if not user_data: return
    credits = user_data[0]
    
    if credits <= 0:
        await update.message.reply_text("❌ <b>You have 0 credits!</b>\n\nClick Buy Credits to purchase.", parse_mode="HTML")
        return

    # --- SMART SEARCH LOGIC ---
    if text.isdigit() and len(text) == 10:
        number = text
        msg = await update.message.reply_text(f"🔍 <b>Searching Mobile Number</b> <code>{number}</code>... Please wait.", parse_mode="HTML")
        
        api_base = get_setting('num_api')
        response = fetch_api_data(api_base, number)
        
        if not response or not response.get("success"):
            await msg.edit_text("❌ <b>Data Not Found.</b> API is not responding or no records exist.", parse_mode="HTML")
            return

        if response.get("count", 0) > 0:
            results = response.get("results", [])
            report = f"🕵️‍♂️ <b>MOBILE DATA FOUND</b>\n<b>Number:</b> <code>{number}</code>\n\n"
            
            for i, data in enumerate(results, 1):
                report += f"👤 <b>Record {i}</b>\n"
                report += f"▪️ <b>Name:</b> {data.get('name', 'N/A')}\n"
                report += f"▪️ <b>Father:</b> {data.get('fathersName', 'N/A')}\n"
                report += f"▪️ <b>Aadhar:</b> {data.get('aadharNumber', 'N/A')}\n"
                report += f"▪️ <b>Alt Number:</b> {data.get('otherNumber', 'N/A')}\n"
                report += f"▪️ <b>Address:</b> {data.get('address', 'N/A')}\n"
                report += f"▪️ <b>District:</b> {data.get('district', 'N/A')}\n"
                report += f"▪️ <b>State:</b> {data.get('state', 'N/A')}\n"
                report += f"▪️ <b>Source:</b> {data.get('source', 'N/A')}\n\n"
            
            increment_search(user_id)
            new_credits = get_user(user_id)[0]
            report += f"💳 <b>Remaining Credits:</b> {new_credits}"
            report += f"\n\n⚠️ <i>This message will auto-delete in 60 seconds.</i>"
            
            await msg.edit_text(report, parse_mode="HTML", disable_web_page_preview=True)
            asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))
        else:
            await msg.edit_text("❌ <b>Data Not Found.</b> No records exist for this mobile number.", parse_mode="HTML")

    elif text.isdigit() and len(text) == 12:
        aadhar = text
        msg = await update.message.reply_text(f"🔍 <b>Searching Aadhar Number</b> <code>{aadhar}</code>... Please wait.", parse_mode="HTML")
        
        api_base = get_setting('aadhar_api')
        response = fetch_api_data(api_base, aadhar)
        
        if not response or not response.get("success"):
            await msg.edit_text("❌ <b>Data Not Found.</b> Aadhar API is not responding or no records exist.", parse_mode="HTML")
            return

        if response.get("count", 0) > 0:
            results = response.get("results", [])
            report = f"🕵️‍♂️ <b>AADHAR DATA FOUND</b>\n<b>Aadhar:</b> <code>{aadhar}</code>\n\n"
            
            for i, data in enumerate(results, 1):
                report += f"👤 <b>Record {i}</b>\n"
                report += f"▪️ <b>Name:</b> {data.get('name', 'N/A')}\n"
                report += f"▪️ <b>Father:</b> {data.get('fathersName', 'N/A')}\n"
                report += f"▪️ <b>Mobile:</b> {data.get('phoneNumber', 'N/A')}\n"
                report += f"▪️ <b>Alt Number:</b> {data.get('otherNumber', 'N/A')}\n"
                report += f"▪️ <b>Address:</b> {data.get('address', 'N/A')}\n"
                report += f"▪️ <b>District:</b> {data.get('district', 'N/A')}\n"
                report += f"▪️ <b>State:</b> {data.get('state', 'N/A')}\n\n"
            
            increment_search(user_id)
            new_credits = get_user(user_id)[0]
            report += f"💳 <b>Remaining Credits:</b> {new_credits}"
            report += f"\n\n⚠️ <i>This message will auto-delete in 60 seconds.</i>"
            
            await msg.edit_text(report, parse_mode="HTML", disable_web_page_preview=True)
            asyncio.create_task(auto_delete_message(ctx, update.effective_chat.id, msg.message_id))
        else:
            await msg.edit_text("❌ <b>Data Not Found.</b> No records exist for this Aadhar number.", parse_mode="HTML")
            
    else:
        await update.message.reply_text("❌ <b>Invalid Format!</b>\nPlease enter a valid 10-digit Mobile Number or 12-digit Aadhar Number.", parse_mode="HTML")

# --- BUTTONS HANDLER ---
async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "verify_join":
        if await is_user_joined(update, ctx):
            keyboard = [
                [InlineKeyboardButton("🟢 📱 Search Number", callback_data="search_num"), InlineKeyboardButton("🔵 🆔 Search Aadhar", callback_data="search_aadhar")],
                [InlineKeyboardButton("🟡 👤 My Profile", callback_data="my_profile"), InlineKeyboardButton("🟢 💳 Buy Credits", callback_data="buy_credits")],
                [InlineKeyboardButton("🔴 🎁 Refer & Earn", callback_data="refer_earn")]
            ]
            await query.message.edit_text("✅ <b>Verification Successful!</b>\nSelect an option below:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            await query.message.edit_text("❌ <b>You haven't joined both channels yet!</b>\nPlease join and verify again.", parse_mode="HTML")
    
    elif data == "main_menu":
        await start(update, ctx)
    
    elif data == "search_num":
        await query.message.edit_text("📱 <b>Please type the 10-digit mobile number to search:</b>", parse_mode="HTML")
        
    elif data == "search_aadhar":
        await query.message.edit_text("🆔 <b>Please type the 12-digit Aadhar number to search:</b>", parse_mode="HTML")
        
    elif data == "my_profile":
        user_data = get_user(user_id)
        if user_data:
            credits, searches, join_date, _ = user_data
            text = (
                f"👤 <b>Your Profile</b>\n\n"
                f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
                f"💳 <b>Credits:</b> {credits}\n"
                f"🔍 <b>Total Searches:</b> {searches}\n"
                f"📅 <b>Joined:</b> {join_date}"
            )
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            await query.answer("User data not found. Please type /start", show_alert=True)
        
    elif data == "buy_credits":
        text = (
            "💳 <b>Buy Credits</b>\n\n"
            "10 Credits = ₹10 (₹1 per search)\n\n"
            "👇 <b>To purchase credits, contact the owner directly:</b>\n"
            f"👑 <b>Owner:</b> {ADMIN_USERNAME}\n\n"
            "⚡ <i>(Malik se mil 😎, screenshot bhejo aur turant credits pao!)</i>"
        )
        keyboard = [[InlineKeyboardButton("🟢 💬 Message Owner", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]]
        
        try:
            await query.message.reply_photo(photo=QR_CODE_FILE_ID, caption=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "refer_earn":
        bot_info = await ctx.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref{user_id}"
        text = (
            f"🎁 <b>Refer & Earn</b>\n\n"
            f"Invite your friends using the link below.\n"
            f"When they join, you both get <b>2 Free Credits!</b>\n\n"
            f"🔗 <code>{ref_link}</code>"
        )
        await query.message.edit_text(text, parse_mode="HTML")

    elif data.startswith("adm_") and is_admin(user_id):
        if data == "adm_users":
            users = get_all_users()
            await query.message.edit_text(f"👥 <b>Total Users:</b> {len(users)}", parse_mode="HTML")
        elif data == "adm_add_credit":
            await query.message.edit_text("🟢 <b>To add credits, type:</b>\n<code>addcredit USER_ID AMOUNT</code>", parse_mode="HTML")
        elif data == "adm_rem_credit":
            await query.message.edit_text("🔴 <b>To remove credits, type:</b>\n<code>remcredit USER_ID AMOUNT</code>", parse_mode="HTML")
        elif data == "adm_broadcast":
            await query.message.edit_text("📢 <b>To broadcast, type:</b>\n<code>broadcast YOUR MESSAGE</code>", parse_mode="HTML")
        elif data == "adm_num_api":
            await query.message.edit_text("🔗 <b>To set Number API:</b>\n<code>setnumapi YOUR_API_LINK</code>", parse_mode="HTML")
        elif data == "adm_aadhar_api":
            await query.message.edit_text("🔗 <b>To set Aadhar API:</b>\n<code>setaadharapi YOUR_API_LINK</code>", parse_mode="HTML")
        elif data == "adm_add_admin":
            await query.message.edit_text("👑 <b>To add admin:</b>\n<code>addadmin USER_ID</code>", parse_mode="HTML")
        elif data == "adm_rem_admin":
            await query.message.edit_text("🚫 <b>To remove admin:</b>\n<code>remadmin USER_ID</code>", parse_mode="HTML")
        elif data == "adm_api_status":
            msg = await query.message.edit_text("⚙️ Checking API Status...")
            api_base = get_setting('num_api')
            try:
                r = requests.get(f"{api_base}9876543210", timeout=20)
                if r.status_code == 200:
                    await msg.edit_text("✅ <b>Number API is Online and Working!</b>", parse_mode="HTML")
                else:
                    await msg.edit_text(f"⚠️ <b>API responded with status code:</b> {r.status_code}", parse_mode="HTML")
            except Exception as e:
                await msg.edit_text(f"❌ <b>API is Down!</b> Error: {e}", parse_mode="HTML")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("profile", user_profile)) # Ye ab fix hai
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("[*] Ultimate OSINT Pro Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()