import logging
import asyncio
import uuid
import os
import aiohttp
from dotenv import load_dotenv
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, ".env"))
from datetime import datetime, timedelta, timezone
TASHKENT_TZ = timezone(timedelta(hours=5))

UZ_MONTHS = {
    1: "yanvar", 2: "fevral", 3: "mart", 4: "aprel", 5: "may", 6: "iyun",
    7: "iyul", 8: "avgust", 9: "sentyabr", 10: "oktyabr", 11: "noyabr", 12: "dekabr"
}
UZ_WEEKDAYS = {
    0: "dushanba", 1: "seshanba", 2: "chorshanba", 3: "payshanba", 4: "juma", 5: "shanba", 6: "yakshanba"
}

def format_date(date_str):
    if not date_str or date_str == "Noma'lum":
        return date_str
    try:
        # Try YYYY-MM-DD HH:MM:SS
        if ' ' in str(date_str):
            dt = datetime.strptime(str(date_str), "%Y-%m-%d %H:%M:%S")
        elif '-' in str(date_str):
            # Try YYYY-MM-DD
            dt = datetime.strptime(str(date_str), "%Y-%m-%d")
        elif '.' in str(date_str):
            # Already in DD.MM.YYYY
            return str(date_str)
        else:
            return str(date_str)
        return dt.strftime("%d.%m.%Y")
    except:
        return str(date_str)
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import BaseMiddleware
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
import firebase_admin
from firebase_admin import credentials, db

# Doimiy mijozlar ro'yxati
REGULAR_CLIENTS = [
    "Comfort", "Iskandar", "Grand plaza", "Baxrom Uchtepa", 
    "Baxrom 9703", "Bahodir aka🚛", "Bahodir aka Andijon", "Akrom aka", 
    "Zoʻr mebel", "Umid", "Akmal aka", "Doʻkon 707", "Farxod Jomiy", "Munosib Mebel", "Ideal Max", "Muxtor aka",
    "Elyor", "Anor Mebel"
]

# Diller nomi -> Telegram ID(lar) xaritasi (bir nechta diller bir kompaniyada bo'lishi mumkin)
DILLER_TELEGRAM_MAP = {
    "Munosib Mebel": [261261387],
    "Zo\u02bbr mebel": [8043160151, 8897559819, 15541688],
    "Ideal Max": [953905880],
    "Iskandar": [1052843333],
    "Umid": [1270440064],
    "Elyor": [1268839562],
    "Anor Mebel": [1062031662, 531650486],
}

# Telegram ID -> Diller nomi (teskari xarita)
DILLER_ID_TO_CLIENT = {
    tg_id: client_name
    for client_name, id_list in DILLER_TELEGRAM_MAP.items()
    for tg_id in id_list
}

def get_clients_keyboard():
    buttons = []
    for i in range(0, len(REGULAR_CLIENTS), 2):
        row = [types.KeyboardButton(text=REGULAR_CLIENTS[i])]
        if i+1 < len(REGULAR_CLIENTS):
            row.append(types.KeyboardButton(text=REGULAR_CLIENTS[i+1]))
        buttons.append(row)
    buttons.append([types.KeyboardButton(text="Boshqa (Yangi diller)")])
    buttons.append([types.KeyboardButton(text="Bosh menyu")])
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

FAVORITE_MODELS = [
    "BF 06", "BF 07", "BF 09", 
    "BF 12", "BF 14", "BF 15", "BF 18",
    "BF 244", "BF 264", "BF 274", "BF 294",
    "BF 246", "BF 266", "BF 276", "BF 296",
    "BF 2461", "BF 2661", "BF 2761", "BF 2961",
    "BF SH 2461", "BF SH 2661", "BF SH 2761", "BF SH 2961",
    "BF 32", "BF 33", "BF 34", "BF 35", "BF 37", "BF 38", "BF 39",
    "BF 321", "BF 331", "BF 341", "BF 351", "BF 371", "BF 381", "BF 391",
    "BF 44", "BF 45",
    "BF 544", "BF 574", "BF 594",
    "BF 54-41", "BF 57-41", "BF 59-41",
    "BF 63", "BF 64", "BF 65", "BF 68",
    "BF 707", "BF 708", "BF 709",
    "BF 762", "BF 752", "BF 772", "KR 792",
    "BF 713", "BF 753", "BF 763",
    "D 100", "D 106", "D 109",
    "D 50", "D 59",
    "D 003", "D 004", "D 006", "D 005"
]

def get_models_keyboard(include_other=False):
    buttons = []
    row = []
    for model in FAVORITE_MODELS:
        row.append(types.KeyboardButton(text=model))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if include_other:
        buttons.append([types.KeyboardButton(text="Boshqa (Qo'lda kiritish)")])
    buttons.append([types.KeyboardButton(text="Bosh menyu")])
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_dates_keyboard(start_day=0):
    buttons = []
    row = []
    now = datetime.now(TASHKENT_TZ)
    for i in range(start_day, start_day + 15):
        date_str = (now + timedelta(days=i)).strftime("%d.%m.%Y")
        row.append(types.KeyboardButton(text=date_str))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([types.KeyboardButton(text="Bosh menyu")])
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# 1. Firebase Sozlamalari (RTDB)
cred_path = os.path.join(base_dir, "serviceAccountKey.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv('FIREBASE_DB_URL', 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app')
})

# 2. Bot Sozlamalari
API_TOKEN = os.getenv('API_TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# 3. FSM (Holatlar)
class ProductState(StatesGroup):
    name = State()
    model = State()
    price = State()
    quantity = State()
    image = State()

class UpdatePriceState(StatesGroup):
    product_id = State()
    new_price = State()

class FinanceState(StatesGroup):
    client_name = State()
    amount_kirim = State()
    amount_chiqim = State()

class DriverFinanceState(StatesGroup):
    driver_name = State()
    amount_kirim = State()
    amount_chiqim = State()

class OrderState(StatesGroup):
    client = State()      # Mijoz ismi
    custom_client = State() # Agar boshqa bosilsa
    product_id = State()  # Mebel ID-si
    custom_product_id = State() # Agar boshqa mebel bo'lsa
    custom_price = State() # Qo'lda kiritilgan mebel narxi
    amount = State()      # Nechta buyurtma berdi
    due_date = State()    # Qaysi sanaga tayyor bo'lishi kerak
    comment = State()     # Izoh

class UpdateStockState(StatesGroup):
    product_id = State()
    new_quantity = State()

class DeliveryControlState(StatesGroup):
    order_id = State()
    new_status = State()
    driver = State()
    delivery_price = State()
    custom_price = State()
    custom_driver = State()


class AdminOrderControlState(StatesGroup):
    select_order = State()
    action = State()
    edit_field = State()
    new_value = State()

class DillerOrderState(StatesGroup):
    select_product = State()  # Mebel tanlash
    amount = State()          # Nechta
    due_date = State()        # Qachon kerak

class DillerCancelState(StatesGroup):
    select_order = State()    # Bekor qilish uchun zakaz tanlash
    confirm = State()         # Tasdiqlash

class DillerPaymentState(StatesGroup):
    amount = State()          # To'lov summasi

# 4. Rollarni Tekshirish (RTDB dan)
async def get_user_role(user_id):
    user_id_str = str(user_id)
    if user_id_str == '883589794':
        return 'omborchi'
    if user_id_str in ['6298036669', '1349256808', '7062569902', '7941658592', '1724350130', '698145797', '5063420475']:
        return 'xodim'
    if user_id in DILLER_ID_TO_CLIENT:
        return 'diller'
    
    ref = db.reference(f'users/{user_id}')
    user_data = await asyncio.to_thread(ref.get)
    if user_data:
        role = user_data.get('role', 'mijoz')
        if role == 'ishchi':
            return 'xodim'
        return role
    return 'mijoz'

# 5. Klaviatura (Menyu)
def main_menu(role):
    buttons = []
    if role == 'admin':
        buttons = [
            [types.KeyboardButton(text="📦 Mavjud mebellar"), types.KeyboardButton(text="📝 Yangi buyurtma")],
            [types.KeyboardButton(text="📋 Buyurtmalar nazorati"), types.KeyboardButton(text="📊 Hisob kitoblar")],
            [types.KeyboardButton(text="🚚 Haydovchilar hisoboti"), types.KeyboardButton(text="💰 Dillerlar qarzi")],
            [types.KeyboardButton(text="🕰 Yetkazish tarixi"), types.KeyboardButton(text="📈 Sotuv statistikasi")]
        ]
    elif role == 'omborchi':
        buttons = [
            [types.KeyboardButton(text="🔄 Omborni yangilash"), types.KeyboardButton(text="🚚 Yetkazishlar nazorati")],
            [types.KeyboardButton(text="📦 Mavjud mebellar"), types.KeyboardButton(text="📊 Dostavka hisoboti")],
            [types.KeyboardButton(text="🕰 Yetkazish tarixi")]
        ]
    elif role == 'xodim':
        buttons = [
            [types.KeyboardButton(text="🔨 Faol buyurtmalar")]
        ]
    elif role == 'diller':
        buttons = [
            [types.KeyboardButton(text="🛍 Sotuvdagi mebellar"), types.KeyboardButton(text="📝 Zakaz berish")],
            [types.KeyboardButton(text="📋 Buyurtmalar tarixi"), types.KeyboardButton(text="❌ Zakazni bekor qilish")],
            [types.KeyboardButton(text="📊 Buyurtmalar holati"), types.KeyboardButton(text="📥 Kirim-Chiqim")],
            [types.KeyboardButton(text="📸 Rasmlar va narxlar")]
        ]
    else:
        buttons = [
            [types.KeyboardButton(text="🛍 Sotuvdagi mebellar")]
        ]
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- BOSH MENYU / BEKOR QILISH ---
MAIN_MENU_BUTTONS = {
    "Bosh menyu", "➕ Yangi mebel", "📦 Mavjud mebellar", 
    "📝 Yangi buyurtma", "📋 Buyurtmalar nazorati", "📊 Hisob kitoblar", "🚚 Haydovchilar hisoboti", "🕰 Yetkazish tarixi", "📈 Sotuv statistikasi",
    "🔄 Omborni yangilash", "🚚 Yetkazishlar nazorati", "📊 Dostavka hisoboti", "🔨 Faol buyurtmalar", "🛍 Sotuvdagi mebellar",
    "📦 Ombor sonini yangilash", "📝 Zakaz berish",
    "📋 Buyurtmalar tarixi", "❌ Zakazni bekor qilish", "📸 Rasmlar va narxlar",
    "📊 Buyurtmalar holati", "📥 Kirim-Chiqim",
    "💳 Barchasini hisob kitob qilish", "✅ Ha, barchasini hisob kitob qilish", "❌ Yo'q, bekor qilish",
    "💰 Dillerlar qarzi"
}

class MainMenuMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: types.Message, data: dict):
        if getattr(event, "text", None) in MAIN_MENU_BUTTONS:
            state: FSMContext = data.get("state")
            if state:
                await state.clear()
        return await handler(event, data)

dp.message.outer_middleware(MainMenuMiddleware())

@dp.message(F.text == "Bosh menyu")
async def cancel_handler(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    await state.clear()
    await message.answer("Asosiy menyuga qaytdingiz.", reply_markup=main_menu(role))

# --- START KOMANDASI ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    role = await get_user_role(message.from_user.id)
    await message.answer(f"Assalomu alaykum! Rolingiz: **{role.upper()}**", 
                         reply_markup=main_menu(role), parse_mode="Markdown")

# --- TEST REMINDER ---
@dp.message(Command("test_reminder"))
async def cmd_test_reminder(message: types.Message):
    if await get_user_role(message.from_user.id) == 'admin':
        await message.answer("Siz so'ragan eslatma hozir barcha xodimlarga yuboriladi...")
        await send_daily_reminders()
    else:
        await message.answer("Sizda bu komandani ishlatishga ruxsat yo'q.")

# --- ADMIN: MEBEL QO'SHISH ---
@dp.message(F.text == "➕ Yangi mebel")
async def add_product_start(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role in ['admin', 'omborchi']:
        await message.answer("Qaysi mebelni qo'shmoqchisiz? Shablondan tanlang yoki yozing:", reply_markup=get_models_keyboard())
        await state.set_state(ProductState.name)
    else:
        await message.answer("⛔ Sizda bu funksiyaga ruxsat yo'q.", reply_markup=main_menu(role))

@dp.message(ProductState.name)
async def add_name(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return
    await state.update_data(name=message.text)
    await message.answer("Modelini kiriting (masalan: Spalniy):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(ProductState.model)

@dp.message(ProductState.model)
async def add_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("Narxini kiriting ($da, masalan: 340):")
    await state.set_state(ProductState.price)

@dp.message(ProductState.price)
async def add_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Omborda nechta bor?")
    await state.set_state(ProductState.quantity)

@dp.message(ProductState.quantity)
async def add_quantity(message: types.Message, state: FSMContext):
    try:
        qty = int(message.text)
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting (masalan: 10):")
        return
    await state.update_data(quantity=qty)
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="⏩ Rasmsiz saqlash")],
            [types.KeyboardButton(text="Bosh menyu")]
        ],
        resize_keyboard=True
    )
    await message.answer("📷 Mahsulot rasmini yuboring (URL ko'rinishida) yoki rasmsiz saqlang:", reply_markup=markup)
    await state.set_state(ProductState.image)

@dp.message(ProductState.image)
async def add_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    p_id = data['name'].replace(" ", "").replace("-", "").upper()
    
    # Rasm URL yoki bo'sh
    rasm_url = ""
    if message.text and message.text != "⏩ Rasmsiz saqlash":
        rasm_url = message.text
    
    # RTDB ga yozish
    await asyncio.to_thread(
        db.reference(f'mebellar/{p_id}').set,
        {
            'id': p_id,
            'nomi': data['name'],
            'modeli': data['model'],
            'narxi': data['price'],
            'soni': int(data['quantity']),
            'rasm': rasm_url
        }
    )
    
    role = await get_user_role(message.from_user.id)
    result_text = f"✅ Mebel qo'shildi!\n🆔 ID: `{p_id}`\n🪑 Nomi: {data['name']}\n📦 Modeli: {data['model']}\n💰 Narxi: {data['price']}$\n📦 Soni: {data['quantity']} ta"
    
    if rasm_url:
        try:
            await message.answer_photo(photo=rasm_url, caption=result_text, parse_mode="Markdown")
        except Exception:
            await message.answer(result_text, parse_mode="Markdown", reply_markup=main_menu(role))
    else:
        await message.answer(result_text, parse_mode="Markdown", reply_markup=main_menu(role))
    
    await state.clear()

# --- BARCHA UCHUN: OMBORNI KO'RISH ---
@dp.message(F.text.in_({"📦 Mavjud mebellar", "🛍 Sotuvdagi mebellar"}))
async def view_stock(message: types.Message):
    role = await get_user_role(message.from_user.id)
    mebellar = await asyncio.to_thread(db.reference('mebellar').get)
    if not mebellar:
        await message.answer("Ombor hozircha bo'sh.")
        return

    for m_id, m in mebellar.items():
        if isinstance(m, dict) and m.get('soni', 0) > 0:
            text = f"🪑 **{m.get('nomi', 'Noma\'lum')}** ({m.get('modeli', '')})\n"
            if role == 'admin':
                text += f"💰 Narxi: {m.get('narxi', '0')}\n"
            text += f"📦 Qoldiq: {m.get('soni', 0)} ta\n"
            text += f"🆔 ID: `{m_id}`"
            
            rasm = m.get('rasm', '')
            if rasm:
                try:
                    await message.answer_photo(photo=rasm, caption=text, parse_mode="Markdown")
                except:
                    await message.answer(text + f"\n📷 Rasmi: {rasm}", parse_mode="Markdown")
            else:
                await message.answer(text, parse_mode="Markdown")

# --- DILLER: RASMLAR VA NARXLAR ---
@dp.message(F.text == "📸 Rasmlar va narxlar")
async def diller_photos_prices(message: types.Message):
    role = await get_user_role(message.from_user.id)
    if role not in ['diller', 'xodim', 'ishchi']:
        await message.answer("Bu funksiya faqat dillerlar uchun.", reply_markup=main_menu(role))
        return
    await message.answer(
        "📸 *Rasmlar va narxlar* bilan tanishish uchun quyidagi Telegram kanalga o'ting:\n\n"
        "👉 [Rasmlar va narxlar kanaliga o'tish](https://t.me/+6yKALewduspiZDBi)",
        parse_mode="Markdown"
    )

# --- DILLER: ZAKAZ BERISH ---
@dp.message(F.text == "📝 Zakaz berish")
async def diller_order_start(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role not in ['diller', 'xodim', 'ishchi']:
        await message.answer("Bu funksiya faqat dillerlar uchun.", reply_markup=main_menu(role))
        return

    # Firebase'dan hozirgi stock ma'lumotlarini olish (ixtiyoriy)
    mebellar = await asyncio.to_thread(db.reference('mebellar').get)
    stock_map = {}  # m_id -> soni
    if mebellar:
        for m_id, m in mebellar.items():
            if isinstance(m, dict):
                stock_map[m_id] = int(m.get('soni', 0))

    # FAVORITE_MODELS ro'yxatidan tugmalar yasash
    buttons = []
    row = []
    items_map = {}  # button_text -> model_name

    for model in FAVORITE_MODELS:
        # Firebase ID ni hisoblash (xuddi order yaratishdagi kabi)
        m_id = model.replace(" ", "").replace("-", "").upper()
        soni = stock_map.get(m_id, 0)
        if soni > 0:
            btn_text = f"{model} ✅ {soni} ta"
        else:
            btn_text = model
        row.append(types.KeyboardButton(text=btn_text))
        items_map[btn_text] = model
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([types.KeyboardButton(text="Bosh menyu")])

    await state.update_data(items_map=items_map, stock_map=stock_map)
    await state.set_state(DillerOrderState.select_product)
    await message.answer(
        "📦 Qaysi mebelni olmoqchisiz?\n"
        "✅ — omborda mavjud | narxi yo'q — oldindan zakaz:",
        reply_markup=types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    )


@dp.message(DillerOrderState.select_product)
async def diller_select_product(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await state.clear()
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        return

    data = await state.get_data()
    items_map = data.get('items_map', {})

    if message.text not in items_map:
        await message.answer("Iltimos, ro'yxatdan tanlang:")
        return

    # items_map: btn_text -> model_name (e.g. "BF 07")
    model_name = items_map[message.text]
    product_id = model_name.replace(" ", "").replace("-", "").upper()

    # Firebase'dan narx va stock olishga urinish
    product_ref = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)
    soni = int(product_ref.get('soni', 0)) if product_ref else 0

    stock_info = f"📦 Omborda: *{soni} ta* mavjud.\n" if soni > 0 else "⚠️ Hozir omborda yo'q — oldindan zakaz qabul qilinadi.\n"

    await state.update_data(
        product_id=product_id,
        product_name=model_name,
        stock_soni=soni
    )
    await message.answer(
        f"✅ *{model_name}* tanlandi.\n"
        f"{stock_info}\n"
        "Nechta olmoqchisiz? (faqat raqam kiriting):",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    await state.set_state(DillerOrderState.amount)

@dp.message(DillerOrderState.amount)
async def diller_order_amount(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await state.clear()
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        return

    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Iltimos, musbat raqam kiriting (masalan: 2):")
        return

    await state.update_data(amount=amount)
    
    data = await state.get_data()
    stock_soni = data.get('stock_soni', 0)
    
    start_day = 0
    if amount > stock_soni:
        start_day = 2
        
    await message.answer(
        "📅 Qaysi sanaga tayyor bo'lishi kerak? Tugmadan tanlang yoki yozing (masalan: 20.05.2026):",
        reply_markup=get_dates_keyboard(start_day)
    )
    await state.set_state(DillerOrderState.due_date)


@dp.message(DillerOrderState.due_date)
async def diller_order_due_date(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await state.clear()
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        return

    due_date = message.text
    data = await state.get_data()
    product_id   = data['product_id']
    product_name = data.get('product_name', product_id)
    amount       = data['amount']

    user = message.from_user
    client_name = DILLER_ID_TO_CLIENT.get(user.id) or user.full_name or user.username or str(user.id)

    order_id = f"{product_id}-{str(uuid.uuid4())[:4].upper()}"
    now_str  = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
    month    = datetime.now(TASHKENT_TZ).strftime("%Y-%m")

    # Mebel ma'lumotlari
    mebel_ref = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)

    # Ombordan ayirish (faqat mavjud miqdor qadar)
    deducted_qty = 0
    if mebel_ref:
        current_qty = int(mebel_ref.get('soni', 0))
        deducted_qty = min(current_qty, amount)  # Haqiqatda ayirilgan miqdor
        new_qty = current_qty - deducted_qty
        if deducted_qty > 0:
            await asyncio.to_thread(db.reference(f'mebellar/{product_id}').update, {'soni': new_qty})

    # Narx hisoblash
    price_val = 0
    if mebel_ref and 'narxi' in mebel_ref:
        price_str = str(mebel_ref['narxi']).replace("so'm", "").replace("$", "").replace(" ", "")
        try:
            price_val = int(price_str)
        except:
            price_val = 0
    total_price = price_val * int(amount)

    # Mebel to'liq ma'lumotlari (omborchiga)
    mebel_nomi   = mebel_ref.get('nomi', product_name) if mebel_ref else product_name
    mebel_modeli = mebel_ref.get('modeli', product_id) if mebel_ref else product_id
    mebel_narxi  = mebel_ref.get('narxi', f'{price_val}$') if mebel_ref else f'{price_val}$'

    # Firebase'ga yozish
    await asyncio.to_thread(
        db.reference(f'orders/{order_id}').set,
        {
            'order_id':     order_id,
            'client_name':  client_name,
            'client_tg_id': str(user.id),
            'product_id':   product_id,
            'amount':       str(amount),
            'due_date':     due_date,
            'comment':      '',
            'status':       'Tayyorlanmoqda',
            'created_at':   now_str,
            'month':        month,
            'source':       'diller',
            'price':        price_val,
            'total_price':  total_price,
            'deducted_qty': deducted_qty  # Ombordan haqiqatda ayirilgan miqdor
        }
    )

    role = await get_user_role(message.from_user.id)
    price_info = f"\n💰 Narxi: {price_val}$ × {amount} = {total_price}$" if price_val > 0 else ""
    await message.answer(
        f"✅ Zakaz qabul qilindi!\n"
        f"🆔 ID: `{order_id}`\n"
        f"📦 Mebel: {product_name} — {amount} ta\n"
        f"📅 Muddat: {format_date(due_date)}"
        f"{price_info}",
        parse_mode="Markdown",
        reply_markup=main_menu(role)
    )
    await state.clear()

    # Admin va omborchiga to'liq komplekt xabari
    price_line = f"💰 Narxi: {mebel_narxi} × {amount} = {total_price}$\n" if price_val > 0 else ""
    notify_text = (
        f"🔔 *Yangi zakaz (dillerdan)!*\n\n"
        f"👤 Diller: {client_name}\n"
        f"📦 Mebel: {mebel_nomi}\n"
        f"📐 Modeli: {mebel_modeli}\n"
        f"🔢 Soni: {amount} ta\n"
        f"{price_line}"
        f"📅 Muddat: {format_date(due_date)}\n"
        f"🆔 Zakaz ID: `{order_id}`"
    )
    users_ref = await asyncio.to_thread(db.reference('users').get)
    for uid, udata in (users_ref or {}).items():
        if isinstance(udata, dict) and udata.get('role') in ['admin', 'omborchi', 'ishchi']:
            try:
                await bot.send_message(int(uid), notify_text, parse_mode="Markdown")
            except Exception:
                pass
    try:
        await bot.send_message(883589794, notify_text, parse_mode="Markdown")
    except Exception:
        pass


# --- DILLER: BUYURTMALAR TARIXI ---
@dp.message(F.text == "📋 Buyurtmalar tarixi")
async def diller_order_history(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role not in ['diller', 'xodim', 'ishchi']:
        return

    user_id = str(message.from_user.id)
    orders_ref = await asyncio.to_thread(db.reference('orders').get)

    if not orders_ref:
        await message.answer("Hozircha buyurtma yo'q.", reply_markup=main_menu(role))
        return

    active    = []
    completed = []

    for o_id, o in orders_ref.items():
        if not isinstance(o, dict):
            continue
        if o.get('client_tg_id') != user_id:
            continue
        status = o.get('status', '')
        if status == 'Bekor qilindi':
            continue
        if status in ['Tayyorlanmoqda', "Tayyor bo'ldi", 'Yuborildi']:
            active.append((o_id, o))
        elif status in ["Dillerni o'zi olib ketdi", "Biz yetkazib berdik"]:
            completed.append((o_id, o))

    def get_order_date(item):
        try:
            return datetime.strptime(item[1].get('created_at', ''), "%Y-%m-%d %H:%M:%S")
        except:
            return datetime.min

    active.sort(key=get_order_date, reverse=True)
    completed.sort(key=get_order_date, reverse=True)

    text = f"📋 *Sizning buyurtmalaringiz:*\n\n"

    if active:
        text += f"⏳ *Tayyorlanayotgan — {len(active)} ta:*\n"
        for o_id, o in active:
            st = o.get('status', '')
            icon = "✅" if st == "Tayyor bo'ldi" else "🔧"
            text += (
                f"  {icon} {o.get('product_id')} — {o.get('amount')} ta\n"
                f"     📅 Muddat: {format_date(o.get('due_date',''))} | {st}\n"
            )
        text += "\n"
    
    if completed:
        text += f"✅ *Olib ketilgan — {len(completed)} ta:*\n"
        for o_id, o in completed[:20]:
            delivered = format_date(o.get('delivered_at', o.get('due_date', '')))
            text += (
                f"  📦 {o.get('product_id')} — {o.get('amount')} ta\n"
                f"     📅 Sana: {delivered} | {o.get('status')}\n"
            )

    if not active and not completed:
        text += "Hozircha buyurtma yo'q."

    # Xabar uzun bo'lsa bo'laklash
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            try:
                await message.answer(text[i:i+4000], parse_mode="Markdown")
            except Exception:
                await message.answer(text[i:i+4000])
    else:
        try:
            await message.answer(text, parse_mode="Markdown", reply_markup=main_menu(role))
        except Exception:
            await message.answer(text, reply_markup=main_menu(role))


# --- DILLER: ZAKAZNI BEKOR QILISH ---
@dp.message(F.text == "❌ Zakazni bekor qilish")
async def diller_cancel_start(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role not in ['diller', 'xodim', 'ishchi']:
        return

    user_id = str(message.from_user.id)
    orders_ref = await asyncio.to_thread(db.reference('orders').get)

    if not orders_ref:
        await message.answer("Sizda faol buyurtma yo'q.", reply_markup=main_menu(role))
        return

    cancellable = []
    for o_id, o in orders_ref.items():
        if not isinstance(o, dict):
            continue
        if o.get('client_tg_id') != user_id:
            continue
        if o.get('status') != 'Tayyorlanmoqda':
            continue
        # Faqat diller o'zi yaratgan zakazlarni bekor qila oladi
        if o.get('source', 'diller') != 'diller':
            continue
        cancellable.append((o_id, o))

    if not cancellable:
        await message.answer(
            "❌ Bekor qilish mumkin bo'lgan zakaz yo'q.\n"
            "_(Faqat siz tomonidan berilgan va 'Tayyorlanmoqda' statusidagi zakazlarni bekor qilish mumkin.\n"
            "Admin tomonidan shakllangan zakazlarni bekor qilib bo'lmaydi.)_",
            parse_mode="Markdown",
            reply_markup=main_menu(role)
        )
        return

    order_info = {}
    buttons = []
    for o_id, o in cancellable:
        btn_text = f"🚫 {o.get('product_id')} — {o.get('amount')} ta | {format_date(o.get('due_date',''))}"
        buttons.append([types.KeyboardButton(text=btn_text)])
        order_info[btn_text] = o_id
    buttons.append([types.KeyboardButton(text="Bosh menyu")])

    await state.update_data(order_info=order_info)
    await state.set_state(DillerCancelState.select_order)
    markup = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("Qaysi zakazni bekor qilmoqchisiz?", reply_markup=markup)


@dp.message(DillerCancelState.select_order)
async def diller_cancel_select(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await state.clear()
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        return

    data = await state.get_data()
    order_info = data.get('order_info', {})

    if message.text not in order_info:
        await message.answer("Iltimos, tugmadan tanlang:")
        return

    order_id  = order_info[message.text]
    order_ref = await asyncio.to_thread(db.reference(f'orders/{order_id}').get)
    if not order_ref:
        await message.answer("Buyurtma topilmadi.")
        await state.clear()
        return

    await state.update_data(cancel_order_id=order_id)
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="✅ Ha, bekor qil")],
            [types.KeyboardButton(text="🔙 Yo'q, qaytish")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        f"⚠️ *{order_ref.get('product_id')}* — {order_ref.get('amount')} ta zakazni bekor qilmoqchimisiz?\n"
        f"📅 Muddat: {format_date(order_ref.get('due_date',''))}",
        parse_mode="Markdown",
        reply_markup=markup
    )
    await state.set_state(DillerCancelState.confirm)


@dp.message(DillerCancelState.confirm)
async def diller_cancel_confirm(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)

    if message.text == "🔙 Yo'q, qaytish":
        await state.clear()
        await message.answer("Bekor qilish to'xtatildi.", reply_markup=main_menu(role))
        return

    if message.text != "✅ Ha, bekor qil":
        await message.answer("Iltimos, tugmadan tanlang:")
        return

    data     = await state.get_data()
    order_id = data.get('cancel_order_id')

    order_ref = await asyncio.to_thread(db.reference(f'orders/{order_id}').get)
    if not order_ref:
        await message.answer("Buyurtma topilmadi.", reply_markup=main_menu(role))
        await state.clear()
        return

    # Statusni yangilash
    await asyncio.to_thread(
        db.reference(f'orders/{order_id}').update,
        {'status': 'Bekor qilindi'}
    )

    # Ombor sonini qaytarish (faqat haqiqatda ayirilgan miqdorni qaytarish)
    product_id = order_ref.get('product_id', '')
    try:
        amount = int(order_ref.get('amount', 1))
    except:
        amount = 1
    # deducted_qty — zakaz vaqtida ombordan haqiqatda ayirilgan miqdor
    try:
        deducted_qty = int(order_ref.get('deducted_qty', -1))
    except:
        deducted_qty = -1
    # Eski zakazlarda deducted_qty yo'q bo'lishi mumkin — xavfsiz fallback
    qty_to_return = deducted_qty if deducted_qty >= 0 else amount
    if product_id and qty_to_return > 0:
        mebel_ref = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)
        if mebel_ref:
            current_qty = int(mebel_ref.get('soni', 0))
            await asyncio.to_thread(
                db.reference(f'mebellar/{product_id}').update,
                {'soni': current_qty + qty_to_return}
            )

    await message.answer(
        f"✅ Zakaz bekor qilindi!\n"
        f"📦 {product_id} — {amount} ta omborda qaytarildi.",
        reply_markup=main_menu(role)
    )
    await state.clear()

    # Admin va omborchiga xabar
    user        = message.from_user
    client_name = user.full_name or user.username or str(user.id)
    notify_text = (
        f"🚫 *Zakaz bekor qilindi (diller tomonidan)!*\n\n"
        f"👤 Diller: {client_name}\n"
        f"📦 Mebel: {product_id} — {amount} ta\n"
        f"🆔 Zakaz ID: `{order_id}`"
    )
    users_ref = await asyncio.to_thread(db.reference('users').get)
    for uid, udata in (users_ref or {}).items():
        if isinstance(udata, dict) and udata.get('role') in ['admin', 'omborchi']:
            try:
                await bot.send_message(int(uid), notify_text, parse_mode="Markdown")
            except Exception:
                pass
    try:
        await bot.send_message(883589794, notify_text, parse_mode="Markdown")
    except Exception:
        pass


# --- DILLER: BUYURTMALAR HOLATI (faqat ko'rish) ---
@dp.message(F.text == "📊 Buyurtmalar holati")
async def diller_order_status(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role not in ['diller', 'xodim', 'ishchi']:
        return

    user_tg_id = str(message.from_user.id)
    # Diller client nomini topish (DILLER_ID_TO_CLIENT xaritasidan)
    client_name_for_diller = DILLER_ID_TO_CLIENT.get(message.from_user.id, '')

    orders_ref = await asyncio.to_thread(db.reference('orders').get)
    if not orders_ref:
        await message.answer("Hozircha buyurtma yo'q.", reply_markup=main_menu(role))
        return

    pending   = []  # Tayyorlanmoqda / Tayyor bo'ldi
    delivered = []  # Yetkazilgan / Olib ketilgan
    cancelled = []  # Bekor qilingan

    STATUS_ICONS = {
        'Tayyorlanmoqda': '🔧',
        "Tayyor bo'ldi":  '✅',
        'Yuborildi':       '🚚',
        "Biz yetkazib berdik":       '📦',
        "Dillerni o'zi olib ketdi":  '🏠',
        'Bekor qilindi':             '❌',
    }

    for o_id, o in orders_ref.items():
        if not isinstance(o, dict):
            continue
        o_tg = o.get('client_tg_id', '')
        o_client = str(o.get('client_name') or o.get('client') or '').strip().lower()
        # O'zi bergan yoki admin uning nomidan bergan zakazlar
        is_own   = (o_tg == user_tg_id)
        is_admin = (client_name_for_diller and
                    o_client == client_name_for_diller.strip().lower())
        if not (is_own or is_admin):
            continue

        status = o.get('status', '')
        source = '👤' if is_own else '🏷'  # 👤 = o'zi, 🏷 = admin yaratgan
        entry = {
            'o_id': o_id,
            'product_id': o.get('product_id', '?'),
            'amount': o.get('amount', '1'),
            'due_date': format_date(o.get('due_date', '')),
            'status': status,
            'price': o.get('price', 0),
            'total_price': o.get('total_price', 0),
            'driver': o.get('driver', ''),
            'delivery_price': o.get('delivery_price', ''),
            'delivered_at': format_date(o.get('delivered_at', '')),
            'source': source,
            'created_at': o.get('created_at', ''),
        }
        if status in ['Tayyorlanmoqda', "Tayyor bo'ldi", 'Yuborildi']:
            pending.append(entry)
        elif status in ["Biz yetkazib berdik", "Dillerni o'zi olib ketdi", "Mijozni o'zi olib ketdi"]:
            delivered.append(entry)
        elif status == 'Bekor qilindi':
            cancelled.append(entry)

    # Saralash — yangirog'i birinchi
    def sort_by_date(e):
        try:
            return datetime.strptime(e['created_at'], "%Y-%m-%d %H:%M:%S")
        except:
            return datetime.min

    pending.sort(key=sort_by_date, reverse=True)
    delivered.sort(key=sort_by_date, reverse=True)

    text = "📊 *Sizning barcha buyurtmalaringiz:*\n"
    text += "_(👤 = siz bergansiz | 🏷 = admin yaratgan)_\n\n"

    if pending:
        text += f"⏳ *Tayyorlanmoqda — {len(pending)} ta:*\n"
        for e in pending:
            icon = STATUS_ICONS.get(e['status'], '🔧')
            try:
                price_val = int(e['price'])
                amount_val = int(e['amount'])
                total = price_val * amount_val
                price_str = f"💰 {total:,}$".replace(',', ' ')
            except:
                price_str = ""
            text += (
                f"  {e['source']} {icon} *{e['product_id']}* — {e['amount']} ta\n"
                f"     📅 Muddat: {e['due_date']} | _{e['status']}_\n"
            )
            if price_str:
                text += f"     {price_str}\n"
        text += "\n"

    if delivered:
        text += f"✅ *Yetkazilgan — {len(delivered)} ta:*\n"
        for e in delivered[:30]:
            try:
                price_val = int(e['price'])
                amount_val = int(e['amount'])
                total = price_val * amount_val
                price_str = f"{total:,}$".replace(',', ' ')
            except:
                price_str = "—"
            driver_info = ""
            if e['driver']:
                driver_info = f" | 🚚 {e['driver']}"
                if e['delivery_price']:
                    driver_info += f" ({e['delivery_price']})"
            text += (
                f"  {e['source']} 📦 *{e['product_id']}* — {e['amount']} ta | 💵 {price_str}\n"
                f"     📅 {e['delivered_at']}{driver_info}\n"
            )
        if len(delivered) > 30:
            text += f"  _...va yana {len(delivered) - 30} ta_\n"
        text += "\n"

    if cancelled:
        text += f"❌ *Bekor qilingan — {len(cancelled)} ta:*\n"
        for e in cancelled[:10]:
            text += f"  ✖️ {e['product_id']} — {e['amount']} ta\n"

    if not pending and not delivered and not cancelled:
        text += "Hozircha buyurtma yo'q."

    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            try:
                await message.answer(text[i:i+4000], parse_mode="Markdown")
            except:
                await message.answer(text[i:i+4000])
    else:
        try:
            await message.answer(text, parse_mode="Markdown", reply_markup=main_menu(role))
        except:
            await message.answer(text, reply_markup=main_menu(role))


# --- DILLER: KIRIM-CHIQIM ---
@dp.message(F.text == "📥 Kirim-Chiqim")
async def diller_payment_start(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role not in ['diller', 'xodim', 'ishchi']:
        return
    await message.answer(
        "💵 *To'lov summasini kiriting*\n\n"
        "Masalan: `450` yoki `450$`\n"
        "_(Bu xabar adminga yuboriladi va u tasdiqlashidan keyin qarzingizdan ayiriladi)_",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="Bosh menyu")]],
            resize_keyboard=True
        )
    )
    await state.set_state(DillerPaymentState.amount)


@dp.message(DillerPaymentState.amount)
async def diller_payment_amount(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if message.text == "Bosh menyu":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu(role))
        return

    import re as _re_pay
    nums = _re_pay.findall(r'\d+(?:\.\d+)?', message.text.replace(',', '.'))
    if not nums:
        await message.answer("❌ Iltimos, raqam kiriting (masalan: 450):")
        return

    amount_val = float(nums[0])
    diller_name = message.from_user.full_name or message.from_user.username or str(message.from_user.id)
    client_name = DILLER_ID_TO_CLIENT.get(message.from_user.id, diller_name)
    diller_tg_id = message.from_user.id
    timestamp = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")

    # Firebase ga pending_payment saqlash
    pay_id = str(uuid.uuid4())[:8].upper()
    payment_record = {
        'pay_id': pay_id,
        'diller_tg_id': diller_tg_id,
        'diller_name': diller_name,
        'client_name': client_name,
        'amount': amount_val,
        'timestamp': timestamp,
        'status': 'pending'
    }
    await asyncio.to_thread(db.reference(f'pending_payments/{pay_id}').set, payment_record)

    # Adminga inline xabar yuborish
    inline_kb = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_confirm:{pay_id}"),
        types.InlineKeyboardButton(text="❌ Rad etish",  callback_data=f"pay_reject:{pay_id}")
    ]])
    admin_text = (
        f"💵 *Diller to'lov bildirdi!*\n\n"
        f"🧑 Diller: *{diller_name}* ({client_name})\n"
        f"💰 Summa: *{amount_val:g}$*\n"
        f"📅 Vaqt: {timestamp}\n\n"
        f"Tasdiqlaysizmi?"
    )
    users_ref = await asyncio.to_thread(db.reference('users').get)
    for uid, udata in (users_ref or {}).items():
        if isinstance(udata, dict) and udata.get('role') == 'admin':
            try:
                await bot.send_message(int(uid), admin_text, reply_markup=inline_kb, parse_mode="Markdown")
            except Exception as e:
                print(f"Adminga to'lov xabari yuborishda xatolik: {e}")

    await state.clear()
    await message.answer(
        f"✅ To'lov bildirganingiz adminga yuborildi!\n💵 Summa: *{amount_val:g}$*\n\nAdmin tasdiqlagach qarzingizdan ayiriladi.",
        parse_mode="Markdown",
        reply_markup=main_menu(role)
    )


# --- ADMIN: KIRIM-CHIQIM TASDIQLASH CALLBACKLAR ---
@dp.callback_query(F.data.startswith("pay_confirm:"))
async def admin_confirm_payment(callback: types.CallbackQuery):
    if await get_user_role(callback.from_user.id) != 'admin':
        await callback.answer("Sizda bu huquq yo'q.", show_alert=True)
        return
    pay_id = callback.data.split(":", 1)[1]
    pay_ref = await asyncio.to_thread(db.reference(f'pending_payments/{pay_id}').get)
    if not pay_ref or not isinstance(pay_ref, dict):
        await callback.answer("To'lov ma'lumoti topilmadi.", show_alert=True)
        return
    if pay_ref.get('status') == 'confirmed':
        await callback.answer("Bu to'lov allaqachon tasdiqlangan.", show_alert=True)
        return

    client_name = pay_ref.get('client_name', '')
    amount_val  = float(pay_ref.get('amount', 0))
    diller_tg_id = int(pay_ref.get('diller_tg_id', 0))
    diller_name  = pay_ref.get('diller_name', '')
    timestamp    = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")

    # Qarzdan ayirish
    debt_ref = await asyncio.to_thread(db.reference(f'debts/{client_name}').get)
    current_debt = int(float(debt_ref)) if debt_ref else 0
    new_debt = max(0, current_debt - int(amount_val))
    await asyncio.to_thread(db.reference(f'debts/{client_name}').set, new_debt)

    # accounting_history ga yozish
    history_record = {
        'client_name': client_name,
        'accounting_type': 'qisman',
        'partial_payment': int(amount_val),
        'accounting_date': timestamp,
        'status': "To'lov qabul qilindi",
        'note': f"Diller to'lov bildirdi: {diller_name} — {amount_val:g}$ (ID: {pay_id})"
    }
    await asyncio.to_thread(db.reference(f'accounting_history/{client_name}').push, history_record)

    # Tranzaksiya
    record = {
        'type': 'Kirim',
        'amount': int(amount_val),
        'timestamp': timestamp,
        'note': f"Diller to'lov: {diller_name} — {amount_val:g}$ (ID: {pay_id})"
    }
    await asyncio.to_thread(db.reference(f'transactions/clients/{client_name}').push, record)

    # Pending ni tugatish
    await asyncio.to_thread(db.reference(f'pending_payments/{pay_id}').update, {'status': 'confirmed'})

    # Tugmalarni o'chirish
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    await callback.message.answer(
        f"✅ To'lov tasdiqlandi!\n🧑 {diller_name} ({client_name})\n💵 {amount_val:g}$\n💳 Yangi qarz: *{new_debt:,}$*".replace(',', ' '),
        parse_mode="Markdown"
    )

    # Dillerga xabar
    if diller_tg_id:
        try:
            await bot.send_message(
                diller_tg_id,
                f"✅ *To'lovingiz tasdiqlandi!*\n\n💵 Summa: *{amount_val:g}$*\n💳 Yangi qarz: *{new_debt:,}$*".replace(',', ' '),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Dillerga to'lov tasdiqlandi xabari: {e}")
    await callback.answer()


@dp.callback_query(F.data.startswith("pay_reject:"))
async def admin_reject_payment(callback: types.CallbackQuery):
    if await get_user_role(callback.from_user.id) != 'admin':
        await callback.answer("Sizda bu huquq yo'q.", show_alert=True)
        return
    pay_id = callback.data.split(":", 1)[1]
    pay_ref = await asyncio.to_thread(db.reference(f'pending_payments/{pay_id}').get)
    if not pay_ref or not isinstance(pay_ref, dict):
        await callback.answer("To'lov ma'lumoti topilmadi.", show_alert=True)
        return

    diller_tg_id = int(pay_ref.get('diller_tg_id', 0))
    diller_name  = pay_ref.get('diller_name', '')
    amount_val   = float(pay_ref.get('amount', 0))

    # Pending ni bekor qilish
    await asyncio.to_thread(db.reference(f'pending_payments/{pay_id}').update, {'status': 'rejected'})

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    await callback.message.answer(f"❌ To'lov rad etildi.\n🧑 {diller_name} — {amount_val:g}$")

    if diller_tg_id:
        try:
            await bot.send_message(
                diller_tg_id,
                f"❌ *To'lovingiz rad etildi.*\n\n💵 Summa: *{amount_val:g}$*\n\nIltimos, admin bilan bog'laning.",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Dillerga rad etildi xabari: {e}")
    await callback.answer()


# --- ADMIN: YANGI BUYURTMA YOZISH ---

@dp.message(F.text == "📝 Yangi buyurtma")
async def new_order_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'admin':
        await message.answer("Dillerni tanlang yoki 'Boshqa' ni bosing:", reply_markup=get_clients_keyboard())
        await state.set_state(OrderState.client)

@dp.message(OrderState.client)
async def process_client(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return

    if message.text == "Boshqa (Yangi diller)":
        await message.answer("Yangi diller ismini kiriting:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(OrderState.custom_client)
        return

    await state.update_data(client=message.text)
    await message.answer("Qanday mebel buyurtma qilinmoqda? (Quyidagilardan tanlang yoki yozing):", reply_markup=get_models_keyboard(include_other=True))
    await state.set_state(OrderState.product_id)

@dp.message(OrderState.custom_client)
async def process_custom_client(message: types.Message, state: FSMContext):
    await state.update_data(client=message.text)
    await message.answer("Qanday mebel buyurtma qilinmoqda? (Quyidagilardan tanlang yoki yozing):", reply_markup=get_models_keyboard(include_other=True))
    await state.set_state(OrderState.product_id)

@dp.message(OrderState.product_id)
async def process_product_id(message: types.Message, state: FSMContext):
    if message.text == "Boshqa (Qo'lda kiritish)":
        await message.answer("Mebelning nomini kiriting:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(OrderState.custom_product_id)
        return

    formatted_id = message.text.replace(" ", "").replace("-", "").upper()
    await state.update_data(product_id=formatted_id)
    
    # Fetch price to show to admin
    role = await get_user_role(message.from_user.id)
    price_text = ""
    if role == 'admin':
        product_ref = await asyncio.to_thread(db.reference(f'mebellar/{formatted_id}').get)
        if product_ref and 'narxi' in product_ref:
            price_text = f"\n(Mebel narxi: {product_ref['narxi']})"
            
    await message.answer(f"Nechta buyurtma berdi?{price_text}", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrderState.amount)

@dp.message(OrderState.custom_product_id)
async def process_custom_product_id(message: types.Message, state: FSMContext):
    formatted_id = message.text.upper()
    await state.update_data(product_id=formatted_id)
    await message.answer("Ushbu mebelning donasi uchun narxini kiriting (faqat raqam, masalan, 300000 yoki 300):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrderState.custom_price)

@dp.message(OrderState.custom_price)
async def process_custom_price(message: types.Message, state: FSMContext):
    await state.update_data(custom_price=message.text)
    await message.answer("Nechta buyurtma berdi?", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrderState.amount)

# Soni kiritilgandan keyin sanani so'rash
@dp.message(OrderState.amount)
async def process_amount(message: types.Message, state: FSMContext):
    await state.update_data(amount=message.text)
    await message.answer("📅 Buyurtma qaysi sanaga tayyor bo'lishi kerak? Tugmalardan tanlang yoki yozing:", reply_markup=get_dates_keyboard())
    await state.set_state(OrderState.due_date)

# Oxirgi bosqich: Sanani qabul qilish va izoh so'rash
@dp.message(OrderState.due_date)
async def process_due_date(message: types.Message, state: FSMContext):
    await state.update_data(due_date=message.text)
    await message.answer("📝 Buyurtma uchun izoh kiriting (mebelning biror joyini o'zgartirish kerak bo'lsa):\n(Agar izoh bo'lmasa 'yoq' deb yozing)", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrderState.comment)

# Izohni qabul qilish va bazaga saqlash
@dp.message(OrderState.comment)
async def process_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    comment = message.text
    product_id = data['product_id']
    order_id = f"{product_id}-{str(uuid.uuid4())[:4].upper()}"
    try:
        amount = int(data['amount'])
    except ValueError:
        amount = 1

    client_name = data['client']
    price_val = 0
    if 'custom_price' in data:
        price_str = data['custom_price'].replace("so'm", "").replace("$", "").replace(" ", "")
        try:
            price_val = int(price_str)
        except:
            price_val = 0
    else:
        mebel_ref = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)
        if mebel_ref and 'narxi' in mebel_ref:
            price_str = str(mebel_ref['narxi']).replace("so'm", "").replace("$", "").replace(" ", "")
            try:
                price_val = int(price_str)
            except:
                price_val = 0

    total_price = price_val * amount
    
    # Ombor qoldig'ini kamaytirish
    mebel_ref = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)
    if mebel_ref and 'soni' in mebel_ref:
        current_qty = int(mebel_ref['soni'])
        new_qty = current_qty - amount
        await asyncio.to_thread(db.reference(f'mebellar/{product_id}').update, {'soni': new_qty})
        
    # Realtime Database (RTDB) ga yozish
    await asyncio.to_thread(
        db.reference(f'orders/{order_id}').set,
        {
            'order_id': order_id,
            'client_name': data['client'],
            'product_id': data['product_id'],
            'amount': data['amount'],
            'due_date': data['due_date'],
            'comment': comment,
            'status': 'Tayyorlanmoqda',
            'source': 'admin',
            'created_at': datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            'month': datetime.now(TASHKENT_TZ).strftime("%Y-%m"),
            'price': price_val,
            'total_price': total_price
        }
    )
    
    await message.answer(f"✅ Buyurtma qabul qilindi!\n🆔 ID: {order_id}\n📅 Muddat: {format_date(data['due_date'])}\n📝 Izoh: {comment}")
    data['comment'] = comment
    await state.clear()
    
    # Omborchiga xabar yuborish
    await notify_warehouse(data, order_id)
    await notify_diller_new_order(data, order_id)

# --- ADMIN: MIJOZLAR HISOBOTI VA QARZ ---
class ReportState(StatesGroup):
    select_client = State()

class ClientAccountingState(StatesGroup):
    select_order = State()         # Buyurtma tanlash
    select_action = State()        # Hisob kitob qilindi / Qisman to'ladi
    partial_amount = State()       # Qisman to'lov summasi
    confirm_all_settle = State()   # Barchasini hisob kitob qilishni tasdiqlash


async def recalculate_and_save_debt(client_name: str) -> int:
    """
    Berilgan client_name uchun qarzni qayta to'g'ri hisoblaydi va Firebase debts ga saqlaydi.
    Barcha hisob kitob joylarida (individual, qisman, barchasini) chaqiriladi.
    Qaytaradi: yangi to'g'ri qarz qiymati.
    """
    EXCLUDED_STATUSES = {'Tayyorlanmoqda', "Tayyor bo'ldi", 'Bekor qilindi', 'Hisob kitob qilindi'}
    search_name = client_name.strip().lower()

    orders_ref = await asyncio.to_thread(db.reference('orders').get)
    mebellar_ref = await asyncio.to_thread(db.reference('mebellar').get)
    acc_history = await asyncio.to_thread(db.reference(f'accounting_history/{client_name}').get)

    # To'liq hisob kitob qilingan order IDlar
    accounted_ids = set()
    total_partial = 0
    if acc_history and isinstance(acc_history, dict):
        # 1-pass: to'liq to'langanlarni yig'ish
        for h_id, h in acc_history.items():
            if not isinstance(h, dict):
                continue
            if h.get('accounting_type') == 'toliq':
                oid = str(h.get('order_id', ''))
                if oid:
                    accounted_ids.add(oid)
        # 2-pass: faqat hali to'liq yopilmagan buyurtmalarning qisman to'lovlarini hisoblash
        for h_id, h in acc_history.items():
            if not isinstance(h, dict):
                continue
            if h.get('accounting_type') == 'qisman':
                oid = str(h.get('order_id', ''))
                if oid in accounted_ids:
                    continue
                try:
                    pp = h.get('partial_payment', 0)
                    total_partial += int(float(str(pp))) if pp else 0
                except Exception:
                    pass

    # Yetkazilgan, hisob kitob qilinmagan buyurtmalar narxlari
    correct_debt = 0
    if orders_ref and isinstance(orders_ref, dict):
        for o_id, o in orders_ref.items():
            if not isinstance(o, dict):
                continue
            o_client = str(o.get('client_name') or o.get('client') or '').strip().lower()
            if o_client != search_name:
                continue
            if o.get('status', '') in EXCLUDED_STATUSES:
                continue
            if str(o_id) in accounted_ids:
                continue

            # Narxni aniqlash
            try:
                raw_total = o.get('total_price', None)
                raw_price = o.get('price', None)
                raw_amount = o.get('amount', 1)
                a_int = int(float(str(raw_amount))) if raw_amount else 1

                order_price = 0
                if raw_total is not None and str(raw_total).strip() not in ('', '0', 'None'):
                    order_price = int(float(str(raw_total)))
                elif raw_price is not None and str(raw_price).strip() not in ('', '0', 'None'):
                    order_price = int(float(str(raw_price))) * a_int
                else:
                    p_id = str(o.get('product_id', '')).replace(' ', '').replace('-', '').upper()
                    if mebellar_ref and isinstance(mebellar_ref, dict) and p_id in mebellar_ref:
                        mebel = mebellar_ref[p_id]
                        if isinstance(mebel, dict) and mebel.get('narxi'):
                            price_str = str(mebel['narxi']).replace("so'm", '').replace('$', '').replace(' ', '').replace(',', '')
                            try:
                                order_price = int(float(price_str)) * a_int
                            except Exception:
                                pass

                if o.get('driver') == "O'zi olib ketdi":
                    try:
                        pd = o.get('pickup_discount', 0)
                        order_price = max(0, order_price - int(float(str(pd))) if pd else order_price)
                    except Exception:
                        pass

                correct_debt += order_price
            except Exception:
                pass

    correct_debt -= total_partial

    # Firebase ga saqlash
    try:
        await asyncio.to_thread(db.reference(f'debts/{client_name}').set, correct_debt)
    except Exception:
        pass

    return correct_debt


# --- ADMIN: DILLERLAR QARZI ---
@dp.message(F.text == "💰 Dillerlar qarzi")
async def show_all_debts(message: types.Message):
    if await get_user_role(message.from_user.id) != 'admin':
        return

    wait_msg = await message.answer("⏳ Hisob yangilanmoqda...")

    try:
        orders_ref      = await asyncio.to_thread(db.reference('orders').get)
        mebellar_ref    = await asyncio.to_thread(db.reference('mebellar').get)
        acc_history_all = await asyncio.to_thread(db.reference('accounting_history').get)
    except Exception as e:
        await wait_msg.delete()
        await message.answer(f"❌ Ma'lumot olishda xatolik: {e}", reply_markup=main_menu('admin'))
        return

    EXCLUDED_STATUSES = {'Tayyorlanmoqda', "Tayyor bo'ldi", 'Bekor qilindi', 'Hisob kitob qilindi'}
    acc_history_all = acc_history_all or {}

    indebted = []

    for client_name in REGULAR_CLIENTS:
        search_name = client_name.strip().lower()

        # Shu diller uchun accounting_history
        acc_history = acc_history_all.get(client_name, {}) or {}

        accounted_ids  = set()
        total_partial  = 0
        if isinstance(acc_history, dict):
            # 1-pass: to'liq to'langanlarni yig'ish
            for h_id, h in acc_history.items():
                if not isinstance(h, dict):
                    continue
                if h.get('accounting_type') == 'toliq':
                    oid = str(h.get('order_id', ''))
                    if oid:
                        accounted_ids.add(oid)
            # 2-pass: faqat hali to'liq yopilmagan buyurtmalarning qisman to'lovlarini hisoblash
            for h_id, h in acc_history.items():
                if not isinstance(h, dict):
                    continue
                if h.get('accounting_type') == 'qisman':
                    oid = str(h.get('order_id', ''))
                    if oid in accounted_ids:
                        continue
                    try:
                        pp = h.get('partial_payment', 0)
                        total_partial += int(float(str(pp))) if pp else 0
                    except Exception:
                        pass

        # Yetkazilgan, hali hisob kitob qilinmagan buyurtmalar
        correct_debt = 0
        if orders_ref and isinstance(orders_ref, dict):
            for o_id, o in orders_ref.items():
                if not isinstance(o, dict):
                    continue
                o_client = str(o.get('client_name') or o.get('client') or '').strip().lower()
                if o_client != search_name:
                    continue
                if o.get('status', '') in EXCLUDED_STATUSES:
                    continue
                if str(o_id) in accounted_ids:
                    continue

                try:
                    raw_total  = o.get('total_price', None)
                    raw_price  = o.get('price', None)
                    raw_amount = o.get('amount', 1)
                    a_int = int(float(str(raw_amount))) if raw_amount else 1

                    order_price = 0
                    if raw_total is not None and str(raw_total).strip() not in ('', '0', 'None'):
                        order_price = int(float(str(raw_total)))
                    elif raw_price is not None and str(raw_price).strip() not in ('', '0', 'None'):
                        order_price = int(float(str(raw_price))) * a_int
                    else:
                        p_id = str(o.get('product_id', '')).replace(' ', '').replace('-', '').upper()
                        if mebellar_ref and isinstance(mebellar_ref, dict) and p_id in mebellar_ref:
                            mebel = mebellar_ref[p_id]
                            if isinstance(mebel, dict) and mebel.get('narxi'):
                                price_str = str(mebel['narxi']).replace("so'm", '').replace('$', '').replace(' ', '').replace(',', '')
                                try:
                                    order_price = int(float(price_str)) * a_int
                                except Exception:
                                    pass

                    if o.get('driver') == "O'zi olib ketdi":
                        try:
                            pd = o.get('pickup_discount', 0)
                            order_price = max(0, order_price - int(float(str(pd))) if pd else order_price)
                        except Exception:
                            pass

                    correct_debt += order_price
                except Exception:
                    pass

        correct_debt -= total_partial

        # Firebase debts ni ham yangilash (sinxronlash uchun)
        try:
            await asyncio.to_thread(db.reference(f'debts/{client_name}').set, max(0, correct_debt))
        except Exception:
            pass

        if correct_debt > 0:
            indebted.append((client_name, correct_debt))

    await wait_msg.delete()

    if not indebted:
        await message.answer("✅ Hech bir dillerda qarz yo'q!", reply_markup=main_menu('admin'))
        return

    # Qarz miqdori bo'yicha kamayish tartibida saralash
    indebted.sort(key=lambda x: x[1], reverse=True)

    total_debt = sum(d for _, d in indebted)
    total_fmt  = f"{int(total_debt):,}".replace(",", " ")

    lines = [f"💰 *Qarzdor dillerlar ro'yxati* ({len(indebted)} ta)\n"]
    for i, (cn, debt_num) in enumerate(indebted, 1):
        debt_fmt = f"{int(debt_num):,}".replace(",", " ")
        lines.append(f"{i}. 🧑 *{cn}* — `{debt_fmt}$`")

    lines.append(f"\n📊 *Jami qarz: {total_fmt}$*")
    await message.answer("\n".join(lines), parse_mode="Markdown", reply_markup=main_menu('admin'))


@dp.message(F.text == "📊 Hisob kitoblar")
async def report_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'admin':
        await message.answer("Qaysi dillerning hisobotini ko'rmoqchisiz?", reply_markup=get_clients_keyboard())
        await state.set_state(ReportState.select_client)

@dp.message(ReportState.select_client)
async def show_client_report(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return
        
    client_name = message.text
    if client_name == "Boshqa (Yangi diller)":
        await message.answer("Faqat doimiy dillerlar hisoboti mavjud.")
        return

    try:
        # Fetch orders, deliveries and mebellar
        orders_ref = await asyncio.to_thread(db.reference('orders').get)
        mebellar_ref = await asyncio.to_thread(db.reference('mebellar').get)

        # Barcha oylar uchun yetkazishlarni olish
        all_deliveries_ref = await asyncio.to_thread(db.reference('deliveries').get)
        deliveries_map = {}  # order_id -> delivery data
        if all_deliveries_ref and isinstance(all_deliveries_ref, dict):
            for month_key, month_data in all_deliveries_ref.items():
                if isinstance(month_data, dict):
                    for d_id, d in month_data.items():
                        if isinstance(d, dict) and d.get('order_id'):
                            deliveries_map[d.get('order_id')] = d

        # ===== QARZNI TO'G'RI HISOBLASH =====
        # Yetkazilmagan yoki bekor qilingan statuslar (blacklist) — qolganlar qarzga kiradi
        EXCLUDED_STATUSES = {'Tayyorlanmoqda', "Tayyor bo'ldi", 'Bekor qilindi', 'Hisob kitob qilindi'}
        search_name_for_debt = client_name.strip().lower()

        # 1-qadam: Hisob kitob tarixidan to'liq to'langan order_id lar va qisman to'lovlarni olish
        acc_history_ref_for_debt = await asyncio.to_thread(
            db.reference(f'accounting_history/{client_name}').get
        )
        accounted_order_ids_set = set()   # to'liq hisob kitob qilingan order IDlar
        total_partial_paid = 0            # jami qisman to'lovlar summasi

        if acc_history_ref_for_debt and isinstance(acc_history_ref_for_debt, dict):
            # 1-pass: to'liq to'langanlarni yig'ish
            for h_id, h in acc_history_ref_for_debt.items():
                if not isinstance(h, dict):
                    continue
                if h.get('accounting_type') == 'toliq':
                    oid = str(h.get('order_id', ''))
                    if oid:
                        accounted_order_ids_set.add(oid)
            # 2-pass: faqat hali to'liq yopilmagan buyurtmalarning qisman to'lovlarini hisoblash
            for h_id, h in acc_history_ref_for_debt.items():
                if not isinstance(h, dict):
                    continue
                if h.get('accounting_type') == 'qisman':
                    oid = str(h.get('order_id', ''))
                    if oid in accounted_order_ids_set:
                        continue
                    try:
                        pp = h.get('partial_payment', 0)
                        total_partial_paid += int(float(str(pp))) if pp else 0
                    except Exception:
                        pass

        # 2-qadam: Yetkazilgan, lekin hali hisob kitob qilinmagan buyurtmalar narxini qo'shish
        correct_debt = 0
        if orders_ref and isinstance(orders_ref, dict):
            for o_id, o in orders_ref.items():
                if not isinstance(o, dict):
                    continue
                o_client = str(o.get('client_name') or o.get('client') or '').strip().lower()
                if o_client != search_name_for_debt:
                    continue
                o_status = o.get('status', '')
                if o_status in EXCLUDED_STATUSES:
                    continue  # Pending yoki bekor — qarzga kiritmaydi
                if str(o_id) in accounted_order_ids_set:
                    continue  # To'liq hisob kitob qilingan — qarzdan chiqarilgan
                # Narxni aniqlash
                try:
                    raw_total = o.get('total_price', None)
                    raw_price = o.get('price', None)
                    raw_amount = o.get('amount', 1)
                    a_int = int(float(str(raw_amount))) if raw_amount else 1

                    order_price = 0
                    if raw_total is not None and str(raw_total).strip() not in ('', '0', 'None'):
                        order_price = int(float(str(raw_total)))
                    elif raw_price is not None and str(raw_price).strip() not in ('', '0', 'None'):
                        order_price = int(float(str(raw_price))) * a_int
                    else:
                        # Fallback: mebellar jadvalidan narx olish (eski buyurtmalar)
                        p_id = str(o.get('product_id', '')).replace(' ', '').replace('-', '').upper()
                        if mebellar_ref and isinstance(mebellar_ref, dict) and p_id in mebellar_ref:
                            mebel = mebellar_ref[p_id]
                            if isinstance(mebel, dict) and mebel.get('narxi'):
                                price_str = str(mebel['narxi']).replace("so'm", '').replace('$', '').replace(' ', '').replace(',', '')
                                try:
                                    order_price = int(float(price_str)) * a_int
                                except Exception:
                                    pass

                    # O'zi olib ketdi bo'lsa — pickup_discount ni qarzdan ayirish
                    if o.get('driver') == "O'zi olib ketdi":
                        try:
                            pd = o.get('pickup_discount', 0)
                            order_price = max(0, order_price - int(float(str(pd))) if pd else order_price)
                        except Exception:
                            pass

                    correct_debt += order_price
                except Exception:
                    pass

        # 3-qadam: Qisman to'lovlarni ayirish
        correct_debt -= total_partial_paid

        # Firebase qiymatini to'g'rilash
        try:
            await asyncio.to_thread(db.reference(f'debts/{client_name}').set, correct_debt)
        except Exception:
            pass

        current_debt = correct_debt
        
        # Hisob kitob qilingan buyurtmalar ro'yxatini olish (tugmalardan yashirish uchun)
        accounted_order_ids = set()
        acc_history_ref = acc_history_ref_for_debt  # allaqachon yuklab olingan
        if acc_history_ref and isinstance(acc_history_ref, dict):
            for h_id, h in acc_history_ref.items():
                if isinstance(h, dict) and h.get('accounting_type') == 'toliq':
                    oid = h.get('order_id', '')
                    if oid:
                        accounted_order_ids.add(str(oid))
        
        # Buyurtmalarni ajratish: faol va yetkazilgan
        pending_orders = []  # Hali olib ketilmagan (faol)
        delivered_orders = []  # Yetkazilgan, hisob kitob qilinmagan
        
        if orders_ref:
            if isinstance(orders_ref, dict):
                items = list(orders_ref.items())
            else:
                items = [(i, o) for i, o in enumerate(orders_ref) if o is not None]
            
            search_name = client_name.strip().lower()
            for o_id, o in items:
                if isinstance(o, dict):
                    o_client_val = o.get('client_name') or o.get('client') or ''
                    o_client = str(o_client_val).strip().lower()
                    
                    if o_client == search_name:
                        status = o.get('status') or "Noma'lum"
                        product_id = o.get('product_id', '-')
                        amount = o.get('amount', '1')
                        
                        # Mebel narxini olish
                        price_text = ""
                        p_id_key = str(product_id).replace(" ", "").replace("-", "").upper()
                        if mebellar_ref and isinstance(mebellar_ref, dict) and p_id_key in mebellar_ref:
                            mebel = mebellar_ref[p_id_key]
                            if isinstance(mebel, dict) and mebel.get('narxi'):
                                price_text = str(mebel.get('narxi'))
                        
                        if status in ['Tayyorlanmoqda', "Tayyor bo'ldi"]:
                            due_date = format_date(o.get('due_date', ''))
                            pending_orders.append({
                                'o_id': o_id,
                                'product_id': product_id,
                                'amount': amount,
                                'status': status,
                                'due_date': due_date,
                                'price': price_text,
                                'comment': o.get('comment', ''),
                                'created_at': o.get('created_at', '')
                            })
                        elif status in ['Bekor qilindi', 'Hisob kitob qilindi']:
                            continue  # Bekor qilingan yoki hisob qilingan — na pending, na delivered
                        else:
                            # Yetkazilgan buyurtma
                            delivered_at = o.get('delivered_at', '')
                            driver = o.get('driver', '')
                            delivery_price = o.get('delivery_price', '')
                            
                            # Delivery ma'lumotlarini delivery_map dan olish
                            if str(o_id) in deliveries_map:
                                d_data = deliveries_map[str(o_id)]
                                if not delivered_at:
                                    delivered_at = d_data.get('timestamp', '')
                                if not driver:
                                    driver = d_data.get('driver', '')
                                if not delivery_price:
                                    delivery_price = d_data.get('price', '')
                            
                            d_date = format_date(delivered_at) if delivered_at else ''
                            
                            # Status text
                            if driver == "O'zi olib ketdi":
                                status_text = "Dillerni o'zi olib ketdi"
                            elif driver:
                                status_text = f"Yetkazildi ({driver})"
                            else:
                                status_text = status

                            # Hisob kitob qilingan bo'lsa tugmadan yashirish
                            if str(o_id) in accounted_order_ids:
                                continue
                            
                            # Narxni to'g'ri aniqlash: avval orderdagi total_price/price, keyin mebellar jadvalidan
                            order_total_price = o.get('total_price', None)
                            order_price_unit = o.get('price', None)
                            order_pickup_discount = o.get('pickup_discount', 0)
                            try:
                                raw_amt = int(float(str(amount))) if amount else 1
                            except:
                                raw_amt = 1

                            if order_total_price is not None and str(order_total_price).strip() not in ('', '0', 'None'):
                                display_price = int(float(str(order_total_price)))
                            elif order_price_unit is not None and str(order_price_unit).strip() not in ('', '0', 'None'):
                                display_price = int(float(str(order_price_unit))) * raw_amt
                            else:
                                display_price = None  # mebellar jadvalidan olinadi (price_text)

                            delivered_orders.append({
                                'o_id': o_id,
                                'product_id': product_id,
                                'amount': amount,
                                'status_text': status_text,
                                'delivered_at': d_date,
                                'price': price_text,
                                'order_total_price': display_price,
                                'pickup_discount': order_pickup_discount,
                                'driver': driver,
                                'delivery_price': delivery_price,
                                'created_at': o.get('created_at', ''),
                                'comment': o.get('comment', '')
                            })
        
        # Pending orders ni sanasi bo'yicha saralash
        def get_pending_sort_date(item):
            try:
                if item.get('due_date') and item['due_date'] != "Noma'lum":
                    return datetime.strptime(item['due_date'], "%d.%m.%Y")
                elif item.get('created_at'):
                    return datetime.strptime(str(item['created_at']).split(' ')[0], "%Y-%m-%d")
            except:
                pass
            return datetime.min
        
        pending_orders.sort(key=get_pending_sort_date, reverse=False)
        
        # Delivered orders ni sanasi bo'yicha saralash (yangirog'i birinchi)
        def get_sort_date(item):
            try:
                if item.get('delivered_at'):
                    return datetime.strptime(item['delivered_at'], "%d.%m.%Y")
                elif item.get('created_at'):
                    return datetime.strptime(str(item['created_at']).split(' ')[0], "%Y-%m-%d")
            except:
                pass
            return datetime.min
        delivered_orders.sort(key=get_sort_date, reverse=True)
        
        # ===== XABAR MATNI =====
        try:
            debt_formatted = f"{int(current_debt):,}".replace(",", " ")
        except Exception:
            debt_formatted = str(current_debt)

        header_text = f"🧑 *{client_name}* — Hisob kitob bo'limi\n"
        header_text += f"💳 Joriy qarzi: *{debt_formatted}*$\n\n"

        # 1. Tayyorlanmoqda — qisqa ro'yxat + guruhlab umumiy narx
        if pending_orders:
            header_text += f"⏳ *Tayyorlanmoqda (qarzga qo'shilmagan) — {len(pending_orders)} ta:*\n"
            # Mahsulot bo'yicha guruhlash
            from collections import defaultdict
            grouped_pending = defaultdict(lambda: {'amount': 0, 'price': '', 'status': '', 'due_date': ''})
            for po in pending_orders:
                pid_key = str(po['product_id']).replace('`', '').replace('*', '')
                grouped_pending[pid_key]['amount'] += int(po['amount']) if str(po['amount']).isdigit() else 0
                grouped_pending[pid_key]['price'] = po.get('price', '')
                grouped_pending[pid_key]['status'] = po.get('status', '')
                grouped_pending[pid_key]['due_date'] = po.get('due_date', '')
            for safe_pid, gdata in list(grouped_pending.items())[:30]:
                status_icon = "✅" if gdata['status'] == "Tayyor bo'ldi" else "🔧"
                price_str = gdata['price']
                total_price_str = ''
                if price_str:
                    try:
                        pval = float(str(price_str).replace('$', '').replace(',', '').replace(' ', ''))
                        total = pval * gdata['amount']
                        total_price_str = f" | 💰 {int(total):,}$".replace(',', ' ')
                    except:
                        total_price_str = f" | 💰 {price_str}"
                header_text += f"  {status_icon} {safe_pid} — {gdata['amount']} ta{total_price_str}\n"
            if len(grouped_pending) > 30:
                header_text += f"  _...va yana {len(grouped_pending) - 30} ta_\n"
            header_text += "\n"

        # 2. Yetkazilgan — tugmalar shaklida (max 30 ta, eng yangi birinchi)
        MAX_BUTTONS = 30
        displayed_delivered = delivered_orders[:MAX_BUTTONS]
        hidden_count = len(delivered_orders) - len(displayed_delivered)

        if delivered_orders:
            if hidden_count > 0:
                header_text += f"📦 *Olib ketilgan mebellar — hisob kitob uchun tanlang:*\n_({hidden_count} ta eskisi yashirilgan, avval yangilarini hisob kitob qiling)_"
            else:
                header_text += f"📦 *Olib ketilgan mebellar — hisob kitob uchun tanlang:*"
        else:
            header_text += "❌ Hisob kitob qilinadigan (olib ketilgan) mebel yo'q."

        # Tugmalar — faqat ko'rsatiladigan buyurtmalar uchun
        order_buttons = []
        for do in displayed_delivered:
            safe_pid = str(do['product_id']).replace('`', '').replace('*', '')
            d_date = do.get('delivered_at', '')
            btn_text = f"🚛 {safe_pid} — {do['amount']} ta | {d_date}"
            order_buttons.append([types.KeyboardButton(text=btn_text)])

        # Tarix, barchasini hisob kitob va Bosh menyu tugmalari
        if delivered_orders:
            order_buttons.append([types.KeyboardButton(text=f"💳 Barchasini hisob kitob qilish")])
        order_buttons.append([types.KeyboardButton(text=f"📜 {client_name} Hisob Tarix")])
        order_buttons.append([types.KeyboardButton(text="Bosh menyu")])

        markup = types.ReplyKeyboardMarkup(keyboard=order_buttons, resize_keyboard=True)

        # Xabar yuborish — hajm bo'yicha bo'laklash
        MAX_MSG = 3800
        if len(header_text) <= MAX_MSG:
            try:
                await message.answer(header_text, parse_mode="Markdown", reply_markup=markup)
            except Exception:
                await message.answer(header_text, reply_markup=markup)
        else:
            # Matnni bo'laklarga ajratib yuborish
            lines = header_text.split('\n')
            chunk = ""
            chunks = []
            for line in lines:
                if len(chunk) + len(line) + 1 > MAX_MSG:
                    chunks.append(chunk)
                    chunk = line + '\n'
                else:
                    chunk += line + '\n'
            if chunk:
                chunks.append(chunk)
            # Birinchi bo'laklar oddiy, oxirgisi keyboard bilan
            for i, ch in enumerate(chunks):
                try:
                    if i == len(chunks) - 1:
                        await message.answer(ch, parse_mode="Markdown", reply_markup=markup)
                    else:
                        await message.answer(ch, parse_mode="Markdown")
                except Exception:
                    if i == len(chunks) - 1:
                        await message.answer(ch, reply_markup=markup)
                    else:
                        await message.answer(ch)
        
        # 💵 Dollar stikeri yuborish
        try:
            await bot.send_sticker(
                chat_id=message.chat.id,
                sticker="CAACAgIAAxkBAAEBjGRoJ3YXSZ4AAeJE5gVF2gJfdWpB8QACWAADr8ZRGvrHuZ6K-cGINgQ"
            )
        except Exception:
            pass
        
        # Ma'lumotlarni saqlash (keyingi qadamda kerak)
        await state.update_data(
            client_name=client_name,
            pending_orders=pending_orders,
            delivered_orders=delivered_orders,
            current_debt=current_debt
        )
        await state.set_state(ClientAccountingState.select_order)
        
    except Exception as e:
        logging.error(f"Client report error: {e}")
        await message.answer(f"Hisobot tayyorlashda xatolik yuz berdi: {e}")
        await state.clear()


@dp.message(ClientAccountingState.select_order)
async def client_order_selected(message: types.Message, state: FSMContext):
    """Mijoz yetkazilgan mebelini tanlaganda, hisob kitob qilindi/qisman to'ladi tugmalarini chiqarish"""
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return
    
    data = await state.get_data()
    client_name = data.get('client_name', '')
    delivered_orders = data.get('delivered_orders', [])
    
    # Tarix tugmasi bosilsa
    if message.text == f"📜 {client_name} Hisob Tarix":
        await show_client_accounting_history(message, client_name)
        return

    # Barchasini hisob kitob qilish tugmasi bosilsa
    if message.text == "💳 Barchasini hisob kitob qilish":
        current_debt = data.get('current_debt', 0)
        try:
            debt_fmt = f"{int(current_debt):,}".replace(',', ' ')
        except:
            debt_fmt = str(current_debt)
        delivered_count = len(data.get('delivered_orders', []))
        markup = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="✅ Ha, barchasini hisob kitob qilish")],
                [types.KeyboardButton(text="❌ Yo'q, bekor qilish")],
                [types.KeyboardButton(text="Bosh menyu")]
            ],
            resize_keyboard=True
        )
        await message.answer(
            f"⚠️ *Diqqat!*\n\n"
            f"🧑 Mijoz: *{client_name}*\n"
            f"📦 Hisob kitob qilinadigan buyurtmalar: *{delivered_count} ta*\n"
            f"💳 Joriy qarz: *{debt_fmt}$*\n\n"
            f"Barcha qarz nolga tushiriladi, lekin olingan mebellar tarixi saqlanib qoladi.\n\n"
            f"Davom etasizmi?",
            parse_mode="Markdown",
            reply_markup=markup
        )
        await state.set_state(ClientAccountingState.confirm_all_settle)
        return
    
    # Qaysi yetkazilgan buyurtma tanlanganini aniqlash
    selected_order = None
    for do in delivered_orders:
        safe_pid = str(do['product_id']).replace('`', '').replace('*', '')
        d_date = do.get('delivered_at', '')
        expected_btn = f"🚛 {safe_pid} — {do['amount']} ta | {d_date}"
        if message.text == expected_btn:
            selected_order = do
            break
    
    if not selected_order:
        await message.answer("Iltimos, tugmalardan birini tanlang:")
        return
    
    # Tanlangan buyurtma ma'lumotlarini saqlash
    await state.update_data(selected_order_id=selected_order['o_id'])
    
    safe_pid = str(selected_order['product_id']).replace('`', '').replace('*', '')
    order_info = f"🚛 *{safe_pid}* — {selected_order['amount']} ta\n"
    order_info += f"📅 Yetkazilgan: {selected_order.get('delivered_at', '')}\n"

    # Narxni ko'rsatish: admin yozgan narxni ustun ko'rsatamiz, yo'q bo'lsa mebellar jadvalidagini
    display_price = selected_order.get('order_total_price')
    pickup_discount = selected_order.get('pickup_discount', 0)
    try:
        pickup_discount = int(float(str(pickup_discount))) if pickup_discount else 0
    except:
        pickup_discount = 0

    if display_price is not None:
        if selected_order.get('driver') == "O'zi olib ketdi" and pickup_discount > 0:
            net = max(0, display_price - pickup_discount)
            order_info += f"💰 Mebel narxi: *{display_price}*$\n💸 Chegirma (o'zi olib ketdi): *-{pickup_discount}*$\n✅ Hisoblangan: *{net}*$\n"
        else:
            order_info += f"💰 Narxi: *{display_price}*$\n"
    elif selected_order.get('price'):
        order_info += f"💰 Narxi: {selected_order['price']}\n"

    if selected_order.get('comment') and str(selected_order.get('comment')).lower() != 'yoq':
        order_info += f"📝 Izoh: {selected_order['comment']}\n"
    order_info += f"📌 Holati: {selected_order.get('status_text', '')}\n\n"
    order_info += "Hisob kitob turini tanlang:"
    
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="✅ Hisob kitob qilindi")],
            [types.KeyboardButton(text="💰 Qisman to'ladi")],
            [types.KeyboardButton(text="🔙 Orqaga")],
            [types.KeyboardButton(text="Bosh menyu")]
        ],
        resize_keyboard=True
    )
    
    try:
        await message.answer(order_info, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        await message.answer(order_info, reply_markup=markup)
    
    await state.set_state(ClientAccountingState.select_action)


@dp.message(ClientAccountingState.select_action)
async def client_accounting_action(message: types.Message, state: FSMContext):
    """Hisob kitob qilindi yoki qisman to'ladi"""
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return
    
    data = await state.get_data()
    client_name = data.get('client_name', '')
    order_id = data.get('selected_order_id', '')
    pending_orders = data.get('pending_orders', [])
    current_debt = data.get('current_debt', 0)
    
    if message.text == "🔙 Orqaga":
        # Qayta mijoz sahifasiga qaytish
        delivered_orders = data.get('delivered_orders', [])
        await show_client_report_inner(message, state, client_name, data.get('pending_orders', []), delivered_orders, current_debt)
        return
    
    if message.text == "✅ Hisob kitob qilindi":
        # Buyurtma tarixga o'tsin — accounting_history ga yozish
        order_ref = await asyncio.to_thread(db.reference(f'orders/{order_id}').get)
        if not order_ref:
            await message.answer("Buyurtma topilmadi.")
            await state.clear()
            return
        
        # ⚠️ Duplikat oldini olish: bu order allaqachon hisob kitob qilinganmi?
        existing_acc = await asyncio.to_thread(db.reference(f'accounting_history/{client_name}').get)
        if existing_acc and isinstance(existing_acc, dict):
            for h_id, h in existing_acc.items():
                if isinstance(h, dict) and h.get('order_id') == str(order_id) and h.get('accounting_type') == 'toliq':
                    product_id = order_ref.get('product_id', '')
                    safe_pid = str(product_id).replace('`', '').replace('*', '')
                    await message.answer(
                        f"⚠️ *{safe_pid}* uchun hisob kitob allaqachon qilingan!\n"
                        f"📋 Tarixda mavjud. Qayta yozilmadi.",
                        parse_mode="Markdown",
                        reply_markup=main_menu('admin')
                    )
                    await state.clear()
                    return
        
        timestamp = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
        history_record = {
            'order_id': order_id,
            'client_name': client_name,
            'product_id': order_ref.get('product_id', ''),
            'amount': order_ref.get('amount', '1'),
            'due_date': order_ref.get('due_date', ''),
            'price': order_ref.get('price', 0),
            'total_price': order_ref.get('total_price', 0),
            'comment': order_ref.get('comment', ''),
            'accounting_type': 'toliq',
            'accounting_date': timestamp,
            'status': 'Hisob kitob qilindi'
        }
        await asyncio.to_thread(db.reference(f'accounting_history/{client_name}').push, history_record)
        
        # Buyurtma holatini bazada 'Hisob kitob qilindi' deb belgilash
        await asyncio.to_thread(db.reference(f'orders/{order_id}').update, {'status': 'Hisob kitob qilindi'})
        
        # Qarzni yangilash
        try:
            raw_total = order_ref.get('total_price', None)
            raw_price = order_ref.get('price', None)
            raw_amount = order_ref.get('amount', 1)
            amount_int = int(float(str(raw_amount))) if raw_amount else 1
            
            # O'zi olib ketdi bo'lsa chegirmani hisobga olish
            pickup_discount = 0
            if order_ref.get('driver') == "O'zi olib ketdi":
                try:
                    pickup_discount = int(order_ref.get('pickup_discount', 0))
                except:
                    pickup_discount = 0

            if raw_total is not None and str(raw_total).strip() not in ('', '0', 'None'):
                total_price = int(float(str(raw_total)))
            elif raw_price is not None and str(raw_price).strip() not in ('', '0', 'None'):
                # total_price yo'q, faqat birlik narxi bor — soniga ko'paytir
                total_price = int(float(str(raw_price))) * amount_int
            else:
                total_price = 0

            # Net narx = mebel narxi - chegirma
            net_price = max(0, total_price - pickup_discount)

        except Exception as _tp_err:
            logging.warning(f"total_price hisoblashda xatolik: {_tp_err}")
            total_price = 0
            net_price = 0
            pickup_discount = 0

        try:
            debt_raw = await asyncio.to_thread(db.reference(f'debts/{client_name}').get)
            current_debt_val = int(float(str(debt_raw))) if debt_raw is not None else 0
        except Exception:
            current_debt_val = 0

        # accounting_history ga yozilgandan so'ng qarzni qayta to'g'ri hisoblash
        new_debt = await recalculate_and_save_debt(client_name)

        # Tranzaksiya tarixiga yozish (net_price > 0 bo'lsa)
        if net_price > 0:
            record = {
                'type': 'Kirim',
                'amount': net_price,
                'timestamp': timestamp,
                'note': f"Hisob kitob qilindi: {order_id} ({order_ref.get('product_id', '')})"
            }
            await asyncio.to_thread(db.reference(f'transactions/clients/{client_name}').push, record)

        product_id = order_ref.get('product_id', '')
        amount_str = order_ref.get('amount', '1')
        safe_pid = str(product_id).replace('`', '').replace('*', '')

        try:
            new_debt_fmt = f"{new_debt:,}".replace(",", " ")
        except Exception:
            new_debt_fmt = str(new_debt)

        # Ko'rsatish uchun matn
        if pickup_discount > 0:
            paid_info = f"\n💰 Mebel narxi: *{total_price}*$\n💸 Chegirma (o'zi olib ketdi): *-{pickup_discount}*$\n✅ Hisoblangan: *{net_price}*$"
        else:
            paid_info = f"\n💸 To'landi: *{net_price:,}*$".replace(",", " ") if net_price > 0 else ""
        await message.answer(
            f"✅ *{safe_pid}* — {amount_str} ta buyurtma hisob kitob qilindi!\n"
            f"📋 Tarixga saqlandi.{paid_info}\n"
            f"💳 Yangi qarz: *{new_debt_fmt}*$",
            parse_mode="Markdown"
        )
        # Hisob kitob qilingan order ni delivered_orders dan olib tashlash va sahifani qayta ko'rsatish
        updated_delivered = [d for d in data.get('delivered_orders', []) if str(d['o_id']) != str(order_id)]
        await state.update_data(delivered_orders=updated_delivered, current_debt=new_debt)
        await show_client_report_inner(message, state, client_name, data.get('pending_orders', []), updated_delivered, new_debt)
        return

    
    if message.text == "💰 Qisman to'ladi":
        order_ref = await asyncio.to_thread(db.reference(f'orders/{order_id}').get)
        product_id = order_ref.get('product_id', '') if order_ref else ''
        safe_pid = str(product_id).replace('`', '').replace('*', '')
        
        await state.update_data(order_id=order_id)
        await message.answer(
            f"💰 *{safe_pid}* uchun qancha pul to'ladi?\n"
            f"(Faqat raqam kiriting, $da):",
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(ClientAccountingState.partial_amount)
        return
    
    await message.answer("Iltimos, tugmalardan birini tanlang.")


@dp.message(ClientAccountingState.partial_amount)
async def client_partial_payment(message: types.Message, state: FSMContext):
    """Qisman to'lov summasini qabul qilish"""
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return
    
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Iltimos, musbat raqam kiriting:")
        return
    
    data = await state.get_data()
    client_name = data.get('client_name', '')
    order_id = data.get('selected_order_id', '')
    
    order_ref = await asyncio.to_thread(db.reference(f'orders/{order_id}').get)
    if not order_ref:
        await message.answer("Buyurtma topilmadi.")
        await state.clear()
        return
    
    timestamp = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
    
    # Qisman to'lov tarixiga yozish
    history_record = {
        'order_id': order_id,
        'client_name': client_name,
        'product_id': order_ref.get('product_id', ''),
        'amount': order_ref.get('amount', '1'),
        'due_date': order_ref.get('due_date', ''),
        'partial_payment': amount,
        'comment': order_ref.get('comment', ''),
        'accounting_type': 'qisman',
        'accounting_date': timestamp,
        'status': 'Qisman to\'ladi'
    }
    await asyncio.to_thread(db.reference(f'accounting_history/{client_name}').push, history_record)
    
    # Qarzni qayta to'g'ri hisoblash va saqlash
    new_debt = await recalculate_and_save_debt(client_name)

    # Tranzaksiya tarixiga yozish
    record = {
        'type': 'Kirim',
        'amount': amount,
        'timestamp': timestamp,
        'note': f"Qisman to'lov: {order_id} ({order_ref.get('product_id', '')})"
    }
    await asyncio.to_thread(db.reference(f'transactions/clients/{client_name}').push, record)

    product_id = order_ref.get('product_id', '')
    safe_pid = str(product_id).replace('`', '').replace('*', '')

    try:
        new_debt_fmt = f"{new_debt:,}".replace(",", " ")
    except Exception:
        new_debt_fmt = str(new_debt)

    await message.answer(
        f"💰 *{safe_pid}* uchun {amount:,}$ qisman to'lov qabul qilindi!\n"
        f"📋 Tarixga saqlandi.\n"
        f"💳 Yangi qarz: *{new_debt_fmt}*$",
        parse_mode="Markdown"
    )
    # Sahifani qayta ko'rsatish
    await state.update_data(current_debt=new_debt)
    updated_data = await state.get_data()
    await show_client_report_inner(message, state, client_name, updated_data.get('pending_orders', []), updated_data.get('delivered_orders', []), new_debt)



async def show_client_report_inner(message, state, client_name, pending_orders, delivered_orders, current_debt):
    """Mijoz hisobot sahifasini qayta ko'rsatish (orqaga qaytganda yoki hisob kitob qilingandan so'ng)"""
    try:
        debt_formatted = f"{int(current_debt):,}".replace(",", " ")
    except:
        debt_formatted = str(current_debt)
    
    header_text = f"🧑 *{client_name}* — Hisob kitob bo'limi\n"
    header_text += f"💳 Joriy qarzi: *{debt_formatted}*$\n\n"
    
    # Pending orders ro'yxati
    if pending_orders:
        header_text += f"⏳ *Tayyorlanmoqda (qarzga qo'shilmagan) — {len(pending_orders)} ta:*\n"
        for po in pending_orders[:30]:
            safe_pid = str(po['product_id']).replace('`', '').replace('*', '')
            status_icon = "✅" if po.get('status') == "Tayyor bo'ldi" else "🔧"
            header_text += f"  {status_icon} {safe_pid} — {po['amount']} ta | {po.get('due_date', '')}\n"
        header_text += "\n"
    
    # Delivered orders tugmalari
    MAX_BUTTONS = 30
    displayed_delivered = delivered_orders[:MAX_BUTTONS]
    hidden_count = len(delivered_orders) - len(displayed_delivered)
    
    if delivered_orders:
        if hidden_count > 0:
            header_text += f"📦 *Olib ketilgan mebellar — hisob kitob uchun tanlang:*\n_({hidden_count} ta eskisi yashirilgan)_"
        else:
            header_text += f"📦 *Olib ketilgan mebellar — hisob kitob uchun tanlang:*"
    else:
        header_text += "✅ Barcha mebellar hisob kitob qilindi."
    
    order_buttons = []
    for do in displayed_delivered:
        safe_pid = str(do['product_id']).replace('`', '').replace('*', '')
        d_date = do.get('delivered_at', '')
        btn_text = f"🚛 {safe_pid} — {do['amount']} ta | {d_date}"
        order_buttons.append([types.KeyboardButton(text=btn_text)])
    
    if delivered_orders:
        order_buttons.append([types.KeyboardButton(text=f"💳 Barchasini hisob kitob qilish")])
    order_buttons.append([types.KeyboardButton(text=f"📜 {client_name} Hisob Tarix")])
    order_buttons.append([types.KeyboardButton(text="Bosh menyu")])
    
    markup = types.ReplyKeyboardMarkup(keyboard=order_buttons, resize_keyboard=True)
    
    try:
        await message.answer(header_text, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        await message.answer(header_text, reply_markup=markup)
    
    await state.set_state(ClientAccountingState.select_order)


@dp.message(ClientAccountingState.confirm_all_settle)
async def confirm_all_settle_handler(message: types.Message, state: FSMContext):
    """Barchasini hisob kitob qilishni tasdiqlash"""
    if message.text == "Bosh menyu" or message.text == "❌ Yo'q, bekor qilish":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bekor qilindi.", reply_markup=main_menu(role))
        await state.clear()
        return

    if message.text != "✅ Ha, barchasini hisob kitob qilish":
        await message.answer("Iltimos, tugmalardan foydalaning.")
        return

    data = await state.get_data()
    client_name = data.get('client_name', '')
    delivered_orders = data.get('delivered_orders', [])

    if not delivered_orders:
        await message.answer("✅ Hisob kitob qilinadigan buyurtma topilmadi.", reply_markup=main_menu('admin'))
        await state.clear()
        return

    # Mavjud accounting_history ni olish (duplikat oldini olish)
    existing_acc = await asyncio.to_thread(db.reference(f'accounting_history/{client_name}').get)
    accounted_ids = set()
    if existing_acc and isinstance(existing_acc, dict):
        for h_id, h in existing_acc.items():
            if isinstance(h, dict) and h.get('accounting_type') == 'toliq':
                oid = str(h.get('order_id', ''))
                if oid:
                    accounted_ids.add(oid)

    # Barcha buyurtmalarni bir marta olish (tejamkorlik uchun)
    orders_ref = await asyncio.to_thread(db.reference('orders').get) or {}
    if not isinstance(orders_ref, dict):
        orders_ref = {}

    timestamp = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
    settled_count = 0
    updates = {}
    history_ref = db.reference(f'accounting_history/{client_name}')

    for do in delivered_orders:
        o_id = str(do.get('o_id', ''))
        if not o_id:
            continue

        order_ref = orders_ref.get(o_id)
        if not order_ref or not isinstance(order_ref, dict):
            continue

        current_status = order_ref.get('status', '')

        # Agar allaqachon tarixda bo'lsa, lekin statusi hali bazada yangilanmagan bo'lsa (mismatch tuzatish)
        if o_id in accounted_ids:
            if current_status != 'Hisob kitob qilindi':
                updates[f'orders/{o_id}/status'] = 'Hisob kitob qilindi'
                settled_count += 1
            continue

        # Tarix yozuvini tayyorlash
        history_record = {
            'order_id': o_id,
            'client_name': client_name,
            'product_id': order_ref.get('product_id', do.get('product_id', '')),
            'amount': order_ref.get('amount', do.get('amount', '1')),
            'due_date': order_ref.get('due_date', do.get('due_date', '')),
            'price': order_ref.get('price', 0),
            'total_price': order_ref.get('total_price', 0),
            'comment': order_ref.get('comment', ''),
            'accounting_type': 'toliq',
            'accounting_date': timestamp,
            'status': 'Hisob kitob qilindi',
            'note': "Barchasini hisob kitob qilish — admin tomonidan"
        }
        
        # Mahalliy ravishda push key yaratish (tarmok so'rovisiz)
        push_key = history_ref.push().key
        updates[f'accounting_history/{client_name}/{push_key}'] = history_record
        updates[f'orders/{o_id}/status'] = 'Hisob kitob qilindi'
        settled_count += 1

    # Barcha o'zgarishlarni bitta so'rovda yangilash (juda tez va xavfsiz)
    if updates:
        await asyncio.to_thread(db.reference().update, updates)

    # debts jadvalida qarzni qayta to'g'ri hisoblash
    await recalculate_and_save_debt(client_name)

    await message.answer(
        f"✅ *{client_name}* — barcha qarz hisob kitob qilindi!\n\n"
        f"📦 Jami *{settled_count} ta* buyurtma hisob kitob qilindi.\n"
        f"💳 Qarz: *0$*\n"
        f"📜 Olingan mebellar tarixi Firebase da saqlanib qoldi.",
        parse_mode="Markdown",
        reply_markup=main_menu('admin')
    )
    await state.clear()




async def show_client_accounting_history(message, client_name):
    """Mijozning hisob kitob tarixini ko'rsatish"""
    history_ref = await asyncio.to_thread(db.reference(f'accounting_history/{client_name}').get)
    
    if not history_ref:
        await message.answer(
            f"📜 *{client_name}* — Hisob kitob tarixi bo'sh.\n"
            "Hali hech qanday hisob kitob qilinmagan.",
            parse_mode="Markdown"
        )
        return
    
    # Narx fallback uchun orders va mebellar jadvallarini yuklab olish
    orders_ref = await asyncio.to_thread(db.reference('orders').get)
    mebellar_ref = await asyncio.to_thread(db.reference('mebellar').get)
    
    header = f"📜 *{client_name} — Hisob kitob tarixi:*\n\n"
    items = []
    
    history_list = []
    for h_id, h in history_ref.items():
        if isinstance(h, dict):
            history_list.append(h)
    
    # Sanasi bo'yicha saralash (yangirog'i birinchi)
    def get_acc_date(item):
        try:
            return datetime.strptime(item.get('accounting_date', ''), "%Y-%m-%d %H:%M:%S")
        except:
            return datetime.min
    history_list.sort(key=get_acc_date, reverse=True)
    
    for h in history_list:
        acc_type = h.get('accounting_type', '')
        if acc_type == 'toliq':
            icon = "✅"
            type_text = "To'liq hisob kitob"
        else:
            icon = "💰"
            paid_amount = h.get('partial_payment', 0)
            try:
                paid_fmt = f"{int(paid_amount):,}".replace(",", " ")
            except:
                paid_fmt = str(paid_amount)
            type_text = f"Qisman to'lov: {paid_fmt}$"
        
        product_id = str(h.get('product_id', '')).replace('`', '').replace('*', '')
        amount = h.get('amount', '1')
        acc_date = format_date(h.get('accounting_date', ''))
        due_date = format_date(h.get('due_date', ''))
        comment = h.get('comment', '')
        
        # Narxni aniqlash: tarix yozuvi → orders → mebellar
        price_val = h.get('price', 0)
        total_val = h.get('total_price', 0)
        try:
            amount_int = int(float(str(amount))) if amount else 1
        except:
            amount_int = 1
        
        # 1. Tarix yozuvidan narx olish
        narx_text = ""
        if total_val and str(total_val).strip() not in ('', '0', 'None'):
            try:
                narx_text = f"{int(float(str(total_val))):,}".replace(",", " ") + "$"
            except:
                narx_text = str(total_val) + "$"
        elif price_val and str(price_val).strip() not in ('', '0', 'None'):
            try:
                p_int = int(float(str(price_val)))
                narx_text = f"{p_int:,}".replace(",", " ") + f"$ × {amount_int} = " + f"{p_int * amount_int:,}".replace(",", " ") + "$"
            except:
                narx_text = str(price_val) + "$"
        
        # 2. Narx topilmasa — orders jadvalidan olish
        if not narx_text:
            order_id_h = h.get('order_id', '')
            if order_id_h and orders_ref and isinstance(orders_ref, dict):
                o = orders_ref.get(str(order_id_h))
                if isinstance(o, dict):
                    raw_total = o.get('total_price', None)
                    raw_price = o.get('price', None)
                    if raw_total and str(raw_total).strip() not in ('', '0', 'None'):
                        try:
                            narx_text = f"{int(float(str(raw_total))):,}".replace(",", " ") + "$"
                        except:
                            pass
                    elif raw_price and str(raw_price).strip() not in ('', '0', 'None'):
                        try:
                            p_int = int(float(str(raw_price)))
                            narx_text = f"{p_int:,}".replace(",", " ") + f"$ × {amount_int} = " + f"{p_int * amount_int:,}".replace(",", " ") + "$"
                        except:
                            pass
        
        # 3. Narx topilmasa — mebellar jadvalidan joriy narxni olish
        if not narx_text:
            p_id_key = str(product_id).replace(" ", "").replace("-", "").upper()
            if mebellar_ref and isinstance(mebellar_ref, dict) and p_id_key in mebellar_ref:
                mebel = mebellar_ref[p_id_key]
                if isinstance(mebel, dict) and mebel.get('narxi'):
                    try:
                        m_price_str = str(mebel['narxi']).replace("so'm", "").replace("$", "").replace(" ", "").replace(",", "")
                        m_price = int(float(m_price_str))
                        narx_text = f"{m_price:,}".replace(",", " ") + f"$ × {amount_int} = " + f"{m_price * amount_int:,}".replace(",", " ") + "$ ⚠️(joriy narx)"
                    except:
                        pass
        
        entry = f"{icon} *{product_id}* — {amount} ta\n"
        entry += f"   📋 {type_text}\n"
        entry += f"   📅 Sana: {acc_date}\n"
        if narx_text:
            entry += f"   💰 Narxi: {narx_text}\n"
        if comment and str(comment).strip().lower() not in ('', 'yoq', "yo'q"):
            entry += f"   📝 Izoh: {comment}\n"
        if due_date:
            entry += f"   🗓 Muddat: {due_date}\n"
        entry += "\n"
        items.append(entry)
    
    # Bo'laklarga ajratib yuborish
    all_parts = [header] + items
    current_msg = ""
    chunks = []
    for part in all_parts:
        if len(current_msg) + len(part) > 3800:
            chunks.append(current_msg)
            current_msg = part
        else:
            current_msg += part
    if current_msg:
        chunks.append(current_msg)
    
    for chunk in chunks:
        try:
            await message.answer(chunk, parse_mode="Markdown")
        except Exception:
            await message.answer(chunk)

# Omborchiga yangi buyurtma haqida xabar yuborish
async def notify_warehouse(order_data, order_id):
    # Asosiy omborchiga xabar yuborish
    try:
        await bot.send_message(
            883589794,
            f"🔔 Yangi buyurtma!\n\n"
            f"🧑 Diller: {order_data['client']}\n"
            f"📦 Mebel: {order_data['product_id']}\n"
            f"📊 Soni: {order_data['amount']}\n"
            f"📅 Muddat: {order_data['due_date']}\n"
            f"📝 Izoh: {order_data.get('comment', 'Yoq')}\n"
            f"🆔 Buyurtma ID: {order_id}"
        )
    except Exception as e:
        print(f"Omborchiga xabar yuborishda xatolik: {e}")

    # Omborchi va xodimlarga xabar yuborish
    users_ref = await asyncio.to_thread(db.reference('users').get)
    for user_id, user_data in (users_ref or {}).items():
        if user_data.get('role') in ['omborchi', 'ishchi', 'xodim'] and int(user_id) != 883589794:
            try:
                await bot.send_message(
                    int(user_id),
                    f"🔔 Yangi buyurtma!\n\n"
                    f"🧑 Diller: {order_data['client']}\n"
                    f"📦 Mebel: {order_data['product_id']}\n"
                    f"📊 Soni: {order_data['amount']}\n"
                    f"📅 Muddat: {order_data['due_date']}\n"
                    f"📝 Izoh: {order_data.get('comment', 'Yoq')}\n"
                    f"🆔 Buyurtma ID: {order_id}"
                )
            except Exception as e:
                print(f"Xodimga xabar yuborishda xatolik: {e}")

async def notify_diller_new_order(order_data, order_id):
    """Admin yangi zakaz yaratganda dillerga xabar yuborish"""
    client_name = order_data.get('client', '')
    diller_ids = DILLER_TELEGRAM_MAP.get(client_name, [])
    if not diller_ids:
        return
    # Narxni hisoblash
    price_val = order_data.get('price', 0)
    try:
        amount = int(order_data.get('amount', 1))
    except:
        amount = 1
    total = 0
    try:
        total = int(price_val) * amount
    except:
        total = 0
    total_str = f"{total:,} so'm".replace(',', ' ') if total else "Ko'rsatilmagan"
    price_str = f"{int(price_val):,} so'm".replace(',', ' ') if price_val else "Ko'rsatilmagan"
    text = (
        f"🎉 *Sizga yangi buyurtma shakllantirildi!*\n\n"
        f"📦 Mebel: *{order_data.get('product_id', '?')}*\n"
        f"📊 Soni: *{amount} ta*\n"
        f"💰 Narxi (1 dona): *{price_str}*\n"
        f"💵 Jami narx: *{total_str}*\n"
        f"📅 Tayyor bo'lish muddati: *{format_date(order_data.get('due_date', '?'))}*\n"
        f"📝 Izoh: {order_data.get('comment', 'Yoq')}\n"
        f"🆔 Buyurtma ID: `{order_id}`"
    )
    for tg_id in diller_ids:
        try:
            await bot.send_message(tg_id, text, parse_mode="Markdown")
        except Exception as e:
            print(f"Dillerga yangi zakaz xabari yuborishda xatolik ({tg_id}): {e}")

# Kunlik eslatma yuborish funksiyasi
def parse_order_date(date_str):
    """Buyurtma sanasini datetime obyektiga o'girish"""
    if not date_str:
        return None
    try:
        if '.' in str(date_str):
            return datetime.strptime(str(date_str), "%d.%m.%Y")
        elif '-' in str(date_str):
            if ' ' in str(date_str):
                return datetime.strptime(str(date_str).split(' ')[0], "%Y-%m-%d")
            return datetime.strptime(str(date_str), "%Y-%m-%d")
    except:
        return None
    return None

async def get_notifiable_users():
    """Xabar yuboriladigan foydalanuvchilar ro'yxatini olish (omborchi va xodimlar)"""
    users_to_notify = set(['883589794'])  # Asosiy omborchi
    for uid in ['6298036669', '1349256808', '7062569902', '7941658592', '1724350130', '698145797', '5063420475']:
        users_to_notify.add(uid)
    
    users_ref = await asyncio.to_thread(db.reference('users').get)
    if users_ref:
        for uid, udata in users_ref.items():
            if isinstance(udata, dict) and udata.get('role') in ['admin', 'omborchi', 'ishchi', 'xodim']:
                users_to_notify.add(str(uid))
    return users_to_notify

async def send_notification(msg):
    """Xabarni barcha omborchi va xodimlarga yuborish"""
    users_to_notify = await get_notifiable_users()
    
    # Bo'laklarga bo'lish (max 3800 belgi)
    chunks = []
    current_msg = ""
    for line in msg.split("\n"):
        if len(current_msg) + len(line) + 1 > 3800:
            chunks.append(current_msg)
            current_msg = line + "\n"
        else:
            current_msg += line + "\n"
    if current_msg:
        chunks.append(current_msg)
        
    for user_id in users_to_notify:
        for chunk in chunks:
            try:
                await bot.send_message(chat_id=int(user_id), text=chunk, parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Error sending reminder to {user_id}: {e}")

async def build_undelivered_msg(header: str, today_str: str) -> str | None:
    """Shu kungacha yetkazilmagan barcha mebellar ro'yxatini tayyorlash"""
    ACTIVE_STATUSES = {'Tayyorlanmoqda', "Tayyor bo'ldi", 'Yuborildi'}

    orders_ref = await asyncio.to_thread(db.reference('orders').get)
    if not orders_ref:
        return None

    now_uz = datetime.now(TASHKENT_TZ)
    today  = now_uz.replace(hour=0, minute=0, second=0, microsecond=0)

    overdue = []
    for o_id, o in orders_ref.items():
        if not isinstance(o, dict):
            continue
        status = o.get('status', '')
        # Faqat faol statusdagi buyurtmalarni ko'rsatish (allaqachon ketgan yoki bekor qilinganlarni emas)
        if status not in ACTIVE_STATUSES:
            continue
        due = parse_order_date(o.get('due_date', ''))
        if due and due.date() <= today.date():
            overdue.append((o_id, o, due))

    if not overdue:
        return None

    overdue.sort(key=lambda x: x[2])  # eng eski muddat tepada

    msg = f"{header}\n📅 Bugun: *{today_str}*\n\n"
    msg += f"📦 Jami: *{len(overdue)} ta* mebel yetkazilmagan\n\n"

    for i, (o_id, o, due) in enumerate(overdue, 1):
        status_icon = "🔧" if o.get('status') == 'Tayyorlanmoqda' else "✅" if o.get('status') == "Tayyor bo'ldi" else "🚛"
        due_formatted = format_date(o.get('due_date', ''))
        msg += f"{i}. {status_icon} *{o.get('client_name', '?')}* — {o.get('product_id', '?')} ({o.get('amount', '?')} ta)\n"
        msg += f"   📅 Muddat: {due_formatted} | 📌 {o.get('status', '?')}\n"
        if o.get('comment') and str(o.get('comment')).lower() not in ('yoq', ''):
            msg += f"   📝 {o.get('comment')}\n"
        msg += "\n"

    return msg

async def send_morning_reminder():
    """09:00 — shu kungacha yetkazilmagan mebellar ro'yxati"""
    today_str = datetime.now(TASHKENT_TZ).strftime("%d.%m.%Y")
    header = f"🌅 *ERTALABKI ESLATMA (09:00)*"
    msg = await build_undelivered_msg(header, today_str)
    if msg:
        await send_notification(msg)
    else:
        await send_notification(
            f"🌅 *ERTALABKI ESLATMA (09:00)*\n📅 Bugun: *{today_str}*\n\n"
            f"✅ Barcha mebellar o'z vaqtida yetkazilgan! Buguncha muddati o'tgan yoki yetkazilmagan zakaz yo'q."
        )

async def send_overdue_reminder():
    """15:00 — shu kungacha yetkazilmagan mebellar ro'yxati"""
    today_str = datetime.now(TASHKENT_TZ).strftime("%d.%m.%Y")
    header = f"🔴 *TUSHKI ESLATMA (15:00) — YETKAZILMAGAN ZAKAZLAR*"
    msg = await build_undelivered_msg(header, today_str)
    if msg:
        await send_notification(msg)
    else:
        await send_notification(
            f"🔴 *TUSHKI ESLATMA (15:00)*\n📅 Bugun: *{today_str}*\n\n"
            f"✅ Zo'r! Buguncha barcha zakazlar yetkazilgan. Muddati o'tgan zakaz yo'q."
        )

async def send_tomorrow_reminder():
    """15:05 - Ertangi zakazlar ro'yxati"""
    now_uz = datetime.now(TASHKENT_TZ)
    tomorrow = (now_uz + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_str = (now_uz + timedelta(days=1)).strftime("%d.%m.%Y")

    orders_ref = await asyncio.to_thread(db.reference('orders').get)
    ACTIVE_STATUSES = {'Tayyorlanmoqda', "Tayyor bo'ldi", 'Yuborildi'}
    tomorrow_orders = []

    if orders_ref:
        for o_id, o in orders_ref.items():
            if not isinstance(o, dict):
                continue
            if o.get('status', '') not in ACTIVE_STATUSES:
                continue
            due = parse_order_date(o.get('due_date', ''))
            if due and due.date() == tomorrow.date():
                tomorrow_orders.append((o_id, o))

    if not tomorrow_orders:
        await send_notification(
            f"📢 *ERTANGI ZAKAZLAR ({tomorrow_str})*\n\n"
            f"✅ Ertaga yetkazilishi kerak bo'lgan zakazlar yo'q."
        )
        return

    msg = f"📢 *ERTANGI ZAKAZLAR ({tomorrow_str})*\n"
    msg += f"Ertaga yetkazishimiz kerak bo'lgan mebellar:\n\n"
    for i, (o_id, o) in enumerate(tomorrow_orders, 1):
        msg += f"{i}. 👤 *{o.get('client_name', '?')}* — {o.get('product_id', '?')} ({o.get('amount', '?')} ta)\n"
        if o.get('comment') and str(o.get('comment')).lower() not in ('yoq', ''):
            msg += f"   📝 {o.get('comment')}\n"
        msg += "\n"
    await send_notification(msg)

async def send_daily_reminders():
    """Test uchun barcha eslatmalarni bir vaqtda yuborish"""
    await send_morning_reminder()
    await asyncio.sleep(2)
    await send_overdue_reminder()
    await asyncio.sleep(2)
    await send_tomorrow_reminder()

# --- XODIM: FAOL BUYURTMALAR ---
@dp.message(F.text == "🔨 Faol buyurtmalar")
async def view_active_orders(message: types.Message):
    role = await get_user_role(message.from_user.id)
    if role in ['xodim', 'admin', 'omborchi']:
        orders_ref = await asyncio.to_thread(db.reference('orders').get)
        if not orders_ref:
            await message.answer("Hozircha hech qanday faol buyurtma yo'q.")
            return
            
        active_orders_list = []
        for o_id, o in orders_ref.items():
            if isinstance(o, dict) and o.get('status') == 'Tayyorlanmoqda':
                active_orders_list.append((o_id, o))
                
        def parse_date(date_str):
            try:
                return datetime.strptime(date_str, "%d.%m.%Y")
            except:
                return datetime.min

        # Guruhlash
        grouped = {}
        for o_id, o in active_orders_list:
            due_date = o.get('due_date', 'Noma\'lum')
            if due_date not in grouped:
                grouped[due_date] = []
            grouped[due_date].append((o_id, o))

        sorted_dates = sorted(grouped.keys(), key=parse_date, reverse=True)

        order_chunks = []
        for d_str in sorted_dates:
            # Sarlavha tayyorlash
            try:
                dt = datetime.strptime(d_str, "%d.%m.%Y")
                header = f"✅ **{dt.day} {UZ_MONTHS[dt.month]} {UZ_WEEKDAYS[dt.weekday()]}**"
            except:
                header = f"✅ **{d_str}**"
            
            day_text = f"{header}\n\n"
            for o_id, o in grouped[d_str]:
                day_text += f"🆔 `{o_id}` - 🧑 Mijoz: {o.get('client_name')}\n"
                day_text += f"📦 Mebel: {o.get('product_id')}\n"
                day_text += f"📊 Soni: {o.get('amount')} ta\n"
                if o.get('comment') and str(o.get('comment')).lower() != 'yoq':
                    day_text += f"📝 Izoh: {o.get('comment')}\n"
                day_text += "------------------------\n"
            order_chunks.append(day_text)
        
        if not order_chunks:
            await message.answer("Hozircha faol zakazlar yo'q.")
            return
            
        current_msg = "🔨 **Faol buyurtmalar ro'yxati:**\n\n"
        for part in order_chunks:
            if len(current_msg) + len(part) > 3900:
                await message.answer(current_msg, parse_mode="Markdown")
                current_msg = part + "\n"
            else:
                current_msg += part + "\n"
        if current_msg:
            await message.answer(current_msg, parse_mode="Markdown")

class DeliveryReportState(StatesGroup):
    select_month = State()

# --- YETKAZISH (DOSTAVKA) HISOBOTI ---
@dp.message(F.text == "📊 Dostavka hisoboti")
async def delivery_report_start(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role not in ['omborchi', 'admin']:
        return

    # So'nggi 6 oyni to'g'ri hisoblash
    now = datetime.now(TASHKENT_TZ)
    months = []
    for i in range(6):
        # Har oyning 1-sanasidan i oy orqaga borish
        month_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1) if i == 0 else now.replace(day=1)
        # Oddiyroq usul: joriy oydan i oy orqaga
        total_month = now.month - i
        year = now.year
        while total_month <= 0:
            total_month += 12
            year -= 1
        months.append(f"{year}-{total_month:02d}")

    buttons = []
    for i in range(0, len(months), 2):
        row = [types.KeyboardButton(text=months[i])]
        if i + 1 < len(months):
            row.append(types.KeyboardButton(text=months[i+1]))
        buttons.append(row)
    buttons.append([types.KeyboardButton(text="Bosh menyu")])

    await message.answer("Qaysi oy hisobotini ko'rmoqchisiz?", reply_markup=types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
    await state.set_state(DeliveryReportState.select_month)

@dp.message(DeliveryReportState.select_month)
async def delivery_report(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return

    try:
        selected_month = message.text
        deliveries_ref = await asyncio.to_thread(db.reference(f'deliveries/{selected_month}').get)

        # Also get completed orders for this month
        orders_ref = await asyncio.to_thread(db.reference('orders').get)
        completed_orders = []
        if orders_ref:
            for o_id, o in orders_ref.items():
                if isinstance(o, dict):
                    order_month = o.get('month', '')
                    order_status = o.get('status', '')
                    if order_month == selected_month and order_status in ["Biz yetkazib berdik", "Dillerni o'zi olib ketdi"]:
                        completed_orders.append((o_id, o))

        # Combine deliveries and completed orders
        all_deliveries = []

        # Add deliveries from deliveries table
        if deliveries_ref:
            if isinstance(deliveries_ref, dict):
                for d_id, d in deliveries_ref.items():
                    if isinstance(d, dict):
                        all_deliveries.append(('delivery', d_id, d))
            elif isinstance(deliveries_ref, list):
                for i, d in enumerate(deliveries_ref):
                    if d is not None and isinstance(d, dict):
                        all_deliveries.append(('delivery', i, d))

        # Add completed orders that don't have delivery records
        for o_id, o in completed_orders:
            # Check if this order already has a delivery record
            has_delivery = False
            for delivery_type, d_id, d in all_deliveries:
                if delivery_type == 'delivery' and d.get('order_id') == o_id:
                    has_delivery = True
                    break

            if not has_delivery:
                # Create a pseudo-delivery record from the order
                pseudo_delivery = {
                    'order_id': o_id,
                    'client': o.get('client_name', 'Noma\'lum'),
                    'product_id': o.get('product_id', 'Noma\'lum'),
                    'amount': o.get('amount', '1'),
                    'driver': o.get('driver', 'O\'zi olib ketdi'),
                    'price': o.get('delivery_price', '0') if o.get('status') == "Biz yetkazib berdik" else o.get('pickup_discount', '0'),
                    'timestamp': o.get('created_at', 'Noma\'lum')
                }
                all_deliveries.append(('order', o_id, pseudo_delivery))

        if not all_deliveries:
            await message.answer(f"{selected_month} oyida hech qanday yetkazib berishlar topilmadi.")
            await state.clear()
            return

        # Sort by timestamp (most recent first)
        def get_timestamp(item):
            delivery_type, d_id, d = item
            timestamp_str = d.get('timestamp', 'Noma\'lum')
            try:
                if timestamp_str != 'Noma\'lum':
                    return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                else:
                    return datetime.min
            except:
                return datetime.min

        all_deliveries.sort(key=get_timestamp, reverse=True)

        report_header = f"📊 **{selected_month} oyi uchun yetkazib berish hisoboti:**\n\n"
        report_items = []

        total_count = 0
        total_items = 0
        total_sum_uzs = 0
        total_sum_usd = 0

        import re
        for delivery_type, d_id, d in all_deliveries:
            order_id = d.get('order_id', "Noma'lum")
            client = d.get('client', "Noma'lum")
            product = d.get('product_id', "Noma'lum")
            driver = d.get('driver', "Noma'lum")
            delivery_date = format_date(d.get('timestamp', "Noma'lum"))
            price = str(d.get('price', '0'))
            amount = d.get('amount', '1')

            try:
                amount_int = int(amount)
            except:
                amount_int = 1

            # Buyurtma sanasini olish
            order_date = "Noma'lum"
            if orders_ref and isinstance(orders_ref, dict) and order_id in orders_ref:
                order_date = format_date(orders_ref[order_id].get('created_at', "Noma'lum"))

            item_text = f"🆔 ID: `{order_id}`\n"
            item_text += f"🧑 Mijoz: {client}\n"
            item_text += f"📦 Mebel: {product} ({amount} ta)\n"
            item_text += f"📅 Buyurtma: {order_date}\n"
            item_text += f"🚚 Yetkazilgan: {delivery_date}\n"
            item_text += f"👨‍✈️ Haydovchi: {driver} ({price})\n"
            item_text += "------------------------"
            report_items.append(item_text)

            # Stats
            total_count += 1
            total_items += amount_int

            # Parse price for totals
            nums = re.findall(r'\d+', price.replace(" ", ""))
            if nums:
                val = int(nums[0])
                if '$' in price:
                    total_sum_usd += val
                else:
                    total_sum_uzs += val

        # Summary
        summary = f"\n📈 **JAMI STATISTIKA ({selected_month}):**\n"
        summary += f"✅ Yetkazib berishlar: {total_count} ta\n"
        summary += f"📦 Jami mebellar: {total_items} ta\n"

        sums = []
        if total_sum_usd > 0:
            sums.append(f"{total_sum_usd}$")
        if total_sum_uzs > 0:
            sums.append(f"{total_sum_uzs:,}$".replace(",", " "))
        if sums:
            summary += f"💰 Jami tushum: {' + '.join(sums)}"
        else:
            summary += "💰 Jami tushum: 0"

        # Send messages in chunks
        full_report = [report_header] + report_items + [summary]

        current_msg = ""
        for part in full_report:
            if len(current_msg) + len(part) > 3900:
                await message.answer(current_msg, parse_mode="Markdown")
                current_msg = part + "\n\n"
            else:
                current_msg += part + "\n\n"

        if current_msg:
            await message.answer(current_msg, parse_mode="Markdown")

        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyuga qaytish uchun tugmani bosing.", reply_markup=main_menu(role))
        await state.clear()

    except Exception as e:
        print(f"Dostavka hisoboti xatolik: {e}")
        role = await get_user_role(message.from_user.id)
        await message.answer("Hisobotni ko'rsatishda xatolik yuz berdi.", reply_markup=main_menu(role))
        await state.clear()

# --- OMBORCHI: OMBORNI YANGILASH (SKLADGA MEBEL QO'SHISH) ---
@dp.message(F.text == "🔄 Omborni yangilash")
async def update_stock_start(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role not in ['omborchi', 'admin']:
        return
    
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📦 Ombor sonini yangilash")],
            [types.KeyboardButton(text="➕ Yangi mebel")],
            [types.KeyboardButton(text="Bosh menyu")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Nima qilmoqchisiz?\n\n"
        "📦 *Ombor sonini yangilash* — mavjud mebelning sonini o'zgartirish\n"
        "➕ *Yangi mebel* — omborga yangi mebel qo'shish",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    await state.clear()

@dp.message(F.text == "📦 Ombor sonini yangilash")
async def update_stock_quantity_start(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role not in ['omborchi', 'admin']:
        return

    # Firebase'dan hozirgi mebellar ro'yxatini olish
    mebellar = await asyncio.to_thread(db.reference('mebellar').get)
    if not mebellar:
        await message.answer("Ombor bo'sh. Avval mebel qo'shing.", reply_markup=main_menu(role))
        return

    buttons = []
    row = []
    items_map = {}  # "BF 07 (8 ta)" -> "BF07"
    for m_id, m in mebellar.items():
        if isinstance(m, dict):
            model = m.get('modeli', m_id)
            soni = m.get('soni', 0)
            btn_text = f"{model} — {soni} ta"
            row.append(types.KeyboardButton(text=btn_text))
            items_map[btn_text] = m_id
            if len(row) == 2:
                buttons.append(row)
                row = []
    if row:
        buttons.append(row)
    buttons.append([types.KeyboardButton(text="🔍 ID orqali qidirish")])
    buttons.append([types.KeyboardButton(text="Bosh menyu")])

    await state.update_data(items_map=items_map)
    await state.set_state(UpdateStockState.product_id)

    markup = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer(
        "📦 Qaysi mebelning sonini yangilamoqchisiz?\n"
        "Ro'yxatdan tanlang yoki 🔍 ID orqali qidiring:",
        reply_markup=markup
    )

@dp.message(UpdateStockState.product_id)
async def update_stock_product_id(message: types.Message, state: FSMContext):
    if message.text == "🔍 ID orqali qidirish":
        await message.answer(
            "Mebel ID sini kiriting (masalan: BF07 yoki BF 07):",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    data = await state.get_data()
    items_map = data.get('items_map', {})

    # Tugma orqali tanladimi yoki qo'lda yozdimi?
    if message.text in items_map:
        product_id = items_map[message.text]
    else:
        product_id = message.text.replace(" ", "").replace("-", "").upper()

    product_ref = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)
    if not product_ref:
        await message.answer(
            f"❌ Mebel topilmadi. Qaytadan tanlang yoki to'g'ri ID kiriting:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    await state.update_data(product_id=product_id)
    await message.answer(
        f"✅ Mebel topildi!\n\n"
        f"🪑 Nomi: *{product_ref.get('nomi', 'Noma\'lum')}*\n"
        f"📐 Modeli: {product_ref.get('modeli', '-')}\n"
        f"📦 Hozirgi qoldiq: *{product_ref.get('soni', 0)} ta*\n\n"
        f"Yangi sonini kiriting:",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    await state.set_state(UpdateStockState.new_quantity)

@dp.message(UpdateStockState.new_quantity)
async def update_stock_new_quantity(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        new_quantity = int(message.text)
        if new_quantity < 0:
            await message.answer("❌ Son manfiy bo'lishi mumkin emas. Qaytadan kiriting:")
            return
        await asyncio.to_thread(
            db.reference(f"mebellar/{data['product_id']}").update,
            {'soni': new_quantity}
        )
        role = await get_user_role(message.from_user.id)
        await message.answer(
            f"✅ Ombor muvaffaqiyatli yangilandi!\n"
            f"🆔 ID: `{data['product_id']}`\n"
            f"📦 Yangi qoldiq: *{new_quantity} ta*",
            reply_markup=main_menu(role),
            parse_mode="Markdown"
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Iltimos, faqat raqam kiriting (masalan: 9):")

# --- OMBORCHI: YETKAZIB BERISH NAZORATI ---
@dp.message(F.text == "🚚 Yetkazishlar nazorati")
async def delivery_control_start(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role not in ['omborchi', 'admin']:
        await message.answer("⛔ Sizda bu funksiyaga ruxsat yo'q.", reply_markup=main_menu(role))
        return
    orders_ref = await asyncio.to_thread(db.reference('orders').get)
    if not orders_ref:
        await message.answer("Hozircha hech qanday buyurtma yo'q.")
        return
            
    active_orders_list = []
    for o_id, o in orders_ref.items():
        if isinstance(o, dict) and o.get('status') in ['Tayyorlanmoqda', "Tayyor bo'ldi", 'Yuborildi']:
            active_orders_list.append((o_id, o))

    def parse_date(date_str):
        try:
            return datetime.strptime(date_str, "%d.%m.%Y")
        except:
            return datetime.min

    # Guruhlash
    grouped = {}
    for o_id, o in active_orders_list:
        due_date = o.get('due_date', 'Noma\'lum')
        if due_date not in grouped:
            grouped[due_date] = []
        grouped[due_date].append((o_id, o))

    sorted_dates = sorted(grouped.keys(), key=parse_date, reverse=True)

    def escape_md(text):
        if not text:
            return ""
        return str(text).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')

    order_report_items = []
    buttons = []
    row = []
    
    for d_str in sorted_dates:
        # Sarlavha tayyorlash
        try:
            dt = datetime.strptime(d_str, "%d.%m.%Y")
            header = f"✅ **{dt.day} {UZ_MONTHS[dt.month]} {UZ_WEEKDAYS[dt.weekday()]}**"
        except:
            header = f"✅ **{escape_md(d_str)}**"
        
        day_text = f"{header}\n\n"
        for o_id, o in grouped[d_str]:
            c_name = escape_md(o.get('client_name', ''))
            p_id = escape_md(o.get('product_id', ''))
            comment_val = o.get('comment', '')
            status_val = escape_md(o.get('status', ''))
            
            day_text += f"🆔 `{escape_md(o_id)}` - 🧑 {c_name}\n"
            day_text += f"📦 Mebel: {p_id} ({o.get('amount')} ta)\n"
            if comment_val and str(comment_val).lower() != 'yoq':
                day_text += f"📝 Izoh: {escape_md(comment_val)}\n"
            day_text += f"📌 Holati: {status_val}\n"
            day_text += "------------------------\n"
            
            # Tugma qo'shish
            button_text = f"{o.get('product_id')} ({str(o_id)})"
            row.append(types.KeyboardButton(text=button_text))
            if len(row) == 2:
                buttons.append(row)
                row = []
                
        order_report_items.append(day_text)
    
    if row:
        buttons.append(row)
    buttons.append([types.KeyboardButton(text="Bosh menyu")])
    
    if not order_report_items:
        await message.answer("Barcha buyurtmalar yetkazib berilgan yoki faol buyurtmalar yo'q.")
        return
        
    markup = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    
    async def send_safe_message(text, reply_markup=None):
        try:
            await message.answer(text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            clean_text = text.replace("**", "").replace("`", "").replace("\\_", "_").replace("\\*", "*").replace("\\[", "[").replace("\\`", "`")
            await message.answer(clean_text, reply_markup=reply_markup)

    # Xabarlarni yuborish
    current_msg = "🚚 **Faol buyurtmalar:**\n\n"
    for i, part in enumerate(order_report_items):
        if len(current_msg) + len(part) > 3800:
            await send_safe_message(current_msg)
            current_msg = part + "\n"
        else:
            current_msg += part + "\n"
            
    prompt = "Qaysi buyurtmaning holatini o'zgartirmoqchisiz? Buyurtma ID-sini tanlang:"
    if len(current_msg) + len(prompt) > 4000:
        await send_safe_message(current_msg)
        await send_safe_message(prompt, reply_markup=markup)
    else:
        await send_safe_message(current_msg + prompt, reply_markup=markup)

    await state.set_state(DeliveryControlState.order_id)

@dp.message(DeliveryControlState.order_id)
async def delivery_order_id(message: types.Message, state: FSMContext):
    if "(" in message.text and ")" in message.text:
        order_id = message.text.split("(")[-1].split(")")[0].strip().upper()
    else:
        order_id = message.text.strip().upper()
        
    order_ref = await asyncio.to_thread(db.reference(f'orders/{order_id}').get)
    if not order_ref:
        await message.answer("Bunday ID li buyurtma topilmadi. Qaytadan kiriting:")
        return
        
    await state.update_data(order_id=order_id, client=order_ref.get('client_name'))
    
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Tayyor bo'ldi"), types.KeyboardButton(text="Biz yetkazib berdik")],
            [types.KeyboardButton(text="Dillerni o'zi olib ketdi"), types.KeyboardButton(text="Bekor qilindi")],
            [types.KeyboardButton(text="Bosh menyu")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(f"Buyurtma: {order_ref.get('client_name')}niki\nHozirgi holat: {order_ref.get('status')}\n\nYangi holatni tanlang:", reply_markup=markup)
    await state.set_state(DeliveryControlState.new_status)

@dp.message(DeliveryControlState.new_status)
async def delivery_new_status(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return
        
    data = await state.get_data()
    new_status = message.text
    
    if new_status in ["Bekor qilindi", "Tayyor bo'ldi"]:
        await asyncio.to_thread(db.reference(f"orders/{data['order_id']}").update, {'status': new_status})
        _role = await get_user_role(message.from_user.id)
        await message.answer(f"✅ Buyurtma holati yangilandi: {new_status}", reply_markup=main_menu(_role))
        
        # Notify admin and workers
        users_ref = await asyncio.to_thread(db.reference('users').get)
        order_ref = await asyncio.to_thread(db.reference(f"orders/{data['order_id']}").get)
        product_id = order_ref.get('product_id', "Noma'lum") if order_ref else "Noma'lum"
        amount = order_ref.get('amount', 1) if order_ref else 1
        client_name_notify = order_ref.get('client_name', data.get('client', '')) if order_ref else data.get('client', '')
        
        for user_id, user_data in (users_ref or {}).items():
            if not isinstance(user_data, dict):
                continue
            if user_data.get('role') == 'admin':
                try:
                    await bot.send_message(
                        int(user_id),
                        f"📦 *Buyurtma holati o'zgardi!*\n\n🆔 ID: `{data['order_id']}`\n🧑 Mijoz: {client_name_notify}\n📦 Mebel: {product_id}\n📊 Soni: {amount} ta\n📌 Yangi holat: *{new_status}*",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    print(f"Adminga xabar yuborishda xatolik: {e}")
            elif user_data.get('role') in ['ishchi', 'xodim'] and new_status == "Tayyor bo'ldi":
                try:
                    await bot.send_message(
                        int(user_id),
                        f"✅ *Mahsulot tayyor bo'ldi!*\n\n🆔 Buyurtma ID: `{data['order_id']}`\n🧑 Mijoz: {client_name_notify}\n📦 Mebel: {product_id}\n📊 Soni: {amount} ta",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

        # Dillerlarga xabar yuborish (faqat "Tayyor bo'ldi" holatida)
        if new_status == "Tayyor bo'ldi":
            diller_tg_ids = DILLER_TELEGRAM_MAP.get(client_name_notify, [])
            due_date = order_ref.get('due_date', '?') if order_ref else '?'
            for diller_tg_id in diller_tg_ids:
                try:
                    await bot.send_message(
                        int(diller_tg_id),
                        f"🎉 *Sizning buyurtmangiz tayyor bo'ldi!*\n\n"
                        f"📦 Mebel: *{product_id}*\n"
                        f"📊 Soni: *{amount} ta*\n"
                        f"📅 Muddati: *{format_date(due_date)}*\n\n"
                        f"Yetkazib berish haqida tez orada xabar beramiz. ✅",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

        await state.clear()
        return

    elif new_status == "Dillerni o'zi olib ketdi":
        await state.update_data(new_status=new_status, driver="O'zi olib ketdi")
        markup = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="6$"), types.KeyboardButton(text="8$")],
                [types.KeyboardButton(text="10$"), types.KeyboardButton(text="0")],
                [types.KeyboardButton(text="Bosh menyu")]
            ],
            resize_keyboard=True
        )
        await message.answer("Chegirma summasini tanlang yoki kiriting ($da):", reply_markup=markup)
        await state.set_state(DeliveryControlState.custom_price)
        return

    elif new_status == "Biz yetkazib berdik":
        await state.update_data(new_status=new_status)
        markup = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="Dilmurod"), types.KeyboardButton(text="Bahodir aka")],
                [types.KeyboardButton(text="Javxar"), types.KeyboardButton(text="Baxrom")],
                [types.KeyboardButton(text="Boshqa"), types.KeyboardButton(text="Bosh menyu")]
            ],
            resize_keyboard=True
        )
        await message.answer("Yetkazib bergan haydovchini tanlang:", reply_markup=markup)
        await state.set_state(DeliveryControlState.driver)
        return

@dp.message(DeliveryControlState.driver)
async def delivery_driver(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return
        
    if message.text == "Boshqa":
        await message.answer("Haydovchi nomini kiriting:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(DeliveryControlState.custom_driver)
        return
        
    try:
        await state.update_data(driver=message.text)
        
        markup = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="3.5$"), types.KeyboardButton(text="6$"), types.KeyboardButton(text="8$")],
                [types.KeyboardButton(text="Boshqa narx"), types.KeyboardButton(text="Bosh menyu")]
            ],
            resize_keyboard=True
        )
        await message.answer("Yetkazib berish narxini belgilang ($da):", reply_markup=markup)
        await state.set_state(DeliveryControlState.delivery_price)
    except Exception as e:
        import traceback
        err_text = traceback.format_exc()
        print(err_text)
        await message.answer(f"Haydovchini tanlashda xatolik yuz berdi:\n\n{err_text[:4000]}")

@dp.message(DeliveryControlState.delivery_price)
async def delivery_price_handler(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return
        
    if message.text == "Boshqa narx":
        await message.answer("Iltimos, narxni kiriting (masalan: 10$):", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(DeliveryControlState.custom_price)
        return
        
    try:
        await process_delivery_final(message.text, message, state)
    except Exception as e:
        import traceback
        err_text = traceback.format_exc()
        print(err_text)
        await message.answer(f"Xatolik yuz berdi:\n\n{err_text[:4000]}")

@dp.message(DeliveryControlState.custom_price)
async def delivery_custom_price(message: types.Message, state: FSMContext):
    try:
        await process_delivery_final(message.text, message, state)
    except Exception as e:
        import traceback
        err_text = traceback.format_exc()
        print(err_text)
        await message.answer(f"Xatolik yuz berdi:\n\n{err_text[:4000]}")

@dp.message(DeliveryControlState.custom_driver)
async def delivery_custom_driver(message: types.Message, state: FSMContext):
    try:
        await state.update_data(driver=message.text)
        
        markup = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="3.5$"), types.KeyboardButton(text="6$"), types.KeyboardButton(text="8$")],
                [types.KeyboardButton(text="Boshqa narx"), types.KeyboardButton(text="Bosh menyu")]
            ],
            resize_keyboard=True
        )
        await message.answer("Yetkazib berish narxini belgilang ($da):", reply_markup=markup)
        await state.set_state(DeliveryControlState.delivery_price)
    except Exception as e:
        import traceback
        err_text = traceback.format_exc()
        print(err_text)
        await message.answer(f"Haydovchini kiritishda xatolik yuz berdi:\n\n{err_text[:4000]}")



async def process_delivery_final(price, message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data['order_id']
    new_status = data['new_status']
    driver = data['driver']
    client = data['client']
    
    # Update order
    current_month = datetime.now(TASHKENT_TZ).strftime("%Y-%m")
    timestamp = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")

    # O'zi olib ketdi uchun chegirma summasini olish
    import re as _re2
    _disc_nums = _re2.findall(r'\d+', str(price).replace(" ", ""))
    discount_val = int(_disc_nums[0]) if _disc_nums and driver == "O'zi olib ketdi" else 0

    await asyncio.to_thread(db.reference(f"orders/{order_id}").update, {
        'status': new_status,
        'driver': driver,
        'delivery_price': price,
        'pickup_discount': discount_val,
        'month': current_month,
        'delivered_at': timestamp
    })
    
    # Get product_id and amount for history
    order_ref = await asyncio.to_thread(db.reference(f"orders/{order_id}").get)
    product_id = order_ref.get('product_id', "Noma'lum") if order_ref else "Noma'lum"
    amount = order_ref.get('amount', 1) if order_ref else 1
    
    # Save delivery report
    current_month = datetime.now(TASHKENT_TZ).strftime("%Y-%m")
    timestamp = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
    # Buyurtma izohini ham saqlash
    order_comment = order_ref.get('comment', '') if order_ref else ''
    delivery_record = {
        'order_id': order_id,
        'client': client,
        'driver': driver,
        'price': price,
        'product_id': product_id,
        'amount': amount,
        'timestamp': timestamp,
        'comment': order_comment
    }
    await asyncio.to_thread(db.reference(f"deliveries/{current_month}").push, delivery_record)

    # Calculate and update client debt only when delivered or picked up
    try:
        try:
            amount_int = int(amount)
        except:
            amount_int = 1

        order_total_price = 0
        if order_ref:
            if 'total_price' in order_ref:
                order_total_price = int(order_ref.get('total_price', 0))
            elif 'price' in order_ref:
                order_total_price = int(order_ref.get('price', 0)) * amount_int
            else:
                # Fallback to mebellar database if not present in order (for old orders)
                mebel_ref = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)
                if mebel_ref and 'narxi' in mebel_ref:
                    price_str = str(mebel_ref['narxi']).replace("so'm", "").replace("$", "").replace(" ", "")
                    try:
                        price_val = int(price_str)
                        order_total_price = price_val * amount_int
                    except:
                        pass

        if order_total_price > 0:
            # O'zi olib ketdi bo'lsa — NET narxni (chegirma ayirib) bir tranzaksiyada yoz
            if driver == "O'zi olib ketdi" and discount_val > 0:
                net_price = max(0, order_total_price - discount_val)
                debt_ref = await asyncio.to_thread(db.reference(f'debts/{client}').get)
                current_debt = int(debt_ref) if debt_ref else 0
                new_debt = current_debt + net_price
                await asyncio.to_thread(db.reference(f'debts/{client}').set, new_debt)
                # Bitta tranzaksiya: chegirma ko'rsatilgan holda
                record = {
                    'type': 'Chiqim',
                    'amount': net_price,
                    'timestamp': timestamp,
                    'note': f"Olib ketdi (chegirma: {discount_val}$): {product_id} ({amount_int} ta) → {order_total_price}$ - {discount_val}$ = {net_price}$ (Buyurtma: {order_id})"
                }
                await asyncio.to_thread(db.reference(f'transactions/clients/{client}').push, record)
            else:
                debt_ref = await asyncio.to_thread(db.reference(f'debts/{client}').get)
                current_debt = int(debt_ref) if debt_ref else 0
                new_debt = current_debt + order_total_price
                await asyncio.to_thread(db.reference(f'debts/{client}').set, new_debt)
                # Tarixga yozish (Chiqim)
                record = {
                    'type': 'Chiqim',
                    'amount': order_total_price,
                    'timestamp': timestamp,
                    'note': f"Yetkazildi: {product_id} ({amount_int} ta) (Buyurtma: {order_id})"
                }
                await asyncio.to_thread(db.reference(f'transactions/clients/{client}').push, record)
    except Exception as _de:
        logging.warning(f"Qarz hisoblashda xatolik: {_de}")

    try:
        import re as _re
        _nums = _re.findall(r'\d+', str(price).replace(" ", ""))
        price_val = int(_nums[0]) if _nums else 0
        if price_val > 0:
            if driver != "O'zi olib ketdi":
                # Faqat haydovchi uchun — balansni oshirish
                balance_ref = await asyncio.to_thread(db.reference(f"driver_balances/{driver}").get)
                current_balance = int(balance_ref) if balance_ref else 0
                new_balance = current_balance + price_val
                await asyncio.to_thread(db.reference(f"driver_balances/{driver}").set, new_balance)
                # Tarixga yozish
                record = {'type': 'Kirim', 'amount': price_val, 'timestamp': timestamp, 'note': f"Yetkazib berish haqi (Buyurtma: {order_id})"}
                await asyncio.to_thread(db.reference(f"transactions/drivers/{driver}").push, record)
    except Exception as _pe:
        logging.warning(f"Narx parse yoki tranzaksiya xatoligi: {_pe}")
        
    # Omborchiga va adminga xabar
    pickup_info = f"\n💸 Chegirma: {price} → Net: {order_total_price - discount_val}$" if driver == "O'zi olib ketdi" and discount_val > 0 else f"\n💵 Narxi: {price}"
    _role = await get_user_role(message.from_user.id)
    await message.answer(
        f"✅ Buyurtma holati yangilandi: {new_status}\n"
        f"🚚 Haydovchi: {driver}{pickup_info}",
        reply_markup=main_menu(_role)
    )
    
    # Notify admin
    admin_ref = await asyncio.to_thread(db.reference('users').get)
    for user_id, user_data in (admin_ref or {}).items():
        if user_data.get('role') == 'admin':
            try:
                await bot.send_message(
                    int(user_id),
                    f"📦 **Buyurtma holati o'zgardi!**\n\n🆔 ID: `{order_id}`\n🧑 Diller: {client}\n📌 Yangi holat: {new_status}\n🚚 Haydovchi: {driver}\n💵 Narxi: {price}",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    # Dillerga yetkazib berilganligi haqida xabar
    diller_ids_for_delivery = DILLER_TELEGRAM_MAP.get(client, [])
    if diller_ids_for_delivery:
        try:
            amount_for_notify = order_ref.get('amount', 1) if order_ref else 1
            price_for_notify  = order_ref.get('price', 0) if order_ref else 0
            total_for_notify  = 0
            try:
                total_for_notify = int(float(str(price_for_notify))) * int(float(str(amount_for_notify)))
            except:
                pass
            total_str_notify = f"{total_for_notify:,}$".replace(',', ' ') if total_for_notify else "—"
            delivery_notify_text = (
                f"🚚 *Mebelingiz yetkazib berildi!*\n\n"
                f"📦 Mebel: *{product_id}*\n"
                f"📊 Soni: *{amount_for_notify} ta*\n"
                f"💵 Mebel narxi: *{total_str_notify}*\n"
                f"🧑 Haydovchi: *{driver}*\n"
                f"💰 Dostavka narxi: *{price}*\n"
                f"🆔 Buyurtma ID: `{order_id}`"
            )
            for d_tg_id in diller_ids_for_delivery:
                try:
                    await bot.send_message(d_tg_id, delivery_notify_text, parse_mode="Markdown")
                except Exception as _de_err:
                    print(f"Dillerga yetkazib berildi xabari ({d_tg_id}): {_de_err}")
        except Exception as _de2:
            print(f"Delivery notify error: {_de2}")

    await state.clear()


class DriverReportState(StatesGroup):
    select_month = State()

@dp.message(F.text == "🚚 Haydovchilar hisoboti")
async def driver_report_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'admin':
        current_month = datetime.now(TASHKENT_TZ).strftime("%Y-%m")
        deliveries_ref = await asyncio.to_thread(db.reference(f'deliveries/{current_month}').get)
        
        if not deliveries_ref:
            await message.answer(f"Ushbu oy ({current_month}) uchun yetkazib berilgan buyurtmalar topilmadi.")
            return
            
        driver_stats = {}
        report_text = f"📊 **{current_month} oyi uchun haydovchilar hisoboti:**\n\n"
        
        import re
        for d_id, d in deliveries_ref.items():
            if isinstance(d, dict):
                driver = d.get('driver', 'Noma\'lum')
                price = str(d.get('price', '0'))
                client = d.get('client', 'Noma\'lum')
                
                if driver not in driver_stats:
                    driver_stats[driver] = {'count': 0, 'total_price': [], 'clients': [], 'sum_dollar': 0, 'sum_som': 0}
                    
                driver_stats[driver]['count'] += 1
                driver_stats[driver]['total_price'].append(price)
                driver_stats[driver]['clients'].append(f"{client} ({price})")
                
                nums = re.findall(r'\d+', price)
                if nums:
                    val = int(nums[0])
                    if '$' in price:
                        driver_stats[driver]['sum_dollar'] += val
                    else:
                        driver_stats[driver]['sum_som'] += val
                
        for driver_name, stats in driver_stats.items():
            report_text += f"🚚 **{driver_name}**\n"
            report_text += f"📦 Jami yetkazib berishlar: {stats['count']} ta\n"
            
            sums_arr = []
            if stats['sum_dollar'] > 0:
                sums_arr.append(f"{stats['sum_dollar']}$")
            if stats['sum_som'] > 0:
                sums_arr.append(f"{stats['sum_som']}$")
            sum_text = " + ".join(sums_arr) if sums_arr else "0"
            
            report_text += f"💰 Narxlar: {', '.join(stats['total_price'])} (Jami: {sum_text})\n"
            report_text += f"👥 Mijozlar: {', '.join(stats['clients'])}\n\n"
            
        drivers = list(driver_stats.keys())
        if "Dilmurod" not in drivers: drivers.append("Dilmurod")
        if "Bahodir aka" not in drivers: drivers.append("Bahodir aka")
        if "Javxar" not in drivers: drivers.append("Javxar")
        if "Baxrom" not in drivers: drivers.append("Baxrom")
        
        buttons = []
        for i in range(0, len(drivers), 2):
            row = [types.KeyboardButton(text=f"👨‍✈️ {drivers[i]}")]
            if i + 1 < len(drivers):
                row.append(types.KeyboardButton(text=f"👨‍✈️ {drivers[i+1]}"))
            buttons.append(row)
        buttons.append([types.KeyboardButton(text="Bosh menyu")])
        markup = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
            
        await message.answer(report_text, parse_mode="Markdown", reply_markup=markup)

@dp.message(F.text.startswith("👨‍✈️ "))
async def select_driver_finance(message: types.Message):
    if await get_user_role(message.from_user.id) == 'admin':
        driver_name = message.text.replace("👨‍✈️ ", "").strip()
        
        bal_ref = await asyncio.to_thread(db.reference(f'driver_balances/{driver_name}').get)
        current_bal = bal_ref if bal_ref is not None else 0
        
        markup = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text=f"➕ {driver_name} ga Pul Berish (D. Chiqim)")],
                [types.KeyboardButton(text=f"➖ {driver_name} dan Pul Qaytardi (D. Kirim)")],
                [types.KeyboardButton(text=f"📜 {driver_name} Moliya Tarixi")],
                [types.KeyboardButton(text=f"📊 {driver_name} yetkazib berish tarixi")],
                [types.KeyboardButton(text="Bosh menyu")]
            ],
            resize_keyboard=True
        )
        
        text = f"👨‍✈️ **Haydovchi:** {driver_name}\n"
        text += f"💳 **Joriy balansi (sizning qarzingiz/haqqingiz):** {current_bal}$\n\n"
        text += "*(Eslatma: Bu balansga qilingan yetkazib berishlar puli avtomatik qo'shilmaydi. Moliya bo'limi orqali hisob-kitobni o'zingiz yurgizasiz)*"
        await message.answer(text, parse_mode="Markdown", reply_markup=markup)

@dp.message(F.text.contains("ga Pul Berish (D. Chiqim)"))
async def driver_chiqim_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'admin':
        driver_name = message.text.replace("➕ ", "").replace(" ga Pul Berish (D. Chiqim)", "").strip()
        await state.update_data(driver_name=driver_name)
        await message.answer(f"👨‍✈️ {driver_name} ga qancha pul berildi? (faqat raqam):", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(DriverFinanceState.amount_chiqim)

@dp.message(DriverFinanceState.amount_chiqim)
async def process_driver_chiqim(message: types.Message, state: FSMContext):
    data = await state.get_data()
    driver_name = data['driver_name']
    try:
        amount = int(message.text)
        bal_ref = await asyncio.to_thread(db.reference(f'driver_balances/{driver_name}').get)
        current_bal = bal_ref if bal_ref is not None else 0
        
        # We give driver money -> decreases the debt we owe them (or makes them owe us)
        new_bal = current_bal - amount
        await asyncio.to_thread(db.reference(f'driver_balances/{driver_name}').set, new_bal)
        
        timestamp = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
        record = {'type': 'Chiqim', 'amount': amount, 'timestamp': timestamp, 'note': "Pul berildi"}
        await asyncio.to_thread(db.reference(f'transactions/drivers/{driver_name}').push, record)
        
        await message.answer(f"✅ {driver_name} ga {amount}$ berildi.\n💳 Yangi balansi: {new_bal}$", reply_markup=main_menu('admin'))
        await state.clear()
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting:")

@dp.message(F.text.contains("dan Pul Qaytardi (D. Kirim)"))
async def driver_kirim_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'admin':
        driver_name = message.text.replace("➖ ", "").replace(" dan Pul Qaytardi (D. Kirim)", "").strip()
        await state.update_data(driver_name=driver_name)
        await message.answer(f"👨‍✈️ {driver_name} qancha pul qaytardi yoki haqqi qo'shildi? (faqat raqam):", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(DriverFinanceState.amount_kirim)

@dp.message(DriverFinanceState.amount_kirim)
async def process_driver_kirim(message: types.Message, state: FSMContext):
    data = await state.get_data()
    driver_name = data['driver_name']
    try:
        amount = int(message.text)
        bal_ref = await asyncio.to_thread(db.reference(f'driver_balances/{driver_name}').get)
        current_bal = bal_ref if bal_ref is not None else 0
        new_bal = current_bal + amount
        await asyncio.to_thread(db.reference(f'driver_balances/{driver_name}').set, new_bal)
        
        timestamp = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
        record = {'type': 'Kirim', 'amount': amount, 'timestamp': timestamp, 'note': "Pul qaytardi / Haqqi yozildi"}
        await asyncio.to_thread(db.reference(f'transactions/drivers/{driver_name}').push, record)
        
        await message.answer(f"✅ {driver_name} hisobiga {amount}$ qo'shildi.\n💳 Yangi balansi: {new_bal}$", reply_markup=main_menu('admin'))
        await state.clear()
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting:")

@dp.message(F.text.contains("Moliya Tarixi"))
async def driver_history(message: types.Message):
    if await get_user_role(message.from_user.id) == 'admin':
        driver_name = message.text.replace("📜 ", "").replace(" Moliya Tarixi", "").strip()
        trans_ref = await asyncio.to_thread(db.reference(f'transactions/drivers/{driver_name}').get)
        if not trans_ref:
            await message.answer(f"👨‍✈️ {driver_name} bo'yicha moliya (Kirim/Chiqim) tarixi yo'q.")
            return
            
        history = f"📜 **{driver_name} moliya tarixi:**\n\n"
        for t_id, t in trans_ref.items():
            if isinstance(t, dict):
                icon = "🔴" if t.get('type') == 'Chiqim' else "🟢"
                history += f"{icon} {t.get('type')}: {t.get('amount')}$\n"
                history += f"📅 Sana: {format_date(t.get('timestamp', ''))}\n\n"
            
        if len(history) > 4000:
            for x in range(0, len(history), 4000):
                await message.answer(history[x:x+4000], parse_mode="Markdown")
        else:
            await message.answer(history, parse_mode="Markdown")

class HistoryState(StatesGroup):
    select_month = State()

@dp.message(F.text == "🕰 Yetkazish tarixi")
async def delivery_history_start(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role in ['admin', 'omborchi']:
        # So'nggi 6 oyni to'g'ri hisoblash
        now = datetime.now(TASHKENT_TZ)
        months = []
        for i in range(6):
            total_month = now.month - i
            year = now.year
            while total_month <= 0:
                total_month += 12
                year -= 1
            months.append(f"{year}-{total_month:02d}")
        
        buttons = []
        for i in range(0, len(months), 2):
            row = [types.KeyboardButton(text=months[i])]
            if i + 1 < len(months):
                row.append(types.KeyboardButton(text=months[i+1]))
            buttons.append(row)
        buttons.append([types.KeyboardButton(text="Bosh menyu")])
        
        await message.answer("Qaysi oy tarixini ko'rmoqchisiz?", reply_markup=types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
        await state.set_state(HistoryState.select_month)

@dp.message(HistoryState.select_month)
async def show_delivery_history(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return
        
    try:
        month = message.text
        deliveries_ref = await asyncio.to_thread(db.reference(f'deliveries/{month}').get)
        if not deliveries_ref:
            await message.answer(f"{month} oyida hech qanday yetkazib berishlar yo'q.")
            return
            
        # Safe iteration
        if isinstance(deliveries_ref, dict):
            items = list(deliveries_ref.items())
        elif isinstance(deliveries_ref, list):
            items = [(i, v) for i, v in enumerate(deliveries_ref) if v is not None]
        else:
            items = []
            
        # Xronologik tartib: eskisi tepada (reverse qilmaymiz)

        def escape_md(text):
            if not text:
                return ""
            return str(text).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')

        history_header = f"🕰 **{escape_md(month)} oyi yetkazib berish tarixi:**\n\n"
        history_items = []
        
        for d_id, d in items:
            if isinstance(d, dict):
                t_str = format_date(d.get('timestamp', "Noma'lum"))
                c_str = escape_md(d.get('client', "Noma'lum"))
                p_str = escape_md(d.get('product_id', "Noma'lum"))
                a_str = escape_md(d.get('amount', '1'))
                dr_str = escape_md(d.get('driver', "Noma'lum"))
                pr_str = escape_md(d.get('price', '0'))
                comment_str = escape_md(d.get('comment', ''))
                
                item_text = f"📅 Vaqt: {t_str}\n"
                item_text += f"🧑 Diller: {c_str}\n"
                item_text += f"📦 Mebel: {p_str} ({a_str} ta)\n"
                item_text += f"🚚 Dostavchik: {dr_str} ({pr_str})\n"
                if comment_str and str(comment_str).lower() not in ['', 'yoq']:
                    item_text += f"📝 Izoh: {comment_str}\n"
                item_text += "------------------------"
                history_items.append(item_text)
                
        # Send in chunks
        full_history = [history_header] + history_items
        current_msg = ""
        
        async def send_safe_message(text):
            try:
                await message.answer(text, parse_mode="Markdown")
            except Exception:
                clean_text = text.replace("**", "").replace("`", "").replace("\\_", "_").replace("\\*", "*").replace("\\[", "[").replace("\\`", "`")
                await message.answer(clean_text)

        for part in full_history:
            if len(current_msg) + len(part) > 3900:
                await send_safe_message(current_msg)
                current_msg = part + "\n\n"
            else:
                current_msg += part + "\n\n"
        
        if current_msg:
            await send_safe_message(current_msg)
            
    except Exception as e:
        logging.error(f"Tarix ko'rsatishda xatolik: {e}")
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")


@dp.message(F.text == "📈 Sotuv statistikasi")
async def sales_statistics(message: types.Message):
    if await get_user_role(message.from_user.id) == 'admin':
        orders_ref = await asyncio.to_thread(db.reference('orders').get)
        if not orders_ref:
            await message.answer("Sotuvlar tarixi bo'sh.")
            return

        monthly_stats = {}
        for o_id, o in orders_ref.items():
            if isinstance(o, dict):
                month = o.get('month', 'Avvalgi oylar')
                pid = o.get('product_id', 'Noma\'lum')
                try:
                    amount = int(o.get('amount', 1))
                except:
                    amount = 1
                
                if month not in monthly_stats:
                    monthly_stats[month] = {}
                monthly_stats[month][pid] = monthly_stats[month].get(pid, 0) + amount
        
        sorted_months = sorted(monthly_stats.keys(), reverse=True)
        text = "📈 **Eng ko'p sotilgan mebellar (Oylar kesimida):**\n\n"
        
        for month in sorted_months:
            text += f"📅 **{month} oyi:**\n"
            month_data = monthly_stats[month]
            sorted_stats = sorted(month_data.items(), key=lambda x: x[1], reverse=True)
            for i, (pid, count) in enumerate(sorted_stats[:20], 1):
                text += f"  {i}. 🪑 {pid} - {count} ta\n"
            text += "\n"
            
        if len(text) > 4000:
            for x in range(0, len(text), 4000):
                await message.answer(text[x:x+4000], parse_mode="Markdown")
        else:
            await message.answer(text, parse_mode="Markdown")

@dp.message(F.text.contains(" yetkazib berish tarixi"))
async def driver_deliveries_history(message: types.Message):
    if await get_user_role(message.from_user.id) == 'admin':
        driver_name = message.text.replace("📊 ", "").replace(" yetkazib berish tarixi", "").strip()
        deliveries_ref = await asyncio.to_thread(db.reference('deliveries').get)
        
        if not deliveries_ref:
            await message.answer("Hech qanday yetkazib berish tarixi topilmadi.")
            return
            
        monthly_stats = {}
        for month, deliveries in deliveries_ref.items():
            if isinstance(deliveries, dict):
                for d_id, d in deliveries.items():
                    if isinstance(d, dict) and d.get('driver') == driver_name:
                        if month not in monthly_stats:
                            monthly_stats[month] = []
                        monthly_stats[month].append(d)
        
        if not monthly_stats:
            await message.answer(f"👨‍✈️ {driver_name} hech qanday mebel yetkazib bermagan.")
            return
            
        sorted_months = sorted(monthly_stats.keys(), reverse=True)
        report_text = f"📊 **{driver_name} yetkazib berish tarixi:**\n\n"
        
        for month in sorted_months:
            month_deliveries = monthly_stats[month]
            report_text += f"📅 **{month} oyi:**\n"
            count = 0
            for d in month_deliveries:
                count += 1
                d_date = format_date(d.get('timestamp', ''))
                date_str = f" [{d_date}]" if d_date and d_date != "Noma'lum" else ""
                report_text += f" ▪️ {d.get('client')} ga: {d.get('product_id')} (Narxi: {d.get('price')}){date_str}\n"
            report_text += f" 📦 Jami shu oyda: {count} ta yetkazib berish\n\n"
            
        if len(report_text) > 4000:
            for x in range(0, len(report_text), 4000):
                await message.answer(report_text[x:x+4000], parse_mode="Markdown")
        else:
            await message.answer(report_text, parse_mode="Markdown")

# --- ADMIN: BUYURTMALAR NAZORATI ---
@dp.message(F.text == "📋 Buyurtmalar nazorati")
async def admin_order_control_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != 'admin':
        return
    
    orders_ref = await asyncio.to_thread(db.reference('orders').get)
    if not orders_ref:
        await message.answer("Hozircha hech qanday buyurtma yo'q.")
        return
    
    active_orders_list = []
    for o_id, o in orders_ref.items():
        if isinstance(o, dict) and o.get('status') in ['Tayyorlanmoqda', "Tayyor bo'ldi", 'Yuborildi']:
            active_orders_list.append((o_id, o))
    
    def parse_date(date_str):
        try:
            return datetime.strptime(date_str, "%d.%m.%Y")
        except:
            return datetime.min
    
    active_orders_list.sort(key=lambda x: parse_date(x[1].get('due_date', '')), reverse=True)
    
    if not active_orders_list:
        await message.answer("Hozircha faol buyurtmalar yo'q.")
        return
    
    order_report_items = []
    buttons = []
    row = []
    for o_id, o in active_orders_list:
        item_text = f"🆔 `{o_id}` - 🧑 {o.get('client_name')}\n"
        item_text += f"📦 Mebel: {o.get('product_id')} ({o.get('amount')} ta)\n"
        item_text += f"📅 Muddat: {format_date(o.get('due_date', ''))}\n"
        if o.get('comment') and str(o.get('comment')).lower() != 'yoq':
            item_text += f"📝 Izoh: {o.get('comment')}\n"
        item_text += f"📌 Holati: {o.get('status')}\n"
        item_text += "------------------------"
        order_report_items.append(item_text)
        
        button_text = f"{o.get('product_id')} ({str(o_id)})"
        row.append(types.KeyboardButton(text=button_text))
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    buttons.append([types.KeyboardButton(text="Bosh menyu")])
    
    markup = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    
    # Send items in chunks to avoid Telegram 4096 length limit
    current_msg = "📋 **Faol buyurtmalar:**\n\n"
    for part in order_report_items:
        if len(current_msg) + len(part) > 3800:
            await message.answer(current_msg, parse_mode="Markdown")
            current_msg = part + "\n\n"
        else:
            current_msg += part + "\n\n"
            
    prompt = "Qaysi buyurtmani boshqarmoqchisiz? Tanlang:"
    if len(current_msg) + len(prompt) > 4000:
        await message.answer(current_msg, parse_mode="Markdown")
        await message.answer(prompt, reply_markup=markup, parse_mode="Markdown")
    else:
        await message.answer(current_msg + prompt, reply_markup=markup, parse_mode="Markdown")

    await state.set_state(AdminOrderControlState.select_order)

@dp.message(AdminOrderControlState.select_order)
async def admin_order_selected(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return
    
    if "(" in message.text and ")" in message.text:
        order_id = message.text.split("(")[-1].split(")")[0].strip().upper()
    else:
        order_id = message.text.strip().upper()
    
    order_ref = await asyncio.to_thread(db.reference(f'orders/{order_id}').get)
    if not order_ref:
        await message.answer("Bunday ID li buyurtma topilmadi. Qaytadan tanlang:")
        return
    
    await state.update_data(order_id=order_id)
    
    info = f"🆔 Buyurtma: `{order_id}`\n"
    info += f"🧑 Diller: {order_ref.get('client_name')}\n"
    info += f"📦 Mebel: {order_ref.get('product_id')}\n"
    info += f"📊 Soni: {order_ref.get('amount')} ta\n"
    info += f"📅 Muddat: {format_date(order_ref.get('due_date', ''))}\n"
    created = order_ref.get('created_at', '')
    if created:
        info += f"📆 Yaratilgan: {format_date(created)}\n"
    if order_ref.get('comment') and str(order_ref.get('comment')).lower() != 'yoq':
        info += f"📝 Izoh: {order_ref.get('comment')}\n"
    info += f"📌 Holati: {order_ref.get('status')}\n"
    
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="❌ Bekor qilish"), types.KeyboardButton(text="✏️ O'zgartirish")],
            [types.KeyboardButton(text="Bosh menyu")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(f"{info}\nNima qilmoqchisiz?", reply_markup=markup, parse_mode="Markdown")
    await state.set_state(AdminOrderControlState.action)

@dp.message(AdminOrderControlState.action)
async def admin_order_action(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        await message.answer("Bosh menyu", reply_markup=main_menu('admin'))
        await state.clear()
        return
    
    data = await state.get_data()
    order_id = data['order_id']
    
    if message.text == "❌ Bekor qilish":
        order_ref = await asyncio.to_thread(db.reference(f'orders/{order_id}').get)
        if order_ref:
            # Omborga qaytarish
            product_id = order_ref.get('product_id')
            try:
                amount = int(order_ref.get('amount', 0))
            except:
                amount = 0
            
            if product_id and amount > 0:
                mebel_ref = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)
                if mebel_ref and 'soni' in mebel_ref:
                    new_qty = int(mebel_ref['soni']) + amount
                    await asyncio.to_thread(db.reference(f'mebellar/{product_id}').update, {'soni': new_qty})
            
            # ℹ️ Qarz O'ZGARTIRILMAYDI: mebel hali yetkazilmagan (Tayyorlanmoqda),
            # shuning uchun qarzga hech qachon qo'shilmagan. Yetkazilganda qarz qo'shiladi.
            
            # Buyurtmani bekor qilish
            await asyncio.to_thread(db.reference(f'orders/{order_id}').update, {'status': 'Bekor qilindi'})
        
        await message.answer(f"✅ Buyurtma `{order_id}` bekor qilindi!\n📦 Omborga qaytarildi.", reply_markup=main_menu('admin'), parse_mode="Markdown")
        
        # Omborchi, xodimlar va dillerga xabar
        cancel_client_name = order_ref.get('client_name', '') if order_ref else ''
        cancel_product = order_ref.get('product_id', '') if order_ref else ''
        cancel_amount = order_ref.get('amount', '') if order_ref else ''
        cancel_msg = (
            f"❌ *Buyurtma admin tomonidan bekor qilindi!*\n"
            f"🆔 ID: `{order_id}`\n"
            f"📦 Mebel: *{cancel_product}*\n"
            f"📊 Soni: *{cancel_amount} ta*\n"
            f"🧑 Diller: {cancel_client_name}"
        )
        users_ref = await asyncio.to_thread(db.reference('users').get)
        for user_id, user_data in (users_ref or {}).items():
            if not isinstance(user_data, dict):
                continue
            if user_data.get('role') in ['omborchi', 'ishchi', 'xodim']:
                try:
                    await bot.send_message(int(user_id), cancel_msg, parse_mode="Markdown")
                except:
                    pass
        # Hardcoded omborchi
        try:
            await bot.send_message(883589794, cancel_msg, parse_mode="Markdown")
        except:
            pass
        # Dillerga xabar yuborish
        diller_tg_ids = DILLER_TELEGRAM_MAP.get(cancel_client_name, [])
        for diller_tg_id in diller_tg_ids:
            try:
                await bot.send_message(
                    int(diller_tg_id),
                    f"❌ *Sizning buyurtmangiz bekor qilindi!*\n\n"
                    f"🆔 Buyurtma ID: `{order_id}`\n"
                    f"📦 Mebel: *{cancel_product}*\n"
                    f"📊 Soni: *{cancel_amount} ta*\n\n"
                    f"Batafsil ma'lumot uchun admin bilan bog'laning.",
                    parse_mode="Markdown"
                )
            except:
                pass
        
        await state.clear()
        return
    
    elif message.text == "✏️ O'zgartirish":
        markup = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="📊 Sonini o'zgartirish"), types.KeyboardButton(text="📅 Muddatni o'zgartirish")],
                [types.KeyboardButton(text="📝 Izohni o'zgartirish")],
                [types.KeyboardButton(text="Bosh menyu")]
            ],
            resize_keyboard=True
        )
        await message.answer("Nimani o'zgartirmoqchisiz?", reply_markup=markup)
        await state.set_state(AdminOrderControlState.edit_field)
        return
    
    await message.answer("Iltimos, tugmalardan foydalaning.")

@dp.message(AdminOrderControlState.edit_field)
async def admin_order_edit_field(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        await message.answer("Bosh menyu", reply_markup=main_menu('admin'))
        await state.clear()
        return
    
    field_map = {
        "📊 Sonini o'zgartirish": "amount",
        "📅 Muddatni o'zgartirish": "due_date",
        "📝 Izohni o'zgartirish": "comment"
    }
    
    field = field_map.get(message.text)
    if not field:
        await message.answer("Iltimos, tugmalardan foydalaning.")
        return
    
    await state.update_data(edit_field=field)
    
    if field == "amount":
        await message.answer("Yangi sonni kiriting (faqat raqam):", reply_markup=types.ReplyKeyboardRemove())
    elif field == "due_date":
        await message.answer("Yangi muddatni tanlang:", reply_markup=get_dates_keyboard())
    elif field == "comment":
        await message.answer("Yangi izohni kiriting:", reply_markup=types.ReplyKeyboardRemove())
    
    await state.set_state(AdminOrderControlState.new_value)

@dp.message(AdminOrderControlState.new_value)
async def admin_order_new_value(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        await message.answer("Bosh menyu", reply_markup=main_menu('admin'))
        await state.clear()
        return
    
    data = await state.get_data()
    order_id = data['order_id']
    field = data['edit_field']
    new_value = message.text
    
    if field == "amount":
        try:
            new_amount = int(new_value)
        except ValueError:
            await message.answer("Iltimos, faqat raqam kiriting:")
            return
        
        # Eski sonni olish va omborni tuzatish
        order_ref = await asyncio.to_thread(db.reference(f'orders/{order_id}').get)
        if order_ref:
            old_amount = int(order_ref.get('amount', 0))
            product_id = order_ref.get('product_id')
            diff = new_amount - old_amount
            
            # Omborni tuzatish
            if product_id:
                mebel_ref = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)
                if mebel_ref and 'soni' in mebel_ref:
                    new_qty = int(mebel_ref['soni']) - diff
                    await asyncio.to_thread(db.reference(f'mebellar/{product_id}').update, {'soni': new_qty})
            
            # ℹ️ Qarz O'ZGARTIRILMAYDI: mebel hali yetkazilmagan (Tayyorlanmoqda),
            # shuning uchun qarzga hech qachon qo'shilmagan. Yetkazilganda qarz qo'shiladi.
        
        await asyncio.to_thread(db.reference(f'orders/{order_id}').update, {'amount': str(new_amount)})
        await message.answer(f"✅ Buyurtma `{order_id}` soni {new_amount} taga o'zgartirildi!", reply_markup=main_menu('admin'), parse_mode="Markdown")
    
    elif field == "due_date":
        await asyncio.to_thread(db.reference(f'orders/{order_id}').update, {'due_date': new_value})
        await message.answer(f"✅ Buyurtma `{order_id}` muddati {new_value} ga o'zgartirildi!", reply_markup=main_menu('admin'), parse_mode="Markdown")
    
    elif field == "comment":
        await asyncio.to_thread(db.reference(f'orders/{order_id}').update, {'comment': new_value})
        await message.answer(f"✅ Buyurtma `{order_id}` izohi o'zgartirildi!", reply_markup=main_menu('admin'), parse_mode="Markdown")
    
    # Omborchi va xodimlarga xabar
    order_ref = await asyncio.to_thread(db.reference(f'orders/{order_id}').get)
    users_ref = await asyncio.to_thread(db.reference('users').get)
    field_names = {'amount': 'Soni', 'due_date': 'Muddati', 'comment': 'Izohi'}
    for user_id, user_data in (users_ref or {}).items():
        if user_data.get('role') in ['omborchi', 'ishchi', 'xodim']:
            try:
                await bot.send_message(
                    int(user_id),
                    f"✏️ Buyurtma o'zgartirildi!\n🆔 ID: {order_id}\n📦 {order_ref.get('product_id')}\n🧑 Diller: {order_ref.get('client_name')}\n🔄 {field_names.get(field, field)}: {new_value}"
                )
            except:
                pass
    try:
        await bot.send_message(883589794, f"✏️ Buyurtma o'zgartirildi!\n🆔 ID: {order_id}\n📦 {order_ref.get('product_id')}\n🧑 Diller: {order_ref.get('client_name')}\n🔄 {field_names.get(field, field)}: {new_value}")
    except:
        pass

    # Dillerga o'zgartirish haqida xabar va tasdiqlash tugmalari
    client_name = order_ref.get('client_name', '') if order_ref else ''
    diller_ids = DILLER_TELEGRAM_MAP.get(client_name, [])
    if diller_ids:
        field_name_uz = field_names.get(field, field)
        if field == 'due_date':
            new_val_display = format_date(new_value)
        else:
            new_val_display = new_value
        # Narxni hisoblash
        price_val = order_ref.get('price', 0) if order_ref else 0
        amount_val = order_ref.get('amount', 1) if order_ref else 1
        try:
            total = int(price_val) * int(amount_val)
            total_str = f"{total:,} so'm".replace(',', ' ')
            price_str = f"{int(price_val):,} so'm".replace(',', ' ')
        except:
            total_str = "Ko'rsatilmagan"
            price_str = "Ko'rsatilmagan"
        inline_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"diller_confirm:{order_id}"),
                types.InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"diller_reject:{order_id}")
            ]
        ])
        change_text = (
            f"⚠️ *Buyurtmangizda o'zgartirish!*\n\n"
            f"🆔 Buyurtma ID: `{order_id}`\n"
            f"📦 Mebel: *{order_ref.get('product_id', '?') if order_ref else '?'}*\n"
            f"🔄 O'zgartirilgan: *{field_name_uz}* → `{new_val_display}`\n"
            f"💰 Narxi (1 dona): *{price_str}*\n"
            f"💵 Jami narx: *{total_str}*\n"
            f"📅 Muddat: *{format_date(order_ref.get('due_date', '?') if order_ref else '?')}*\n\n"
            f"❓ Siz uchun qabulmi?"
        )
        for tg_id in diller_ids:
            try:
                await bot.send_message(tg_id, change_text, reply_markup=inline_kb, parse_mode="Markdown")
            except Exception as e:
                print(f"Dillerga o'zgartirish xabari yuborishda xatolik ({tg_id}): {e}")

    await state.clear()


# --- DILLER: O'ZGARTISHNI TASDIQLASH / BEKOR QILISH ---
@dp.callback_query(F.data.startswith("diller_confirm:"))
async def diller_confirm_change(callback: types.CallbackQuery):
    order_id = callback.data.split(":", 1)[1]
    role = await get_user_role(callback.from_user.id)
    if role not in ['diller', 'xodim', 'ishchi']:
        await callback.answer("Sizda bu amalni bajarish huquqi yo'q.", show_alert=True)
        return
    # Tugmalarni o'chirish
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    await callback.message.answer(
        f"✅ *O'zgarish tasdiqlandi!*\n🆔 Buyurtma ID: `{order_id}`\n\nRahmat! Admin xabardor qilindi.",
        parse_mode="Markdown"
    )
    # Adminga xabar
    users_ref = await asyncio.to_thread(db.reference('users').get)
    notify_text = f"✅ Diller o'zgarishni *TASDIQLADI*\n🆔 Buyurtma ID: `{order_id}`"
    for uid, udata in (users_ref or {}).items():
        if isinstance(udata, dict) and udata.get('role') == 'admin':
            try:
                await bot.send_message(int(uid), notify_text, parse_mode="Markdown")
            except:
                pass
    await callback.answer()

@dp.callback_query(F.data.startswith("diller_reject:"))
async def diller_reject_change(callback: types.CallbackQuery):
    order_id = callback.data.split(":", 1)[1]
    role = await get_user_role(callback.from_user.id)
    if role not in ['diller', 'xodim', 'ishchi']:
        await callback.answer("Sizda bu amalni bajarish huquqi yo'q.", show_alert=True)
        return
    # Tugmalarni o'chirish
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    await callback.message.answer(
        f"❌ *O'zgarish rad etildi!*\n🆔 Buyurtma ID: `{order_id}`\n\nAdmin xabardor qilindi.",
        parse_mode="Markdown"
    )
    # Adminga xabar
    users_ref = await asyncio.to_thread(db.reference('users').get)
    notify_text = f"❌ Diller o'zgarishni *RAD ETDI*\n🆔 Buyurtma ID: `{order_id}`\nIltimos, diller bilan bog'laning!"
    for uid, udata in (users_ref or {}).items():
        if isinstance(udata, dict) and udata.get('role') == 'admin':
            try:
                await bot.send_message(int(uid), notify_text, parse_mode="Markdown")
            except:
                pass
    await callback.answer()

@dp.message(StateFilter(None))
async def fallback_handler(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    await state.clear()
    await message.answer("Noto'g'ri buyruq yoki tushunarsiz matn kiritildi.\nIltimos, pastdagi tugmalardan foydalaning.", reply_markup=main_menu(role))

async def handle(request):
    return web.Response(text="Bot is running")

async def check_and_mark_reminder(reminder_type: str) -> bool:
    """Firebase da bugun ushbu eslatma yuborilganligini tekshiradi.
    Yuborilmagan bo'lsa True qaytaradi va belgilab qo'yadi.
    Yuborilgan bo'lsa False qaytaradi (duplicate oldini olish)."""
    today_str = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d")
    ref_path = f"reminder_sent/{today_str}/{reminder_type}"
    already_sent = await asyncio.to_thread(db.reference(ref_path).get)
    if already_sent:
        logging.info(f"[Reminder] {reminder_type} bugun allaqachon yuborilgan, o'tkazib yuborildi.")
        return False
    await asyncio.to_thread(db.reference(ref_path).set, True)
    return True

async def handle_morning_cron(request):
    token = request.query.get('token')
    if not token or token != API_TOKEN:
        return web.Response(text="Unauthorized", status=403)
    try:
        if await check_and_mark_reminder('morning'):
            await send_morning_reminder()
            return web.Response(text="Morning reminder sent")
        return web.Response(text="Morning reminder already sent today")
    except Exception as e:
        logging.error(f"Cron morning error: {e}")
        return web.Response(text=f"Error: {e}", status=500)

async def handle_overdue_cron(request):
    token = request.query.get('token')
    if not token or token != API_TOKEN:
        return web.Response(text="Unauthorized", status=403)
    try:
        if await check_and_mark_reminder('overdue'):
            await send_overdue_reminder()
            return web.Response(text="Overdue reminder sent")
        return web.Response(text="Overdue reminder already sent today")
    except Exception as e:
        logging.error(f"Cron overdue error: {e}")
        return web.Response(text=f"Error: {e}", status=500)

async def handle_tomorrow_cron(request):
    token = request.query.get('token')
    if not token or token != API_TOKEN:
        return web.Response(text="Unauthorized", status=403)
    try:
        if await check_and_mark_reminder('tomorrow'):
            await send_tomorrow_reminder()
            return web.Response(text="Tomorrow reminder sent")
        return web.Response(text="Tomorrow reminder already sent today")
    except Exception as e:
        logging.error(f"Cron tomorrow error: {e}")
        return web.Response(text=f"Error: {e}", status=500)

async def keep_awake():
    url = "https://mmebel-bot.onrender.com"
    while True:
        await asyncio.sleep(600)  # 10 daqiqa
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    pass
        except Exception:
            pass

async def daily_reminder_task():
    """Kuniga 3 marta eslatma yuborish:
    - 09:00 — ertalabki (yetkazilmagan mebellar)
    - 15:00 — tushki (yetkazilmagan mebellar)
    - 15:05 — ertangi zakazlar ro'yxati
    Firebase orqali duplicate yuborishdan himoyalangan.
    """
    while True:
        now = datetime.now(TASHKENT_TZ)

        # 09:00 da ertalabki eslatma
        if now.hour == 9 and now.minute == 0:
            try:
                if await check_and_mark_reminder('morning'):
                    await send_morning_reminder()
                    logging.info("[Scheduler] Morning reminder sent.")
            except Exception as e:
                logging.error(f"[Scheduler] Morning xato: {e}")

        # 15:00 da tushki eslatma
        if now.hour == 15 and now.minute == 0:
            try:
                if await check_and_mark_reminder('overdue'):
                    await send_overdue_reminder()
                    logging.info("[Scheduler] Overdue reminder sent.")
            except Exception as e:
                logging.error(f"[Scheduler] Overdue xato: {e}")

        # 15:05 da ertangi zakazlar
        if now.hour == 15 and now.minute == 5:
            try:
                if await check_and_mark_reminder('tomorrow'):
                    await send_tomorrow_reminder()
                    logging.info("[Scheduler] Tomorrow reminder sent.")
            except Exception as e:
                logging.error(f"[Scheduler] Tomorrow xato: {e}")

        # Har 30 soniyada tekshirish (aniq vaqtda yuborish uchun)
        await asyncio.sleep(30)

async def daily_backup_task():
    import json
    import os
    from aiogram.types import FSInputFile
    while True:
        now = datetime.now(TASHKENT_TZ)
        target = now.replace(hour=23, minute=59, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
            
        sleep_seconds = (target - now).total_seconds()
        await asyncio.sleep(sleep_seconds)
        
        try:
            db_data = await asyncio.to_thread(db.reference('/').get)
            if db_data:
                backup_filename = f"backup_{datetime.now(TASHKENT_TZ).strftime('%Y%m%d_%H%M%S')}.json"
                with open(backup_filename, 'w', encoding='utf-8') as f:
                    json.dump(db_data, f, ensure_ascii=False, indent=4)
                
                users_ref = await asyncio.to_thread(db.reference('users').get)
                admin_ids = []
                if users_ref:
                    for uid, udata in users_ref.items():
                        if isinstance(udata, dict) and udata.get('role') == 'admin':
                            admin_ids.append(uid)
                
                for admin_id in admin_ids:
                    try:
                        file = FSInputFile(backup_filename)
                        await bot.send_document(
                            chat_id=int(admin_id), 
                            document=file, 
                            caption="📁 Baza zaxira nusxasi (Kunlik avtomatik backup)\n\nUshbu faylni ehtiyot qilib saqlang. Agar baza o'chib ketsa, shu fayl orqali qayta tiklasa bo'ladi."
                        )
                    except Exception as e:
                        print(f"Error sending backup to {admin_id}: {e}")
                
                if os.path.exists(backup_filename):
                    os.remove(backup_filename)
        except Exception as e:
            print(f"Backup task error: {e}")

WEBHOOK_PATH = f"/webhook"
WEBHOOK_URL = f"https://mmebel-bot.onrender.com{WEBHOOK_PATH}"

async def main():
    # Eski polling yangilanishlarini o'chirish va webhookni o'rnatish
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    
    app = web.Application()
    app.router.add_get('/', handle)
    app.router.add_get('/cron/morning', handle_morning_cron)
    app.router.add_get('/cron/overdue', handle_overdue_cron)
    app.router.add_get('/cron/tomorrow', handle_tomorrow_cron)
    
    # Webhook so'rovlarini qabul qiluvchi handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # Uygotgichni fonga ishga tushirish
    asyncio.create_task(keep_awake())
    
    # Kunlik eslatmani fonga ishga tushirish
    asyncio.create_task(daily_reminder_task())
    
    # Avtomatik backupni fonga ishga tushirish
    asyncio.create_task(daily_backup_task())
    
    # Dastur doimiy ishlashi uchun cheksiz kutish
    await asyncio.Event().wait()

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())