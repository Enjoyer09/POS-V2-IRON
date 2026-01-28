import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import random
import time
from sqlalchemy import text
import os
import bcrypt
import secrets
import datetime
import qrcode
from io import BytesIO
import zipfile
from PIL import Image, ImageDraw, ImageFont
import requests
from urllib.parse import urlparse, parse_qs 
import base64
import json
from collections import Counter

# ==========================================
# === EMALATKHANA POS - V5.1 (FINAL POLISH) ===
# ==========================================

VERSION = "v5.1 ENTERPRISE (Full)"
BRAND_NAME = "Emalatkhana Daily Coffee"

# --- INFRA ---
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
DOMAIN = "demo.ironwaves.store" 
APP_URL = f"https://{DOMAIN}"
DEFAULT_SENDER_EMAIL = "info@ironwaves.store" 

# --- CONFIG ---
st.set_page_config(page_title=BRAND_NAME, page_icon="☕", layout="wide", initial_sidebar_state="collapsed")

# --- INIT STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'language' not in st.session_state: st.session_state.language = 'az'
if 'cart_takeaway' not in st.session_state: st.session_state.cart_takeaway = []
if 'cart_table' not in st.session_state: st.session_state.cart_table = []
if 'current_customer_ta' not in st.session_state: st.session_state.current_customer_ta = None
if 'current_customer_tb' not in st.session_state: st.session_state.current_customer_tb = None
if 'last_sale' not in st.session_state: st.session_state.last_sale = None
if 'selected_table' not in st.session_state: st.session_state.selected_table = None
if 'selected_recipe_product' not in st.session_state: st.session_state.selected_recipe_product = None

# --- TRANSLATION DICTIONARY ---
T = {
    # Login & General
    "login_staff": {"az": "İŞÇİ GİRİŞİ", "en": "STAFF LOGIN"},
    "login_admin": {"az": "İDARƏETMƏ", "en": "MANAGEMENT"},
    "username": {"az": "İstifadəçi", "en": "Username"},
    "password": {"az": "Şifrə/PIN", "en": "Password/PIN"},
    "login_btn": {"az": "Daxil Ol", "en": "Log In"},
    "logout": {"az": "Çıxış", "en": "Logout"},
    "refresh": {"az": "Yenilə", "en": "Refresh"},
    
    # Customer Portal
    "cust_welcome": {"az": "🎉 Xoş gəlmisiniz!", "en": "🎉 Welcome!"},
    "cust_complete": {"az": "Qeydiyyatı tamamlayın", "en": "Complete Registration"},
    "dob": {"az": "Doğum Tarixi", "en": "Date of Birth"},
    "agree_title": {"az": "📜 İstifadəçi Razılaşması", "en": "📜 User Agreement"},
    "read_terms": {"az": "Qaydaları Oxumaq üçün Toxunun", "en": "Tap to Read Terms"},
    "agree_check": {"az": "Şərtləri qəbul edirəm", "en": "I accept the terms"},
    "submit": {"az": "Təsdiqlə", "en": "Submit"},
    "balance": {"az": "BALANS", "en": "BALANCE"},
    "feedback_title": {"az": "🌟 Fikriniz önəmlidir!", "en": "🌟 Your feedback matters!"},
    "rate_us": {"az": "Xidmətimizi qiymətləndirin:", "en": "Rate our service:"},
    "comment_ph": {"az": "Kofe necə idi?", "en": "How was the coffee?"},
    "send": {"az": "Göndər", "en": "Send"},
    "feedback_thanks": {"az": "Təşəkkürlər! Rəyiniz qəbul olundu. 💚", "en": "Thanks! Feedback received. 💚"},
    "feedback_done": {"az": "Rəyiniz üçün təşəkkürlər! 💚", "en": "Thanks for your feedback! 💚"},
    "terms_text": {
        "az": """**1. Ümumi Müddəalar**\nBu proqram "Emalatkhana" sistemi vasitəsilə idarə olunur.\n\n**2. Bonuslar**\nToplanılan ulduzlar nağd pula çevrilə bilməz. Endirimlər yalnız kofe məhsullarına şamil edilir.\n\n**3. Məxfilik**\nSizin məlumatlarınız (Email, Doğum tarixi) üçüncü tərəflə paylaşılmır.""",
        "en": """**1. General**\nThis program is managed by "Emalatkhana" system.\n\n**2. Bonuses**\nCollected stars cannot be exchanged for cash. Discounts apply only to coffee products.\n\n**3. Privacy**\nYour data (Email, DOB) is not shared with third parties."""
    },

    # POS Tabs
    "tab_takeaway": {"az": "🏃‍♂️ AL-APAR", "en": "🏃‍♂️ TAKEAWAY"},
    "tab_tables": {"az": "🍽️ MASALAR", "en": "🍽️ TABLES"},
    "tab_stock": {"az": "📦 Anbar", "en": "📦 Stock"},
    "tab_recipes": {"az": "📜 Resept", "en": "📜 Recipes"},
    "tab_analytics": {"az": "Analitika", "en": "Analytics"},
    "tab_crm": {"az": "👥 CRM", "en": "👥 CRM"},
    "tab_menu": {"az": "Menyu", "en": "Menu"},
    "tab_settings": {"az": "⚙️ Ayarlar", "en": "⚙️ Settings"},
    
    # Actions
    "pay_btn": {"az": "✅ ÖDƏNİŞ ET", "en": "✅ PAY NOW"},
    "send_kitchen": {"az": "🔥 MƏTBƏXƏ GÖNDƏR", "en": "🔥 SEND TO KITCHEN"},
    "print_check": {"az": "🖨️ Hesabı Gətir", "en": "🖨️ Print Check"},
    "total": {"az": "YEKUN", "en": "TOTAL"},
    "discount": {"az": "Endirim", "en": "Discount"},
    "service": {"az": "Servis", "en": "Service"},
    "customer": {"az": "Müştəri", "en": "Customer"},
    "scan": {"az": "Skan...", "en": "Scan..."},
    "find": {"az": "Axtar", "en": "Search"},
    "add": {"az": "Əlavə Et", "en": "Add"},
    "delete": {"az": "Sil", "en": "Delete"},
    "save": {"az": "Yadda Saxla", "en": "Save"},
    "error_pin": {"az": "Yanlış PIN!", "en": "Wrong PIN!"},
    "error_auth": {"az": "Səhv Məlumat!", "en": "Invalid Credentials!"},
}

def txt(key):
    return T.get(key, {}).get(st.session_state.language, key)

# --- CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Courier+Prime&display=swap');

    .stApp { font-family: 'Oswald', sans-serif !important; background-color: #F4F6F9; }
    header, #MainMenu, footer, [data-testid="stSidebar"] { display: none !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
    
    h1 { color: #2E7D32 !important; } 

    button[data-baseweb="tab"] {
        font-family: 'Oswald', sans-serif !important; font-size: 18px !important; font-weight: 700 !important;
        background-color: white !important; border: 2px solid #FFCCBC !important; border-radius: 12px !important;
        margin: 0 4px !important; color: #555 !important; flex-grow: 1;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #2E7D32, #1B5E20) !important; border-color: #2E7D32 !important; color: white !important;
        box-shadow: 0 4px 12px rgba(46, 125, 50, 0.4);
    }
    
    div[data-testid="stRadio"] label[aria-checked="true"] {
        background: #2E7D32; color: white; border-color: #2E7D32;
    }

    div.stButton > button { border-radius: 12px !important; height: 60px !important; font-weight: 700 !important; box-shadow: 0 4px 0 rgba(0,0,0,0.1) !important; transition: all 0.1s !important; }
    div.stButton > button:active { transform: translateY(3px) !important; box-shadow: none !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #FF6B35, #FF8C00) !important; color: white !important; }
    
    .small-btn button { height: 35px !important; min-height: 35px !important; font-size: 14px !important; padding: 0 !important; }

    div.stButton > button[kind="secondary"] { background: linear-gradient(135deg, #43A047, #2E7D32) !important; color: white !important; border: 2px solid #1B5E20 !important; height: 120px !important; font-size: 24px !important; white-space: pre-wrap !important; }
    div.stButton > button[kind="primary"].table-occ { background: linear-gradient(135deg, #E53935, #C62828) !important; color: white !important; border: 2px solid #B71C1C !important; height: 120px !important; font-size: 24px !important; white-space: pre-wrap !important; animation: pulse-red 2s infinite; }

    .paper-receipt { background-color: #fff; width: 100%; max-width: 350px; padding: 20px; margin: 0 auto; box-shadow: 0 0 15px rgba(0,0,0,0.1); font-family: 'Courier Prime', monospace; font-size: 13px; color: #000; border: 1px solid #ddd; }
    .receipt-cut-line { border-bottom: 2px dashed #000; margin: 15px 0; }
    
    .cust-card { background: white; border-radius: 20px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); text-align: center; margin-bottom: 20px; border: 1px solid #eee; }
    .coffee-grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-top: 20px; }
    .coffee-icon { width: 45px; opacity: 0.2; filter: grayscale(100%); transition: all 0.5s; }
    .coffee-icon.active { opacity: 1; filter: none; transform: scale(1.1); }
    
    .motivation-text { font-size: 18px; color: #555; font-style: italic; text-align: center; margin-bottom: 15px; }

    @media print {
        body * { visibility: hidden; }
        .paper-receipt, .paper-receipt * { visibility: visible; }
        .paper-receipt { position: fixed; left: 0; top: 0; width: 100%; margin: 0; padding: 0; border: none; box-shadow: none; }
        div[data-testid="stDialog"], div[role="dialog"] { box-shadow: none !important; background: none !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- DB CONNECTION ---
try:
    db_url = os.environ.get("STREAMLIT_CONNECTIONS_NEON_URL") or os.environ.get("DATABASE_URL")
    if not db_url: st.error("DB URL Not Found"); st.stop()
    if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    conn = st.connection("neon", type="sql", url=db_url, pool_pre_ping=True)
except Exception as e: st.error(f"DB Error: {e}"); st.stop()

# --- SCHEMA ---
@st.cache_resource
def ensure_schema():
    with conn.session as s:
        s.execute(text("CREATE TABLE IF NOT EXISTS tables (id SERIAL PRIMARY KEY, label TEXT, is_occupied BOOLEAN DEFAULT FALSE, items TEXT, total DECIMAL(10,2) DEFAULT 0, opened_at TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS menu (id SERIAL PRIMARY KEY, item_name TEXT, price DECIMAL(10,2), category TEXT, is_active BOOLEAN DEFAULT FALSE, is_coffee BOOLEAN DEFAULT FALSE);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, items TEXT, total DECIMAL(10,2), payment_method TEXT, cashier TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, last_seen TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS active_sessions (token TEXT PRIMARY KEY, username TEXT, role TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS ingredients (id SERIAL PRIMARY KEY, name TEXT UNIQUE, stock_qty DECIMAL(10,2) DEFAULT 0, unit TEXT, category TEXT, min_limit DECIMAL(10,2) DEFAULT 10);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS recipes (id SERIAL PRIMARY KEY, menu_item_name TEXT, ingredient_name TEXT, quantity_required DECIMAL(10,2));"))
        s.execute(text("CREATE TABLE IF NOT EXISTS customers (card_id TEXT PRIMARY KEY, stars INTEGER DEFAULT 0, type TEXT, email TEXT, birth_date TEXT, is_active BOOLEAN DEFAULT FALSE, last_visit TIMESTAMP, secret_token TEXT, gender TEXT);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS customer_coupons (id SERIAL PRIMARY KEY, card_id TEXT, coupon_type TEXT, is_used BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, card_id TEXT, message TEXT, is_read BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS system_logs (id SERIAL PRIMARY KEY, username TEXT, action TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS expenses (id SERIAL PRIMARY KEY, title TEXT, amount DECIMAL(10,2), category TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS coupon_templates (id SERIAL PRIMARY KEY, name TEXT, percent INTEGER, days_valid INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS void_logs (id SERIAL PRIMARY KEY, item_name TEXT, qty INTEGER, reason TEXT, deleted_by TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS feedbacks (id SERIAL PRIMARY KEY, card_id TEXT, rating INTEGER, comment TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS failed_logins (username TEXT PRIMARY KEY, attempt_count INTEGER DEFAULT 0, last_attempt TIMESTAMP, blocked_until TIMESTAMP);"))

        try: s.execute(text("ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_card_id TEXT;"))
        except: pass
        try: s.execute(text("ALTER TABLE tables ADD COLUMN IF NOT EXISTS active_customer_id TEXT;"))
        except: pass
        try: s.execute(text("ALTER TABLE menu ADD COLUMN IF NOT EXISTS printer_target TEXT DEFAULT 'kitchen';")) 
        except: pass
        try: s.execute(text("ALTER TABLE menu ADD COLUMN IF NOT EXISTS price_half DECIMAL(10,2);"))
        except: pass
        try: s.execute(text("ALTER TABLE recipes ADD COLUMN IF NOT EXISTS ingredient_name TEXT;"))
        except: pass
        try: s.execute(text("ALTER TABLE recipes ADD COLUMN IF NOT EXISTS menu_item_name TEXT;"))
        except: pass
        try: s.execute(text("ALTER TABLE recipes ADD COLUMN IF NOT EXISTS quantity_required DECIMAL(10,2);"))
        except: pass
        try: s.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS last_feedback_star_count INTEGER DEFAULT 0;"))
        except: pass
        try: s.execute(text("ALTER TABLE menu ADD COLUMN IF NOT EXISTS item_name_en TEXT;"))
        except: pass
        
        res = s.execute(text("SELECT count(*) FROM tables")).fetchone()
        if res[0] == 0:
            for i in range(1, 7): s.execute(text("INSERT INTO tables (label, is_occupied) VALUES (:l, FALSE)"), {"l": f"MASA {i}"})
        s.commit()
    
    with conn.session as s:
        try:
            p_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
            s.execute(text("""
                INSERT INTO users (username, password, role) VALUES ('admin', :p, 'admin')
                ON CONFLICT (username) DO UPDATE SET password = :p
            """), {"p": p_hash})
            s.commit()
        except: s.rollback()
    return True

ensure_schema()

# --- HELPERS ---
def get_baku_now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=4))).replace(tzinfo=None)
def run_query(q, p=None): 
    if p:
        for k, v in p.items():
            if hasattr(v, 'item'): p[k] = int(v.item())
    return conn.query(q, params=p, ttl=0)
def run_action(q, p=None): 
    if p:
        new_p = {}
        for k, v in p.items():
            if hasattr(v, 'item'): new_p[k] = int(v.item()) 
            elif isinstance(v, (int, float)): new_p[k] = v 
            else: new_p[k] = v
        p = new_p
    with conn.session as s: s.execute(text(q), p); s.commit()
    return True
def hash_password(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def verify_password(p, h): 
    try: return bcrypt.checkpw(p.encode(), h.encode()) if h.startswith('$2b$') else p == h
    except: return False
def log_system(user, action):
    try: run_action("INSERT INTO system_logs (username, action, created_at) VALUES (:u, :a, :t)", {"u":user, "a":action, "t":get_baku_now()})
    except: pass
def get_setting(key, default=""):
    try:
        r = run_query("SELECT value FROM settings WHERE key=:k", {"k":key})
        return r.iloc[0]['value'] if not r.empty else default
    except: return default
def set_setting(key, value):
    run_action("INSERT INTO settings (key, value) VALUES (:k, :v) ON CONFLICT (key) DO UPDATE SET value=:v", {"k":key, "v":value})
def image_to_base64(image_file): return base64.b64encode(image_file.getvalue()).decode()
@st.cache_data
def generate_custom_qr(data, center_text):
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(data); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGBA')
    datas = img.getdata(); newData = []
    for item in datas:
        if item[0] > 200: newData.append((255, 255, 255, 0)) 
        else: newData.append((0, 100, 0, 255)) 
    img.putdata(newData)
    buf = BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()
def send_email(to_email, subject, body):
    if not RESEND_API_KEY: return "API_KEY_MISSING"
    url = "https://api.resend.com/emails"
    headers = {"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"}
    payload = {"from": f"Emalatxana <{DEFAULT_SENDER_EMAIL}>", "to": [to_email], "subject": subject, "html": body}
    try: 
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        if r.status_code == 200: return "OK"
        else: return f"API Error {r.status_code}"
    except: return "Connection Error"
def format_qty(val):
    if val % 1 == 0: return int(val)
    return val
def clean_df_for_excel(df):
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)
    return df

# --- LOGIN SECURITY HELPERS ---
def check_login_block(username):
    try:
        row = run_query("SELECT attempt_count, blocked_until FROM failed_logins WHERE username=:u", {"u":username})
        if not row.empty:
            data = row.iloc[0]
            if data['blocked_until'] and data['blocked_until'] > get_baku_now():
                delta = data['blocked_until'] - get_baku_now()
                return True, int(delta.total_seconds() // 60) + 1
    except: pass
    return False, 0

def register_failed_login(username):
    now = get_baku_now()
    try:
        row = run_query("SELECT attempt_count FROM failed_logins WHERE username=:u", {"u":username})
        if row.empty:
            run_action("INSERT INTO failed_logins (username, attempt_count, last_attempt) VALUES (:u, 1, :t)", {"u":username, "t":now})
        else:
            new_count = row.iloc[0]['attempt_count'] + 1
            blocked_until = None
            if new_count >= 5: 
                blocked_until = now + datetime.timedelta(minutes=5)
            run_action("UPDATE failed_logins SET attempt_count=:c, last_attempt=:t, blocked_until=:b WHERE username=:u", 
                       {"c":new_count, "t":now, "b":blocked_until, "u":username})
    except: pass

def clear_failed_login(username):
    try: run_action("DELETE FROM failed_logins WHERE username=:u", {"u":username})
    except: pass

# --- SMART CALCULATION ENGINE ---
def calculate_smart_total(cart, customer=None, is_table=False):
    total = 0.0; discounted_total = 0.0; coffee_discount_rate = 0.0
    current_stars = 0
    if customer:
        current_stars = customer.get('stars', 0)
        if customer.get('type') == 'thermos': coffee_discount_rate = 0.20
        try:
            coupons = run_query("SELECT coupon_type FROM customer_coupons WHERE card_id=:id AND is_used=FALSE AND (expires_at IS NULL OR expires_at > NOW())", {"id": customer['card_id']})
            for _, c in coupons.iterrows():
                parts = c['coupon_type'].split('_')
                for p in parts:
                    if p.isdigit():
                        rate = int(p) / 100.0
                        if rate > coffee_discount_rate: coffee_discount_rate = rate 
        except: pass

    cart_coffee_count = sum([item['qty'] for item in cart if item.get('is_coffee')])
    total_star_pool = current_stars + cart_coffee_count
    potential_free = int(total_star_pool // 10)
    free_coffees_to_apply = min(potential_free, cart_coffee_count)
    
    for item in cart:
        total += item['qty'] * item['price']
    
    discounted_total = total
    coffee_sum = sum([item['qty'] * item['price'] for item in cart if item.get('is_coffee')])
    discount_amount = coffee_sum * coffee_discount_rate
    discounted_total -= discount_amount
    
    service_charge = 0.0
    if is_table:
        service_charge = discounted_total * 0.07
        discounted_total += service_charge
            
    return total, discounted_total, coffee_discount_rate, free_coffees_to_apply, total_star_pool, service_charge

# --- RENDERERS ---
def generate_receipt_html(sale_data):
    r_store = get_setting("receipt_store_name", BRAND_NAME)
    r_addr = get_setting("receipt_address", "Bakı ş., Mərkəz")
    r_phone = get_setting("receipt_phone", "+994 50 000 00 00")
    r_footer = get_setting("receipt_footer", "Bizi seçdiyiniz üçün təşəkkürlər!")
    r_logo_b64 = get_setting("receipt_logo_base64", "")
    logo_html = f'<div style="text-align:center;"><img src="data:image/png;base64,{r_logo_b64}" style="max-width:80px;"></div><br>' if r_logo_b64 else ''
    items_html = "<table style='width:100%; border-collapse: collapse; font-size:13px;'>"
    if isinstance(sale_data['items'], str):
        clean_items_str = sale_data['items']
        if clean_items_str.startswith("["): parts = clean_items_str.split("] ", 1); clean_items_str = parts[1] if len(parts)>1 else clean_items_str
        for item in clean_items_str.split(', '):
            if " x" in item: parts = item.rsplit(" x", 1); name = parts[0]; qty = parts[1]
            else: name = item; qty = "1"
            items_html += f"<tr><td style='text-align:left;'>{name}</td><td style='text-align:right;'>x{qty}</td></tr>"
    items_html += "</table>"
    
    financial_html = ""
    subtotal = sale_data.get('subtotal', sale_data['total']); discount = sale_data.get('discount', 0); service = sale_data.get('service_charge', 0)
    financial_html += f"<div style='display:flex; justify-content:space-between; margin-top:5px;'><span>Ara Cəm:</span><span>{subtotal:.2f} ₼</span></div>"
    if discount > 0: financial_html += f"<div style='display:flex; justify-content:space-between; color:red; font-weight:bold;'><span>{txt('discount')}:</span><span>-{discount:.2f} ₼</span></div>"
    if service > 0: financial_html += f"<div style='display:flex; justify-content:space-between; color:blue;'><span>{txt('service')} (7%):</span><span>{service:.2f} ₼</span></div>"
    financial_html += f"<div style='display:flex; justify-content:space-between; font-weight:bold; font-size:18px; margin-top:5px; border-top:1px solid black; padding-top:5px;'><span>{txt('total')}:</span><span>{sale_data['total']:.2f} ₼</span></div>"
    return f"""<div class="paper-receipt">{logo_html}<div style="text-align:center; font-weight:bold; font-size:18px;">{r_store}</div><div style="text-align:center; font-size:12px;">{r_addr}</div><div style="text-align:center; font-size:12px;">📞 {r_phone}</div><div class="receipt-cut-line"></div><div style="font-size:12px;">TARİX: {sale_data['date']}<br>ÇEK №: {sale_data['id']}<br>KASSİR: {sale_data['cashier']}</div><div class="receipt-cut-line"></div>{items_html}<div class="receipt-cut-line"></div>{financial_html}<div class="receipt-cut-line"></div><div style="text-align:center; font-size:12px; margin-top:5px;">{r_footer}</div></div>"""

@st.dialog("Çek")
def show_receipt_dialog():
    if 'last_sale' in st.session_state and st.session_state.last_sale:
        sale = st.session_state.last_sale
        st.markdown(generate_receipt_html(sale), unsafe_allow_html=True)
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            components.html("""<script>function printPage() { window.parent.print(); }</script><button onclick="printPage()" style="width:100%; height:50px; background: linear-gradient(135deg, #2c3e50, #4ca1af); color:white; border:none; border-radius:10px; font-family:sans-serif; font-size:16px; font-weight:bold; cursor:pointer; box-shadow: 0 4px 0 rgba(0,0,0,0.1);">🖨️ PRINT</button>""", height=70)
        with c2:
            if sale.get('customer_email'):
                if st.button("📧 Email", type="primary", use_container_width=True):
                    res = send_email(sale['customer_email'], f"Receipt №{sale['id']}", generate_receipt_html(sale))
                    if res == "OK": st.toast("✅ Sent!", icon="📧")
                    else: st.toast(f"❌ {res}", icon="⚠️")
            else: st.button("📧 Email", disabled=True, use_container_width=True)

@st.dialog("Transfer")
def show_transfer_dialog(current_table_id):
    tables = run_query("SELECT id, label, is_occupied, active_customer_id FROM tables WHERE id != :id ORDER BY id", {"id":current_table_id})
    if not tables.empty:
        target = st.selectbox("Target", tables['label'].tolist())
        if st.button("OK"):
            if 'selected_table' in st.session_state and st.session_state.selected_table and st.session_state.selected_table['id'] == current_table_id:
                raw_total, final_total, _, _, _, _ = calculate_smart_total(st.session_state.cart_table, st.session_state.current_customer_tb, is_table=True)
                cust_id = st.session_state.current_customer_tb['card_id'] if st.session_state.current_customer_tb else None
                run_action("UPDATE tables SET is_occupied=TRUE, items=:i, total=:t, active_customer_id=:c WHERE id=:id", 
                           {"i":json.dumps(st.session_state.cart_table), "t":final_total, "c":cust_id, "id":current_table_id})
            
            target_id = int(tables[tables['label']==target].iloc[0]['id'])
            curr = run_query("SELECT items, total, active_customer_id FROM tables WHERE id=:id", {"id":int(current_table_id)}).iloc[0]
            targ = run_query("SELECT items, total, active_customer_id FROM tables WHERE id=:id", {"id":target_id}).iloc[0]
            c_items = json.loads(curr['items']) if curr['items'] else []
            t_items = json.loads(targ['items']) if targ['items'] else []
            new_items = t_items + c_items
            new_total = float(curr['total'] or 0) + float(targ['total'] or 0)
            final_cust_id = targ['active_customer_id'] if targ['active_customer_id'] else curr['active_customer_id']
            run_action("UPDATE tables SET is_occupied=TRUE, items=:i, total=:t, active_customer_id=:c WHERE id=:id", 
                       {"i":json.dumps(new_items), "t":new_total, "c":final_cust_id, "id":target_id})
            run_action("UPDATE tables SET is_occupied=FALSE, items=NULL, total=0, active_customer_id=NULL WHERE id=:id", {"id":int(current_table_id)})
            st.session_state.selected_table = None; st.rerun()

@st.dialog("Pre-Check")
def show_pre_check_dialog(raw_t, final_t, serv, items, label, date):
    html = generate_receipt_html({
        "id": "PRE-CHECK",
        "date": date,
        "cashier": st.session_state.user,
        "items": f"[{label}] " + ", ".join([f"{x['item_name']} x{x['qty']}" for x in items]),
        "subtotal": raw_t,
        "total": final_t,
        "discount": raw_t - final_t + serv,
        "service_charge": serv
    })
    st.markdown(html, unsafe_allow_html=True)
    components.html("""<script>function printPage() { window.parent.print(); }</script><button onclick="printPage()" style="width:100%; height:50px; background: linear-gradient(135deg, #2c3e50, #4ca1af); color:white; border:none; border-radius:10px; font-family:sans-serif; font-size:16px; font-weight:bold; cursor:pointer; box-shadow: 0 4px 0 rgba(0,0,0,0.1);">🖨️ PRINT</button>""", height=70)

@st.dialog("Pay")
def show_payment_dialog(table_id):
    st.markdown("### Payment")
    mode = st.radio("Method", ["Full", "Split"], horizontal=True)
    
    if mode == "Full":
        pm = st.radio("Type", ["Cash", "Card"], horizontal=True)
        if st.button("✅ OK", type="primary", use_container_width=True):
            raw_total, final_total, disc_rate, free_count, total_pool, serv_chg = calculate_smart_total(st.session_state.cart_table, st.session_state.current_customer_tb, is_table=True)
            istr = f"[{st.session_state.selected_table['label']}] " + ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart_table])
            cust_id = st.session_state.current_customer_tb['card_id'] if st.session_state.current_customer_tb else None
            cust_email = st.session_state.current_customer_tb.get('email') if st.session_state.current_customer_tb else None
            
            run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at, customer_card_id) VALUES (:i,:t,:p,:c,:time, :cid)", 
                       {"i":istr,"t":final_total,"p":pm,"c":st.session_state.user, "time":get_baku_now(), "cid":cust_id})
            
            with conn.session as s:
                for it in st.session_state.cart_table:
                    rs = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m"), {"m":it['item_name']}).fetchall()
                    for r in rs: s.execute(text("UPDATE ingredients SET stock_qty=stock_qty-:q WHERE name=:n"), {"q":float(r[1])*it['qty'], "n":r[0]})
                if st.session_state.current_customer_tb:
                    new_stars_balance = total_pool - (free_count * 10)
                    s.execute(text("UPDATE customers SET stars=:s WHERE card_id=:id"), {"s":new_stars_balance, "id":cust_id})
                s.commit()
            
            run_action("UPDATE tables SET is_occupied=FALSE, items=NULL, total=0, active_customer_id=NULL WHERE id=:id", {"id":table_id})
            st.session_state.last_sale = {"id": int(time.time()), "items": istr, "total": final_total, "subtotal": raw_total, "discount": raw_total - final_total, "date": get_baku_now().strftime("%Y-%m-%d %H:%M"), "cashier": st.session_state.user, "customer_email": cust_email, "service_charge": serv_chg}
            st.session_state.cart_table=[]; st.session_state.selected_table=None; st.rerun()

    else: 
        st.info("Select items to split.")
        split_data = []
        for i, item in enumerate(st.session_state.cart_table):
            split_data.append({"Item": item['item_name'], "Price": item['price'], "Total Qty": item['qty'], "Pay Qty": 0, "_idx": i})
        df = pd.DataFrame(split_data)
        edited_df = st.data_editor(df, column_config={"Item": st.column_config.TextColumn(disabled=True), "Price": st.column_config.NumberColumn(disabled=True), "Total Qty": st.column_config.NumberColumn(disabled=True), "Pay Qty": st.column_config.NumberColumn(min_value=0, max_value=100, step=1), "_idx": None}, hide_index=True, use_container_width=True)
        
        selected_cart = []
        remaining_cart = []
        
        for index, row in edited_df.iterrows():
            orig_idx = row['_idx']
            orig_item = st.session_state.cart_table[orig_idx]
            pay_qty = int(row['Pay Qty'])
            if pay_qty > 0:
                item_copy = orig_item.copy(); item_copy['qty'] = pay_qty
                selected_cart.append(item_copy)
            rem_qty = orig_item['qty'] - pay_qty
            if rem_qty > 0:
                item_rem = orig_item.copy(); item_rem['qty'] = rem_qty
                remaining_cart.append(item_rem)

        if selected_cart:
            raw_t, final_t, _, free_cnt, pool, serv = calculate_smart_total(selected_cart, st.session_state.current_customer_tb, is_table=True)
            st.divider()
            st.markdown(f"**To Pay:** {final_t:.2f} ₼")
            pm_split = st.radio("Pay Method", ["Cash", "Card"], horizontal=True, key="pm_split")
            
            if st.button(f"Pay ({final_t:.2f} ₼)"):
                istr = f"[{st.session_state.selected_table['label']} - Split] " + ", ".join([f"{x['item_name']} x{x['qty']}" for x in selected_cart])
                cust_id = st.session_state.current_customer_tb['card_id'] if st.session_state.current_customer_tb else None
                run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at, customer_card_id) VALUES (:i,:t,:p,:c,:time, :cid)", 
                           {"i":istr,"t":final_t,"p":pm_split,"c":st.session_state.user, "time":get_baku_now(), "cid":cust_id})
                
                with conn.session as s:
                    for it in selected_cart:
                        rs = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m"), {"m":it['item_name']}).fetchall()
                        for r in rs: s.execute(text("UPDATE ingredients SET stock_qty=stock_qty-:q WHERE name=:n"), {"q":float(r[1])*it['qty'], "n":r[0]})
                    if st.session_state.current_customer_tb:
                        old_stars = st.session_state.current_customer_tb.get('stars', 0)
                        paid_coffee_count = sum([x['qty'] for x in selected_cart if x.get('is_coffee')])
                        new_bal = (old_stars + paid_coffee_count) - (free_cnt * 10)
                        s.execute(text("UPDATE customers SET stars=:s WHERE card_id=:id"), {"s":new_bal, "id":cust_id})
                    s.commit()

                if not remaining_cart:
                    run_action("UPDATE tables SET is_occupied=FALSE, items=NULL, total=0, active_customer_id=NULL WHERE id=:id", {"id":table_id})
                    st.session_state.selected_table = None
                else:
                    _, rem_total, _, _, _, _ = calculate_smart_total(remaining_cart, st.session_state.current_customer_tb, is_table=True)
                    run_action("UPDATE tables SET items=:i, total=:t WHERE id=:id", {"i":json.dumps(remaining_cart), "t":rem_total, "id":table_id})
                    st.session_state.cart_table = remaining_cart
                
                st.session_state.last_sale = {"id": int(time.time()), "items": istr, "total": final_t, "subtotal": raw_t, "discount": raw_t - final_t, "date": get_baku_now().strftime("%Y-%m-%d %H:%M"), "cashier": st.session_state.user, "customer_email": None, "service_charge": serv}
                st.rerun()

@st.dialog("Auth")
def admin_auth_dialog(item_idx=None, sale_to_delete=None):
    st.warning("Admin/Manager Approval")
    reason = st.text_input("Reason")
    pin = st.text_input("PIN", type="password")
    if st.button("Confirm"):
        target_roles = ['admin'] if sale_to_delete else ['admin', 'manager']
        role_ph = ",".join([f"'{r}'" for r in target_roles])
        approvers = run_query(f"SELECT password, role FROM users WHERE role IN ({role_ph})")
        approved = False; approver_role = ""
        for _, row in approvers.iterrows():
            if verify_password(pin, row['password']):
                approved = True; approver_role = row['role']; break
        
        if approved:
            if sale_to_delete: 
                s_info = run_query("SELECT * FROM sales WHERE id=:id", {"id":int(sale_to_delete)}).iloc[0]
                run_action("DELETE FROM sales WHERE id=:id", {"id":int(sale_to_delete)})
                log_system(st.session_state.user, f"Deleted Sale #{sale_to_delete}. Reason: {reason}")
                st.success("Deleted!"); st.rerun()
            else: 
                item = st.session_state.cart_table[item_idx]
                run_action("INSERT INTO void_logs (item_name, qty, reason, deleted_by, created_at) VALUES (:n, :q, :r, :u, :t)", 
                           {"n":item['item_name'], "q":item['qty'], "r":reason, "u":f"{st.session_state.user} ({approver_role})", "t":get_baku_now()})
                st.session_state.cart_table.pop(item_idx)
                run_action("UPDATE tables SET items=:i WHERE id=:id", {"i":json.dumps(st.session_state.cart_table), "id":st.session_state.selected_table['id']})
                st.success("Voided!"); st.rerun()
        else: st.error("Invalid PIN")

def add_to_cart(cart_ref, item):
    try:
        r = run_query("SELECT printer_target, price_half FROM menu WHERE item_name=:n", {"n":item['item_name']})
        if not r.empty:
            item['printer_target'] = r.iloc[0]['printer_target']
            item['price_half'] = float(r.iloc[0]['price_half']) if r.iloc[0]['price_half'] else None
        else:
            item['printer_target'] = 'kitchen'
            item['price_half'] = None
    except: 
        item['printer_target'] = 'kitchen'
        item['price_half'] = None
    
    for ex in cart_ref:
        if ex['item_name'] == item['item_name'] and ex.get('status') == 'new' and ex.get('qty') % 1 == 0: 
            ex['qty'] += 1
            return
    cart_ref.append(item)

def toggle_portion(idx):
    item = st.session_state.cart_table[idx]
    if item['qty'] == 1.0:
        item['qty'] = 0.5
        if item.get('price_half'):
            item['price'] = item['price_half'] * 2 
    elif item['qty'] == 0.5:
        item['qty'] = 1.0
        r = run_query("SELECT price FROM menu WHERE item_name=:n", {"n":item['item_name']})
        if not r.empty: item['price'] = float(r.iloc[0]['price'])

def render_menu_grid(cart_ref, key_prefix):
    cats = run_query("SELECT DISTINCT category FROM menu WHERE is_active=TRUE")
    cat_list = ["Hamısı"] + sorted(cats['category'].tolist()) if not cats.empty else ["Hamısı"]
    sc = st.radio("Kataloq", cat_list, horizontal=True, label_visibility="collapsed", key=f"cat_{key_prefix}")
    
    # MULTI-LANG: SELECT CORRECT COLUMN
    col_name = "item_name_en" if st.session_state.language == 'en' else "item_name"
    
    sql = f"SELECT id, item_name, {col_name} as display_name, price, is_coffee FROM menu WHERE is_active=TRUE"
    p = {}
    if sc != "Hamısı": 
        sql += " AND category=:c"
        p["c"] = sc
    sql += " ORDER BY price ASC"
    
    prods = run_query(sql, p)

    if not prods.empty:
        # If English name is empty, fall back to AZ name
        prods['display_name'] = prods['display_name'].fillna(prods['item_name'])
        
        gr = {}
        for _, r in prods.iterrows():
            n = r['display_name']; pts = n.split()
            if len(pts)>1 and pts[-1] in ['S','M','L','XL','Single','Double']: base = " ".join(pts[:-1]); gr.setdefault(base, []).append(r)
            else: gr[n] = [r]
        cols = st.columns(4); i=0
        @st.dialog("Size")
        def show_v(bn, its):
            st.write(f"### {bn}")
            for it in its:
                if st.button(f"{it['display_name'].replace(bn,'').strip()}\n{it['price']} ₼", key=f"v_{it['id']}_{key_prefix}", use_container_width=True):
                    add_to_cart(cart_ref, {'item_name':it['item_name'], 'price':float(it['price']), 'qty':1, 'is_coffee':it['is_coffee'], 'status':'new'}); st.rerun()
        for bn, its in gr.items():
            with cols[i%4]:
                if len(its)>1:
                    if st.button(f"{bn}\n(Select)", key=f"g_{bn}_{key_prefix}", use_container_width=True): show_v(bn, its)
                else:
                    it = its[0]
                    if st.button(f"{it['display_name']}\n{it['price']} ₼", key=f"s_{it['id']}_{key_prefix}", use_container_width=True):
                        add_to_cart(cart_ref, {'item_name':it['item_name'], 'price':float(it['price']), 'qty':1, 'is_coffee':it['is_coffee'], 'status':'new'}); st.rerun()
            i+=1

def render_takeaway():
    c1, c2 = st.columns([1.5, 3])
    with c1:
        st.info(txt("tab_takeaway"))
        with st.form("sc_ta", clear_on_submit=True):
            ci, cb = st.columns([3,1]); qv = ci.text_input(txt("customer"), label_visibility="collapsed", placeholder=txt("scan")); 
            if cb.form_submit_button(txt("find")) or qv:
                try: 
                    cid = qv.strip().split("id=")[1].split("&")[0] if "id=" in qv else qv.strip()
                    r = run_query("SELECT * FROM customers WHERE card_id=:id", {"id":cid})
                    if not r.empty: st.session_state.current_customer_ta = r.iloc[0].to_dict(); st.toast("✅"); st.rerun()
                    else: st.error("Tapılmadı")
                except: pass
        if st.session_state.current_customer_ta:
            c = st.session_state.current_customer_ta; st.success(f"👤 {c['card_id']} | ⭐ {c['stars']}")
            if st.button("Ləğv Et", key="ta_cl"): st.session_state.current_customer_ta=None; st.rerun()
        
        raw_total, final_total, disc_rate, free_count, total_pool, sc = calculate_smart_total(st.session_state.cart_takeaway, st.session_state.current_customer_ta, is_table=False)
        
        if st.session_state.cart_takeaway:
            for i, it in enumerate(st.session_state.cart_takeaway):
                st.markdown(f"<div style='background:white;padding:10px;margin-bottom:5px;border-radius:8px;display:flex;justify-content:space-between;align-items:center;border:1px solid #ddd;'><div style='flex:2'><b>{it['item_name']}</b></div><div style='flex:1'>{it['price']}</div><div style='flex:1;color:#E65100'>x{it['qty']}</div><div style='flex:1;text-align:right'>{it['qty']*it['price']:.1f}</div></div>", unsafe_allow_html=True)
                b1,b2,b3=st.columns([1,1,4])
                with b1: 
                    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                    if st.button("➖", key=f"m_ta_{i}"): 
                        if it['qty']>1: it['qty']-=1 
                        else: st.session_state.cart_takeaway.pop(i)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with b2:
                    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                    if st.button("➕", key=f"p_ta_{i}"): it['qty']+=1; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        
        if raw_total != final_total:
            st.markdown(f"<h3 style='text-align:right; color:#777; text-decoration: line-through;'>{raw_total:.2f} ₼</h3>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:right; color:#E65100'>{final_total:.2f} ₼</h2>", unsafe_allow_html=True)
        
        if free_count > 0: st.success(f"🎁 {free_count} ədəd Kofe HƏDİYYƏ! (-{free_count * 10} ulduz)")
        if disc_rate > 0: st.caption(f"⚡ {int(disc_rate*100)}% Kofe Endirimi Tətbiq Edildi")

        pm = st.radio("Metod", ["Cash", "Card"], horizontal=True, key="pm_ta")
        if st.button(txt("pay_btn"), type="primary", use_container_width=True, key="pay_ta"):
            if not st.session_state.cart_takeaway: st.error("Boşdur!"); st.stop()
            try:
                istr = ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart_takeaway])
                cust_id = st.session_state.current_customer_ta['card_id'] if st.session_state.current_customer_ta else None
                cust_email = st.session_state.current_customer_ta.get('email') if st.session_state.current_customer_ta else None
                run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at, customer_card_id) VALUES (:i,:t,:p,:c,:time, :cid)", 
                           {"i":istr,"t":final_total,"p":pm,"c":st.session_state.user, "time":get_baku_now(), "cid":cust_id})
                with conn.session as s:
                    for it in st.session_state.cart_takeaway:
                        rs = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m"), {"m":it['item_name']}).fetchall()
                        for r in rs: s.execute(text("UPDATE ingredients SET stock_qty=stock_qty-:q WHERE name=:n"), {"q":float(r[1])*it['qty'], "n":r[0]})
                    if st.session_state.current_customer_ta:
                        new_stars_balance = total_pool - (free_count * 10)
                        s.execute(text("UPDATE customers SET stars=:s WHERE card_id=:id"), {"s":new_stars_balance, "id":cust_id})
                    s.commit()
                st.session_state.last_sale = {"id": int(time.time()), "items": istr, "total": final_total, "subtotal": raw_total, "discount": raw_total - final_total, "date": get_baku_now().strftime("%Y-%m-%d %H:%M"), "cashier": st.session_state.user, "customer_email": cust_email, "service_charge": 0}
                st.session_state.cart_takeaway=[]; st.rerun()
            except Exception as e: st.error(str(e))
    with c2: render_menu_grid(st.session_state.cart_takeaway, "ta")

def render_tables_main():
    if st.session_state.selected_table: render_table_order()
    else: render_table_grid()

def render_table_grid():
    if st.session_state.role in ['admin', 'manager']:
        with st.expander("🛠️ Masa İdarəetməsi"):
            c_add, c_del = st.columns(2)
            with c_add:
                new_l = st.text_input("Masa Adı", key="new_table_input")
                if st.button(txt("add"), key="add_table_btn"): 
                    run_action("INSERT INTO tables (label) VALUES (:l)", {"l":new_l})
                    log_system(st.session_state.user, f"Created Table: {new_l}")
                    st.rerun()
            with c_del:
                tabs = run_query("SELECT label FROM tables")
                d_l = st.selectbox("Silinəcək", tabs['label'].tolist() if not tabs.empty else [], key="del_table_select")
                if st.button(txt("delete"), key="del_table_btn"): 
                    run_action("DELETE FROM tables WHERE label=:l", {"l":d_l})
                    log_system(st.session_state.user, f"Deleted Table: {d_l}")
                    st.rerun()
    st.markdown(f"### {txt('tab_tables')}")
    tables = run_query("SELECT * FROM tables ORDER BY id")
    cols = st.columns(3)
    for idx, row in tables.iterrows():
        with cols[idx % 3]:
            # KOT Logic Color
            items = json.loads(row['items']) if row['items'] else []
            has_unsent = any(x.get('status') == 'new' for x in items)
            is_occ = row['is_occupied']
            label_extra = ""
            if is_occ:
                if has_unsent: label_extra = "\n🟡 Yığılır"
                else: label_extra = "\n🔴 Hazırlanır"
            
            label = f"{row['label']}\n{row['total']} ₼{label_extra}" if is_occ else f"{row['label']}\n(BOŞ)"
            kind = "primary" if is_occ else "secondary"
            if st.button(label, key=f"tbl_btn_{row['id']}", type=kind, use_container_width=True):
                st.session_state.selected_table = row.to_dict(); st.session_state.cart_table = items; st.rerun()

def render_table_order():
    tbl = st.session_state.selected_table
    c_back, c_trans = st.columns([3, 1])
    if c_back.button("⬅️ Geri", key="back_tbl", use_container_width=True): st.session_state.selected_table = None; st.session_state.cart_table = []; st.rerun()
    if c_trans.button("➡️ Köçür", use_container_width=True): show_transfer_dialog(tbl['id'])
    
    st.markdown(f"### 📝 {tbl['label']}")
    c1, c2 = st.columns([1.5, 3])
    with c1:
        st.info("Masa Sifarişi")
        db_cust_id = tbl.get('active_customer_id')
        if db_cust_id and not st.session_state.current_customer_tb:
             r = run_query("SELECT * FROM customers WHERE card_id=:id", {"id":db_cust_id})
             if not r.empty: st.session_state.current_customer_tb = r.iloc[0].to_dict()

        with st.form("sc_tb", clear_on_submit=True):
            ci, cb = st.columns([3,1]); qv = ci.text_input(txt("customer"), label_visibility="collapsed", placeholder=txt("scan")); 
            if cb.form_submit_button(txt("find")) or qv:
                try: 
                    cid = qv.strip().split("id=")[1].split("&")[0] if "id=" in qv else qv.strip()
                    r = run_query("SELECT * FROM customers WHERE card_id=:id", {"id":cid})
                    if not r.empty: st.session_state.current_customer_tb = r.iloc[0].to_dict(); st.toast("✅"); st.rerun()
                    else: st.error("Tapılmadı")
                except: pass
        if st.session_state.current_customer_tb:
            c = st.session_state.current_customer_tb; st.success(f"👤 {c['card_id']} | ⭐ {c['stars']}")
            if st.button("Ləğv Et", key="tb_cl"): st.session_state.current_customer_tb=None; st.rerun()
        
        raw_total, final_total, disc_rate, free_count, total_pool, serv_chg = calculate_smart_total(st.session_state.cart_table, st.session_state.current_customer_tb, is_table=True)

        if st.session_state.cart_table:
            for i, it in enumerate(st.session_state.cart_table):
                status = it.get('status', 'new')
                bg_col = "#e3f2fd" if status == 'sent' else "white"
                status_icon = "🔥" if status == 'sent' else "✏️"
                
                st.markdown(f"<div style='background:{bg_col};padding:10px;margin-bottom:5px;border-radius:8px;display:flex;justify-content:space-between;align-items:center;border:1px solid #ddd;'><div style='flex:2'><b>{it['item_name']}</b> <small>{status_icon}</small></div><div style='flex:1'>{it['price']}</div><div style='flex:1;color:#E65100'>x{it['qty']}</div><div style='flex:1;text-align:right'>{it['qty']*it['price']:.1f}</div></div>", unsafe_allow_html=True)
                b1,b2,b3,b4=st.columns([1,1,1,3])
                with b1:
                    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                    if st.button("½", key=f"half_{i}"): toggle_portion(i); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with b2:
                    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                    if st.button("➕", key=f"p_tb_{i}"): 
                        if it['qty'] == 0.5: it['qty'] = 1.0 
                        else: it['qty']+=1
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with b3:
                    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                    if st.button("➖", key=f"m_tb_{i}"): 
                        if status == 'sent': admin_auth_dialog(item_idx=i)
                        else:
                            if it['qty']>1 and it['qty']!=0.5: it['qty']-=1 
                            else: st.session_state.cart_table.pop(i)
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown(f"<h3 style='text-align:right; color:#777; text-decoration: line-through;'>{raw_total:.2f} ₼</h3>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:right; color:#E65100'>{final_total:.2f} ₼</h2>", unsafe_allow_html=True)
        if serv_chg > 0: st.caption(f"ℹ️ Servis Haqqı (7%): {serv_chg:.2f} ₼ daxildir")
        if free_count > 0: st.success(f"🎁 {free_count} ədəd Kofe HƏDİYYƏ! (-{free_count * 10} ulduz)")
        if disc_rate > 0: st.caption(f"⚡ {int(disc_rate*100)}% Kofe Endirimi Tətbiq Edildi")

        col_s, col_p = st.columns(2)
        if col_s.button(txt("send_kitchen"), key="save_tbl", use_container_width=True):
            kitchen_items = []
            bar_items = []
            new_items_found = False
            
            for x in st.session_state.cart_table:
                if x.get('status') == 'new':
                    new_items_found = True
                    target = x.get('printer_target', 'kitchen')
                    if target == 'kitchen': kitchen_items.append(f"{x['item_name']} x{x['qty']}")
                    else: bar_items.append(f"{x['item_name']} x{x['qty']}")
                    x['status'] = 'sent'
            
            if new_items_found:
                if bar_items: st.toast(f"🍺 BARA ÇIXDI: {', '.join(bar_items)}", icon="🖨️")
                if kitchen_items: st.toast(f"🍳 MƏTBƏXƏ ÇIXDI: {', '.join(kitchen_items)}", icon="🖨️")
                
                act_cust_id = st.session_state.current_customer_tb['card_id'] if st.session_state.current_customer_tb else None
                run_action("UPDATE tables SET is_occupied=TRUE, items=:i, total=:t, active_customer_id=:c WHERE id=:id", 
                           {"i":json.dumps(st.session_state.cart_table), "t":final_total, "c":act_cust_id, "id":tbl['id']})
                st.success("Göndərildi!"); time.sleep(1); st.rerun()
            else:
                st.warning("Yeni sifariş yoxdur!")

        if col_p.button(txt("pay_btn"), key="pay_tbl", type="primary", use_container_width=True):
            if not st.session_state.cart_table: st.error("Boşdur!"); st.stop()
            show_payment_dialog(tbl['id'])
        
        if st.button(txt("print_check"), use_container_width=True):
            show_pre_check_dialog(raw_total, final_total, serv_chg, st.session_state.cart_table, tbl['label'], get_baku_now().strftime("%Y-%m-%d %H:%M"))

    with c2: render_menu_grid(st.session_state.cart_table, "tb")

def render_analytics(is_admin=False, is_manager=False):
    tab_list = [txt("tab_analytics")]
    if is_admin or is_manager: tab_list.extend(["Xərclər", "Loglar", "Void Report"])
    tabs = st.tabs(tab_list)
    
    with tabs[0]:
        c_filt, c_sum = st.columns([2, 1])
        with c_filt:
            ft = st.selectbox("Filtr", ["Bu Gün", "Bu Ay", "Tarix Aralığı"], label_visibility="collapsed")
        
        base_sql = "SELECT id, created_at, items, total, payment_method, cashier, customer_card_id FROM sales"
        p = {}
        if not (is_admin or is_manager):
            base_sql += " WHERE cashier = :u"
            p['u'] = st.session_state.user
        base_sql += " ORDER BY created_at DESC"
        
        df = run_query(base_sql, p)
        
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at'])
            now = get_baku_now()
            
            if ft == "Bu Gün":
                df = df[df['created_at'].dt.date == now.date()]
            elif ft == "Bu Ay":
                df = df[(df['created_at'].dt.month == now.month) & (df['created_at'].dt.year == now.year)]
            elif ft == "Tarix Aralığı":
                c_d1, c_d2 = st.columns(2)
                d1 = c_d1.date_input("Başlanğıc")
                d2 = c_d2.date_input("Bitmə")
                if d1 and d2:
                    df = df[(df['created_at'].dt.date >= d1) & (df['created_at'].dt.date <= d2)]
            
            with c_sum:
                st.metric("Dövriyyə", f"{df['total'].sum():.2f} ₼")
            
            if is_admin:
                df_editor = df.copy()
                df_editor.insert(0, "Seç", False)
                edited_df = st.data_editor(df_editor, hide_index=True, use_container_width=True, disabled=["id", "items", "total", "cashier", "created_at"])
                to_del = edited_df[edited_df['Seç']]['id'].tolist()
                if to_del:
                    if st.button(f"🗑️ Seçilənləri Sil ({len(to_del)})", type="primary"):
                        admin_auth_dialog(sale_to_delete=to_del[0])
            else:
                st.dataframe(df, hide_index=True, use_container_width=True)
                
            if (is_admin or is_manager) and st.button("📩 Hesabatı Emailə Göndər"):
                body = f"<h1>Satış Hesabatı ({ft})</h1><h3>Cəm: {df['total'].sum():.2f} ₼</h3>"
                res = send_email(DEFAULT_SENDER_EMAIL, "Satış Hesabatı", body)
                if res == "OK": st.success("Göndərildi!")
                else: st.error(res)
        else:
            st.info("Məlumat tapılmadı")

    if (is_admin or is_manager) and len(tabs)>1:
        with tabs[1]:
            st.markdown("### 💰 Xərclər")
            expenses = run_query("SELECT * FROM expenses ORDER BY created_at DESC")
            expenses.insert(0, "Seç", False)
            edited = st.data_editor(expenses, hide_index=True, use_container_width=True)
            if is_admin:
                to_del = edited[edited['Seç']]['id'].tolist()
                if to_del and st.button(f"Seçilənləri Sil ({len(to_del)})"):
                    for d_id in to_del: run_action("DELETE FROM expenses WHERE id=:id", {"id":int(d_id)})
                    st.rerun()
            
            with st.expander("➕ Yeni Xərc"):
                with st.form("add_exp_new"):
                    t=st.text_input("Təyinat"); a=st.number_input("Məbləğ", min_value=0.0); c=st.selectbox("Kat", ["İcarə","Kommunal","Maaş","Təchizat"]); 
                    if st.form_submit_button("Əlavə Et"): 
                        run_action("INSERT INTO expenses (title,amount,category,created_at) VALUES (:t,:a,:c,:time)",{"t":t,"a":a,"c":c, "time":get_baku_now()}); st.rerun()
        with tabs[2]: 
            st.markdown("### 📜 Sistem Logları")
            u_list = ["Hamısı"] + run_query("SELECT username FROM users")['username'].tolist()
            sel_u = st.selectbox("İstifadəçi", u_list)
            sql_l = "SELECT * FROM system_logs"
            p_l = {}
            if sel_u != "Hamısı":
                sql_l += " WHERE username=:u"
                p_l['u'] = sel_u
            sql_l += " ORDER BY created_at DESC LIMIT 200"
            st.dataframe(run_query(sql_l, p_l), use_container_width=True)
            
        with tabs[3]: 
            st.markdown("### 🗑️ Ləğv Edilənlər (Void)"); 
            voids = run_query("SELECT * FROM void_logs ORDER BY created_at DESC")
            st.dataframe(voids, use_container_width=True)

# --- MAIN ---
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        # Language Selector
        lang = st.selectbox("Language / Dil", ["🇦🇿 AZ", "🇬🇧 EN"], index=0 if st.session_state.language=='az' else 1)
        st.session_state.language = 'az' if lang == "🇦🇿 AZ" else 'en'
        
        # 1. CUSTOMER PORTAL LOGIC (INSIDE LOGGED OUT STATE)
        qp = st.query_params
        if "id" in qp:
            card_id = qp["id"]
            st.markdown(f"<h2 style='text-align:center; color:#2E7D32; font-weight:bold;'>{BRAND_NAME}</h2>", unsafe_allow_html=True)
            
            user_df = run_query("SELECT * FROM customers WHERE card_id = :id", {"id": card_id})
            if not user_df.empty:
                user = user_df.iloc[0]
                st.markdown(f"<div class='motivation-text'>{txt('cust_welcome')}</div>", unsafe_allow_html=True)

                if not user['is_active']:
                    st.info(txt("cust_complete"))
                    with st.form("act_form"):
                        em = st.text_input("Email"); dob = st.date_input(txt("dob"), min_value=datetime.date(1950,1,1))
                        st.markdown(f"### {txt('agree_title')}")
                        with st.expander(txt("read_terms")):
                            st.markdown(txt("terms_text"))
                        agree = st.checkbox(txt("agree_check"))
                        if st.form_submit_button(txt("submit")):
                            if agree:
                                run_action("UPDATE customers SET email=:e, birth_date=:b, is_active=TRUE WHERE card_id=:i", {"e":em, "b":dob, "i":card_id})
                                st.success("OK!"); st.rerun()
                            else: st.error("!")
                    st.stop()
                
                st.markdown(f"<div class='cust-card'><h4 style='margin:0; color:#888;'>{txt('balance')}</h4><h1 style='color:#2E7D32; font-size: 48px; margin:0;'>{user['stars']} / 10</h1><p style='color:#555;'>ID: {card_id}</p></div>", unsafe_allow_html=True)
                
                # Feedback Logic
                last_fb = user.get('last_feedback_star_count', 0) or 0
                if user['stars'] > 0 and user['stars'] > last_fb:
                    st.divider()
                    st.markdown(f"#### {txt('feedback_title')}")
                    with st.form("fb_form"):
                        rating = st.radio(txt("rate_us"), ["⭐️", "⭐️⭐️", "⭐️⭐️⭐️", "⭐️⭐️⭐️⭐️", "⭐️⭐️⭐️⭐️⭐️"], horizontal=True, index=4)
                        comment = st.text_area("Rəy", placeholder=txt("comment_ph"))
                        if st.form_submit_button(txt("send")):
                            r_val = len(rating) // 2 
                            if rating == "⭐️": r_val = 1
                            elif rating == "⭐️⭐️": r_val = 2
                            elif rating == "⭐️⭐️⭐️": r_val = 3
                            elif rating == "⭐️⭐️⭐️⭐️": r_val = 4
                            elif rating == "⭐️⭐️⭐️⭐️⭐️": r_val = 5
                            run_action("INSERT INTO feedbacks (card_id, rating, comment, created_at) VALUES (:c, :r, :m, :t)", {"c":card_id, "r":r_val, "m":comment, "t":get_baku_now()})
                            run_action("UPDATE customers SET last_feedback_star_count = :s WHERE card_id = :c", {"s":user['stars'], "c":card_id})
                            st.success(txt("feedback_thanks")); time.sleep(2); st.rerun()
                elif user['stars'] > 0 and user['stars'] == last_fb:
                    st.markdown(f"<p style='text-align:center; color:#2E7D32;'><i>{txt('feedback_done')}</i></p>", unsafe_allow_html=True)

                st.divider()
                if st.button(txt("logout")): st.query_params.clear(); st.rerun()
                st.stop()

        # 2. LOGIN TABS
        st.markdown(f"<h1 style='text-align:center; color:#2E7D32;'>{BRAND_NAME}</h1><h5 style='text-align:center; color:#777;'>{VERSION}</h5>", unsafe_allow_html=True)
        tabs = st.tabs([txt("login_staff"), txt("login_admin")])
        with tabs[0]:
            with st.form("staff_login"):
                pin = st.text_input("PIN", type="password"); 
                if st.form_submit_button(txt("login_btn"), use_container_width=True):
                    is_blocked, mins = check_login_block(pin) 
                    if is_blocked: st.error(f"BLOCKED! {mins} min."); st.stop()
                    
                    udf = run_query("SELECT * FROM users WHERE role='staff'")
                    found = False
                    for _, row in udf.iterrows():
                        if verify_password(pin, row['password']):
                            clear_failed_login(row['username'])
                            st.session_state.logged_in=True; st.session_state.user=row['username']; st.session_state.role='staff'
                            tok=secrets.token_urlsafe(16); run_action("INSERT INTO active_sessions (token,username,role,created_at) VALUES (:t,:u,:r,:time)", {"t":tok,"u":row['username'],"r":'staff',"time":get_baku_now()})
                            log_system(row['username'], "Login (Staff)"); st.query_params["token"] = tok; st.rerun(); found=True; break
                    
                    if not found:
                        st.error(txt("error_pin"))
                        time.sleep(2)

        with tabs[1]:
            with st.form("admin_login"):
                u = st.text_input(txt("username")); p = st.text_input(txt("password"), type="password")
                if st.form_submit_button(txt("login_btn"), use_container_width=True):
                    is_blocked, mins = check_login_block(u)
                    if is_blocked: st.error(f"BLOCKED! {mins} min."); st.stop()

                    udf = run_query("SELECT * FROM users WHERE LOWER(username)=LOWER(:u) AND role IN ('admin', 'manager')", {"u":u})
                    if not udf.empty:
                        row = udf.iloc[0]
                        if verify_password(p, row['password']):
                            clear_failed_login(u)
                            st.session_state.logged_in=True; st.session_state.user=u; st.session_state.role=row['role']
                            tok=secrets.token_urlsafe(16); run_action("INSERT INTO active_sessions (token,username,role,created_at) VALUES (:t,:u,:r,:time)", {"t":tok,"u":u,"r":row['role'],"time":get_baku_now()})
                            log_system(u, f"Login ({row['role']})"); st.query_params["token"] = tok; st.rerun()
                        else:
                            register_failed_login(u)
                            st.error(txt("error_auth"))
                    else:
                        st.error(txt("error_auth")) 
                        time.sleep(1)
else:
    h1, h2, h3 = st.columns([4, 1, 1])
    with h1: st.markdown(f"**👤 {st.session_state.user}** | {st.session_state.role.upper()}")
    with h2: 
        if st.button(txt("refresh"), use_container_width=True): st.rerun()
    with h3: 
        if st.button(txt("logout"), type="primary", use_container_width=True):
            run_action("DELETE FROM active_sessions WHERE token=:t", {"t":st.query_params.get("token")})
            log_system(st.session_state.user, "Logout"); st.session_state.logged_in = False; st.rerun()
    st.divider()

    role = st.session_state.role
    
    if role == 'admin':
        # ADMIN: Full Access
        tabs = st.tabs([txt("tab_takeaway"), txt("tab_tables"), txt("tab_stock"), txt("tab_recipes"), txt("tab_analytics"), txt("tab_crm"), txt("tab_menu"), txt("tab_settings"), "Admin", "QR"])
        with tabs[0]: render_takeaway()
        with tabs[1]: render_tables_main()
        with tabs[2]: # Anbar
            st.subheader(txt("tab_stock"))
            cats = run_query("SELECT DISTINCT category FROM ingredients ORDER BY category")['category'].tolist()
            if not cats: cats = ["Ümumi"]
            all_tabs_list = ["Bütün"] + cats
            inv_tabs = st.tabs(all_tabs_list)
            
            @st.dialog("Anbar Əməliyyatı")
            def manage_stock(id, name, current_qty, unit):
                st.markdown(f"### {name}")
                c1, c2 = st.columns(2)
                with c1:
                    add_q = st.number_input(f"Artır ({unit})", min_value=0.0, key=f"add_{id}")
                    if st.button("➕ Mədaxil", key=f"btn_add_{id}"):
                        run_action("UPDATE ingredients SET stock_qty=stock_qty+:q WHERE id=:id", {"q":add_q, "id":id}); st.success("Oldu!"); st.rerun()
                with c2:
                    fix_q = st.number_input("Dəqiq Say", value=float(current_qty), min_value=0.0, key=f"fix_{id}")
                    if st.button("✏️ Düzəliş", key=f"btn_fix_{id}"):
                        run_action("UPDATE ingredients SET stock_qty=:q WHERE id=:id", {"q":fix_q, "id":id}); st.success("Oldu!"); st.rerun()
                st.divider()
                if st.button("🗑️ Malı Sil", key=f"del_{id}", type="primary"):
                    run_action("DELETE FROM ingredients WHERE id=:id", {"id":id}); st.rerun()

            def render_inv(cat=None):
                sql = "SELECT * FROM ingredients"
                p={}
                if cat and cat != "Bütün": sql += " WHERE category=:c"; p['c']=cat
                sql += " ORDER BY name"
                df = run_query(sql, p)
                if not df.empty:
                    cols = st.columns(4)
                    for idx, r in df.iterrows():
                        with cols[idx % 4]:
                            key_suffix = cat if cat else "all"
                            label = f"{r['name']}\n{format_qty(r['stock_qty'])} {r['unit']}"
                            if st.button(label, key=f"inv_{r['id']}_{key_suffix}", use_container_width=True):
                                manage_stock(r['id'], r['name'], r['stock_qty'], r['unit'])
                else: st.info("Boşdur")

            for i, t_name in enumerate(all_tabs_list):
                with inv_tabs[i]:
                    render_inv(t_name)
                    if i==0:
                        st.divider()
                        with st.expander("➕ Yeni Mal Yarat"):
                            with st.form("new_inv"):
                                n=st.text_input("Ad"); q=st.number_input("Say", min_value=0.0, key="ni_q"); u=st.selectbox("Vahid",["gr","ml","ədəd","litr","kq"]); c=st.text_input("Kateqoriya (Məs: Bar, Süd)")
                                if st.form_submit_button("Yarat"):
                                    run_action("INSERT INTO ingredients (name,stock_qty,unit,category) VALUES (:n,:q,:u,:c)", {"n":n,"q":q,"u":u,"c":c}); st.rerun()

        with tabs[3]: # Resept
            st.subheader(txt("tab_recipes"))
            rc1, rc2 = st.columns([1, 2])
            with rc1: 
                search_menu = st.text_input(txt("find"), key="rec_search")
                sql = "SELECT id, item_name FROM menu WHERE is_active=TRUE"
                if search_menu: sql += f" AND item_name ILIKE '%{search_menu}%'"
                sql += " ORDER BY item_name"
                menu_items = run_query(sql)
                if not menu_items.empty:
                    for _, r in menu_items.iterrows():
                        if st.button(r['item_name'], key=f"rm_{r['id']}", use_container_width=True):
                            st.session_state.selected_recipe_product = r['item_name']
                else: st.caption("Tapılmadı")
            with rc2: 
                if st.session_state.selected_recipe_product:
                    p_name = st.session_state.selected_recipe_product
                    p_price = run_query("SELECT price FROM menu WHERE item_name=:n", {"n":p_name}).iloc[0]['price']
                    with st.container(border=True):
                        st.markdown(f"### 🍹 {p_name}")
                        st.markdown(f"**Satış Qiyməti:** {p_price} ₼")
                        st.divider()
                        recs = run_query("""
                            SELECT r.id, r.ingredient_name, r.quantity_required, i.unit 
                            FROM recipes r 
                            JOIN ingredients i ON r.ingredient_name = i.name 
                            WHERE r.menu_item_name=:n
                        """, {"n":p_name})
                        if not recs.empty:
                            recs['Miqdar'] = recs['quantity_required'].astype(str) + " " + recs['unit']
                            recs.insert(0, "Seç", False)
                            edited_recs = st.data_editor(
                                recs, 
                                column_config={
                                    "Seç": st.column_config.CheckboxColumn(required=True),
                                    "id": None, "quantity_required": None, "unit": None,
                                    "ingredient_name": "İnqrediyent"
                                }, 
                                hide_index=True, use_container_width=True, key="rec_editor"
                            )
                            to_del = edited_recs[edited_recs['Seç']]['id'].tolist()
                            if to_del and st.button(f"Seçilənləri Sil ({len(to_del)})", type="primary"):
                                for d_id in to_del: run_action("DELETE FROM recipes WHERE id=:id", {"id":d_id})
                                st.rerun()
                        else: st.info("Resept boşdur.")
                        st.divider()
                        st.markdown("➕ **İnqrediyent Əlavə Et**")
                        all_ings = run_query("SELECT name, unit FROM ingredients ORDER BY name")
                        if not all_ings.empty:
                            c_sel, c_qty, c_btn = st.columns([2, 1, 1])
                            sel_ing = c_sel.selectbox("Xammal", all_ings['name'].tolist(), label_visibility="collapsed", key="new_r_ing")
                            sel_unit = all_ings[all_ings['name']==sel_ing].iloc[0]['unit']
                            sel_qty = c_qty.number_input(f"Miqdar ({sel_unit})", min_value=0.0, step=1.0, label_visibility="collapsed", key="new_r_qty")
                            if c_btn.button("Əlavə", type="primary", use_container_width=True):
                                run_action("INSERT INTO recipes (menu_item_name, ingredient_name, quantity_required) VALUES (:m,:i,:q)", {"m":p_name, "i":sel_ing, "q":sel_qty}); st.rerun()
                else: st.info("👈 Soldan məhsul seçin")

        with tabs[4]: render_analytics(is_admin=True) # ADMIN MODE
        with tabs[5]: # CRM
            st.subheader(txt("tab_crm")); c_cp, c_mail, c_fb = st.columns([1,1,1])
            crm_tabs = st.tabs(["Kupon Yarat", "Şablonlar", "Email", "💬 Rəylər"])
            
            with crm_tabs[0]:
                with st.form("custom_coupon"):
                    cc_name = st.text_input("Kupon Kodu (Məs: YAY2026)")
                    cc_perc = st.number_input("Endirim (%)", 1, 100, 10)
                    cc_days = st.number_input("Müddət (Gün)", 1, 365, 7)
                    if st.form_submit_button("Şablonu Yadda Saxla"):
                        run_action("INSERT INTO coupon_templates (name, percent, days_valid) VALUES (:n, :p, :d)", {"n":cc_name, "p":cc_perc, "d":cc_days})
                        st.success("Yadda saxlandı!")
            
            with crm_tabs[1]:
                templates = run_query("SELECT * FROM coupon_templates ORDER BY created_at DESC")
                if not templates.empty:
                    for _, t in templates.iterrows():
                        c_t1, c_t2 = st.columns([3, 1])
                        c_t1.write(f"🏷️ **{t['name']}** - {t['percent']}% ({t['days_valid']} gün)")
                        if c_t2.button("Payla", key=f"dist_{t['id']}"):
                            ctype = f"custom_{t['percent']}_{t['name']}"
                            for _, r in run_query("SELECT card_id FROM customers").iterrows(): 
                                run_action(f"INSERT INTO customer_coupons (card_id, coupon_type, expires_at) VALUES ('{r['card_id']}', '{ctype}', NOW() + INTERVAL '{t['days_valid']} days')")
                            st.success("Göndərildi!")
                else: st.info("Şablon yoxdur")

            with crm_tabs[2]:
                st.markdown("#### 📧 Email")
                all_customers = run_query("SELECT card_id, email, stars FROM customers")
                all_customers.insert(0, "Seç", False)
                edited_df = st.data_editor(all_customers, hide_index=True, use_container_width=True)
                selected_emails = edited_df[edited_df["Seç"] == True]['email'].tolist()
                with st.form("mail"):
                    sub = st.text_input("Mövzu"); msg = st.text_area("Mesaj"); 
                    if st.form_submit_button("Seçilənlərə Göndər"):
                        c = 0
                        for e in selected_emails: 
                            if e and send_email(e, sub, msg) == "OK": c+=1
                        st.success(f"{c} email getdi!")
            
            with crm_tabs[3]:
                st.markdown("### 💬 Müştəri Rəyləri")
                fbs = run_query("SELECT * FROM feedbacks ORDER BY created_at DESC")
                if not fbs.empty:
                    for _, fb in fbs.iterrows():
                        stars = "⭐️" * fb['rating']
                        st.markdown(f"**ID:** {fb['card_id']} | {stars}")
                        st.info(fb['comment'] or "(Rəy yazılmayıb)")
                        st.caption(f"Tarix: {fb['created_at']}")
                        st.divider()
                else: st.info("Hələ rəy yoxdur")

        with tabs[6]: # Menyu (V4.6)
            st.subheader(txt("tab_menu"))
            with st.expander("📥 Excel"):
                up = st.file_uploader("Fayl", type=['xlsx'])
                if up and st.button("Yüklə", key="xl_load"):
                    df = pd.read_excel(up); run_action("DELETE FROM menu")
                    for _, row in df.iterrows(): 
                        pt = row.get('printer_target', 'kitchen')
                        ph = row.get('price_half', None)
                        # Multi-lang support for Excel
                        name_en = row.get('item_name_en', None)
                        run_action("INSERT INTO menu (item_name, item_name_en, price, category, is_active, is_coffee, printer_target, price_half) VALUES (:n, :ne, :p, :c, TRUE, :ic, :pt, :ph)", 
                                   {"n":row['item_name'],"ne":name_en, "p":row['price'],"c":row['category'],"ic":row.get('is_coffee',False),"pt":pt,"ph":ph})
                    st.rerun()
            with st.form("nm"):
                c1, c2, c3, c4 = st.columns(4)
                with c1: n=st.text_input("Ad (AZ)"); 
                with c2: ne=st.text_input("Name (EN)"); 
                with c3: p=st.number_input("Qiymət", min_value=0.0, key="menu_p")
                with c4: c=st.text_input("Kat"); 
                ic=st.checkbox("Kofe?"); pt=st.selectbox("Printer", ["kitchen", "bar"])
                ph=st.number_input("Yarım Qiymət (Seçimli)", min_value=0.0, value=0.0)
                
                if st.form_submit_button(txt("add")): 
                    ph_val = ph if ph > 0 else None
                    ne_val = ne if ne else None
                    run_action("INSERT INTO menu (item_name, item_name_en, price, category, is_active, is_coffee, printer_target, price_half) VALUES (:n, :ne, :p, :c, TRUE, :ic, :pt, :ph)", 
                               {"n":n,"ne":ne_val,"p":p,"c":c,"ic":ic,"pt":pt,"ph":ph_val}); st.rerun()
            
            ml = run_query("SELECT * FROM menu")
            if not ml.empty:
                ml.insert(0, "Seç", False)
                edited_menu = st.data_editor(ml, column_config={"Seç": st.column_config.CheckboxColumn(required=True)}, hide_index=True, use_container_width=True)
                to_del_menu = edited_menu[edited_menu['Seç']]['item_name'].tolist()
                if to_del_menu and st.button(f"{txt('delete')} ({len(to_del_menu)})", type="primary", key="del_menu_bulk"):
                    for i_n in to_del_menu: run_action("DELETE FROM menu WHERE item_name=:n", {"n":i_n})
                    st.rerun()

        with tabs[7]: # Ayarlar (User Management Here)
            st.subheader(txt("tab_settings"))
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🧾 Çek Məlumatları**")
                r_name = st.text_input("Mağaza Adı", value=get_setting("receipt_store_name", BRAND_NAME))
                r_addr = st.text_input("Ünvan", value=get_setting("receipt_address", "Bakı"))
                r_phone = st.text_input("Telefon", value=get_setting("receipt_phone", "+994 55 000 00 00"))
                r_web = st.text_input("Vebsayt", value=get_setting("receipt_web", "www.ironwaves.store"))
                r_insta = st.text_input("Instagram", value=get_setting("receipt_insta", "@ironwaves"))
                r_email = st.text_input("Email", value=get_setting("receipt_email", "info@ironwaves.store"))
                r_foot = st.text_input("Footer", value=get_setting("receipt_footer", "Təşəkkürlər!"))
                lf = st.file_uploader("Logo"); 
                if lf and st.button("Logo Saxla", key="sv_lg"): set_setting("receipt_logo_base64", image_to_base64(lf)); st.success("OK")
                if st.button("Məlumatları Saxla", key="sv_txt"): 
                    set_setting("receipt_store_name", r_name); set_setting("receipt_address", r_addr)
                    set_setting("receipt_phone", r_phone); set_setting("receipt_footer", r_foot)
                    set_setting("receipt_web", r_web); set_setting("receipt_insta", r_insta); set_setting("receipt_email", r_email)
                    st.success("Yadda saxlanıldı!")
                
                st.divider()
                st.markdown("**🔧 Sistem Ayarları**")
                show_tbl = st.checkbox("İşçi Panelində 'Masalar' bölməsini göstər", value=(get_setting("staff_show_tables", "TRUE")=="TRUE"))
                if st.button(txt("save"), key="sv_sys"):
                    set_setting("staff_show_tables", "TRUE" if show_tbl else "FALSE")
                    st.success("Yadda saxlanıldı! (Yeniləyin)")

            with c2:
                st.markdown("**🔐 Şifrə Dəyişmə & İstifadəçilər**")
                all_users = run_query("SELECT username, role FROM users")
                
                # --- DELETE USER ---
                with st.expander("🗑️ İstifadəçi Sil (Təhlükəli)", expanded=False):
                    user_to_del = st.selectbox("Silinəcək İstifadəçi", all_users['username'].tolist(), key="u_del_sel")
                    if user_to_del != "admin": # Protect main admin
                        if st.button("SİL", type="primary", key="del_user_btn"):
                            run_action("DELETE FROM users WHERE username=:u", {"u":user_to_del})
                            log_system(st.session_state.user, f"Deleted User: {user_to_del}")
                            st.success("Silindi!"); st.rerun()
                    else: st.caption("Admin silinə bilməz.")
                
                target_user = st.selectbox("Şifrə Dəyiş", all_users['username'].tolist(), key="cp_user")
                new_pass = st.text_input("Yeni Şifrə / PIN", type="password", key="cp_pass")
                if st.button("Şifrəni Yenilə"):
                    run_action("UPDATE users SET password=:p WHERE username=:u", {"p":hash_password(new_pass), "u":target_user})
                    log_system(st.session_state.user, f"Changed password for {target_user}")
                    st.success("Yeniləndi!")
                
                st.divider()
                with st.form("nu"):
                    u=st.text_input("Ad"); p=st.text_input("PIN"); r=st.selectbox("Rol",["staff","manager", "admin"]) # Added Manager
                    if st.form_submit_button("Yarat"): 
                        run_action("INSERT INTO users (username,password,role) VALUES (:u,:p,:r)", {"u":u,"p":hash_password(p),"r":r})
                        log_system(st.session_state.user, f"Created User: {u} as {r}")
                        st.success("OK")
        
        with tabs[8]: # Admin Tools (Backup)
            st.subheader("🔧 Admin Tools")
            if st.button("📥 FULL BACKUP", key="bkp_btn"):
                log_system(st.session_state.user, "Requested Full Backup")
                out = BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    for t in ["customers", "sales", "menu", "users", "ingredients", "recipes", "system_logs", "tables", "expenses", "void_logs", "feedbacks", "failed_logins"]:
                        clean_df_for_excel(run_query(f"SELECT * FROM {t}")).to_excel(writer, sheet_name=t.capitalize())
                st.download_button("⬇️ Endir", out.getvalue(), "Backup.xlsx")
            st.divider()
            with st.form("restore_form"):
                rf = st.file_uploader("Backup (.xlsx)")
                ap = st.text_input("Admin Şifrə", type="password")
                if st.form_submit_button("Bərpa Et"):
                    adm = run_query("SELECT password FROM users WHERE role='admin' LIMIT 1")
                    if not adm.empty and verify_password(ap, adm.iloc[0]['password']):
                        if rf:
                            xls = pd.ExcelFile(rf)
                            try:
                                run_action("DELETE FROM menu"); run_action("DELETE FROM ingredients"); run_action("DELETE FROM recipes")
                                if "Menu" in xls.sheet_names:
                                    for _, row in pd.read_excel(xls, "Menu").iterrows():
                                        # Handle new lang column in excel restore
                                        ne = row.get('item_name_en', None)
                                        run_action("INSERT INTO menu (item_name, item_name_en, price, category, is_active, is_coffee) VALUES (:n,:ne,:p,:c,TRUE,:ic)", 
                                                   {"n":row['item_name'],"ne":ne,"p":row['price'],"c":row['category'],"ic":row.get('is_coffee',False)})
                                log_system(st.session_state.user, "Restored Database from Backup")
                                st.success("Bərpa olundu!")
                            except Exception as e: st.error(f"Xəta: {e}")
                    else: st.error("Şifrə səhvdir")

        with tabs[9]: # QR
            cnt = st.number_input("Say", value=1, min_value=1, key="qr_cnt"); k = st.selectbox("Növ", ["Standard", "Termos", "10%", "20%", "50%"])
            if st.button("Yarat", key="gen_qr"):
                zb = BytesIO()
                with zipfile.ZipFile(zb, "w") as zf:
                    images = []
                    for _ in range(cnt):
                        i = str(random.randint(10000000, 99999999)); tok = secrets.token_hex(8); ct = "thermos" if k=="Termos" else "standard"
                        run_action("INSERT INTO customers (card_id, stars, type, secret_token) VALUES (:i, 0, :t, :st)", {"i":i, "t":ct, "st":tok})
                        code = None
                        if "10%" in k: code="disc_10"
                        elif "20%" in k: code="disc_20"
                        elif "50%" in k: code="disc_50"
                        if code: run_action("INSERT INTO customer_coupons (card_id, coupon_type) VALUES (:i, :c)", {"i":i, "c":code})
                        
                        img_bytes = generate_custom_qr(f"{APP_URL}/?id={i}&t={tok}", i)
                        zf.writestr(f"QR_{i}.png", img_bytes)
                        images.append(img_bytes)
                
                if cnt <= 3:
                    cols = st.columns(cnt)
                    for idx, img in enumerate(images):
                        with cols[idx]: st.image(img, width=200)
                
                st.download_button("📥 Bütün QR-ları Endir (ZIP)", zb.getvalue(), "qrcodes.zip", "application/zip", type="primary")

    elif role == 'manager':
        # MANAGER VIEW (V4.7 - Limited)
        # Tabs: POS, Tables, Inventory, Recipes, Analytics (Filtered), CRM, Menu
        tabs = st.tabs([txt("tab_takeaway"), txt("tab_tables"), txt("tab_stock"), txt("tab_recipes"), txt("tab_analytics"), txt("tab_crm"), txt("tab_menu")])
        with tabs[0]: render_takeaway()
        with tabs[1]: render_tables_main()
        with tabs[2]: # Anbar (Manager Access)
            st.subheader(txt("tab_stock"))
            cats = run_query("SELECT DISTINCT category FROM ingredients ORDER BY category")['category'].tolist()
            if not cats: cats = ["Ümumi"]
            all_tabs_list = ["Bütün"] + cats
            inv_tabs = st.tabs(all_tabs_list)
            
            @st.dialog("Anbar Əməliyyatı")
            def manage_stock(id, name, current_qty, unit):
                st.markdown(f"### {name}")
                c1, c2 = st.columns(2)
                with c1:
                    add_q = st.number_input(f"Artır ({unit})", min_value=0.0, key=f"add_{id}")
                    if st.button("➕ Mədaxil", key=f"btn_add_{id}"):
                        run_action("UPDATE ingredients SET stock_qty=stock_qty+:q WHERE id=:id", {"q":add_q, "id":id}); 
                        log_system(st.session_state.user, f"Restock: {name} +{add_q}{unit}")
                        st.success("Oldu!"); st.rerun()
                with c2:
                    fix_q = st.number_input("Dəqiq Say", value=float(current_qty), min_value=0.0, key=f"fix_{id}")
                    if st.button("✏️ Düzəliş", key=f"btn_fix_{id}"):
                        run_action("UPDATE ingredients SET stock_qty=:q WHERE id=:id", {"q":fix_q, "id":id}); 
                        log_system(st.session_state.user, f"Stock Correction: {name} -> {fix_q}{unit}")
                        st.success("Oldu!"); st.rerun()
            def render_inv(cat=None):
                sql = "SELECT * FROM ingredients"
                p={}
                if cat and cat != "Bütün": sql += " WHERE category=:c"; p['c']=cat
                sql += " ORDER BY name"
                df = run_query(sql, p)
                if not df.empty:
                    cols = st.columns(4)
                    for idx, r in df.iterrows():
                        with cols[idx % 4]:
                            key_suffix = cat if cat else "all"
                            label = f"{r['name']}\n{format_qty(r['stock_qty'])} {r['unit']}"
                            if st.button(label, key=f"inv_{r['id']}_{key_suffix}", use_container_width=True):
                                manage_stock(r['id'], r['name'], r['stock_qty'], r['unit'])
                else: st.info("Boşdur")
            for i, t_name in enumerate(all_tabs_list):
                with inv_tabs[i]: render_inv(t_name)

        with tabs[3]: # Resept
            st.subheader(txt("tab_recipes"))
            rc1, rc2 = st.columns([1, 2])
            with rc1: 
                search_menu = st.text_input(txt("find"), key="rec_search")
                sql = "SELECT id, item_name FROM menu WHERE is_active=TRUE"
                if search_menu: sql += f" AND item_name ILIKE '%{search_menu}%'"
                sql += " ORDER BY item_name"
                menu_items = run_query(sql)
                if not menu_items.empty:
                    for _, r in menu_items.iterrows():
                        if st.button(r['item_name'], key=f"rm_{r['id']}", use_container_width=True):
                            st.session_state.selected_recipe_product = r['item_name']
                else: st.caption("Tapılmadı")
            with rc2: 
                if st.session_state.selected_recipe_product:
                    p_name = st.session_state.selected_recipe_product
                    p_price = run_query("SELECT price FROM menu WHERE item_name=:n", {"n":p_name}).iloc[0]['price']
                    with st.container(border=True):
                        st.markdown(f"### 🍹 {p_name}")
                        st.markdown(f"**Satış Qiyməti:** {p_price} ₼")
                        st.divider()
                        recs = run_query("""
                            SELECT r.id, r.ingredient_name, r.quantity_required, i.unit 
                            FROM recipes r 
                            JOIN ingredients i ON r.ingredient_name = i.name 
                            WHERE r.menu_item_name=:n
                        """, {"n":p_name})
                        if not recs.empty:
                            recs['Miqdar'] = recs['quantity_required'].astype(str) + " " + recs['unit']
                            st.dataframe(recs[['ingredient_name', 'Miqdar']], hide_index=True)
                        else: st.info("Resept boşdur.")

        with tabs[4]: render_analytics(is_admin=False, is_manager=True) # Manager Mode
        
        with tabs[5]: # CRM (Manager)
            st.subheader(txt("tab_crm"))
            fbs = run_query("SELECT * FROM feedbacks ORDER BY created_at DESC")
            if not fbs.empty:
                for _, fb in fbs.iterrows():
                    stars = "⭐️" * fb['rating']
                    st.markdown(f"**ID:** {fb['card_id']} | {stars}")
                    st.info(fb['comment'] or "(Rəy yazılmayıb)")
                    st.divider()
            else: st.info("Hələ rəy yoxdur")

        with tabs[6]: # Menyu (Manager Edit)
            st.subheader(txt("tab_menu"))
            with st.form("nm"):
                c1, c2, c3, c4 = st.columns(4)
                with c1: n=st.text_input("Ad (AZ)"); 
                with c2: ne=st.text_input("Name (EN)"); 
                with c3: p=st.number_input("Qiymət", min_value=0.0, key="menu_p")
                with c4: c=st.text_input("Kat"); 
                ic=st.checkbox("Kofe?"); pt=st.selectbox("Printer", ["kitchen", "bar"])
                ph=st.number_input("Yarım Qiymət (Seçimli)", min_value=0.0, value=0.0)
                if st.form_submit_button(txt("add")): 
                    ph_val = ph if ph > 0 else None
                    ne_val = ne if ne else None
                    run_action("INSERT INTO menu (item_name, item_name_en, price, category, is_active, is_coffee, printer_target, price_half) VALUES (:n, :ne, :p, :c, TRUE, :ic, :pt, :ph)", 
                               {"n":n,"ne":ne_val,"p":p,"c":c,"ic":ic,"pt":pt,"ph":ph_val})
                    log_system(st.session_state.user, f"Manager Added Item: {n}")
                    st.rerun()
            ml = run_query("SELECT * FROM menu")
            if not ml.empty:
                ml.insert(0, "Seç", False)
                edited_menu = st.data_editor(ml, column_config={"Seç": st.column_config.CheckboxColumn(required=True)}, hide_index=True, use_container_width=True)
                to_del_menu = edited_menu[edited_menu['Seç']]['item_name'].tolist()
                if to_del_menu and st.button(f"{txt('delete')} ({len(to_del_menu)})", type="primary", key="del_menu_bulk"):
                    for i_n in to_del_menu: 
                        run_action("DELETE FROM menu WHERE item_name=:n", {"n":i_n})
                        log_system(st.session_state.user, f"Manager Deleted Item: {i_n}")
                    st.rerun()

    elif role == 'staff':
        # DYNAMIC STAFF TABS (V4.2)
        show_tables = (get_setting("staff_show_tables", "TRUE") == "TRUE")
        if show_tables:
            staff_tabs = st.tabs([txt("tab_takeaway"), txt("tab_tables"), "Mənim Satışlarım"])
            with staff_tabs[0]: render_takeaway()
            with staff_tabs[1]: render_tables_main()
            with staff_tabs[2]: render_analytics(is_admin=False)
        else:
            staff_tabs = st.tabs([txt("tab_takeaway"), "Mənim Satışlarım"])
            with staff_tabs[0]: render_takeaway()
            with staff_tabs[1]: render_analytics(is_admin=False)

    st.markdown(f"<div class='footer'>Ironwaves POS {VERSION} | © 2026</div>", unsafe_allow_html=True)
