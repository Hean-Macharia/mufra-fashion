import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_pymongo import PyMongo
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from bson.objectid import ObjectId
from paystackapi.paystack import Paystack
import uuid
import base64
import json
from datetime import datetime
import bcrypt
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mufra-fashions-secret-key-2024')

# MongoDB Atlas Connection
MONGODB_URI = "mongodb+srv://iconichean:1Loye8PM3YwlV5h4@cluster0.meufk73.mongodb.net/mufra_fashions?retryWrites=true&w=majority"
app.config["MONGO_URI"] = MONGODB_URI

# Paystack Configuration
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY', 'sk_test_4d05b36c31bf5a4943a92c8ce13882a7859544bc')
PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY', 'pk_test_ba60dd518974e7639e8f78deb0d7dee3acb96133')
paystack_client = Paystack(secret_key=PAYSTACK_SECRET_KEY)

try:
    mongo = PyMongo(app)
    # Test connection
    mongo.db.command('ping')
    print("✅ MongoDB Atlas connection established!")
    db_connected = True
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")
    print("⚠️ Running in demo mode without database...")
    mongo = None
    db_connected = False

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

class User:
    def __init__(self, user_data):
        self.id = str(user_data.get('_id', 'demo'))
        self.username = user_data.get('username', '')
        self.email = user_data.get('email', '')
        self.is_admin = user_data.get('is_admin', False)
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return self.id

@login_manager.user_loader
def load_user(user_id):
    try:
        print(f"\n=== LOADING USER: {user_id} ===")
        
        if db_connected:
            user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            if user_data:
                print(f"User found in DB: {user_data['username']}")
                return User(user_data)
        
        # Check session for demo admin
        if user_id == 'demo_admin_id' or (session.get('is_admin') and session.get('user_id') == user_id):
            print("Loading demo admin from session")
            return User({
                '_id': user_id,
                'username': 'admin',
                'email': 'admin@mufrafashions.com',
                'is_admin': True
            })
            
    except Exception as e:
        print(f"Error loading user: {e}")
    
    print("No user found")
    return None

def initialize_database():
    """Initialize database with admin user if not exists"""
    if not db_connected:
        print("⚠️ Using demo mode - no database connection")
        return
    
    try:
        print("🔧 Setting up database...")
        
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
            print("✅ Admin user created (admin/admin123)")
        else:
            print("✅ Admin user exists")
        
        # Check if sample products exist
        product_count = mongo.db.products.count_documents({})
        if product_count == 0:
            sample_products = [
                {
                    '_id': ObjectId(),
                    'name': 'Men\'s Running Shoes',
                    'description': 'Comfortable running shoes for men',
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
                    '_id': ObjectId(),
                    'name': 'Women\'s Casual Dress',
                    'description': 'Elegant casual dress for women',
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
                    '_id': ObjectId(),
                    'name': 'Second-hand Leather Jacket',
                    'description': 'Good condition leather jacket',
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
                    '_id': ObjectId(),
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
                }
            ]
            mongo.db.products.insert_many(sample_products)
            print(f"✅ Added {len(sample_products)} sample products")
        
        print("🎉 Database setup complete!")
        
    except Exception as e:
        print(f"⚠️ Database setup warning: {e}")

# ========== CONTEXT PROCESSORS ==========
@app.context_processor
def inject_current_time():
    return {'current_time': datetime.now().strftime('%B %d, %Y %I:%M %p')}

@app.context_processor
def inject_total_revenue():
    if db_connected:
        try:
            pipeline = [
                {'$match': {'status': {'$in': ['completed', 'delivered']}}},
                {'$group': {'_id': None, 'total': {'$sum': '$total_amount'}}}
            ]
            result = list(mongo.db.orders.aggregate(pipeline))
            total_revenue = result[0]['total'] if result else 0
        except:
            total_revenue = 0
    else:
        total_revenue = len(session.get('orders', [])) * 100
    
    return {'total_revenue': total_revenue}

@app.context_processor
def inject_total_value():
    if db_connected:
        try:
            pipeline = [
                {'$group': {'_id': None, 'total': {'$sum': {'$multiply': ['$price', '$stock']}}}}
            ]
            result = list(mongo.db.products.aggregate(pipeline))
            total_value = result[0]['total'] if result else 0
        except:
            total_value = 0
    else:
        total_value = 1500  # Demo value
    
    return {'total_value': total_value}

class MpesaService:
    def __init__(self, consumer_key, consumer_secret, environment='sandbox'):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.environment = environment
        
        if environment == 'production':
            self.base_url = 'https://api.safaricom.co.ke'
        else:
            self.base_url = 'https://sandbox.safaricom.co.ke'
        
        self.access_token = None
        self.token_expiry = None

    def get_access_token(self):
        """Get M-Pesa API access token"""
        try:
            # Encode consumer key and secret
            auth_string = f"{self.consumer_key}:{self.consumer_secret}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_auth}'
            }
            
            url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.token_expiry = datetime.now().timestamp() + int(data.get('expires_in', 3600))
                return self.access_token
            else:
                print(f"M-Pesa token error: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting M-Pesa token: {e}")
            return None

    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """Initiate STK Push payment"""
        try:
            # Get access token if not available or expired
            if not self.access_token or (self.token_expiry and datetime.now().timestamp() > self.token_expiry):
                self.get_access_token()
            
            if not self.access_token:
                return {'success': False, 'error': 'Failed to authenticate with M-Pesa'}
            
            # Format phone number
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            elif phone_number.startswith('+254'):
                phone_number = phone_number[1:]
            elif phone_number.startswith('254'):
                pass  # Already correct
            else:
                phone_number = '254' + phone_number
            
            # Remove any spaces or dashes
            phone_number = phone_number.replace(' ', '').replace('-', '')
            
            # For sandbox, use test credentials
            if self.environment == 'sandbox':
                business_shortcode = '174379'
                passkey = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
                callback_url = 'https://mufra-fashion.onrender.com/callback/mpesa'
            else:
                business_shortcode = 'YOUR_BUSINESS_SHORTCODE'
                passkey = 'YOUR_PASSKEY'
                callback_url = 'https://mufra-fashion.onrender.com/callback/mpesa'
            
            # Generate timestamp
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Generate password
            password_string = f"{business_shortcode}{passkey}{timestamp}"
            password = base64.b64encode(password_string.encode()).decode()
            
            # STK Push request
            stk_url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'BusinessShortCode': business_shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': int(amount),
                'PartyA': phone_number,
                'PartyB': business_shortcode,
                'PhoneNumber': phone_number,
                'CallBackURL': callback_url,
                'AccountReference': account_reference,
                'TransactionDesc': transaction_desc
            }
            
            response = requests.post(stk_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ResponseCode') == '0':
                    return {
                        'success': True,
                        'checkout_request_id': data.get('CheckoutRequestID'),
                        'customer_message': data.get('CustomerMessage'),
                        'merchant_request_id': data.get('MerchantRequestID')
                    }
                else:
                    return {
                        'success': False,
                        'error': data.get('ResponseDescription', 'STK Push failed')
                    }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

class AirtelMoneyService:
    def __init__(self, client_id, client_secret, environment='sandbox'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment
        
        if environment == 'production':
            self.base_url = 'https://openapi.airtel.africa'
        else:
            self.base_url = 'https://openapiuat.airtel.africa'
        
        self.access_token = None

    def get_access_token(self):
        """Get Airtel Money API access token"""
        try:
            url = f"{self.base_url}/auth/oauth2/token"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials'
            }
            
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                return self.access_token
            else:
                print(f"Airtel token error: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting Airtel token: {e}")
            return None

    def initiate_payment(self, msisdn, amount, transaction_id, callback_url):
        """Initiate Airtel Money payment"""
        try:
            if not self.access_token:
                self.get_access_token()
            
            if not self.access_token:
                return {'success': False, 'error': 'Failed to authenticate with Airtel'}
            
            # Format phone number
            if msisdn.startswith('0'):
                msisdn = '254' + msisdn[1:]
            elif msisdn.startswith('+254'):
                msisdn = msisdn[1:]
            
            url = f"{self.base_url}/merchant/v1/payments/"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'X-Country': 'KE',
                'X-Currency': 'KES'
            }
            
            payload = {
                'reference': transaction_id,
                'subscriber': {
                    'country': 'KE',
                    'currency': 'KES',
                    'msisdn': msisdn
                },
                'transaction': {
                    'amount': str(amount),
                    'country': 'KE',
                    'currency': 'KES',
                    'id': transaction_id
                }
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('status', {}).get('code') == '200':
                    return {
                        'success': True,
                        'transaction_id': transaction_id,
                        'message': 'Payment request sent to customer'
                    }
                else:
                    return {
                        'success': False,
                        'error': data.get('status', {}).get('message', 'Payment failed')
                    }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

# ========== HELPER FUNCTIONS ==========
def get_demo_products():
    """Return demo products for testing"""
    print("Loading DEMO products")
    return [
        {
            '_id': '1',
            'name': 'Men\'s Running Shoes',
            'description': 'Comfortable running shoes for daily use',
            'price': 45.99,
            'category': 'shoes',
            'subcategory': 'new',
            'images': ['https://images.unsplash.com/photo-1542291026-7eec264c27ff?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80']
        },
        {
            '_id': '2',
            'name': 'Women\'s Casual Dress',
            'description': 'Elegant dress for casual occasions',
            'price': 35.50,
            'category': 'clothes',
            'subcategory': 'new',
            'images': ['https://images.unsplash.com/photo-1595777457583-95e059d581b8?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80']
        },
        {
            '_id': '3',
            'name': 'Leather Jacket',
            'description': 'Stylish second-hand leather jacket',
            'price': 25.00,
            'category': 'clothes',
            'subcategory': 'secondhand',
            'images': ['https://images.unsplash.com/photo-1551028719-00167b16eac5?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80']
        },
        {
            '_id': '4',
            'name': 'Basketball Sneakers',
            'description': 'High-performance sports shoes',
            'price': 65.99,
            'category': 'shoes',
            'subcategory': 'new',
            'images': ['https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80']
        }
    ]

def get_filtered_demo_products(category, subcategory):
    """Return filtered demo products"""
    products = [
        {'_id': '1', 'name': 'Men\'s Running Shoes', 'price': 45.99, 'category': 'shoes', 'subcategory': 'new',
         'images': ['https://images.unsplash.com/photo-1542291026-7eec264c27ff?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80']},
        {'_id': '2', 'name': 'Women\'s Casual Dress', 'price': 35.50, 'category': 'clothes', 'subcategory': 'new',
         'images': ['https://images.unsplash.com/photo-1595777457583-95e059d581b8?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80']},
        {'_id': '3', 'name': 'Leather Jacket', 'price': 25.00, 'category': 'clothes', 'subcategory': 'secondhand',
         'images': ['https://images.unsplash.com/photo-1551028719-00167b16eac5?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80']},
        {'_id': '4', 'name': 'Basketball Sneakers', 'price': 65.99, 'category': 'shoes', 'subcategory': 'new',
         'images': ['https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80']}
    ]
    
    # Filter demo products
    filtered = []
    for p in products:
        if category != 'all' and p.get('category') != category:
            continue
        if subcategory != 'all' and p.get('subcategory', 'new') != subcategory:
            continue
        filtered.append(p)
    
    return filtered

def get_demo_product(product_id):
    """Return a demo product"""
    return {
        '_id': product_id, 
        'name': 'Sample Product', 
        'price': 29.99, 
        'description': 'This is a sample product description.',
        'sizes': ['S', 'M', 'L'], 
        'colors': ['Red', 'Blue', 'Black'],
        'stock': 10, 
        'images': ['https://via.placeholder.com/500'],
        'category': 'clothes',
        'subcategory': 'new'
    }

# ========== MAIN ROUTES ==========
@app.route('/')
def home():
    print("\n" + "="*50)
    print("HOME PAGE REQUEST")
    print("="*50)
    
    try:
        if db_connected:
            print("Database is CONNECTED")
            
            # Try to get products
            products = list(mongo.db.products.find({'is_active': True}).limit(8))
            print(f"Found {len(products)} products in database")
            
            if not products:
                print("No products found in database, using demo products")
                products = get_demo_products()
            else:
                # Log each product
                for i, p in enumerate(products):
                    print(f"Product {i+1}: ID={p.get('_id')}, Name='{p.get('name')}', Price={p.get('price')}")
        else:
            print("Database is NOT connected, using demo mode")
            products = get_demo_products()
            
    except Exception as e:
        print(f"ERROR loading products: {e}")
        products = get_demo_products()
    
    print(f"Rendering template with {len(products)} products")
    print("="*50 + "\n")
    
    return render_template('index.html', products=products)

@app.route('/callback/paystack/mobile', methods=['POST'])
def paystack_mobile_callback():
    """Handle Paystack mobile money callback (webhook)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
        
        event = data.get('event')
        
        if event == 'charge.success':
            # Payment successful
            charge_data = data.get('data', {})
            reference = charge_data.get('reference')
            
            if not reference:
                return jsonify({'status': 'error', 'message': 'No reference'}), 400
            
            # Find the order
            if db_connected:
                order = mongo.db.orders.find_one({'reference': reference})
                if not order:
                    # Try alternative reference field
                    order = mongo.db.orders.find_one({'paystack_mobile_ref': reference})
            else:
                order = None
                if 'orders' in session:
                    for o in session['orders']:
                        if o.get('reference') == reference or o.get('paystack_mobile_ref') == reference:
                            order = o
                            break
            
            if order:
                # Update order status
                update_data = {
                    'payment_status': 'completed',
                    'status': 'confirmed',
                    'transaction_id': charge_data.get('id'),
                    'paid_at': datetime.now(),
                    'payment_details': {
                        'channel': charge_data.get('channel', 'mobile_money'),
                        'mobile_money_provider': charge_data.get('authorization', {}).get('mobile_money_provider', 'unknown'),
                        'last4': charge_data.get('authorization', {}).get('last4', ''),
                        'paid_at': charge_data.get('paid_at', '')
                    }
                }
                
                if db_connected:
                    mongo.db.orders.update_one(
                        {'reference': reference},
                        {'$set': update_data}
                    )
                else:
                    # Update in session
                    if 'orders' in session:
                        for i, o in enumerate(session['orders']):
                            if o.get('reference') == reference or o.get('paystack_mobile_ref') == reference:
                                session['orders'][i].update(update_data)
                                session.modified = True
                                break
                
                print(f"✅ Mobile money payment completed for order: {order.get('order_id')}")
            
            return jsonify({'status': 'success'}), 200
        
        elif event == 'charge.failed':
            # Payment failed
            charge_data = data.get('data', {})
            reference = charge_data.get('reference')
            
            if reference:
                if db_connected:
                    mongo.db.orders.update_one(
                        {'reference': reference},
                        {'$set': {
                            'payment_status': 'failed',
                            'payment_error': charge_data.get('gateway_response', 'Payment failed'),
                            'updated_at': datetime.now()
                        }}
                    )
            
            return jsonify({'status': 'received'}), 200
        
        return jsonify({'status': 'ignored'}), 200
        
    except Exception as e:
        print(f"❌ Paystack mobile callback error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400
    
@app.route('/api/check_payment_status/<order_id>', methods=['GET'])
def check_payment_status(order_id):
    """Check payment status for an order (especially for mobile money)"""
    try:
        # Find the order
        if db_connected:
            order = mongo.db.orders.find_one({'order_id': order_id})
        else:
            order = None
            if 'orders' in session:
                for o in session['orders']:
                    if str(o.get('order_id')) == order_id:
                        order = o
                        break
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404
        
        # If order has a Paystack reference, check status with Paystack
        reference = order.get('reference') or order.get('paystack_ref') or order.get('paystack_mobile_ref')
        
        if reference and order.get('payment_status') in ['pending', 'processing']:
            try:
                # Check with Paystack API
                url = f"https://api.paystack.co/transaction/verify/{reference}"
                headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
                
                response = requests.get(url, headers=headers)
                result = response.json()
                
                if response.status_code == 200 and result.get('status'):
                    transaction_data = result.get('data', {})
                    
                    if transaction_data.get('status') == 'success':
                        # Payment successful
                        update_data = {
                            'payment_status': 'completed',
                            'status': 'confirmed',
                            'transaction_id': transaction_data.get('id'),
                            'paid_at': datetime.now()
                        }
                        
                        if db_connected:
                            mongo.db.orders.update_one(
                                {'order_id': order_id},
                                {'$set': update_data}
                            )
                        else:
                            if 'orders' in session:
                                for i, o in enumerate(session['orders']):
                                    if str(o.get('order_id')) == order_id:
                                        session['orders'][i].update(update_data)
                                        session.modified = True
                                        break
                        
                        return jsonify({
                            'success': True,
                            'status': 'completed',
                            'message': 'Payment completed successfully',
                            'order_status': 'confirmed'
                        })
                    
                    elif transaction_data.get('status') == 'failed':
                        # Payment failed
                        update_data = {
                            'payment_status': 'failed',
                            'payment_error': transaction_data.get('gateway_response', 'Payment failed')
                        }
                        
                        if db_connected:
                            mongo.db.orders.update_one(
                                {'order_id': order_id},
                                {'$set': update_data}
                            )
                        
                        return jsonify({
                            'success': True,
                            'status': 'failed',
                            'message': transaction_data.get('gateway_response', 'Payment failed'),
                            'order_status': 'pending'
                        })
                    
                    elif transaction_data.get('status') in ['pending', 'send_pending']:
                        # Still pending
                        return jsonify({
                            'success': True,
                            'status': 'processing',
                            'message': 'Payment request sent. Please check your phone.',
                            'order_status': 'pending'
                        })
                
            except Exception as e:
                print(f"Error checking payment status with Paystack: {e}")
                # Continue to return current status
        
        # Return current status
        return jsonify({
            'success': True,
            'status': order.get('payment_status', 'pending'),
            'order_status': order.get('status', 'pending'),
            'message': order.get('paystack_response', '')
        })
        
    except Exception as e:
        print(f"❌ Error checking payment status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
def verify_paystack_webhook(request):
    """Verify that webhook is from Paystack"""
    try:
        signature = request.headers.get('x-paystack-signature')
        if not signature:
            return False
        
        # In production, you should verify the signature
        # For now, we'll accept all webhooks in test mode
        # You should implement proper signature verification in production
        return True
        
    except Exception as e:
        print(f"Webhook verification error: {e}")
        return False



def handle_successful_payment(data):
    """Handle successful payment from webhook"""
    try:
        charge_data = data.get('data', {})
        reference = charge_data.get('reference')
        
        if not reference:
            return jsonify({'status': 'error', 'message': 'No reference'}), 400
        
        # Find order by reference
        if db_connected:
            order = mongo.db.orders.find_one({'$or': [
                {'reference': reference},
                {'paystack_ref': reference},
                {'paystack_mobile_ref': reference}
            ]})
        else:
            order = None
            if 'orders' in session:
                for o in session['orders']:
                    if (o.get('reference') == reference or 
                        o.get('paystack_ref') == reference or
                        o.get('paystack_mobile_ref') == reference):
                        order = o
                        break
        
        if order:
            # Update order
            update_data = {
                'payment_status': 'completed',
                'status': 'confirmed',
                'transaction_id': charge_data.get('id'),
                'paid_at': datetime.now(),
                'webhook_processed': True
            }
            
            if db_connected:
                mongo.db.orders.update_one(
                    {'_id': order['_id']},
                    {'$set': update_data}
                )
            else:
                if 'orders' in session:
                    for i, o in enumerate(session['orders']):
                        if str(o.get('_id')) == str(order.get('_id')):
                            session['orders'][i].update(update_data)
                            session.modified = True
                            break
            
            print(f"✅ Webhook: Order {order.get('order_id')} marked as paid")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Error handling successful payment: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/categories')
def categories():
    category = request.args.get('category', 'all')
    subcategory = request.args.get('subcategory', 'all')
    
    if db_connected:
        try:
            query = {'is_active': True}
            if category != 'all':
                query['category'] = category
            if subcategory != 'all':
                query['subcategory'] = subcategory
            
            products = list(mongo.db.products.find(query))
        except:
            products = get_filtered_demo_products(category, subcategory)
    else:
        products = get_filtered_demo_products(category, subcategory)
    
    return render_template('categories.html', 
                         products=products, 
                         selected_category=category, 
                         selected_subcategory=subcategory)

@app.route('/product/<product_id>')
def product_detail(product_id):
    if db_connected:
        try:
            product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
            if not product:
                product = get_demo_product(product_id)
            reviews = []
        except:
            product = get_demo_product(product_id)
            reviews = []
    else:
        product = get_demo_product(product_id)
        reviews = []
    
    return render_template('product.html', product=product, reviews=reviews)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'cart' not in session:
        session['cart'] = []
    
    try:
        product_id = request.form.get('product_id')
        quantity = int(request.form.get('quantity', 1))
        size = request.form.get('size', '')
        color = request.form.get('color', '')
        
        # Check if already in cart
        for item in session['cart']:
            if (item['product_id'] == product_id and 
                item.get('size') == size and 
                item.get('color') == color):
                item['quantity'] += quantity
                session.modified = True
                return jsonify({'success': True, 'cart_count': len(session['cart'])})
        
        # Add new item
        session['cart'].append({
            'product_id': product_id,
            'quantity': quantity,
            'size': size,
            'color': color,
            'added_at': datetime.now().isoformat()
        })
        session.modified = True
        
        return jsonify({'success': True, 'cart_count': len(session['cart'])})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/cart')
def cart():
    cart_items = []
    total = 0
    
    # Get products from database or use demo
    for item in session.get('cart', []):
        if db_connected:
            try:
                product = mongo.db.products.find_one({'_id': ObjectId(item['product_id'])})
                if product:
                    item_total = product['price'] * item['quantity']
                    cart_items.append({
                        'product': product,
                        'quantity': item['quantity'],
                        'size': item.get('size', ''),
                        'color': item.get('color', ''),
                        'item_total': item_total
                    })
                    total += item_total
            except:
                continue
        else:
            # Demo product
            product = get_demo_product(item['product_id'])
            item_total = product['price'] * item['quantity']
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'size': item.get('size', ''),
                'color': item.get('color', ''),
                'item_total': item_total
            })
            total += item_total
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # Redirect if cart is empty
    if 'cart' not in session or not session['cart']:
        return redirect(url_for('cart'))

    # Initialize discount to 0
    discount = 0

    if request.method == 'POST':
        try:
            # Calculate cart total and prepare items
            cart_items = []
            cart_total = 0
            
            for item in session['cart']:
                if db_connected:
                    product = mongo.db.products.find_one({'_id': ObjectId(item['product_id'])})
                    if product:
                        item_total = product['price'] * item['quantity']
                        cart_items.append({
                            'product_id': str(product['_id']),
                            'name': product['name'],
                            'price': product['price'],
                            'quantity': item['quantity'],
                            'size': item.get('size', ''),
                            'color': item.get('color', ''),
                            'item_total': item_total
                        })
                        cart_total += item_total
                else:
                    # Demo product
                    demo_price = 29.99
                    item_total = demo_price * item['quantity']
                    cart_items.append({
                        'product_id': item['product_id'],
                        'name': f"Product {item['product_id']}",
                        'price': demo_price,
                        'quantity': item['quantity'],
                        'size': item.get('size', ''),
                        'color': item.get('color', ''),
                        'item_total': item_total
                    })
                    cart_total += item_total
            
            # Calculate delivery fee
            region = request.form.get('region', '').lower()
            delivery_fee = 0
            
            if region == 'embu':
                delivery_fee = 0
            elif region in ['meru', 'kirinyaga', 'tharakanithi']:
                delivery_fee = 150
            elif region == 'nairobi':
                delivery_fee = 200
            elif region == 'other':
                delivery_fee = 250
            else:
                delivery_fee = 150  # Default
            
            # Calculate total amount
            total_amount = cart_total + delivery_fee - discount
            
            # Get payment method
            payment_method = request.form.get('payment_method')
            
            # Validate required fields
            required_fields = ['name', 'phone', 'address', 'city', 'region', 'payment_method']
            for field in required_fields:
                if not request.form.get(field):
                    return render_template('checkout.html', 
                                         error=f"Please fill in all required fields. Missing: {field}",
                                         discount=discount)
            
            # Validate phone number
            phone = request.form.get('phone')
            if len(phone.replace(' ', '').replace('-', '')) < 10:
                return render_template('checkout.html',
                                     error="Please enter a valid phone number",
                                     discount=discount)
            
            # Validate email if provided
            email = request.form.get('email')
            if email and '@' not in email:
                return render_template('checkout.html',
                                     error="Please enter a valid email address",
                                     discount=discount)
            
            # Validate payment method specific fields
            if payment_method == 'mpesa':
                mpesa_number = request.form.get('mpesa_number')
                if not mpesa_number:
                    return render_template('checkout.html',
                                         error="Please enter your M-Pesa number",
                                         discount=discount)
            
            elif payment_method == 'airtel':
                airtel_number = request.form.get('airtel_number')
                if not airtel_number:
                    return render_template('checkout.html',
                                         error="Please enter your Airtel Money number",
                                         discount=discount)
            
            elif payment_method == 'paystack' and not email:
                return render_template('checkout.html',
                                     error="Email is required for Paystack payments",
                                     discount=discount)
            
            # Check terms agreement
            if not request.form.get('terms'):
                return render_template('checkout.html',
                                     error="You must agree to the terms and conditions",
                                     discount=discount)
            
            # Build order data
            order_id = f"MUFRA{datetime.now().strftime('%Y%m%d%H%M%S')}"
            order_data = {
                '_id': order_id,
                'order_id': order_id,
                'name': request.form.get('name'),
                'email': request.form.get('email', ''),
                'phone': request.form.get('phone'),
                'address': request.form.get('address'),
                'city': request.form.get('city'),
                'region': request.form.get('region'),
                'payment_method': payment_method,
                'payment_number': request.form.get('mpesa_number') or request.form.get('airtel_number') or '',
                'delivery_fee': delivery_fee,
                'cart_total': cart_total,
                'discount': discount,
                'total_amount': total_amount,
                'items': cart_items,
                'status': 'pending',
                'payment_status': 'pending',
                'created_at': datetime.now(),
                'session_id': session.sid,
                'user_id': session.get('user_id')
            }
            
            # Handle different payment methods
            if payment_method == 'paystack':
                # Handle Paystack card/bank payments
                try:
                    # Generate a unique reference
                    paystack_ref = f"MUFRA{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
                    
                    # Create callback URL
                    callback_url = url_for('paystack_callback', _external=True)
                    
                    # For Paystack, we need an email
                    customer_email = email or f"customer_{order_data['phone']}@mufrafashions.com"
                    
                    # Create transaction
                    response = paystack_client.transaction.initialize(
                        amount=int(total_amount * 100),  # Convert to kobo (smallest currency unit)
                        email=customer_email,
                        reference=paystack_ref,
                        callback_url=callback_url,
                        metadata={
                            'order_id': order_data['order_id'],
                            'customer_name': order_data['name'],
                            'phone': order_data['phone']
                        }
                    )
                    
                    if response['status']:
                        # Save order with Paystack reference
                        order_data['paystack_ref'] = paystack_ref
                        order_data['paystack_access_code'] = response['data']['access_code']
                        order_data['paystack_authorization_url'] = response['data']['authorization_url']
                        
                        # Save order to database or session
                        if db_connected:
                            mongo.db.orders.insert_one(order_data)
                        else:
                            if 'orders' not in session:
                                session['orders'] = []
                            session['orders'].append(order_data)
                            session.modified = True
                        
                        # Store order ID in session for verification
                        session['pending_order_id'] = order_data['order_id']
                        
                        # Redirect to Paystack payment page
                        return redirect(response['data']['authorization_url'])
                    else:
                        return render_template('checkout.html', 
                                             error=f"Payment initialization failed: {response.get('message', 'Unknown error')}",
                                             discount=discount)
                        
                except Exception as e:
                    print(f"❌ Paystack error: {e}")
                    return render_template('checkout.html', 
                                         error=f"Payment processing error: {str(e)}",
                                         discount=discount)
            
            elif payment_method == 'mpesa':
                # Handle M-Pesa through Paystack STK Push
                mpesa_number = request.form.get('mpesa_number')
                if not mpesa_number:
                    return render_template('checkout.html',
                                         error="Please enter your M-Pesa number",
                                         discount=discount)
                
                # Format phone number for Paystack
                phone = mpesa_number.replace('+254', '').replace(' ', '').replace('-', '')
                if phone.startswith('0'):
                    phone = phone[1:]  # Remove leading 0
                phone = '254' + phone  # Add 254 prefix
                
                try:
                    # Generate a unique reference
                    paystack_ref = f"MUFRA-MPESA-{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
                    
                    # Paystack mobile money API endpoint
                    url = "https://api.paystack.co/charge"
                    
                    headers = {
                        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "email": email or f"customer_{order_data['phone']}@mufrafashions.com",
                        "amount": int(total_amount * 100),  # Convert to kobo
                        "mobile_money": {
                            "phone": phone,
                            "provider": "mpesa"
                        },
                        "reference": paystack_ref,
                        "callback_url": url_for('paystack_webhook', _external=True),
                        "metadata": {
                            "order_id": order_data['order_id'],
                            "customer_name": order_data['name'],
                            "payment_method": "mpesa",
                            "phone": phone
                        }
                    }
                    
                    print(f"📱 Initiating M-Pesa payment for order {order_id}")
                    print(f"📞 Phone: {phone}, Amount: {total_amount}")
                    
                    response = requests.post(url, json=payload, headers=headers)
                    result = response.json()
                    
                    print(f"📨 Paystack M-Pesa response: {result}")
                    
                    if response.status_code == 200 and result.get('status'):
                        data = result.get('data', {})
                        
                        if data.get('status') == 'success':
                            # Payment already completed (rare for mobile money)
                            order_data['payment_status'] = 'completed'
                            order_data['status'] = 'confirmed'
                            order_data['transaction_id'] = data.get('id')
                            order_data['reference'] = paystack_ref
                            order_data['paid_at'] = datetime.now()
                            order_data['paystack_response'] = data.get('message', 'Payment successful')
                            
                        elif data.get('status') in ['pending', 'send_pending']:
                            # STK Push sent, waiting for user to complete
                            order_data['payment_status'] = 'processing'
                            order_data['status'] = 'pending'
                            order_data['reference'] = paystack_ref
                            order_data['stk_push_sent'] = True
                            order_data['paystack_mobile_ref'] = paystack_ref
                            order_data['paystack_response'] = data.get('message', 'STK Push sent')
                            order_data['display_text'] = data.get('display_text', 'Enter your M-Pesa PIN to complete payment')
                            
                        else:
                            error_msg = result.get('message', data.get('gateway_response', 'M-Pesa payment failed'))
                            print(f"❌ M-Pesa payment error: {error_msg}")
                            return render_template('checkout.html',
                                                 error=f"M-Pesa payment failed: {error_msg}",
                                                 discount=discount)
                    else:
                        error_msg = result.get('message', 'Payment initialization failed')
                        print(f"❌ M-Pesa API error: {error_msg}")
                        return render_template('checkout.html',
                                             error=f"M-Pesa payment failed: {error_msg}",
                                             discount=discount)
                    
                    # Save order
                    if db_connected:
                        mongo.db.orders.insert_one(order_data)
                    else:
                        if 'orders' not in session:
                            session['orders'] = []
                        session['orders'].append(order_data)
                        session.modified = True
                    
                    # Clear cart
                    session.pop('cart', None)
                    
                    return redirect(url_for('order_confirmation', order_id=order_data['order_id']))
                    
                except Exception as e:
                    print(f"❌ M-Pesa Paystack error: {e}")
                    # Still save order but mark as pending
                    order_data['payment_status'] = 'pending'
                    order_data['payment_error'] = str(e)
                    
                    # Save order anyway
                    if db_connected:
                        mongo.db.orders.insert_one(order_data)
                    else:
                        if 'orders' not in session:
                            session['orders'] = []
                        session['orders'].append(order_data)
                        session.modified = True
                    
                    # Clear cart
                    session.pop('cart', None)
                    
                    return redirect(url_for('order_confirmation', order_id=order_data['order_id']))
            
            elif payment_method == 'airtel':
                # Handle Airtel Money through Paystack STK Push
                airtel_number = request.form.get('airtel_number')
                if not airtel_number:
                    return render_template('checkout.html',
                                         error="Please enter your Airtel Money number",
                                         discount=discount)
                
                # Format phone number for Paystack
                phone = airtel_number.replace('+254', '').replace(' ', '').replace('-', '')
                if phone.startswith('0'):
                    phone = phone[1:]  # Remove leading 0
                phone = '254' + phone  # Add 254 prefix
                
                try:
                    # Generate a unique reference
                    paystack_ref = f"MUFRA-AIRTEL-{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
                    
                    # Paystack mobile money API endpoint
                    url = "https://api.paystack.co/charge"
                    
                    headers = {
                        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "email": email or f"customer_{order_data['phone']}@mufrafashions.com",
                        "amount": int(total_amount * 100),  # Convert to kobo
                        "mobile_money": {
                            "phone": phone,
                            "provider": "airtel"
                        },
                        "reference": paystack_ref,
                        "callback_url": url_for('paystack_webhook', _external=True),
                        "metadata": {
                            "order_id": order_data['order_id'],
                            "customer_name": order_data['name'],
                            "payment_method": "airtel",
                            "phone": phone
                        }
                    }
                    
                    print(f"📱 Initiating Airtel Money payment for order {order_id}")
                    print(f"📞 Phone: {phone}, Amount: {total_amount}")
                    
                    response = requests.post(url, json=payload, headers=headers)
                    result = response.json()
                    
                    print(f"📨 Paystack Airtel response: {result}")
                    
                    if response.status_code == 200 and result.get('status'):
                        data = result.get('data', {})
                        
                        if data.get('status') == 'success':
                            # Payment already completed
                            order_data['payment_status'] = 'completed'
                            order_data['status'] = 'confirmed'
                            order_data['transaction_id'] = data.get('id')
                            order_data['reference'] = paystack_ref
                            order_data['paid_at'] = datetime.now()
                            order_data['paystack_response'] = data.get('message', 'Payment successful')
                            
                        elif data.get('status') in ['pending', 'send_pending']:
                            # Payment request sent, waiting for user
                            order_data['payment_status'] = 'processing'
                            order_data['status'] = 'pending'
                            order_data['reference'] = paystack_ref
                            order_data['stk_push_sent'] = True
                            order_data['paystack_mobile_ref'] = paystack_ref
                            order_data['paystack_response'] = data.get('message', 'Payment request sent')
                            order_data['display_text'] = data.get('display_text', 'Enter your Airtel Money PIN to complete payment')
                            
                        else:
                            error_msg = result.get('message', data.get('gateway_response', 'Airtel payment failed'))
                            print(f"❌ Airtel payment error: {error_msg}")
                            return render_template('checkout.html',
                                                 error=f"Airtel Money payment failed: {error_msg}",
                                                 discount=discount)
                    else:
                        error_msg = result.get('message', 'Payment initialization failed')
                        print(f"❌ Airtel API error: {error_msg}")
                        return render_template('checkout.html',
                                             error=f"Airtel Money payment failed: {error_msg}",
                                             discount=discount)
                    
                    # Save order
                    if db_connected:
                        mongo.db.orders.insert_one(order_data)
                    else:
                        if 'orders' not in session:
                            session['orders'] = []
                        session['orders'].append(order_data)
                        session.modified = True
                    
                    # Clear cart
                    session.pop('cart', None)
                    
                    return redirect(url_for('order_confirmation', order_id=order_data['order_id']))
                    
                except Exception as e:
                    print(f"❌ Airtel Paystack error: {e}")
                    # Still save order but mark as pending
                    order_data['payment_status'] = 'pending'
                    order_data['payment_error'] = str(e)
                    
                    # Save order anyway
                    if db_connected:
                        mongo.db.orders.insert_one(order_data)
                    else:
                        if 'orders' not in session:
                            session['orders'] = []
                        session['orders'].append(order_data)
                        session.modified = True
                    
                    # Clear cart
                    session.pop('cart', None)
                    
                    return redirect(url_for('order_confirmation', order_id=order_data['order_id']))
            
            else:
                # For Cash on Delivery and other methods
                if payment_method == 'cod':
                    order_data['payment_status'] = 'pending_cod'
                elif payment_method in ['mpesa', 'airtel']:
                    order_data['payment_status'] = 'processing'
                
                # Save order
                if db_connected:
                    mongo.db.orders.insert_one(order_data)
                else:
                    if 'orders' not in session:
                        session['orders'] = []
                    session['orders'].append(order_data)
                    session.modified = True
                
                # Clear cart
                session.pop('cart', None)
                
                return redirect(url_for('order_confirmation', order_id=order_data['order_id']))

        except Exception as e:
            print(f"❌ Checkout error: {e}")
            import traceback
            traceback.print_exc()
            return render_template('checkout.html', error=str(e), discount=discount)

    # GET request → show checkout form with cart data
    cart_items = []
    cart_total = 0
    
    for item in session.get('cart', []):
        if db_connected:
            try:
                product = mongo.db.products.find_one({'_id': ObjectId(item['product_id'])})
                if product:
                    item_total = product['price'] * item['quantity']
                    cart_items.append({
                        'product': product,
                        'quantity': item['quantity'],
                        'size': item.get('size', ''),
                        'color': item.get('color', ''),
                        'item_total': item_total
                    })
                    cart_total += item_total
            except:
                continue
        else:
            # Demo product
            product = get_demo_product(item['product_id'])
            item_total = product['price'] * item['quantity']
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'size': item.get('size', ''),
                'color': item.get('color', ''),
                'item_total': item_total
            })
            cart_total += item_total
    
    return render_template('checkout.html', 
                         cart_items=cart_items,
                         cart_total=cart_total,
                         discount=discount)
@app.route('/paystack/callback')
def paystack_callback():
    """Handle Paystack payment callback"""
    try:
        reference = request.args.get('reference')
        trxref = request.args.get('trxref')
        
        if not reference:
            return render_template('payment_error.html', 
                                 error="No payment reference provided")
        
        # Verify the transaction
        response = paystack_client.transaction.verify(reference)
        
        if response['status'] and response['data']['status'] == 'success':
            # Payment successful
            transaction_data = response['data']
            
            # Find the order using the reference
            if db_connected:
                order = mongo.db.orders.find_one({'paystack_ref': reference})
            else:
                order = None
                if 'orders' in session:
                    for o in session['orders']:
                        if o.get('paystack_ref') == reference:
                            order = o
                            break
            
            if order:
                # Update order status
                update_data = {
                    'status': 'paid',
                    'payment_status': 'completed',
                    'transaction_id': transaction_data['id'],
                    'paid_at': datetime.now(),
                    'payment_details': {
                        'channel': transaction_data.get('channel', ''),
                        'ip_address': transaction_data.get('ip_address', ''),
                        'paid_at': transaction_data.get('paid_at', ''),
                        'authorization': transaction_data.get('authorization', {})
                    }
                }
                
                if db_connected:
                    mongo.db.orders.update_one(
                        {'paystack_ref': reference},
                        {'$set': update_data}
                    )
                else:
                    # Update in session
                    if 'orders' in session:
                        for i, o in enumerate(session['orders']):
                            if o.get('paystack_ref') == reference:
                                session['orders'][i].update(update_data)
                                session.modified = True
                                break
                
                # Clear cart and pending order session
                session.pop('cart', None)
                session.pop('pending_order_id', None)
                
                return redirect(url_for('order_confirmation', 
                                      order_id=order['order_id']))
            else:
                return render_template('payment_error.html', 
                                     error="Order not found")
        else:
            # Payment failed
            error_message = response.get('message', 'Payment verification failed')
            return render_template('payment_error.html', 
                                 error=error_message)
            
    except Exception as e:
        print(f"❌ Paystack callback error: {e}")
        return render_template('payment_error.html', 
                             error=f"Payment processing error: {str(e)}")

@app.route('/paystack/webhook', methods=['POST'])
def paystack_webhook():
    """Handle Paystack webhook for server-to-server notifications (including mobile money)"""
    try:
        # Verify it's from Paystack (in production, verify signature)
        # For now, we'll trust the payload for testing
        
        data = request.get_json()
        event = data.get('event')
        
        print(f"📨 Paystack webhook received: {event}")
        
        if event == 'charge.success':
            charge_data = data.get('data', {})
            reference = charge_data.get('reference')
            
            if not reference:
                print("❌ No reference in webhook")
                return jsonify({'status': 'error', 'message': 'No reference'}), 400
            
            print(f"✅ Payment successful for reference: {reference}")
            
            # Find the order using the reference
            if db_connected:
                # Check all possible reference fields
                order = mongo.db.orders.find_one({'$or': [
                    {'paystack_ref': reference},
                    {'reference': reference},
                    {'paystack_mobile_ref': reference}
                ]})
            else:
                order = None
                if 'orders' in session:
                    for o in session['orders']:
                        if (o.get('paystack_ref') == reference or 
                            o.get('reference') == reference or
                            o.get('paystack_mobile_ref') == reference):
                            order = o
                            break
            
            if order:
                # Update order status
                update_data = {
                    'status': 'confirmed',
                    'payment_status': 'completed',
                    'transaction_id': charge_data.get('id'),
                    'paid_at': datetime.now(),
                    'webhook_processed': True,
                    'payment_details': {
                        'channel': charge_data.get('channel', ''),
                        'gateway_response': charge_data.get('gateway_response', ''),
                        'paid_at': charge_data.get('paid_at', ''),
                        'authorization': charge_data.get('authorization', {})
                    }
                }
                
                # Check if it's mobile money
                if charge_data.get('authorization', {}).get('channel') == 'mobile_money':
                    update_data['payment_details']['mobile_money_provider'] = charge_data.get('authorization', {}).get('mobile_money_provider', '')
                    update_data['payment_details']['mobile_money_number'] = charge_data.get('authorization', {}).get('mobile_money_number', '')
                
                if db_connected:
                    mongo.db.orders.update_one(
                        {'_id': order['_id']},
                        {'$set': update_data}
                    )
                else:
                    # Update in session
                    if 'orders' in session:
                        for i, o in enumerate(session['orders']):
                            if str(o.get('_id')) == str(order.get('_id')):
                                session['orders'][i].update(update_data)
                                session.modified = True
                                break
                
                print(f"✅ Webhook: Order {order.get('order_id')} marked as paid")
                
                # Clear cart if it exists in session
                if 'cart' in session:
                    session.pop('cart', None)
                    print("✅ Cart cleared after successful payment")
            
            else:
                print(f"⚠️ Order not found for reference: {reference}")
            
            return jsonify({'status': 'success'}), 200
        
        elif event == 'charge.failed':
            charge_data = data.get('data', {})
            reference = charge_data.get('reference')
            
            print(f"❌ Payment failed for reference: {reference}")
            
            if reference:
                if db_connected:
                    mongo.db.orders.update_one(
                        {'$or': [
                            {'paystack_ref': reference},
                            {'reference': reference},
                            {'paystack_mobile_ref': reference}
                        ]},
                        {'$set': {
                            'payment_status': 'failed',
                            'payment_error': charge_data.get('gateway_response', 'Payment failed'),
                            'updated_at': datetime.now()
                        }}
                    )
                    print(f"✅ Marked order as failed: {reference}")
            
            return jsonify({'status': 'received'}), 200
        
        return jsonify({'status': 'ignored'}), 200
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/order_confirmation/<order_id>')
def order_confirmation(order_id):
    order = None
    
    # Try to find order in database
    if db_connected:
        try:
            # Try by ObjectId first
            try:
                order = mongo.db.orders.find_one({'_id': ObjectId(order_id)})
            except:
                order = None
            
            # If not found, try by demo order ID format
            if not order:
                order = mongo.db.orders.find_one({'_id': order_id})
        except Exception as e:
            print(f"Error finding order in DB: {e}")
            order = None
    
    # If not in database, check session (for demo mode)
    if not order and 'orders' in session:
        for o in session['orders']:
            if str(o.get('_id')) == order_id:
                order = o
                break
    
    # If still no order, create demo order
    if not order:
        order = {
            '_id': order_id,
            'name': 'John Doe',
            'phone': '0712345678',
            'address': '123 Main Street',
            'city': 'Embu',
            'region': 'Embu',
            'payment_method': 'mpesa',
            'payment_number': '0712345678',
            'delivery_fee': 100,
            'cart_total': 59.98,
            'total_amount': 159.98,
            'items': [
                {
                    'name': 'Demo Product', 
                    'quantity': 2, 
                    'price': 29.99, 
                    'item_total': 59.98,
                    'size': 'M',
                    'color': 'Black'
                }
            ],
            'status': 'pending',
            'created_at': datetime.now()
        }
        print(f"⚠️ Using demo order data for: {order_id}")
    else:
        print(f"✅ Found order: {order_id}")
    
    # Convert ObjectId to string for template
    if '_id' in order and isinstance(order['_id'], ObjectId):
        order['_id'] = str(order['_id'])
    
    return render_template('order_confirmation.html', order=order)

@app.route('/my_orders')
def my_orders():
    orders = []
    
    if db_connected:
        try:
            # For logged-in users, get their orders
            if current_user.is_authenticated:
                orders = list(mongo.db.orders.find({
                    'user_id': current_user.id
                }).sort('created_at', -1))
                print(f"✅ Found {len(orders)} orders for user {current_user.id}")
            else:
                # For guest users, get by session ID
                orders = list(mongo.db.orders.find({
                    'session_id': session.sid
                }).sort('created_at', -1))
                print(f"✅ Found {len(orders)} orders for session {session.sid}")
        except Exception as e:
            print(f"❌ Error loading orders from DB: {e}")
    
    # Fallback to session orders for demo
    if not orders and 'orders' in session:
        orders = session['orders']
        print(f"✅ Found {len(orders)} orders in session")
    
    # Convert ObjectIds to strings for template
    for order in orders:
        if '_id' in order and isinstance(order['_id'], ObjectId):
            order['_id'] = str(order['_id'])
    
    return render_template('my_orders.html', orders=orders)

# ========== ADMIN ROUTES ==========
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    print(f"\n=== ADMIN LOGIN ATTEMPT ===")
    print(f"Current user authenticated: {current_user.is_authenticated}")
    print(f"Current user admin: {getattr(current_user, 'is_admin', False)}")
    
    if current_user.is_authenticated and getattr(current_user, 'is_admin', False):
        print("Already logged in as admin, redirecting to dashboard")
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print(f"Login attempt - Username: {username}, Password: {password}")
        
        if db_connected:
            try:
                print("Checking MongoDB for admin user...")
                admin = mongo.db.users.find_one({'username': username, 'is_admin': True})
                
                if admin:
                    print(f"Admin found: {admin['username']}")
                    
                    # Check password
                    if bcrypt.checkpw(password.encode('utf-8'), admin['password']):
                        print("Password correct!")
                        user_obj = User(admin)
                        login_user(user_obj)
                        print(f"User logged in. ID: {user_obj.id}, Admin: {user_obj.is_admin}")
                        
                        # Set session to remember login
                        session['user_id'] = str(admin['_id'])
                        session['is_admin'] = True
                        
                        next_page = request.args.get('next')
                        if next_page:
                            return redirect(next_page)
                        return redirect(url_for('admin_dashboard'))
                    else:
                        print("Password incorrect")
                else:
                    print("Admin user not found")
            except Exception as e:
                print(f"Database error: {e}")
        
        # Fallback: Demo mode admin login
        if username == 'admin' and password == 'admin123':
            print("Using demo admin login")
            user_obj = User({
                '_id': 'demo_admin_id',
                'username': 'admin',
                'email': 'admin@mufrafashions.com',
                'is_admin': True
            })
            login_user(user_obj)
            
            # Set session
            session['user_id'] = 'demo_admin_id'
            session['is_admin'] = True
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('admin_dashboard'))
        
        print("Login failed - invalid credentials")
        return render_template('admin/login.html', error='Invalid credentials')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    session.pop('user_id', None)
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if db_connected:
        try:
            total_orders = mongo.db.orders.count_documents({})
            total_products = mongo.db.products.count_documents({})
            pending_orders = mongo.db.orders.count_documents({'status': 'pending'})
            
            # Calculate revenue
            pipeline = [
                {'$match': {'status': {'$in': ['completed', 'delivered']}}},
                {'$group': {'_id': None, 'total': {'$sum': '$total_amount'}}}
            ]
            result = list(mongo.db.orders.aggregate(pipeline))
            total_revenue = result[0]['total'] if result else 0
            
            recent_orders = list(mongo.db.orders.find().sort('created_at', -1).limit(10))
            low_stock_products = list(mongo.db.products.find({'stock': {'$lt': 10}}).limit(5))
            
        except Exception as e:
            print(f"Database error in admin dashboard: {e}")
            total_orders = total_products = pending_orders = total_revenue = 0
            recent_orders = []
            low_stock_products = []
    else:
        total_orders = len(session.get('orders', []))
        total_products = 4
        pending_orders = total_orders
        total_revenue = total_orders * 100
        recent_orders = session.get('orders', [])[:10] if 'orders' in session else []
        low_stock_products = []
    
    # Convert ObjectIds to strings for template
    for order in recent_orders:
        if '_id' in order and isinstance(order['_id'], ObjectId):
            order['_id'] = str(order['_id'])
    
    for product in low_stock_products:
        if '_id' in product and isinstance(product['_id'], ObjectId):
            product['_id'] = str(product['_id'])
    
    return render_template('admin/dashboard.html',
                         total_orders=total_orders,
                         total_products=total_products,
                         pending_orders=pending_orders,
                         total_revenue=total_revenue,
                         recent_orders=recent_orders,
                         low_stock_products=low_stock_products)

@app.route('/admin/orders')
@login_required
def admin_orders():
    if db_connected:
        try:
            orders = list(mongo.db.orders.find().sort('created_at', -1))
            # Convert ObjectIds to strings
            for order in orders:
                if '_id' in order and isinstance(order['_id'], ObjectId):
                    order['_id'] = str(order['_id'])
        except Exception as e:
            print(f"Error loading orders: {e}")
            orders = []
    else:
        orders = session.get('orders', []) if 'orders' in session else []
    
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/products')
@login_required
def admin_products():
    if db_connected:
        try:
            products = list(mongo.db.products.find().sort('created_at', -1))
            # Convert ObjectIds to strings
            for product in products:
                if '_id' in product and isinstance(product['_id'], ObjectId):
                    product['_id'] = str(product['_id'])
        except Exception as e:
            print(f"Error loading products: {e}")
            products = get_demo_products()
    else:
        products = get_demo_products()
    
    return render_template('admin/products.html', products=products)

# ========== API ROUTES ==========
@app.route('/api/cart_count')
def api_cart_count():
    return jsonify({'count': len(session.get('cart', []))})

@app.route('/api/update_order_status', methods=['POST'])
@login_required
def update_order_status():
    try:
        order_id = request.form.get('order_id')
        status = request.form.get('status')
        
        if db_connected:
            mongo.db.orders.update_one(
                {'_id': ObjectId(order_id)},
                {'$set': {'status': status, 'updated_at': datetime.utcnow()}}
            )
            print(f"✅ Updated order {order_id} to status: {status}")
            return jsonify({'success': True})
        else:
            # Update in session for demo
            if 'orders' in session:
                for order in session['orders']:
                    if str(order.get('_id')) == order_id:
                        order['status'] = status
                        order['updated_at'] = datetime.now().isoformat()
                        session.modified = True
                        break
            return jsonify({'success': True})
    except Exception as e:
        print(f"❌ Error updating order status: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update_product', methods=['POST'])
@login_required
def update_product():
    try:
        product_id = request.form.get('product_id')
        stock = int(request.form.get('stock', 0))
        
        if db_connected:
            mongo.db.products.update_one(
                {'_id': ObjectId(product_id)},
                {'$set': {'stock': stock, 'updated_at': datetime.utcnow()}}
            )
            print(f"✅ Updated product {product_id} stock to: {stock}")
            return jsonify({'success': True})
        else:
            return jsonify({'success': True})  # Demo mode
    except Exception as e:
        print(f"❌ Error updating product: {e}")
        return jsonify({'success': False, 'error': str(e)})


    
@app.route('/api/upload_images', methods=['POST'])
@login_required
def upload_images():
    try:
        if 'images' not in request.files:
            return jsonify({'success': False, 'error': 'No images uploaded'})
        
        files = request.files.getlist('images')
        image_urls = []
        
        # In a real app, you would upload to cloud storage (AWS S3, Cloudinary, etc.)
        # For now, we'll return placeholder URLs
        for file in files:
            if file.filename:
                # Save to server (for demo - in production use cloud storage)
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'products')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                # Store relative path
                image_urls.append(f"/static/uploads/products/{filename}")
        
        return jsonify({
            'success': True, 
            'image_urls': image_urls,
            'message': f'Uploaded {len(image_urls)} images'
        })
        
    except Exception as e:
        print(f"❌ Error uploading images: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cancel_order', methods=['POST'])
def cancel_order():
    try:
        order_id = request.form.get('order_id')
        
        if db_connected:
            result = mongo.db.orders.update_one(
                {'_id': ObjectId(order_id)},
                {'$set': {'status': 'cancelled', 'cancelled_at': datetime.utcnow()}}
            )
            
            if result.modified_count > 0:
                print(f"✅ Cancelled order: {order_id}")
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Order not found'})
        else:
            # Update in session for demo
            if 'orders' in session:
                for order in session['orders']:
                    if str(order.get('_id')) == order_id:
                        order['status'] = 'cancelled'
                        order['cancelled_at'] = datetime.now().isoformat()
                        session.modified = True
                        print(f"✅ Cancelled demo order: {order_id}")
                        return jsonify({'success': True})
            
            return jsonify({'success': False, 'error': 'Order not found'})
            
    except Exception as e:
        print(f"❌ Error cancelling order: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ========== ERROR HANDLERS ==========
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

@app.route('/404')
def not_found_page():
    return render_template('404.html')

@app.route('/500')
def server_error_page():
    return render_template('500.html')
@app.route('/api/save_product', methods=['POST'])
@login_required
def save_product():
    try:
        # Get form data
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        print(f"📦 Saving product data: {data}")
        
        # Convert data types
        data['price'] = float(data.get('price', 0))
        data['stock'] = int(data.get('stock', 0))
        
        if data.get('compare_price'):
            data['compare_price'] = float(data['compare_price'])
        else:
            data.pop('compare_price', None)
        
        # Generate SKU if not provided
        if not data.get('sku'):
            category = data.get('category', 'PROD')[:3].upper()
            timestamp = datetime.now().strftime('%y%m%d%H%M')
            data['sku'] = f"{category}-{timestamp}"
        
        # Add default images if none provided
        if not data.get('images'):
            data['images'] = ['https://via.placeholder.com/500x300?text=Product+Image']
        
        # Add default arrays
        data['sizes'] = data.get('sizes', ['S', 'M', 'L', 'XL'])
        data['colors'] = data.get('colors', ['Red', 'Blue', 'Black', 'White'])
        
        # Add timestamps
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
        
        # Handle is_active - it could be boolean or string
        is_active = data.get('is_active', True)
        if isinstance(is_active, str):
            data['is_active'] = is_active.lower() == 'true'
        else:
            data['is_active'] = bool(is_active)
        
        if db_connected:
            result = mongo.db.products.insert_one(data)
            product_id = str(result.inserted_id)
            
            print(f"✅ Product saved to database. ID: {product_id}")
            return jsonify({
                'success': True, 
                'message': 'Product saved successfully!',
                'product_id': product_id
            })
        else:
            # Demo mode
            demo_id = f"DEMO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            data['_id'] = demo_id
            print(f"✅ Product saved in demo mode. ID: {demo_id}")
            return jsonify({
                'success': True, 
                'message': 'Product saved successfully (demo mode)!',
                'product_id': demo_id
            })
            
    except Exception as e:
        print(f"❌ Error saving product: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_product/<product_id>')
@login_required
def get_product(product_id):
    try:
        if db_connected:
            try:
                product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
            except:
                product = mongo.db.products.find_one({'_id': product_id})
            
            if product:
                # Convert ObjectId to string for JSON serialization
                product['_id'] = str(product['_id'])
                return jsonify(product)
        
        # Return demo product if not found or demo mode
        return jsonify({
            '_id': product_id,
            'name': 'Sample Product',
            'price': 29.99,
            'stock': 10,
            'is_active': True
        })
        
    except Exception as e:
        print(f"❌ Error getting product: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update_product_details', methods=['POST'])
@login_required
def update_product_details():
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'success': False, 'error': 'Product ID is required'}), 400
        
        # Remove product_id from update data
        data.pop('product_id', None)
        
        # Convert data types
        if 'price' in data:
            data['price'] = float(data['price'])
        if 'stock' in data:
            data['stock'] = int(data['stock'])
        if 'compare_price' in data:
            if data['compare_price']:
                data['compare_price'] = float(data['compare_price'])
            else:
                data['compare_price'] = None
        
        # Update timestamp
        data['updated_at'] = datetime.utcnow()
        
        print(f"📝 Updating product {product_id} with data: {data}")
        
        if db_connected:
            try:
                result = mongo.db.products.update_one(
                    {'_id': ObjectId(product_id)},
                    {'$set': data}
                )
            except:
                result = mongo.db.products.update_one(
                    {'_id': product_id},
                    {'$set': data}
                )
            
            if result.modified_count > 0:
                print(f"✅ Product updated: {product_id}")
                return jsonify({'success': True, 'message': 'Product updated successfully!'})
            else:
                return jsonify({'success': False, 'error': 'Product not found'}), 404
        else:
            print(f"✅ Product updated in demo mode: {product_id}")
            return jsonify({'success': True, 'message': 'Product updated (demo mode)!'})
            
    except Exception as e:
        print(f"❌ Error updating product: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update_product_status', methods=['POST'])
@login_required
def update_product_status():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        is_active = data.get('is_active')
        
        if not product_id:
            return jsonify({'success': False, 'error': 'Product ID is required'}), 400
        
        update_data = {'updated_at': datetime.utcnow()}
        if is_active is not None:
            update_data['is_active'] = bool(is_active)
        
        if db_connected:
            try:
                result = mongo.db.products.update_one(
                    {'_id': ObjectId(product_id)},
                    {'$set': update_data}
                )
            except:
                result = mongo.db.products.update_one(
                    {'_id': product_id},
                    {'$set': update_data}
                )
            
            if result.modified_count > 0:
                print(f"✅ Product status updated: {product_id}")
                return jsonify({'success': True, 'message': 'Product status updated!'})
            else:
                return jsonify({'success': False, 'error': 'Product not found'}), 404
        else:
            print(f"✅ Product status updated in demo mode: {product_id}")
            return jsonify({'success': True, 'message': 'Product status updated (demo mode)!'})
            
    except Exception as e:
        print(f"❌ Error updating product status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/duplicate_product', methods=['POST'])
@login_required
def duplicate_product():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'success': False, 'error': 'Product ID is required'}), 400
        
        if db_connected:
            try:
                product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
            except:
                product = mongo.db.products.find_one({'_id': product_id})
            
            if product:
                # Remove _id and add "Copy" to name
                product.pop('_id', None)
                product['name'] = f"{product.get('name', 'Product')} (Copy)"
                product['sku'] = f"{product.get('sku', 'PROD')}-COPY"
                product['created_at'] = datetime.utcnow()
                product['updated_at'] = datetime.utcnow()
                
                result = mongo.db.products.insert_one(product)
                print(f"✅ Product duplicated: {product_id} -> {result.inserted_id}")
                return jsonify({'success': True, 'message': 'Product duplicated successfully!'})
            else:
                return jsonify({'success': False, 'error': 'Product not found'}), 404
        else:
            print(f"✅ Product duplicated in demo mode: {product_id}")
            return jsonify({'success': True, 'message': 'Product duplicated (demo mode)!'})
            
    except Exception as e:
        print(f"❌ Error duplicating product: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete_product', methods=['POST'])
@login_required
def delete_product():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'success': False, 'error': 'Product ID is required'}), 400
        
        if db_connected:
            try:
                result = mongo.db.products.delete_one({'_id': ObjectId(product_id)})
            except:
                result = mongo.db.products.delete_one({'_id': product_id})
            
            if result.deleted_count > 0:
                print(f"✅ Product deleted: {product_id}")
                return jsonify({'success': True, 'message': 'Product deleted successfully!'})
            else:
                return jsonify({'success': False, 'error': 'Product not found'}), 404
        else:
            print(f"✅ Product deleted in demo mode: {product_id}")
            return jsonify({'success': True, 'message': 'Product deleted (demo mode)!'})
            
    except Exception as e:
        print(f"❌ Error deleting product: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== MAIN EXECUTION ==========
if __name__ == '__main__':
    with app.app_context():
        initialize_database()
    
    print("\n" + "="*60)
    print("🚀 MUFRA FASHIONS E-commerce Website")
    print("="*60)
    print("\n🌐 Access Points:")
    print("  Store:      http://localhost:5000")
    print("  My Orders:  http://localhost:5000/my_orders")
    print("  Admin:      http://localhost:5000/admin/login")
    print("\n🔐 Admin Credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("\n🔧 Database Status:", "✅ Connected" if db_connected else "⚠️ Demo Mode")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)