import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_pymongo import PyMongo
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from bson.objectid import ObjectId
from datetime import datetime
import bcrypt
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mufra-fashions-secret-key-2024')

# MongoDB Atlas Connection
MONGODB_URI = "mongodb+srv://iconichean:1Loye8PM3YwlV5h4@cluster0.meufk73.mongodb.net/mufra_fashions?retryWrites=true&w=majority"
app.config["MONGO_URI"] = MONGODB_URI

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
            delivery_fee = 100 if region == 'embu' else 200
            total_amount = cart_total + delivery_fee
            
            # Build complete order data
            order_data = {
                'name': request.form.get('name'),
                'phone': request.form.get('phone'),
                'address': request.form.get('address'),
                'city': request.form.get('city'),
                'region': request.form.get('region'),
                'payment_method': request.form.get('payment_method'),
                'payment_number': request.form.get('payment_number'),
                'delivery_fee': delivery_fee,
                'cart_total': cart_total,
                'total_amount': total_amount,
                'items': cart_items,  # ✅ Now saving cart items
                'status': 'pending',
                'created_at': datetime.now(),
                'session_id': session.sid,  # Track session
                'user_id': session.get('user_id')  # Link to user if logged in
            }
            
            # Save order to database or session
            if db_connected:
                result = mongo.db.orders.insert_one(order_data)
                order_id = str(result.inserted_id)
                print(f"✅ Order saved to database: {order_id}")
            else:
                # Save to session for demo
                if 'orders' not in session:
                    session['orders'] = []
                order_data['_id'] = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
                session['orders'].append(order_data)
                session.modified = True
                order_id = order_data['_id']
                print(f"✅ Order saved to session: {order_id}")

            # Clear cart
            session.pop('cart', None)

            return redirect(url_for('order_confirmation', order_id=order_id))

        except Exception as e:
            print(f"❌ Checkout error: {e}")
            return render_template('checkout.html', error=str(e))

    # GET request → show checkout form
    return render_template('checkout.html')

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