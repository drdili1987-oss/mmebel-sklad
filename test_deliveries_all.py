import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'
})

deliveries_ref = db.reference('deliveries').get()
print(f"Deliveries keys: {deliveries_ref.keys() if deliveries_ref else 'None'}")
if deliveries_ref:
    for k, v in deliveries_ref.items():
        if isinstance(v, dict):
            print(f"Month: {k}, Deliveries: {len(v)}")
        elif isinstance(v, list):
            print(f"Month: {k}, Deliveries: {len([x for x in v if x is not None])}")
