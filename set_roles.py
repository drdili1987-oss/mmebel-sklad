import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred, {'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'})

db.reference('users/7498888755').update({'role': 'ishchi'})
db.reference('users/5063420475').update({'role': 'omborchi'})
print('Rollar muvaffaqiyatli saqlandi.')
