from itertools import product
import os
import json
import random
import string
from datetime import datetime, timezone
from datetime import timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from types import SimpleNamespace
from flask_pymongo import PyMongo
from flask_mail import Mail, Message
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
import uuid
import jwt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mufra-fashions-secret-key-2024')

# MongoDB configuration
MONGODB_CONNECTION_STRING = os.getenv('MONGO_URI', 'mongodb+srv://iconichean:1Loye8PM3YwlV5h4@cluster0.meufk73.mongodb.net/mufra_fashions?retryWrites=true&w=majority')
app.config['MONGO_URI'] = MONGODB_CONNECTION_STRING

# File upload configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'your-app-password')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'mufrafashions@gmail.com')
app.config['MAIL_SUPPRESS_SEND'] = os.getenv('MAIL_SUPPRESS_SEND', 'False').lower() == 'true'

# Paystack configuration
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', 'pk_test_ba60dd518974e7639e8f78deb0d7dee3acb96133')
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', 'sk_test_4d05b36c31bf5a4943a92c8ce13882a7859544bc')
PAYSTACK_BASE_URL = 'https://api.paystack.co'

# Allowed file extensions for product images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Initialize extensions
mongo = PyMongo(app, connectTimeoutMS=30000, socketTimeoutMS=30000, retryWrites=True)
mail = Mail(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ========== HELPER FUNCTIONS ==========
def now():
    """Return current datetime for templates"""
    return datetime.now()
def get_db():
    """Get database instance"""
    return mongo.db

def get_collection(collection_name):
    """Get or create a collection"""
    db = get_db()
    if collection_name not in db.list_collection_names():
        db.create_collection(collection_name)
    return db[collection_name]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        users_collection = get_collection('users')
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        if not user or user.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def generate_order_id():
    return 'MUFRA' + ''.join(random.choices(string.digits, k=8))

def send_email(to, subject, template, **kwargs):
    """Robust email sending for production - FIXED version"""
    import os
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    # Check if we're in production
    is_production = os.getenv('FLASK_ENV') == 'production' or not app.debug
    
    print(f"\n{'='*60}")
    print(f"📧 EMAIL REQUEST:")
    print(f"   To: {to}")
    print(f"   Subject: {subject}")
    print(f"   Production Mode: {is_production}")
    
    # Always log OTP for debugging
    if 'otp' in kwargs:
        print(f"🔐 OTP FOR {to}: {kwargs['otp']}")
    
    # Check if email sending is suppressed
    if app.config.get('MAIL_SUPPRESS_SEND', False):
        print(f"⚠️  MAIL_SUPPRESS_SEND=True - Email suppressed")
        print(f"{'='*60}\n")
        return True
    
    try:
        # Check if credentials are configured
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            print(f"⚠️  Email credentials not configured - skipping email")
            print(f"{'='*60}\n")
            return True
        
        # Create email content
        try:
            html_body = render_template(f'emails/{template}.html', **kwargs)
            text_body = render_template(f'emails/{template}.txt', **kwargs)
        except:
            # Fallback template
            html_body = f"""
            <html><body>
                <h2>{subject}</h2>
                <p>Hello {kwargs.get('name', 'User')},</p>
                <p>Your verification code is: <strong>{kwargs.get('otp', 'N/A')}</strong></p>
            </body></html>
            """
            text_body = f"{subject}\nHello {kwargs.get('name', 'User')},\nYour verification code is: {kwargs.get('otp', 'N/A')}"
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = to
        
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email - FIXED: removed .settimeout()
        try:
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], timeout=10) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(msg)
            
            print(f"✅ Email sent successfully")
            print(f"{'='*60}\n")
            
            return True
            
        except Exception as e:
            print(f"❌ EMAIL SEND FAILED: {str(e)}")
            print(f"{'='*60}\n")
            return True  # Continue despite email failure
        
    except Exception as e:
        print(f"❌ EMAIL SETUP FAILED: {str(e)}")
        print(f"{'='*60}\n")
        return True  
def send_verification_email(email, name, otp):
    """Send OTP verification email"""
    subject = "Verify Your Email - MUFRA FASHIONS"
    return send_email(
        to=email,
        subject=subject,
        template='verify_email',
        name=name,
        otp=otp,
        year=datetime.now().year
    )

def initialize_paystack_payment(email, amount, order_id, name, phone):
    """Initialize Paystack payment - FIXED VERSION"""
    try:
        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Generate simple reference
        reference = f'MUFRA-{order_id}-{int(datetime.now().timestamp())}'
        
        # Simplified data - Remove custom_fields that might cause issues
        data = {
            'email': email,
            'amount': int(amount * 100),  # Amount in cents
            'reference': reference,
            'callback_url': url_for('paystack_callback', _external=True),
            'metadata': {
                'order_id': order_id,
                'customer_name': name,
                'phone': phone
            }
            # REMOVED: 'currency': 'KES' - Let Paystack use default
        }
        
        print(f"\n🔍 CHECKOUT Paystack Request:")
        print(f"Amount: {amount} KES -> {int(amount * 100)} cents")
        print(f"Reference: {reference}")
        print(f"Data: {json.dumps(data, indent=2)}")
        
        response = requests.post(
            f'{PAYSTACK_BASE_URL}/transaction/initialize',
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"🔍 Response Status: {response.status_code}")
        print(f"🔍 Response: {response.text[:500]}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Authorization URL: {result.get('data', {}).get('authorization_url')}")
            return result
        else:
            print(f"❌ ERROR: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return None

def verify_paystack_payment(reference):
    """Verify Paystack payment"""
    try:
        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f'{PAYSTACK_BASE_URL}/transaction/verify/{reference}',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Paystack verification error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error verifying Paystack payment: {e}")
        return None

def send_order_confirmation(email, order_id, total, items, shipping_address):
    """Send order confirmation email"""
    subject = f"Order Confirmation #{order_id} - MUFRA FASHIONS"
    return send_email(
        to=email,
        subject=subject,
        template='order_confirmation',
        order_id=order_id,
        total=total,
        items=items,
        shipping_address=shipping_address,
        date=datetime.now().strftime('%B %d, %Y'),
        year=datetime.now().year
    )

def send_welcome_email(email, name):
    """Send welcome email"""
    subject = "Welcome to MUFRA FASHIONS!"
    return send_email(
        to=email,
        subject=subject,
        template='welcome',
        name=name,
        year=datetime.now().year
    )

def send_password_reset_email(email, name, reset_token):
    """Send password reset email"""
    subject = "Reset Your Password - MUFRA FASHIONS"
    reset_url = url_for('reset_password', token=reset_token, _external=True)
    return send_email(
        to=email,
        subject=subject,
        template='password_reset',
        name=name,
        reset_url=reset_url,
        year=datetime.now().year
    )

def initialize_sample_data():
    """Initialize database with sample data"""
    try:
        # Get collections
        categories_collection = get_collection('categories')
        products_collection = get_collection('products')
        users_collection = get_collection('users')
        
        # Create categories if none exist
        if categories_collection.count_documents({}) == 0:
            categories = [
                {'name': 'Shoes', 'slug': 'shoes', 'description': 'Footwear for all occasions'},
                {'name': 'Clothes', 'slug': 'clothes', 'description': 'Fashion clothing for everyone'},
                {'name': 'New', 'slug': 'new', 'description': 'Brand new products'},
                {'name': 'Second Hand', 'slug': 'second-hand', 'description': 'Quality second-hand items'}
            ]
            categories_collection.insert_many(categories)
            print("✓ Categories created successfully")
        
        # Create sample products if none exist - UPDATED FOR MULTIPLE IMAGES
        if products_collection.count_documents({}) == 0:
            products = [
                {
                    'name': 'Premium Running Shoes',
                    'description': 'High-quality running shoes with cushioned soles',
                    'price': 4500,
                    'category': 'Shoes',
                    'subcategory': 'Sports',
                    'condition': 'New',
                    'sizes': ['8', '9', '10', '11'],
                    'colors': ['Blue', 'White', 'Black'],
                    'stock': 50,
                    'images': [
                        {
                            'url': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80',
                            'filename': 'running_shoes_1.jpg',
                            'is_main': True
                        },
                        {
                            'url': 'https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60',
                            'filename': 'running_shoes_2.jpg',
                            'is_main': False
                        }
                    ],
                    'featured': True,
                    'rating': 4.5,
                    'reviews_count': 23,
                    'created_at': datetime.utcnow()
                },
                {
                    'name': 'Casual Sneakers',
                    'description': 'Comfortable casual sneakers for everyday wear',
                    'price': 3200,
                    'category': 'Shoes',
                    'subcategory': 'Casual',
                    'condition': 'New',
                    'sizes': ['7', '8', '9', '10'],
                    'colors': ['White', 'Gray', 'Navy'],
                    'stock': 30,
                    'images': [
                        {
                            'url': 'https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80',
                            'filename': 'sneakers_1.jpg',
                            'is_main': True
                        },
                        {
                            'url': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60',
                            'filename': 'sneakers_2.jpg',
                            'is_main': False
                        }
                    ],
                    'featured': True,
                    'rating': 4.2,
                    'reviews_count': 15,
                    'created_at': datetime.utcnow()
                },
                {
                    'name': 'Designer T-Shirt',
                    'description': 'Premium cotton t-shirt with designer print',
                    'price': 1500,
                    'category': 'Clothes',
                    'subcategory': 'Tops',
                    'condition': 'New',
                    'sizes': ['S', 'M', 'L', 'XL'],
                    'colors': ['Blue', 'White', 'Black'],
                    'stock': 100,
                    'images': [
                        {
                            'url': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80',
                            'filename': 'tshirt_1.jpg',
                            'is_main': True
                        },
                        {
                            'url': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60',
                            'filename': 'tshirt_2.jpg',
                            'is_main': False
                        },
                        {
                            'url': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=40',
                            'filename': 'tshirt_3.jpg',
                            'is_main': False
                        }
                    ],
                    'featured': True,
                    'rating': 4.7,
                    'reviews_count': 42,
                    'created_at': datetime.utcnow()
                },
                {
                    'name': 'Denim Jeans',
                    'description': 'Classic blue denim jeans',
                    'price': 2800,
                    'category': 'Clothes',
                    'subcategory': 'Bottoms',
                    'condition': 'Second Hand',
                    'sizes': ['30', '32', '34', '36'],
                    'colors': ['Blue'],
                    'stock': 25,
                    'images': [
                        {
                            'url': 'https://images.unsplash.com/photo-1542272604-787c3835535d?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80',
                            'filename': 'jeans_1.jpg',
                            'is_main': True
                        },
                        {
                            'url': 'https://images.unsplash.com/photo-1542272604-787c3835535d?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60',
                            'filename': 'jeans_2.jpg',
                            'is_main': False
                        }
                    ],
                    'featured': True,
                    'rating': 4.3,
                    'reviews_count': 18,
                    'created_at': datetime.utcnow()
                }
            ]
            products_collection.insert_many(products)
            print("✓ Products created successfully with multiple images")
        
        # Create admin user if not exists
        if users_collection.count_documents({'email': 'admin@mufra.com'}) == 0:
            admin_user = {
                'name': 'Admin',
                'email': 'admin@mufra.com',
                'phone': '+254700000000',
                'password': generate_password_hash('admin123'),
                'role': 'admin',
                'verified': True,
                'cart': [],
                'wishlist': [],
                'created_at': datetime.utcnow()
            }
            users_collection.insert_one(admin_user)
            print("✓ Admin user created successfully")
        
        # Create other collections if they don't exist
        get_collection('orders')
        get_collection('reviews')
        
        print("✓ Database initialization completed successfully!")
        
    except Exception as e:
        print(f"⚠ Warning during database initialization: {e}")

@app.route('/paystack/callback')
def paystack_callback():
    """Handle Paystack callback after payment - COMPLETELY REWRITTEN"""
    try:
        reference = request.args.get('reference', '')
        
        if not reference:
            flash('Invalid payment reference', 'danger')
            return redirect(url_for('account'))
        
        print(f"\n🔍 ===== PAYSTACK CALLBACK =====")
        print(f"Reference: {reference}")
        
        # Verify payment
        verification = verify_paystack_payment(reference)
        
        if not verification or not verification.get('status'):
            flash('Payment verification failed', 'danger')
            return redirect(url_for('checkout'))
        
        data = verification.get('data', {})
        status = data.get('status', 'failed')
        metadata = data.get('metadata', {})
        order_id_from_metadata = metadata.get('order_id', '')
        
        print(f"Payment status: {status}")
        print(f"Order ID from metadata: {order_id_from_metadata}")
        
        if not order_id_from_metadata:
            flash('Order ID not found in payment metadata', 'danger')
            return redirect(url_for('account'))
        
        # Get collections
        orders_collection = get_collection('orders')
        products_collection = get_collection('products')
        users_collection = get_collection('users')
        
        # ===== FIND THE ORDER =====
        order = None
        
        # Method 1: Try with order_id field (MUFRA format)
        order = orders_collection.find_one({'order_id': order_id_from_metadata})
        if order:
            print(f"✅ Found order by order_id field: {order_id_from_metadata}")
        
        # Method 2: Try with paystack_reference
        if not order:
            order = orders_collection.find_one({'paystack_reference': reference})
            if order:
                print(f"✅ Found order by paystack_reference: {reference}")
                # Get the actual order_id from this order
                order_id_from_metadata = order.get('order_id')
        
        # Method 3: Search by partial order_id (some orders might have MUFRA prefix in different places)
        if not order:
            # Extract the numeric part if it's in MUFRAXXXX format
            if order_id_from_metadata.startswith('MUFRA'):
                numeric_part = order_id_from_metadata[5:]  # Remove MUFRA prefix
                order = orders_collection.find_one({'order_id': {'$regex': f'MUFRA{numeric_part}'}})
                if order:
                    print(f"✅ Found order by regex match: MUFRA{numeric_part}")
        
        if not order:
            print(f"❌ Order not found with ID: {order_id_from_metadata}")
            flash('Order not found. Please check your orders page.', 'danger')
            return redirect(url_for('account'))
        
        # Get the actual order_id from the found order
        actual_order_id = order.get('order_id')
        if not actual_order_id:
            actual_order_id = str(order.get('_id'))
        
        print(f"Actual order ID to use: {actual_order_id}")
        
        if status == 'success':
            # Update order status
            update_result = orders_collection.update_one(
                {'_id': order['_id']},
                {'$set': {
                    'payment_status': 'paid',
                    'status': 'processing',
                    'payment_reference': reference,
                    'paystack_reference': reference,
                    'payment_date': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                }}
            )
            
            print(f"✅ Order updated: {update_result.modified_count} document(s) modified")
            
            # Update product stock
            for item in order.get('items', []):
                try:
                    product_id = item.get('product_id')
                    quantity = item.get('quantity', 1)
                    if product_id:
                        # Convert to ObjectId if it's a string
                        if isinstance(product_id, str):
                            try:
                                product_id = ObjectId(product_id)
                            except:
                                pass
                        
                        products_collection.update_one(
                            {'_id': product_id},
                            {'$inc': {'stock': -quantity}}
                        )
                        print(f"✅ Updated stock for product: {product_id}, reduced by {quantity}")
                except Exception as stock_error:
                    print(f"⚠️ Error updating stock: {stock_error}")
            
            # Clear user's cart
            if order.get('user_id'):
                try:
                    user_id = order['user_id']
                    users_collection.update_one(
                        {'_id': user_id},
                        {'$set': {'cart': []}}
                    )
                    print(f"✅ Cart cleared for user: {user_id}")
                    
                    # Send order confirmation email
                    user = users_collection.find_one({'_id': user_id})
                    if user:
                        try:
                            send_order_confirmation(
                                email=user['email'],
                                order_id=actual_order_id,
                                total=order.get('total', 0),
                                items=order.get('items', []),
                                shipping_address=order.get('shipping_address', {})
                            )
                            print(f"✅ Order confirmation email sent")
                        except Exception as email_error:
                            print(f"⚠️ Error sending email: {email_error}")
                except Exception as cart_error:
                    print(f"⚠️ Error clearing cart: {cart_error}")
            
            flash('Payment successful! Your order has been confirmed.', 'success')
            print(f"✅ Redirecting to order confirmation: {actual_order_id}")
            
            # DIRECT REDIRECT - NO COMPLEX LOGIC
            return redirect(url_for('order_confirmation', order_id=actual_order_id))
            
        else:
            # Payment failed
            orders_collection.update_one(
                {'_id': order['_id']},
                {'$set': {
                    'payment_status': 'failed',
                    'status': 'failed',
                    'updated_at': datetime.now(timezone.utc)
                }}
            )
            
            flash('Payment failed. Please try again.', 'danger')
            return redirect(url_for('checkout'))
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR in paystack_callback: {e}")
        import traceback
        traceback.print_exc()
        flash('Error processing payment. Please check your orders page.', 'danger')
        return redirect(url_for('account'))
# ========== CUSTOM JINJA2 FILTERS ==========
@app.template_filter('safe_length')
def safe_length_filter(value):
    """Safely get the length of a value, handling functions and None"""
    if value is None:
        return 0
    if callable(value):
        try:
            value = value()
        except:
            return 0
    if hasattr(value, '__len__'):
        try:
            return len(value)
        except:
            return 0
    if isinstance(value, (list, tuple, dict, str)):
        return len(value)
    return 0

@app.template_filter('is_list')
def is_list_filter(value):
    """Check if value is a list (not a function)"""
    if value is None:
        return False
    if callable(value):
        return False
    return isinstance(value, (list, tuple))

@app.template_filter('safe_items')
def safe_items_filter(value):
    """Safely get items as a list, handling functions"""
    if value is None:
        return []
    if callable(value):
        try:
            value = value()
        except:
            return []
    if isinstance(value, list):
        return value
    if hasattr(value, '__iter__'):
        try:
            return list(value)
        except:
            return []
    return []

@app.route('/debug-order-json/<order_id>')
@login_required
def debug_order_json(order_id):
    """Debug endpoint to see raw order data"""
    try:
        orders_collection = get_collection('orders')
        order = orders_collection.find_one({'order_id': order_id})
        
        if not order:
            return jsonify({'error': 'Order not found'})
        
        # Check ownership
        if str(order.get('user_id')) != session['user_id']:
            return jsonify({'error': 'Unauthorized'})
        
        # Convert to serializable format
        def convert_to_serializable(obj):
            if isinstance(obj, ObjectId):
                return str(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            return obj
        
        safe_order = convert_to_serializable(order)
        
        return jsonify(safe_order)
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()})

@app.route('/paystack/webhook', methods=['POST'])
def paystack_webhook():
    """Handle Paystack webhook for payment notifications"""
    try:
        # Get the payload
        payload = request.get_json()
        
        if not payload:
            return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400
        
        # Verify the event
        event = payload.get('event', '')
        data = payload.get('data', {})
        
        if event == 'charge.success':
            reference = data.get('reference', '')
            order_id = data.get('metadata', {}).get('order_id', '')
            
            if reference and order_id:
                orders_collection = get_collection('orders')
                
                # Update order status
                orders_collection.update_one(
                    {'order_id': order_id},
                    {'$set': {
                        'payment_status': 'paid',
                        'status': 'processing',
                        'payment_date': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }}
                )
                
                # Send confirmation email, etc.
                print(f"Webhook: Order {order_id} payment successful")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/', methods=['POST'])
def root_post_handler():
    """Fallback handler for POST requests to root - forwards Paystack webhooks"""
    try:
        payload = request.get_json()
        
        # Check if this looks like a Paystack webhook
        if payload and 'event' in payload and 'data' in payload:
            print(f"📧 Forwarding Paystack webhook from / to /paystack/webhook")
            # Forward to paystack_webhook handler
            return paystack_webhook()
        
        # For other POST requests, return 405
        return jsonify({'status': 'error', 'message': 'Method not allowed'}), 405
        
    except Exception as e:
        print(f"Root POST handler error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/fix-admin-password')
def fix_admin_password():
    """Fix admin password (one-time use)"""
    try:
        users_collection = get_collection('users')
        
        # Find the admin user
        admin = users_collection.find_one({'email': 'admin@mufra.com'})
        
        if not admin:
            return "Admin user not found. Please create an admin user first."
        
        # Get the current password (could be str or bytes)
        current_password = admin.get('password', '')
        
        # Convert to string for comparison
        if isinstance(current_password, bytes):
            password_str = current_password.decode('utf-8')
        else:
            password_str = str(current_password)
        
        # Check if password is already hashed
        if password_str.startswith('pbkdf2:sha256:'):
            return "Password is already hashed correctly"
        
        # Hash the password
        hashed_password = generate_password_hash('admin123')
        
        # Update the password
        users_collection.update_one(
            {'_id': admin['_id']},
            {'$set': {'password': hashed_password}}
        )
        
        return """
        <h2>Admin password has been fixed!</h2>
        <p><strong>Email:</strong> admin@mufra.com</p>
        <p><strong>New Password:</strong> admin123</p>
        <p><a href="/login">Go to Login</a></p>
        """
    
    except Exception as e:
        return f"<h2>Error:</h2><p>{str(e)}</p>"

@app.route('/check-flask-mail-config')
def check_flask_mail_config():
    """Check Flask mail configuration"""
    config_info = {
        'MAIL_SERVER': app.config.get('MAIL_SERVER'),
        'MAIL_PORT': app.config.get('MAIL_PORT'),
        'MAIL_USE_TLS': app.config.get('MAIL_USE_TLS'),
        'MAIL_USE_SSL': app.config.get('MAIL_USE_SSL'),
        'MAIL_USERNAME': app.config.get('MAIL_USERNAME'),
        'MAIL_PASSWORD_LENGTH': len(app.config.get('MAIL_PASSWORD', '')) if app.config.get('MAIL_PASSWORD') else 0,
        'MAIL_PASSWORD_SET': bool(app.config.get('MAIL_PASSWORD')),
        'MAIL_SUPPRESS_SEND': app.config.get('MAIL_SUPPRESS_SEND', False),
        'MAIL_DEFAULT_SENDER': app.config.get('MAIL_DEFAULT_SENDER'),
    }
    
    return f"""
    <h2>Flask Mail Configuration</h2>
    <pre>{json.dumps(config_info, indent=2)}</pre>
    <p><strong>Note:</strong> Password is {'correctly set' if config_info['MAIL_PASSWORD_SET'] else 'NOT SET!'}</p>
    """

# ========== ROUTES ==========

@app.route('/')
def home():
    """Home page"""
    try:
        products_collection = get_collection('products')
        categories_collection = get_collection('categories')
        
        # Get featured products with default values
        featured_products = list(products_collection.find({'featured': True}).limit(8))
        
        # Process each product to ensure proper image structure
        for product in featured_products:
            product.setdefault('rating', 0)
            product.setdefault('reviews_count', 0)
            
            # Ensure images field exists and is properly formatted
            if 'images' not in product or not product['images']:
                # Convert single image to images array if needed
                if 'image' in product and product['image']:
                    product['images'] = [{
                        'url': product['image'],
                        'filename': product['image'].split('/')[-1] if '/' in product['image'] else product['image'],
                        'is_main': True
                    }]
                else:
                    product['images'] = [{
                        'url': 'https://via.placeholder.com/400x300?text=Product+Image',
                        'filename': 'placeholder.jpg',
                        'is_main': True
                    }]
            else:
                # Ensure each image has required fields
                for i, img in enumerate(product['images']):
                    if isinstance(img, str):
                        # Convert string to dict
                        product['images'][i] = {
                            'url': img,
                            'filename': img.split('/')[-1] if '/' in img else img,
                            'is_main': i == 0
                        }
                    elif isinstance(img, dict):
                        # Ensure dict has all required fields
                        img.setdefault('url', img.get('url', 'https://via.placeholder.com/400x300?text=Product+Image'))
                        img.setdefault('filename', img.get('filename', img['url'].split('/')[-1]))
                        img.setdefault('is_main', img.get('is_main', i == 0))
        
        # Get categories for navigation
        categories = list(categories_collection.find({}))
        
        # Personalized recommendations
        recommended_products = []
        if 'user_id' in session:
            users_collection = get_collection('users')
            user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
            if user and 'viewed_products' in user:
                viewed_categories = set()
                for product_id in user.get('viewed_products', [])[-3:]:
                    product = products_collection.find_one({'_id': ObjectId(product_id)})
                    if product:
                        viewed_categories.add(product['category'])
                
                if viewed_categories:
                    recommended_products = list(products_collection.find({
                        'category': {'$in': list(viewed_categories)},
                        '_id': {'$nin': user.get('viewed_products', [])}
                    }).limit(4))
                    
                    # Process recommended products images
                    for product in recommended_products:
                        product.setdefault('rating', 0)
                        product.setdefault('reviews_count', 0)
                        if 'images' not in product or not product['images']:
                            if 'image' in product and product['image']:
                                product['images'] = [{
                                    'url': product['image'],
                                    'filename': product['image'].split('/')[-1] if '/' in product['image'] else product['image'],
                                    'is_main': True
                                }]
                            else:
                                product['images'] = [{
                                    'url': 'https://via.placeholder.com/400x300?text=Product+Image',
                                    'filename': 'placeholder.jpg',
                                    'is_main': True
                                }]
        
        return render_template('index.html', 
                             featured_products=featured_products,
                             categories=categories,
                             recommended_products=recommended_products)
    except Exception as e:
        print(f"Error in home route: {e}")
        return render_template('index.html', 
                             featured_products=[],
                             categories=[],
                             recommended_products=[])

@app.route('/migrate-products-images')
@admin_required
def migrate_products_images():
    """Migrate existing products to use images array"""
    try:
        products_collection = get_collection('products')
        updated_count = 0
        
        # Find all products that don't have images array or have old image field
        products = list(products_collection.find({
            '$or': [
                {'images': {'$exists': False}},
                {'image': {'$exists': True}},
                {'images': {'$size': 0}}
            ]
        }))
        
        for product in products:
            update_data = {}
            
            # If product has image field but no images array
            if 'image' in product and product['image'] and ('images' not in product or not product['images']):
                update_data['images'] = [{
                    'url': product['image'],
                    'filename': product['image'].split('/')[-1] if '/' in product['image'] else product['image'],
                    'is_main': True
                }]
                update_data['main_image'] = product['image']
                # Optionally remove the old image field
                update_data['$unset'] = {'image': ''}
            
            # If images array exists but is empty or malformed
            elif 'images' in product and (not product['images'] or isinstance(product['images'][0], str)):
                if product['images'] and isinstance(product['images'][0], str):
                    # Convert string array to object array
                    new_images = []
                    for i, img_url in enumerate(product['images']):
                        new_images.append({
                            'url': img_url,
                            'filename': img_url.split('/')[-1] if '/' in img_url else img_url,
                            'is_main': i == 0
                        })
                    update_data['images'] = new_images
                    update_data['main_image'] = new_images[0]['url'] if new_images else ''
            
            if update_data:
                products_collection.update_one(
                    {'_id': product['_id']},
                    {'$set': update_data}
                )
                updated_count += 1
                print(f"Updated product: {product.get('name', 'Unknown')}")
        
        return f"""
        <h2>Migration Complete!</h2>
        <p>Updated {updated_count} out of {len(products)} products</p>
        <p><a href="/">Go to Home</a></p>
        """
    except Exception as e:
        return f"<h2>Error:</h2><p>{str(e)}</p>"

@app.route('/categories')
def categories():
    """Categories page with filtering"""
    try:
        category = request.args.get('category', '')
        condition = request.args.get('condition', '')
        min_price = request.args.get('min_price', 0, type=int)
        max_price = request.args.get('max_price', 100000, type=int)
        sort_option = request.args.get('sort', 'date_desc')  # ADD DEFAULT SORT OPTION
        page = request.args.get('page', 1, type=int)
        
        # Build query
        query = {}
        if category:
            query['category'] = category
        if condition:
            query['condition'] = condition
        if min_price > 0 or max_price < 100000:
            query['price'] = {'$gte': min_price, '$lte': max_price}
        
        # Get products and categories
        products_collection = get_collection('products')
        categories_collection = get_collection('categories')
        
        # Apply sorting
        sort_mapping = {
            'price_asc': [('price', 1)],
            'price_desc': [('price', -1)],
            'rating_desc': [('rating', -1)],
            'name_asc': [('name', 1)],
            'name_desc': [('name', -1)],
            'date_desc': [('created_at', -1)]
        }
        sort_criteria = sort_mapping.get(sort_option, [('created_at', -1)])
        
        # Pagination
        per_page = 12
        skip = (page - 1) * per_page
        
        # Get products with pagination and sorting
        total_products = products_collection.count_documents(query)
        products = list(products_collection.find(query)
                       .sort(sort_criteria)
                       .skip(skip)
                       .limit(per_page))
        
        # Ensure all products have required fields
        for product in products:
            product.setdefault('rating', 0)
            product.setdefault('reviews_count', 0)
            product.setdefault('stock', 0)
            product.setdefault('featured', False)
            product.setdefault('sizes', [])
            product.setdefault('colors', [])
            product.setdefault('image', 'https://via.placeholder.com/400x300?text=Product+Image')
        
        categories_list = list(categories_collection.find({}))
        total_pages = (total_products + per_page - 1) // per_page
        
        return render_template('categories.html', 
                             products=products,
                             categories=categories_list,
                             selected_category=category,
                             selected_condition=condition,
                             sort_option=sort_option,  # PASS SORT OPTION TO TEMPLATE
                             page=page,
                             total_pages=total_pages)
    except Exception as e:
        print(f"Error in categories route: {e}")
        flash('Error loading categories', 'danger')
        return render_template('categories.html', 
                             products=[],
                             categories=[],
                             selected_category='',
                             selected_condition='',
                             sort_option='date_desc',
                             page=1,
                             total_pages=0)

@app.route('/product/<product_id>')
def product_details(product_id):
    """Product details page"""
    try:
        products_collection = get_collection('products')
        reviews_collection = get_collection('reviews')
        
        product = products_collection.find_one({'_id': ObjectId(product_id)})
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('home'))
        
        # Convert ObjectId to string
        product['_id'] = str(product['_id'])
        
        # Ensure product has all required fields
        product.setdefault('rating', 0)
        product.setdefault('reviews_count', 0)
        product.setdefault('stock', 0)
        product.setdefault('sizes', [])
        product.setdefault('colors', [])
        product.setdefault('image', 'https://via.placeholder.com/400x300?text=Product+Image')
        
        # Get reviews
        reviews = list(reviews_collection.find({'product_id': ObjectId(product_id)}).sort('created_at', -1))
        for review in reviews:
            review['_id'] = str(review['_id'])
            review['user_id'] = str(review['user_id'])
        
        # Update viewed products if logged in
        if 'user_id' in session:
            users_collection = get_collection('users')
            users_collection.update_one(
                {'_id': ObjectId(session['user_id'])},
                {'$addToSet': {'viewed_products': ObjectId(product_id)}}
            )
        
        # Get related products
        related_products = list(products_collection.find({
            'category': product.get('category', ''),
            '_id': {'$ne': ObjectId(product_id)}
        }).limit(4))
        
        for p in related_products:
            p['_id'] = str(p['_id'])
            p.setdefault('rating', 0)
            p.setdefault('reviews_count', 0)
            p.setdefault('image', 'https://via.placeholder.com/400x300?text=Product+Image')
        
        return render_template('product_details.html',
                             product=product,
                             reviews=reviews,
                             related_products=related_products)
    except Exception as e:
        print(f"\n❌ ERROR in product_details: {e}")
        import traceback
        print(f"❌ TRACEBACK: {traceback.format_exc()}")
        flash('Error loading product details', 'danger')
        return redirect(url_for('home'))

@app.route('/add-to-cart/<product_id>', methods=['POST'])
def add_to_cart(product_id):
    """Add item to cart - FIXED to include all product details"""
    try:
        products_collection = get_collection('products')
        product = products_collection.find_one({'_id': ObjectId(product_id)})
        
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'})
        
        # Get form data
        size = request.form.get('size')
        color = request.form.get('color')
        quantity = int(request.form.get('quantity', 1))
        
        # Check stock
        if product.get('stock', 0) < quantity:
            return jsonify({'success': False, 'message': 'Insufficient stock'})
        
        # Get product image
        product_image = ''
        if 'images' in product and product['images']:
            # Get main image or first image
            for img in product['images']:
                if img.get('is_main', False):
                    product_image = img.get('url', '')
                    break
            if not product_image and product['images']:
                product_image = product['images'][0].get('url', '')
        elif 'image' in product:
            product_image = product['image']
        
        # Create cart item with ALL product details
        cart_item = {
            'product_id': str(product_id),
            'name': product.get('name', 'Product'),
            'price': float(product.get('price', 0)),
            'size': size,
            'color': color,
            'quantity': quantity,
            'image': product_image,
            'stock': product.get('stock', 0),
            'description': product.get('description', ''),
            'category': product.get('category', '')
        }
        
        if 'user_id' in session:
            # Logged in user - store in database
            cart_item_for_db = cart_item.copy()
            cart_item_for_db['product_id'] = ObjectId(product_id)  # ObjectId for DB
            
            users_collection = get_collection('users')
            user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
            cart = user.get('cart', [])
            
            # Check if item already exists (same product, size, color)
            item_found = False
            for i, item in enumerate(cart):
                if (str(item['product_id']) == product_id and 
                    item.get('size') == size and 
                    item.get('color') == color):
                    # Update existing item
                    cart[i]['quantity'] += quantity
                    # Update price and name in case they changed
                    cart[i]['name'] = cart_item['name']
                    cart[i]['price'] = cart_item['price']
                    cart[i]['image'] = cart_item['image']
                    item_found = True
                    break
            
            if not item_found:
                cart.append(cart_item_for_db)
            
            users_collection.update_one(
                {'_id': ObjectId(session['user_id'])},
                {'$set': {'cart': cart}}
            )
            cart_count = len(cart)
        else:
            # Guest user - store in session
            cart = session.get('cart', [])
            
            # Check if item already exists
            item_found = False
            for i, item in enumerate(cart):
                if (str(item['product_id']) == product_id and 
                    item.get('size') == size and 
                    item.get('color') == color):
                    cart[i]['quantity'] += quantity
                    # Update price and name in case they changed
                    cart[i]['name'] = cart_item['name']
                    cart[i]['price'] = cart_item['price']
                    cart[i]['image'] = cart_item['image']
                    item_found = True
                    break
            
            if not item_found:
                cart.append(cart_item)
            
            session['cart'] = cart
            cart_count = len(cart)
        
        return jsonify({
            'success': True, 
            'message': 'Added to cart', 
            'cart_count': cart_count,
            'item': {
                'name': cart_item['name'],
                'price': cart_item['price'],
                'quantity': cart_item['quantity']
            }
        })
    except Exception as e:
        print(f"Error in add_to_cart: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error adding to cart'})
    

@app.route('/cart')
def cart():
    """Shopping cart page"""
    try:
        if 'user_id' in session:
            users_collection = get_collection('users')
            user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
            cart_items = user.get('cart', [])
        else:
            cart_items = session.get('cart', [])
        
        # Calculate subtotal
        subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart_items)
        
        return render_template('cart.html', cart_items=cart_items, subtotal=subtotal)
    except Exception as e:
        print(f"Error in cart: {e}")
        flash('Error loading cart', 'danger')
        return render_template('cart.html', cart_items=[], subtotal=0)

@app.route('/update-cart', methods=['POST'])
def update_cart():
    """Update cart item quantity"""
    try:
        item_index = int(request.form.get('item_index'))
        quantity = int(request.form.get('quantity', 1))
        
        if quantity <= 0:
            return jsonify({'success': False, 'message': 'Quantity must be greater than 0'})
        
        if 'user_id' in session:
            users_collection = get_collection('users')
            user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
            cart_items = user.get('cart', [])
            
            if 0 <= item_index < len(cart_items):
                cart_items[item_index]['quantity'] = quantity
                users_collection.update_one(
                    {'_id': ObjectId(session['user_id'])},
                    {'$set': {'cart': cart_items}}
                )
                return jsonify({'success': True})
        else:
            cart_items = session.get('cart', [])
            
            if 0 <= item_index < len(cart_items):
                cart_items[item_index]['quantity'] = quantity
                session['cart'] = cart_items
                return jsonify({'success': True})
        
        return jsonify({'success': False, 'message': 'Item not found in cart'})
    except Exception as e:
        print(f"Error in update_cart: {e}")
        return jsonify({'success': False, 'message': 'Error updating cart'})

@app.route('/remove-from-cart/<int:item_index>')
def remove_from_cart(item_index):
    """Remove item from cart"""
    try:
        if 'user_id' in session:
            users_collection = get_collection('users')
            user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
            cart_items = user.get('cart', [])
            
            if 0 <= item_index < len(cart_items):
                cart_items.pop(item_index)
                users_collection.update_one(
                    {'_id': ObjectId(session['user_id'])},
                    {'$set': {'cart': cart_items}}
                )
        else:
            cart_items = session.get('cart', [])
            
            if 0 <= item_index < len(cart_items):
                cart_items.pop(item_index)
                session['cart'] = cart_items
        
        flash('Item removed from cart', 'success')
        return redirect(url_for('cart'))
    except Exception as e:
        print(f"Error in remove_from_cart: {e}")
        flash('Error removing item from cart', 'danger')
        return redirect(url_for('cart'))

@app.route('/checkout')
@login_required
def checkout():
    """Checkout page"""
    try:
        users_collection = get_collection('users')
        products_collection = get_collection('products')
        
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        cart_items = user.get('cart', [])
        
        if not cart_items:
            flash('Your cart is empty', 'warning')
            return redirect(url_for('cart'))
        
        # Check stock availability
        for item in cart_items:
            product = products_collection.find_one({'_id': item['product_id']})
            if not product or product.get('stock', 0) < item.get('quantity', 1):
                flash(f'{item["name"]} is out of stock', 'danger')
                return redirect(url_for('cart'))
        
        # Calculate subtotal
        subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart_items)
        
        return render_template('checkout.html', 
                             cart_items=cart_items, 
                             subtotal=subtotal,
                             user=user)
    except Exception as e:
        print(f"Error in checkout: {e}")
        flash('Error loading checkout page', 'danger')
        return redirect(url_for('cart'))

@app.route('/process-checkout', methods=['POST'])
@login_required
def process_checkout():
    """Process checkout and redirect directly to Paystack"""
    try:
        users_collection = get_collection('users')
        products_collection = get_collection('products')
        orders_collection = get_collection('orders')
        
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        if not user:
            flash('User not found. Please login again.', 'danger')
            return redirect(url_for('login'))
        
        cart_items = user.get('cart', [])
        
        if not cart_items:
            flash('Your cart is empty', 'warning')
            return redirect(url_for('cart'))
        
        # Get shipping address
        shipping_address = {
            'street': request.form.get('street', '').strip(),
            'city': request.form.get('city', '').strip(),
            'county': request.form.get('county', '').strip(),
            'postal_code': request.form.get('postal_code', '').strip(),
            'phone': request.form.get('phone', '').strip()
        }
        
        # Validate required fields
        required_fields = ['street', 'city', 'county', 'phone']
        for field in required_fields:
            if not shipping_address[field]:
                flash(f'Please enter your {field.replace("_", " ")}', 'danger')
                return redirect(url_for('checkout'))
        
        # Validate phone number
        phone = shipping_address['phone']
        if len(phone) != 9 or not phone.isdigit():
            flash('Please enter a valid 9-digit phone number without leading 0', 'danger')
            return redirect(url_for('checkout'))
        
        # Check stock availability before proceeding
        for item in cart_items:
            product = products_collection.find_one({'_id': ObjectId(item['product_id'])})
            if not product:
                flash(f'Product {item["name"]} not found', 'danger')
                return redirect(url_for('cart'))
            if product.get('stock', 0) < item.get('quantity', 1):
                flash(f'{item["name"]} is out of stock', 'danger')
                return redirect(url_for('cart'))
        
        # Calculate totals
        subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart_items)
        county = shipping_address.get('county', '').lower()
        delivery_fee = 100 if 'embu' in county else 200
        
        # Free shipping for orders over 5000
        if subtotal >= 5000:
            delivery_fee = 0
            
        total = subtotal + delivery_fee
        
        # Generate order ID
        order_id = generate_order_id()
        
        # Process cart items to ensure proper format with ALL product details
        processed_items = []
        for item in cart_items:
            # Get full product details from database
            product = products_collection.find_one({'_id': ObjectId(item['product_id'])})
            
            if product:
                processed_item = {
                    'product_id': str(item['product_id']),
                    'name': str(product.get('name', item.get('name', 'Product'))),
                    'price': float(product.get('price', item.get('price', 0))),
                    'quantity': int(item.get('quantity', 1)),
                    'size': str(item.get('size', '')),
                    'color': str(item.get('color', '')),
                    'image': str(product.get('image', item.get('image', ''))),
                    'description': str(product.get('description', ''))
                }
            else:
                # Fallback to cart item data
                processed_item = {
                    'product_id': str(item['product_id']),
                    'name': str(item.get('name', 'Product')),
                    'price': float(item.get('price', 0)),
                    'quantity': int(item.get('quantity', 1)),
                    'size': str(item.get('size', '')),
                    'color': str(item.get('color', '')),
                    'image': str(item.get('image', ''))
                }
            processed_items.append(processed_item)
        
        # Create order with processed items
        order = {
            'order_id': order_id,
            'user_id': ObjectId(session['user_id']),
            'items': processed_items,  # Use processed items with full details
            'shipping_address': shipping_address,
            'payment_method': 'paystack',
            'subtotal': subtotal,
            'delivery_fee': delivery_fee,
            'total': total,
            'status': 'pending',
            'payment_status': 'pending',
            'paystack_reference': None,
            'paystack_authorization_url': None,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        # Save order to database
        orders_collection.insert_one(order)
        
        # Initialize Paystack payment
        try:
            paystack_response = initialize_paystack_payment(
                email=user['email'],
                amount=total,
                order_id=order_id,
                name=user['name'],
                phone=shipping_address['phone']
            )
            
            if paystack_response and paystack_response.get('status'):
                # Get authorization URL
                authorization_url = paystack_response.get('data', {}).get('authorization_url')
                reference = paystack_response.get('data', {}).get('reference')
                
                # Update order with Paystack details
                orders_collection.update_one(
                    {'order_id': order_id},
                    {'$set': {
                        'paystack_reference': reference,
                        'paystack_authorization_url': authorization_url,
                        'updated_at': datetime.now(timezone.utc)
                    }}
                )
                
                # ✅ DIRECT REDIRECT TO PAYSTACK - FULLY AUTOMATED
                return redirect(authorization_url)
                
            else:
                # Payment initialization failed
                error_msg = 'Payment initialization failed. Please try again.'
                if paystack_response and 'message' in paystack_response:
                    error_msg = paystack_response['message']
                
                flash(error_msg, 'danger')
                return redirect(url_for('checkout'))
                
        except Exception as paystack_error:
            print(f"❌ Paystack initialization error: {paystack_error}")
            import traceback
            print(traceback.format_exc())
            
            flash('Payment service temporarily unavailable. Please try again later.', 'danger')
            return redirect(url_for('checkout'))
        
    except Exception as e:
        print(f"❌ Error in process_checkout: {e}")
        import traceback
        print(traceback.format_exc())
        
        flash('An error occurred during checkout. Please try again.', 'danger')
        return redirect(url_for('checkout'))



@app.route('/order-confirmation/<order_id>')
@login_required
def order_confirmation(order_id):
    """FIXED order confirmation page - ensures items is a list"""
    try:
        print(f"\n🔍 ===== ORDER CONFIRMATION =====")
        print(f"Looking for order with ID: {order_id}")
        
        orders_collection = get_collection('orders')
        
        # Try to find the order
        order = None
        
        # Try as order_id field first
        order = orders_collection.find_one({'order_id': order_id})
        if order:
            print(f"✅ Found by order_id: {order_id}")
        
        # If not found, try as _id
        if not order:
            try:
                if len(order_id) == 24:  # Possible ObjectId
                    order = orders_collection.find_one({'_id': ObjectId(order_id)})
                    if order:
                        print(f"✅ Found by _id (ObjectId): {order_id}")
            except:
                pass
        
        # If still not found, try as string _id
        if not order:
            order = orders_collection.find_one({'_id': order_id})
            if order:
                print(f"✅ Found by _id (string): {order_id}")
        
        if not order:
            print(f"❌ Order not found: {order_id}")
            flash('Order not found', 'danger')
            return redirect(url_for('account'))
        
        # Check ownership
        user_id = order.get('user_id')
        if user_id:
            user_id_str = str(user_id)
            if user_id_str != session['user_id']:
                print(f"❌ Order belongs to {user_id_str}, not {session['user_id']}")
                flash('Order not found', 'danger')
                return redirect(url_for('account'))
        
        # ===== CRITICAL FIX: Handle items that might be functions =====
        items_data = order.get('items', [])
        
        # Check if items is callable (function/method)
        if callable(items_data):
            print("⚠️ Items is a function, trying to call it")
            try:
                items_data = items_data()
            except Exception as e:
                print(f"❌ Error calling items function: {e}")
                items_data = []
        
        # Ensure items is a list
        if not isinstance(items_data, list):
            print(f"⚠️ Items is not a list: {type(items_data)}")
            # Try to convert to list if it's a cursor or other iterable
            try:
                items_data = list(items_data)
            except:
                items_data = []
        
        # Process each item to ensure it's a proper dict
        processed_items = []
        for item in items_data:
            if item is None:
                continue
                
            if isinstance(item, dict):
                # Item is already a dict
                safe_item = {
                    'name': str(item.get('name', 'Product')),
                    'price': float(item.get('price', 0)),
                    'quantity': int(item.get('quantity', 1)),
                    'size': str(item.get('size', '')),
                    'color': str(item.get('color', ''))
                }
                processed_items.append(safe_item)
            elif hasattr(item, 'to_dict'):  # Handle MongoDB SON objects
                try:
                    item_dict = item.to_dict()
                    safe_item = {
                        'name': str(item_dict.get('name', 'Product')),
                        'price': float(item_dict.get('price', 0)),
                        'quantity': int(item_dict.get('quantity', 1)),
                        'size': str(item_dict.get('size', '')),
                        'color': str(item_dict.get('color', ''))
                    }
                    processed_items.append(safe_item)
                except Exception as e:
                    print(f"❌ Error processing item with to_dict: {e}")
        
        # ===== SAFELY EXTRACT OTHER ORDER DATA =====
        safe_order = {
            'order_id': str(order.get('order_id', order_id)),
            'status': str(order.get('status', 'pending')),
            'payment_status': str(order.get('payment_status', 'pending')),
            'payment_method': str(order.get('payment_method', 'paystack')),
            'subtotal': 0,
            'delivery_fee': 0,
            'total': 0,
            'created_at': order.get('created_at', datetime.now()),
            'paystack_reference': str(order.get('paystack_reference', '')),
            'items': processed_items,  # Use the processed items list
            'shipping_address': {}
        }
        
        # Safely get numeric values
        try:
            safe_order['subtotal'] = float(order.get('subtotal', 0))
        except:
            safe_order['subtotal'] = 0
            
        try:
            safe_order['delivery_fee'] = float(order.get('delivery_fee', 0))
        except:
            safe_order['delivery_fee'] = 0
            
        try:
            safe_order['total'] = float(order.get('total', 0))
        except:
            safe_order['total'] = 0
        
        # ===== PROCESS SHIPPING ADDRESS SAFELY =====
        shipping = order.get('shipping_address', {})
        
        if callable(shipping):
            print("⚠️ Shipping address is a function")
            try:
                shipping = shipping()
            except:
                shipping = {}
        
        if isinstance(shipping, dict):
            safe_order['shipping_address'] = {
                'street': str(shipping.get('street', '')),
                'city': str(shipping.get('city', '')),
                'county': str(shipping.get('county', '')),
                'postal_code': str(shipping.get('postal_code', '')),
                'phone': str(shipping.get('phone', ''))
            }
        elif hasattr(shipping, 'to_dict'):
            try:
                shipping_dict = shipping.to_dict()
                safe_order['shipping_address'] = {
                    'street': str(shipping_dict.get('street', '')),
                    'city': str(shipping_dict.get('city', '')),
                    'county': str(shipping_dict.get('county', '')),
                    'postal_code': str(shipping_dict.get('postal_code', '')),
                    'phone': str(shipping_dict.get('phone', ''))
                }
            except:
                pass
        
        print(f"✅ Items found and processed: {len(safe_order['items'])}")
        print(f"✅ Items type: {type(safe_order['items'])}")
        print(f"✅ First item: {safe_order['items'][0] if safe_order['items'] else 'None'}")
        
        return render_template('order_confirmation.html', order=safe_order)
        
    except Exception as e:
        print(f"❌ ERROR in order_confirmation: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to create a minimal order object from what we know
        try:
            # Try to find the order again to get at least basic info
            orders_collection = get_collection('orders')
            order = orders_collection.find_one({'order_id': order_id})
            
            if order:
                # Try to get items
                items_data = order.get('items', [])
                if callable(items_data):
                    try:
                        items_data = items_data()
                    except:
                        items_data = []
                
                items_list = []
                if isinstance(items_data, list):
                    for item in items_data:
                        if isinstance(item, dict):
                            items_list.append({
                                'name': item.get('name', 'Product'),
                                'price': float(item.get('price', 0)),
                                'quantity': int(item.get('quantity', 1)),
                                'size': item.get('size', ''),
                                'color': item.get('color', '')
                            })
                
                minimal_order = {
                    'order_id': order_id,
                    'status': str(order.get('status', 'processing')),
                    'payment_status': str(order.get('payment_status', 'paid')),
                    'payment_method': 'paystack',
                    'subtotal': float(order.get('subtotal', 0)),
                    'delivery_fee': float(order.get('delivery_fee', 0)),
                    'total': float(order.get('total', 0)),
                    'created_at': order.get('created_at', datetime.now()),
                    'paystack_reference': str(order.get('paystack_reference', '')),
                    'items': items_list,
                    'shipping_address': {}
                }
                
                # Process shipping address
                shipping = order.get('shipping_address', {})
                if isinstance(shipping, dict):
                    minimal_order['shipping_address'] = {
                        'street': str(shipping.get('street', '')),
                        'city': str(shipping.get('city', '')),
                        'county': str(shipping.get('county', '')),
                        'postal_code': str(shipping.get('postal_code', '')),
                        'phone': str(shipping.get('phone', ''))
                    }
                
                flash('Order found but there was an error loading full details. Showing available information.', 'warning')
                return render_template('order_confirmation.html', order=minimal_order)
            else:
                flash('Order not found', 'danger')
                return redirect(url_for('account'))
        except:
            flash('Error loading order confirmation. Please check your orders page.', 'danger')
            return redirect(url_for('account'))
@app.route('/debug-order/<order_id>')
@login_required
def debug_order(order_id):
    """Debug order data"""
    try:
        orders_collection = get_collection('orders')
        order = orders_collection.find_one({'order_id': order_id})
        
        if not order or str(order.get('user_id')) != session['user_id']:
            return jsonify({'error': 'Order not found or not authorized'})
        
        # Convert ObjectId to string for JSON serialization
        order['_id'] = str(order['_id'])
        order['user_id'] = str(order['user_id'])
        
        if 'items' in order:
            # Convert items list
            for item in order['items']:
                if 'product_id' in item:
                    item['product_id'] = str(item['product_id'])
        
        # Debug info
        debug_info = {
            'order_exists': order is not None,
            'order_id': order.get('order_id'),
            'has_items': 'items' in order,
            'items_count': len(order.get('items', [])),
            'items_type': type(order.get('items')).__name__,
            'is_items_list': isinstance(order.get('items'), list),
            'order_keys': list(order.keys()),
            'items_sample': str(order.get('items'))[:200] if order.get('items') else None
        }
        
        return jsonify(debug_info)
    
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration - Direct redirect without email verification"""
    try:
        if request.method == 'POST':
            # Get form data
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            phone = request.form.get('phone', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not all([name, email, phone, password]):
                flash('All fields are required', 'danger')
                return redirect(url_for('register'))
            
            if password != confirm_password:
                flash('Passwords do not match', 'danger')
                return redirect(url_for('register'))
            
            if len(password) < 6:
                flash('Password must be at least 6 characters', 'danger')
                return redirect(url_for('register'))
            
            # Check if user already exists
            users_collection = get_collection('users')
            existing_user = users_collection.find_one({'$or': [{'email': email}, {'phone': phone}]})
            if existing_user:
                flash('User with this email or phone already exists', 'danger')
                return redirect(url_for('register'))
            
            # Create user
            user = {
                'name': name,
                'email': email,
                'phone': phone,
                'password': generate_password_hash(password),
                'role': 'customer',
                'verified': True,  # Auto-verify since no email verification
                'cart': [],
                'wishlist': [],
                'created_at': datetime.utcnow()
            }
            
            # Save user to database
            result = users_collection.insert_one(user)
            
            # Create session immediately
            session['user_id'] = str(result.inserted_id)
            session['user_name'] = user['name']
            session['user_role'] = user.get('role', 'customer')
            
            # Flash success message
            flash(f'Welcome to MUFRA FASHIONS, {name}! Registration successful.', 'success')
            
            # Redirect directly to home
            return redirect(url_for('home'))
        
        return render_template('register.html')
    except Exception as e:
        print(f"Registration error: {e}")
        flash('Error during registration. Please try again.', 'danger')
        return render_template('register.html')

@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    """Email verification"""
    try:
        if 'temp_user_id' not in session:
            flash('Session expired. Please register again.', 'warning')
            return redirect(url_for('register'))
        
        if request.method == 'POST':
            otp = request.form.get('otp', '')
            users_collection = get_collection('users')
            user = users_collection.find_one({'_id': ObjectId(session['temp_user_id'])})
            
            if not user:
                flash('User not found', 'danger')
                return redirect(url_for('register'))
            
            # Verify OTP
            if (user.get('verification_otp') == otp and 
                user.get('otp_expires') > datetime.utcnow()):
                
                # Mark as verified
                users_collection.update_one(
                    {'_id': ObjectId(session['temp_user_id'])},
                    {'$set': {'verified': True}, 
                     '$unset': {'verification_otp': '', 'otp_expires': ''}}
                )
                
                # Create session and send welcome email
                session['user_id'] = str(user['_id'])
                session['user_name'] = user['name']
                session['user_role'] = user.get('role', 'customer')
                session.pop('temp_user_id', None)
                
                # Send welcome email
                send_welcome_email(user['email'], user['name'])
                
                flash('Email verified successfully! Welcome to MUFRA FASHIONS.', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid or expired OTP', 'danger')
        
        return render_template('verify_email.html')
    except Exception as e:
        print(f"Error in verify_email: {e}")
        flash('Error during verification', 'danger')
        return redirect(url_for('register'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    try:
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            
            users_collection = get_collection('users')
            user = users_collection.find_one({'email': email})
            
            if user:
                try:
                    # Try to check the password
                    if check_password_hash(user['password'], password):
                        if not user.get('verified', False):
                            flash('Please verify your email first', 'warning')
                            # Resend verification
                            session['temp_user_id'] = str(user['_id'])
                            return redirect(url_for('verify_email'))
                        
                        # Create session
                        session['user_id'] = str(user['_id'])
                        session['user_name'] = user['name']
                        session['user_role'] = user.get('role', 'customer')
                        
                        # Migrate session cart to user cart
                        if 'cart' in session and user.get('role') == 'customer':
                            session_cart = session.get('cart', [])
                            user_cart = user.get('cart', [])
                            
                            for session_item in session_cart:
                                found = False
                                for user_item in user_cart:
                                    if (str(session_item['product_id']) == str(user_item['product_id']) and
                                        session_item.get('size') == user_item.get('size') and
                                        session_item.get('color') == user_item.get('color')):
                                        user_item['quantity'] += session_item['quantity']
                                        found = True
                                        break
                                
                                if not found:
                                    session_item['product_id'] = ObjectId(session_item['product_id'])
                                    user_cart.append(session_item)
                            
                            users_collection.update_one(
                                {'_id': user['_id']},
                                {'$set': {'cart': user_cart}}
                            )
                            
                            session.pop('cart', None)
                        
                        flash('Login successful!', 'success')
                        
                        # Redirect admin users to admin panel
                        if user.get('role') == 'admin':
                            return redirect(url_for('admin_dashboard'))
                        else:
                            return redirect(url_for('home'))
                            
                    else:
                        flash('Invalid email or password', 'danger')
                except Exception as hash_error:
                    # Password is not properly hashed
                    print(f"Password hash error: {hash_error}")
                    if user.get('password') == password:  # Plain text password
                        # Fix the password by hashing it
                        users_collection.update_one(
                            {'_id': user['_id']},
                            {'$set': {'password': generate_password_hash(password)}}
                        )
                        
                        # Create session
                        session['user_id'] = str(user['_id'])
                        session['user_name'] = user['name']
                        session['user_role'] = user.get('role', 'customer')
                        
                        flash('Login successful! Password has been secured.', 'success')
                        
                        # Redirect admin users to admin panel
                        if user.get('role') == 'admin':
                            return redirect(url_for('admin_dashboard'))
                        else:
                            return redirect(url_for('home'))
                    else:
                        flash('Invalid email or password', 'danger')
            else:
                flash('Invalid email or password', 'danger')
        
        return render_template('login.html')
    except Exception as e:
        print(f"Error in login: {e}")
        flash('Error during login', 'danger')
        return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('home'))

@app.route('/account')
@login_required
def account():
    """User account dashboard - FIXED for function/method items"""
    try:
        print(f"\n🔍 ===== ACCOUNT PAGE LOADING =====")
        print(f"🔍 User ID in session: {session.get('user_id')}")
        
        # Get collections
        users_collection = get_collection('users')
        orders_collection = get_collection('orders')
        
        # ===== 1. GET USER - WITH MULTIPLE FALLBACKS =====
        user = None
        user_id = session.get('user_id')
        
        if user_id:
            try:
                # Try as ObjectId first
                user = users_collection.find_one({'_id': ObjectId(user_id)})
            except:
                try:
                    # Try as string
                    user = users_collection.find_one({'_id': user_id})
                except:
                    pass
        
        # If still no user, create minimal user object
        if not user:
            print(f"❌ User not found, creating minimal user object")
            user = {
                '_id': user_id,
                'name': 'Customer',
                'email': '',
                'phone': '',
                'role': 'customer',
                'verified': False,
                'cart': [],
                'wishlist': [],
                'created_at': datetime.now(),
                'last_login': datetime.now()
            }
        
        # ===== 2. SAFELY CONVERT USER OBJECT =====
        safe_user = {}
        
        # Copy all fields safely
        for key, value in user.items():
            if isinstance(value, ObjectId):
                safe_user[key] = str(value)
            elif isinstance(value, datetime):
                safe_user[key] = value
            elif key == 'cart':
                # Ensure cart is a list
                if isinstance(value, list):
                    safe_user[key] = value
                else:
                    safe_user[key] = []
            elif key == 'wishlist':
                # Ensure wishlist is a list
                if isinstance(value, list):
                    safe_user[key] = value
                else:
                    safe_user[key] = []
            else:
                safe_user[key] = value
        
        # Set defaults for missing fields
        user_defaults = {
            'name': 'Customer',
            'email': '',
            'phone': '',
            'role': 'customer',
            'verified': False,
            'cart': [],
            'wishlist': [],
            'addresses': [],
            'profile_picture': '',
            'created_at': datetime.now(),
            'last_login': datetime.now()
        }
        
        for key, default_value in user_defaults.items():
            if key not in safe_user or safe_user[key] is None:
                safe_user[key] = default_value
        
        # ===== 3. GET ORDERS - WITH COMPLETE ERROR HANDLING =====
        safe_orders = []
        
        try:
            if user_id:
                # Try to find orders
                try:
                    orders_cursor = orders_collection.find({'user_id': ObjectId(user_id)}).sort('created_at', -1)
                    db_orders = list(orders_cursor)
                except:
                    try:
                        orders_cursor = orders_collection.find({'user_id': user_id}).sort('created_at', -1)
                        db_orders = list(orders_cursor)
                    except:
                        db_orders = []
                
                # Process each order safely
                for order in db_orders:
                    try:
                        # ===== FIX: Handle items that might be functions =====
                        items_data = order.get('items', [])
                        if callable(items_data):
                            try:
                                items_data = items_data()
                            except:
                                items_data = []
                        
                        # Ensure items is a list
                        if not isinstance(items_data, list):
                            items_data = []
                        
                        # Process items count safely
                        items_count = 0
                        for item in items_data:
                            if isinstance(item, dict):
                                items_count += 1
                            elif hasattr(item, 'to_dict'):
                                items_count += 1
                        
                        safe_order = {
                            '_id': str(order.get('_id', '')),
                            'order_id': str(order.get('order_id', f"ORD-{str(order.get('_id', ''))[-8:]}")),
                            'user_id': str(order.get('user_id', '')),
                            'status': order.get('status', 'pending'),
                            'payment_status': order.get('payment_status', 'pending'),
                            'payment_method': order.get('payment_method', 'paystack'),
                            'subtotal': 0,
                            'delivery_fee': 0,
                            'total': 0,
                            'items': [],  # Empty list for template
                            'items_count': items_count,  # Store count separately
                            'shipping_address': {},
                            'created_at': order.get('created_at', datetime.now()),
                            'updated_at': order.get('updated_at', datetime.now())
                        }
                        
                        # Safely get subtotal
                        try:
                            safe_order['subtotal'] = float(order.get('subtotal', 0))
                        except:
                            safe_order['subtotal'] = 0
                        
                        # Safely get delivery_fee
                        try:
                            safe_order['delivery_fee'] = float(order.get('delivery_fee', 0))
                        except:
                            safe_order['delivery_fee'] = 0
                        
                        # Safely get total
                        try:
                            safe_order['total'] = float(order.get('total', 0))
                        except:
                            safe_order['total'] = 0
                        
                        # Safely process shipping address
                        shipping = order.get('shipping_address', {})
                        if callable(shipping):
                            try:
                                shipping = shipping()
                            except:
                                shipping = {}
                        
                        if isinstance(shipping, dict):
                            safe_order['shipping_address'] = shipping
                        elif hasattr(shipping, 'to_dict'):
                            try:
                                safe_order['shipping_address'] = shipping.to_dict()
                            except:
                                safe_order['shipping_address'] = {}
                        
                        safe_orders.append(safe_order)
                        
                    except Exception as order_error:
                        print(f"⚠️ Error processing individual order: {order_error}")
                        continue
                        
        except Exception as orders_error:
            print(f"⚠️ Error fetching orders: {orders_error}")
            safe_orders = []
        
        # ===== 4. CALCULATE STATISTICS SAFELY =====
        total_orders = len(safe_orders)
        pending_count = 0
        delivered_count = 0
        total_spent = 0
        
        for order in safe_orders:
            # Count pending
            if order.get('status') == 'pending':
                pending_count += 1
            # Count delivered
            if order.get('status') == 'delivered':
                delivered_count += 1
            # Calculate total spent (only paid orders)
            if order.get('payment_status') == 'paid' and order.get('total'):
                try:
                    total_spent += float(order['total'])
                except:
                    pass
        
        print(f"✅ User loaded: {safe_user.get('name')}")
        print(f"✅ Orders found: {len(safe_orders)}")
        print(f"✅ Pending: {pending_count}, Delivered: {delivered_count}")
        print(f"✅ Total spent: {total_spent}")
        
        # ===== 5. RENDER TEMPLATE WITH ALL DATA =====
        return render_template(
            'account.html',
            user=safe_user,
            orders=safe_orders,
            total_orders=total_orders,
            pending_count=pending_count,
            delivered_count=delivered_count,
            total_spent=total_spent
        )
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR in account route: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        
        # Even on error, show a basic page
        flash('Unable to load your account details. Please try again.', 'warning')
        return render_template(
            'account.html',
            user={
                'name': session.get('user_name', 'Customer'),
                'email': '',
                'phone': '',
                'role': 'customer',
                'verified': False,
                'cart': [],
                'wishlist': [],
                'created_at': datetime.now()
            },
            orders=[],
            total_orders=0,
            pending_count=0,
            delivered_count=0,
            total_spent=0
        )
@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        if not name or not phone:
            return jsonify({'success': False, 'message': 'Name and phone are required'})
        
        users_collection = get_collection('users')
        users_collection.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': {
                'name': name,
                'phone': phone,
                'updated_at': datetime.utcnow()
            }}
        )
        
        # Update session
        session['user_name'] = name
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        print(f"Error in update_profile: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not current_password or not new_password or not confirm_password:
            return jsonify({'success': False, 'message': 'All password fields are required'})
        
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': 'New passwords do not match'})
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'New password must be at least 6 characters'})
        
        users_collection = get_collection('users')
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Check current password
        if not check_password_hash(user['password'], current_password):
            return jsonify({'success': False, 'message': 'Current password is incorrect'})
        
        # Update password
        users_collection.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': {
                'password': generate_password_hash(new_password),
                'updated_at': datetime.utcnow()
            }}
        )
        
        return jsonify({'success': True, 'message': 'Password changed successfully'})
    except Exception as e:
        print(f"Error in change_password: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/add-review/<product_id>', methods=['POST'])
@login_required
def add_review(product_id):
    """Add product review"""
    try:
        rating = int(request.form.get('rating', 5))
        comment = request.form.get('comment', '').strip()
        
        if not comment or rating < 1 or rating > 5:
            flash('Please provide a valid rating and comment', 'warning')
            return redirect(url_for('product_details', product_id=product_id))
        
        reviews_collection = get_collection('reviews')
        products_collection = get_collection('products')
        
        # Create review
        review = {
            'product_id': ObjectId(product_id),
            'user_id': ObjectId(session['user_id']),
            'user_name': session['user_name'],
            'rating': rating,
            'comment': comment,
            'created_at': datetime.utcnow()
        }
        
        reviews_collection.insert_one(review)
        
        # Update product rating
        product_reviews = list(reviews_collection.find({'product_id': ObjectId(product_id)}))
        if product_reviews:
            avg_rating = sum(r['rating'] for r in product_reviews) / len(product_reviews)
            products_collection.update_one(
                {'_id': ObjectId(product_id)},
                {'$set': {
                    'rating': round(avg_rating, 1),
                    'reviews_count': len(product_reviews)
                }}
            )
        
        flash('Review added successfully', 'success')
        return redirect(url_for('product_details', product_id=product_id))
    except Exception as e:
        print(f"Error in add_review: {e}")
        flash('Error adding review', 'danger')
        return redirect(url_for('product_details', product_id=product_id))

# ========== PASSWORD RESET ROUTES ==========

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address', 'warning')
            return redirect(url_for('forgot_password'))
        
        users_collection = get_collection('users')
        user = users_collection.find_one({'email': email})
        
        if user:
            # Generate reset token
            reset_token = str(uuid.uuid4())
            reset_expires = datetime.utcnow() + timedelta(hours=1)
            
            # Save token to user
            users_collection.update_one(
                {'_id': user['_id']},
                {'$set': {
                    'reset_token': reset_token,
                    'reset_expires': reset_expires
                }}
            )
            
            # Send password reset email
            send_password_reset_email(
                email=user['email'],
                name=user['name'],
                reset_token=reset_token
            )
            
            flash('Password reset instructions sent to your email', 'success')
        else:
            flash('Email not found in our system', 'danger')
        
        return redirect(url_for('forgot_password'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    users_collection = get_collection('users')
    user = users_collection.find_one({
        'reset_token': token,
        'reset_expires': {'$gt': datetime.utcnow()}
    })
    
    if not user:
        flash('Invalid or expired reset token', 'danger')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not password or not confirm_password:
            flash('Please enter and confirm your new password', 'warning')
            return render_template('reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('reset_password.html', token=token)
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'warning')
            return render_template('reset_password.html', token=token)
        
        # Update password and clear reset token
        users_collection.update_one(
            {'_id': user['_id']},
            {'$set': {'password': generate_password_hash(password)},
             '$unset': {'reset_token': '', 'reset_expires': ''}}
        )
        
        flash('Password reset successfully! You can now login with your new password.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

# ========== ADMIN ROUTES ==========

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    try:
        orders_collection = get_collection('orders')
        products_collection = get_collection('products')
        users_collection = get_collection('users')
        
        # Statistics
        total_orders = orders_collection.count_documents({})
        total_products = products_collection.count_documents({})
        total_users = users_collection.count_documents({'role': 'customer'})
        
        # Get recent orders with user information
        recent_orders = list(orders_collection.find().sort('created_at', -1).limit(10))
        
        # Add user information to each order
        for order in recent_orders:
            user = users_collection.find_one({'_id': order['user_id']})
            order['user_name'] = user.get('name', 'Unknown') if user else 'Unknown'
            order['user_email'] = user.get('email', 'N/A') if user else 'N/A'
        
        # Calculate revenue
        try:
            revenue_cursor = orders_collection.aggregate([
                {'$match': {'status': 'delivered'}},
                {'$group': {'_id': None, 'total': {'$sum': '$total'}}}
            ])
            revenue_result = list(revenue_cursor)
            total_revenue = revenue_result[0]['total'] if revenue_result else 0
        except Exception as agg_error:
            print(f"Aggregation error: {agg_error}")
            total_revenue = 0
        
        return render_template('admin/dashboard.html',
                             total_orders=total_orders,
                             total_products=total_products,
                             total_users=total_users,
                             total_revenue=total_revenue,
                             recent_orders=recent_orders)
    except Exception as e:
        print(f"Error in admin_dashboard: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        flash('Error loading admin dashboard', 'danger')
        return redirect(url_for('home'))

@app.route('/debug-categories')
@admin_required
def debug_categories():
    """Debug categories"""
    try:
        categories_collection = get_collection('categories')
        categories = list(categories_collection.find({}))
        
        return jsonify({
            'total_categories': len(categories),
            'categories': categories
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/admin/products')
@admin_required
def admin_products():
    """Admin product management"""
    try:
        products_collection = get_collection('products')
        products = list(products_collection.find().sort('_id', -1))
        return render_template('admin/products.html', products=products)
    except Exception as e:
        print(f"Error in admin_products: {e}")
        flash('Error loading products', 'danger')
        return render_template('admin/products.html', products=[])

@app.route('/wishlist')
def wishlist_redirect():
    """Compatibility route: redirect legacy /wishlist endpoint to account#wishlist or login"""
    try:
        if 'user_id' in session:
            return redirect(url_for('account') + '#wishlist')
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Error in wishlist_redirect: {e}")
        return redirect(url_for('home'))

@app.route('/admin/add-product', methods=['GET', 'POST'])
@admin_required
def add_product():
    """Add new product with multiple images - SIMPLIFIED VERSION"""
    try:
        if request.method == 'POST':
            # Get form data
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            price = request.form.get('price', '0')
            category = request.form.get('category', '')
            subcategory = request.form.get('subcategory', '').strip()
            condition = request.form.get('condition', 'New')
            stock = request.form.get('stock', '0')
            
            # Validate required fields
            if not name or not price or not category:
                flash('Please fill in all required fields', 'danger')
                return redirect(url_for('add_product'))
            
            try:
                price = float(price)
                stock = int(stock)
            except ValueError:
                flash('Invalid price or stock value', 'danger')
                return redirect(url_for('add_product'))
            
            # Get sizes and colors
            sizes = request.form.getlist('sizes[]')
            colors = request.form.getlist('colors[]')
            
            # Handle image uploads
            images = []
            if 'images' in request.files:
                files = request.files.getlist('images')
                for file in files:
                    if file and file.filename != '' and allowed_file(file.filename):
                        # Generate unique filename
                        filename = secure_filename(file.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        
                        # Save file
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(file_path)
                        
                        images.append({
                            'filename': unique_filename,
                            'url': f"/static/uploads/{unique_filename}",
                            'is_main': len(images) == 0
                        })
            
            # If no images uploaded, use placeholder
            if not images:
                images.append({
                    'filename': 'placeholder.jpg',
                    'url': 'https://via.placeholder.com/400x300?text=Product+Image',
                    'is_main': True
                })
            
            # Create product
            products_collection = get_collection('products')
            product = {
                'name': name,
                'description': description,
                'price': price,
                'category': category,
                'subcategory': subcategory,
                'condition': condition,
                'stock': stock,
                'sizes': sizes,
                'colors': colors,
                'images': images,
                'main_image': images[0]['url'] if images else '',
                'featured': 'featured' in request.form,
                'status': 'active',
                'rating': 0,
                'reviews_count': 0,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            products_collection.insert_one(product)
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin_products'))
        
        # GET request - show form
        categories_collection = get_collection('categories')
        categories = list(categories_collection.find({}))
        return render_template('admin/add_product.html', categories=categories)
        
    except Exception as e:
        print(f"Error in add_product: {e}")
        flash('Error adding product: ' + str(e), 'danger')
        return redirect(url_for('admin_products'))

@app.route('/admin/edit-product/<product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    """Edit product with multiple images"""
    try:
        products_collection = get_collection('products')
        product = products_collection.find_one({'_id': ObjectId(product_id)})
        
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('admin_products'))
        
        # Ensure images field exists and is properly formatted
        if 'images' not in product or not product['images']:
            # Convert single image to images array if needed
            if 'image' in product and product['image']:
                product['images'] = [{
                    'url': product['image'],
                    'filename': product['image'].split('/')[-1] if '/' in product['image'] else product['image'],
                    'is_main': True
                }]
            else:
                product['images'] = [{
                    'url': 'https://via.placeholder.com/400x300?text=Product+Image',
                    'filename': 'placeholder.jpg',
                    'is_main': True
                }]
        else:
            # Ensure each image has required fields
            for img in product['images']:
                if isinstance(img, str):
                    # If image is just a URL string
                    idx = product['images'].index(img)
                    product['images'][idx] = {
                        'url': img,
                        'filename': img.split('/')[-1] if '/' in img else img,
                        'is_main': idx == 0
                    }
                elif isinstance(img, dict):
                    # Ensure dict has all required fields
                    img.setdefault('filename', img.get('url', '').split('/')[-1])
                    img.setdefault('url', img.get('url', 'https://via.placeholder.com/400x300?text=Product+Image'))
                    img.setdefault('is_main', idx == 0)
        
        if request.method == 'POST':
            # Get updated data
            update_data = {
                'name': request.form.get('name', '').strip(),
                'description': request.form.get('description', '').strip(),
                'price': float(request.form.get('price', 0)),
                'category': request.form.get('category', ''),
                'subcategory': request.form.get('subcategory', '').strip(),
                'condition': request.form.get('condition', 'New'),
                'stock': int(request.form.get('stock', 0)),
                'sizes': request.form.getlist('sizes[]'),
                'colors': request.form.getlist('colors[]'),
                'featured': bool(request.form.get('featured')),
                'updated_at': datetime.utcnow()
            }
            
            # Handle existing images
            existing_images = []
            existing_image_filenames = request.form.getlist('existing_images[]')
            
            # Keep existing images
            for img in product.get('images', []):
                img_filename = img.get('filename', '')
                if img_filename in existing_image_filenames:
                    existing_images.append(img)
            
            # Handle new image uploads
            new_images = []
            if 'images' in request.files:
                files = request.files.getlist('images')
                for file in files:
                    if file and file.filename != '' and allowed_file(file.filename):
                        # Generate unique filename
                        filename = secure_filename(file.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        
                        # Save file
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(file_path)
                        
                        # Add to images list
                        new_images.append({
                            'filename': unique_filename,
                            'url': f"/static/uploads/{unique_filename}",
                            'is_main': len(existing_images) + len(new_images) == 0  # First image is main
                        })
            
            # Combine existing and new images
            all_images = existing_images + new_images
            
            # Ensure at least one image
            if not all_images:
                all_images = [{
                    'filename': 'placeholder.jpg',
                    'url': 'https://via.placeholder.com/400x300?text=Product+Image',
                    'is_main': True
                }]
            
            # Update images in database
            update_data['images'] = all_images
            update_data['main_image'] = all_images[0]['url'] if all_images else ''
            
            # Update product in database
            products_collection.update_one(
                {'_id': ObjectId(product_id)},
                {'$set': update_data}
            )
            
            flash('Product updated successfully', 'success')
            return redirect(url_for('admin_products'))
        
        categories_collection = get_collection('categories')
        categories = list(categories_collection.find({}))
        return render_template('admin/edit_product.html', 
                             product=product, 
                             categories=categories)
    except Exception as e:
        print(f"Error in edit_product: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        flash('Error updating product', 'danger')
        return redirect(url_for('admin_products'))

@app.route('/admin/delete-product/<product_id>')
@admin_required
def delete_product(product_id):
    """Delete product"""
    try:
        products_collection = get_collection('products')
        products_collection.delete_one({'_id': ObjectId(product_id)})
        flash('Product deleted successfully', 'success')
        return redirect(url_for('admin_products'))
    except Exception as e:
        print(f"Error in delete_product: {e}")
        flash('Error deleting product', 'danger')
        return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    """Admin order management - HANDLES ALL ORDER FORMATS"""
    try:
        print("\n🔍 ===== ADMIN ORDERS ROUTE STARTED =====")
        
        # Get collections
        orders_collection = get_collection('orders')
        users_collection = get_collection('users')
        
        # Get ALL orders
        orders = list(orders_collection.find({}).sort('created_at', -1))
        print(f"✅ Raw orders from database: {len(orders)}")
        
        # Process orders for template
        processed_orders = []
        
        for order in orders:
            try:
                # Create a clean dictionary
                clean_order = {}
                
                # Handle different ID fields
                if '_id' in order:
                    clean_order['_id'] = str(order['_id']) if isinstance(order['_id'], ObjectId) else str(order['_id'])
                
                # Handle order_id - some use _id as order_id, some have separate field
                if 'order_id' in order and order['order_id']:
                    clean_order['order_id'] = str(order['order_id'])
                elif '_id' in order:
                    # Use _id as order_id if no order_id exists
                    id_str = str(order['_id']) if isinstance(order['_id'], ObjectId) else str(order['_id'])
                    # If it starts with MUFRA, use as is, otherwise generate
                    if id_str.startswith('MUFRA'):
                        clean_order['order_id'] = id_str
                    else:
                        clean_order['order_id'] = f"MUFRA{id_str[-8:]}"
                else:
                    clean_order['order_id'] = f"ORDER-{datetime.utcnow().timestamp()}"
                
                # Handle amount/total - some use total_amount, some use total
                if 'total_amount' in order:
                    clean_order['total'] = float(order['total_amount'])
                elif 'total' in order:
                    clean_order['total'] = float(order['total'])
                else:
                    clean_order['total'] = 0
                
                # Handle subtotal
                if 'subtotal' in order:
                    clean_order['subtotal'] = float(order['subtotal'])
                elif 'cart_total' in order:
                    clean_order['subtotal'] = float(order['cart_total'])
                else:
                    clean_order['subtotal'] = clean_order['total'] - order.get('delivery_fee', 0)
                
                # Handle delivery_fee
                if 'delivery_fee' in order:
                    clean_order['delivery_fee'] = float(order['delivery_fee'])
                else:
                    clean_order['delivery_fee'] = 150  # Default
                
                # Handle status
                if 'status' in order:
                    clean_order['status'] = order['status']
                else:
                    clean_order['status'] = 'pending'
                
                # Handle payment_status
                if 'payment_status' in order:
                    clean_order['payment_status'] = order['payment_status']
                elif order.get('paid_at'):
                    clean_order['payment_status'] = 'paid'
                else:
                    clean_order['payment_status'] = 'pending'
                
                # Handle payment_method
                if 'payment_method' in order:
                    clean_order['payment_method'] = order['payment_method']
                else:
                    clean_order['payment_method'] = 'paystack'
                
                # Handle created_at
                if 'created_at' in order and order['created_at']:
                    clean_order['created_at'] = order['created_at']
                else:
                    clean_order['created_at'] = datetime.utcnow()
                
                # Handle updated_at
                if 'updated_at' in order and order['updated_at']:
                    clean_order['updated_at'] = order['updated_at']
                else:
                    clean_order['updated_at'] = datetime.utcnow()
                
                # Handle shipping_address - different formats
                clean_order['shipping_address'] = {}
                
                # Format 1: Direct fields in order
                if 'address' in order or 'city' in order or 'region' in order:
                    clean_order['shipping_address'] = {
                        'street': order.get('address', ''),
                        'city': order.get('city', ''),
                        'county': order.get('region', order.get('county', '')),
                        'postal_code': order.get('postal_code', ''),
                        'phone': order.get('phone', ''),
                        'name': order.get('name', 'Customer')
                    }
                
                # Format 2: shipping_address object
                elif 'shipping_address' in order and isinstance(order['shipping_address'], dict):
                    clean_order['shipping_address'] = order['shipping_address']
                
                # Handle items - CRITICAL: Ensure it's a list
                if 'items' in order:
                    if isinstance(order['items'], list):
                        processed_items = []
                        for item in order['items']:
                            if isinstance(item, dict):
                                item_dict = {}
                                for key, value in item.items():
                                    if isinstance(value, ObjectId):
                                        item_dict[key] = str(value)
                                    else:
                                        item_dict[key] = value
                                processed_items.append(item_dict)
                        clean_order['items'] = processed_items
                    else:
                        # If items is not a list, create empty list
                        clean_order['items'] = []
                else:
                    clean_order['items'] = []
                
                # Handle user_id - could be null for guest checkouts
                user_id = order.get('user_id')
                clean_order['user_name'] = order.get('name', 'Guest Customer')
                clean_order['user_email'] = order.get('email', 'N/A')
                
                if user_id:
                    try:
                        user_id_str = str(user_id) if not isinstance(user_id, ObjectId) else str(user_id)
                        try:
                            user = users_collection.find_one({'_id': ObjectId(user_id_str)})
                        except:
                            user = users_collection.find_one({'_id': user_id_str})
                        
                        if user:
                            clean_order['user_name'] = user.get('name', order.get('name', 'Customer'))
                            clean_order['user_email'] = user.get('email', order.get('email', 'N/A'))
                    except Exception as e:
                        print(f"⚠️ Error getting user: {e}")
                
                processed_orders.append(clean_order)
                
            except Exception as order_error:
                print(f"❌ Error processing order: {order_error}")
                import traceback
                print(traceback.format_exc())
                continue
        
        print(f"✅ Processed {len(processed_orders)} orders for template")
        
        # Return the template with orders
        return render_template('admin/orders.html', orders=processed_orders)
        
    except Exception as e:
        import traceback
        print(f"❌ CRITICAL ERROR in admin_orders: {e}")
        print(traceback.format_exc())
        flash(f'Error loading orders: {str(e)}', 'danger')
        return render_template('admin/orders.html', orders=[])

@app.route('/admin/debug-orders-direct')
@admin_required
def debug_orders_direct():
    """Direct debug to see what's in the orders collection"""
    try:
        orders_collection = get_collection('orders')
        
        # Get raw count
        total_count = orders_collection.count_documents({})
        
        # Get raw documents
        raw_orders = list(orders_collection.find({}).limit(5))
        
        # Convert to JSON-serializable format
        debug_orders = []
        for order in raw_orders:
            order_dict = {}
            for key, value in order.items():
                if isinstance(value, ObjectId):
                    order_dict[key] = str(value)
                elif isinstance(value, datetime):
                    order_dict[key] = value.isoformat()
                elif key == 'items':
                    items = []
                    for item in value:
                        item_dict = {}
                        for ik, iv in item.items():
                            if isinstance(iv, ObjectId):
                                item_dict[ik] = str(iv)
                            else:
                                item_dict[ik] = iv
                        items.append(item_dict)
                    order_dict[key] = items
                else:
                    order_dict[key] = value
            debug_orders.append(order_dict)
        
        return jsonify({
            'total_orders_in_db': total_count,
            'sample_orders': debug_orders,
            'collections': get_db().list_collection_names()
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/admin/update-order-status/<order_id>', methods=['POST'])
@admin_required
def update_order_status(order_id):
    """Update order status"""
    try:
        status = request.form.get('status', '')
        orders_collection = get_collection('orders')
        
        orders_collection.update_one(
            {'order_id': order_id},
            {'$set': {'status': status, 'updated_at': datetime.utcnow()}}
        )
        
        flash('Order status updated', 'success')
        return redirect(url_for('admin_orders'))
    except Exception as e:
        print(f"Error in update_order_status: {e}")
        flash('Error updating order status', 'danger')
        return redirect(url_for('admin_orders'))

@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin user management"""
    try:
        users_collection = get_collection('users')
        users = list(users_collection.find({'role': 'customer'}).sort('created_at', -1))
        return render_template('admin/users.html', users=users)
    except Exception as e:
        print(f"Error in admin_users: {e}")
        flash('Error loading users', 'danger')
        return render_template('admin/users.html', users=[])

# ========== REAL-TIME ADMIN FEATURES ==========

@app.route('/admin/orders-api')
@admin_required
def admin_orders_api():
    """API for real-time admin orders management"""
    try:
        orders_collection = get_collection('orders')
        orders = list(orders_collection.find().sort('created_at', -1).limit(100))
        
        # Convert ObjectId to string for JSON serialization
        for order in orders:
            order['_id'] = str(order['_id'])
            order['created_at'] = order['created_at'].isoformat() if order.get('created_at') else ''
            order['updated_at'] = order['updated_at'].isoformat() if order.get('updated_at') else ''
        
        return jsonify({
            'success': True,
            'orders': orders,
            'total': orders_collection.count_documents({})
        })
    except Exception as e:
        print(f"Error in admin_orders_api: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/update-status/<order_id>', methods=['POST'])
@admin_required
def admin_update_status(order_id):
    """Update order status with real-time notification"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'error': 'Status required'}), 400
        
        orders_collection = get_collection('orders')
        
        # Get order info
        order = orders_collection.find_one({'order_id': order_id})
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404
        
        # Update order status
        orders_collection.update_one(
            {'order_id': order_id},
            {'$set': {
                'status': new_status,
                'updated_at': datetime.utcnow(),
                'status_history': order.get('status_history', []) + [{
                    'status': new_status,
                    'timestamp': datetime.utcnow(),
                    'updated_by': session.get('user_name', 'Admin')
                }]
            }}
        )
        
        # Send email notification to user
        user = get_collection('users').find_one({'_id': order.get('user_id')})
        if user and 'status_updated' in order or True:  # Always send
            try:
                email_status_map = {
                    'processing': 'Processing',
                    'shipped': 'Shipped',
                    'delivered': 'Delivered',
                    'cancelled': 'Cancelled'
                }
                
                msg = Message(
                    subject=f'Order {order_id} Status Update - {email_status_map.get(new_status, new_status)}',
                    recipients=[user.get('email', '')],
                    html=f'''
                    <h2>Order Status Update</h2>
                    <p>Hi {user.get('first_name', 'Customer')},</p>
                    <p>Your order <strong>{order_id}</strong> status has been updated to:</p>
                    <h3 style="color: #D81B60;">{email_status_map.get(new_status, new_status)}</h3>
                    <p>Items: {len(order.get('items', []))} items</p>
                    <p>Total: KES {order.get('total', 0)}</p>
                    <p><a href="{url_for('order_confirmation', order_id=order_id, _external=True)}">View Order Details</a></p>
                    <p>Thank you for shopping at MUFRA FASHIONS!</p>
                    '''
                )
                mail.send(msg)
            except Exception as email_error:
                print(f"Error sending email: {email_error}")
        
        return jsonify({
            'success': True,
            'message': f'Order status updated to {new_status}',
            'order_id': order_id
        })
    except Exception as e:
        print(f"Error in admin_update_status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/order-status/<order_id>')
def get_order_status(order_id):
    """Get order status in real-time (for users)"""
    try:
        orders_collection = get_collection('orders')
        order = orders_collection.find_one({'order_id': order_id})
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404
        
        return jsonify({
            'success': True,
            'status': order.get('status'),
            'status_history': [
                {
                    'status': h.get('status'),
                    'timestamp': h.get('timestamp').isoformat() if h.get('timestamp') else '',
                    'updated_by': h.get('updated_by')
                }
                for h in order.get('status_history', [])
            ],
            'updated_at': order.get('updated_at').isoformat() if order.get('updated_at') else ''
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ========== NEWSLETTER SYSTEM ==========

@app.route('/subscribe-newsletter', methods=['POST'])
def subscribe_newsletter():
    """Subscribe to newsletter"""
    try:
        # Handle both JSON and form data
        if request.is_json:
            email = request.get_json().get('email', '').strip().lower()
        else:
            email = request.form.get('email', '').strip().lower()
        
        if not email or '@' not in email:
            return jsonify({'success': False, 'message': 'Invalid email address'}), 400
        
        subscriptions = get_collection('newsletter_subscriptions')
        
        # Check if already subscribed
        existing = subscriptions.find_one({'email': email})
        if existing and existing.get('subscribed'):
            return jsonify({'success': False, 'message': 'You\'re already subscribed!'}), 400
        
        # Add or update subscription
        subscriptions.update_one(
            {'email': email},
            {'$set': {
                'email': email,
                'subscribed': True,
                'subscribed_at': datetime.utcnow()
            }},
            upsert=True
        )
        
        return jsonify({
            'success': True,
            'message': 'Successfully subscribed to newsletter!'
        })
    except Exception as e:
        print(f"Error in subscribe_newsletter: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 400

@app.route('/unsubscribe-newsletter/<token>', methods=['GET'])
def unsubscribe_newsletter(token):
    """Unsubscribe from newsletter"""
    try:
        # Decode token (simple implementation)
        subscriptions = get_collection('newsletter_subscriptions')
        result = subscriptions.update_one(
            {'_id': ObjectId(token)},
            {'$set': {'subscribed': False, 'unsubscribed_at': datetime.utcnow()}}
        )
        
        if result.modified_count:
            flash('You have been unsubscribed from our newsletter', 'info')
        else:
            flash('Unsubscribe token invalid or already unsubscribed', 'warning')
        
        return redirect(url_for('home'))
    except Exception as e:
        print(f"Error in unsubscribe_newsletter: {e}")
        flash('Error unsubscribing', 'danger')
        return redirect(url_for('home'))

@app.route('/admin/newsletter')
@admin_required
def admin_newsletter():
    """Admin newsletter management"""
    try:
        subscriptions = get_collection('newsletter_subscriptions')
        active_subs = subscriptions.count_documents({'subscribed': True})
        total_subs = subscriptions.count_documents({})
        
        # Get recent newsletters
        newsletters = list(get_collection('newsletters').find().sort('sent_at', -1).limit(20))
        
        return render_template('admin/newsletter.html',
                             active_subscriptions=active_subs,
                             total_subscriptions=total_subs,
                             newsletters=newsletters)
    except Exception as e:
        print(f"Error in admin_newsletter: {e}")
        flash('Error loading newsletter page', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/send-newsletter', methods=['POST'])
@admin_required
def admin_send_newsletter():
    """Send newsletter to all subscribers"""
    try:
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        
        if not subject or not message:
            return jsonify({'success': False, 'error': 'Subject and message required'}), 400
        
        # Get all active subscribers
        subscriptions = get_collection('newsletter_subscriptions')
        subscribers = list(subscriptions.find({'subscribed': True}))
        
        if not subscribers:
            return jsonify({'success': False, 'error': 'No active subscribers'}), 400
        
        # Send emails asynchronously
        successful = 0
        for subscriber in subscribers:
            try:
                msg = Message(
                    subject=subject,
                    recipients=[subscriber.get('email')],
                    html=f'''
                    <h2>{subject}</h2>
                    <div style="font-size: 1rem; line-height: 1.6;">
                        {message}
                    </div>
                    <hr>
                    <p style="font-size: 0.9rem; color: #999;">
                        <a href="{url_for('unsubscribe_newsletter', token=str(subscriber.get('_id')), _external=True)}">Unsubscribe</a>
                    </p>
                    '''
                )
                mail.send(msg)
                successful += 1
            except Exception as e:
                print(f"Error sending to {subscriber.get('email')}: {e}")
        
        # Save newsletter record
        get_collection('newsletters').insert_one({
            'subject': subject,
            'message': message,
            'sent_at': datetime.utcnow(),
            'sent_by': session.get('user_name'),
            'recipients_count': successful,
            'total_subscribers': len(subscribers)
        })
        
        return jsonify({
            'success': True,
            'message': f'Newsletter sent to {successful} subscribers!',
            'sent_count': successful
        })
    except Exception as e:
        print(f"Error in admin_send_newsletter: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/newsletter-stats')
@admin_required
def newsletter_stats():
    """Get newsletter statistics"""
    try:
        subscriptions = get_collection('newsletter_subscriptions')
        newsletters = get_collection('newsletters')
        
        active = subscriptions.count_documents({'subscribed': True})
        inactive = subscriptions.count_documents({'subscribed': False})
        
        recent_newsletters = list(newsletters.find().sort('sent_at', -1).limit(5))
        for nl in recent_newsletters:
            nl['_id'] = str(nl['_id'])
            nl['sent_at'] = nl['sent_at'].isoformat()
        
        return jsonify({
            'success': True,
            'active_subscribers': active,
            'inactive_subscribers': inactive,
            'total_subscribers': active + inactive,
            'recent_newsletters': recent_newsletters
        })
    except Exception as e:
        print(f"Error in newsletter_stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

# ========== OTHER ROUTES ==========

@app.route('/search')
def search():
    """Search products"""
    try:
        query = request.args.get('q', '').strip()
        
        products_collection = get_collection('products')
        if query:
            products = list(products_collection.find({
                '$or': [
                    {'name': {'$regex': query, '$options': 'i'}},
                    {'description': {'$regex': query, '$options': 'i'}},
                    {'category': {'$regex': query, '$options': 'i'}}
                ]
            }))
        else:
            products = []
        
        return render_template('search_results.html', products=products, query=query)
    except Exception as e:
        print(f"Error in search: {e}")
        return render_template('search_results.html', products=[], query=query)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            subject = request.form.get('subject', '').strip()
            order_number = request.form.get('order_number', '').strip()
            message = request.form.get('message', '').strip()
            
            # Validate
            if not all([name, email, message]):
                flash('Please fill in all required fields', 'danger')
                return redirect(url_for('contact'))
            
            # Here you would typically:
            # 1. Save to database
            # 2. Send email to admin
            # 3. Send confirmation email to user
            
            # For now, just show success message
            flash('Thank you for your message! We\'ll get back to you within 24 hours.', 'success')
            return redirect(url_for('contact'))
            
        except Exception as e:
            print(f"Error in contact form: {e}")
            flash('Error sending message. Please try again.', 'danger')
            return redirect(url_for('contact'))
    
    return render_template('contact.html')

@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend OTP"""
    try:
        if 'temp_user_id' not in session:
            return jsonify({'success': False, 'message': 'Session expired'})
        
        users_collection = get_collection('users')
        user = users_collection.find_one({'_id': ObjectId(session['temp_user_id'])})
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Generate new OTP
        otp = generate_otp()
        users_collection.update_one(
            {'_id': ObjectId(session['temp_user_id'])},
            {'$set': {
                'verification_otp': otp,
                'otp_expires': datetime.utcnow() + timedelta(minutes=10)
            }}
        )
        
        # Send new OTP
        send_verification_email(user['email'], user['name'], otp)
        
        return jsonify({'success': True, 'message': 'New OTP sent'})
    except Exception as e:
        print(f"Error in resend_otp: {e}")
        return jsonify({'success': False, 'message': 'Error resending OTP'})

# ========== ERROR HANDLERS ==========

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# ========== CONTEXT PROCESSORS ==========

@app.context_processor
def utility_processor():
    """Make utility functions available in templates - UPDATED FOR MULTIPLE IMAGES"""
    
    def safe_get(obj, key, default=None):
        """Safely get a value from a dictionary or object"""
        if isinstance(obj, dict):
            return obj.get(key, default)
        elif hasattr(obj, key):
            return getattr(obj, key, default)
        return default
    
    def convert_objectid_to_str(obj):
        """Recursively convert ObjectId to string in dictionaries and lists"""
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: convert_objectid_to_str(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_objectid_to_str(item) for item in obj]
        else:
            return obj
    
    def get_product_images(product):
        """Get product images with fallback to single image - HANDLES BOTH FORMATS"""
        if not product:
            return [{
                'url': 'https://via.placeholder.com/400x300?text=Product+Image', 
                'filename': 'placeholder.jpg',
                'is_main': True
            }]
        
        # Check if product has images array
        if 'images' in product and product['images']:
            images = []
            # Ensure all images are properly formatted
            for i, img in enumerate(product['images']):
                if isinstance(img, str):
                    # String URL - convert to dict
                    images.append({
                        'url': img,
                        'filename': img.split('/')[-1] if '/' in img else img,
                        'is_main': i == 0
                    })
                elif isinstance(img, dict):
                    # Already a dict - ensure all fields
                    img_copy = dict(img)
                    img_copy.setdefault('url', img.get('url', 'https://via.placeholder.com/400x300?text=Product+Image'))
                    img_copy.setdefault('filename', img.get('filename', img_copy['url'].split('/')[-1]))
                    img_copy.setdefault('is_main', img.get('is_main', i == 0))
                    images.append(img_copy)
                else:
                    # Unknown format - skip
                    continue
            
            # Ensure at least one image
            if not images:
                images.append({
                    'url': 'https://via.placeholder.com/400x300?text=Product+Image',
                    'filename': 'placeholder.jpg',
                    'is_main': True
                })
            
            # Ensure first image is marked as main
            if images:
                images[0]['is_main'] = True
            
            return images
        
        # Fallback to old image field
        elif 'image' in product and product['image']:
            return [{
                'url': product['image'],
                'filename': product['image'].split('/')[-1] if '/' in product['image'] else product['image'],
                'is_main': True
            }]
        
        # No images found
        else:
            return [{
                'url': 'https://via.placeholder.com/400x300?text=Product+Image',
                'filename': 'placeholder.jpg',
                'is_main': True
            }]
    
    def get_main_product_image(product):
        """Get main product image"""
        images = get_product_images(product)
        if images:
            # Find the main image or use first
            for img in images:
                if img.get('is_main', False):
                    return img['url']
            return images[0]['url']
        return 'https://via.placeholder.com/400x300?text=Product+Image'
    
    def get_product_image(product):
        """Get product image URL, with fallback (legacy compatibility)"""
        return get_main_product_image(product)
    
    def get_user_by_id(user_id):
        """Get user by ID - for use in templates"""
        try:
            users_collection = get_collection('users')
            user = users_collection.find_one({'_id': ObjectId(user_id)})
            if user:
                user = convert_objectid_to_str(user)
            return user
        except:
            return None
    
    def get_cart_count():
        """Get cart count for current user"""
        try:
            if 'user_id' in session:
                users_collection = get_collection('users')
                user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
                return len(user.get('cart', [])) if user else 0
            else:
                return len(session.get('cart', []))
        except:
            return 0
    
    def get_wishlist_count():
        """Get wishlist count for current user"""
        try:
            if 'user_id' in session:
                users_collection = get_collection('users')
                user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
                return len(user.get('wishlist', [])) if user else 0
            else:
                return 0
        except:
            return 0
    
    def format_price(price):
        """Format price with KES currency"""
        try:
            if price is None:
                return "KES 0"
            return f"KES {int(float(price)):,}"
        except (ValueError, TypeError):
            try:
                return f"KES {price}"
            except:
                return "KES 0"
    
    def format_date(date, format='%B %d, %Y'):
        """Format datetime object"""
        try:
            if date:
                return date.strftime(format)
            return "N/A"
        except:
            return "N/A"
    
    def get_order_status_badge(status):
        """Get Bootstrap badge class for order status"""
        status_map = {
            'pending': 'warning',
            'processing': 'info',
            'paid': 'primary',
            'disbursed': 'info',
            'shipped': 'secondary',
            'delivered': 'success',
            'received': 'success',
            'cancelled': 'danger',
            'failed': 'danger'
        }
        return status_map.get(status.lower(), 'secondary')
    
    def get_order_status_icon(status):
        """Get Font Awesome icon class for order status"""
        icon_map = {
            'pending': 'hourglass-start',
            'processing': 'cog',
            'paid': 'credit-card',
            'disbursed': 'hand-holding-box',
            'shipped': 'shipping-fast',
            'delivered': 'check-circle',
            'received': 'box-open',
            'cancelled': 'times-circle',
            'failed': 'exclamation-circle'
        }
        return icon_map.get(status.lower(), 'box')
    
    def get_product_stock_status(stock):
        """Get stock status text and color"""
        try:
            stock_int = int(stock)
            if stock_int == 0:
                return {'text': 'Out of Stock', 'color': 'danger'}
            elif stock_int <= 10:
                return {'text': f'Only {stock_int} left', 'color': 'warning'}
            elif stock_int <= 50:
                return {'text': 'In Stock', 'color': 'info'}
            else:
                return {'text': 'In Stock', 'color': 'success'}
        except:
            return {'text': 'Stock info unavailable', 'color': 'secondary'}
    
    def truncate_text(text, length=100):
        """Truncate text to specified length"""
        if not text:
            return ""
        if len(text) <= length:
            return text
        return text[:length] + "..."
    
    def get_current_year():
        """Get current year"""
        return datetime.now().year
    
    def get_user_role_badge(role):
        """Get badge for user role"""
        role_badges = {
            'admin': 'danger',
            'customer': 'primary',
            'vendor': 'success',
            'staff': 'info'
        }
        return role_badges.get(role, 'secondary')
    
    def get_payment_method_badge(method):
        """Get badge for payment method"""
        method_badges = {
            'paystack': 'primary',
            'mpesa': 'success',
            'cash': 'warning',
            'card': 'info'
        }
        return method_badges.get(method.lower() if method else '', 'secondary')
    
    def calculate_subtotal(cart_items):
        """Calculate subtotal from cart items"""
        try:
            total = 0
            for item in cart_items:
                price = safe_get(item, 'price', 0)
                quantity = safe_get(item, 'quantity', 1)
                total += float(price) * int(quantity)
            return total
        except:
            return 0
    
    def get_paystack_public_key():
        """Get Paystack public key for client-side use"""
        return PAYSTACK_PUBLIC_KEY
    
    def is_paystack_test_mode():
        """Check if Paystack is in test mode"""
        return 'test' in PAYSTACK_PUBLIC_KEY.lower()
    
    def get_payment_status_text(status):
        """Get human-readable payment status text"""
        status_texts = {
            'pending': 'Pending Payment',
            'processing': 'Processing',
            'paid': 'Payment Successful',
            'failed': 'Payment Failed',
            'refunded': 'Refunded',
            'cancelled': 'Cancelled'
        }
        return status_texts.get(status, 'Unknown')
    
    def calculate_delivery_fee(county, subtotal):
        """Calculate delivery fee based on county and subtotal"""
        if not county:
            return 200
        
        county_lower = county.lower()
        
        # Free shipping for Embu orders over 5000
        if 'embu' in county_lower and subtotal >= 5000:
            return 0
        
        # Embu shipping
        if 'embu' in county_lower:
            return 100
        
        # Default shipping for other counties
        return 200
    
    def format_phone_number(phone):
        """Format phone number for display"""
        if not phone:
            return ''
        
        phone_str = str(phone)
        
        # Remove any non-digit characters
        digits = ''.join(filter(str.isdigit, phone_str))
        
        # Format as Kenyan number
        if len(digits) == 9:
            return f"+254{digits}"
        elif len(digits) == 12 and digits.startswith('254'):
            return f"+{digits}"
        elif len(digits) == 10 and digits.startswith('0'):
            return f"+254{digits[1:]}"
        
        # Return as is if format doesn't match
        return phone_str
    
    def get_order_items_count(order):
        """Get total number of items in an order"""
        try:
            items = safe_get(order, 'items', [])
            if isinstance(items, list):
                return sum(safe_get(item, 'quantity', 1) for item in items)
            return 0
        except:
            return 0
    
    def get_recent_orders(limit=5):
        """Get recent orders for the current user"""
        try:
            if 'user_id' not in session:
                return []
            
            orders_collection = get_collection('orders')
            orders = list(orders_collection.find(
                {'user_id': ObjectId(session['user_id'])}
            ).sort('created_at', -1).limit(limit))
            
            # Convert ObjectIds to strings
            orders = convert_objectid_to_str(orders)
            
            return orders
        except:
            return []
    
    def get_recently_viewed(limit=4):
        """Get recently viewed products for the current user"""
        try:
            if 'user_id' not in session:
                return []
            
            users_collection = get_collection('users')
            products_collection = get_collection('products')
            
            user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
            if not user or 'viewed_products' not in user:
                return []
            
            viewed_ids = user.get('viewed_products', [])[-limit:]
            
            # Get the actual products
            products = []
            for pid in viewed_ids:
                product = products_collection.find_one({'_id': pid})
                if product:
                    # Convert ObjectId to string
                    product['_id'] = str(product['_id'])
                    # Ensure images are properly formatted
                    if 'images' not in product or not product['images']:
                        if 'image' in product and product['image']:
                            product['images'] = [{
                                'url': product['image'],
                                'filename': product['image'].split('/')[-1] if '/' in product['image'] else product['image'],
                                'is_main': True
                            }]
                        else:
                            product['images'] = [{
                                'url': 'https://via.placeholder.com/400x300?text=Product+Image',
                                'filename': 'placeholder.jpg',
                                'is_main': True
                            }]
                    products.append(product)
            
            return products
        except Exception as e:
            print(f"Error in get_recently_viewed: {e}")
            return []
    
    def get_featured_products(limit=8):
        """Get featured products with proper image handling"""
        try:
            products_collection = get_collection('products')
            products = list(products_collection.find(
                {'featured': True}
            ).limit(limit))
            
            # Process each product to ensure proper image structure
            for product in products:
                # Convert ObjectId to string
                product['_id'] = str(product['_id'])
                product.setdefault('rating', 0)
                product.setdefault('reviews_count', 0)
                product.setdefault('stock', 0)
                product.setdefault('sizes', [])
                product.setdefault('colors', [])
                product.setdefault('featured', False)
                
                # Ensure images are properly formatted
                if 'images' not in product or not product['images']:
                    if 'image' in product and product['image']:
                        product['images'] = [{
                            'url': product['image'],
                            'filename': product['image'].split('/')[-1] if '/' in product['image'] else product['image'],
                            'is_main': True
                        }]
                    else:
                        product['images'] = [{
                            'url': 'https://via.placeholder.com/400x300?text=Product+Image',
                            'filename': 'placeholder.jpg',
                            'is_main': True
                        }]
                else:
                    # Ensure each image has all required fields
                    formatted_images = []
                    for i, img in enumerate(product['images']):
                        if isinstance(img, str):
                            formatted_images.append({
                                'url': img,
                                'filename': img.split('/')[-1] if '/' in img else img,
                                'is_main': i == 0
                            })
                        elif isinstance(img, dict):
                            img_copy = dict(img)
                            img_copy.setdefault('url', img.get('url', 'https://via.placeholder.com/400x300?text=Product+Image'))
                            img_copy.setdefault('filename', img.get('filename', img_copy['url'].split('/')[-1]))
                            img_copy.setdefault('is_main', img.get('is_main', i == 0))
                            formatted_images.append(img_copy)
                    product['images'] = formatted_images
                    # Ensure first image is main
                    if product['images']:
                        product['images'][0]['is_main'] = True
            
            return products
        except Exception as e:
            print(f"Error in get_featured_products: {e}")
            return []
    
    def get_product_reviews(product_id):
        """Get reviews for a product"""
        try:
            reviews_collection = get_collection('reviews')
            reviews = list(reviews_collection.find(
                {'product_id': ObjectId(product_id)}
            ).sort('created_at', -1))
            
            # Convert ObjectIds to strings
            for review in reviews:
                review['_id'] = str(review['_id'])
                review['user_id'] = str(review['user_id'])
                review['product_id'] = str(review['product_id'])
            
            return reviews
        except:
            return []
    
    def get_average_rating(product_id):
        """Calculate average rating for a product"""
        try:
            reviews = get_product_reviews(product_id)
            if not reviews:
                return 0
            
            total_rating = sum(review.get('rating', 0) for review in reviews)
            return round(total_rating / len(reviews), 1)
        except:
            return 0
    
    def get_payment_icon(method):
        """Get icon for payment method"""
        icons = {
            'paystack': 'fas fa-credit-card',
            'mpesa': 'fas fa-mobile-alt',
            'card': 'fas fa-credit-card',
            'cash': 'fas fa-money-bill-wave',
            'bank': 'fas fa-university'
        }
        return icons.get(method.lower(), 'fas fa-money-bill')
    
    def get_delivery_time(county):
        """Get estimated delivery time based on county"""
        if not county:
            return "3-5 business days"
        
        county_lower = county.lower()
        
        if 'embu' in county_lower:
            return "1-2 business days"
        elif county_lower in ['nairobi', 'mombasa', 'kisumu', 'nakuru']:
            return "2-3 business days"
        else:
            return "3-5 business days"
    
    def can_cancel_order(order):
        """Check if order can be cancelled"""
        try:
            status = safe_get(order, 'status', '')
            created_at = safe_get(order, 'created_at')
            
            if status not in ['pending', 'processing']:
                return False
            
            if not created_at:
                return False
            
            # Allow cancellation within 1 hour of order
            time_diff = datetime.utcnow() - created_at
            return time_diff.total_seconds() <= 3600  # 1 hour in seconds
            
        except:
            return False
    
    def get_currency_symbol():
        """Get currency symbol"""
        return "KES"
    
    def format_order_id(order_id):
        """Format order ID for display"""
        if not order_id:
            return "N/A"
        
        # If it's a MongoDB ObjectId, convert to string
        if isinstance(order_id, ObjectId):
            return str(order_id)[-8:].upper()
        
        # If it starts with MUFRA, use as is
        if str(order_id).startswith('MUFRA'):
            return order_id
        
        # Otherwise, truncate
        return str(order_id)[-8:].upper()
    
    def get_image_count(product):
        """Get the number of images for a product"""
        images = get_product_images(product)
        return len(images)
    
    def get_product_categories():
        """Get all product categories"""
        try:
            categories_collection = get_collection('categories')
            categories = list(categories_collection.find({}).sort('name', 1))
            # Convert ObjectIds to strings
            for cat in categories:
                cat['_id'] = str(cat['_id'])
            return categories
        except:
            return []
    
    def get_product_by_id(product_id):
        """Get product by ID with proper image handling"""
        try:
            products_collection = get_collection('products')
            product = products_collection.find_one({'_id': ObjectId(product_id)})
            if product:
                # Convert ObjectId to string
                product['_id'] = str(product['_id'])
                # Ensure images are properly formatted
                if 'images' not in product or not product['images']:
                    if 'image' in product and product['image']:
                        product['images'] = [{
                            'url': product['image'],
                            'filename': product['image'].split('/')[-1] if '/' in product['image'] else product['image'],
                            'is_main': True
                        }]
                    else:
                        product['images'] = [{
                            'url': 'https://via.placeholder.com/400x300?text=Product+Image',
                            'filename': 'placeholder.jpg',
                            'is_main': True
                        }]
                else:
                    # Ensure each image has all required fields
                    formatted_images = []
                    for i, img in enumerate(product['images']):
                        if isinstance(img, str):
                            formatted_images.append({
                                'url': img,
                                'filename': img.split('/')[-1] if '/' in img else img,
                                'is_main': i == 0
                            })
                        elif isinstance(img, dict):
                            img_copy = dict(img)
                            img_copy.setdefault('url', img.get('url', 'https://via.placeholder.com/400x300?text=Product+Image'))
                            img_copy.setdefault('filename', img.get('filename', img_copy['url'].split('/')[-1]))
                            img_copy.setdefault('is_main', img.get('is_main', i == 0))
                            formatted_images.append(img_copy)
                    product['images'] = formatted_images
                    # Ensure first image is main
                    if product['images']:
                        product['images'][0]['is_main'] = True
            return product
        except Exception as e:
            print(f"Error in get_product_by_id: {e}")
            return None
    
    def is_product_featured(product):
        """Check if product is featured"""
        return safe_get(product, 'featured', False)
    
    def get_product_discount_price(original_price, discount_percentage):
        """Calculate discounted price"""
        try:
            if discount_percentage > 0:
                discount_amount = (original_price * discount_percentage) / 100
                return original_price - discount_amount
            return original_price
        except:
            return original_price
    
    def format_number(number, decimals=0):
        """Format number with commas"""
        try:
            if number is None:
                return "0"
            return f"{float(number):,.{decimals}f}"
        except:
            return str(number)
    
    def get_session_user():
        """Get current session user"""
        try:
            if 'user_id' in session:
                users_collection = get_collection('users')
                user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
                if user:
                    user = convert_objectid_to_str(user)
                return user
        except:
            return None
    
    def is_user_admin():
        """Check if current user is admin"""
        user = get_session_user()
        return user and user.get('role') == 'admin'
    
    def is_user_verified():
        """Check if current user is verified"""
        user = get_session_user()
        return user and user.get('verified', False)
    
    def get_product_availability(product):
        """Get product availability status"""
        stock = safe_get(product, 'stock', 0)
        if stock <= 0:
            return {'status': 'out_of_stock', 'text': 'Out of Stock', 'color': 'danger'}
        elif stock <= 5:
            return {'status': 'low_stock', 'text': 'Low Stock', 'color': 'warning'}
        else:
            return {'status': 'in_stock', 'text': 'In Stock', 'color': 'success'}
    
    def get_product_condition_badge(condition):
        """Get badge for product condition"""
        condition_badges = {
            'new': 'success',
            'second hand': 'info',
            'used': 'warning',
            'refurbished': 'secondary'
        }
        return condition_badges.get(condition.lower(), 'secondary')
    
    def get_random_products(limit=4):
        """Get random products with proper image handling"""
        try:
            products_collection = get_collection('products')
            products = list(products_collection.aggregate([
                {'$match': {}},
                {'$sample': {'size': limit}},
                {'$addFields': {
                    'images': {'$ifNull': ['$images', []]}
                }}
            ]))
            
            # Process each product to ensure proper image structure
            for product in products:
                # Convert ObjectId to string
                product['_id'] = str(product['_id'])
                product.setdefault('rating', 0)
                product.setdefault('reviews_count', 0)
                
                if 'images' not in product or not product['images']:
                    if 'image' in product and product['image']:
                        product['images'] = [{
                            'url': product['image'],
                            'filename': product['image'].split('/')[-1] if '/' in product['image'] else product['image'],
                            'is_main': True
                        }]
                    else:
                        product['images'] = [{
                            'url': 'https://via.placeholder.com/400x300?text=Product+Image',
                            'filename': 'placeholder.jpg',
                            'is_main': True
                        }]
                else:
                    # Ensure each image has all required fields
                    formatted_images = []
                    for i, img in enumerate(product['images']):
                        if isinstance(img, str):
                            formatted_images.append({
                                'url': img,
                                'filename': img.split('/')[-1] if '/' in img else img,
                                'is_main': i == 0
                            })
                        elif isinstance(img, dict):
                            img_copy = dict(img)
                            img_copy.setdefault('url', img.get('url', 'https://via.placeholder.com/400x300?text=Product+Image'))
                            img_copy.setdefault('filename', img.get('filename', img_copy['url'].split('/')[-1]))
                            img_copy.setdefault('is_main', img.get('is_main', i == 0))
                            formatted_images.append(img_copy)
                    product['images'] = formatted_images
                    if product['images']:
                        product['images'][0]['is_main'] = True
            
            return products
        except Exception as e:
            print(f"Error in get_random_products: {e}")
            return []
    
    def get_product_similar_products(product_id, limit=4):
        """Get similar products based on category with proper image handling"""
        try:
            products_collection = get_collection('products')
            product = products_collection.find_one({'_id': ObjectId(product_id)})
            
            if not product:
                return []
            
            similar_products = list(products_collection.find({
                '_id': {'$ne': ObjectId(product_id)},
                'category': product.get('category', '')
            }).limit(limit))
            
            # Process each similar product
            for p in similar_products:
                p['_id'] = str(p['_id'])
                p['images'] = get_product_images(p)
            
            return similar_products
        except Exception as e:
            print(f"Error in get_product_similar_products: {e}")
            return []
    
    def get_product_main_image(product):
        """Get the main image URL from product images"""
        images = get_product_images(product)
        for img in images:
            if img.get('is_main', False):
                return img['url']
        return images[0]['url'] if images else 'https://via.placeholder.com/400x300?text=Product+Image'
    
    def get_product_image_urls(product):
        """Get list of image URLs from product"""
        images = get_product_images(product)
        return [img['url'] for img in images]
    
    def has_multiple_images(product):
        """Check if product has multiple images"""
        images = get_product_images(product)
        return len(images) > 1
    
    def get_product_image_by_index(product, index=0):
        """Get product image by index"""
        images = get_product_images(product)
        if 0 <= index < len(images):
            return images[index]
        return {'url': 'https://via.placeholder.com/400x300?text=Product+Image', 'filename': 'placeholder.jpg', 'is_main': True}
    
    def get_product_image_filenames(product):
        """Get list of image filenames from product"""
        images = get_product_images(product)
        return [img.get('filename', '') for img in images if img.get('filename')]
    
    def get_cart_item_image(cart_item):
        """Get image for cart item"""
        if 'image' in cart_item and cart_item['image']:
            return cart_item['image']
        
        # Try to get from product
        if 'product_id' in cart_item:
            product = get_product_by_id(cart_item['product_id'])
            if product:
                return get_product_main_image(product)
        
        return 'https://via.placeholder.com/100x100?text=Product'

    def get_cart_item_images(cart_item):
        """Get images for cart item - handles both dict and object formats"""
        try:
            # If product_id exists, try to get the full product
            product_id = cart_item.get('product_id') if isinstance(cart_item, dict) else getattr(cart_item, 'product_id', None)
            if product_id:
                # Convert to ObjectId if it's a string
                from bson.objectid import ObjectId
                try:
                    if isinstance(product_id, str):
                        product_obj_id = ObjectId(product_id)
                    else:
                        product_obj_id = product_id
                    
                    products_collection = get_collection('products')
                    product = products_collection.find_one({'_id': product_obj_id})
                    
                    if product:
                        return get_product_images(product)
                except Exception:
                    pass
            
            # Fallback to cart item's image field
            image_field = None
            if isinstance(cart_item, dict):
                image_field = cart_item.get('image')
            else:
                image_field = getattr(cart_item, 'image', None)

            if image_field:
                return [{
                    'url': image_field,
                    'filename': image_field.split('/')[-1] if '/' in image_field else image_field,
                    'is_main': True
                }]
            
            # Default placeholder
            return [{
                'url': 'https://via.placeholder.com/100x100?text=Product',
                'filename': 'placeholder.jpg',
                'is_main': True
            }]
        except Exception as e:
            print(f"Error in get_cart_item_images: {e}")
            return [{
                'url': 'https://via.placeholder.com/100x100?text=Product',
                'filename': 'placeholder.jpg',
                'is_main': True
            }]
    
    def process_product_images(products):
        """Process multiple products to ensure proper image structure"""
        for product in products:
            if 'images' not in product or not product['images']:
                if 'image' in product and product['image']:
                    product['images'] = [{
                        'url': product['image'],
                        'filename': product['image'].split('/')[-1] if '/' in product['image'] else product['image'],
                        'is_main': True
                    }]
                else:
                    product['images'] = [{
                        'url': 'https://via.placeholder.com/400x300?text=Product+Image',
                        'filename': 'placeholder.jpg',
                        'is_main': True
                    }]
            else:
                # Ensure each image has all required fields
                formatted_images = []
                for i, img in enumerate(product['images']):
                    if isinstance(img, str):
                        formatted_images.append({
                            'url': img,
                            'filename': img.split('/')[-1] if '/' in img else img,
                            'is_main': i == 0
                        })
                    elif isinstance(img, dict):
                        img_copy = dict(img)
                        img_copy.setdefault('url', img.get('url', 'https://via.placeholder.com/400x300?text=Product+Image'))
                        img_copy.setdefault('filename', img.get('filename', img_copy['url'].split('/')[-1]))
                        img_copy.setdefault('is_main', img.get('is_main', i == 0))
                        formatted_images.append(img_copy)
                product['images'] = formatted_images
                if product['images']:
                    product['images'][0]['is_main'] = True
        
        return products
    
    def get_product_variations(product):
        """Get product variations (sizes and colors)"""
        sizes = safe_get(product, 'sizes', [])
        colors = safe_get(product, 'colors', [])
        
        variations = []
        if sizes:
            variations.append({
                'name': 'Size',
                'values': sizes,
                'type': 'size'
            })
        if colors:
            variations.append({
                'name': 'Color',
                'values': colors,
                'type': 'color'
            })
        
        return variations
    
    return dict(
        # Built-in functions (avoid overriding core Jinja filters like 'len' and 'list')
        enumerate=enumerate,
        str=str,
        int=int,
        float=float,
        range=range,
        
        # Core helper functions
        safe_get=safe_get,
        format_price=format_price,
        format_date=format_date,
        format_number=format_number,
        truncate_text=truncate_text,
        get_current_year=get_current_year,
        format_phone_number=format_phone_number,
        convert_objectid_to_str=convert_objectid_to_str,
        
        # Image handling functions (UPDATED)
        get_product_images=get_product_images,
        get_main_product_image=get_main_product_image,
        get_product_main_image=get_product_main_image,
        get_product_image=get_product_image,  # Legacy compatibility
        get_product_image_urls=get_product_image_urls,
        get_product_image_by_index=get_product_image_by_index,
        get_product_image_filenames=get_product_image_filenames,
        get_image_count=get_image_count,
        has_multiple_images=has_multiple_images,
        process_product_images=process_product_images,
        
        # Product functions
        get_product_by_id=get_product_by_id,
        get_product_categories=get_product_categories,
        get_featured_products=get_featured_products,
        get_random_products=get_random_products,
        get_product_similar_products=get_product_similar_products,
        get_product_reviews=get_product_reviews,
        get_average_rating=get_average_rating,
        get_product_stock_status=get_product_stock_status,
        get_product_availability=get_product_availability,
        get_product_condition_badge=get_product_condition_badge,
        get_product_discount_price=get_product_discount_price,
        get_product_variations=get_product_variations,
        is_product_featured=is_product_featured,
        
        # User functions
        get_user_by_id=get_user_by_id,
        get_session_user=get_session_user,
        is_user_admin=is_user_admin,
        is_user_verified=is_user_verified,
        get_user_role_badge=get_user_role_badge,
        get_cart_count=get_cart_count,
        get_wishlist_count=get_wishlist_count,
        get_cart_item_image=get_cart_item_image,
        
        # Order functions
        get_recent_orders=get_recent_orders,
        get_recently_viewed=get_recently_viewed,  # ADDED THIS LINE
        get_order_status_badge=get_order_status_badge,
        get_order_status_icon=get_order_status_icon,
        get_order_items_count=get_order_items_count,
        format_order_id=format_order_id,
        can_cancel_order=can_cancel_order,
        
        # Cart functions
        calculate_subtotal=calculate_subtotal,
        
        # Payment functions
        get_payment_method_badge=get_payment_method_badge,
        get_payment_status_text=get_payment_status_text,
        get_payment_icon=get_payment_icon,
        get_paystack_public_key=get_paystack_public_key,
        is_paystack_test_mode=is_paystack_test_mode,
        
        # Shipping functions
        calculate_delivery_fee=calculate_delivery_fee,
        get_delivery_time=get_delivery_time,
        get_currency_symbol=get_currency_symbol,
        
        # Database utility
        get_collection=get_collection,
        
        # Other utilities
        datetime=datetime,
        request=request,
        session=session,
        
        # Configuration
        PAYSTACK_PUBLIC_KEY=PAYSTACK_PUBLIC_KEY,
        PAYSTACK_BASE_URL=PAYSTACK_BASE_URL
    )

# ========== APPLICATION STARTUP ==========
# ========== JINJA2 FILTERS ==========
app.jinja_env.globals.update(now=now)
@app.route('/admin/bulk-delete-products', methods=['POST'])
@admin_required
def bulk_delete_products():
    """Bulk delete products"""
    try:
        data = request.get_json()
        product_ids = data.get('product_ids', [])
        
        if not product_ids:
            return jsonify({'success': False, 'message': 'No products selected'})
        
        products_collection = get_collection('products')
        
        # Convert string IDs to ObjectId
        object_ids = [ObjectId(pid) for pid in product_ids]
        
        # Delete products
        result = products_collection.delete_many({'_id': {'$in': object_ids}})
        
        return jsonify({
            'success': True, 
            'message': f'{result.deleted_count} product(s) deleted successfully',
            'deleted_count': result.deleted_count
        })
    except Exception as e:
        print(f"Error in bulk_delete_products: {e}")
        return jsonify({'success': False, 'message': 'Error deleting products'}), 500

@app.route('/admin/toggle-product-status/<product_id>')
@admin_required
def toggle_product_status(product_id):
    """Toggle product status between active and draft"""
    try:
        products_collection = get_collection('products')
        product = products_collection.find_one({'_id': ObjectId(product_id)})
        
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('admin_products'))
        
        new_status = 'draft' if product.get('status') == 'active' else 'active'
        
        products_collection.update_one(
            {'_id': ObjectId(product_id)},
            {'$set': {'status': new_status}}
        )
        
        flash(f'Product status changed to {new_status}', 'success')
        return redirect(url_for('admin_products'))
    except Exception as e:
        print(f"Error in toggle_product_status: {e}")
        flash('Error updating product status', 'danger')
        return redirect(url_for('admin_products'))

@app.route('/admin/toggle-featured/<product_id>')
@admin_required
def toggle_featured(product_id):
    """Toggle featured status of a product"""
    try:
        products_collection = get_collection('products')
        product = products_collection.find_one({'_id': ObjectId(product_id)})
        
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('admin_products'))
        
        new_featured = not product.get('featured', False)
        
        products_collection.update_one(
            {'_id': ObjectId(product_id)},
            {'$set': {'featured': new_featured}}
        )
        
        status = 'featured' if new_featured else 'unfeatured'
        flash(f'Product {status} successfully', 'success')
        return redirect(url_for('admin_products'))
    except Exception as e:
        print(f"Error in toggle_featured: {e}")
        flash('Error updating featured status', 'danger')
        return redirect(url_for('admin_products'))

@app.route('/admin/duplicate-product/<product_id>', methods=['GET', 'POST'])
@admin_required
def duplicate_product(product_id):
    """Duplicate a product"""
    try:
        products_collection = get_collection('products')
        
        if request.method == 'GET':
            product = products_collection.find_one({'_id': ObjectId(product_id)})
            if not product:
                flash('Product not found', 'danger')
                return redirect(url_for('admin_products'))
            return render_template('admin/duplicate_product.html', product=product)
        
        elif request.method == 'POST':
            product = products_collection.find_one({'_id': ObjectId(product_id)})
            if not product:
                flash('Product not found', 'danger')
                return redirect(url_for('admin_products'))
            
            # Get form data
            new_name = request.form.get('new_name', f"{product['name']} (Copy)")
            copy_images = request.form.get('copy_images') == 'on'
            draft_status = request.form.get('draft_status') == 'on'
            
            # Create a copy of the product
            new_product = dict(product)
            
            # Remove MongoDB _id to create a new document
            new_product.pop('_id', None)
            
            # Update fields
            new_product['name'] = new_name
            new_product['status'] = 'draft' if draft_status else 'active'
            new_product['featured'] = False  # Reset featured status for copy
            new_product['created_at'] = datetime.utcnow()
            new_product['updated_at'] = datetime.utcnow()
            
            # Insert the duplicated product
            result = products_collection.insert_one(new_product)
            
            flash(f'Product duplicated successfully!', 'success')
            return redirect(url_for('admin_products'))
            
    except Exception as e:
        print(f"Error in duplicate_product: {e}")
        flash('Error duplicating product', 'danger')
        return redirect(url_for('admin_products'))

# Register format_number as a Jinja2 filter
@app.template_filter('format_number')
def format_number_filter(number, decimals=0):
    """Format number with commas - Jinja2 filter version"""
    try:
        if number is None:
            return "0"
        return f"{float(number):,.{decimals}f}"
    except (ValueError, TypeError):
        return str(number)

# Register other filters you need
@app.template_filter('format_date')
def format_date_filter(date, format='%B %d, %Y'):
    """Format datetime object - Jinja2 filter version"""
    try:
        if date:
            return date.strftime(format)
        return "N/A"
    except (AttributeError, ValueError):
        return "N/A"

@app.template_filter('format_order_id')
def format_order_id_filter(order_id):
    """Format order ID for display - Jinja2 filter version"""
    if not order_id:
        return "N/A"
    
    # If it's a MongoDB ObjectId, convert to string
    if isinstance(order_id, ObjectId):
        return str(order_id)[-8:].upper()
    
    # If it starts with MUFRA, use as is
    if str(order_id).startswith('MUFRA'):
        return order_id
    
    # Otherwise, truncate
    return str(order_id)[-8:].upper()

# You might also need this filter that's used in your template:
@app.template_filter('format_price')
def format_price_filter(price):
    """Format price with KES currency - Jinja2 filter version"""
    try:
        if price is None:
            return "KES 0"
        return f"KES {int(float(price)):,}"
    except (ValueError, TypeError):
        try:
            return f"KES {price}"
        except:
            return "KES 0"

# ========== PERFORMANCE OPTIMIZATION ==========
@app.after_request
def set_cache_headers(response):
    """Add caching headers for static files to reduce server load"""
    if request.path.startswith('/static/'):
        # Cache static assets for 30 days
        response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'
        response.headers['Vary'] = 'Accept-Encoding'
    else:
        # Don't cache HTML pages
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response

if __name__ == '__main__':
    print("\n" + "="*50)
    print("Starting MUFRA FASHIONS Application")
    print("="*50)
    
    # Initialize database
    with app.app_context():
        try:
            initialize_sample_data()
        except Exception as e:
            print(f"⚠ Database initialization warning: {e}")
    
    print(f"\n📦 MongoDB: {MONGODB_CONNECTION_STRING[:60]}...")
    print(f"📧 Email: {'Configured' if app.config['MAIL_USERNAME'] else 'Console mode'}")
    print(f"💳 Paystack: {'Test mode' if 'test' in PAYSTACK_PUBLIC_KEY else 'Live mode'}")
    print("\n🚀 Server running on http://localhost:5000")
    print("="*50 + "\n")
    
    app.run(debug=True, port=5000, host='0.0.0.0')