import os
import firebase_admin
from firebase_admin import credentials, db

cred_path = os.path.join(os.getcwd(), "serviceAccountKey.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'
})

orders_ref = db.reference('orders').get()
active_orders_list = []
if orders_ref:
    for o_id, o in orders_ref.items():
        if isinstance(o, dict) and o.get('status') in ['Tayyorlanmoqda', "Tayyor bo'ldi", 'Yuborildi']:
            active_orders_list.append((o_id, o))

active_orders = ""
for o_id, o in active_orders_list:
    active_orders += f"🆔 `{o_id}` - 🧑 {o.get('client_name')}\n📦 Mebel: {o.get('product_id')} ({o.get('amount')} ta)\n📅 Muddat: {o.get('due_date')}\n"
    if o.get('comment') and str(o.get('comment')).lower() != 'yoq':
        active_orders += f"📝 Izoh: {o.get('comment')}\n"
    active_orders += f"📌 Holati: {o.get('status')}\n\n"

full_text = f"Faol buyurtmalar:\n\n{active_orders}\nQaysi buyurtmaning holatini o'zgartirmoqchisiz? Buyurtma ID-sini tanlang:"
print(f"Total characters: {len(full_text)}")
if len(full_text) > 4096:
    print("OVER LIMIT! IT WILL FAIL!")
else:
    print("Under limit.")
