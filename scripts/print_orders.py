from pymongo import MongoClient
import os

MONGO_URI = os.getenv('MONGO_URI') or os.getenv('MONGO_DB_URI') or 'mongodb+srv://iconichean:1Loye8PM3YwlV5h4@cluster0.meufk73.mongodb.net/mufra_fashions?retryWrites=true&w=majority'
client = MongoClient(MONGO_URI)
try:
    db = client.get_default_database()
except Exception:
    db = client['mufra_fashions']

orders = db.orders.find().sort('created_at', -1).limit(10)
for o in orders:
    print('ORDER:', o.get('order_id'), 'status:', o.get('status'), 'payment_status:', o.get('payment_status'))
    print(' user_id:', o.get('user_id'))
    print(' total:', o.get('total'))
    print(' created_at:', o.get('created_at'))
    print('---')
print('Done')
