from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import datetime
import random

# Use the same MONGO_URI as the app if available
MONGO_URI = os.getenv('MONGO_URI') or os.getenv('MONGO_DB_URI') or 'mongodb+srv://iconichean:1Loye8PM3YwlV5h4@cluster0.meufk73.mongodb.net/mufra_fashions?retryWrites=true&w=majority'
print('Using MONGO_URI:', MONGO_URI[:60] + '...')
client = MongoClient(MONGO_URI)
# Use default database from URI
try:
    db = client.get_default_database()
except Exception:
    db = client['mufra_fashions']

users = db.users
orders = db.orders
products = db.products

# Create test user
user_doc = {
    'first_name': 'Test',
    'last_name': 'User',
    'email': f'testuser+{random.randint(1000,9999)}@example.com',
    'password': 'hashed-placeholder',
    'role': 'user',
    'verified': True,
    'cart': [],
    'wishlist': [],
    'created_at': datetime.datetime.utcnow()
}
user_res = users.insert_one(user_doc)
user_id = user_res.inserted_id
print('Inserted user id:', user_id)

# Create test order
order_id = 'TEST' + ''.join([str(random.randint(0,9)) for _ in range(8)])
now = datetime.datetime.now(datetime.timezone.utc)
order_doc = {
    'order_id': order_id,
    'user_id': user_id,
    'items': [
        {
            'product_id': None,
            'name': 'Test Product',
            'price': 1500,
            'quantity': 1
        }
    ],
    'shipping_address': {
        'street': '123 Test Rd',
        'city': 'Test City',
        'county': 'Embu',
        'postal_code': '00100',
        'phone': '700000000'
    },
    'payment_method': 'paystack',
    'subtotal': 1500,
    'delivery_fee': 100,
    'total': 1600,
    'status': 'pending',
    'payment_status': 'pending',
    'paystack_reference': None,
    'created_at': now,
    'updated_at': now,
    'status_history': [
        {
            'status': 'pending',
            'timestamp': now,
            'updated_by': 'system'
        }
    ]
}
orders_res = orders.insert_one(order_doc)
print('Inserted order id:', order_id)
print('Order _id:', orders_res.inserted_id)
print('Done.')
