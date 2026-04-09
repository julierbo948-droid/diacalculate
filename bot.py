import asyncio
import logging
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- .env ဖိုင်မှ အချက်အလက်များ ဆွဲယူခြင်း ---
load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
MONGO_URL = os.getenv('MONGO_URL')

# --- MongoDB ချိတ်ဆက်ခြင်း ---
client = AsyncIOMotorClient(MONGO_URL)
db = client['mlbb_bot_db']
users_col = db['user_settings']
approved_col = db['approved_users']

# Premium Emoji ID များ
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

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- Database Helper Functions (MongoDB Version) ---

async def get_user_setting(user_id, key):
    # User တစ်ဦးချင်းစီရဲ့ Setting ကို အရင်ရှာမည်
    user = await users_col.find_one({"user_id": user_id, "key": key})
    if user:
        return user['value']
    
    # မရှိပါက Global Default (user_id: 0) ကို ရှာမည်
    default = await users_col.find_one({"user_id": 0, "key": key})
    if default:
        return default['value']
    
    # လုံးဝမရှိသေးပါက Default တန်ဖိုးများ သတ်မှတ်ပေးရန်
    defaults = {"rate_large": 80.0, "rate_small": 80.0, "profit": 5.0}
    return defaults.get(key)

async def is_approved(user_id):
    if user_id == ADMIN_ID: return True
    user = await approved_col.find_one({"user_id": user_id})
    return user is not None

# --- ဈေးနှုန်းဒေတာများ ---
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

async def calc(coin_val, user_id, is_small=False):
    if is_small:
        rate = await get_user_setting(user_id, 'rate_small')
    else:
        rate = await get_user_setting(user_id, 'rate_large')
    profit = await get_user_setting(user_id, 'profit')
    total = (coin_val * rate) * (1 + profit / 100)
    return int(round(total / 50) * 50)

# --- Premium Emoji Global Variables ---
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

# --- Handlers ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not await is_approved(message.from_user.id):
        await message.answer(f"<tg-emoji emoji-id='{RATE_EMOJI_ID}'>❤️</tg-emoji>", parse_mode="HTML")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔑 အသုံးပြုခွင့်တောင်းရန်", callback_data=f"req_{message.from_user.id}")]
        ])
        return await message.answer("❌ သင်သည် ဤဘော့ကို အသုံးပြုခွင့် မရှိသေးပါ။\nAdmin ထံမှ ခွင့်ပြုချက် အရင်တောင်းပါ။", parse_mode="HTML", reply_markup=kb)

    text = f"{h_emo} <b>MLBB Diamond Price Calculator</b> {h_emo}\n\n🤖 ဤဘော့သည် MLBB Diamond ဈေးနှုန်းများကို တွက်ချက်ပေးသည်။\n\n📋 <b>အသုံးပြုနည်း:</b>\n• /price - ဈေးနှုန်းစာရင်းကြည့်ရန်\n• /r &lt;ဈေးနှုန်း&gt; - အကြီးစိန်များအတွက် rate သတ်မှတ်ရန်\n• /r2 &lt;ဈေးနှုန်း&gt; - စိန်အသေးများအတွက် rate သတ်မှတ်ရန်\n• /s &lt;ရာခိုင်နှုန်း&gt; - အမြတ်ငွေ သတ်မှတ်ရန်\n\n⚙️ သင့်ဈေးနှုန်းများကို ပြောင်းလဲပြီး /price နဲ့ ကြည့်နိုင်ပါသည်။"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Price List", callback_data="btn_price")],
        [InlineKeyboardButton(text="⚙️ Set Rates", callback_data="btn_set_rate")],
        [InlineKeyboardButton(text="💰 Set Profit", callback_data="btn_set_profit")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

# --- Optimized Calculation Functions ---

@dp.message(Command("price"))
async def cmd_price(message: Message):
    if not await is_approved(message.from_user.id):
        await message.reply("❌ သင်သည် ဤဘော့ကို အသုံးပြုခွင့် မရှိသေးပါ။")
        return

    # Database ကို ၃ ကြိမ်ပဲ ခေါ်ပြီး Memory ထဲမှာ သိမ်းထားမယ်
    user_id = message.from_user.id
    rate_l = await get_user_setting(user_id, 'rate_large')
    rate_s = await get_user_setting(user_id, 'rate_small')
    profit = await get_user_setting(user_id, 'profit')

    # တွက်ချက်မှုအတွက် Local Function တစ်ခု ဆောက်ထားမယ်
    def quick_calc(coin_val, r, p):
        total = (coin_val * r) * (1 + p / 100)
        return int(round(total / 50) * 50)

    text = f"{h_emo} <b>MLBB Diamond Prices</b> {h_emo}\n\n"
    
    # Weekly Pass Section
    text += f"{w_emo} <b>Weekly Pass:</b>\n"
    for k, v in COIN_PRICES["WP"].items():
        res = quick_calc(v, rate_l, profit)
        text += f"• {k} {a_emo} {res:,} MMK\n"

    # Regular & Small Diamonds Section
    text += f"\n{rg_emo} <b>Regular Diamonds:</b>\n"
    for k, v in COIN_PRICES["Small"].items():
        res = quick_calc(v, rate_s, profit) # စိန်အသေးအတွက် rate_small သုံးမယ်
        text += f"{d_emo} • {k} {a_emo} {res:,} MMK\n"
        
    for k, v in COIN_PRICES["Regular"].items():
        res = quick_calc(v, rate_l, profit)
        text += f"{d_emo} • {k} {a_emo} {res:,} MMK\n"

    # Double Diamonds Section
    text += f"\n{db_emo} <b>2X Diamond Pass:</b> {db_emo}\n"
    for k, v in COIN_PRICES["Double"].items():
        res = quick_calc(v, rate_l, profit)
        text += f"{d_emo} • {k} {a_emo} {res:,} MMK\n"

    # Others Section
    text += f"\n{t_emo} • Twilight Pass = {quick_calc(COIN_PRICES['Others']['tp'], rate_l, profit):,} MMK\n"
    text += f"{w_emo} Weekly elite bundle = {quick_calc(COIN_PRICES['Others']['web'], rate_l, profit):,} MMK\n"
    text += f"{m_emo} Monthly epic bundle = {quick_calc(COIN_PRICES['Others']['meb'], rate_l, profit):,} MMK\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Price", callback_data="btn_price")],
        [InlineKeyboardButton(text="⚙️ Set Rates", callback_data="btn_set_rate")],
        [InlineKeyboardButton(text="💰 Set Profit", callback_data="btn_set_profit")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data == "btn_price")
async def btn_price(cb: CallbackQuery):
    if not await is_approved(cb.from_user.id):
        await cb.answer("❌ သင်သည်ဤဘော့ကို အသုံးပြုခွင့်မရှိသေးပါ။", show_alert=True)
        return

    # Callback မှာလည်း အပေါ်ကအတိုင်း Database ခေါ်တာ လျှော့ချမယ်
    user_id = cb.from_user.id
    rate_l = await get_user_setting(user_id, 'rate_large')
    rate_s = await get_user_setting(user_id, 'rate_small')
    profit = await get_user_setting(user_id, 'profit')

    def quick_calc(coin_val, r, p):
        total = (coin_val * r) * (1 + p / 100)
        return int(round(total / 50) * 50)

    text = f"{h_emo} <b>MLBB Diamond Prices</b> {h_emo}\n\n"
    
    text += f"{w_emo} <b>Weekly Pass:</b>\n"
    for k, v in COIN_PRICES['WP'].items():
        res = quick_calc(v, rate_l, profit)
        text += f"• {k} {a_emo} {res:,} MMK\n"
    
    text += f"\n{rg_emo} <b>Regular Diamonds:</b>\n"
    for k, v in COIN_PRICES['Small'].items():
        res = quick_calc(v, rate_s, profit)
        text += f"{d_emo} • {k} {a_emo} {res:,} MMK\n"
        
    for k, v in COIN_PRICES['Regular'].items():
        res = quick_calc(v, rate_l, profit)
        text += f"{d_emo} • {k} {a_emo} {res:,} MMK\n"
    
    text += f"\n{db_emo} <b>2X Diamond Pass:</b> {db_emo}\n"
    for k, v in COIN_PRICES['Double'].items():
        res = quick_calc(v, rate_l, profit)
        text += f"{d_emo} • {k} {a_emo} {res:,} MMK\n"
    
    text += f"\n{t_emo} • Twilight Pass = {quick_calc(COIN_PRICES['Others']['tp'], rate_l, profit):,} MMK\n"
    text += f"{w_emo} Weekly elite bundle = {quick_calc(COIN_PRICES['Others']['web'], rate_l, profit):,} MMK\n"
    text += f"{m_emo} Monthly epic bundle = {quick_calc(COIN_PRICES['Others']['meb'], rate_l, profit):,} MMK\n"

    await cb.message.answer(text, parse_mode='HTML')
    await cb.answer()

@dp.callback_query(F.data.startswith("req_"))
async def request_access(cb: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ ခွင့်ပြုမည်", callback_data=f"ok_{cb.from_user.id}")]])
    await bot.send_message(ADMIN_ID, f"👤 <b>Access Request</b>\nName: {cb.from_user.full_name}\nID: {cb.from_user.id}", parse_mode="HTML", reply_markup=kb)
    await cb.answer("Admin ထံသို့ တောင်းဆိုချက် ပို့ပြီးပါပြီ။", show_alert=True)

@dp.callback_query(F.data.startswith("ok_"))
async def approve_user(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    uid = int(cb.data.split("_")[1])
    await approved_col.update_one({"user_id": uid}, {"$set": {"approved": True}}, upsert=True)
    await bot.send_message(uid, "✅ Admin က သင့်ကို အသုံးပြုခွင့် ပေးလိုက်ပါပြီ။\n/price ကို သုံးနိုင်ပါပြီ။")
    await cb.message.edit_text(f"✅ User {uid} ကို ခွင့်ပြုပြီးပါပြီ။")

@dp.callback_query(F.data == "btn_price")
async def btn_price(cb: CallbackQuery):
    if not await is_approved(cb.from_user.id):
        await cb.answer("❌ သင်သည်ဤဘော့ကို အသုံးပြုခွင့်မရှိသေးပါ။", show_alert=True)
        return
    
    text = f"{h_emo} <b>MLBB Diamond Prices</b> {h_emo}\n\n{w_emo} <b>Weekly Pass:</b>\n"
    for k, v in COIN_PRICES['WP'].items():
        res = await calc(v, cb.from_user.id)
        text += f"• {k} {a_emo} {res:,} MMK\n"
    
    text += f"\n{rg_emo} <b>Regular Diamonds:</b>\n"
    for k, v in COIN_PRICES['Small'].items():
        res = await calc(v, cb.from_user.id, is_small=True)
        text += f"{d_emo} • {k} {a_emo} {res:,} MMK\n\n"
    for k, v in COIN_PRICES['Regular'].items():
        res = await calc(v, cb.from_user.id)
        text += f"{d_emo} • {k} {a_emo} {res:,} MMK\n"
    
    text += f"\n{db_emo} <b>2X Diamond Pass:</b> {db_emo}\n"
    for k, v in COIN_PRICES['Double'].items():
        res = await calc(v, cb.from_user.id)
        text += f"{d_emo} • {k} {a_emo} {res:,} MMK\n"
    
    text += f"\n{t_emo} • Twilight Pass = {await calc(COIN_PRICES['Others']['tp'], cb.from_user.id):,} MMK\n"
    text += f"{w_emo} Weekly elite bundle = {await calc(COIN_PRICES['Others']['web'], cb.from_user.id):,} MMK\n"
    text += f"{m_emo} Monthly epic bundle = {await calc(COIN_PRICES['Others']['meb'], cb.from_user.id):,} MMK\n"
    await cb.message.answer(text, parse_mode='HTML')
    await cb.answer()

@dp.callback_query(F.data == "btn_set_rate")
async def btn_set_rate(cb: CallbackQuery):
    if not await is_approved(cb.from_user.id):
        await cb.answer("❌ သင်သည်ဤဘော့ကို အသုံးပြုခွင့်မရှိသေးပါ။", show_alert=True)
        return
    await cb.message.answer("📌 ဈေးနှုန်းကို အသေးစိတ် စည်းမျဉ်းပါ:\n/r &lt;အကြီးဈေးနှုန်း&gt; - အကြီးစိန်များအတွက်\n/r2 &lt;အသေးဈေးနှုန်း&gt; - စိန်အသေးများအတွက်\nဥပမာ: /r 85, /r2 90")
    await cb.answer()

@dp.callback_query(F.data == "btn_set_profit")
async def btn_set_profit(cb: CallbackQuery):
    if not await is_approved(cb.from_user.id):
        await cb.answer("❌ သင်သည်ဤဘော့ကို အသုံးပြုခွင့်မရှိသေးပါ။", show_alert=True)
        return
    await cb.message.answer("📌 အမြတ်ငွေ% ကို အသေးစိတ် စည်းမျဉ်းပါ: /s &lt;အတန်ဖိုး&gt;\nဥပမာ: /s 10")
    await cb.answer()

@dp.message(or_f(Command("role"), F.text.regexp(r"(?i)^\.role(?:$|\s+)")))
async def handle_check_role(message: types.Message):

    if not await is_authorized(message.from_user.id): return await message.reply("ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.")
    match = re.search(r"(?i)^[./]?role\s+(\d+)\s*[\(]?\s*(\d+)\s*[\)]?", message.text.strip())
    if not match: return await message.reply("❌ Invalid format. Use: `.role 12345678 1234`")
    
    game_id, zone_id = match.group(1).strip(), match.group(2).strip()
    loading_msg = await message.reply("<tg-emoji emoji-id='6186254847713484259'>❤️</tg-emoji>", parse_mode=ParseMode.HTML)

    # ---------------------------------------------------------
    # ၁။ Caliph Dev API (Name, Region စစ်ဆေးရန်)
    # ---------------------------------------------------------
    url_caliph = 'https://cekidml.caliph.dev/api/validasi'
    params_caliph = {
        'id': game_id,
        'serverid': zone_id
    }
    headers_caliph = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://cekidml.caliph.dev/',
        'X-Requested-With': 'XMLHttpRequest'
    }

    # ---------------------------------------------------------
    # ၂။ Malsawma Store API (Double Diamond Bonus စစ်ဆေးရန်)
    # ---------------------------------------------------------
    url_malsawma = 'https://www.malsawmastore.in/gadget/doublediamonds_action.php'
    payload_malsawma = {
        'id': game_id,
        'zone': zone_id
    }
    headers_malsawma = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
        'Origin': 'https://www.malsawmastore.in',
        'Referer': 'https://www.malsawmastore.in/gadget/doublediamonds',
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    }

    try:
        async with AsyncSession(impersonate="safari_ios") as local_scraper:
           
            await local_scraper.get('https://cekidml.caliph.dev/', headers=headers_caliph, timeout=15)
            
            res_caliph, res_malsawma = await asyncio.gather(
                local_scraper.get(url_caliph, params=params_caliph, headers=headers_caliph, timeout=15),
                local_scraper.post(url_malsawma, data=payload_malsawma, headers=headers_malsawma, timeout=15)
            )
        
        ig_name = "Unknown"
        region = "Unknown"

        try:
            data_caliph = res_caliph.json()
            
            if data_caliph.get('status') == 'success':
                result_data = data_caliph.get('result', {})
                ig_name = result_data.get('nickname', 'Unknown')
                region = result_data.get('country', 'Unknown')
            else:
                error_msg = data_caliph.get('message') or data_caliph.get('msg') or "Game ID သို့မဟုတ် Zone ID မှားယွင်းနေပါသည်။"
                return await loading_msg.edit_text(f"❌ <b>Invalid Account:</b> {error_msg}", parse_mode=ParseMode.HTML)

        except Exception as e:
        
            debug_msg = res_caliph.text[:120].replace('<', '&lt;').replace('>', '&gt;').strip()
            return await loading_msg.edit_text(f"❌ **API Error:**\n<code>{debug_msg}...</code>", parse_mode=ParseMode.HTML)


        limit_50 = limit_150 = limit_250 = limit_500 = True 
        debug_bonus_error = ""

        try:
            data_double = res_malsawma.json()
            if str(data_double.get('status', '')).lower() == 'true':
                dd_data = data_double.get('dd', {})
                limit_50 = not dd_data.get('50', False)
                limit_150 = not dd_data.get('150', False)
                limit_250 = not dd_data.get('250', False)
                limit_500 = not dd_data.get('500', False)
            else:
                debug_bonus_error = " <i>(Bonus Data Unavailable)</i>"
        except Exception as e:
            debug_bonus_error = " <i>(Bonus Data Error)</i>"

        # ==========================================
        # (ဂ) Keyboard နှင့် Report ထုတ်ပေးခြင်း
        # ==========================================
        style_50 = "danger" if limit_50 else "success"
        style_150 = "danger" if limit_150 else "success"
        style_250 = "danger" if limit_250 else "success"
        style_500 = "danger" if limit_500 else "success"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Bᴏɴᴜs 50+50", callback_data="ignore", style=style_50),
                InlineKeyboardButton(text="Bᴏɴᴜs 150+150", callback_data="ignore", style=style_150)
            ],
            [
                InlineKeyboardButton(text="Bᴏɴᴜs 250+250", callback_data="ignore", style=style_250),
                InlineKeyboardButton(text="Bᴏɴᴜs 500+500", callback_data="ignore", style=style_500)
            ]
        ])

        final_report = (
            f"<u><b>Mᴏʙɪʟᴇ Lᴇɢᴇɴᴅs Bᴀɴɢ Bᴀɴɢ</b></u>\n\n"
            f"🆔 <code>{'User ID' :<9}:</code> <code>{game_id}</code> (<code>{zone_id}</code>)\n"
            f"👤 <code>{'Nickname':<9}:</code> {ig_name}\n"
            f"🌍 <code>{'Region'  :<9}:</code> {region}\n"
            f"────────────────\n\n"
            f"🎁 <b>Fɪʀsᴛ Rᴇᴄʜᴀʀɢᴇ Bᴏɴᴜs Sᴛᴀᴛᴜs</b>{debug_bonus_error}"
        )

        await loading_msg.edit_text(final_report, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except Exception as e: 
        await loading_msg.edit_text(f"❌ System Error: {str(e)}", parse_mode=ParseMode.HTML)

@dp.message(Command("r", "r2", "s"))
async def handle_settings(message: Message, command: Command):
    if not await is_approved(message.from_user.id):
        await message.reply("❌ သင်သည် ဤဘော့ကို အသုံးပြုခွင့် မရှိသေးပါ။")
        return
    try:
        val = float(message.text.split()[1])
        key = "rate_large" if command.command == "r" else "rate_small" if command.command == "r2" else "profit"
        await users_col.update_one({"user_id": message.from_user.id, "key": key}, {"$set": {"value": val}}, upsert=True)
        await message.reply(f"{re_emo} သတ်မှတ်ချက် အောင်မြင်ပါသည်။", parse_mode="HTML")
    except:
        await message.reply("❌ မှန်ကန်စွာ ထည့်သွင်းပါ။")

async def main():
    # Global Default များ ထည့်သွင်းရန် (user_id: 0)
    for key, val in [("rate_large", 80.0), ("rate_small", 80.0), ("profit", 5.0)]:
        await users_col.update_one({"user_id": 0, "key": key}, {"$set": {"value": val}}, upsert=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
