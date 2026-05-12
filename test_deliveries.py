import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'
})

current_month = datetime.now().strftime("%Y-%m")
deliveries_ref = db.reference(f'deliveries/{current_month}').get()

if isinstance(deliveries_ref, dict):
    items = list(deliveries_ref.items())
elif isinstance(deliveries_ref, list):
    items = [(i, v) for i, v in enumerate(deliveries_ref) if v is not None]
else:
    items = []

print(f"Type: {type(deliveries_ref)}")
print(f"Items count: {len(items)}")

for d_id, d in items:
    if not isinstance(d, dict):
        print(f"Warning: Item {d_id} is not a dict: {d}")
    else:
        print(f"{d_id}: {d}")
