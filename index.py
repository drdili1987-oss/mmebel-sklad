import logging
import asyncio
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import firebase_admin
from firebase_admin import credentials, db


from bot import API_TOKEN, bot, dp, root_ref
logging.basicConfig(level=logging.INFO)

# 3. Holatlar (States)
class ProductState(StatesGroup):
    name = State()
    model = State()
    price = State()
    quantity = State()

class OrderState(StatesGroup):
    client = State()
    product_id = State()
    amount = State()

class UpdateState(StatesGroup):
    product_id = State()
    new_value = State()

# 4. Rollarni tekshirish funksiyasi (Realtime Database uchun)
async def get_user_role(user_id):
    user = root_ref.child('users').child(str(user_id)).get()
    if user and 'role' in user:
        return user['role']
    return 'mijoz'

# 5. Menyu Tugmalari
def get_keyboard(role):
    buttons = []
    if role == 'admin':
        buttons = [
            [types.KeyboardButton(text="➕ Yangi mahsulot"), types.KeyboardButton(text="💰 Narxni o'zgartirish")],
            [types.KeyboardButton(text="📝 Yangi zakaz yozish"), types.KeyboardButton(text="📦 Sklad qoldig'i")]
        ]
    elif role == 'omborchi':
        buttons = [
            [types.KeyboardButton(text="🔄 Skladni yangilash"), types.KeyboardButton(text="🚚 Dostavka holati")],
            [types.KeyboardButton(text="📦 Sklad qoldig'i")]
        ]
    else:
        buttons = [[types.KeyboardButton(text="🛍 Sotuvdagi mebellar")]]
    
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def start(message: types.Message):
    role = await get_user_role(message.from_user.id)
    await message.answer(f"Xush kelibsiz! Sizning rolingiz: {role.capitalize()}", 
                         reply_markup=get_keyboard(role))

# 🛍 MIJOZ: Skladni ko'rish (Realtime Database uchun)
@dp.message(F.text == "🛍 Sotuvdagi mebellar")
@dp.message(F.text == "📦 Sklad qoldig'i")
async def view_stock(message: types.Message):
    items = root_ref.child('mebellar').get() or {}
    res = "🏠 Munosib Mebel Skladi:\n\n"
    for p_id, d in items.items():
        if d.get('soni', 0) > 0:
            res += f"🔹 {d['nomi']} ({d['modeli']})\n   Narxi: {d['price']} | Qoldi: {d['soni']} ta\n   ID: {p_id}\n\n"
    await message.answer(res, parse_mode="Markdown")

# ➕ ADMIN: Mahsulot qo'shish boshlanishi
@dp.message(F.text == "➕ Yangi mahsulot")
async def add_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) == 'admin':
        await message.answer("Mebel nomini yozing:")
        await state.set_state(ProductState.name)

@dp.message(ProductState.name)
async def add_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Modelini yozing:")
    await state.set_state(ProductState.model)

@dp.message(ProductState.model)
async def add_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("Narxini yozing:")
    await state.set_state(ProductState.price)

@dp.message(ProductState.price)
async def add_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Soni nechta?")
    await state.set_state(ProductState.quantity)

@dp.message(ProductState.quantity)
async def add_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    p_id = str(uuid.uuid4())[:6].upper()
    root_ref.child('mebellar').child(p_id).set({
        'nomi': data['name'],
        'modeli': data['model'],
        'price': data['price'],
        'soni': int(message.text)
    })
    await message.answer(f"✅ Saqlandi! ID: {p_id}")
    await state.clear()

# 🚚 OMBORCHI: Dostavka (Inline tugmalar bilan)
@dp.message(F.text == "🚚 Dostavka holati")
async def delivery(message: types.Message):
    if await get_user_role(message.from_user.id) in ['admin', 'omborchi']:
        # Bu yerda zakazlar ro'yxati chiqadi (oldingi kod kabi)
        await message.answer("Hozircha faol zakazlar yo'q.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
