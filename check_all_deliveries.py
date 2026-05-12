import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'
})

deliveries_ref = db.reference('deliveries').get()
print("All deliveries in database:")
for month, deliveries in deliveries_ref.items():
    print(f"\nMonth: {month}")
    if isinstance(deliveries, dict):
        for d_id, delivery in deliveries.items():
            if isinstance(delivery, dict):
                print(f"  ID: {d_id}")
                print(f"  Order ID: {delivery.get('order_id', 'N/A')}")
                print(f"  Client: {delivery.get('client', 'N/A')}")
                print(f"  Driver: {delivery.get('driver', 'N/A')}")
                print(f"  Product: {delivery.get('product_id', 'N/A')}")
                print(f"  Price: {delivery.get('price', 'N/A')}")
                print(f"  Timestamp: {delivery.get('timestamp', 'N/A')}")
                print("  ---")