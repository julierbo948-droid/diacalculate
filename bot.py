import asyncio
import logging
import os
import re
import aiohttp
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- ၁။ Setup & Configuration ---
load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
MONGO_URL = os.getenv('MONGO_URL')

client = AsyncIOMotorClient(MONGO_URL)
db = client['mlbb_bot_db']
users_col = db['user_settings']
approved_col = db['approved_users']

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ၂။ Premium Emoji IDs ---
HEART_EMOJI_ID = "6179090116414283047"
DIAMOND_EMOJI_ID = "6185744240526499155"
WEEKLY_EMOJI_ID = "6179026014027389952"
TWILIGHT_EMOJI_ID = "6113808606379908695"
WBUNDLE_EMOJI_ID = "6199726197320981347"
MBUNDLE_EMOJI_ID = "6199302017760894623"
DOUBLE_EMOJI_ID = "6199737316991311031"
RATE_EMOJI_ID = "6186016335294636592"
ARROW_EMOJI_ID = "6199561309231522146"
REGULAR_EMOJI_ID = "6186142585858301432"
REQ_EMOJI_ID = "6199433963451194506"

h_emo = f"<tg-emoji emoji-id='{HEART_EMOJI_ID}'>❤️</tg-emoji>"
d_emo = f"<tg-emoji emoji-id='{DIAMOND_EMOJI_ID}'>💎</tg-emoji>"
w_emo = f"<tg-emoji emoji-id='{WEEKLY_EMOJI_ID}'>📆</tg-emoji>"
t_emo = f"<tg-emoji emoji-id='{TWILIGHT_EMOJI_ID}'>🛡️</tg-emoji>"
wb_emo = f"<tg-emoji emoji-id='{WBUNDLE_EMOJI_ID}'>🎁</tg-emoji>"
m_emo = f"<tg-emoji emoji-id='{MBUNDLE_EMOJI_ID}'>👑</tg-emoji>"
db_emo = f"<tg-emoji emoji-id='{DOUBLE_EMOJI_ID}'>💎</tg-emoji>"
re_emo = f"<tg-emoji emoji-id='{RATE_EMOJI_ID}'>📊</tg-emoji>"
a_emo = f"<tg-emoji emoji-id='{ARROW_EMOJI_ID}'>➡️</tg-emoji>"
rg_emo = f"<tg-emoji emoji-id='{REGULAR_EMOJI_ID}'>💎</tg-emoji>"
rq_emo = f"<tg-emoji emoji-id='{REQ_EMOJI_ID}'>🔑</tg-emoji>"

# --- ၃။ ဈေးနှုန်းဒေတာများ ---
COIN_PRICES = {
    "Small": {"11": 9.50, "22": 19.00, "33": 28.50, "44": 38.00, "56": 47.50, "112": 95.00},
    "Double": {"55": 39.00, "165": 116.90, "275": 187.50, "565": 385.00},
    "Regular": {
        "86": 61.50, "172": 122.00, "257": 177.50, "343": 239.00, "429": 299.50,
        "514": 355.00, "600": 416.50, "706": 480.00, "878": 602.00, "963": 657.50,
        "1049": 719.00, "1135": 779.50, "1412": 960.00, "1584": 1082.00, "1755": 1199.00,
        "2195": 1453.00, "2538": 1692.00, "2901": 1933.00, "3244": 2172.00, "3688": 2424.00,
        "5532": 3660.00, "9288": 6079.00
    },
    "WP": {
        "wp1": 76.00, "wp2": 152.00, "wp3": 228.00, "wp4": 304.00, "wp5": 380.00,
        "wp6": 456.00, "wp7": 532.00, "wp8": 608.00, "wp9": 684.00, "wp10": 760.00
    },
    "Others": {"tp": 402.50, "web": 39.00, "meb": 196.50}
}

# --- ၄။ Database & Helper Functions ---
async def get_user_setting(user_id, key):
    user = await users_col.find_one({"user_id": user_id, "key": key})
    if user: return user['value']
    default = await users_col.find_one({"user_id": 0, "key": key})
    return default['value'] if default else {"rate_large": 80.0, "rate_small": 80.0, "profit": 5.0}.get(key)

async def is_approved(user_id):
    if user_id == ADMIN_ID: return True
    user = await approved_col.find_one({"user_id": user_id})
    return user is not None

async def get_db_rate():
    config = await db.settings.find_one({"type": "rate_config"})
    return config.get("usd_to_mmk", 4550) if config else 4550

async def get_exchange_data():
    url = "https://api.binance.com/api/v3/ticker/price"
    rates = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                data = await response.json()
                for item in data:
                    if item['symbol'] in ["TONUSDT", "USDTTHB"]:
                        rates[item['symbol']] = float(item['price'])
        return rates
    except Exception: return {"TONUSDT": 0, "USDTTHB": 35}

# --- ၅။ Converter Handlers ---
@dp.message(Command(re.compile(r"^(u2m|m2u)$", re.I)))
async def usd_mmk_handler(message: Message):
    if not await is_approved(message.from_user.id): return
    args = message.text.split()
    if len(args) < 2: return await message.reply("💡 /u2m 100")
    rate = await get_db_rate()
    try:
        val = float(args[1])
        if "u2m" in message.text.lower():
            await message.reply(f"🇺🇸 {val:,} USD\n➡️ {val*rate:,.0f} MMK\n(Rate: {rate})")
        else:
            await message.reply(f"🇲🇲 {val:,} MMK\n➡️ {val/rate:,.2f} USD\n(Rate: {rate})")
    except: await message.reply("❌ ဂဏန်းထည့်ပါ။")

@dp.message(Command(re.compile(r"^(b2m|m2b|t2m|m2t)$", re.I)))
async def other_converters(message: Message):
    if not await is_approved(message.from_user.id): return
    args = message.text.split()
    if len(args) < 2: return
    rate = await get_db_rate()
    ex = await get_exchange_data()
    try:
        val = float(args[1])
        cmd = message.text.lower()
        if "b2m" in cmd:
            r = rate / ex.get("USDTTHB", 35)
            await message.reply(f"🇹🇭 {val:,} THB ➡️ {val*r:,.0f} MMK")
        elif "m2b" in cmd:
            r = rate / ex.get("USDTTHB", 35)
            await message.reply(f"🇲🇲 {val:,} MMK ➡️ {val/r:,.2f} THB")
        elif "t2m" in cmd:
            r = ex.get("TONUSDT", 0) * rate
            await message.reply(f"💎 {val:,} TON ➡️ {val*r:,.0f} MMK")
        elif "m2t" in cmd:
            r = ex.get("TONUSDT", 0) * rate
            await message.reply(f"🇲🇲 {val:,} MMK ➡️ {val/r:,.4f} TON")
    except: pass

@dp.message(Command("sr"))
async def set_db_rate(message: Message):
    if not await is_approved(message.from_user.id): return
    try:
        new_rate = int(message.text.split()[1])
        await db.settings.update_one({"type": "rate_config"}, {"$set": {"usd_to_mmk": new_rate}}, upsert=True)
        await message.reply(f"✅ USD Base Rate: {new_rate} MMK")
    except: await message.reply("❌ /sr 4650")

# --- ၆။ MLBB Handlers ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not await is_approved(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔑 အသုံးပြုခွင့်တောင်းရန်", callback_data=f"req_{message.from_user.id}")]])
        return await message.answer("❌ အသုံးပြုခွင့်မရှိပါ။", reply_markup=kb)
    
    text = f"{h_emo} <b>MLBB Bot</b>\n\n/price - ဈေးနှုန်း\n/u2m, /b2m, /t2m - Converter"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Price List", callback_data="btn_price")],
        [InlineKeyboardButton(text="⚙️ Set Rates", callback_data="btn_set_rate")],
        [InlineKeyboardButton(text="💰 Set Profit", callback_data="btn_set_profit")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@dp.message(Command("price"))
@dp.callback_query(F.data == "btn_price")
async def show_price(event):
    uid = event.from_user.id
    if not await is_approved(uid): return
    rl = await get_user_setting(uid, 'rate_large')
    rs = await get_user_setting(uid, 'rate_small')
    p = await get_user_setting(uid, 'profit')
    
    def qc(v, r, pr): return int(round(((v * r) * (1 + pr / 100)) / 50) * 50)

    res = f"{h_emo} <b>Diamond Prices</b>\n\n{w_emo} <b>Weekly:</b>\n"
    for k, v in COIN_PRICES["WP"].items(): res += f"• {k} {a_emo} {qc(v, rl, p):,} MMK\n"
    res += f"\n{rg_emo} <b>Regular:</b>\n"
    for k, v in COIN_PRICES["Small"].items(): res += f"• {k} {a_emo} {qc(v, rs, p):,} MMK\n"
    for k, v in COIN_PRICES["Regular"].items(): res += f"• {k} {a_emo} {qc(v, rl, p):,} MMK\n"
    
    msg = event if isinstance(event, Message) else event.message
    await msg.answer(res, parse_mode="HTML")
    if isinstance(event, CallbackQuery): await event.answer()

@dp.callback_query(F.data.startswith(("req_", "ok_")))
async def handle_auth(cb: CallbackQuery):
    if cb.data.startswith("req_"):
        await bot.send_message(ADMIN_ID, f"🔑 Request: {cb.from_user.id}", 
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Allow", callback_data=f"ok_{cb.from_user.id}")]]))
        await cb.answer("Admin ထံပို့ပြီး။")
    else:
        if cb.from_user.id != ADMIN_ID: return
        uid = int(cb.data.split("_")[1])
        await approved_col.update_one({"user_id": uid}, {"$set": {"approved": True}}, upsert=True)
        await bot.send_message(uid, "✅ အသုံးပြုခွင့်ရပါပြီ။")
        await cb.message.edit_text("Approved!")

@dp.callback_query(F.data.in_(["btn_set_rate", "btn_set_profit"]))
async def btn_settings(cb: CallbackQuery):
    await cb.message.answer("⚙️ /r <L> | /r2 <S> | /s <%> | /sr <USD>")
    await cb.answer()

@dp.message(Command("r", "r2", "s"))
async def handle_settings(message: Message, command: Command):
    if not await is_approved(message.from_user.id): return
    try:
        val = float(message.text.split()[1])
        k = "rate_large" if command.command == "r" else "rate_small" if command.command == "r2" else "profit"
        await users_col.update_one({"user_id": message.from_user.id, "key": k}, {"$set": {"value": val}}, upsert=True)
        await message.reply(f"✅ {k} = {val}")
    except: await message.reply("❌ Error")

async def main():
    for k, v in [("rate_large", 80.0), ("rate_small", 80.0), ("profit", 5.0)]:
        await users_col.update_one({"user_id": 0, "key": k}, {"$set": {"value": val}}, upsert=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
