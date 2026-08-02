import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('firebase_service_account.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

docs = db.collection('students').stream()
print("Student IDs in DB:")
for doc in docs:
    print(doc.id)
