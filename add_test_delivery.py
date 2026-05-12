import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'
})

current_month = datetime.now().strftime("%Y-%m")
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

delivery_record = {
    'order_id': 'TEST-1234',
    'client': 'Munosib Mebel',
    'driver': 'Dilmurod',
    'price': '10$',
    'product_id': 'BF 09',
    'amount': '2',
    'timestamp': timestamp
}

db.reference(f"deliveries/{current_month}").push(delivery_record)
print(f"Added test delivery to deliveries/{current_month}")
