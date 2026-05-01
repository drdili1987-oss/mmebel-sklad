import logging
import asyncio
import uuid
import os
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import firebase_admin
from firebase_admin import credentials, db

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

class OrderState(StatesGroup):
    client = State()      # Mijoz ismi
    product_id = State()  # Mebel ID-si
    amount = State()      # Nechta zakaz berdi
    due_date = State()    # Qaysi sanaga tayyor bo'lishi kerak
    comment = State()     # Izoh

class UpdateStockState(StatesGroup):
    product_id = State()
    new_quantity = State()

class DeliveryControlState(StatesGroup):
    order_id = State()
    new_status = State()

# 4. Rollarni Tekshirish (RTDB dan)
async def get_user_role(user_id):
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
            [types.KeyboardButton(text="📦 Sklad qoldig'i"), types.KeyboardButton(text="📝 Yangi zakaz")]
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

# --- START KOMANDASI ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    role = await get_user_role(message.from_user.id)
    await message.answer(f"Assalomu alaykum! Rolingiz: **{role.upper()}**", 
                         reply_markup=main_menu(role), parse_mode="Markdown")

# --- ADMIN: MEBEL QO'SHISH ---
@dp.message(F.text == "➕ Yangi mebel")
async def add_product_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'admin':
        await message.answer("Mebel nomini kiriting:")
        await state.set_state(ProductState.name)

@dp.message(ProductState.name)
async def add_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Modelini kiriting (masalan: Spalniy):")
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
    await state.update_data(quantity=message.text)
    await message.answer("📷 Mahsulot rasmini yuboring (URL ko'rinishida):\nMasalan: https://example.com/rasm.jpg")
    await state.set_state(ProductState.image)

@dp.message(ProductState.image)
async def add_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    p_id = str(uuid.uuid4())[:6].upper()
    
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
            text += f"💰 Narxi: {m.get('narxi', '0')} so'm\n"
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
        await message.answer("Mijoz ismini kiriting:")
        await state.set_state(OrderState.client)

@dp.message(OrderState.client)
async def process_client(message: types.Message, state: FSMContext):
    await state.update_data(client=message.text)
    await message.answer("Mebel ID'sini kiriting (sklad ro'yxatidan):")
    await state.set_state(OrderState.product_id)

@dp.message(OrderState.product_id)
async def process_product_id(message: types.Message, state: FSMContext):
    await state.update_data(product_id=message.text)
    await message.answer("Nechta zakaz berdi?")
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
    order_id = str(uuid.uuid4())[:8].upper()
    
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
            'created_at': str(asyncio.get_event_loop().time())
        }
    )
    
    await message.answer(f"✅ Zakaz qabul qilindi!\n🆔 ID: {order_id}\n📅 Muddat: {data['due_date']}\n📝 Izoh: {comment}")
    data['comment'] = comment
    await state.clear()
    
    # Omborchiga xabar yuborish
    await notify_warehouse(data, order_id)

# Omborchiga yangi zakaz haqida xabar yuborish
async def notify_warehouse(order_data, order_id):
    # Omborchi user ID sini Firebase dan olish
    omborchi_ref = await asyncio.to_thread(db.reference('users').get)
    for user_id, user_data in (omborchi_ref or {}).items():
        if user_data.get('role') == 'omborchi':
            try:
                await bot.send_message(
                    int(user_id),
                    f"🔔 **Yangi zakaz!**\n\n"
                    f"🧑 Mijoz: {order_data['client']}\n"
                    f"📦 Mebel ID: {order_data['product_id']}\n"
                    f"📊 Soni: {order_data['amount']}\n"
                    f"📅 Muddat: {order_data['due_date']}\n"
                    f"📝 Izoh: {order_data.get('comment', 'Yoq')}\n"
                    f"🆔 Zakaz ID: {order_id}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Omborchiga xabar yuborishda xatolik: {e}")

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
                active_orders += f"🆔 `{o_id}` - 📦 Mebel ID: {o.get('product_id')}\n"
                active_orders += f"📊 Soni: {o.get('amount')} ta\n"
                active_orders += f"📅 Muddat: {o.get('due_date')}\n"
                if o.get('comment') and str(o.get('comment')).lower() != 'yoq':
                    active_orders += f"📝 Izoh: {o.get('comment')}\n"
                active_orders += "\n"
        
        if not active_orders:
            await message.answer("Hozircha faol zakazlar yo'q.")
            return
            
        await message.answer(f"🔨 **Faol zakazlar ro'yxati:**\n\n{active_orders}", parse_mode="Markdown")

# --- OMBORCHI: SKLADNI YANGILASH ---
@dp.message(F.text == "🔄 Skladni yangilash")
async def update_stock_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'omborchi':
        await message.answer("Qaysi mebelning sonini yangilamoqchisiz? Mebel ID-sini kiriting:")
        await state.set_state(UpdateStockState.product_id)

@dp.message(UpdateStockState.product_id)
async def update_stock_product_id(message: types.Message, state: FSMContext):
    product_id = message.text.upper()
    product_ref = await asyncio.to_thread(db.reference(f'mebellar/{product_id}').get)
    if not product_ref:
        await message.answer("Bunday ID li mebel topilmadi. Qaytadan kiriting:")
        return
    await state.update_data(product_id=product_id)
    await message.answer(f"Mebel: {product_ref['nomi']} ({product_ref['modeli']})\nHozirgi qoldiq: {product_ref['soni']} ta\n\nYangi sonini kiriting:")
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
        for o_id, o in orders_ref.items():
            if isinstance(o, dict) and o.get('status') in ['Tayyorlanmoqda', 'Yuborildi']:
                active_orders += f"🆔 `{o_id}` - 🧑 {o.get('client_name')}\n📦 Mebel: {o.get('product_id')} ({o.get('amount')} ta)\n📅 Muddat: {o.get('due_date')}\n📌 Holati: {o.get('status')}\n\n"
        
        if not active_orders:
            await message.answer("Barcha zakazlar yetkazib berilgan yoki faol zakazlar yo'q.")
            return
            
        await message.answer(f"Faol zakazlar:\n\n{active_orders}\nQaysi zakazning holatini o'zgartirmoqchisiz? Zakaz ID-sini kiriting:", parse_mode="Markdown")
        await state.set_state(DeliveryControlState.order_id)

@dp.message(DeliveryControlState.order_id)
async def delivery_order_id(message: types.Message, state: FSMContext):
    order_id = message.text.upper()
    order_ref = await asyncio.to_thread(db.reference(f'orders/{order_id}').get)
    if not order_ref:
        await message.answer("Bunday ID li zakaz topilmadi. Qaytadan kiriting:")
        return
        
    await state.update_data(order_id=order_id, client=order_ref.get('client_name'))
    
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Yuborildi"), types.KeyboardButton(text="Yetkazib berildi")],
            [types.KeyboardButton(text="Bekor qilindi"), types.KeyboardButton(text="Bosh menyu")]
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
    await asyncio.to_thread(db.reference(f"orders/{data['order_id']}").update, {'status': new_status})
    
    await message.answer(f"✅ Zakaz holati yangilandi: {new_status}", reply_markup=main_menu('omborchi'))
    
    # Notify admin
    admin_ref = await asyncio.to_thread(db.reference('users').get)
    for user_id, user_data in (admin_ref or {}).items():
        if user_data.get('role') == 'admin':
            try:
                await bot.send_message(
                    int(user_id),
                    f"📦 **Zakaz holati o'zgardi!**\n\n🆔 ID: `{data['order_id']}`\n🧑 Mijoz: {data['client']}\n📌 Yangi holat: {new_status}",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
                
    await state.clear()

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