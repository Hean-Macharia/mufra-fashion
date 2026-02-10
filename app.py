import os
import json
import random
import string
from datetime import datetime, timezone
from datetime import timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
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
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@mufrafashions.com')
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
    """Send email to a recipient using direct SMTP"""
    try:
        print(f"\n{'='*60}")
        print(f"📧 SENDING EMAIL TO: {to}")
        print(f"📋 SUBJECT: {subject}")
        print(f"📝 TEMPLATE: {template}")
        
        # Always show OTP in console for development
        if 'otp' in kwargs:
            print(f"🔐 OTP FOR USER: {kwargs['otp']}")
            print(f"   User can enter this code to verify")
        
        # Check if we should suppress sending
        if app.config.get('MAIL_SUPPRESS_SEND', False):
            print(f"\n⚠️  MAIL_SUPPRESS_SEND is True - email will not be sent")
            print(f"{'='*60}\n")
            return True
        
        # Use direct SMTP (more reliable than Flask-Mail)
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = to
        
        try:
            # Try to render templates
            html_body = render_template(f'emails/{template}.html', **kwargs)
            text_body = render_template(f'emails/{template}.txt', **kwargs)
        except:
            # Fallback templates
            html_body = f"""
            <html>
            <body>
                <h2>{subject}</h2>
                <p>Hello {kwargs.get('name', 'User')},</p>
                <p>Your verification code is: <strong>{kwargs.get('otp', 'N/A')}</strong></p>
            </body>
            </html>
            """
            text_body = f"{subject}\n\nHello {kwargs.get('name', 'User')},\n\nYour verification code is: {kwargs.get('otp', 'N/A')}"
        
        # Attach parts
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        
        print(f"✅ Email sent successfully to: {to}")
        print(f"{'='*60}\n")
        return True
        
    except Exception as e:
        print(f"❌ ERROR SENDING EMAIL: {e}")
        print(f"\n🔍 Debug info:")
        print(f"  To: {to}")
        print(f"  Subject: {subject}")
        
        if 'otp' in kwargs:
            print(f"\n🔐 IMPORTANT: OTP FOR USER: {kwargs['otp']}")
            print(f"   User can use this code to verify their account")
        
        print(f"{'='*60}\n")
        return False
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
        
        # Create sample products if none exist
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
                    'image': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80',
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
                    'image': 'https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80',
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
                    'image': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80',
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
                    'image': 'https://images.unsplash.com/photo-1542272604-787c3835535d?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80',
                    'featured': True,
                    'rating': 4.3,
                    'reviews_count': 18,
                    'created_at': datetime.utcnow()
                }
            ]
            products_collection.insert_many(products)
            print("✓ Products created successfully")
        
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
    """Handle Paystack callback after payment"""
    try:
        reference = request.args.get('reference', '')
        
        if not reference:
            flash('Invalid payment reference', 'danger')
            return redirect(url_for('account'))
        
        print(f"🔍 Paystack callback received for reference: {reference}")
        
        # Verify payment
        verification = verify_paystack_payment(reference)
        
        if verification and verification.get('status'):
            data = verification.get('data', {})
            status = data.get('status', 'failed')
            metadata = data.get('metadata', {})
            order_id = metadata.get('order_id', '')
            
            print(f"🔍 Verification status: {status}, Order ID: {order_id}")
            
            if not order_id:
                flash('Order ID not found in payment metadata', 'danger')
                return redirect(url_for('account'))
            
            orders_collection = get_collection('orders')
            products_collection = get_collection('products')
            users_collection = get_collection('users')
            
            # Find order
            order = orders_collection.find_one({'order_id': order_id})
            
            if not order:
                flash('Order not found', 'danger')
                return redirect(url_for('account'))
            
            if status == 'success':
                # Payment successful
                orders_collection.update_one(
                    {'order_id': order_id},
                    {'$set': {
                        'payment_status': 'paid',
                        'status': 'processing',
                        'payment_reference': reference,
                        'payment_date': datetime.now(timezone.utc),
                        'updated_at': datetime.now(timezone.utc)
                    }}
                )
                
                # Update product stock
                for item in order.get('items', []):
                    products_collection.update_one(
                        {'_id': item.get('product_id')},
                        {'$inc': {'stock': -item.get('quantity', 1)}}
                    )
                
                # Clear user's cart
                users_collection.update_one(
                    {'_id': order['user_id']},
                    {'$set': {'cart': []}}
                )
                
                # Get user email
                user = users_collection.find_one({'_id': order['user_id']})
                if user:
                    # Send order confirmation email
                    send_order_confirmation(
                        email=user['email'],
                        order_id=order_id,
                        total=order.get('total', 0),
                        items=order.get('items', []),
                        shipping_address=order.get('shipping_address', {})
                    )
                
                flash('Payment successful! Your order has been confirmed.', 'success')
                return redirect(url_for('order_confirmation', order_id=order_id))
            else:
                # Payment failed
                orders_collection.update_one(
                    {'order_id': order_id},
                    {'$set': {
                        'payment_status': 'failed',
                        'status': 'failed',
                        'updated_at': datetime.now(timezone.utc)
                    }}
                )
                
                flash('Payment failed. Please try again.', 'danger')
                return redirect(url_for('checkout'))
        else:
            flash('Payment verification failed', 'danger')
            return redirect(url_for('checkout'))
            
    except Exception as e:
        print(f"Error in paystack_callback: {e}")
        flash('Error processing payment. Please contact support.', 'danger')
        return redirect(url_for('account'))
    
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
        for product in featured_products:
            product.setdefault('rating', 0)
            product.setdefault('reviews_count', 0)
            product.setdefault('image', 'https://via.placeholder.com/400x300?text=Product+Image')
        
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
                    
                    for product in recommended_products:
                        product.setdefault('rating', 0)
                        product.setdefault('reviews_count', 0)
                        product.setdefault('image', 'https://via.placeholder.com/400x300?text=Product+Image')
        
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
        
        # Ensure product has all required fields
        product.setdefault('rating', 0)
        product.setdefault('reviews_count', 0)
        product.setdefault('stock', 0)
        product.setdefault('sizes', [])
        product.setdefault('colors', [])
        product.setdefault('image', 'https://via.placeholder.com/400x300?text=Product+Image')
        
        # Get reviews
        reviews = list(reviews_collection.find({'product_id': ObjectId(product_id)}).sort('created_at', -1))
        
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
            p.setdefault('rating', 0)
            p.setdefault('reviews_count', 0)
            p.setdefault('image', 'https://via.placeholder.com/400x300?text=Product+Image')
        
        # Debug output
        print(f"\n🔍 DEBUG: Loading product details for {product_id}")
        print(f"🔍 DEBUG: Product found: {product.get('name')}")
        print(f"🔍 DEBUG: Reviews count: {len(reviews)}")
        print(f"🔍 DEBUG: Related products: {len(related_products)}\n")
        
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
    """Add item to cart"""
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
        
        # Create cart item
        cart_item = {
            'product_id': ObjectId(product_id),
            'name': product['name'],
            'price': product['price'],
            'size': size,
            'color': color,
            'quantity': quantity,
            'image': product.get('image', ''),
            'stock': product.get('stock', 0)
        }
        
        if 'user_id' in session:
            # Logged in user - store in database
            users_collection = get_collection('users')
            user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
            cart = user.get('cart', [])
            
            # Check if item already exists
            item_found = False
            for item in cart:
                if (str(item['product_id']) == product_id and 
                    item.get('size') == size and 
                    item.get('color') == color):
                    item['quantity'] += quantity
                    item_found = True
                    break
            
            if not item_found:
                cart.append(cart_item)
            
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
            for item in cart:
                if (str(item['product_id']) == product_id and 
                    item.get('size') == size and 
                    item.get('color') == color):
                    item['quantity'] += quantity
                    item_found = True
                    break
            
            if not item_found:
                cart.append(cart_item)
            
            session['cart'] = cart
            cart_count = len(cart)
        
        return jsonify({'success': True, 'message': 'Added to cart', 'cart_count': cart_count})
    except Exception as e:
        print(f"Error in add_to_cart: {e}")
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
    """Process checkout and create order - always uses Paystack"""
    try:
        users_collection = get_collection('users')
        products_collection = get_collection('products')
        orders_collection = get_collection('orders')
        
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        cart_items = user.get('cart', [])
        
        if not cart_items:
            return jsonify({'success': False, 'message': 'Cart is empty'})
        
        # Get shipping address
        shipping_address = {
            'street': request.form.get('street', ''),
            'city': request.form.get('city', ''),
            'county': request.form.get('county', ''),
            'postal_code': request.form.get('postal_code', ''),
            'phone': request.form.get('phone', '')
        }
        
        # Validate required fields
        required_fields = ['street', 'city', 'county', 'phone']
        for field in required_fields:
            if not shipping_address[field]:
                return jsonify({'success': False, 'message': f'Please enter your {field}'})
        
        # Calculate totals
        subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart_items)
        county = shipping_address.get('county', '').lower()
        delivery_fee = 100 if 'embu' in county else 200
        total = subtotal + delivery_fee
        
        # Create order
        order_id = generate_order_id()
        order = {
            'order_id': order_id,
            'user_id': ObjectId(session['user_id']),
            'items': cart_items,
            'shipping_address': shipping_address,
            'payment_method': 'paystack',
            'subtotal': subtotal,
            'delivery_fee': delivery_fee,
            'total': total,
            'status': 'pending',
            'payment_status': 'pending',
            'paystack_reference': None,
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
                # Update order with Paystack reference
                orders_collection.update_one(
                    {'order_id': order_id},
                    {'$set': {
                        'paystack_reference': paystack_response.get('data', {}).get('reference'),
                        'paystack_authorization_url': paystack_response.get('data', {}).get('authorization_url')
                    }}
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Redirecting to secure payment...',
                    'payment_method': 'paystack',
                    'authorization_url': paystack_response.get('data', {}).get('authorization_url'),
                    'reference': paystack_response.get('data', {}).get('reference'),
                    'order_id': order_id,
                    'amount': total
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Payment initialization failed. Please try again.'
                })
                
        except Exception as paystack_error:
            print(f"Paystack initialization error: {paystack_error}")
            return jsonify({
                'success': False,
                'message': 'Payment service temporarily unavailable. Please try again.'
            })
        
    except Exception as e:
        print(f"Error in process_checkout: {e}")
        return jsonify({'success': False, 'message': str(e)})
    


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
@app.route('/order-confirmation/<order_id>')
@login_required
def order_confirmation(order_id):
    """Order confirmation page"""
    try:
        print(f"\n🔍 DEBUG: Loading order confirmation for {order_id}")
        print(f"🔍 DEBUG: User ID in session: {session.get('user_id')}")
        
        orders_collection = get_collection('orders')
        order = orders_collection.find_one({'order_id': order_id})
        
        print(f"🔍 DEBUG: Order found: {order is not None}")
        
        if not order:
            print(f"🔍 DEBUG: Order not found in database")
            flash('Order not found', 'danger')
            return redirect(url_for('home'))
        
        if str(order['user_id']) != session['user_id']:
            print(f"🔍 DEBUG: User mismatch. Order user: {order['user_id']}, Session user: {session['user_id']}")
            flash('Order not found', 'danger')
            return redirect(url_for('home'))
        
        # Convert ObjectId to string for template safety
        order['_id'] = str(order['_id'])
        order['user_id'] = str(order['user_id'])
        
        # Ensure items is properly formatted as a list
        if 'items' in order:
            if not isinstance(order['items'], list):
                order['items'] = []
        
        # Ensure all items have product_id as string
        for item in order.get('items', []):
            if 'product_id' in item:
                item['product_id'] = str(item['product_id'])
        
        # Ensure all required fields exist in order
        order.setdefault('subtotal', 0)
        order.setdefault('delivery_fee', 0)
        order.setdefault('total', 0)
        order.setdefault('status', 'pending')
        order.setdefault('payment_status', 'pending')
        order.setdefault('payment_method', 'paystack')  # Changed from mpesa to paystack
        order.setdefault('shipping_address', {})
        order.setdefault('created_at', datetime.now(timezone.utc))  # Fixed deprecation
        order.setdefault('updated_at', datetime.now(timezone.utc))  # Fixed deprecation
        
        print(f"🔍 DEBUG: Order prepared for template. Items count: {len(order.get('items', []))}")
        print(f"🔍 DEBUG: Order keys: {list(order.keys())}")
        
        # Check payment status from query parameter
        payment_status = request.args.get('payment', '')
        if payment_status == 'success':
            order['payment_status'] = 'paid'
        elif payment_status == 'pending':
            order['payment_status'] = 'pending'
        
        return render_template('order_confirmation.html', order=order)
        
    except Exception as e:
        print(f"\n❌ ERROR in order_confirmation: {e}")
        import traceback
        print(f"❌ ERROR Traceback: {traceback.format_exc()}")
        
        flash('Error loading order confirmation', 'danger')
        return redirect(url_for('home'))
@app.route('/debug-order/<order_id>')
@login_required
def debug_order(order_id):
    """Debug order data"""
    try:
        orders_collection = get_collection('orders')
        order = orders_collection.find_one({'order_id': order_id})
        
        if not order or str(order['user_id']) != session['user_id']:
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
    """User registration"""
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
                'verified': False,
                'cart': [],
                'wishlist': [],
                'created_at': datetime.utcnow()
            }
            
            # Generate OTP
            otp = generate_otp()
            user['verification_otp'] = otp
            user['otp_expires'] = datetime.utcnow() + timedelta(minutes=10)
            
            # Save user
            result = users_collection.insert_one(user)
            
            # Send verification email
            email_sent = send_verification_email(email, name, otp)
            
            if email_sent:
                flash('Registration successful! Check your email for verification code.', 'success')
            else:
                flash(f'Registration successful! Your verification code: {otp}', 'info')
            
            session['temp_user_id'] = str(result.inserted_id)
            return redirect(url_for('verify_email'))
        
        return render_template('register.html')
    except Exception as e:
        print(f"Error in register: {e}")
        flash('Error during registration', 'danger')
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
    """User account dashboard"""
    try:
        print(f"\n🔍 ACCOUNT ROUTE CALLED:")
        print(f"🔍 User ID: {session.get('user_id')}")
        print(f"🔍 User Name: {session.get('user_name')}")
        
        users_collection = get_collection('users')
        orders_collection = get_collection('orders')
        
        # Get user
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        
        if not user:
            print(f"❌ User not found in database")
            flash('User not found', 'danger')
            return redirect(url_for('home'))
        
        print(f"✅ User found: {user.get('name')}")
        
        # Convert ObjectId to string
        user['_id'] = str(user['_id'])
        
        # Ensure all required fields exist with defaults
        defaults = {
            'name': 'Customer',
            'email': '',
            'phone': '',
            'role': 'customer',
            'cart': [],
            'wishlist': [],
            'addresses': [],
            'profile_picture': '',
            'verified': False,
            'created_at': datetime.now(),
            'last_login': datetime.now()
        }
        
        for key, default_value in defaults.items():
            if key not in user:
                user[key] = default_value
        
        # Handle cart and wishlist specifically
        if isinstance(user.get('cart'), list):
            user['cart'] = user['cart']
        else:
            user['cart'] = []
            
        if isinstance(user.get('wishlist'), list):
            user['wishlist'] = user['wishlist']
        else:
            user['wishlist'] = []
        
        print(f"🔍 Cart items: {len(user['cart'])}")
        print(f"🔍 Wishlist items: {len(user['wishlist'])}")
        
        # Get orders
        try:
            orders = list(orders_collection.find({'user_id': ObjectId(session['user_id'])})
                         .sort('created_at', -1).limit(20))
            print(f"🔍 Orders retrieved: {len(orders)}")
            
            # Process each order
            processed_orders = []
            for order in orders:
                order_copy = dict(order)  # Convert to regular dict
                order_copy['_id'] = str(order_copy['_id'])
                order_copy['user_id'] = str(order_copy['user_id'])
                
                # CRITICAL FIX: Ensure items is a proper list
                if 'items' in order_copy:
                    # Check if items is a method/function
                    if callable(order_copy['items']):
                        print(f"⚠️ Order {order_copy.get('order_id', 'N/A')}: items is a method/function")
                        order_copy['items'] = []
                    elif isinstance(order_copy['items'], list):
                        # Ensure all items have proper structure
                        fixed_items = []
                        for item in order_copy['items']:
                            if isinstance(item, dict):
                                fixed_items.append(item)
                            else:
                                print(f"⚠️ Item is not a dict: {type(item)}")
                        order_copy['items'] = fixed_items
                    else:
                        print(f"⚠️ Order {order_copy.get('order_id', 'N/A')}: items is {type(order_copy['items'])}")
                        order_copy['items'] = []
                else:
                    order_copy['items'] = []
                
                # Set defaults for order fields
                order_defaults = {
                    'order_id': order_copy.get('order_id', f'ORDER-{str(order_copy["_id"])[:8]}'),
                    'status': 'pending',
                    'payment_status': 'pending',
                    'subtotal': 0,
                    'delivery_fee': 0,
                    'total': 0,
                    'payment_method': 'mpesa',
                    'shipping_address': {},
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                
                for key, value in order_defaults.items():
                    if key not in order_copy:
                        order_copy[key] = value
                
                processed_orders.append(order_copy)
            
            orders = processed_orders
            
        except Exception as order_error:
            print(f"⚠ Error fetching orders: {order_error}")
            import traceback
            print(f"⚠ Order error traceback: {traceback.format_exc()}")
            orders = []
        
        print(f"✅ Account data prepared successfully")
        print(f"✅ Rendering template with {len(orders)} orders")
        
        # Debug: Check first order structure
        if orders:
            print(f"🔍 First order structure:")
            print(f"  - Order ID: {orders[0].get('order_id')}")
            print(f"  - Items type: {type(orders[0].get('items'))}")
            print(f"  - Items length: {len(orders[0].get('items', []))}")
            print(f"  - Items content: {orders[0].get('items', [])[:2]}")
        
        return render_template('account.html', user=user, orders=orders)
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR in account route: {e}")
        import traceback
        print(f"❌ TRACEBACK: {traceback.format_exc()}")
        flash('Error loading account page. Please try again.', 'danger')
        return redirect(url_for('home'))

# ADD THESE ROUTES RIGHT HERE, RIGHT AFTER THE ACCOUNT ROUTE:

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


# ========== ACCOUNT MANAGEMENT ROUTES ==========



# ========== OTHER ROUTES ==========
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

@app.route('/admin/add-product', methods=['GET', 'POST'])
@admin_required
def add_product():
    """Add new product"""
    try:
        if request.method == 'POST':
            # Get form data
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            price = float(request.form.get('price', 0))
            category = request.form.get('category', '')
            subcategory = request.form.get('subcategory', '').strip()
            condition = request.form.get('condition', 'New')
            stock = int(request.form.get('stock', 0))
            
            # Get sizes and colors
            sizes = request.form.getlist('sizes[]')
            colors = request.form.getlist('colors[]')
            
            # Handle image upload
            image_url = ''
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Save file
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    # Create URL for the image
                    image_url = f"/static/uploads/{filename}"
                elif request.form.get('image_url'):  # Allow URL input as alternative
                    image_url = request.form.get('image_url', '').strip()
            
            # If no image uploaded, use a placeholder
            if not image_url:
                image_url = 'https://via.placeholder.com/400x300?text=Product+Image'
            
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
                'image': image_url,  # Use full URL/path
                'featured': bool(request.form.get('featured')),
                'rating': 0,
                'reviews_count': 0,
                'created_at': datetime.utcnow()
            }
            
            products_collection.insert_one(product)
            flash('Product added successfully', 'success')
            return redirect(url_for('admin_products'))
        
        categories_collection = get_collection('categories')
        categories = list(categories_collection.find({}))
        return render_template('admin/add_product.html', categories=categories)
    except Exception as e:
        print(f"Error in add_product: {e}")
        flash('Error adding product', 'danger')
        return redirect(url_for('admin_products'))

@app.route('/admin/edit-product/<product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    """Edit product"""
    try:
        products_collection = get_collection('products')
        product = products_collection.find_one({'_id': ObjectId(product_id)})
        
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('admin_products'))
        
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
            
            # Handle image upload or URL
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    update_data['image'] = f"/static/uploads/{filename}"
            elif request.form.get('image_url'):  # Allow URL input
                update_data['image'] = request.form.get('image_url', '').strip()
            
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
    """Admin order management"""
    try:
        orders_collection = get_collection('orders')
        orders = list(orders_collection.find().sort('created_at', -1))
        return render_template('admin/orders.html', orders=orders)
    except Exception as e:
        print(f"Error in admin_orders: {e}")
        flash('Error loading orders', 'danger')
        return render_template('admin/orders.html', orders=[])

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
    """Make utility functions available in templates"""
    
    def safe_get(obj, key, default=None):
        """Safely get a value from a dictionary or object"""
        if isinstance(obj, dict):
            return obj.get(key, default)
        elif hasattr(obj, key):
            return getattr(obj, key, default)
        return default
    
    def get_product_image(product):
        """Get product image URL, with fallback"""
        if not product:
            return 'https://via.placeholder.com/400x300?text=Product+Image'
        
        image = safe_get(product, 'image', '')
        if not image:
            return 'https://via.placeholder.com/400x300?text=Product+Image'
        
        # If it's already a full URL or starts with /static, return as is
        if image.startswith('http') or image.startswith('/static'):
            return image
        
        # Otherwise, assume it's in uploads folder
        return f"/static/uploads/{image}"
    
    def get_user_by_id(user_id):
        """Get user by ID - for use in templates"""
        try:
            users_collection = get_collection('users')
            user = users_collection.find_one({'_id': ObjectId(user_id)})
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
            'shipped': 'secondary',
            'delivered': 'success',
            'cancelled': 'danger',
            'failed': 'danger'
        }
        return status_map.get(status.lower(), 'secondary')
    
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
            
            return orders
        except:
            return []
    
    def get_featured_products(limit=4):
        """Get featured products"""
        try:
            products_collection = get_collection('products')
            products = list(products_collection.find(
                {'featured': True}
            ).limit(limit))
            
            for product in products:
                product.setdefault('rating', 0)
                product.setdefault('reviews_count', 0)
                product.setdefault('image', 'https://via.placeholder.com/400x300?text=Product+Image')
            
            return products
        except:
            return []
    
    def get_product_reviews(product_id):
        """Get reviews for a product"""
        try:
            reviews_collection = get_collection('reviews')
            reviews = list(reviews_collection.find(
                {'product_id': ObjectId(product_id)}
            ).sort('created_at', -1))
            
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
    
    return dict(
        # Built-in functions
        enumerate=enumerate,
        len=len,
        str=str,
        int=int,
        float=float,
        list=list,
        range=range,
        
        # Custom helper functions
        safe_get=safe_get,
        get_product_image=get_product_image,
        get_user_by_id=get_user_by_id,
        get_cart_count=get_cart_count,
        get_wishlist_count=get_wishlist_count,
        format_price=format_price,
        format_date=format_date,
        get_order_status_badge=get_order_status_badge,
        get_product_stock_status=get_product_stock_status,
        truncate_text=truncate_text,
        get_current_year=get_current_year,
        get_user_role_badge=get_user_role_badge,
        get_payment_method_badge=get_payment_method_badge,
        calculate_subtotal=calculate_subtotal,
        get_paystack_public_key=get_paystack_public_key,
        is_paystack_test_mode=is_paystack_test_mode,
        get_payment_status_text=get_payment_status_text,
        calculate_delivery_fee=calculate_delivery_fee,
        format_phone_number=format_phone_number,
        get_order_items_count=get_order_items_count,
        get_recent_orders=get_recent_orders,
        get_featured_products=get_featured_products,
        get_product_reviews=get_product_reviews,
        get_average_rating=get_average_rating,
        get_payment_icon=get_payment_icon,
        get_delivery_time=get_delivery_time,
        can_cancel_order=can_cancel_order,
        get_currency_symbol=get_currency_symbol,
        format_order_id=format_order_id,
        
        # Other utilities
        datetime=datetime,
        get_collection=get_collection,
        request=request,
        session=session,
        
        # Paystack configuration
        PAYSTACK_PUBLIC_KEY=PAYSTACK_PUBLIC_KEY,
        PAYSTACK_BASE_URL=PAYSTACK_BASE_URL
    )

# ========== APPLICATION STARTUP ==========

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