import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, InlineQueryResultArticle, InputTextMessageContent
from pymongo import MongoClient
import datetime
import requests
import threading
import time
import random
import uuid

# === PYDROID 3 DNS FIX ===
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1'] 
# ==========================

# ==========================================
# ⚙️ CONFIGURATION & MONGODB SETUP
# ==========================================
CONFIG = {
    "BOT_TOKEN": "9276888973:AAFoTKyBwNSyGpQYoo2-cZmk5hakBlUd2MA",
    "ADMIN_ID": 8798465416,  
    "BOT_USERNAME": "Redcube_giftbot", 
    
    # 🔴 PREMIUM EMOJIS IDs
    "TEXT_EMOJI": {
        "CHICK": "5282918917788935437", 
        "GIFT": "5846184826184408721",
        "STAR": "5798819377088307477", 
        "PROFILE": "5258011929993026890",
        "WELCOME": "5436203513149404753",    
        "SUCCESS": "5798517767304912593",    
        "ERROR": "5210952531676504517",     
        "TICKET": "5431653802753159903",    
        "DOWN": "5231102735817918643",      
        "LUCK": "5258040062028822951",      
        "WIN": "6041731551845159060",       
        "LOSE": "5314535215731857373",      
        "REFUND": "5904223745752439710"
    },
    "BTN_EMOJI": {
        "PROFILE": "12345678901", "GIFT": "12345678902", "STAR": "12345678906",
        "HELP": "12345678907", "LANG": "12345678908", "BACK": "12345678909",
        "CANCEL": "12345678910", "PROMO": "12345678911", "LUCK": "12345678912",
        "CHECK": "12345678913"
    },
    
    # 🛠️ REAL GIFT MAPPING
    "REAL_GIFT_IDS": {
        "Teddy bear": "5170233102089322756", 
        "Heart": "5170145012310081615",        
        "Rose": "5168103777563050263", 
        "Gift box": "5170250947678437525",   
        "Champagne": "6028601630662853006", 
        "Rocket": "5170564780938756245",     
        "Bouquet": "5170314324215857265", 
        "Cake": "5170144170496491616",        
        "Diamond": "5170521118301225164", 
        "Ring": "5170690322832818290",        
        "Trophy": "5168043875654172773"        
    }
}

# 🛠 MONGODB CONNECTION
MONGO_URI = "mongodb+srv://Cricket_231:Rohit1616%40@zolmdho.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["StarGift5BotDB"]
users_col = db["users"]
promos_col = db["promos"]
gifts_catalog_col = db["gifts_catalog"]
bot_config_col = db["bot_config"] 
checks_col = db["checks"]
group_activity_col = db["group_activity"]
rains_col = db["rains"]
pending_rains_col = db["pending_rains"]

bot = telebot.TeleBot(CONFIG["BOT_TOKEN"], parse_mode="HTML", threaded=True)

# 🛠 DEFAULT GIFTS SEEDING
if gifts_catalog_col.count_documents({}) == 0:
    default_gifts = [
        {"name": "Champagne", "id": CONFIG["REAL_GIFT_IDS"]["Champagne"], "price": 48},
        {"name": "Diamond", "id": CONFIG["REAL_GIFT_IDS"]["Diamond"], "price": 98},
        {"name": "Ring", "id": CONFIG["REAL_GIFT_IDS"]["Ring"], "price": 98},
        {"name": "Trophy", "id": CONFIG["REAL_GIFT_IDS"]["Trophy"], "price": 98},
        {"name": "Rocket", "id": CONFIG["REAL_GIFT_IDS"]["Rocket"], "price": 48},
        {"name": "Bouquet", "id": CONFIG["REAL_GIFT_IDS"]["Bouquet"], "price": 48},
        {"name": "Cake", "id": CONFIG["REAL_GIFT_IDS"]["Cake"], "price": 48},
        {"name": "Rose", "id": CONFIG["REAL_GIFT_IDS"]["Rose"], "price": 23},
        {"name": "Gift box", "id": CONFIG["REAL_GIFT_IDS"]["Gift box"], "price": 23},
        {"name": "Teddy bear", "id": CONFIG["REAL_GIFT_IDS"]["Teddy bear"], "price": 1},
        {"name": "Heart", "id": CONFIG["REAL_GIFT_IDS"]["Heart"], "price": 1}
    ]
    gifts_catalog_col.insert_many(default_gifts)
else:
    for gift_name, correct_id in CONFIG["REAL_GIFT_IDS"].items():
        gifts_catalog_col.update_one({"name": {"$regex": f"^{gift_name}$", "$options": "i"}}, {"$set": {"id": correct_id}}, upsert=False)

# ==========================================
# 🛡 DATABASE HELPERS
# ==========================================
def get_user(user_id, username=None):
    user = users_col.find_one({"_id": user_id})
    if not user:
        user = {"_id": user_id, "username": username, "lang": "en", "balance": 0, "bought_teddy": False, "bought_heart": False}
        users_col.insert_one(user)
    return user

def update_balance(user_id, amount):
    users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})

def update_house_bal(amount):
    bot_config_col.update_one({"_id": "house"}, {"$inc": {"balance": amount}}, upsert=True)

def get_house_bal():
    doc = bot_config_col.find_one({"_id": "house"})
    return doc["balance"] if doc else 0

# ==========================================
# 🎁 REAL TELEGRAM GIFT SENDER FUNCTION
# ==========================================
def send_real_telegram_gift(chat_id, gift_name, amount, comment=None):
    url = f"https://api.telegram.org/bot{CONFIG['BOT_TOKEN']}/sendGift"
    
    g = gifts_catalog_col.find_one({"name": {"$regex": f"^{gift_name}$", "$options": "i"}})
    gift_id = g["id"] if g else CONFIG["REAL_GIFT_IDS"].get(gift_name, "INVALID_ID")
    
    payload = {"user_id": chat_id, "gift_id": gift_id}
    if comment:
        payload["text"] = comment

    try:
        res = requests.post(url, json=payload, timeout=5).json()
    except:
        res = {"ok": False, "description": "API connection error"}
    
    if res.get("ok"):
        update_house_bal(-amount)
        msg = f"<tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['SUCCESS']}'>✅</tg-emoji> <b>Congratulations!</b>\n\n<tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['GIFT']}'>🎁</tg-emoji> You just received a real <b>{gift_name}</b> gift on your profile!"
        try: bot.send_message(chat_id, msg)
        except Exception: pass 
        return True
    else:
        update_balance(chat_id, amount)
        err = res.get("description", "Unknown error")
        msg = (
            f"<tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['ERROR']}'>❌</tg-emoji> <b>Gift Delivery Failed!</b>\n\n"
            f"<tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['REFUND']}'>💸</tg-emoji> <b>Refund Processed:</b> {amount} <tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['STAR']}'>⭐️</tg-emoji> returned to your wallet.\n"
            f"<i>Reason: {err}</i>"
        )
        try: bot.send_message(chat_id, msg)
        except Exception: pass 
        return False

# ==========================================
# 🌍 LANGUAGE & TEXT
# ==========================================
TE = CONFIG["TEXT_EMOJI"]
BE = CONFIG["BTN_EMOJI"]

def get_start_text(lang, name, balance):
    if lang == "en":
        return (
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='{TE['CHICK']}'>🐣</tg-emoji> <b>Hello, {name}!</b>\n\n"
            f"<tg-emoji emoji-id='{TE['GIFT']}'>🎁</tg-emoji> <b>Buy a Gift</b> for yourself!\n\n"
            f"<tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji> Your balance: <b>{balance}</b> <tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji>\n\n"
            f"<tg-emoji emoji-id='{TE['DOWN']}'>👇</tg-emoji> <b>Choose an action from the menu below:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        return (
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='{TE['CHICK']}'>🐣</tg-emoji> <b>Привет, {name}!</b>\n\n"
            f"<tg-emoji emoji-id='{TE['GIFT']}'>🎁</tg-emoji> <b>Купить подарок</b> для себя!\n\n"
            f"<tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji> Ваш баланс: <b>{balance}</b> <tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji>\n\n"
            f"<tg-emoji emoji-id='{TE['DOWN']}'>👇</tg-emoji> <b>Выберите действие из меню ниже:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )

LANG = {
    "en": {
        "profile_text": f"<tg-emoji emoji-id='{TE['PROFILE']}'>🕵️‍♂️</tg-emoji> <b>Your Profile</b>\n\n🆔 ID: <code>{{id}}</code>\n👤 Username: @{{username}}\n<tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji> Balance: <b>{{balance}}</b> <tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji>",
        "topup_text": "Choose a top-up amount or enter your own number of stars below:",
        "gift_text": f"<tg-emoji emoji-id='{TE['GIFT']}'>🎁</tg-emoji> <b>Gift Catalog</b>\n\nChoose a gift to buy for yourself:",
        "promo_text": f"<tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji> <tg-emoji emoji-id='{TE['TICKET']}'>🎟</tg-emoji> <b>Enter your Promo Code:</b>\n\nPlease send the promo code in the chat below.",
        "luck_text": f"🍀 <b>Slot Game</b>\n\nRoll the 🎰 and win big rewards!\n\n<tg-emoji emoji-id='{TE['DOWN']}'>👇</tg-emoji> Select your bet:",
        "btn_profile": "Profile / Balance", "btn_send_gift": "Buy Gift", "btn_luck": "Luck",
        "btn_help": "Help / Support", "btn_lang": "🇷🇺 Switch to Russian", "btn_topup": "Top Up Balance",
        "btn_promo": "Promo Codes", "btn_back": "Back", "btn_cancel": "Cancel",
        "check_claim": "Claim ⭐️", "rain_claim": "Start Bot to Claim Gift 🎁"
    },
    "ru": {
        "profile_text": f"<tg-emoji emoji-id='{TE['PROFILE']}'>🕵️‍♂️</tg-emoji> <b>Ваш Профиль</b>\n\n🆔 ID: <code>{{id}}</code>\n👤 Юзернейм: @{{username}}\n<tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji> Баланс: <b>{{balance}}</b> <tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji>",
        "topup_text": "Выберите сумму пополнения или введите свое количество звезд ниже:",
        "gift_text": f"<tg-emoji emoji-id='{TE['GIFT']}'>🎁</tg-emoji> <b>Каталог Подарков</b>\n\nВыберите подарок для себя:",
        "promo_text": f"<tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji> <tg-emoji emoji-id='{TE['TICKET']}'>🎟</tg-emoji> <b>Введите ваш промокод:</b>\n\nОтправьте код ниже.",
        "luck_text": f"🍀 <b>Слот Игра</b>\n\nКрути 🎰 и выигрывай!\n\n<tg-emoji emoji-id='{TE['DOWN']}'>👇</tg-emoji> Выберите ставку:",
        "btn_profile": "Профиль / Баланс", "btn_send_gift": "Купить Подарок", "btn_luck": "Удача",
        "btn_help": "Поддержка", "btn_lang": "🇬🇧 Switch to English", "btn_topup": "Пополнить Баланс",
        "btn_promo": "Промокоды", "btn_back": "Назад", "btn_cancel": "Отмена",
        "check_claim": "Забрать ⭐️", "rain_claim": "Запустите бота, чтобы забрать 🎁"
    }
}

# ==========================================
# 🎛 KEYBOARDS (STYLED WITH COLORS & AUTO-URL)
# ==========================================
def btn(text: str, data: str = None, style: str = None, url: str = None, icon: str = None):
    b = InlineKeyboardButton(text=str(text))
    
    # 🔴 FIX: Auto detect URL if data starts with http (Solves Cinex Support link issue)
    if data and data.startswith("http"):
        url = data
        data = None

    if url: 
        b.url = str(url)
    else: 
        b.callback_data = str(data) if data else "noop"
        
    if icon and icon in BE: 
        b.custom_emoji_id = BE[icon]
        
    if style:
        setattr(b, 'style', style) 
        setattr(b, 'color', style)
    return b

def kb(*rows):
    m = InlineKeyboardMarkup()
    for row in rows:
        row_btns = []
        for item in row:
            if len(item) >= 4: row_btns.append(btn(item[0], item[1], style=item[2], icon=item[3]))
            elif len(item) == 3: row_btns.append(btn(item[0], item[1], style=item[2]))
            elif len(item) == 2: row_btns.append(btn(item[0], item[1]))
            elif len(item) == 1: row_btns.append(btn(item[0], item[0]))
        if row_btns:
            m.row(*row_btns)
    return m

def main_menu_kb(l):
    t = LANG[l]
    return kb(
        [(t["btn_profile"], "menu_profile", "primary", "PROFILE"), (t["btn_send_gift"], "menu_gifts", "success", "GIFT")],
        [(t["btn_luck"], "menu_luck", None, "LUCK")],
        [(t["btn_help"], "https://t.me/Cinex", "danger", "HELP"), (t["btn_lang"], "switch_lang", "primary", "LANG")]
    )

def profile_kb(l):
    t = LANG[l]
    return kb(
        [(t["btn_topup"], "menu_topup", "success", "STAR"), (t["btn_promo"], "menu_promo", "primary", "PROMO")],
        [(t["btn_back"], "menu_main", "danger", "BACK")]
    )

def topup_kb(l):
    t = LANG[l]
    return kb(
        [("25", "pay_25", "primary", "STAR"), ("50", "pay_50", None, "STAR")],
        [("100", "pay_100", "success", "STAR"), ("150", "pay_150", "primary", "STAR")],
        [(t["btn_cancel"], "menu_profile", "danger", "CANCEL")]
    )

def luck_kb(l):
    t = LANG[l]
    return kb(
        [("6 ⭐️", "slot_6", "primary", "STAR"), ("10 ⭐️", "slot_10", None, "STAR")],
        [("20 ⭐️", "slot_20", "success", "STAR")],
        [(t["btn_back"], "menu_main", "danger", "BACK")]
    )

def slot_options_kb(bet, l):
    rows = []
    if bet == 6:
        rows.append([("Any Combo (Win Rose)", "slotbet_6_rose", "primary"), ("Unique Combo (Win Teddy)", "slotbet_6_teddy", "success")])
    elif bet == 10:
        rows.append([("Win Flower", "slotbet_10_flower", "primary"), ("Win Rose", "slotbet_10_rose", "success")])
    elif bet == 20:
        rows.append([("Win Ring", "slotbet_20_ring", "primary"), ("Win Flower", "slotbet_20_flower", "success")])
        
    rows.append([(LANG[l]["btn_back"], "menu_luck", "danger", "BACK")])
    return kb(*rows)

def gifts_kb(lang_code, user):
    t = LANG[lang_code]
    m = InlineKeyboardMarkup()
    all_gifts = list(gifts_catalog_col.find())
    
    for i, g in enumerate(all_gifts):
        price = g["price"]
        # 1-star logic inside inline menu only
        if g["name"].lower() == "teddy bear" and user.get("bought_teddy"): price = 14
        if g["name"].lower() == "heart" and user.get("bought_heart"): price = 14
        
        # Applying alternating colors to list
        style = "primary" if i % 2 == 0 else "success"
        # 🔴 FIX: Explicitly passing keyword args so CANCEL doesn't become URL
        m.row(btn(f"{g['name']} - {price}", data=f"buyg|{g['name']}|{price}", style=style, icon="GIFT"))
        
    m.row(btn(t["btn_cancel"], data="menu_main", style="danger", icon="CANCEL"))
    return m

# ==========================================
# 👑 ADMIN COMMANDS
# ==========================================
@bot.message_handler(commands=['qpromo'])
def admin_promo(message):
    if message.from_user.id != CONFIG["ADMIN_ID"]: return
    try:
        _, code, amount, users, hours = message.text.split()
        expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=int(hours))
        promos_col.update_one({"_id": code.upper()}, {"$set": {"amount": int(amount), "max_users": int(users), "used_by": [], "expires_at": expires}}, upsert=True)
        bot.reply_to(message, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> Promo {code.upper()} created!")
    except ValueError:
        bot.reply_to(message, "❌ Invalid! Use: `/qpromo CODE AMOUNT USERS HOURS`", parse_mode="Markdown")

@bot.message_handler(commands=['addgift'])
def admin_addgift(message):
    if message.from_user.id != CONFIG["ADMIN_ID"]: return
    try:
        parts = message.text.split(" ", 3)
        gift_name = parts[1].replace("_", " ") 
        gift_id = parts[2]
        amount = int(parts[3])
        gifts_catalog_col.update_one({"name": gift_name}, {"$set": {"id": gift_id, "price": amount}}, upsert=True)
        bot.reply_to(message, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> <b>Gift Added!</b>\nName: {gift_name}\nID: <code>{gift_id}</code>\nPrice: {amount} ⭐️")
    except Exception:
        bot.reply_to(message, "❌ Format: `/addgift Gift_Name Gift_ID Amount`", parse_mode="Markdown")

@bot.message_handler(commands=['giftsend'])
def admin_giftsend(message):
    if message.from_user.id != CONFIG["ADMIN_ID"]: return
    try:
        parts = message.text.split(" ", 3)
        target = parts[1]
        gift_name = parts[2].replace("_", " ")
        comment = parts[3] if len(parts) > 3 else None

        u = users_col.find_one({"username": target.replace("@", "")}) if target.startswith("@") else users_col.find_one({"_id": int(target)})
        if not u: return bot.reply_to(message, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> User not found in database.")

        bot.reply_to(message, "Sending gift...")
        g = gifts_catalog_col.find_one({"name": {"$regex": f"^{gift_name}$", "$options": "i"}})
        price = g["price"] if g else 0
        actual_name = g["name"] if g else gift_name
        threading.Thread(target=send_real_telegram_gift, args=(u["_id"], actual_name, price, comment)).start()
        bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> Gift {actual_name} action triggered to {target}!")
    except Exception:
        bot.reply_to(message, "❌ Format: `/giftsend UserID_or_@User Gift_Name Comment`", parse_mode="Markdown")

@bot.message_handler(commands=['housebal'])
def public_housebal(message):
    bot.reply_to(message, f"<tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji> <b>Bot's Reserve Balance:</b> {get_house_bal()} Stars")

@bot.message_handler(commands=['topup'])
def admin_topup(message):
    if message.from_user.id != CONFIG["ADMIN_ID"]: return
    try:
        parts = message.text.split()
        amount = int(parts[1])
        update_house_bal(amount)
        bot.reply_to(message, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> Successfully added {amount} ⭐️ to the Bot Reserve. Current balance: {get_house_bal()} ⭐️")
    except Exception:
        bot.reply_to(message, "❌ Format: `/topup Amount`")

@bot.message_handler(commands=['broadcast'])
def admin_broadcast(message):
    if message.from_user.id != CONFIG["ADMIN_ID"]: return
    if not message.reply_to_message and len(message.text.split()) < 2:
        return bot.reply_to(message, "Reply to a message or type text after /broadcast.")
    users = users_col.find()
    bot.reply_to(message, "Broadcast started...")
    for u in users:
        try:
            if message.reply_to_message: bot.copy_message(u["_id"], message.chat.id, message.reply_to_message.message_id)
            else: bot.send_message(u["_id"], message.text.split(maxsplit=1)[1])
        except: pass
    bot.reply_to(message, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> Broadcast Complete!")

# ==========================================
# 🌧 GROUP RAIN & LEADERBOARD COMMANDS
# ==========================================
@bot.message_handler(commands=['rain'])
def rain_command(message):
    if message.chat.type == "private": return bot.reply_to(message, "Use this command in a group!")
    
    try:
        parts = message.text.split(maxsplit=3)
        if len(parts) < 3:
            raise ValueError("Not enough arguments")
        gift_name = parts[1].replace("_", " ")
        winners_count = int(parts[2])
        comment = parts[3] if len(parts) > 3 else "Group Rain Gift!"
    except Exception:
        return bot.reply_to(message, "❌ <b>Format:</b> <code>/rain Gift_Name Amount_of_Winners Comment</code>\n<b>Example:</b> <code>/rain Heart 1 Happy</code>", parse_mode="HTML")
        
    g = gifts_catalog_col.find_one({"name": {"$regex": f"^{gift_name}$", "$options": "i"}})
    if not g: return bot.reply_to(message, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> Gift not found!")
    
    actual_gift_name = g["name"]
    gift_unit_price = g["price"]
    
    if actual_gift_name.lower() in ["teddy bear", "heart"] and gift_unit_price == 1:
        gift_unit_price = 14
        
    total_cost = gift_unit_price * winners_count
    user = get_user(message.from_user.id)
    
    if user["balance"] < total_cost:
        return bot.reply_to(message, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Insufficient stars!</b>\nAvailable balance: {user['balance']} ⭐️\nNeeded ({gift_unit_price} ⭐️ × {winners_count} winners): {total_cost} ⭐️")
    
    active_users = list(group_activity_col.find({"chat_id": message.chat.id, "user_id": {"$ne": message.from_user.id}}))
    if len(active_users) < winners_count:
        return bot.reply_to(message, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> Not enough active users in this group to rain on!")
        
    update_balance(message.from_user.id, -total_cost)
    winners = random.sample(active_users, winners_count)
    
    rains_col.update_one(
        {"chat_id": message.chat.id, "user_id": message.from_user.id},
        {"$inc": {"spent": total_cost}, "$set": {"username": message.from_user.username or message.from_user.first_name}},
        upsert=True
    )
    
    announcement = f"🌧 <b>{message.from_user.first_name} is raining {winners_count}x {actual_gift_name}!</b>\n\n🏆 <b>Winners:</b>\n"
    for i, w in enumerate(winners, 1):
        uname = f"@{w['username']}" if w.get("username") else f"<a href='tg://user?id={w['user_id']}'>User</a>"
        announcement += f"{i}. {uname}\n"
        
    bot.send_message(message.chat.id, announcement, parse_mode="HTML")
    
    def handle_rain_winner(wid, wname, group_id):
        u_doc = users_col.find_one({"_id": wid})
        blocked = False
        if not u_doc:
            blocked = True
        else:
            try:
                bot.send_chat_action(wid, 'typing')
            except Exception:
                blocked = True
                
        if blocked:
            rain_id = str(uuid.uuid4().hex)[:8]
            pending_rains_col.insert_one({"_id": rain_id, "user_id": wid, "gift_name": actual_gift_name, "price": gift_unit_price, "comment": comment})
            
            markup = kb([(LANG["en"]["rain_claim"], f"https://t.me/{CONFIG['BOT_USERNAME']}?start=rain_{rain_id}", "success")])
            bot.send_message(group_id, f"Hey <a href='tg://user?id={wid}'>{wname}</a>, you won a <b>{actual_gift_name}</b>! Start the bot to claim.", reply_markup=markup, parse_mode="HTML")
        else:
            send_real_telegram_gift(wid, actual_gift_name, gift_unit_price, comment)

    for w in winners:
        threading.Thread(target=handle_rain_winner, args=(w["user_id"], w.get("username", "User"), message.chat.id)).start()

@bot.message_handler(commands=['rainlb'])
def rainlb_command(message):
    if message.chat.type == "private": return
    
    top_rainers = list(rains_col.find({"chat_id": message.chat.id}).sort("spent", -1).limit(10))
    if not top_rainers: return bot.reply_to(message, "No rainers in this group yet!")
    
    text = f"🌧 <b>Top Rainers in Group</b>\n\n"
    for idx, r in enumerate(top_rainers, 1):
        text += f"{idx}. {r.get('username', 'Unknown')} - {r['spent']} ⭐️\n"
        
    bot.reply_to(message, text)

# ==========================================
# 💸 INLINE DM CHECKS
# ==========================================
@bot.inline_handler(lambda query: len(query.query.split()) >= 1)
def inline_checks(inline_query):
    try:
        query_text = inline_query.query.strip()
        parts = query_text.split(" ", 1)
        amount_str = ''.join(filter(str.isdigit, parts[0]))
        if not amount_str: return bot.answer_inline_query(inline_query.id, [])
        amount = int(amount_str)
        comment = parts[1] if len(parts) > 1 else "A gift for you!"
        
        user = get_user(inline_query.from_user.id)
        if user["balance"] < amount:
            res = InlineQueryResultArticle(
                id="insufficient",
                title="❌ Insufficient Stars!",
                description=f"You need {amount} ⭐️ but have {user['balance']} ⭐️.",
                input_message_content=InputTextMessageContent("Insufficient balance to send this check.")
            )
            return bot.answer_inline_query(inline_query.id, [res], cache_time=1)
            
        check_id = str(uuid.uuid4().hex)[:10]
        
        markup = kb([(LANG["en"]["check_claim"].replace("⭐️", f"{amount} ⭐️"), f"https://t.me/{CONFIG['BOT_USERNAME']}?start=chk_{check_id}", "success")])
        
        checks_col.insert_one({
            "_id": check_id, "creator": inline_query.from_user.id, 
            "amount": amount, "status": "active"
        })
        
        res = InlineQueryResultArticle(
            id=check_id,
            title=f"Create Check for {amount} ⭐️",
            description=comment,
            input_message_content=InputTextMessageContent(f"<b>⭐️ Telegram Stars Check</b>\n\nAmount: {amount} ⭐️\n💬 {comment}", parse_mode="HTML"),
            reply_markup=markup
        )
        bot.answer_inline_query(inline_query.id, [res], cache_time=1)
    except Exception:
        pass

@bot.chosen_inline_handler(func=lambda chosen_inline_result: True)
def chosen_check(chosen_inline_result):
    check_id = chosen_inline_result.result_id
    inline_msg_id = chosen_inline_result.inline_message_id
    
    if inline_msg_id:
        checks_col.update_one({"_id": check_id}, {"$set": {"inline_msg_id": inline_msg_id}})
        
# ==========================================
# 🚀 USER HANDLERS (START MENU & RAIN/CHECK CLAIM)
# ==========================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user = get_user(message.from_user.id, message.from_user.username)
    
    if len(message.text.split()) > 1:
        param = message.text.split()[1]
        
        if param.startswith("chk_"):
            check_id = param.replace("chk_", "")
            chk = checks_col.find_one({"_id": check_id})
            
            if not chk or chk["status"] != "active":
                bot.reply_to(message, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Check already claimed or bounced.</b>")
                return
                
            if chk["creator"] == message.from_user.id:
                bot.reply_to(message, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> You cannot claim your own check!")
                return
                
            creator_user = get_user(chk["creator"])
            if creator_user["balance"] < chk["amount"]:
                checks_col.update_one({"_id": check_id}, {"$set": {"status": "bounced"}})
                bot.reply_to(message, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Check Bounced!</b> The creator doesn't have enough stars anymore.")
                return
                
            update_balance(chk["creator"], -chk["amount"])
            checks_col.update_one({"_id": check_id}, {"$set": {"status": "claimed", "claimer": message.from_user.id}})
            update_balance(message.from_user.id, chk["amount"])
            
            bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> <b>You received {chk['amount']} ⭐️!</b>")
            
            try:
                bot.send_message(chk["creator"], f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> User @{message.from_user.username or message.from_user.first_name} claimed your checked amount of {chk['amount']} ⭐️!")
            except Exception: pass
            
            inline_msg_id = chk.get("inline_msg_id")
            if inline_msg_id:
                claimed_markup = kb([("Claimed ✅", "already_claimed", "success")])
                try: bot.edit_message_reply_markup(inline_message_id=inline_msg_id, reply_markup=claimed_markup)
                except Exception: pass
                
            return

        elif param.startswith("rain_"):
            rain_id = param.replace("rain_", "")
            r = pending_rains_col.find_one({"_id": rain_id, "user_id": message.from_user.id})
            if r:
                pending_rains_col.delete_one({"_id": rain_id})
                threading.Thread(target=send_real_telegram_gift, args=(message.from_user.id, r["gift_name"], r["price"], r["comment"])).start()
                return
    
    welcome_msg = f"<b>Welcome, {message.from_user.first_name}!</b> <tg-emoji emoji-id='{TE['WELCOME']}'>👋</tg-emoji>"
    bot.send_message(message.chat.id, welcome_msg)
    
    text = get_start_text(user["lang"], message.from_user.first_name, user["balance"])
    bot.send_message(message.chat.id, text, reply_markup=main_menu_kb(user["lang"]))

# ==========================================
# 🔄 FAST CALLBACK HANDLER
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    lang = user["lang"]
    data = call.data
    
    try:
        chat_id = None
        if hasattr(call, 'message') and call.message:
            chat_id = call.message.chat.id
            bot.clear_step_handler_by_chat_id(chat_id)

        if data == "already_claimed":
            return bot.answer_callback_query(call.id, "This check has already been claimed.", show_alert=True)

        if data.startswith("slotbet_"):
            _, bet, target = data.split("_")
            bet = int(bet)
            
            if user["balance"] < bet:
                return bot.answer_callback_query(call.id, "Insufficient balance!", show_alert=True)
                
            bot.answer_callback_query(call.id)
            update_balance(user_id, -bet)
            if chat_id:
                try:
                    bot.edit_message_text(f"🎰 Rolling the slot machine for {bet} ⭐️...", chat_id=chat_id, message_id=call.message.message_id)
                except Exception: pass
                dice_msg = bot.send_dice(chat_id, emoji="🎰")
                threading.Thread(target=process_slot_result, args=(chat_id, call.message.message_id, user_id, bet, target, dice_msg.dice.value)).start()
            return
            
        bot.answer_callback_query(call.id)

        if not chat_id: return 

        if data == "switch_lang":
            new_lang = "ru" if lang == "en" else "en"
            users_col.update_one({"_id": user_id}, {"$set": {"lang": new_lang}})
            text = get_start_text(new_lang, call.from_user.first_name, user["balance"])
            try: bot.edit_message_text(text=text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=main_menu_kb(new_lang))
            except Exception: pass
            
        elif data == "menu_main":
            text = get_start_text(lang, call.from_user.first_name, user["balance"])
            try: bot.edit_message_text(text=text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=main_menu_kb(lang))
            except Exception: pass
            
        elif data == "menu_profile":
            try: bot.edit_message_text(text=LANG[lang]["profile_text"].format(id=user_id, username=user.get("username", "None"), balance=user["balance"]), chat_id=chat_id, message_id=call.message.message_id, reply_markup=profile_kb(lang))
            except Exception: pass
            
        elif data == "menu_topup":
            try:
                msg = bot.edit_message_text(text=LANG[lang]["topup_text"], chat_id=chat_id, message_id=call.message.message_id, reply_markup=topup_kb(lang))
                bot.register_next_step_handler(msg, process_custom_topup)
            except Exception: pass
            
        elif data == "menu_gifts":
            try: bot.edit_message_text(text=LANG[lang]["gift_text"], chat_id=chat_id, message_id=call.message.message_id, reply_markup=gifts_kb(lang, user))
            except Exception as e: print("Gift menu error:", e)
        
        elif data == "menu_luck":
            try: bot.edit_message_text(text=LANG[lang]["luck_text"], chat_id=chat_id, message_id=call.message.message_id, reply_markup=luck_kb(lang))
            except Exception: pass
            
        elif data.startswith("slot_"):
            bet = int(data.split("_")[1])
            try: bot.edit_message_text(text=f"🍀 Select your condition for {bet} ⭐️:", chat_id=chat_id, message_id=call.message.message_id, reply_markup=slot_options_kb(bet, lang))
            except Exception: pass
            
        elif data == "menu_promo":
            try:
                msg = bot.edit_message_text(text=LANG[lang]["promo_text"], chat_id=chat_id, message_id=call.message.message_id)
                bot.register_next_step_handler(msg, process_promo_code, lang)
            except Exception: pass
            
        elif data.startswith("pay_"):
            amount = int(data.split("_")[1])
            bot.send_invoice(chat_id, title="Top-Up Balance", description=f"Top up {amount} ⭐️", invoice_payload=f"topup_{amount}", provider_token="", currency="XTR", prices=[LabeledPrice("Stars", amount)])

        elif data.startswith("buyg|"):
            parts = data.split("|")
            gift_name = parts[1]
            amount = int(parts[2])
            
            if user["balance"] >= amount:
                update_balance(user_id, -amount)
                if gift_name.lower() == "teddy bear": users_col.update_one({"_id": user_id}, {"$set": {"bought_teddy": True}})
                elif gift_name.lower() == "heart": users_col.update_one({"_id": user_id}, {"$set": {"bought_heart": True}})
                
                updated_user = get_user(user_id) 
                try: bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=gifts_kb(lang, updated_user))
                except Exception: pass
                
                if amount == 1:
                    auto_comment = "A small gift by @redcube. Join today and earn and win money. Contact @Cinex"
                    threading.Thread(target=send_real_telegram_gift, args=(chat_id, gift_name, amount, auto_comment)).start()
                else:
                    markup = kb([("⏭ Skip Comment", f"skip|{gift_name}|{amount}", "primary")])
                    msg = bot.send_message(
                        chat_id, 
                        f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> <b>{gift_name}</b> purchased!\n\n💬 Please send a comment for your gift below, or click <b>Skip</b>.", 
                        reply_markup=markup
                    )
                    bot.register_next_step_handler(msg, process_gift_comment, gift_name, amount)
                
            else:
                bot.send_invoice(chat_id, title=f"Buy Gift: {gift_name}", description=f"Purchase {gift_name} for {amount} ⭐️", invoice_payload=f"buygift|{gift_name}|{amount}", provider_token="", currency="XTR", prices=[LabeledPrice(gift_name, amount)])
        
        elif data.startswith("skip|"):
            parts = data.split("|")
            gift_name = parts[1]
            amount = int(parts[2])
            
            bot.clear_step_handler_by_chat_id(chat_id)
            try: bot.delete_message(chat_id, call.message.message_id) 
            except Exception: pass
            threading.Thread(target=send_real_telegram_gift, args=(chat_id, gift_name, amount, None)).start()
            
    except Exception as e:
        print(f"Error in Callback: {e}")

# ==========================================
# 💰 PROCESS CUSTOM TOPUP
# ==========================================
def process_custom_topup(message):
    if not message.text or not message.text.isdigit(): return
        
    amount = int(message.text)
    if amount < 1:
        bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['ERROR']}'>❌</tg-emoji> Minimum amount is 1 ⭐️")
        return
        
    bot.send_invoice(
        chat_id=message.chat.id, 
        title="Top-Up Balance", 
        description=f"Top up {amount} ⭐️", 
        invoice_payload=f"topup_{amount}", 
        provider_token="", 
        currency="XTR", 
        prices=[LabeledPrice("Stars", amount)]
    )

# ==========================================
# 🎰 SLOT GAME LOGIC PROCESSOR
# ==========================================
def process_slot_result(chat_id, message_id, user_id, bet, target, dice_value):
    time.sleep(2.5) 
    
    is_win = False
    reward_name = ""
    
    if bet == 6:
        if target == "rose" and dice_value in [1, 22, 43, 64]: is_win = True
        elif target == "teddy" and dice_value == 64: is_win = True
    else:
        win_prob = 20 if bet == 10 else 30
        if random.randint(1, 100) <= win_prob: is_win = True
        
    if is_win:
        gift_mapping = {"rose": "Rose", "teddy": "Teddy bear", "flower": "Bouquet", "ring": "Ring"}
        reward_name = gift_mapping.get(target, "Gift box")
        
        bot.send_message(chat_id, f"<tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['WIN']}'>🎉</tg-emoji> <b>JACKPOT!</b>\n\nYou won a {reward_name}!")
        g = gifts_catalog_col.find_one({"name": {"$regex": f"^{reward_name}$", "$options": "i"}})
        price = g["price"] if g else 0
        send_real_telegram_gift(chat_id, reward_name, price, "You won the slot machine!")
    else:
        bot.send_message(chat_id, f"<tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['LOSE']}'>😢</tg-emoji> <b>You lost!</b>\n\nBetter luck next time. Lost {bet} ⭐️.")
        
    user = get_user(user_id)
    text = get_start_text(user["lang"], "Player", user["balance"])
    bot.send_message(chat_id, text, reply_markup=main_menu_kb(user["lang"]))

# ==========================================
# 💬 PROCESS TEXT COMMENT
# ==========================================
def process_gift_comment(message, gift_name, amount):
    if not message.text:
        bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> Please send a valid text comment. Try buying again.")
        return
    threading.Thread(target=send_real_telegram_gift, args=(message.chat.id, gift_name, amount, message.text)).start()

# ==========================================
# 🎟 PROMO PROCESSOR
# ==========================================
def process_promo_code(message, lang):
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass
    
    code = message.text.upper()
    promo = promos_col.find_one({"_id": code})
    
    markup = kb([(LANG[lang]["btn_back"], "menu_profile", "danger", "BACK")])
    
    if not promo: 
        return bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Invalid Promo Code!</b>", reply_markup=markup)
    
    expires_at = promo["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
        
    if datetime.datetime.now(datetime.timezone.utc) > expires_at: 
        return bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Promo Expired!</b>", reply_markup=markup)
    if message.from_user.id in promo["used_by"]: 
        return bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Already used!</b>", reply_markup=markup)
    if len(promo["used_by"]) >= promo["max_users"]: 
        return bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Limit reached!</b>", reply_markup=markup)
    
    promos_col.update_one({"_id": code}, {"$push": {"used_by": message.from_user.id}})
    update_balance(message.from_user.id, promo["amount"])
    bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> <b>Promo Applied!</b>\nYou received {promo['amount']} <tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji>", reply_markup=markup)

# ==========================================
# 💳 PAYMENT SUCCESS HANDLERS
# ==========================================
@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    
    if payload.startswith("topup_"):
        amount = int(payload.split("_")[1])
        update_balance(user_id, amount)
        update_house_bal(amount) 
        bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> Top-Up Successful! Added {amount} ⭐️ to your balance.")
        
    elif payload.startswith("buygift|"):
        parts = payload.split("|")
        gift_name = parts[1]
        amount = int(parts[2])
        
        update_house_bal(amount) 
        
        if gift_name.lower() == "teddy bear": users_col.update_one({"_id": user_id}, {"$set": {"bought_teddy": True}})
        elif gift_name.lower() == "heart": users_col.update_one({"_id": user_id}, {"$set": {"bought_heart": True}})
            
        if amount == 1:
            auto_comment = "A small gift by @redcube. Join today and earn and win money. Contact @Cinex"
            threading.Thread(target=send_real_telegram_gift, args=(message.chat.id, gift_name, amount, auto_comment)).start()
        else:
            markup = kb([("⏭ Skip Comment", f"skip|{gift_name}|{amount}", "primary")])
            msg = bot.send_message(
                message.chat.id, 
                f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> <b>{gift_name}</b> purchased!\n\n💬 Please send a comment for your gift below, or click <b>Skip</b>.", 
                reply_markup=markup
            )
            bot.register_next_step_handler(msg, process_gift_comment, gift_name, amount)

    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass

# ==========================================
# 📊 GROUP ACTIVITY TRACKER (MUST BE LAST)
# ==========================================
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'])
def track_activity(message):
    group_activity_col.update_one(
        {"chat_id": message.chat.id, "user_id": message.from_user.id},
        {"$set": {"username": message.from_user.username or message.from_user.first_name, "last_active": datetime.datetime.now(datetime.timezone.utc)}},
        upsert=True
    )

print("🚀 Fully Loaded Premium Styled Bot is running...")
bot.infinity_polling(skip_pending=True)