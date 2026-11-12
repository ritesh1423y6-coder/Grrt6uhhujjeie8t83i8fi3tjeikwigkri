import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, InlineQueryResultArticle, InputTextMessageContent, BotCommand
from telebot.apihelper import ApiTelegramException
from pymongo import MongoClient
import datetime
import requests
import threading
import time
import random
import uuid
import re

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
    
    # 🛠️ REAL GIFT MAPPING
    "REAL_GIFT_IDS": {
        "Teddy bear": "5170233102089322756", "Heart": "5170145012310081615",        
        "Rose": "5168103777563050263", "Gift box": "5170250947678437525",   
        "Champagne": "6028601630662853006", "Rocket": "5170564780938756245",     
        "Bouquet": "5170314324215857265", "Cake": "5170144170496491616",        
        "Diamond": "5170521118301225164", "Ring": "5170690322832818290",        
        "Trophy": "5168043875654172773"        
    }
}

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
giveaways_col = db["giveaways"]

bot = telebot.TeleBot(CONFIG["BOT_TOKEN"], parse_mode="HTML", threaded=True)

default_gifts = [
    {"name": "Champagne", "id": CONFIG["REAL_GIFT_IDS"]["Champagne"], "price": 49},
    {"name": "Diamond", "id": CONFIG["REAL_GIFT_IDS"]["Diamond"], "price": 99},
    {"name": "Ring", "id": CONFIG["REAL_GIFT_IDS"]["Ring"], "price": 99},
    {"name": "Trophy", "id": CONFIG["REAL_GIFT_IDS"]["Trophy"], "price": 99},
    {"name": "Rocket", "id": CONFIG["REAL_GIFT_IDS"]["Rocket"], "price": 49},
    {"name": "Bouquet", "id": CONFIG["REAL_GIFT_IDS"]["Bouquet"], "price": 49},
    {"name": "Cake", "id": CONFIG["REAL_GIFT_IDS"]["Cake"], "price": 49},
    {"name": "Rose", "id": CONFIG["REAL_GIFT_IDS"]["Rose"], "price": 24},
    {"name": "Gift box", "id": CONFIG["REAL_GIFT_IDS"]["Gift box"], "price": 24},
    {"name": "Teddy bear", "id": CONFIG["REAL_GIFT_IDS"]["Teddy bear"], "price": 7},
    {"name": "Heart", "id": CONFIG["REAL_GIFT_IDS"]["Heart"], "price": 7}
]

if gifts_catalog_col.count_documents({}) == 0:
    gifts_catalog_col.insert_many(default_gifts)
else:
    for g in default_gifts:
        gifts_catalog_col.update_one({"name": {"$regex": f"^{g['name']}$", "$options": "i"}}, {"$set": {"id": g["id"], "price": g["price"]}}, upsert=False)

GIFTS_CACHE = []
def refresh_gifts_cache():
    global GIFTS_CACHE
    GIFTS_CACHE = list(gifts_catalog_col.find())
refresh_gifts_cache()

# ==========================================
# 🛡 DATABASE HELPERS
# ==========================================
def get_user(user_id, username=None):
    user = users_col.find_one({"_id": user_id})
    if not user:
        user = {"_id": user_id, "username": username, "lang": "en", "balance": 0, "bought_teddy": False, "bought_heart": False}
        users_col.insert_one(user)
    elif username and user.get("username") != username:
        users_col.update_one({"_id": user_id}, {"$set": {"username": username}})
        user["username"] = username
    return user

def update_balance(user_id, amount):
    users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})

def update_house_bal(amount):
    bot_config_col.update_one({"_id": "house"}, {"$inc": {"balance": amount}}, upsert=True)

def get_house_bal():
    doc = bot_config_col.find_one({"_id": "house"})
    return doc["balance"] if doc else 0

def safe_delete(chat_id, msg_id):
    try: bot.delete_message(chat_id, msg_id)
    except: pass

def check_user_joined(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['member', 'administrator', 'creator', 'restricted']
    except ApiTelegramException: return False

def get_username_formatted(user_id):
    u = users_col.find_one({"_id": user_id})
    if u and u.get('username'): return f"@{u['username']}"
    return f"<a href='tg://user?id={user_id}'>User</a>"

# ==========================================
# 🎁 REAL TELEGRAM GIFT SENDER
# ==========================================
def send_real_telegram_gift(chat_id, gift_name, amount, comment=None):
    url = f"https://api.telegram.org/bot{CONFIG['BOT_TOKEN']}/sendGift"
    g = next((item for item in GIFTS_CACHE if item["name"].lower() == gift_name.lower()), None)
    gift_id = g["id"] if g else CONFIG["REAL_GIFT_IDS"].get(gift_name, "INVALID_ID")
    
    payload = {"user_id": chat_id, "gift_id": gift_id}
    if comment: payload["text"] = comment

    try: res = requests.post(url, json=payload, timeout=5).json()
    except: res = {"ok": False, "description": "API connection error"}
    
    if res.get("ok"):
        update_house_bal(-amount)
        msg = f"<tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['SUCCESS']}'>✅</tg-emoji> <b>Congratulations!</b>\n\n<tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['GIFT']}'>🎁</tg-emoji> You just received a real <b>{gift_name}</b> gift on your profile!"
        try: bot.send_message(chat_id, msg)
        except: pass 
        return True
    else:
        update_balance(chat_id, amount)
        err = res.get("description", "Unknown error")
        msg = f"<tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['ERROR']}'>❌</tg-emoji> <b>Gift Delivery Failed!</b>\n\n<tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['REFUND']}'>💸</tg-emoji> <b>Refund Processed:</b> {amount} <tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['STAR']}'>⭐️</tg-emoji> returned to your wallet.\n<i>Reason: {err}</i>"
        try: bot.send_message(chat_id, msg)
        except: pass 
        return False

# ==========================================
# 🌍 LANGUAGE & TEXT (BUTTON EMOJIS REMOVED)
# ==========================================
TE = CONFIG["TEXT_EMOJI"]

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
        "luck_text": f"<tg-emoji emoji-id='{TE['LUCK']}'>🍀</tg-emoji> <b>Slot Game</b>\n\nRoll the slot and win big rewards!\n\n<tg-emoji emoji-id='{TE['DOWN']}'>👇</tg-emoji> Select your bet:",
        "btn_profile": "Profile", "btn_send_gift": "Buy Gift", "btn_luck": "Luck",
        "btn_help": "Help", "btn_lang": "Russian", "btn_topup": "Top Up",
        "btn_promo": "Promos", "btn_back": "Back", "btn_cancel": "Cancel",
        "btn_giveaway": "Giveaway",
        "check_claim": "Claim Stars", "rain_claim": "Start Bot to Claim Gift"
    },
    "ru": {
        "profile_text": f"<tg-emoji emoji-id='{TE['PROFILE']}'>🕵️‍♂️</tg-emoji> <b>Ваш Профиль</b>\n\n🆔 ID: <code>{{id}}</code>\n👤 Юзернейм: @{{username}}\n<tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji> Баланс: <b>{{balance}}</b> <tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji>",
        "topup_text": "Выберите сумму пополнения или введите свое количество звезд ниже:",
        "gift_text": f"<tg-emoji emoji-id='{TE['GIFT']}'>🎁</tg-emoji> <b>Каталог Подарков</b>\n\nВыберите подарок для себя:",
        "promo_text": f"<tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji> <tg-emoji emoji-id='{TE['TICKET']}'>🎟</tg-emoji> <b>Введите ваш промокод:</b>\n\nОтправьте код ниже.",
        "luck_text": f"<tg-emoji emoji-id='{TE['LUCK']}'>🍀</tg-emoji> <b>Слот Игра</b>\n\nКрути слот и выигрывай!\n\n<tg-emoji emoji-id='{TE['DOWN']}'>👇</tg-emoji> Выберите ставку:",
        "btn_profile": "Профиль", "btn_send_gift": "Подарок", "btn_luck": "Удача",
        "btn_help": "Помощь", "btn_lang": "English", "btn_topup": "Пополнить",
        "btn_promo": "Промокоды", "btn_back": "Назад", "btn_cancel": "Отмена",
        "btn_giveaway": "Розыгрыш",
        "check_claim": "Забрать", "rain_claim": "Запустите бота"
    }
}

# ==========================================
# 🎛 KEYBOARDS
# ==========================================
def btn(text: str, data: str = None, style: str = None, url: str = None):
    b = InlineKeyboardButton(text=str(text))
    if data and data.startswith("http"): url = data; data = None
    if url: b.url = str(url)
    else: b.callback_data = str(data) if data else "noop"
    if style: setattr(b, 'style', style); setattr(b, 'color', style)
    return b

def kb(*rows):
    m = InlineKeyboardMarkup()
    for row in rows:
        row_btns = []
        for item in row:
            if len(item) >= 3: row_btns.append(btn(item[0], item[1], style=item[2]))
            elif len(item) == 2: row_btns.append(btn(item[0], item[1]))
            elif len(item) == 1: row_btns.append(btn(item[0], item[0]))
        if row_btns: m.row(*row_btns)
    return m

def main_menu_kb(l):
    return kb(
        [("Profile", "menu_profile", "primary"), ("Buy Gift", "menu_gifts", "success")],
        [("Giveaway", "menu_giveaway", "primary"), ("Luck", "menu_luck", None)],
        [("Help", "https://t.me/Cinex", "danger"), ("Switch Lang", "switch_lang", "primary")]
    )

def profile_kb(l):
    return kb([("Top Up", "menu_topup", "success"), ("Promos", "menu_promo", "primary")], [("Back", "menu_main", "danger")])

def topup_kb(l):
    return kb([("25", "pay_25", "primary"), ("50", "pay_50", None)], [("100", "pay_100", "success"), ("150", "pay_150", "primary")], [("Cancel", "menu_profile", "danger")])

def luck_kb(l):
    return kb([("10", "slot_10", "primary"), ("15", "slot_15", None)], [("30", "slot_30", "success")], [("Back", "menu_main", "danger")])

def slot_options_kb(bet, l):
    rows = []
    if bet == 10: rows.append([("Any Combo", "slotbet_10_any", "primary"), ("Unique Combo", "slotbet_10_unique", "success")])
    elif bet == 15: rows.append([("Any Combo", "slotbet_15_any", "primary"), ("Unique Combo", "slotbet_15_unique", "success")])
    elif bet == 30: rows.append([("Any Combo", "slotbet_30_any", "primary"), ("Unique Combo", "slotbet_30_unique", "success")])
    rows.append([("Back", "menu_luck", "danger")])
    return kb(*rows)

def gifts_kb(lang_code, user):
    m = InlineKeyboardMarkup()
    for i, g in enumerate(GIFTS_CACHE):
        price = g["price"]
        if g["name"].lower() == "teddy bear" and user.get("bought_teddy"): price = 14
        if g["name"].lower() == "heart" and user.get("bought_heart"): price = 14
        style = "primary" if i % 2 == 0 else "success"
        m.row(btn(f"{g['name']} - {price}", data=f"buyg|{g['name']}|{price}", style=style))
    m.row(btn("Cancel", data="menu_main", style="danger"))
    return m

# ==========================================
# 🎉 GIVEAWAY WIZARD & LOGIC
# ==========================================
user_gw_drafts = {}

def reset_gw_draft(user_id):
    user_gw_drafts[user_id] = {
        "wizard_msg_id": None, "host_chat": None, "host_chat_name": None, 
        "prize_type": None, "prize_val": None, "title": "Giveaway", 
        "banner": None, "hosted_by": None, "winners": 1, "duration": 0, 
        "captcha": False, "req_channels": [], "req_channels_names": [],
        "notes": None, "stars_deducted": False,
        "req_active": False, "req_name": False, "req_bio": False, 
        "req_premium": False, "req_boost": False, "req_ref": False
    }

def get_gw_draft(user_id):
    if user_id not in user_gw_drafts: reset_gw_draft(user_id)
    return user_gw_drafts[user_id]

def parse_time_to_seconds(t_str):
    t_str = t_str.lower()
    total = 0
    d = re.search(r'(\d+)\s*d', t_str)
    h = re.search(r'(\d+)\s*h', t_str)
    m = re.search(r'(\d+)\s*m', t_str)
    s = re.search(r'(\d+)\s*s', t_str)
    if d: total += int(d.group(1)) * 86400
    if h: total += int(h.group(1)) * 3600
    if m: total += int(m.group(1)) * 60
    if s: total += int(s.group(1))
    if total == 0 and t_str.isdigit(): total = int(t_str) * 60 
    return total

def gw_main_kb():
    return kb([("Start new giveaway", "gw_new", "primary")], [("Manage Giveaways", "gwm_list", "success")], [("Back to menu", "menu_main", "danger")])

def gw_prize_kb():
    return kb([("Star", "gw_prize_star", "primary"), ("Custom prize", "gw_prize_custom", "success")], [("Cancel", "menu_cancel_gw", "danger")])

def gw_cancel_kb(): return kb([("Cancel", "menu_cancel_gw", "danger")])
def gw_skip_kb(next_step): return kb([("Skip", next_step, "primary")], [("Cancel", "menu_cancel_gw", "danger")])

def gw_reqs_kb(draft):
    return kb(
        [(f"Active in group: {'On' if draft.get('req_active') else 'Off'}", "gwr_active", "primary")],
        [(f"Name contain: {'On' if draft.get('req_name') else 'Off'}", "gwr_name", "primary")],
        [(f"Bio contain: {'On' if draft.get('req_bio') else 'Off'}", "gwr_bio", "primary")],
        [(f"Telegram premium: {'On' if draft.get('req_premium') else 'Off'}", "gwr_premium", "primary")],
        [(f"Boost bonus: {'On' if draft.get('req_boost') else 'Off'}", "gwr_boost", "primary")],
        [(f"Referrals: {'On' if draft.get('req_ref') else 'Off'}", "gwr_ref", "primary")],
        [("Continue -> review", "gw_preview", "success")], [("Cancel", "menu_cancel_gw", "danger")]
    )

def gw_preview_kb():
    return kb([("Continue post", "gw_publish", "success")], [("Edit requirements", "gw_edit_reqs", "primary")], [("Cancel", "menu_cancel_gw", "danger")])

def build_giveaway_text(gw_data, preview_mode=False):
    title = gw_data.get('title', 'Giveaway')
    p_name = f"{gw_data['prize_val']} Stars" if gw_data['prize_type'] == 'star' else gw_data['prize_val']
    
    txt = f"<b>{title}</b>\n{p_name}\n\n"
    if gw_data.get('hosted_by'): txt += f"Hosted by — {gw_data['hosted_by']}\n\n"
        
    txt += "<blockquote><b>To Participate:</b>\n"
    txt += f"• Join {gw_data.get('host_chat_name', gw_data['host_chat'])}\n"
    
    if 'req_channels_names' in gw_data and gw_data['req_channels_names']:
        for c in gw_data['req_channels_names']: txt += f"• Join {c}\n"
        
    if gw_data.get('req_premium'): txt += "• Must have Telegram Premium\n"
    if gw_data.get('req_boost'): txt += "• Boost the channel for an extra chance\n"
    txt += "• Tap Participate</blockquote>\n\n"
    
    if gw_data.get('notes'): txt += f"{gw_data['notes']}\n\n"
        
    p_count = len(gw_data.get('participants', []))
    txt += f"Participants: {p_count}\nWinners: {gw_data['winners']}\n\n"
    
    if preview_mode: txt += f"Giveaway Ends In: <b>{datetime.timedelta(seconds=gw_data['duration'])}</b>"
    else:
        end_ts = int(gw_data['end_time'].timestamp())
        txt += f"Giveaway Ends In: <t:{end_ts}:R>\n<i>(<t:{end_ts}:f>)</i>"
    return txt

def build_ended_post_text(gw_id):
    gw = giveaways_col.find_one({"_id": gw_id})
    title = gw.get('title', 'Giveaway')
    p_name = f"{gw['prize_val']} Stars" if gw['prize_type'] == 'star' else gw['prize_val']
    
    txt = f"<b>{title}</b>\n{p_name}\n\n"
    txt += f"Entries: {len(gw.get('participants', []))}\n"
    txt += f"Giveaway Timer: ended\n\n"
    txt += "<b>Winners</b>\n"
    
    winners = gw.get('winner_ids', [])
    if not winners: txt += "No participants."
    else:
        for w in winners: txt += f"- {get_username_formatted(w)}\n"
    return txt

def update_gw_post_participants(gw_id):
    gw = giveaways_col.find_one({"_id": gw_id})
    if not gw or not gw.get('msg_id') or gw['status'] != 'active': return
    try:
        txt = build_giveaway_text(gw, preview_mode=False)
        markup = kb([("Join Giveaway", f"gw_join_{gw_id}", "success")])
        if gw.get('banner'): bot.edit_message_caption(txt, chat_id=gw['host_chat'], message_id=gw['msg_id'], reply_markup=markup, parse_mode="HTML")
        else: bot.edit_message_text(txt, chat_id=gw['host_chat'], message_id=gw['msg_id'], reply_markup=markup, parse_mode="HTML")
    except Exception: pass

def update_gw_post_ended(gw_id):
    gw = giveaways_col.find_one({"_id": gw_id})
    if not gw or not gw.get('msg_id'): return
    try:
        txt = build_ended_post_text(gw_id)
        if gw.get('banner'): bot.edit_message_caption(txt, chat_id=gw['host_chat'], message_id=gw['msg_id'], parse_mode="HTML")
        else: bot.edit_message_text(txt, chat_id=gw['host_chat'], message_id=gw['msg_id'], parse_mode="HTML")
    except Exception: pass

def perform_reroll(gw_id, replace_ids=None):
    gw = giveaways_col.find_one({"_id": gw_id})
    current_winners = gw.get('winner_ids', [])
    participants = gw.get('participants', [])
    
    if replace_ids is None: replace_ids = current_winners
    eligible = [p for p in participants if p not in current_winners]
    
    new_winners = list(current_winners)
    for r_id in replace_ids:
        if eligible:
            chosen = random.choice(eligible)
            eligible.remove(chosen)
            if r_id in new_winners: new_winners[new_winners.index(r_id)] = chosen
            else: new_winners.append(chosen)
            
    giveaways_col.update_one({"_id": gw_id}, {"$set": {"winner_ids": new_winners}})
    update_gw_post_ended(gw_id)

# --- GW WIZARD STEP HANDLERS ---
def gw_step_host(m):
    safe_delete(m.chat.id, m.message_id)
    if not m.text: return
    draft = get_gw_draft(m.from_user.id)
    chat_id_to_check = m.text.strip()
    
    try:
        chat_obj = bot.get_chat(chat_id_to_check)
        member = bot.get_chat_member(chat_id_to_check, bot.get_me().id)
        if member.status not in ['administrator', 'creator']: raise Exception("Not admin")
        draft['host_chat'] = chat_id_to_check
        draft['host_chat_name'] = f"@{chat_obj.username}" if chat_obj.username else chat_obj.title
    except Exception:
        bot.edit_message_text(f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>I am not an Admin in {chat_id_to_check}!</b>\n\nMake sure the bot is an administrator in that chat, then send the @username or ID again:", m.chat.id, draft['wizard_msg_id'], reply_markup=gw_cancel_kb())
        return bot.register_next_step_handler_by_chat_id(m.chat.id, gw_step_host)

    bot.edit_message_text(f"<tg-emoji emoji-id='{TE['GIFT']}'>🎁</tg-emoji> <b>Giveaway Prize</b>\n\nWhat will the winners receive?", m.chat.id, draft['wizard_msg_id'], reply_markup=gw_prize_kb())

def gw_step_star_amt(m):
    safe_delete(m.chat.id, m.message_id)
    draft = get_gw_draft(m.from_user.id)
    if not m.text or not m.text.isdigit():
        bot.edit_message_text(f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> Invalid amount. Please type numbers only:", m.chat.id, draft['wizard_msg_id'], reply_markup=gw_cancel_kb())
        return bot.register_next_step_handler_by_chat_id(m.chat.id, gw_step_star_amt)
    
    amt = int(m.text)
    u = get_user(m.from_user.id)
    if u['balance'] < amt:
        bot.edit_message_text(f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Insufficient Stars!</b>\n\nYou only have {u['balance']} <tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji>.\nSend a lower amount or cancel:", m.chat.id, draft['wizard_msg_id'], reply_markup=gw_cancel_kb())
        return bot.register_next_step_handler_by_chat_id(m.chat.id, gw_step_star_amt)
        
    update_balance(m.from_user.id, -amt); update_house_bal(amt)
    draft['prize_val'] = amt; draft['stars_deducted'] = True
    
    bot.edit_message_text(f"<tg-emoji emoji-id='{TE['TICKET']}'>📝</tg-emoji> <b>Send giveaway title</b> (or click Skip for default)", m.chat.id, draft['wizard_msg_id'], reply_markup=gw_skip_kb("gw_ask_banner"))
    bot.register_next_step_handler_by_chat_id(m.chat.id, gw_step_title)

def gw_step_custom_name(m):
    safe_delete(m.chat.id, m.message_id)
    if not m.text: return
    get_gw_draft(m.from_user.id)['prize_val'] = m.text
    bot.edit_message_text(f"<tg-emoji emoji-id='{TE['TICKET']}'>📝</tg-emoji> <b>Send giveaway title</b> (or click Skip for default)", m.chat.id, get_gw_draft(m.from_user.id)['wizard_msg_id'], reply_markup=gw_skip_kb("gw_ask_banner"))
    bot.register_next_step_handler_by_chat_id(m.chat.id, gw_step_title)

def gw_step_title(m):
    safe_delete(m.chat.id, m.message_id)
    if not m.text: return
    get_gw_draft(m.from_user.id)['title'] = m.text
    bot.edit_message_text(f"<tg-emoji emoji-id='{TE['PROFILE']}'>🖼</tg-emoji> <b>Banner</b>\nDo you want a banner? Send an image or click Skip.", m.chat.id, get_gw_draft(m.from_user.id)['wizard_msg_id'], reply_markup=gw_skip_kb("gw_ask_hostedby"))
    bot.register_next_step_handler_by_chat_id(m.chat.id, gw_step_banner)

def gw_step_banner(m):
    safe_delete(m.chat.id, m.message_id)
    if m.photo: get_gw_draft(m.from_user.id)['banner'] = m.photo[-1].file_id
    bot.edit_message_text(f"<tg-emoji emoji-id='{TE['PROFILE']}'>👤</tg-emoji> <b>Send Hosted by</b> (a name or @username)", m.chat.id, get_gw_draft(m.from_user.id)['wizard_msg_id'], reply_markup=gw_skip_kb("gw_ask_winners"))
    bot.register_next_step_handler_by_chat_id(m.chat.id, gw_step_hostedby)

def gw_step_hostedby(m):
    safe_delete(m.chat.id, m.message_id)
    if not m.text: return
    get_gw_draft(m.from_user.id)['hosted_by'] = m.text
    bot.edit_message_text(f"<tg-emoji emoji-id='{TE['WIN']}'>🏆</tg-emoji> <b>Number of winners (>=1)</b>", m.chat.id, get_gw_draft(m.from_user.id)['wizard_msg_id'], reply_markup=gw_cancel_kb())
    bot.register_next_step_handler_by_chat_id(m.chat.id, gw_step_winners)

def gw_step_winners(m):
    safe_delete(m.chat.id, m.message_id)
    draft = get_gw_draft(m.from_user.id)
    if not m.text or not m.text.isdigit() or int(m.text) < 1:
        bot.edit_message_text(f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> Enter a valid number >= 1:", m.chat.id, draft['wizard_msg_id'], reply_markup=gw_cancel_kb())
        return bot.register_next_step_handler_by_chat_id(m.chat.id, gw_step_winners)
    draft['winners'] = int(m.text)
    bot.edit_message_text(f"<tg-emoji emoji-id='{TE['DOWN']}'>⏳</tg-emoji> <b>Giveaway duration</b> (e.g., 1d 12h, 10h, 30m, or seconds).", m.chat.id, draft['wizard_msg_id'], reply_markup=gw_cancel_kb())
    bot.register_next_step_handler_by_chat_id(m.chat.id, gw_step_duration)

def gw_step_duration(m):
    safe_delete(m.chat.id, m.message_id)
    draft = get_gw_draft(m.from_user.id)
    if not m.text: return
    secs = parse_time_to_seconds(m.text)
    if secs < 60:
        bot.edit_message_text(f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> Duration too short. Min 60s:", m.chat.id, draft['wizard_msg_id'], reply_markup=gw_cancel_kb())
        return bot.register_next_step_handler_by_chat_id(m.chat.id, gw_step_duration)
        
    draft['duration'] = secs
    bot.edit_message_text(f"<tg-emoji emoji-id='{TE['PROFILE']}'>🤖</tg-emoji> <b>Captcha</b>\nDo you want anti-bots in this giveaway?", m.chat.id, draft['wizard_msg_id'], reply_markup=kb([("Enable", "gw_set_cap_1", "success"), ("Disable", "gw_set_cap_0", "danger")], [("Cancel", "menu_cancel_gw", "primary")]))

def gw_step_channels(m):
    safe_delete(m.chat.id, m.message_id)
    if not m.text: return
    draft = get_gw_draft(m.from_user.id)
    valid_ids, valid_names = [], []
    for ch in m.text.split():
        try:
            chat_obj = bot.get_chat(ch)
            member = bot.get_chat_member(ch, bot.get_me().id)
            if member.status not in ['administrator', 'creator']: raise Exception("Not admin")
            valid_ids.append(ch)
            valid_names.append(f"@{chat_obj.username}" if chat_obj.username else chat_obj.title)
        except Exception:
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>I am not an Admin in {ch}!</b>\n\nMake sure I am an admin in all required channels, then send the list again:", m.chat.id, draft['wizard_msg_id'], reply_markup=gw_cancel_kb())
            return bot.register_next_step_handler_by_chat_id(m.chat.id, gw_step_channels)
            
    draft['req_channels'], draft['req_channels_names'] = valid_ids, valid_names
    bot.edit_message_text(f"<tg-emoji emoji-id='{TE['DOWN']}'>📝</tg-emoji> <b>Additional Notes</b>\nRules, links - anything you want participants to see (or Skip).", m.chat.id, draft['wizard_msg_id'], reply_markup=gw_skip_kb("gw_edit_reqs"))
    bot.register_next_step_handler_by_chat_id(m.chat.id, gw_step_notes)

def gw_step_notes(m):
    safe_delete(m.chat.id, m.message_id)
    if not m.text: return
    get_gw_draft(m.from_user.id)['notes'] = m.text
    bot.edit_message_text(f"<tg-emoji emoji-id='{TE['TICKET']}'>🛠</tg-emoji> <b>Requirements</b>\nConfigure participation restrictions. Continue when ready.", m.chat.id, get_gw_draft(m.from_user.id)['wizard_msg_id'], reply_markup=gw_reqs_kb(get_gw_draft(m.from_user.id)))

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
    except ValueError: bot.reply_to(message, "❌ Invalid! Use: `/qpromo CODE AMOUNT USERS HOURS`", parse_mode="Markdown")

@bot.message_handler(commands=['addgift'])
def admin_addgift(message):
    if message.from_user.id != CONFIG["ADMIN_ID"]: return
    try:
        parts = message.text.split(" ", 3)
        gift_name = parts[1].replace("_", " ") 
        gift_id = parts[2]
        amount = int(parts[3])
        gifts_catalog_col.update_one({"name": gift_name}, {"$set": {"id": gift_id, "price": amount}}, upsert=True)
        refresh_gifts_cache()
        bot.reply_to(message, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> <b>Gift Added!</b>\nName: {gift_name}\nID: <code>{gift_id}</code>\nPrice: {amount} ⭐️")
    except Exception: bot.reply_to(message, "❌ Format: `/addgift Gift_Name Gift_ID Amount`", parse_mode="Markdown")

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

        g = next((item for item in GIFTS_CACHE if item["name"].lower() == gift_name.lower()), None)
        price = g["price"] if g else 0
        actual_name = g["name"] if g else gift_name
        threading.Thread(target=send_real_telegram_gift, args=(u["_id"], actual_name, price, comment)).start()
        bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> Gift {actual_name} action triggered to {target}!")
    except Exception: bot.reply_to(message, "❌ Format: `/giftsend UserID_or_@User Gift_Name Comment`", parse_mode="Markdown")

@bot.message_handler(commands=['housebal'])
def public_housebal(message):
    bot.reply_to(message, f"<tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji> <b>Bot's Reserve Balance:</b> {get_house_bal()} Stars")

@bot.message_handler(commands=['topup'])
def admin_topup(message):
    if message.from_user.id != CONFIG["ADMIN_ID"]: return
    try:
        amount = int(message.text.split()[1])
        update_house_bal(amount)
        bot.reply_to(message, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> Successfully added {amount} ⭐️ to the Bot Reserve. Current balance: {get_house_bal()} ⭐️")
    except Exception: bot.reply_to(message, "❌ Format: `/topup Amount`")

@bot.message_handler(commands=['broadcast'])
def admin_broadcast(message):
    if message.from_user.id != CONFIG["ADMIN_ID"]: return
    if not message.reply_to_message and len(message.text.split()) < 2: return bot.reply_to(message, "Reply to a message or type text after /broadcast.")
    users = users_col.find()
    bot.reply_to(message, "Broadcast started...")
    for u in users:
        try:
            if message.reply_to_message: bot.copy_message(u["_id"], message.chat.id, message.reply_to_message.message_id)
            else: bot.send_message(u["_id"], message.text.split(maxsplit=1)[1])
        except: pass
    bot.reply_to(message, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> Broadcast Complete!")

# ==========================================
# 🌧 GROUP RAIN & LEADERBOARD
# ==========================================
@bot.message_handler(commands=['rain'])
def rain_command(message):
    if message.chat.type == "private": return bot.reply_to(message, "Use this command in a group!")
    
    try:
        parts = message.text.split(maxsplit=3)
        gift_name = parts[1].replace("_", " ")
        winners_count = int(parts[2])
        comment = parts[3] if len(parts) > 3 else "Group Rain Gift!"
    except Exception: return bot.reply_to(message, "❌ <b>Format:</b> <code>/rain Gift_Name Amount_of_Winners Comment</code>\n<b>Example:</b> <code>/rain Heart 1 Happy</code>", parse_mode="HTML")
        
    g = next((item for item in GIFTS_CACHE if item["name"].lower() == gift_name.lower()), None)
    if not g: return bot.reply_to(message, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> Gift not found!")
    
    actual_gift_name = g["name"]
    gift_unit_price = g["price"]
    if actual_gift_name.lower() in ["teddy bear", "heart"] and gift_unit_price == 7: gift_unit_price = 14
        
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
        if not u_doc: blocked = True
        else:
            try: bot.send_chat_action(wid, 'typing')
            except Exception: blocked = True
                
        if blocked:
            rain_id = str(uuid.uuid4().hex)[:8]
            pending_rains_col.insert_one({"_id": rain_id, "user_id": wid, "gift_name": actual_gift_name, "price": gift_unit_price, "comment": comment})
            markup = kb([(LANG["en"]["rain_claim"], f"https://t.me/{CONFIG['BOT_USERNAME']}?start=rain_{rain_id}", "success")])
            bot.send_message(group_id, f"Hey <a href='tg://user?id={wid}'>{wname}</a>, you won a <b>{actual_gift_name}</b>! Start the bot to claim.", reply_markup=markup, parse_mode="HTML")
        else: send_real_telegram_gift(wid, actual_gift_name, gift_unit_price, comment)

    for w in winners: threading.Thread(target=handle_rain_winner, args=(w["user_id"], w.get("username", "User"), message.chat.id)).start()

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
                id="insufficient", title="❌ Insufficient Stars!",
                description=f"You need {amount} ⭐️ but have {user['balance']} ⭐️.",
                input_message_content=InputTextMessageContent("Insufficient balance to send this check.")
            )
            return bot.answer_inline_query(inline_query.id, [res], cache_time=1)
            
        check_id = str(uuid.uuid4().hex)[:10]
        markup = kb([(LANG["en"]["check_claim"].replace("⭐️", f"{amount} ⭐️"), f"https://t.me/{CONFIG['BOT_USERNAME']}?start=chk_{check_id}", "success")])
        checks_col.insert_one({"_id": check_id, "creator": inline_query.from_user.id, "amount": amount, "status": "active"})
        
        res = InlineQueryResultArticle(
            id=check_id, title=f"Create Check for {amount} ⭐️", description=comment,
            input_message_content=InputTextMessageContent(f"<b>⭐️ Telegram Stars Check</b>\n\nAmount: {amount} ⭐️\n💬 {comment}", parse_mode="HTML"),
            reply_markup=markup
        )
        bot.answer_inline_query(inline_query.id, [res], cache_time=1)
    except Exception: pass

@bot.chosen_inline_handler(func=lambda chosen_inline_result: True)
def chosen_check(chosen_inline_result):
    if chosen_inline_result.inline_message_id: checks_col.update_one({"_id": chosen_inline_result.result_id}, {"$set": {"inline_msg_id": chosen_inline_result.inline_message_id}})
        
# ==========================================
# 🚀 USER HANDLERS (START MENU)
# ==========================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    user = get_user(message.from_user.id, message.from_user.username)
    
    if len(message.text.split()) > 1:
        param = message.text.split()[1]
        
        if param.startswith("chk_"):
            check_id = param.replace("chk_", "")
            chk = checks_col.find_one({"_id": check_id})
            
            if not chk or chk["status"] != "active":
                return bot.reply_to(message, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Check already claimed or bounced.</b>")
                
            if chk["creator"] == message.from_user.id:
                return bot.reply_to(message, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> You cannot claim your own check!")
                
            creator_user = get_user(chk["creator"])
            if creator_user["balance"] < chk["amount"]:
                checks_col.update_one({"_id": check_id}, {"$set": {"status": "bounced"}})
                return bot.reply_to(message, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Check Bounced!</b> The creator doesn't have enough stars anymore.")
                
            update_balance(chk["creator"], -chk["amount"])
            checks_col.update_one({"_id": check_id}, {"$set": {"status": "claimed", "claimer": message.from_user.id}})
            update_balance(message.from_user.id, chk["amount"])
            
            bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> <b>You received {chk['amount']} ⭐️!</b>")
            try: bot.send_message(chk["creator"], f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> User @{message.from_user.username or message.from_user.first_name} claimed your checked amount of {chk['amount']} ⭐️!")
            except Exception: pass
            
            inline_msg_id = chk.get("inline_msg_id")
            if inline_msg_id:
                try: bot.edit_message_reply_markup(inline_message_id=inline_msg_id, reply_markup=kb([("Claimed", "already_claimed", "success")]))
                except Exception: pass
            return

        elif param.startswith("rain_"):
            rain_id = param.replace("rain_", "")
            r = pending_rains_col.find_one({"_id": rain_id, "user_id": message.from_user.id})
            if r:
                pending_rains_col.delete_one({"_id": rain_id})
                threading.Thread(target=send_real_telegram_gift, args=(message.from_user.id, r["gift_name"], r["price"], r["comment"])).start()
                return

        elif param.startswith("gwc_"):
            gw_id = param.replace("gwc_", "")
            gw = giveaways_col.find_one({"_id": gw_id})
            if gw and gw['status'] == 'active':
                if message.from_user.id in gw.get('participants', []): return bot.reply_to(message, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> You are already participating!")
                a, b = random.randint(1, 10), random.randint(1, 10)
                msg = bot.reply_to(message, f"<tg-emoji emoji-id='{TE['PROFILE']}'>🤖</tg-emoji> <b>Captcha Check</b>\nWhat is {a} + {b}?")
                bot.register_next_step_handler(msg, process_gw_captcha, gw_id, a+b)
                return

    bot.send_message(message.chat.id, f"<b>Welcome, {message.from_user.first_name}!</b> <tg-emoji emoji-id='{TE['WELCOME']}'>👋</tg-emoji>")
    bot.send_message(message.chat.id, get_start_text(user["lang"], message.from_user.first_name, user["balance"]), reply_markup=main_menu_kb(user["lang"]))

def process_gw_captcha(message, gw_id, ans):
    if message.text and message.text.isdigit() and int(message.text) == ans:
        get_user(message.from_user.id, message.from_user.username) 
        giveaways_col.update_one({"_id": gw_id}, {"$addToSet": {"participants": message.from_user.id}})
        update_gw_post_participants(gw_id)
        bot.reply_to(message, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> <b>Captcha solved!</b> You are now entered in the giveaway.")
    else: bot.reply_to(message, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Incorrect!</b> Please try joining the giveaway again.")

# ==========================================
# 🔄 FAST CALLBACK HANDLER
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('gw_join_'))
def gw_join_handler(call):
    gw_id = call.data.replace('gw_join_', '')
    gw = giveaways_col.find_one({"_id": gw_id})
    if not gw or gw['status'] != 'active': return bot.answer_callback_query(call.id, "Giveaway is over or not found!", show_alert=True)
    if call.from_user.id in gw.get('participants', []): return bot.answer_callback_query(call.id, "You are already participating!", show_alert=True)
        
    if not check_user_joined(gw['host_chat'], call.from_user.id):
        return bot.answer_callback_query(call.id, f"❌ You must join {gw.get('host_chat_name', gw['host_chat'])} first!", show_alert=True)
        
    for rc in gw.get('req_channels', []):
        if not check_user_joined(rc, call.from_user.id): return bot.answer_callback_query(call.id, f"❌ You must join all required channels first!", show_alert=True)
            
    if gw.get('req_premium') and not call.from_user.is_premium:
        return bot.answer_callback_query(call.id, "❌ You must have Telegram Premium to participate.", show_alert=True)
        
    if gw.get('captcha'): return bot.answer_callback_query(call.id, "Please verify captcha in bot PM", url=f"https://t.me/{CONFIG['BOT_USERNAME']}?start=gwc_{gw_id}")
        
    get_user(call.from_user.id, call.from_user.username) 
    giveaways_col.update_one({"_id": gw_id}, {"$addToSet": {"participants": call.from_user.id}})
    update_gw_post_participants(gw_id)
    bot.answer_callback_query(call.id, "✅ You have successfully entered the giveaway!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('gwr_'))
def gw_reqs_toggle_handler(call):
    try: bot.answer_callback_query(call.id)
    except: pass
    draft = get_gw_draft(call.from_user.id)
    key = call.data.replace('gwr_', 'req_')
    if key in draft: draft[key] = not draft[key]
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=gw_reqs_kb(draft))
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('gwm_'))
def gwm_management_handler(call):
    try: bot.answer_callback_query(call.id)
    except: pass
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    if call.data == "gwm_list":
        gws = list(giveaways_col.find({"creator": user_id}).sort("end_time", -1).limit(15))
        if not gws:
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> You haven't hosted any giveaways yet.", chat_id, call.message.id, reply_markup=kb([("Back", "menu_giveaway", "danger")]))
        else:
            markup = InlineKeyboardMarkup()
            for gw in gws:
                s_icon = "🟢" if gw['status'] == 'active' else "🔴"
                p_name = f"{gw['prize_val']} Stars" if gw['prize_type'] == 'star' else gw['prize_val']
                markup.row(btn(f"{s_icon} {p_name} | {len(gw.get('participants',[]))} Entries", f"gwm_view_{gw['_id']}", "primary"))
            markup.row(btn("Back", "menu_giveaway", "danger"))
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['PROFILE']}'>🗂</tg-emoji> <b>Select a Giveaway to Manage:</b>", chat_id, call.message.id, reply_markup=markup)
            
    elif call.data.startswith("gwm_view_"):
        gw_id = call.data.replace("gwm_view_", "")
        gw = giveaways_col.find_one({"_id": gw_id})
        
        if gw['status'] == 'active':
            txt = f"<tg-emoji emoji-id='{TE['WIN']}'>🎉</tg-emoji> <b>Active Giveaway</b>\n\nPrize: {gw['prize_val']}\nEntries: {len(gw.get('participants', []))}\nEnds: <t:{int(gw['end_time'].timestamp())}:R>"
            markup = kb([("Cancel Giveaway", f"gwm_can_{gw_id}", "danger"), ("Repost", f"gwm_rep_{gw_id}", "primary")], [("Back", "gwm_list", "primary")])
            bot.edit_message_text(txt, chat_id, call.message.id, reply_markup=markup)
        else:
            txt = f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> <b>Ended Giveaway</b>\n\nPrize: {gw['prize_val']}\nEntries: {len(gw.get('participants', []))}\n\n<b>Winners:</b>\n"
            winners = gw.get('winner_ids', [])
            if winners:
                for w in winners: txt += f"- {get_username_formatted(w)}\n"
            else: txt += "No participants."
            
            if gw.get('prize_status') == 'sent':
                markup = kb([("Back", "gwm_list", "primary")])
                txt += "\n\n<i>Prize sent already, no reroll available.</i>"
            else:
                markup = kb([("Confirm & Send Prize", f"gwm_snd_{gw_id}", "success")], [("Reroll", f"gwm_rr_m_{gw_id}", "primary")], [("Back", "gwm_list", "danger")])
            bot.edit_message_text(txt, chat_id, call.message.id, reply_markup=markup, disable_web_page_preview=True)
            
    elif call.data.startswith("gwm_can_"):
        gw_id = call.data.replace("gwm_can_", "")
        gw = giveaways_col.find_one({"_id": gw_id})
        if gw and gw['status'] == 'active':
            if gw['prize_type'] == 'star':
                update_balance(user_id, gw['prize_val']); update_house_bal(-gw['prize_val'])
            giveaways_col.update_one({"_id": gw_id}, {"$set": {"status": "cancelled"}})
            try: bot.edit_message_text("Giveaway Cancelled.", gw['host_chat'], gw['msg_id'])
            except: pass
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> Giveaway Cancelled & Refunded.", chat_id, call.message.id, reply_markup=kb([("Back", "gwm_list", "primary")]))
            
    elif call.data.startswith("gwm_rep_"):
        gw_id = call.data.replace("gwm_rep_", "")
        gw = giveaways_col.find_one({"_id": gw_id})
        if gw and gw['status'] == 'active':
            txt = build_giveaway_text(gw)
            markup = kb([("Join Giveaway", f"gw_join_{gw_id}", "success")])
            try: bot.delete_message(gw['host_chat'], gw['msg_id'])
            except: pass
            if gw.get('banner'): posted = bot.send_photo(gw['host_chat'], gw['banner'], caption=txt, reply_markup=markup, parse_mode="HTML")
            else: posted = bot.send_message(gw['host_chat'], txt, reply_markup=markup, parse_mode="HTML")
            giveaways_col.update_one({"_id": gw_id}, {"$set": {"msg_id": posted.message_id}})
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> Giveaway Reposted.", chat_id, call.message.id, reply_markup=kb([("Back", f"gwm_view_{gw_id}", "primary")]))

    elif call.data.startswith("gwm_snd_"):
        gw_id = call.data.replace("gwm_snd_", "")
        gw = giveaways_col.find_one({"_id": gw_id})
        if gw.get('prize_status') == 'sent': return bot.answer_callback_query(call.id, "Price sent already, no reroll available.", show_alert=True)
            
        for w in gw.get('winner_ids', []):
            if gw['prize_type'] == 'star':
                update_balance(w, gw['prize_val'])
                try: bot.send_message(w, f"🎉 You have received {gw['prize_val']} stars from a giveaway!")
                except: pass
            else:
                try: bot.send_message(w, f"🎉 You have won {gw['prize_val']} from a giveaway! Contact the host to claim.")
                except: pass
                
        giveaways_col.update_one({"_id": gw_id}, {"$set": {"prize_status": "sent"}})
        bot.edit_message_text("Price sent already, no reroll available.", chat_id, call.message.id, reply_markup=kb([("Back", "gwm_list", "primary")]))
        
    elif call.data.startswith("gwm_rr_m_"):
        gw_id = call.data.replace("gwm_rr_m_", "")
        gw = giveaways_col.find_one({"_id": gw_id})
        if gw.get('prize_status') == 'sent': return bot.answer_callback_query(call.id, "Price sent already, no reroll available.", show_alert=True)
            
        winners = gw.get('winner_ids', [])
        if len(winners) <= 1:
            perform_reroll(gw_id)
            gwm_management_handler(type('obj', (object,), {'id': call.id, 'data': f"gwm_view_{gw_id}", 'from_user': call.from_user, 'message': call.message}))
        else:
            markup = kb([("All winners", f"gwm_rr_all_{gw_id}", "primary"), ("Expect winner", f"gwm_rr_exc_{gw_id}", "primary")], [("Back", f"gwm_view_{gw_id}", "danger")])
            bot.edit_message_text("Choose reroll type:", chat_id, call.message.id, reply_markup=markup)
            
    elif call.data.startswith("gwm_rr_all_"):
        gw_id = call.data.replace("gwm_rr_all_", "")
        perform_reroll(gw_id)
        gwm_management_handler(type('obj', (object,), {'id': call.id, 'data': f"gwm_view_{gw_id}", 'from_user': call.from_user, 'message': call.message}))
        
    elif call.data.startswith("gwm_rr_exc_"):
        gw_id = call.data.replace("gwm_rr_exc_", "")
        gw = giveaways_col.find_one({"_id": gw_id})
        markup = InlineKeyboardMarkup()
        for w in gw.get('winner_ids', []):
            markup.add(btn(get_username_formatted(w).replace("<a href='tg://user?id=","").replace("'>User</a>","").replace("@",""), f"gwm_r1_{gw_id}_{w}", "primary"))
        markup.add(btn("Back", f"gwm_rr_m_{gw_id}", "danger"))
        bot.edit_message_text("Select the winner you want to REPLACE:", chat_id, call.message.id, reply_markup=markup)
        
    elif call.data.startswith("gwm_r1_"):
        parts = call.data.split("_")
        gw_id = parts[2]
        user_to_replace = int(parts[3])
        perform_reroll(gw_id, [user_to_replace])
        gwm_management_handler(type('obj', (object,), {'id': call.id, 'data': f"gwm_view_{gw_id}", 'from_user': call.from_user, 'message': call.message}))

@bot.callback_query_handler(func=lambda call: call.data.startswith('gw_') or call.data == 'menu_cancel_gw')
def gw_callbacks(call):
    if call.data.startswith('gw_join_') or call.data.startswith('gwr_') or call.data.startswith('gwm_'): return 
    try: bot.answer_callback_query(call.id)
    except: pass
    
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    data = call.data
    draft = get_gw_draft(user_id)
    bot.clear_step_handler_by_chat_id(chat_id)
    
    try:
        if data == "menu_cancel_gw":
            if draft.get('stars_deducted') and draft.get('prize_val'):
                update_balance(user_id, draft['prize_val']); update_house_bal(-draft['prize_val'])
            reset_gw_draft(user_id)
            user = get_user(user_id)
            bot.edit_message_text(get_start_text(user["lang"], call.from_user.first_name, user["balance"]), chat_id, call.message.id, reply_markup=main_menu_kb(user["lang"]))
            
        elif data == "gw_new":
            reset_gw_draft(user_id); draft = get_gw_draft(user_id); draft['wizard_msg_id'] = call.message.message_id
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['DOWN']}'>👇</tg-emoji> <b>Step 1: Select Host Chat</b>\n\nSend the channel or group username (e.g., @mychannel) or ID.\n⚠️ <i>Make sure I am an Admin there!</i>", chat_id, call.message.id, reply_markup=gw_cancel_kb())
            bot.register_next_step_handler_by_chat_id(chat_id, gw_step_host)
            
        elif data == "gw_prize_star":
            draft['prize_type'] = 'star'
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['STAR']}'>⭐️</tg-emoji> <b>Send the number of Stars for the prize:</b>", chat_id, draft['wizard_msg_id'], reply_markup=gw_cancel_kb())
            bot.register_next_step_handler_by_chat_id(chat_id, gw_step_star_amt)
            
        elif data == "gw_prize_custom":
            draft['prize_type'] = 'custom'
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['GIFT']}'>🎁</tg-emoji> <b>Send the prize name (example: Telegram Gift):</b>", chat_id, draft['wizard_msg_id'], reply_markup=gw_cancel_kb())
            bot.register_next_step_handler_by_chat_id(chat_id, gw_step_custom_name)
            
        elif data == "gw_ask_banner":
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['PROFILE']}'>🖼</tg-emoji> <b>Banner</b>\nDo you want a banner? Send image or click Skip.", chat_id, draft['wizard_msg_id'], reply_markup=gw_skip_kb("gw_ask_hostedby"))
            bot.register_next_step_handler_by_chat_id(chat_id, gw_step_banner)
            
        elif data == "gw_ask_hostedby":
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['PROFILE']}'>👤</tg-emoji> <b>Send Hosted by</b> (a name or @username)", chat_id, draft['wizard_msg_id'], reply_markup=gw_skip_kb("gw_ask_winners"))
            bot.register_next_step_handler_by_chat_id(chat_id, gw_step_hostedby)
            
        elif data == "gw_ask_winners":
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['WIN']}'>🏆</tg-emoji> <b>Number of winners (>=1)</b>", chat_id, draft['wizard_msg_id'], reply_markup=gw_cancel_kb())
            bot.register_next_step_handler_by_chat_id(chat_id, gw_step_winners)
            
        elif data == "gw_ask_duration":
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['DOWN']}'>⏳</tg-emoji> <b>Giveaway duration</b> (e.g., 1d 12h, 10h, 30m, or seconds).", chat_id, draft['wizard_msg_id'], reply_markup=gw_cancel_kb())
            bot.register_next_step_handler_by_chat_id(chat_id, gw_step_duration)
            
        elif data.startswith("gw_set_cap_"):
            draft['captcha'] = data.endswith("1")
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['TICKET']}'>🔗</tg-emoji> <b>Required Channels</b>\nSend additional required channels/groups as chat_id or @username separated by space, or press Skip", chat_id, draft['wizard_msg_id'], reply_markup=gw_skip_kb("gw_ask_notes"))
            bot.register_next_step_handler_by_chat_id(chat_id, gw_step_channels)
            
        elif data == "gw_ask_notes":
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['DOWN']}'>📝</tg-emoji> <b>Additional Notes</b>\nRules, links - anything you want participants to see (or click Skip).", chat_id, draft['wizard_msg_id'], reply_markup=gw_skip_kb("gw_edit_reqs"))
            bot.register_next_step_handler_by_chat_id(chat_id, gw_step_notes)
            
        elif data == "gw_edit_reqs":
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['TICKET']}'>🛠</tg-emoji> <b>Requirements</b>\nConfigure participation restrictions. Continue when ready.", chat_id, draft['wizard_msg_id'], reply_markup=gw_reqs_kb(draft))
            
        elif data == "gw_preview":
            txt = build_giveaway_text(draft, preview_mode=True)
            bot.edit_message_text(f"<tg-emoji emoji-id='{TE['SUCCESS']}'>📋</tg-emoji> <b>Message Layout / Preview</b>\n\n{txt}", chat_id, draft['wizard_msg_id'], reply_markup=gw_preview_kb(), parse_mode="HTML")
            
        elif data == "gw_publish":
            end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=draft['duration'])
            gw_id = str(uuid.uuid4().hex)[:10]
            
            giveaways_col.insert_one({
                "_id": gw_id, "creator": user_id, "host_chat": draft['host_chat'], "host_chat_name": draft['host_chat_name'],
                "prize_type": draft['prize_type'], "prize_val": draft['prize_val'],
                "winners": draft['winners'], "captcha": draft['captcha'],
                "req_channels": draft['req_channels'], "req_channels_names": draft.get('req_channels_names', []),
                "end_time": end_time, "status": "active", "participants": [], "notes": draft['notes'],
                "hosted_by": draft['hosted_by'], "title": draft.get('title', 'Giveaway'),
                "req_premium": draft.get('req_premium'), "req_boost": draft.get('req_boost'),
                "prize_status": "pending"
            })
            
            txt = build_giveaway_text(draft, preview_mode=False)
            markup = kb([("Join Giveaway", f"gw_join_{gw_id}", "success")])
            
            try:
                if draft['banner']: posted = bot.send_photo(draft['host_chat'], draft['banner'], caption=txt, reply_markup=markup, parse_mode="HTML")
                else: posted = bot.send_message(draft['host_chat'], txt, reply_markup=markup, parse_mode="HTML")
                    
                giveaways_col.update_one({"_id": gw_id}, {"$set": {"msg_id": posted.message_id}})
                bot.edit_message_text(f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> <b>Giveaway Published successfully!</b>", chat_id, draft['wizard_msg_id'], reply_markup=kb([("Back to menu", "menu_main", "primary")]))
                reset_gw_draft(user_id)
            except Exception as e:
                bot.edit_message_text(f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Error publishing:</b> {e}\nEnsure bot is admin in the target chat.", chat_id, draft['wizard_msg_id'], reply_markup=gw_preview_kb())
            
    except Exception as e: print(f"GW Callback Error: {e}")

@bot.callback_query_handler(func=lambda call: not call.data.startswith('gw_') and not call.data.startswith('gwr_') and not call.data.startswith('gwm_') and call.data != 'menu_cancel_gw')
def callback_handler(call):
    try: bot.answer_callback_query(call.id)
    except Exception: pass
    
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
            parts = data.split("_")
            bet = int(parts[1])
            target = parts[2]
            
            if user["balance"] < bet: return bot.answer_callback_query(call.id, "Insufficient balance!", show_alert=True)
                
            update_balance(user_id, -bet)
            if chat_id:
                try: bot.edit_message_text(f"🎰 Rolling the slot machine for {bet} ⭐️...", chat_id=chat_id, message_id=call.message.message_id)
                except Exception: pass
                dice_msg = bot.send_dice(chat_id, emoji="🎰")
                threading.Thread(target=process_slot_result, args=(chat_id, call.message.message_id, user_id, bet, target, dice_msg.dice.value)).start()
            return

        if not chat_id: return 

        if data == "switch_lang":
            new_lang = "ru" if lang == "en" else "en"
            users_col.update_one({"_id": user_id}, {"$set": {"lang": new_lang}})
            try: bot.edit_message_text(get_start_text(new_lang, call.from_user.first_name, user["balance"]), chat_id, call.message.message_id, reply_markup=main_menu_kb(new_lang))
            except Exception: pass
            
        elif data == "menu_main":
            try: bot.edit_message_text(get_start_text(lang, call.from_user.first_name, user["balance"]), chat_id, call.message.message_id, reply_markup=main_menu_kb(lang))
            except Exception: pass
            
        elif data == "menu_profile":
            try: bot.edit_message_text(LANG[lang]["profile_text"].format(id=user_id, username=user.get("username", "None"), balance=user["balance"]), chat_id, call.message.message_id, reply_markup=profile_kb(lang))
            except Exception: pass
            
        elif data == "menu_topup":
            try:
                msg = bot.edit_message_text(LANG[lang]["topup_text"], chat_id, call.message.message_id, reply_markup=topup_kb(lang))
                bot.register_next_step_handler(msg, process_custom_topup)
            except Exception: pass
            
        elif data == "menu_gifts":
            try: bot.edit_message_text(LANG[lang]["gift_text"], chat_id, call.message.message_id, reply_markup=gifts_kb(lang, user))
            except Exception: pass
        
        elif data == "menu_giveaway":
            try: bot.edit_message_text(f"<tg-emoji emoji-id='{TE['WIN']}'>🎉</tg-emoji> <b>Giveaway</b>\n\nHost a giveaway in your channel or group with entry rules, captcha and automatic winners.", chat_id, call.message.message_id, reply_markup=gw_main_kb())
            except Exception: pass

        elif data == "menu_luck":
            try: bot.edit_message_text(LANG[lang]["luck_text"], chat_id, call.message.message_id, reply_markup=luck_kb(lang))
            except Exception: pass
            
        elif data.startswith("slot_"):
            bet = int(data.split("_")[1])
            try: bot.edit_message_text(f"🍀 Select your condition for {bet} ⭐️:", chat_id, call.message.message_id, reply_markup=slot_options_kb(bet, lang))
            except Exception: pass
            
        elif data == "menu_promo":
            try:
                msg = bot.edit_message_text(LANG[lang]["promo_text"], chat_id, call.message.message_id)
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
                
                if amount == 7:
                    auto_comment = "A small gift by @redcube. Join today and earn and win money. Contact @Cinex"
                    threading.Thread(target=send_real_telegram_gift, args=(chat_id, gift_name, amount, auto_comment)).start()
                else:
                    markup = kb([("Skip Comment", f"skip|{gift_name}|{amount}", "primary")])
                    msg = bot.send_message(chat_id, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> <b>{gift_name}</b> purchased!\n\n💬 Please send a comment for your gift below, or click <b>Skip</b>.", reply_markup=markup)
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
            
    except Exception as e: print(f"Error in Callback: {e}")

# ==========================================
# 💰 PROCESS CUSTOM TOPUP
# ==========================================
def process_custom_topup(message):
    safe_delete(message.chat.id, message.message_id)
    if not message.text or not message.text.isdigit(): return
    amount = int(message.text)
    if amount < 1: return bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['ERROR']}'>❌</tg-emoji> Minimum amount is 1 ⭐️")
        
    bot.send_invoice(
        chat_id=message.chat.id, title="Top-Up Balance", description=f"Top up {amount} ⭐️", 
        invoice_payload=f"topup_{amount}", provider_token="", currency="XTR", prices=[LabeledPrice("Stars", amount)]
    )

# ==========================================
# 🎰 SLOT GAME EXACT LOGIC PROCESSOR
# ==========================================
def process_slot_result(chat_id, message_id, user_id, bet, target, dice_value):
    time.sleep(2.5) 
    is_win = False
    reward_name = ""
    
    v0 = dice_value - 1
    reel1 = v0 % 4
    reel2 = (v0 // 4) % 4
    reel3 = (v0 // 16) % 4
    
    is_any_combo = (reel1 == reel2 == reel3)
    is_unique_combo = (reel1 != reel2 and reel1 != reel3 and reel2 != reel3)
    
    if target == "any": 
        if is_any_combo: is_win = True
    elif target == "unique": 
        if is_unique_combo: is_win = True
            
    if is_win:
        if bet == 10: reward_name = "Rose" if target == "any" else "Teddy bear"
        elif bet == 15: reward_name = "Bouquet" if target == "any" else "Rose"
        elif bet == 30: reward_name = "Ring" if target == "any" else "Bouquet"
        else: reward_name = "Gift box"
            
        bot.send_message(chat_id, f"<tg-emoji emoji-id='{CONFIG['TEXT_EMOJI']['WIN']}'>🎉</tg-emoji> <b>WINNER!</b>\n\nYou won a {reward_name}!")
        g = next((item for item in GIFTS_CACHE if item["name"].lower() == reward_name.lower()), None)
        price = 14 if reward_name.lower() in ["teddy bear", "heart"] else (g["price"] if g else bet)
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
    safe_delete(message.chat.id, message.message_id)
    if not message.text: return bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> Please send a valid text comment. Try buying again.")
    threading.Thread(target=send_real_telegram_gift, args=(message.chat.id, gift_name, amount, message.text)).start()

# ==========================================
# 🎟 PROMO PROCESSOR
# ==========================================
def process_promo_code(message, lang):
    safe_delete(message.chat.id, message.message_id)
    code = message.text.upper()
    promo = promos_col.find_one({"_id": code})
    markup = kb([(LANG[lang]["btn_back"], "menu_profile", "danger")])
    
    if not promo: return bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Invalid Promo Code!</b>", reply_markup=markup)
    
    expires_at = promo["expires_at"]
    if expires_at.tzinfo is None: expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
        
    if datetime.datetime.now(datetime.timezone.utc) > expires_at: return bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Promo Expired!</b>", reply_markup=markup)
    if message.from_user.id in promo["used_by"]: return bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Already used!</b>", reply_markup=markup)
    if len(promo["used_by"]) >= promo["max_users"]: return bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['ERROR']}'>❌</tg-emoji> <b>Limit reached!</b>", reply_markup=markup)
    
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
            
        if amount == 7:
            auto_comment = "A small gift by @redcube. Join today and earn and win money. Contact @Cinex"
            threading.Thread(target=send_real_telegram_gift, args=(message.chat.id, gift_name, amount, auto_comment)).start()
        else:
            markup = kb([("Skip Comment", f"skip|{gift_name}|{amount}", "primary")])
            msg = bot.send_message(message.chat.id, f"<tg-emoji emoji-id='{TE['SUCCESS']}'>✅</tg-emoji> <b>{gift_name}</b> purchased!\n\n💬 Please send a comment for your gift below, or click <b>Skip</b>.", reply_markup=markup)
            bot.register_next_step_handler(msg, process_gift_comment, gift_name, amount)

    safe_delete(message.chat.id, message.message_id)

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

# ==========================================
# ⏱ GIVEAWAY BACKGROUND WORKER
# ==========================================
def giveaway_worker():
    while True:
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            ended_gws = giveaways_col.find({"status": "active", "end_time": {"$lte": now}})
            for gw in ended_gws:
                participants = gw.get("participants", [])
                winners_count = gw["winners"]
                winner_ids = random.sample(participants, min(len(participants), winners_count)) if participants else []
                
                giveaways_col.update_one({"_id": gw["_id"]}, {"$set": {"status": "ended", "winner_ids": winner_ids}})
                update_gw_post_ended(gw["_id"])
                
                creator_msg = f"<tg-emoji emoji-id='{TE['WIN']}'>🎉</tg-emoji> <b>Giveaway Ended!</b>\n\nPrize: {gw['prize_val']}\nWinners: {len(winner_ids)}\n\nWhat would you like to do?"
                markup = kb([("Confirm and Send Prize", f"gwm_snd_{gw['_id']}", "success")], [("Reroll", f"gwm_rr_m_{gw['_id']}", "primary")])
                try: bot.send_message(gw["creator"], creator_msg, reply_markup=markup)
                except: pass
                
        except Exception as e: print(f"Giveaway Worker Error: {e}")
        time.sleep(10)

threading.Thread(target=giveaway_worker, daemon=True).start()

print("🚀 Fully Loaded Premium Styled Bot (with Giveaways) is running...")
bot.infinity_polling(skip_pending=True)
