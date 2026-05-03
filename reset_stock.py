import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred, {'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'})

mebellar_ref = db.reference('mebellar')
mebellar = mebellar_ref.get()
if mebellar:
    for m_id in mebellar.keys():
        mebellar_ref.child(m_id).update({'soni': 0})
    print('Barcha sklad qoldiqlari 0 ga tushirildi.')
