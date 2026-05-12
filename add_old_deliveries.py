import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timedelta

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'
})

# Add test deliveries for previous months
months_to_add = ['2026-04', '2026-03', '2026-02', '2026-01', '2025-12']

for month in months_to_add:
    # Create a timestamp for that month
    year, month_num = map(int, month.split('-'))
    timestamp = f"{year}-{month_num:02d}-15 14:30:00"  # 15th of the month

    delivery_record = {
        'order_id': f'TEST-{month.replace("-", "")}',
        'client': f'Mijoz {month}',
        'driver': 'Bahodir aka',
        'price': '8 so\'m',
        'product_id': 'BF 12',
        'amount': '1',
        'timestamp': timestamp
    }

    db.reference(f"deliveries/{month}").push(delivery_record)
    print(f"Added test delivery to deliveries/{month}")

print("Test deliveries added for previous months!")