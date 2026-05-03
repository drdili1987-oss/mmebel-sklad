import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred, {'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'})

nodes_to_delete = ['orders', 'deliveries', 'debts', 'transactions', 'driver_balances']
for node in nodes_to_delete:
    db.reference(node).delete()
    print(f'Deleted {node}')

print('Barcha tarix va hisobotlar tozalandi (nol qilindi).')
