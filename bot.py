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
    "Zoʻr mebel", "Umid", "Akmal aka", "Doʻkon 707", "Farxod Jomiy", "Munosib Mebel", "Islom aka", "Muxtor aka"
]

def get_clients_keyboard():
    buttons = []
    for i in range(0, len(REGULAR_CLIENTS), 2):
        row = [types.KeyboardButton(text=REGULAR_CLIENTS[i])]
        if i+1 < len(REGULAR_CLIENTS):
            row.append(types.KeyboardButton(text=REGULAR_CLIENTS[i+1]))
        buttons.append(row)
    buttons.append([types.KeyboardButton(text="Boshqa (Yangi mijoz)")])
    buttons.append([types.KeyboardButton(text="Bosh menyu")])
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

FAVORITE_MODELS = [
    "BF 06", "BF 07", "BF 09", 
    "BF 12", "BF 14", "BF 15", "BF 18",
    "BF 244", "BF 264", "BF 274", "BF 294",
    "BF 246", "BF 266", "BF 276", "BF 296",
    "BF 2761", "BF 2961",
    "BF SH 2761", "BF SH 2961",
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
    comment = State()         # Izoh
    phone = State()           # Telefon raqam

# 4. Rollarni Tekshirish (RTDB dan)
async def get_user_role(user_id):
    user_id_str = str(user_id)
    if user_id_str == '883589794':
        return 'omborchi'
    if user_id_str in ['6298036669', '1349256808', '7062569902', '7941658592', '1724350130', '698145797', '5063420475']:
        return 'xodim'
    if user_id_str in ['261261387']:
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
            [types.KeyboardButton(text="📋 Buyurtmalar nazorati"), types.KeyboardButton(text="📊 Mijozlar hisoboti")],
            [types.KeyboardButton(text="🚚 Haydovchilar hisoboti")],
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
            [types.KeyboardButton(text="🛍 Sotuvdagi mebellar"), types.KeyboardButton(text="📝 Zakaz berish")]
        ]
    else:
        buttons = [
            [types.KeyboardButton(text="🛍 Sotuvdagi mebellar")]
        ]
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- BOSH MENYU / BEKOR QILISH ---
MAIN_MENU_BUTTONS = {
    "Bosh menyu", "➕ Yangi mebel", "📦 Mavjud mebellar", 
    "📝 Yangi buyurtma", "📋 Buyurtmalar nazorati", "📊 Mijozlar hisoboti", "🚚 Haydovchilar hisoboti", "🕰 Yetkazish tarixi", "📈 Sotuv statistikasi",
    "🔄 Omborni yangilash", "🚚 Yetkazishlar nazorati", "📊 Dostavka hisoboti", "🔨 Faol buyurtmalar", "🛍 Sotuvdagi mebellar",
    "📦 Ombor sonini yangilash", "📝 Zakaz berish"
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
    await message.answer("Narxini kiriting (so'mda):")
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
    result_text = f"✅ Mebel qo'shildi!\n🆔 ID: `{p_id}`\n🪑 Nomi: {data['name']}\n📦 Modeli: {data['model']}\n💰 Narxi: {data['price']} so'm\n📦 Soni: {data['quantity']} ta"
    
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

    await state.update_data(due_date=message.text)
    await message.answer(
        "📝 Izoh kiriting (masalan: rang, o'lcham, yetkazib berish manzili).\n"
        "Agar izoh bo'lmasa 'yoq' deb yozing:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(DillerOrderState.comment)

@dp.message(DillerOrderState.comment)
async def diller_order_comment(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await state.clear()
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        return

    await state.update_data(comment=message.text)
    
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📞 Raqamni yuborish", request_contact=True)],
            [types.KeyboardButton(text="Bosh menyu")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "📱 Iltimos, telefon raqamingizni yuboring (pastdagi tugmani bosing yoki yozing):",
        reply_markup=markup
    )
    await state.set_state(DillerOrderState.phone)

@dp.message(DillerOrderState.phone)
async def diller_order_phone(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await state.clear()
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        return

    phone = ""
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text

    data = await state.get_data()
    product_id   = data['product_id']
    product_name = data.get('product_name', product_id)
    amount       = data['amount']
    due_date     = data['due_date']
    comment      = data['comment']

    # Telegram user info
    user = message.from_user
    client_name = user.full_name or user.username or str(user.id)

    order_id = f"{product_id}-{str(uuid.uuid4())[:4].upper()}"
    now_str  = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
    month    = datetime.now(TASHKENT_TZ).strftime("%Y-%m")

    # Ombordan ayirish
    mebel_ref = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)
    if mebel_ref:
        current_qty = int(mebel_ref.get('soni', 0))
        new_qty = max(0, current_qty - amount)
        await asyncio.to_thread(db.reference(f'mebellar/{product_id}').update, {'soni': new_qty})

    # Firebase'ga yozish
    await asyncio.to_thread(
        db.reference(f'orders/{order_id}').set,
        {
            'order_id':    order_id,
            'client_name': client_name,
            'client_tg_id': str(user.id),
            'client_phone': phone,
            'product_id':  product_id,
            'amount':      str(amount),
            'due_date':    due_date,
            'comment':     comment,
            'status':      'Tayyorlanmoqda',
            'created_at':  now_str,
            'month':       month,
            'source':      'diller'
        }
    )

    role = await get_user_role(message.from_user.id)
    await message.answer(
        f"✅ Zakaz qabul qilindi!\n"
        f"🆔 ID: `{order_id}`\n"
        f"📦 Mebel: {product_name} — {amount} ta\n"
        f"📅 Muddat: {format_date(due_date)}\n"
        f"📝 Izoh: {comment}\n"
        f"📱 Telefon: {phone}",
        parse_mode="Markdown",
        reply_markup=main_menu(role)
    )
    await state.clear()

    # Admin va omborchiga xabar
    notify_text = (
        f"🔔 *Yangi zakaz (dillerdan)!*\n\n"
        f"👤 Mijoz: {client_name} (TG: {user.id})\n"
        f"📱 Telefon: {phone}\n"
        f"📦 Mebel: {product_name} — {amount} ta\n"
        f"📅 Muddat: {format_date(due_date)}\n"
        f"📝 Izoh: {comment}\n"
        f"🆔 ID: `{order_id}`"
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

# --- ADMIN: YANGI BUYURTMA YOZISH ---
@dp.message(F.text == "📝 Yangi buyurtma")
async def new_order_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'admin':
        await message.answer("Mijozni tanlang yoki 'Boshqa' ni bosing:", reply_markup=get_clients_keyboard())
        await state.set_state(OrderState.client)

@dp.message(OrderState.client)
async def process_client(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return

    if message.text == "Boshqa (Yangi mijoz)":
        await message.answer("Yangi mijoz ismini kiriting:", reply_markup=types.ReplyKeyboardRemove())
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
    
    # Mijoz qarzini hisoblash va tarixga yozish
    if total_price > 0:
        debt_ref = await asyncio.to_thread(db.reference(f'debts/{client_name}').get)
        current_debt = int(debt_ref) if debt_ref else 0
        new_debt = current_debt + total_price
        await asyncio.to_thread(db.reference(f'debts/{client_name}').set, new_debt)
        
        timestamp = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
        record = {'type': 'Chiqim', 'amount': total_price, 'timestamp': timestamp, 'note': f"Buyurtma qildi: {product_id} ({amount} ta)"}
        await asyncio.to_thread(db.reference(f'transactions/clients/{client_name}').push, record)

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
            'created_at': datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            'month': datetime.now(TASHKENT_TZ).strftime("%Y-%m")
        }
    )
    
    await message.answer(f"✅ Buyurtma qabul qilindi!\n🆔 ID: {order_id}\n📅 Muddat: {format_date(data['due_date'])}\n📝 Izoh: {comment}")
    data['comment'] = comment
    await state.clear()
    
    # Omborchiga xabar yuborish
    await notify_warehouse(data, order_id)

# --- ADMIN: MIJOZLAR HISOBOTI VA QARZ ---
class ReportState(StatesGroup):
    select_client = State()

@dp.message(F.text == "📊 Mijozlar hisoboti")
async def report_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'admin':
        await message.answer("Qaysi mijozning hisobotini ko'rmoqchisiz?", reply_markup=get_clients_keyboard())
        await state.set_state(ReportState.select_client)

@dp.message(ReportState.select_client)
async def show_client_report(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        role = await get_user_role(message.from_user.id)
        await message.answer("Bosh menyu", reply_markup=main_menu(role))
        await state.clear()
        return
        
    client_name = message.text
    if client_name == "Boshqa (Yangi mijoz)":
        await message.answer("Faqat doimiy mijozlar hisoboti mavjud.")
        return

    try:
        # Fetch orders, debt, deliveries and mebellar
        orders_ref = await asyncio.to_thread(db.reference('orders').get)
        debt_ref = await asyncio.to_thread(db.reference(f'debts/{client_name}').get)
        mebellar_ref = await asyncio.to_thread(db.reference('mebellar').get)
        
        current_debt = debt_ref if debt_ref is not None else 0
        
        # Barcha oylar uchun yetkazishlarni olish
        all_deliveries_ref = await asyncio.to_thread(db.reference('deliveries').get)
        deliveries_map = {}  # order_id -> delivery data
        if all_deliveries_ref and isinstance(all_deliveries_ref, dict):
            for month_key, month_data in all_deliveries_ref.items():
                if isinstance(month_data, dict):
                    for d_id, d in month_data.items():
                        if isinstance(d, dict) and d.get('order_id'):
                            deliveries_map[d.get('order_id')] = d
        
        try:
            debt_formatted = f"{int(current_debt):,}".replace(",", " ")
        except Exception:
            debt_formatted = str(current_debt)
        
        # Buyurtmalarni ajratish: tayyorlanmoqda va yetkazilgan
        pending_orders = []  # Hali olib ketilmagan
        delivered_orders = []  # Olib ketilgan
        
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
                                status_text = "Mijozni o'zi olib ketdi"
                            elif driver:
                                status_text = f"Yetkazildi ({driver})"
                            else:
                                status_text = status
                            
                            delivered_orders.append({
                                'o_id': o_id,
                                'product_id': product_id,
                                'amount': amount,
                                'status_text': status_text,
                                'delivered_at': d_date,
                                'price': price_text,
                                'delivery_price': delivery_price,
                                'created_at': o.get('created_at', '')
                            })
        
        # Delivered orders ni sanasi bo'yicha saralash (oxirgi birinchi)
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
        
        # Hisobot tayyorlash
        report = f"👤 Mijoz: {client_name}\n"
        report += f"💳 Joriy qarzi: {debt_formatted} 💰\n\n"
        
        # 1. Olib ketilmagan (tayyorlanmoqda) mebellar
        if pending_orders:
            report += "⏳Buyurtma berilgan, lekin olib ketilmagan mebellar ro'yxati:\n"
            for po in pending_orders:
                safe_pid = str(po['product_id']).replace('`', '').replace('*', '')
                status_label = "Tayyor" if po['status'] == "Tayyor bo'ldi" else "Tayyorlanmoqda"
                report += f"▪️ {safe_pid} — {po['amount']} ta ({status_label})\n"
                report += f"   📅 {po['due_date']}\n"
                if po['price']:
                    report += f"   {po['price']}💰\n"
                if po.get('comment') and str(po.get('comment')).lower() != 'yoq':
                    report += f"   📝 {po['comment']}\n"
            report += "\n"
        
        # 2. Olingan mebellar tarixi
        report += "📦 Olingan mebellar tarixi:\n"
        if delivered_orders:
            displayed = delivered_orders[:50]
            if len(delivered_orders) > 50:
                report += f"_(Jami {len(delivered_orders)} ta — oxirgi 50 tasi ko'rsatilmoqda)_\n"
            
            for do in displayed:
                safe_pid = str(do['product_id']).replace('`', '').replace('*', '')
                report += f"▪️ {safe_pid} — {do['amount']} ta ({do['status_text']}) 🚛 {do['delivered_at']}\n"
                if do['price']:
                    report += f"   {do['price']}💰\n"
        else:
            report += "Hech qanday mebel olinmagan.\n"
        
        markup = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text=f"➕ {client_name} dan Pul Olish (Kirim)")],
                [types.KeyboardButton(text=f"➖ {client_name} ga Pul Berish (Chiqim)")],
                [types.KeyboardButton(text=f"📜 {client_name} To'lovlar Tarixi")],
                [types.KeyboardButton(text="Bosh menyu")]
            ],
            resize_keyboard=True
        )
        
        # Xabarni bo'laklarga bo'lib yuborish
        chunks = []
        current_msg = ""
        for line in report.split("\n"):
            if len(current_msg) + len(line) + 1 > 3800:
                chunks.append(current_msg)
                current_msg = line + "\n"
            else:
                current_msg += line + "\n"
        if current_msg:
            chunks.append(current_msg)
        
        for i, chunk in enumerate(chunks):
            is_last = (i == len(chunks) - 1)
            try:
                await message.answer(
                    chunk,
                    parse_mode="Markdown",
                    reply_markup=markup if is_last else None
                )
            except Exception:
                await message.answer(
                    chunk,
                    reply_markup=markup if is_last else None
                )
        
        # 💵 Dollar stikeri yuborish
        try:
            await bot.send_sticker(
                chat_id=message.chat.id,
                sticker="CAACAgIAAxkBAAEBjGRoJ3YXSZ4AAeJE5gVF2gJfdWpB8QACWAADr8ZRGvrHuZ6K-cGINgQ"
            )
        except Exception:
            pass
        
        await state.clear()
        
    except Exception as e:
        logging.error(f"Client report error: {e}")
        await message.answer(f"Hisobot tayyorlashda xatolik yuz berdi: {e}")
        await state.clear()

@dp.message(F.text.contains("dan Pul Olish (Kirim)"))
async def client_kirim_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'admin':
        client_name = message.text.replace("➕ ", "").replace(" dan Pul Olish (Kirim)", "").strip()
        await state.update_data(client_name=client_name)
        await message.answer(f"👤 {client_name} dan olingan pul summasini kiriting (faqat raqam):", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(FinanceState.amount_kirim)

@dp.message(FinanceState.amount_kirim)
async def process_client_kirim(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client_name = data['client_name']
    try:
        amount = int(message.text)
        # Qarzni kamaytirish
        debt_ref = await asyncio.to_thread(db.reference(f'debts/{client_name}').get)
        current_debt = debt_ref if debt_ref is not None else 0
        new_debt = current_debt - amount
        await asyncio.to_thread(db.reference(f'debts/{client_name}').set, new_debt)
        
        # Tarixga yozish
        timestamp = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
        record = {'type': 'Kirim', 'amount': amount, 'timestamp': timestamp, 'note': "Mijoz pul berdi"}
        await asyncio.to_thread(db.reference(f'transactions/clients/{client_name}').push, record)
        
        await message.answer(f"✅ {client_name} dan {amount} so'm qabul qilindi.\n💳 Yangi qarzi: {new_debt} so'm", reply_markup=main_menu('admin'))
        await state.clear()
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting:")

@dp.message(F.text.contains("ga Pul Berish (Chiqim)"))
async def client_chiqim_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'admin':
        client_name = message.text.replace("➖ ", "").replace(" ga Pul Berish (Chiqim)", "").strip()
        await state.update_data(client_name=client_name)
        await message.answer(f"👤 {client_name} ga qarz sifatida yoziladigan yoki qaytariladigan pul summasini kiriting (faqat raqam):", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(FinanceState.amount_chiqim)

@dp.message(FinanceState.amount_chiqim)
async def process_client_chiqim(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client_name = data['client_name']
    try:
        amount = int(message.text)
        # Qarzni ko'paytirish
        debt_ref = await asyncio.to_thread(db.reference(f'debts/{client_name}').get)
        current_debt = debt_ref if debt_ref is not None else 0
        new_debt = current_debt + amount
        await asyncio.to_thread(db.reference(f'debts/{client_name}').set, new_debt)
        
        # Tarixga yozish
        timestamp = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
        record = {'type': 'Chiqim', 'amount': amount, 'timestamp': timestamp, 'note': "Mijoz qarzi ko'paydi"}
        await asyncio.to_thread(db.reference(f'transactions/clients/{client_name}').push, record)
        
        await message.answer(f"✅ {client_name} qarziga {amount} so'm qo'shildi.\n💳 Yangi qarzi: {new_debt} so'm", reply_markup=main_menu('admin'))
        await state.clear()
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting:")

@dp.message(F.text.contains("To'lovlar Tarixi"))
async def client_history(message: types.Message):
    if await get_user_role(message.from_user.id) == 'admin':
        client_name = message.text.replace("📜 ", "").replace(" To'lovlar Tarixi", "").strip()
        trans_ref = await asyncio.to_thread(db.reference(f'transactions/clients/{client_name}').get)
        if not trans_ref:
            await message.answer(f"👤 {client_name} bo'yicha to'lovlar tarixi yo'q.")
            return
        
        header = f"📜 **{client_name} to'lovlar (Kirim/Chiqim) tarixi:**\n\n"
        items = []
        for t_id, t in trans_ref.items():
            if isinstance(t, dict):
                icon = "🟢" if t.get('type') == 'Kirim' else "🔴"
                entry = f"{icon} {t.get('type')}: {t.get('amount')} so'm\n"
                entry += f"📅 Sana: {format_date(t.get('timestamp', ''))}\n"
                note = t.get('note', '')
                if note:
                    entry += f"📝 {note}\n"
                entry += "\n"
                items.append(entry)
        
        # Build chunks at item boundaries (max 3800 chars)
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
            f"🧑 Mijoz: {order_data['client']}\n"
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
                    f"🧑 Mijoz: {order_data['client']}\n"
                    f"📦 Mebel: {order_data['product_id']}\n"
                    f"📊 Soni: {order_data['amount']}\n"
                    f"📅 Muddat: {order_data['due_date']}\n"
                    f"📝 Izoh: {order_data.get('comment', 'Yoq')}\n"
                    f"🆔 Buyurtma ID: {order_id}"
                )
            except Exception as e:
                print(f"Xodimga xabar yuborishda xatolik: {e}")

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
    for user_id in users_to_notify:
        try:
            await bot.send_message(chat_id=int(user_id), text=msg, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Error sending reminder to {user_id}: {e}")

async def send_morning_reminder():
    """9:00 - Bugungacha bo'lgan barcha faol zakazlar"""
    now_uz = datetime.now(TASHKENT_TZ)
    today = now_uz.replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = now_uz.strftime("%d.%m.%Y")
    
    orders_ref = await asyncio.to_thread(db.reference('orders').get)
    if not orders_ref:
        return
    
    overdue_orders = []
    for o_id, o in orders_ref.items():
        if isinstance(o, dict) and o.get('status') == 'Tayyorlanmoqda':
            due = parse_order_date(o.get('due_date', ''))
            if due and due <= today:
                overdue_orders.append((o_id, o, due))
    
    if not overdue_orders:
        return
    
    overdue_orders.sort(key=lambda x: x[2])
    
    msg = f"🔔 **ERTALABKI ESLATMA** ({today_str})\n\n"
    msg += f"📋 Bugungacha tayyor bo'lishi kerak bo'lgan zakazlar:\n\n"
    
    for i, (o_id, o, due) in enumerate(overdue_orders, 1):
        due_formatted = format_date(o.get('due_date', ''))
        msg += f"{i}. 👤 **{o.get('client_name')}** - 📦 {o.get('product_id')} ({o.get('amount')} ta)\n"
        msg += f"   📅 Muddat: {due_formatted}\n"
        if o.get('comment') and str(o.get('comment')).lower() != 'yoq':
            msg += f"   📝 Izoh: {o.get('comment')}\n"
        msg += "\n"
    
    await send_notification(msg)

async def send_overdue_reminder():
    """15:00 - Bugungacha berib ulgurmagan mebellar ro'yxati"""
    now_uz = datetime.now(TASHKENT_TZ)
    today = now_uz.replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = now_uz.strftime("%d.%m.%Y")
    
    orders_ref = await asyncio.to_thread(db.reference('orders').get)
    if not orders_ref:
        return
    
    overdue_orders = []
    for o_id, o in orders_ref.items():
        if isinstance(o, dict) and o.get('status') == 'Tayyorlanmoqda':
            due = parse_order_date(o.get('due_date', ''))
            if due and due <= today:
                overdue_orders.append((o_id, o, due))
    
    if not overdue_orders:
        return
    
    overdue_orders.sort(key=lambda x: x[2])
    
    msg = f"🔴 🔴 🔴 **DIQQAT! BUGUNGACHA YETKAZILMAGAN ZAKAZLAR** 🔴 🔴 🔴\n\n"
    msg += f"📅 Bugun: {today_str}\n\n"
    msg += "Quyidagi mebellarni tayyorlab berishimiz kerak:\n\n"
    
    for i, (o_id, o, due) in enumerate(overdue_orders, 1):
        due_formatted = format_date(o.get('due_date', ''))
        msg += f"{i}. 👤 **{o.get('client_name')}** - 📦 {o.get('product_id')} ({o.get('amount')} ta)\n"
        msg += f"   📅 Muddat: {due_formatted}\n"
        if o.get('comment') and str(o.get('comment')).lower() != 'yoq':
            msg += f"   📝 Izoh: {o.get('comment')}\n"
        msg += "\n"
    
    await send_notification(msg)

async def send_tomorrow_reminder():
    """15:05 - Ertangi zakazlar ro'yxati"""
    now_uz = datetime.now(TASHKENT_TZ)
    tomorrow = (now_uz + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_str = (now_uz + timedelta(days=1)).strftime("%d.%m.%Y")
    
    orders_ref = await asyncio.to_thread(db.reference('orders').get)
    if not orders_ref:
        return
    
    tomorrow_orders = []
    for o_id, o in orders_ref.items():
        if isinstance(o, dict) and o.get('status') == 'Tayyorlanmoqda':
            due = parse_order_date(o.get('due_date', ''))
            if due and due.year == tomorrow.year and due.month == tomorrow.month and due.day == tomorrow.day:
                tomorrow_orders.append((o_id, o))
    
    if not tomorrow_orders:
        return
    
    msg = f"📢 **ERTANGI ZAKAZLAR** ({tomorrow_str})\n\n"
    msg += f"Ertaga yetkazishimiz kerak bo'lgan mebellar:\n\n"
    
    for i, (o_id, o) in enumerate(tomorrow_orders, 1):
        msg += f"{i}. 👤 **{o.get('client_name')}** - 📦 {o.get('product_id')} ({o.get('amount')} ta)\n"
        if o.get('comment') and str(o.get('comment')).lower() != 'yoq':
            msg += f"   📝 Izoh: {o.get('comment')}\n"
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
                    if order_month == selected_month and order_status in ["Biz yetkazib berdik", "Mijozni o'zi olib ketdi"]:
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
            sums.append(f"{total_sum_uzs:,} so'm".replace(",", " "))
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

    order_report_items = []
    buttons = []
    row = []
    
    for d_str in sorted_dates:
        # Sarlavha tayyorlash
        try:
            dt = datetime.strptime(d_str, "%d.%m.%Y")
            header = f"✅ **{dt.day} {UZ_MONTHS[dt.month]} {UZ_WEEKDAYS[dt.weekday()]}**"
        except:
            header = f"✅ **{d_str}**"
        
        day_text = f"{header}\n\n"
        for o_id, o in grouped[d_str]:
            day_text += f"🆔 `{o_id}` - 🧑 {o.get('client_name')}\n"
            day_text += f"📦 Mebel: {o.get('product_id')} ({o.get('amount')} ta)\n"
            if o.get('comment') and str(o.get('comment')).lower() != 'yoq':
                day_text += f"📝 Izoh: {o.get('comment')}\n"
            day_text += f"📌 Holati: {o.get('status')}\n"
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
    
    # Xabarlarni yuborish
    current_msg = "🚚 **Faol buyurtmalar:**\n\n"
    for i, part in enumerate(order_report_items):
        if len(current_msg) + len(part) > 3800:
            await message.answer(current_msg, parse_mode="Markdown")
            current_msg = part + "\n"
        else:
            current_msg += part + "\n"
            
    prompt = "Qaysi buyurtmaning holatini o'zgartirmoqchisiz? Buyurtma ID-sini tanlang:"
    if len(current_msg) + len(prompt) > 4000:
        await message.answer(current_msg, parse_mode="Markdown")
        await message.answer(prompt, reply_markup=markup, parse_mode="Markdown")
    else:
        await message.answer(current_msg + prompt, reply_markup=markup, parse_mode="Markdown")

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
            [types.KeyboardButton(text="Mijozni o'zi olib ketdi"), types.KeyboardButton(text="Bekor qilindi")],
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
        product_id = order_ref.get('product_id', 'Noma\'lum') if order_ref else 'Noma\'lum'
        amount = order_ref.get('amount', 1) if order_ref else 1
        
        for user_id, user_data in (users_ref or {}).items():
            if user_data.get('role') == 'admin':
                try:
                    await bot.send_message(
                        int(user_id),
                        f"📦 **Buyurtma holati o'zgardi!**\n\n🆔 ID: `{data['order_id']}`\n🧑 Mijoz: {data['client']}\n📌 Yangi holat: {new_status}",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            elif user_data.get('role') in ['ishchi', 'xodim'] and new_status == "Tayyor bo'ldi":
                try:
                    await bot.send_message(
                        int(user_id),
                        f"✅ **Mahsulot tayyor bo'ldi!**\n\n🆔 Buyurtma ID: `{data['order_id']}`\n🧑 Mijoz: {data['client']}\n📦 Mebel: {product_id}\n📊 Soni: {amount} ta",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
                    
        await state.clear()
        return

    elif new_status == "Mijozni o'zi olib ketdi":
        await state.update_data(new_status=new_status, driver="O'zi olib ketdi")
        markup = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="6 so'm"), types.KeyboardButton(text="8 so'm")],
                [types.KeyboardButton(text="10 so'm"), types.KeyboardButton(text="0")],
                [types.KeyboardButton(text="Bosh menyu")]
            ],
            resize_keyboard=True
        )
        await message.answer("Chegirma summasini tanlang yoki kiriting:", reply_markup=markup)
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
                [types.KeyboardButton(text="3,5 so'm"), types.KeyboardButton(text="6 so'm"), types.KeyboardButton(text="8 so'm")],
                [types.KeyboardButton(text="Boshqa narx"), types.KeyboardButton(text="Bosh menyu")]
            ],
            resize_keyboard=True
        )
        await message.answer("Yetkazib berish narxini belgilang:", reply_markup=markup)
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
        await message.answer("Iltimos, narxni kiriting (masalan: 10$ yoki 100000 so'm):", reply_markup=types.ReplyKeyboardRemove())
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
                [types.KeyboardButton(text="3,5 so'm"), types.KeyboardButton(text="6 so'm"), types.KeyboardButton(text="8 so'm")],
                [types.KeyboardButton(text="Boshqa narx"), types.KeyboardButton(text="Bosh menyu")]
            ],
            resize_keyboard=True
        )
        await message.answer("Yetkazib berish narxini belgilang:", reply_markup=markup)
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
    await asyncio.to_thread(db.reference(f"orders/{order_id}").update, {
        'status': new_status,
        'driver': driver,
        'delivery_price': price,
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
    delivery_record = {
        'order_id': order_id,
        'client': client,
        'driver': driver,
        'price': price,
        'product_id': product_id,
        'amount': amount,
        'timestamp': timestamp
    }
    await asyncio.to_thread(db.reference(f"deliveries/{current_month}").push, delivery_record)
    
    try:
        import re as _re
        _nums = _re.findall(r'\d+', str(price).replace(" ", ""))
        price_val = int(_nums[0]) if _nums else 0
        if price_val > 0:
            if driver == "O'zi olib ketdi":
                # Mijoz qarzidan chegirish
                debt_ref = await asyncio.to_thread(db.reference(f'debts/{client}').get)
                current_debt = int(debt_ref) if debt_ref else 0
                new_debt = current_debt - price_val
                await asyncio.to_thread(db.reference(f'debts/{client}').set, new_debt)
                
                # Tarixga yozish
                record = {'type': 'Kirim', 'amount': price_val, 'timestamp': timestamp, 'note': f"O'zi olib ketgani uchun chegirma (Buyurtma: {order_id})"}
                await asyncio.to_thread(db.reference(f'transactions/clients/{client}').push, record)
            else:
                # Haydovchi balansini oshirish
                balance_ref = await asyncio.to_thread(db.reference(f"driver_balances/{driver}").get)
                current_balance = int(balance_ref) if balance_ref else 0
                new_balance = current_balance + price_val
                await asyncio.to_thread(db.reference(f"driver_balances/{driver}").set, new_balance)
                
                # Tarixga yozish
                record = {'type': 'Kirim', 'amount': price_val, 'timestamp': timestamp, 'note': f"Yetkazib berish haqi (Buyurtma: {order_id})"}
                await asyncio.to_thread(db.reference(f"transactions/drivers/{driver}").push, record)
    except Exception as _pe:
        logging.warning(f"Narx parse yoki tranzaksiya xatoligi: {_pe}")
        
    _role = await get_user_role(message.from_user.id)
    await message.answer(f"✅ Buyurtma holati yangilandi: {new_status}\n🚚 Haydovchi: {driver}\n💵 Narxi: {price}", reply_markup=main_menu(_role))
    
    # Notify admin
    admin_ref = await asyncio.to_thread(db.reference('users').get)
    for user_id, user_data in (admin_ref or {}).items():
        if user_data.get('role') == 'admin':
            try:
                await bot.send_message(
                    int(user_id),
                    f"📦 **Buyurtma holati o'zgardi!**\n\n🆔 ID: `{order_id}`\n🧑 Mijoz: {client}\n📌 Yangi holat: {new_status}\n🚚 Haydovchi: {driver}\n💵 Narxi: {price}",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
                
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
                sums_arr.append(f"{stats['sum_som']} so'm")
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
        text += f"💳 **Joriy balansi (sizning qarzingiz/haqqingiz):** {current_bal} so'm\n\n"
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
        
        await message.answer(f"✅ {driver_name} ga {amount} so'm berildi.\n💳 Yangi balansi: {new_bal} so'm", reply_markup=main_menu('admin'))
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
        
        await message.answer(f"✅ {driver_name} hisobiga {amount} so'm qo'shildi.\n💳 Yangi balansi: {new_bal} so'm", reply_markup=main_menu('admin'))
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
                history += f"{icon} {t.get('type')}: {t.get('amount')} so'm\n"
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
            
        items.reverse() # Oxirgisi tepada

        history_header = f"🕰 **{month} oyi yetkazib berish tarixi:**\n\n"
        history_items = []
        
        for d_id, d in items:
            if isinstance(d, dict):
                t_str = format_date(d.get('timestamp', "Noma'lum"))
                c_str = d.get('client', "Noma'lum")
                p_str = d.get('product_id', "Noma'lum")
                a_str = d.get('amount', '1')
                dr_str = d.get('driver', "Noma'lum")
                pr_str = d.get('price', '0')
                
                item_text = f"📅 Vaqt: {t_str}\n"
                item_text += f"🧑 Mijoz: {c_str}\n"
                item_text += f"📦 Mebel: {p_str} ({a_str} ta)\n"
                item_text += f"🚚 Dostavchik: {dr_str} ({pr_str})\n"
                item_text += "------------------------"
                history_items.append(item_text)
                
        # Send in chunks
        full_history = [history_header] + history_items
        current_msg = ""
        for part in full_history:
            if len(current_msg) + len(part) > 3900:
                await message.answer(current_msg, parse_mode="Markdown")
                current_msg = part + "\n\n"
            else:
                current_msg += part + "\n\n"
        
        if current_msg:
            await message.answer(current_msg, parse_mode="Markdown")
            
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
    info += f"🧑 Mijoz: {order_ref.get('client_name')}\n"
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
            
            # Mijoz qarzini kamaytirish
            client_name = order_ref.get('client_name')
            if client_name:
                # Narxni hisoblash
                price_val = 0
                mebel_data = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)
                if mebel_data and 'narxi' in mebel_data:
                    price_str = str(mebel_data['narxi']).replace("so'm", "").replace("$", "").replace(" ", "")
                    try:
                        price_val = int(price_str)
                    except:
                        price_val = 0
                
                total_price = price_val * amount
                if total_price > 0:
                    debt_ref = await asyncio.to_thread(db.reference(f'debts/{client_name}').get)
                    current_debt = int(debt_ref) if debt_ref else 0
                    new_debt = current_debt - total_price
                    await asyncio.to_thread(db.reference(f'debts/{client_name}').set, new_debt)
                    
                    timestamp = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
                    record = {'type': 'Kirim', 'amount': total_price, 'timestamp': timestamp, 'note': f"Buyurtma bekor qilindi: {order_id}"}
                    await asyncio.to_thread(db.reference(f'transactions/clients/{client_name}').push, record)
            
            # Buyurtmani bekor qilish
            await asyncio.to_thread(db.reference(f'orders/{order_id}').update, {'status': 'Bekor qilindi'})
        
        await message.answer(f"✅ Buyurtma `{order_id}` bekor qilindi!\n📦 Omborga qaytarildi.", reply_markup=main_menu('admin'), parse_mode="Markdown")
        
        # Omborchi va xodimlarga xabar
        users_ref = await asyncio.to_thread(db.reference('users').get)
        for user_id, user_data in (users_ref or {}).items():
            if user_data.get('role') in ['omborchi', 'ishchi', 'xodim']:
                try:
                    await bot.send_message(
                        int(user_id),
                        f"⚠️ Buyurtma bekor qilindi!\n🆔 ID: {order_id}\n📦 Mebel: {order_ref.get('product_id')}\n🧑 Mijoz: {order_ref.get('client_name')}"
                    )
                except:
                    pass
        # Hardcoded omborchi
        try:
            await bot.send_message(883589794, f"⚠️ Buyurtma bekor qilindi!\n🆔 ID: {order_id}\n📦 Mebel: {order_ref.get('product_id')}\n🧑 Mijoz: {order_ref.get('client_name')}")
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
            
            # Qarzni tuzatish
            client_name = order_ref.get('client_name')
            if client_name:
                price_val = 0
                mebel_data = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)
                if mebel_data and 'narxi' in mebel_data:
                    price_str = str(mebel_data['narxi']).replace("so'm", "").replace("$", "").replace(" ", "")
                    try:
                        price_val = int(price_str)
                    except:
                        price_val = 0
                
                price_diff = price_val * diff
                if price_diff != 0:
                    debt_ref = await asyncio.to_thread(db.reference(f'debts/{client_name}').get)
                    current_debt = int(debt_ref) if debt_ref else 0
                    new_debt = current_debt + price_diff
                    await asyncio.to_thread(db.reference(f'debts/{client_name}').set, new_debt)
        
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
                    f"✏️ Buyurtma o'zgartirildi!\n🆔 ID: {order_id}\n📦 {order_ref.get('product_id')}\n🧑 Mijoz: {order_ref.get('client_name')}\n🔄 {field_names.get(field, field)}: {new_value}"
                )
            except:
                pass
    try:
        await bot.send_message(883589794, f"✏️ Buyurtma o'zgartirildi!\n🆔 ID: {order_id}\n📦 {order_ref.get('product_id')}\n🧑 Mijoz: {order_ref.get('client_name')}\n🔄 {field_names.get(field, field)}: {new_value}")
    except:
        pass
    
    await state.clear()

@dp.message(StateFilter(None))
async def fallback_handler(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    await state.clear()
    await message.answer("Noto'g'ri buyruq yoki tushunarsiz matn kiritildi.\nIltimos, pastdagi tugmalardan foydalaning.", reply_markup=main_menu(role))

async def handle(request):
    return web.Response(text="Bot is running")

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
    """Kuniga 3 marta eslatma yuborish: 9:00, 15:00, 15:05"""
    while True:
        now = datetime.now(TASHKENT_TZ)
        
        # Bugungi uchta vaqtni hisoblash
        schedule = [
            (now.replace(hour=9, minute=0, second=0, microsecond=0), send_morning_reminder),
            (now.replace(hour=15, minute=0, second=0, microsecond=0), send_overdue_reminder),
            (now.replace(hour=15, minute=5, second=0, microsecond=0), send_tomorrow_reminder),
        ]
        
        # Navbatdagi eng yaqin vaqtni topish
        next_target = None
        next_func = None
        for target_time, func in schedule:
            if now < target_time:
                next_target = target_time
                next_func = func
                break
        
        # Agar bugungi barcha vaqtlar o'tgan bo'lsa, ertangi 9:00 ga o'tish
        if next_target is None:
            next_target = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            next_func = send_morning_reminder
        
        sleep_seconds = (next_target - now).total_seconds()
        logging.info(f"Keyingi eslatma: {next_target.strftime('%H:%M')} da ({sleep_seconds:.0f} sekund qoldi)")
        await asyncio.sleep(sleep_seconds)
        
        try:
            await next_func()
        except Exception as e:
            logging.error(f"Daily reminder task error: {e}")

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