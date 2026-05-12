import os
import firebase_admin
from firebase_admin import credentials, db

cred_path = os.path.join(os.getcwd(), "serviceAccountKey.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'
})

users = db.reference('users').get()
print("=== USERS ===")
import json
print(json.dumps(users, indent=2))

orders = db.reference('orders').get()
print("\n=== ORDERS SAMPLE ===")
if orders:
    # Print active orders only
    active = {k:v for k,v in orders.items() if v.get('status') in ['Tayyorlanmoqda', "Tayyor bo'ldi", 'Yuborildi']}
    print(f"Total active orders: {len(active)}")
    for k, v in list(active.items())[:3]:
        print(f"{k}: {v.get('status')}")
else:
    print("No orders.")
