from flask_login import UserMixin
from datetime import datetime
from bson import ObjectId

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data.get('username')
        self.email = user_data.get('email')
        self.is_admin = user_data.get('is_admin', False)

class Product:
    @staticmethod
    def create(data):
        return {
            'name': data['name'],
            'description': data['description'],
            'price': float(data['price']),
            'category': data['category'],
            'subcategory': data.get('subcategory', 'new'),
            'sizes': data.get('sizes', []),
            'colors': data.get('colors', []),
            'images': data.get('images', []),
            'stock': int(data.get('stock', 0)),
            'created_at': datetime.utcnow(),
            'is_active': True
        }

class Order:
    @staticmethod
    def create(data):
        return {
            'user_id': data['user_id'],
            'items': data['items'],
            'total_amount': data['total_amount'],
            'shipping_address': data['shipping_address'],
            'delivery_fee': data['delivery_fee'],
            'payment_method': data['payment_method'],
            'payment_number': data['payment_number'],
            'status': 'pending',
            'created_at': datetime.utcnow()
        }