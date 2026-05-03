import logging
import asyncio
import uuid
import os
import aiohttp
from datetime import datetime, timedelta, timezone
TASHKENT_TZ = timezone(timedelta(hours=5))
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import firebase_admin
from firebase_admin import credentials, db

# Doimiy mijozlar ro'yxati
REGULAR_CLIENTS = [
    "Comfort", "Iskandar", "Grand plaza", "Baxrom Uchtepa", 
    "Baxrom 9703", "Bahodir aka🚛", "Bahodir aka Andijon", "Akrom aka", 
    "Zoʻr mebel", "Umid", "Akmal aka", "Doʻkon 707", "Farxod Jomiy", "Munosib Mebel"
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
    "BF 32", "BF 33", "BF 34", "BF 35", "BF 37", "BF 38", "BF 39",
    "BF 321", "BF 331", "BF 341", "BF 351", "BF 371", "BF 381", "BF 391",
    "BF 44", "BF 45",
    "BF 544", "BF 574", "BF 594",
    "BF 54-41", "BF 57-41", "BF 59-41",
    "BF 63", "BF 64", "BF 65", "BF 68",
    "BF 707", "BF 708", "BF 709",
    "BF 762", "BF 752", "BF 772",
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

# 1. Firebase Sozlamalari (RTDB)
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'
})

# 2. Bot Sozlamalari
API_TOKEN = '703858792:AAF2jgcbSpbvRd9cOVBuIrrK9vA5KXCzif4'
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
    amount = State()      # Nechta zakaz berdi
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

# 4. Rollarni Tekshirish (RTDB dan)
async def get_user_role(user_id):
    user_id_str = str(user_id)
    if user_id_str == '883589794':
        return 'omborchi'
    if user_id_str in ['6298036669', '1349256808', '7062569902', '7941658592', '1724350130']:
        return 'ishchi'
    
    ref = db.reference(f'users/{user_id}')
    user_data = await asyncio.to_thread(ref.get)
    if user_data:
        return user_data.get('role', 'mijoz')
    return 'mijoz'

# 5. Klaviatura (Menyu)
def main_menu(role):
    buttons = []
    if role == 'admin':
        buttons = [
            [types.KeyboardButton(text="➕ Yangi mebel"), types.KeyboardButton(text="💰 Narxni o'zgartirish")],
            [types.KeyboardButton(text="📦 Sklad qoldig'i"), types.KeyboardButton(text="📝 Yangi zakaz")],
            [types.KeyboardButton(text="📊 Mijozlar hisoboti"), types.KeyboardButton(text="🚚 Dostavkachilar hisoboti")],
            [types.KeyboardButton(text="🕰 Dostavka tarixi"), types.KeyboardButton(text="📈 Sotuv statistikasi")]
        ]
    elif role == 'omborchi':
        buttons = [
            [types.KeyboardButton(text="🔄 Skladni yangilash"), types.KeyboardButton(text="🚚 Dostavka nazorati")],
            [types.KeyboardButton(text="📦 Sklad qoldig'i")]
        ]
    elif role == 'ishchi':
        buttons = [
            [types.KeyboardButton(text="🔨 Faol zakazlar")]
        ]
    else:
        buttons = [[types.KeyboardButton(text="🛍 Sotuvdagi mebellar")]]
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- BOSH MENYU / BEKOR QILISH ---
MAIN_MENU_BUTTONS = {
    "Bosh menyu", "➕ Yangi mebel", "💰 Narxni o'zgartirish", "📦 Sklad qoldig'i", 
    "📝 Yangi zakaz", "📊 Mijozlar hisoboti", "🚚 Dostavkachilar hisoboti", "🕰 Dostavka tarixi", "📈 Sotuv statistikasi",
    "🔄 Skladni yangilash", "🚚 Dostavka nazorati", "🔨 Faol zakazlar", "🛍 Sotuvdagi mebellar"
}

@dp.message(F.text.in_(MAIN_MENU_BUTTONS), ~StateFilter(None))
async def main_menu_interceptor(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    await state.clear()
    if message.text == "Bosh menyu":
        await message.answer("Asosiy menyuga qaytdingiz.", reply_markup=main_menu(role))
    else:
        await message.answer("Jarayon bekor qilindi. Iltimos, tugmani qayta bosing.", reply_markup=main_menu(role))

@dp.message(F.text == "Bosh menyu", StateFilter("*"))
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

# --- ADMIN: MEBEL QO'SHISH ---
@dp.message(F.text == "➕ Yangi mebel")
async def add_product_start(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role in ['admin', 'omborchi']:
        await message.answer("Qaysi mebelni qo'shmoqchisiz? Shablondan tanlang yoki yozing:", reply_markup=get_models_keyboard())
        await state.set_state(ProductState.name)

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
    await message.answer("Skladda nechta bor?")
    await state.set_state(ProductState.quantity)

@dp.message(ProductState.quantity)
async def add_quantity(message: types.Message, state: FSMContext):
    try:
        qty = int(message.text)
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting (masalan: 10):")
        return
    await state.update_data(quantity=qty)
    await message.answer("📷 Mahsulot rasmini yuboring (URL ko'rinishida):\nMasalan: https://example.com/rasm.jpg")
    await state.set_state(ProductState.image)

@dp.message(ProductState.image)
async def add_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    p_id = data['name'].replace(" ", "").replace("-", "").upper()
    
    # RTDB ga yozish
    await asyncio.to_thread(
        db.reference(f'mebellar/{p_id}').set,
        {
            'id': p_id,
            'nomi': data['name'],
            'modeli': data['model'],
            'narxi': data['price'],
            'soni': int(data['quantity']),
            'rasm': message.text
        }
    )
    
    await message.answer(f"✅ Mebel qo'shildi! ID: `{p_id}`")
    await message.answer_photo(photo=message.text, caption=f"🪑 {data['name']} ({data['model']})\n💰 Narxi: {data['price']} so'm\n📦 Soni: {data['quantity']} ta")
    await state.clear()

# --- BARCHA UCHUN: SKLADNI KO'RISH ---
@dp.message(F.text.in_({"📦 Sklad qoldig'i", "🛍 Sotuvdagi mebellar"}))
async def view_stock(message: types.Message):
    mebellar = await asyncio.to_thread(db.reference('mebellar').get)
    if not mebellar:
        await message.answer("Sklad hozircha bo'sh.")
        return

    for m_id, m in mebellar.items():
        if isinstance(m, dict) and m.get('soni', 0) > 0:
            text = f"🪑 **{m.get('nomi', 'Noma\'lum')}** ({m.get('modeli', '')})\n"
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

# --- ADMIN: YANGI ZAKAZ YOZISH ---
@dp.message(F.text == "📝 Yangi zakaz")
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
            
    await message.answer(f"Nechta zakaz berdi?{price_text}", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrderState.amount)

@dp.message(OrderState.custom_product_id)
async def process_custom_product_id(message: types.Message, state: FSMContext):
    formatted_id = message.text.upper()
    await state.update_data(product_id=formatted_id)
    await message.answer("Nechta zakaz berdi?", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrderState.amount)

# Soni kiritilgandan keyin sanani so'rash
@dp.message(OrderState.amount)
async def process_amount(message: types.Message, state: FSMContext):
    await state.update_data(amount=message.text)
    await message.answer("📅 Zakaz qaysi sanaga tayyor bo'lishi kerak?\n(Masalan: 15.05.2026 yoki 'Ertaga kechqurun')")
    await state.set_state(OrderState.due_date)

# Oxirgi bosqich: Sanani qabul qilish va izoh so'rash
@dp.message(OrderState.due_date)
async def process_due_date(message: types.Message, state: FSMContext):
    await state.update_data(due_date=message.text)
    await message.answer("📝 Zakaz uchun izoh kiriting (mebelning biror joyini o'zgartirish kerak bo'lsa):\n(Agar izoh bo'lmasa 'yoq' deb yozing)")
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

    # Skladni kamaytirish
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
    
    await message.answer(f"✅ Zakaz qabul qilindi!\n🆔 ID: {order_id}\n📅 Muddat: {data['due_date']}\n📝 Izoh: {comment}")
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

    # Fetch orders and debt
    orders_ref = await asyncio.to_thread(db.reference('orders').get)
    debt_ref = await asyncio.to_thread(db.reference(f'debts/{client_name}').get)
    
    current_debt = debt_ref if debt_ref is not None else 0
    
    report_text = f"👤 **Mijoz:** {client_name}\n"
    report_text += f"💳 **Joriy qarzi:** {current_debt} so'm\n\n"
    report_text += "📦 **Olingan mebellar tarixi:**\n"
    
    count = 0
    if orders_ref:
        for o_id, o in orders_ref.items():
            if isinstance(o, dict) and str(o.get('client_name')).strip() == client_name.strip():
                count += 1
                report_text += f"▪️ {o.get('product_id')} - {o.get('amount')} ta ({o.get('status')})\n"
                
    if count == 0:
        report_text += "Hech qanday mebel olinmagan.\n"
        
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text=f"➕ {client_name} dan Pul Olish (Kirim)")],
            [types.KeyboardButton(text=f"➖ {client_name} ga Pul Berish (Chiqim)")],
            [types.KeyboardButton(text=f"📜 {client_name} To'lovlar Tarixi")],
            [types.KeyboardButton(text="Bosh menyu")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(report_text, parse_mode="Markdown", reply_markup=markup)
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
            
        history = f"📜 **{client_name} to'lovlar (Kirim/Chiqim) tarixi:**\n\n"
        for t_id, t in trans_ref.items():
            if isinstance(t, dict):
                icon = "🟢" if t.get('type') == 'Kirim' else "🔴"
                history += f"{icon} {t.get('type')}: {t.get('amount')} so'm\n"
                history += f"📅 Sana: {t.get('timestamp')}\n\n"
            
        if len(history) > 4000:
            for x in range(0, len(history), 4000):
                await message.answer(history[x:x+4000], parse_mode="Markdown")
        else:
            await message.answer(history, parse_mode="Markdown")

# Omborchiga yangi zakaz haqida xabar yuborish
async def notify_warehouse(order_data, order_id):
    # Asosiy omborchiga xabar yuborish
    try:
        await bot.send_message(
            883589794,
            f"🔔 Yangi zakaz!\n\n"
            f"🧑 Mijoz: {order_data['client']}\n"
            f"📦 Mebel: {order_data['product_id']}\n"
            f"📊 Soni: {order_data['amount']}\n"
            f"📅 Muddat: {order_data['due_date']}\n"
            f"📝 Izoh: {order_data.get('comment', 'Yoq')}\n"
            f"🆔 Zakaz ID: {order_id}"
        )
    except Exception as e:
        print(f"Omborchiga xabar yuborishda xatolik: {e}")

    # Omborchi va ishchilarga xabar yuborish
    users_ref = await asyncio.to_thread(db.reference('users').get)
    for user_id, user_data in (users_ref or {}).items():
        if user_data.get('role') in ['omborchi', 'ishchi'] and int(user_id) != 883589794:
            try:
                await bot.send_message(
                    int(user_id),
                    f"🔔 Yangi zakaz!\n\n"
                    f"🧑 Mijoz: {order_data['client']}\n"
                    f"📦 Mebel: {order_data['product_id']}\n"
                    f"📊 Soni: {order_data['amount']}\n"
                    f"📅 Muddat: {order_data['due_date']}\n"
                    f"📝 Izoh: {order_data.get('comment', 'Yoq')}\n"
                    f"🆔 Zakaz ID: {order_id}"
                )
            except Exception as e:
                print(f"Xodimga xabar yuborishda xatolik: {e}")

# --- ISHCHI: FAOL ZAKAZLAR ---
@dp.message(F.text == "🔨 Faol zakazlar")
async def view_active_orders(message: types.Message):
    role = await get_user_role(message.from_user.id)
    if role in ['ishchi', 'admin', 'omborchi']:
        orders_ref = await asyncio.to_thread(db.reference('orders').get)
        if not orders_ref:
            await message.answer("Hozircha hech qanday faol zakaz yo'q.")
            return
            
        active_orders = ""
        for o_id, o in orders_ref.items():
            if isinstance(o, dict) and o.get('status') == 'Tayyorlanmoqda':
                active_orders += f"🆔 `{o_id}` - 📦 Mebel: {o.get('product_id')}\n"
                active_orders += f"📊 Soni: {o.get('amount')} ta\n"
                active_orders += f"📅 Muddat: {o.get('due_date')}\n"
                if o.get('comment') and str(o.get('comment')).lower() != 'yoq':
                    active_orders += f"📝 Izoh: {o.get('comment')}\n"
                active_orders += "\n"
        
        if not active_orders:
            await message.answer("Hozircha faol zakazlar yo'q.")
            return
            
        await message.answer(f"🔨 Faol zakazlar ro'yxati:\n\n{active_orders}")

# --- OMBORCHI: SKLADNI YANGILASH ---
@dp.message(F.text == "🔄 Skladni yangilash")
async def update_stock_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'omborchi':
        await message.answer("Qaysi mebelning sonini yangilamoqchisiz? Tanlang yoki ID kiriting:", reply_markup=get_models_keyboard())
        await state.set_state(UpdateStockState.product_id)

@dp.message(UpdateStockState.product_id)
async def update_stock_product_id(message: types.Message, state: FSMContext):
    product_id = message.text.replace(" ", "").replace("-", "").upper()
    product_ref = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)
    if not product_ref:
        await message.answer("Bunday ID li mebel topilmadi. Qaytadan kiriting:", reply_markup=types.ReplyKeyboardRemove())
        return
    await state.update_data(product_id=product_id)
    await message.answer(f"Mebel: {product_ref['nomi']} ({product_ref['modeli']})\nHozirgi qoldiq: {product_ref['soni']} ta\n\nYangi sonini kiriting:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(UpdateStockState.new_quantity)

@dp.message(UpdateStockState.new_quantity)
async def update_stock_new_quantity(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        new_quantity = int(message.text)
        await asyncio.to_thread(db.reference(f"mebellar/{data['product_id']}").update, {'soni': new_quantity})
        await message.answer(f"✅ Sklad muvaffaqiyatli yangilandi!\nYangi qoldiq: {new_quantity} ta", reply_markup=main_menu('omborchi'))
        await state.clear()
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting:")

# --- OMBORCHI: DOSTAVKA NAZORATI ---
@dp.message(F.text == "🚚 Dostavka nazorati")
async def delivery_control_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'omborchi':
        orders_ref = await asyncio.to_thread(db.reference('orders').get)
        if not orders_ref:
            await message.answer("Hozircha hech qanday zakaz yo'q.")
            return
            
        active_orders = ""
        buttons = []
        row = []
        for o_id, o in orders_ref.items():
            if isinstance(o, dict) and o.get('status') in ['Tayyorlanmoqda', "Tayyor bo'ldi", 'Yuborildi']:
                active_orders += f"🆔 `{o_id}` - 🧑 {o.get('client_name')}\n📦 Mebel: {o.get('product_id')} ({o.get('amount')} ta)\n📅 Muddat: {o.get('due_date')}\n"
                if o.get('comment') and str(o.get('comment')).lower() != 'yoq':
                    active_orders += f"📝 Izoh: {o.get('comment')}\n"
                active_orders += f"📌 Holati: {o.get('status')}\n\n"
                button_text = f"{o.get('product_id')} ({str(o_id)})"
                row.append(types.KeyboardButton(text=button_text))
                if len(row) == 2:
                    buttons.append(row)
                    row = []
        
        if row:
            buttons.append(row)
        buttons.append([types.KeyboardButton(text="Bosh menyu")])
        
        if not active_orders:
            await message.answer("Barcha zakazlar yetkazib berilgan yoki faol zakazlar yo'q.")
            return
            
        markup = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
        await message.answer(f"Faol zakazlar:\n\n{active_orders}\nQaysi zakazning holatini o'zgartirmoqchisiz? Zakaz ID-sini tanlang:", reply_markup=markup)
        await state.set_state(DeliveryControlState.order_id)

@dp.message(DeliveryControlState.order_id)
async def delivery_order_id(message: types.Message, state: FSMContext):
    if "(" in message.text and ")" in message.text:
        order_id = message.text.split("(")[-1].split(")")[0].strip().upper()
    else:
        order_id = message.text.strip().upper()
        
    order_ref = await asyncio.to_thread(db.reference(f'orders/{order_id}').get)
    if not order_ref:
        await message.answer("Bunday ID li zakaz topilmadi. Qaytadan kiriting:")
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
    
    await message.answer(f"Zakaz: {order_ref.get('client_name')}niki\nHozirgi holat: {order_ref.get('status')}\n\nYangi holatni tanlang:", reply_markup=markup)
    await state.set_state(DeliveryControlState.new_status)

@dp.message(DeliveryControlState.new_status)
async def delivery_new_status(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        await message.answer("Bosh menyu", reply_markup=main_menu('omborchi'))
        await state.clear()
        return
        
    data = await state.get_data()
    new_status = message.text
    
    if new_status in ["Mijozni o'zi olib ketdi", "Bekor qilindi", "Tayyor bo'ldi"]:
        await asyncio.to_thread(db.reference(f"orders/{data['order_id']}").update, {'status': new_status})
        await message.answer(f"✅ Zakaz holati yangilandi: {new_status}", reply_markup=main_menu('omborchi'))
        
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
                        f"📦 **Zakaz holati o'zgardi!**\n\n🆔 ID: `{data['order_id']}`\n🧑 Mijoz: {data['client']}\n📌 Yangi holat: {new_status}",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            elif user_data.get('role') == 'ishchi' and new_status == "Tayyor bo'ldi":
                try:
                    await bot.send_message(
                        int(user_id),
                        f"✅ **Mahsulot tayyor bo'ldi!**\n\n🆔 Zakaz ID: `{data['order_id']}`\n🧑 Mijoz: {data['client']}\n📦 Mebel: {product_id}\n📊 Soni: {amount} ta",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
                    
        await state.clear()
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
        await message.answer("Yetkazib bergan dastavchikni tanlang:", reply_markup=markup)
        await state.set_state(DeliveryControlState.driver)
        return

@dp.message(DeliveryControlState.driver)
async def delivery_driver(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        await message.answer("Bosh menyu", reply_markup=main_menu('omborchi'))
        await state.clear()
        return
        
    await state.update_data(driver=message.text)
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="6 so'm"), types.KeyboardButton(text="8 so'm")],
            [types.KeyboardButton(text="Boshqa narx"), types.KeyboardButton(text="Bosh menyu")]
        ],
        resize_keyboard=True
    )
    await message.answer("Dostavka narxini belgilang:", reply_markup=markup)
    await state.set_state(DeliveryControlState.delivery_price)

@dp.message(DeliveryControlState.delivery_price)
async def delivery_price_handler(message: types.Message, state: FSMContext):
    if message.text == "Bosh menyu":
        await message.answer("Bosh menyu", reply_markup=main_menu('omborchi'))
        await state.clear()
        return
        
    if message.text == "Boshqa narx":
        await message.answer("Iltimos, narxni kiriting (masalan: 10$ yoki 100000 so'm):", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(DeliveryControlState.custom_price)
        return
        
    await process_delivery_final(message.text, message, state)

@dp.message(DeliveryControlState.custom_price)
async def delivery_custom_price(message: types.Message, state: FSMContext):
    await process_delivery_final(message.text, message, state)

async def process_delivery_final(price, message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data['order_id']
    new_status = data['new_status']
    driver = data['driver']
    client = data['client']
    
    # Update order
    await asyncio.to_thread(db.reference(f"orders/{order_id}").update, {
        'status': new_status,
        'driver': driver,
        'delivery_price': price
    })
    
    # Get product_id for history
    order_ref = await asyncio.to_thread(db.reference(f"orders/{order_id}").get)
    product_id = order_ref.get('product_id', 'Noma\'lum') if order_ref else 'Noma\'lum'
    
    # Save delivery report
    current_month = datetime.now(TASHKENT_TZ).strftime("%Y-%m")
    timestamp = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
    delivery_record = {
        'order_id': order_id,
        'client': client,
        'driver': driver,
        'price': price,
        'product_id': product_id,
        'timestamp': timestamp
    }
    await asyncio.to_thread(db.reference(f"deliveries/{current_month}").push, delivery_record)
    
    await message.answer(f"✅ Zakaz holati yangilandi: {new_status}\n🚚 Dostavchik: {driver}\n💵 Narxi: {price}", reply_markup=main_menu('omborchi'))
    
    # Notify admin
    admin_ref = await asyncio.to_thread(db.reference('users').get)
    for user_id, user_data in (admin_ref or {}).items():
        if user_data.get('role') == 'admin':
            try:
                await bot.send_message(
                    int(user_id),
                    f"📦 **Zakaz holati o'zgardi!**\n\n🆔 ID: `{order_id}`\n🧑 Mijoz: {client}\n📌 Yangi holat: {new_status}\n🚚 Dostavchik: {driver}\n💵 Narxi: {price}",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
                
    await state.clear()

class DriverReportState(StatesGroup):
    select_month = State()

@dp.message(F.text == "🚚 Dostavkachilar hisoboti")
async def driver_report_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'admin':
        current_month = datetime.now(TASHKENT_TZ).strftime("%Y-%m")
        deliveries_ref = await asyncio.to_thread(db.reference(f'deliveries/{current_month}').get)
        
        if not deliveries_ref:
            await message.answer(f"Ushbu oy ({current_month}) uchun dostavka qilingan zakazlar topilmadi.")
            return
            
        driver_stats = {}
        report_text = f"📊 **{current_month} oyi uchun dostavkachilar hisoboti:**\n\n"
        
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
            report_text += f"📦 Jami dostavkalar: {stats['count']} ta\n"
            
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
        
        text = f"👨‍✈️ **Dostavkachi:** {driver_name}\n"
        text += f"💳 **Joriy balansi (sizning qarzingiz/haqqingiz):** {current_bal} so'm\n\n"
        text += "*(Eslatma: Bu balansga qilingan dostavkalar puli avtomatik qo'shilmaydi. Moliya bo'limi orqali hisob-kitobni o'zingiz yurgizasiz)*"
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
                history += f"📅 Sana: {t.get('timestamp')}\n\n"
            
        if len(history) > 4000:
            for x in range(0, len(history), 4000):
                await message.answer(history[x:x+4000], parse_mode="Markdown")
        else:
            await message.answer(history, parse_mode="Markdown")

class HistoryState(StatesGroup):
    select_month = State()

@dp.message(F.text == "🕰 Dostavka tarixi")
async def delivery_history_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'admin':
        # Show last 6 months as keyboard buttons
        months = []
        for i in range(6):
            m = (datetime.now(TASHKENT_TZ).month - i - 1) % 12 + 1
            y = datetime.now(TASHKENT_TZ).year + (datetime.now(TASHKENT_TZ).month - i - 1) // 12
            if m <= 0:
                m += 12
                y -= 1
            months.append(f"{y}-{m:02d}")
        
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
        
    month = message.text
    deliveries_ref = await asyncio.to_thread(db.reference(f'deliveries/{month}').get)
    if not deliveries_ref:
        await message.answer(f"{month} oyida hech qanday yetkazib berishlar yo'q.")
        return
        
    history_text = f"🕰 **{month} oyi dostavka tarixi:**\n\n"
    for d_id, d in deliveries_ref.items():
        if isinstance(d, dict):
            history_text += f"📅 Vaqt: {d.get('timestamp', 'Noma\'lum')}\n"
            history_text += f"🧑 Mijoz: {d.get('client', 'Noma\'lum')}\n"
            history_text += f"📦 Mebel: {d.get('product_id', 'Noma\'lum')}\n"
            history_text += f"🚚 Dostavchik: {d.get('driver', 'Noma\'lum')} ({d.get('price', '0')})\n\n"
            
    # Send in chunks if it's too long
    if len(history_text) > 4000:
        for x in range(0, len(history_text), 4000):
            await message.answer(history_text[x:x+4000], parse_mode="Markdown")
    else:
        await message.answer(history_text, parse_mode="Markdown")


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
            await message.answer("Hech qanday dostavka tarixi topilmadi.")
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
                report_text += f" ▪️ {d.get('client')} ga: {d.get('product_id')} (Narxi: {d.get('price')})\n"
            report_text += f" 📦 Jami shu oyda: {count} ta dostavka\n\n"
            
        if len(report_text) > 4000:
            for x in range(0, len(report_text), 4000):
                await message.answer(report_text[x:x+4000], parse_mode="Markdown")
        else:
            await message.answer(report_text, parse_mode="Markdown")

@dp.message(StateFilter('*'))
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

async def main():
    # Render Web Service portini ochib turish uchun vaqtinchalik server
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # Uygotgichni fonga ishga tushirish
    asyncio.create_task(keep_awake())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())