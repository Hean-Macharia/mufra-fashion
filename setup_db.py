from flask import Flask
from flask_pymongo import PyMongo
import bcrypt
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config["MONGO_URI"] = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/mufra_fashions')

mongo = PyMongo(app)

def setup_database():
    with app.app_context():
        try:
            # Create indexes
            mongo.db.products.create_index([('name', 'text'), ('description', 'text')])
            mongo.db.orders.create_index('user_id')
            mongo.db.orders.create_index('status')
            mongo.db.orders.create_index('created_at')
            mongo.db.users.create_index('username', unique=True)
            
            print("Indexes created successfully")
            
            # Create admin user if not exists
            admin_exists = mongo.db.users.find_one({'username': 'admin'})
            if not admin_exists:
                hashed_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
                mongo.db.users.insert_one({
                    'username': 'admin',
                    'email': 'admin@mufrafashions.com',
                    'password': hashed_password,
                    'is_admin': True,
                    'created_at': datetime.utcnow()
                })
                print("✓ Admin user created")
                print("  Username: admin")
                print("  Password: admin123")
            else:
                print("✓ Admin user already exists")
            
            # Add sample products if none exist
            product_count = mongo.db.products.count_documents({})
            if product_count == 0:
                sample_products = [
                    {
                        'name': 'Men\'s Running Shoes',
                        'description': 'Comfortable running shoes for men with excellent cushioning',
                        'price': 45.99,
                        'category': 'shoes',
                        'subcategory': 'new',
                        'sizes': ['8', '9', '10', '11'],
                        'colors': ['black', 'blue', 'white'],
                        'stock': 50,
                        'images': ['https://images.unsplash.com/photo-1542291026-7eec264c27ff?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'],
                        'created_at': datetime.utcnow(),
                        'is_active': True
                    },
                    {
                        'name': 'Women\'s Casual Dress',
                        'description': 'Elegant casual dress for women, perfect for summer',
                        'price': 35.50,
                        'category': 'clothes',
                        'subcategory': 'new',
                        'sizes': ['S', 'M', 'L', 'XL'],
                        'colors': ['red', 'black', 'blue'],
                        'stock': 30,
                        'images': ['https://images.unsplash.com/photo-1595777457583-95e059d581b8?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'],
                        'created_at': datetime.utcnow(),
                        'is_active': True
                    },
                    {
                        'name': 'Second-hand Leather Jacket',
                        'description': 'Good condition leather jacket, slightly worn',
                        'price': 25.00,
                        'category': 'clothes',
                        'subcategory': 'secondhand',
                        'sizes': ['M', 'L'],
                        'colors': ['brown', 'black'],
                        'stock': 5,
                        'images': ['https://images.unsplash.com/photo-1551028719-00167b16eac5?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'],
                        'created_at': datetime.utcnow(),
                        'is_active': True
                    },
                    {
                        'name': 'Basketball Sneakers',
                        'description': 'High-performance basketball shoes',
                        'price': 65.99,
                        'category': 'shoes',
                        'subcategory': 'new',
                        'sizes': ['7', '8', '9', '10', '11', '12'],
                        'colors': ['white', 'red', 'blue'],
                        'stock': 25,
                        'images': ['https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'],
                        'created_at': datetime.utcnow(),
                        'is_active': True
                    },
                    {
                        'name': 'Denim Jeans',
                        'description': 'Classic blue denim jeans',
                        'price': 29.99,
                        'category': 'clothes',
                        'subcategory': 'new',
                        'sizes': ['28', '30', '32', '34', '36'],
                        'colors': ['blue', 'black'],
                        'stock': 40,
                        'images': ['https://images.unsplash.com/photo-1542272604-787c3835535d?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'],
                        'created_at': datetime.utcnow(),
                        'is_active': True
                    },
                    {
                        'name': 'Formal Shoes',
                        'description': 'Elegant formal shoes for business occasions',
                        'price': 55.00,
                        'category': 'shoes',
                        'subcategory': 'new',
                        'sizes': ['8', '9', '10', '11'],
                        'colors': ['black', 'brown'],
                        'stock': 20,
                        'images': ['https://images.unsplash.com/photo-1597045566677-8cf032ed6634?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'],
                        'created_at': datetime.utcnow(),
                        'is_active': True
                    }
                ]
                result = mongo.db.products.insert_many(sample_products)
                print(f"✓ {len(result.inserted_ids)} sample products added")
            else:
                print(f"✓ {product_count} products already exist in database")
            
            print("\n✅ Database setup completed successfully!")
            print("\nAccess the application at:")
            print("  Store: http://localhost:5000")
            print("  Admin: http://localhost:5000/admin/login")
            
        except Exception as e:
            print(f"❌ Error during database setup: {str(e)}")
            print("\nMake sure:")
            print("1. MongoDB is running")
            print("2. MONGODB_URI is correct in .env file")
            print("3. You have proper connection to MongoDB Atlas")

if __name__ == '__main__':
    setup_database()