import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'
})

# Check orders that have been delivered
orders_ref = db.reference('orders').get()
print("Checking orders for delivered items:")
if orders_ref:
    for order_id, order in orders_ref.items():
        if isinstance(order, dict) and order.get('status') in ['Biz yetkazib berdik', 'Mijozni o\'zi olib ketdi']:
            print(f"Order ID: {order_id}")
            print(f"  Client: {order.get('client_name', 'N/A')}")
            print(f"  Product: {order.get('product_id', 'N/A')}")
            print(f"  Status: {order.get('status', 'N/A')}")
            print(f"  Driver: {order.get('driver', 'N/A')}")
            print(f"  Delivery Price: {order.get('delivery_price', 'N/A')}")
            print(f"  Created: {order.get('created_at', 'N/A')}")
            print("  ---")

# Check if there are deliveries that don't have TEST in order_id
deliveries_ref = db.reference('deliveries').get()
print("\nChecking for non-test deliveries:")
if deliveries_ref:
    for month, deliveries in deliveries_ref.items():
        if isinstance(deliveries, dict):
            for d_id, delivery in deliveries.items():
                if isinstance(delivery, dict):
                    order_id = delivery.get('order_id', '')
                    if 'TEST' not in str(order_id):
                        print(f"Month: {month}, Order ID: {order_id}")
                        print(f"  Client: {delivery.get('client', 'N/A')}")
                        print(f"  Driver: {delivery.get('driver', 'N/A')}")
                        print(f"  Product: {delivery.get('product_id', 'N/A')}")
                        print(f"  Price: {delivery.get('price', 'N/A')}")
                        print("  ---")