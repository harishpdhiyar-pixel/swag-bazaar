import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import sqlite3
import csv
import io
import re
import time
import secrets
from datetime import datetime
from collections import defaultdict
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- 1. PERSISTENT STRONG SECRET KEY ---
KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.secret_key')
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, 'r', encoding='utf-8') as f:
        app.secret_key = f.read().strip()
else:
    new_key = secrets.token_hex(32)
    with open(KEY_FILE, 'w', encoding='utf-8') as f:
        f.write(new_key)
    app.secret_key = new_key

# Cookie Security Configuration
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_NAME='sbz_session',
    PERMANENT_SESSION_LIFETIME=86400  # 24 hours
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swag_bazaar.db')

# --- 2. SECURITY: BRUTE FORCE & RATE LIMITING ---
# In-memory tracking of failed logins & order spam
FAILED_LOGINS = defaultdict(lambda: {'count': 0, 'locked_until': 0})
ORDER_LIMITS = defaultdict(list)

def get_client_ip():
    # Supports Cloudflare / Render / Nginx reverse proxies
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'

# Security Headers Middleware
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    return response

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                title_hi TEXT,
                category TEXT NOT NULL,
                price INTEGER NOT NULL,
                original_price INTEGER NOT NULL,
                discount INTEGER,
                image_url TEXT NOT NULL,
                affiliate_url TEXT NOT NULL,
                badge TEXT,
                description TEXT,
                sizes TEXT,
                platform_name TEXT DEFAULT 'Direct Store',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Orders / Leads table (secure customer storage)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                customer_address TEXT NOT NULL,
                customer_city TEXT NOT NULL,
                customer_state TEXT NOT NULL,
                customer_pincode TEXT NOT NULL,
                product_id INTEGER,
                product_title TEXT NOT NULL,
                product_price INTEGER NOT NULL,
                selected_size TEXT,
                quantity INTEGER DEFAULT 1,
                payment_method TEXT DEFAULT 'COD',
                status TEXT DEFAULT 'New Order',
                order_note TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        # Default settings with HASHED PIN for unbreakable security
        default_pin_hash = generate_password_hash('1234')
        
        cursor.execute('SELECT value FROM settings WHERE key = "admin_pin"')
        existing_pin = cursor.fetchone()
        
        if not existing_pin:
            cursor.execute('INSERT INTO settings (key, value) VALUES ("admin_pin", ?)', (default_pin_hash,))
        elif not existing_pin[0].startswith('scrypt:') and not existing_pin[0].startswith('pbkdf2:'):
            # Auto-upgrade plaintext pin to secure cryptographic hash!
            hashed = generate_password_hash(existing_pin[0])
            cursor.execute('UPDATE settings SET value = ? WHERE key = "admin_pin"', (hashed,))
            
        # Other default store settings
        defaults = [
            ('whatsapp_number', '919876543210'),
            ('store_name_hi', 'स्वैग बाज़ार'),
            ('store_name_en', 'SWAG BAZAAR'),
            ('insta_handle', '@swagbazaar_official'),
            ('upi_id', 'swagbazaar@upi')
        ]
        for key, val in defaults:
            cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, val))
            
        cursor.execute('SELECT COUNT(*) FROM products')
        count = cursor.fetchone()[0]
        if count == 0:
            seed_sample_products(cursor)
            
        conn.commit()

def seed_sample_products(cursor):
    sample_products = [
        # 1. JEANS (जींस)
        (
            'Baggy Wide Leg Cargo Denim Jeans',
            'बैगी कार्गो डेनिम जींस (ट्रेंडिंग रील स्टाइल)',
            'jeans',
            799, 1999, 60,
            'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?auto=format&fit=crop&w=700&q=80',
            'https://amazon.in?tag=swagbazaar-21',
            '🔥 Instagram Viral',
            'प्रीमियम हेवी डेनिम फैब्रिक, 6 पॉकेट्स के साथ सुपर कम्फर्टेबल बैगी फिट।',
            '28, 30, 32, 34, 36',
            'Resell Special / Amazon'
        ),
        (
            'Distressed Washed Slim Fit Jeans',
            'डिस्ट्रेस्ड स्लिम फिट रफ जींस',
            'jeans',
            849, 2199, 61,
            'https://images.unsplash.com/photo-1542272604-780c96856592?auto=format&fit=crop&w=700&q=80',
            'https://flipkart.com?affid=swagbazaar',
            '⚡ 61% OFF',
            'स्ट्रेचेबल रफ स्टाइल डेनिम जींस, पार्टी और कैज़ुअल वियर के लिए परफेक्ट।',
            '30, 32, 34',
            'Flipkart / Direct'
        ),
        # 2. SHIRT (शर्ट)
        (
            'Korean Oversized Linen Casual Shirt',
            'कोरियन ओवरसाइज़्ड लिनन शर्ट',
            'shirt',
            549, 1399, 60,
            'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=700&q=80',
            'https://meesho.com?ref=swagbazaar',
            '✨ Old Money Aesthetic',
            'सॉफ्ट ब्रीदेबल फैब्रिक, लाइटवेट और रिच एलिगेंट लुक।',
            'M, L, XL, XXL',
            'Meesho / Direct'
        ),
        (
            'Cuban Collar Tropical Printed Shirt',
            'क्यूबन कॉलर फ्लोरल समर शर्ट',
            'shirt',
            499, 1299, 61,
            'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=700&q=80',
            'https://amazon.in?tag=swagbazaar-21',
            '🔥 Trending Look',
            'वाइब्रेंट ट्रॉपिकल प्रिंट्स के साथ अल्ट्रा-स्मूथ रेयान फैब्रिक।',
            'S, M, L, XL',
            'Amazon'
        ),
        # 3. PANT (पैंट)
        (
            'Korean Pleated Relaxed Fit Trousers',
            'कोरियन प्लीटेड रिलैक्स्ड ट्राउजर्स पैंट',
            'pant',
            649, 1699, 62,
            'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=700&q=80',
            'https://myntra.com?aff=swagbazaar',
            '👑 Luxury Look',
            'रिंकल-फ्री प्रीमियम फैब्रिक, परफेक्ट फॉल और मॉडर्न कोरियन कट।',
            '28, 30, 32, 34',
            'Myntra / Resell'
        ),
        (
            '6-Pocket Tactical Streetwear Cargo Pant',
            '6-पॉकेट टैक्टिकल स्ट्रीटवियर कार्गो पैंट',
            'pant',
            699, 1799, 61,
            'https://images.unsplash.com/photo-1517445312882-bc9910d016b7?auto=format&fit=crop&w=700&q=80',
            'https://meesho.com?ref=swagbazaar',
            '📸 Instagram Hit',
            'मजबूत कॉटन ट्विल फैब्रिक, डीप यूटिलिटी पॉकेट्स।',
            'M, L, XL',
            'Meesho'
        ),
        # 4. T-SHIRT (टी-शर्ट)
        (
            'Anime Graphic Heavyweight Oversized Tee',
            'एनीमे ग्राफिक हैवीवेट ओवरसाइज़्ड टी-शर्ट',
            'tshirt',
            449, 1199, 62,
            'https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?auto=format&fit=crop&w=700&q=80',
            'https://amazon.in?tag=swagbazaar-21',
            '🔥 Bestseller',
            '240 GSM प्योर कॉटन, हाई डेफिनिशन बैक ग्राफिक प्रिंट।',
            'M, L, XL, XXL',
            'Amazon / Direct'
        ),
        (
            'Acid Wash Vintage Drop-Shoulder Tee',
            'एसिड वॉश विंटेज ड्रॉप शोल्डर टी-शर्ट',
            'tshirt',
            429, 1099, 61,
            'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=700&q=80',
            'https://flipkart.com?affid=swagbazaar',
            '⚡ 61% OFF',
            'विंटेज वॉश लुक, सॉफ्ट कॉटन और कम्फर्टेबल स्ट्रीट ड्रॉप शोल्डर फिट।',
            'S, M, L, XL',
            'Flipkart'
        ),
        # 5. CAP (कैप / टोपी)
        (
            'NY Vintage Embroidered Streetwear Cap',
            'एनवाई विंटेज एम्ब्रॉयडर्ड बेसबॉल कैप',
            'cap',
            299, 799, 62,
            'https://images.unsplash.com/photo-1588850561407-ed78c282e89b?auto=format&fit=crop&w=700&q=80',
            'https://amazon.in?tag=swagbazaar-21',
            '🧢 Top Trending',
            'प्रीमियम 3D एम्ब्रॉयडरी, एडजस्टेबल स्ट्रैप बैक और 100% ब्रीदेबल कॉटन।',
            'Free Size (Adjustable)',
            'Amazon'
        ),
        (
            'Aesthetic Minimalist Dad Hat Snapback',
            'मिनिमल एस्थेटिक स्नैपबैक कैप',
            'cap',
            279, 699, 60,
            'https://images.unsplash.com/photo-1575428652377-a2d80e2277fc?auto=format&fit=crop&w=700&q=80',
            'https://meesho.com?ref=swagbazaar',
            '✨ Viral Piece',
            'अट्रैक्टिव कलर और यूनिसेक्स डिज़ाइन।',
            'Free Size',
            'Meesho'
        ),
        # 6. CHASHMA (चश्मा / सनग्लासेस)
        (
            'Cyberpunk Matrix Retro Black Sunglasses',
            'साइबरपंक मैट्रिक्स रेट्रो ब्लैक सनग्लासेस',
            'chashma',
            349, 999, 65,
            'https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=700&q=80',
            'https://amazon.in?tag=swagbazaar-21',
            '🕶️ Reel Viral',
            'UV400 प्रोटेक्टेड डार्क लैंस, लाइटवेट मेटल-पॉलीकार्बोनेट फ्रेम।',
            'Free Size',
            'Amazon'
        ),
        (
            'Luxury Gold Rimless Hexagon Goggles',
            'लक्ज़री गोल्ड रिमलेस हेक्सागोन चश्मा',
            'chashma',
            399, 1199, 67,
            'https://images.unsplash.com/photo-1508296695146-257a814070b4?auto=format&fit=crop&w=700&q=80',
            'https://flipkart.com?affid=swagbazaar',
            '⚡ 67% OFF',
            'रिच गोल्डन फ्रेम फिनिश, प्रीमियम ग्रेडिएंट टिंटेड लैंस।',
            'Free Size',
            'Flipkart'
        ),
        # 7. BEAUTY (ब्यूटी व ग्रूमिंग)
        (
            'Hydrating Glow Vitamin C Face Serum & Mist',
            'विटामिन सी ग्लोइंग फेस सीरम कॉम्बो',
            'beauty',
            449, 1099, 59,
            'https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=700&q=80',
            'https://amazon.in?tag=swagbazaar-21',
            '✨ Instant Glow',
            'नेचुरल इंग्रीडिएंट्स से बना डीप हाइड्रेशन और इंस्टेंट ग्लो सीरम।',
            '30ml + 50ml Combo',
            'Amazon'
        ),
        (
            'Matte Liquid Velvet Lip & Cheek Tint Combo (Set of 3)',
            'मैट वेलवेट लिप व चीक टिंट कॉम्बो (सेट ऑफ 3)',
            'beauty',
            399, 999, 60,
            'https://images.unsplash.com/photo-1586495777744-4413f21062fa?auto=format&fit=crop&w=700&q=80',
            'https://meesho.com?ref=swagbazaar',
            '💄 Super Viral',
            '12 घंटे तक लॉन्ग-लास्टिंग वाटरप्रूफ टिंट।',
            'Pack of 3 Shades',
            'Meesho / Direct'
        )
    ]
    cursor.executemany('''
        INSERT INTO products (
            title, title_hi, category, price, original_price, discount,
            image_url, affiliate_url, badge, description, sizes, platform_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_products)

def get_settings_dict():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM settings')
        return {row['key']: row['value'] for row in cursor.fetchall()}

# Categories definition
CATEGORIES = [
    {'id': 'all', 'name_hi': 'सभी प्रोडक्ट्स', 'name_en': 'All Swag', 'icon': '✨'},
    {'id': 'jeans', 'name_hi': 'जींस', 'name_en': 'Jeans', 'icon': '👖'},
    {'id': 'shirt', 'name_hi': 'शर्ट', 'name_en': 'Shirt', 'icon': '👔'},
    {'id': 'pant', 'name_hi': 'पैंट', 'name_en': 'Pant', 'icon': '👖'},
    {'id': 'tshirt', 'name_hi': 'टी-शर्ट', 'name_en': 'T-Shirt', 'icon': '👕'},
    {'id': 'cap', 'name_hi': 'कैप', 'name_en': 'Cap', 'icon': '🧢'},
    {'id': 'chashma', 'name_hi': 'चश्मा', 'name_en': 'Chashma', 'icon': '🕶️'},
    {'id': 'beauty', 'name_hi': 'ब्यूटी', 'name_en': 'Beauty', 'icon': '💄'}
]

# Helper to sanitize strings
def clean_str(val, max_len=200):
    if not val:
        return ''
    # Remove HTML tags & trim
    clean = re.sub(r'<[^>]*>', '', str(val)).strip()
    return clean[:max_len]

# --- STOREFRONT ROUTES ---
@app.route('/')
def home():
    cat = request.args.get('category', 'all')
    search = clean_str(request.args.get('q', ''))
    
    with get_db() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM products WHERE 1=1'
        params = []
        
        if cat and cat != 'all':
            query += ' AND category = ?'
            params.append(cat)
            
        if search:
            query += ' AND (title LIKE ? OR title_hi LIKE ? OR description LIKE ?)'
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param])
            
        query += ' ORDER BY id DESC'
        cursor.execute(query, params)
        products = [dict(row) for row in cursor.fetchall()]
        
    settings = get_settings_dict()
    return render_template('index.html', products=products, categories=CATEGORIES, current_cat=cat, search=search, settings=settings)

@app.route('/api/products')
def api_products():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products ORDER BY id DESC')
        products = [dict(row) for row in cursor.fetchall()]
    return jsonify(products)

# --- SECURE ORDER PLACEMENT (LEAD CAPTURE) ---
@app.route('/api/order', methods=['POST'])
def place_order():
    ip = get_client_ip()
    current_t = time.time()
    
    # Anti-Spam: Max 10 orders per 10 minutes per IP
    recent_orders = [t for t in ORDER_LIMITS[ip] if current_t - t < 600]
    ORDER_LIMITS[ip] = recent_orders
    if len(recent_orders) >= 10:
        return jsonify({'success': False, 'message': 'कृपया थोड़ा इंतज़ार करें! बहुत अधिक रिक्वेस्ट दर्ज हुई हैं।'}), 429

    data = request.json or request.form
    customer_name = clean_str(data.get('name', ''), 100)
    customer_phone = clean_str(data.get('phone', ''), 15)
    customer_address = clean_str(data.get('address', ''), 300)
    customer_city = clean_str(data.get('city', ''), 100)
    customer_state = clean_str(data.get('state', ''), 100)
    customer_pincode = clean_str(data.get('pincode', ''), 10)
    product_id = data.get('product_id')
    selected_size = clean_str(data.get('size', 'Standard'), 50)
    payment_method = clean_str(data.get('payment_method', 'Cash on Delivery (COD)'), 50)
    order_note = clean_str(data.get('order_note', ''), 200)
    
    try:
        quantity = max(1, min(10, int(data.get('quantity', 1))))
    except:
        quantity = 1

    # Strict Validation
    if not customer_name or len(customer_name) < 2:
        return jsonify({'success': False, 'message': 'कृपया सही ग्राहक नाम दर्ज करें!'}), 400

    # Phone validation (10 digits Indian mobile)
    phone_digits = re.sub(r'\D', '', customer_phone)
    if len(phone_digits) != 10:
        return jsonify({'success': False, 'message': 'कृपया वैध 10 अंकों का मोबाइल नंबर दर्ज करें!'}), 400

    # Pincode validation (6 digits Indian postal code)
    pin_digits = re.sub(r'\D', '', customer_pincode)
    if len(pin_digits) != 6:
        return jsonify({'success': False, 'message': 'कृपया सही 6 अंकों का पिनकोड दर्ज करें!'}), 400

    if not customer_address or len(customer_address) < 5:
        return jsonify({'success': False, 'message': 'कृपया पूरा डिलीवरी पता दर्ज करें!'}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        prod = cursor.fetchone()
        
        if not prod:
            return jsonify({'success': False, 'message': 'प्रोडक्ट नहीं मिला!'}), 404
            
        order_code = f"SBZ-{secrets.randbelow(90000) + 10000}"
        total_amount = prod['price'] * quantity
        
        cursor.execute('''
            INSERT INTO orders (
                order_id, customer_name, customer_phone, customer_address, customer_city,
                customer_state, customer_pincode, product_id, product_title, product_price,
                selected_size, quantity, payment_method, order_note, status, ip_address
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_code, customer_name, phone_digits, customer_address, customer_city,
            customer_state, pin_digits, prod['id'], prod['title'], total_amount,
            selected_size, quantity, payment_method, order_note, 'New Order', ip
        ))
        conn.commit()

    ORDER_LIMITS[ip].append(current_t)

    settings = get_settings_dict()
    owner_wa = settings.get('whatsapp_number', '919876543210')
    
    wa_msg = (
        f"🛍️ *नया ऑर्डर - Swag Bazaar*\n"
        f"🆔 ऑर्डर कोड: *{order_code}*\n\n"
        f"📦 *प्रोडक्ट:* {prod['title']}\n"
        f"📏 *साइज़:* {selected_size}\n"
        f"🔢 *मात्रा:* {quantity}\n"
        f"💰 *कुल मूल्य:* ₹{total_amount}\n"
        f"💳 *भुगतान माध्यम:* {payment_method}\n\n"
        f"👤 *ग्राहक विवरण:*\n"
        f"• नाम: {customer_name}\n"
        f"• मोबाइल: {phone_digits}\n"
        f"• पता: {customer_address}, {customer_city}, {customer_state} - {pin_digits}\n"
    )
    if order_note:
        wa_msg += f"• नोट: {order_note}\n"
    
    wa_msg += "\nकृपया मेरा ऑर्डर कन्फर्म करें!"
    import urllib.parse
    wa_link = f"https://wa.me/{owner_wa}?text={urllib.parse.quote(wa_msg)}"

    return jsonify({
        'success': True,
        'order_id': order_code,
        'product_title': prod['title'],
        'total_amount': total_amount,
        'whatsapp_url': wa_link,
        'message': 'ऑर्डर सफलतापूर्वक दर्ज हो गया है!'
    })

# --- ADMIN SECURITY & AUTHENTICATION ---
@app.route('/admin')
def admin_page():
    settings = get_settings_dict()
    is_logged_in = session.get('is_admin', False)
    
    orders = []
    products = []
    stats = {'total_orders': 0, 'total_revenue': 0, 'new_orders': 0, 'total_products': 0}
    
    if is_logged_in:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders ORDER BY id DESC')
            orders = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute('SELECT * FROM products ORDER BY id DESC')
            products = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute('SELECT COUNT(*) FROM orders')
            stats['total_orders'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COALESCE(SUM(product_price), 0) FROM orders WHERE status != "Cancelled"')
            stats['total_revenue'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "New Order"')
            stats['new_orders'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM products')
            stats['total_products'] = cursor.fetchone()[0]

    return render_template('admin.html', is_logged_in=is_logged_in, orders=orders, products=products, stats=stats, settings=settings)

# Login with Brute-Force Defense (Auto lockout after 5 fails)
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    ip = get_client_ip()
    current_t = time.time()
    
    tracker = FAILED_LOGINS[ip]
    if tracker['locked_until'] > current_t:
        remaining_secs = int(tracker['locked_until'] - current_t)
        return jsonify({
            'success': False,
            'message': f'सुरक्षा चेतावनी: बहुत अधिक गलत प्रयास! कृपया {remaining_secs // 60 + 1} मिनट बाद पुनः प्रयास करें।'
        }), 429

    data = request.json or request.form
    pin = str(data.get('pin', '')).strip()
    
    settings = get_settings_dict()
    stored_hash = settings.get('admin_pin', '')
    
    is_valid = False
    if stored_hash.startswith('scrypt:') or stored_hash.startswith('pbkdf2:'):
        is_valid = check_password_hash(stored_hash, pin)
    else:
        # Fallback if plaintext and immediately upgrade
        is_valid = (stored_hash == pin)
        if is_valid:
            with get_db() as conn:
                conn.cursor().execute('UPDATE settings SET value = ? WHERE key = "admin_pin"', (generate_password_hash(pin),))
                conn.commit()

    if is_valid:
        FAILED_LOGINS.pop(ip, None)
        session.clear()
        session['is_admin'] = True
        return jsonify({'success': True})
    else:
        tracker['count'] += 1
        if tracker['count'] >= 5:
            tracker['locked_until'] = current_t + 900  # 15 minutes lockout
            return jsonify({
                'success': False,
                'message': 'सुरक्षा चेतावनी: 5 गलत प्रयास दर्ज हुए हैं। आपका IP 15 मिनट के लिए लॉक कर दिया गया है!'
            }), 429
            
        remaining_attempts = 5 - tracker['count']
        return jsonify({
            'success': False,
            'message': f'गलत एडमिन पिन! केवल {remaining_attempts} प्रयास शेष हैं।'
        }), 401

@app.route('/api/admin/logout', methods=['POST', 'GET'])
def admin_logout():
    session.clear()
    return redirect(url_for('admin_page'))

@app.route('/api/admin/orders/<int:order_id>/status', methods=['POST'])
def update_order_status(order_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json or {}
    new_status = clean_str(data.get('status', 'New Order'), 30)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
        conn.commit()
        
    return jsonify({'success': True})

@app.route('/api/admin/orders/export')
def export_orders_csv():
    if not session.get('is_admin'):
        return redirect(url_for('admin_page'))
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders ORDER BY id DESC')
        rows = cursor.fetchall()

    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM for Microsoft Excel
    writer = csv.writer(output)
    writer.writerow([
        'Order ID', 'Date & Time', 'Customer Name', 'Phone', 'Address', 'City',
        'State', 'Pin Code', 'Product Name', 'Price (Rs)', 'Size', 'Qty',
        'Payment Method', 'Status', 'Order Note', 'Customer IP'
    ])

    for row in rows:
        writer.writerow([
            row['order_id'], row['created_at'], row['customer_name'], row['customer_phone'],
            row['customer_address'], row['customer_city'], row['customer_state'],
            row['customer_pincode'], row['product_title'], row['product_price'],
            row['selected_size'], row['quantity'], row['payment_method'], row['status'],
            row['order_note'] or '', row['ip_address'] or ''
        ])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment;filename=Swag_Bazaar_Customers_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"}
    )

@app.route('/api/admin/products', methods=['POST'])
def add_product():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or request.form
    title = clean_str(data.get('title'), 150)
    title_hi = clean_str(data.get('title_hi', ''), 150)
    category = clean_str(data.get('category'), 50)
    price = int(data.get('price', 0))
    original_price = int(data.get('original_price', price))
    discount = int(((original_price - price) / original_price * 100)) if original_price > price else 0
    image_url = clean_str(data.get('image_url'), 500)
    affiliate_url = clean_str(data.get('affiliate_url'), 500)
    badge = clean_str(data.get('badge', '🔥 Trending'), 50)
    description = clean_str(data.get('description', ''), 500)
    sizes = clean_str(data.get('sizes', 'Standard'), 100)
    platform_name = clean_str(data.get('platform_name', 'Affiliate / Resell'), 50)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO products (
                title, title_hi, category, price, original_price, discount,
                image_url, affiliate_url, badge, description, sizes, platform_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            title, title_hi, category, price, original_price, discount,
            image_url, affiliate_url, badge, description, sizes, platform_name
        ))
        conn.commit()

    return jsonify({'success': True, 'message': 'नया प्रोडक्ट जोड़ दिया गया!'})

@app.route('/api/admin/products/<int:prod_id>/delete', methods=['POST'])
def delete_product(prod_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = ?', (prod_id,))
        conn.commit()

    return jsonify({'success': True, 'message': 'प्रोडक्ट हटा दिया गया!'})

@app.route('/api/admin/settings', methods=['POST'])
def update_settings():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or request.form
    with get_db() as conn:
        cursor = conn.cursor()
        for key in ['whatsapp_number', 'store_name_hi', 'store_name_en', 'insta_handle', 'upi_id']:
            if key in data:
                cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, clean_str(data[key], 100)))
        
        # If user changed PIN, hash it with PBKDF2/scrypt!
        if 'admin_pin' in data and data['admin_pin'].strip():
            new_pin = str(data['admin_pin']).strip()
            if len(new_pin) >= 4:
                hashed_pin = generate_password_hash(new_pin)
                cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("admin_pin", ?)', (hashed_pin,))
                
        conn.commit()

    return jsonify({'success': True, 'message': 'सेटिंग्स सुरक्षित हो गईं!'})

# Initialization
init_db()

if __name__ == '__main__':
    # For local quick debug test only
    app.run(host='0.0.0.0', port=5000, debug=False)
