import os
import firebase_admin
from firebase_admin import credentials, db

cred_path = os.path.join(os.getcwd(), "serviceAccountKey.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'
})

mebellar = db.reference('mebellar').get()
print("=== MEBELLAR ===")
import json
print(json.dumps(mebellar, indent=2))
