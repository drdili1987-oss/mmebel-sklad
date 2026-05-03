import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'
})

data = [
    ("Komplekt", ["BF 06", "BF 07", "BF 09"], "350$"),
    ("Komplekt", ["BF 12", "BF 14", "BF 15", "BF 18"], "335$"),
    ("Komplekt", ["BF 244", "BF 264", "BF 274", "BF 294"], "320$"),
    ("Komplekt", ["BF 246", "BF 266", "BF 276", "BF 296"], "340$"),
    ("Komplekt", ["BF 32", "BF 33", "BF 34", "BF 35", "BF 37", "BF 38", "BF 39"], "270$"),
    ("Komplekt", ["BF 321", "BF 331", "BF 341", "BF 351", "BF 371", "BF 381", "BF 391"], "330$"),
    ("Komplekt", ["BF 44", "BF 45"], "425$"),
    ("Komplekt", ["BF 544", "BF 574", "BF 594"], "360$"),
    ("Komplekt", ["BF 54-41", "BF 57-41", "BF 59-41"], "425$"),
    ("Komplekt", ["BF 63", "BF 64", "BF 65", "BF 68"], "400$"),
    ("Komplekt", ["BF 707", "BF 708", "BF 709"], "490$"),
    ("Komplekt", ["BF 762", "BF 752", "BF 772"], "265$"),
    ("Komplekt", ["BF 713", "BF 753", "BF 763"], "285$"),
    
    ("Shkaf", ["D 100", "D 106", "D 109"], "260$"),
    ("Shkaf", ["D 50", "D 59"], "195$"),
    ("Shkaf", ["D 003"], "200$"),
    ("Shkaf", ["D 004", "D 006"], "230$"),
    ("Shkaf", ["D 005"], "0$"),
    ("Shkaf", ["BF 762 SHKAF", "BF 752 SHKAF", "BF 772 SHKAF"], "135$"),
]

for category, models, price in data:
    for model in models:
        p_id = model.replace(" ", "").replace("-", "").upper()
        # Bazadagi bor ma'lumotni o'chirib yubormaslik uchun sonini tekshiramiz
        ref = db.reference(f'mebellar/{p_id}')
        existing = ref.get()
        soni = existing.get('soni', 0) if existing else 0
        rasm = existing.get('rasm', '') if existing else ''
        
        ref.set({
            'id': p_id,
            'nomi': category,
            'modeli': model,
            'narxi': price,
            'soni': soni,
            'rasm': rasm
        })
        print(f"Qo'shildi: {model} - {price}")

print("Barcha modellar muvaffaqiyatli bazaga kiritildi!")
