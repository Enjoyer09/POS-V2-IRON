import streamlit as st
import pandas as pd
import random
import time
from sqlalchemy import text
import os
import bcrypt
import secrets
import datetime
import math
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import SquareModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from io import BytesIO
import zipfile
import requests
import json
import base64
import streamlit.components.v1 as components
import re

# ==========================================
# === EMALATKHANA POS - V5.28 (DEMO EDITION) ===
# ==========================================

VERSION = "v5.28 DEMO (Stable + Notepad)"
BRAND_NAME = "Emalatkhana (DEMO REJİMİ)"

# --- CONFIG ---
st.set_page_config(page_title=BRAND_NAME, page_icon="🧪", layout="wide", initial_sidebar_state="collapsed")
ADMIN_DEFAULT_PASS = os.environ.get("ADMIN_PASS", "admin123")

# --- YENİLƏNMİŞ QAYDALAR ---
DEFAULT_TERMS = """
<div style="font-family: 'Arial', sans-serif; color: #333; line-height: 1.6; font-size: 14px;">
    <h4 style="color: #D32F2F; border-bottom: 2px solid #D32F2F; padding-bottom: 10px; margin-top: 0;">
        🧪 DEMO REJİMİ - QAYDALAR
    </h4>
    <div style="margin-bottom: 15px;">
        <strong style="color: #E65100;">1. Ümumi Müddəalar</strong>
        <p style="margin-top: 5px; text-align: justify;">
            Bu "Emalatkhana" sisteminin DEMO versiyasıdır. Burada edilən əməliyyatlar real deyil.
        </p>
    </div>
</div>
"""

CARTOON_QUOTES = ["Bu gün sənin günündür! 🚀", "Qəhrəman kimi parılda! ⭐", "Bir fincan kofe = Xoşbəxtlik! ☕", "Enerjini topla, dünyanı fəth et! 🌍"]
SUBJECTS = ["Admin", "Abbas (Manager)", "Nicat (Investor)", "Elvin (Investor)", "Təchizatçı", "Digər"]

# --- PRESET KATEQORIYALAR ---
PRESET_CATEGORIES = [
    "Kofe (Dənələr)", 
    "Süd Məhsulları", 
    "Bar Məhsulları (Su/Buz)", 
    "Siroplar", 
    "Soslar və Pastalar", 
    "Qablaşdırma (Stəkan/Qapaq)", 
    "Şirniyyat (Hazır)", 
    "İçkilər (Hazır)",
    "Meyvə-Tərəvəz",
    "Təsərrüfat/Təmizlik"
]

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
DOMAIN = "demo.ironwaves.store"
APP_URL = f"https://{DOMAIN}"
DEFAULT_SENDER_EMAIL = "info@ironwaves.store"

# --- STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'session_token' not in st.session_state: st.session_state.session_token = None
if 'cart_takeaway' not in st.session_state: st.session_state.cart_takeaway = []
if 'cart_table' not in st.session_state: st.session_state.cart_table = []
if 'current_customer_ta' not in st.session_state: st.session_state.current_customer_ta = None
if 'current_customer_tb' not in st.session_state: st.session_state.current_customer_tb = None
if 'selected_table' not in st.session_state: st.session_state.selected_table = None
if 'show_receipt_popup' not in st.session_state: st.session_state.show_receipt_popup = False
if 'last_receipt_data' not in st.session_state: st.session_state.last_receipt_data = None
if 'anbar_page' not in st.session_state: st.session_state.anbar_page = 0
if 'anbar_rows_per_page' not in st.session_state: st.session_state.anbar_rows_per_page = 20
if 'edit_item_id' not in st.session_state: st.session_state.edit_item_id = None
if 'restock_item_id' not in st.session_state: st.session_state.restock_item_id = None
if 'menu_edit_id' not in st.session_state: st.session_state.menu_edit_id = None
if 'z_report_active' not in st.session_state: st.session_state.z_report_active = False
if 'z_calculated' not in st.session_state: st.session_state.z_calculated = False 
if 'sale_to_delete' not in st.session_state: st.session_state.sale_to_delete = None

# --- CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Comfortaa:wght@400;700&display=swap');

    :root { --primary-color: #2E7D32; }
    .stApp { background-color: #F8F9FA !important; color: #333 !important; font-family: 'Arial', sans-serif !important; }
    
    div[data-testid="stStatusWidget"] { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    header { visibility: hidden; }
    footer { visibility: hidden; }

    /* DEMO COLORING */
    h1 { color: #D32F2F !important; }

    div.stButton > button { 
        border-radius: 12px !important; min-height: 80px !important; 
        font-weight: bold !important; font-size: 18px !important; 
        border: 1px solid #ccc !important; box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important; 
    }
    div.stButton > button:active { transform: scale(0.98); }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #FF6B35, #FF8C00) !important; color: white !important; border: none !important; }
    div.stButton > button[kind="secondary"] { background: linear-gradient(135deg, #43A047, #2E7D32) !important; color: white !important; }

    .cartoon-quote { font-family: 'Comfortaa', cursive; color: #E65100; font-size: 22px; font-weight: 700; text-align: center; margin-bottom: 20px; animation: float 3s infinite; }
    @keyframes float { 0% {transform: translateY(0px);} 50% {transform: translateY(-8px);} 100% {transform: translateY(0px);} }
    .msg-box { background: linear-gradient(45deg, #FF9800, #FFC107); padding: 15px; border-radius: 15px; color: white; font-weight: bold; text-align: center; margin-bottom: 20px; font-family: 'Comfortaa', cursive !important; animation: pulse 2s infinite; }
    @keyframes pulse { 0% {transform: scale(1);} 50% {transform: scale(1.02);} 100% {transform: scale(1);} }

    .stamp-container { display: flex; justify-content: center; margin-bottom: 20px; }
    .stamp-card { background: white; padding: 15px 30px; text-align: center; font-family: 'Courier Prime', monospace; font-weight: bold; transform: rotate(-3deg); border-radius: 12px; border: 4px solid #B71C1C; color: #B71C1C; box-shadow: 0 0 0 4px white, 0 0 0 7px #B71C1C; }

    .coffee-grid-container { display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; justify-items: center; margin-top: 20px; max-width: 400px; margin-left: auto; margin-right: auto; }
    .coffee-icon-img { width: 50px; height: 50px; transition: all 0.5s ease; }
    .cup-earned { filter: invert(24%) sepia(96%) saturate(1720%) hue-rotate(94deg) brightness(92%) contrast(102%); opacity: 1; transform: scale(1.1); }
    .cup-red-base { filter: invert(18%) sepia(90%) saturate(6329%) hue-rotate(356deg) brightness(96%) contrast(116%); }
    .cup-anim { animation: bounce 1s infinite; }
    .cup-empty { filter: grayscale(100%); opacity: 0.2; }
    @keyframes bounce { 0%, 100% {transform: translateY(0);} 50% {transform: translateY(-5px);} }

    div[data-testid="stRating"] { justify-content: center !important; transform: scale(1.5); }
    div[data-testid="stRating"] svg { fill: #FF0000 !important; color: #FF0000 !important; }
    @media print { body * { visibility: hidden; } #hidden-print-area, #hidden-print-area * { visibility: visible; } #hidden-print-area { position: fixed; left: 0; top: 0; width: 100%; } }
    </style>
""", unsafe_allow_html=True)

# --- DB ---
try:
    db_url = os.environ.get("STREAMLIT_CONNECTIONS_NEON_URL") or os.environ.get("DATABASE_URL")
    if not db_url: st.error("DB URL Not Found"); st.stop()
    if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    conn = st.connection("neon", type="sql", url=db_url, pool_pre_ping=True, pool_size=20, max_overflow=30)
except Exception as e: st.error(f"DB Error: {e}"); st.stop()

@st.cache_resource
def ensure_schema():
    with conn.session as s:
        s.execute(text("CREATE TABLE IF NOT EXISTS tables (id SERIAL PRIMARY KEY, label TEXT, is_occupied BOOLEAN DEFAULT FALSE, items TEXT, total DECIMAL(10,2) DEFAULT 0, opened_at TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS menu (id SERIAL PRIMARY KEY, item_name TEXT, price DECIMAL(10,2), category TEXT, is_active BOOLEAN DEFAULT FALSE, is_coffee BOOLEAN DEFAULT FALSE, printer_target TEXT DEFAULT 'kitchen', price_half DECIMAL(10,2));"))
        s.execute(text("CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, items TEXT, total DECIMAL(10,2), payment_method TEXT, cashier TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, customer_card_id TEXT);"))
        try: s.execute(text("ALTER TABLE sales ADD COLUMN IF NOT EXISTS original_total DECIMAL(10,2) DEFAULT 0")); s.commit()
        except: pass
        try: s.execute(text("ALTER TABLE sales ADD COLUMN IF NOT EXISTS discount_amount DECIMAL(10,2) DEFAULT 0")); s.commit()
        except: pass
        s.execute(text("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, last_seen TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS active_sessions (token TEXT PRIMARY KEY, username TEXT, role TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS ingredients (id SERIAL PRIMARY KEY, name TEXT UNIQUE, stock_qty DECIMAL(10,2) DEFAULT 0, unit TEXT, category TEXT, min_limit DECIMAL(10,2) DEFAULT 10, type TEXT DEFAULT 'ingredient', unit_cost DECIMAL(18,5) DEFAULT 0, approx_count INTEGER DEFAULT 0);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS finance (id SERIAL PRIMARY KEY, type TEXT, category TEXT, amount DECIMAL(10,2), source TEXT, description TEXT, created_by TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        try: s.execute(text("ALTER TABLE finance ADD COLUMN IF NOT EXISTS subject TEXT")); s.commit()
        except: pass
        s.execute(text("CREATE TABLE IF NOT EXISTS expenses (id SERIAL PRIMARY KEY, amount DECIMAL(10,2), reason TEXT, spender TEXT, source TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS recipes (id SERIAL PRIMARY KEY, menu_item_name TEXT, ingredient_name TEXT, quantity_required DECIMAL(10,2));"))
        s.execute(text("CREATE TABLE IF NOT EXISTS customers (card_id TEXT PRIMARY KEY, stars INTEGER DEFAULT 0, type TEXT, email TEXT, birth_date TEXT, is_active BOOLEAN DEFAULT FALSE, last_visit TIMESTAMP, secret_token TEXT, gender TEXT, staff_note TEXT);"))
        try: s.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS created_at TIMESTAMP")); s.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS activated_at TIMESTAMP"))
        except: pass
        try: s.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS staff_note TEXT"))
        except: pass
        s.execute(text("CREATE TABLE IF NOT EXISTS promo_codes (id SERIAL PRIMARY KEY, code TEXT UNIQUE, discount_percent INTEGER, valid_until DATE, assigned_user_id TEXT, is_used BOOLEAN DEFAULT FALSE);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS customer_coupons (id SERIAL PRIMARY KEY, card_id TEXT, coupon_type TEXT, is_used BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, card_id TEXT, message TEXT, is_read BOOLEAN DEFAULT FALSE, attached_coupon TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS system_logs (id SERIAL PRIMARY KEY, username TEXT, action TEXT, customer_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        try: s.execute(text("ALTER TABLE system_logs ADD COLUMN IF NOT EXISTS customer_id TEXT")); s.commit()
        except: pass
        s.execute(text("CREATE TABLE IF NOT EXISTS feedbacks (id SERIAL PRIMARY KEY, card_id TEXT, rating INTEGER, comment TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        # ADMIN NOTES TABLE
        s.execute(text("CREATE TABLE IF NOT EXISTS admin_notes (id SERIAL PRIMARY KEY, note TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS failed_logins (username TEXT PRIMARY KEY, attempt_count INTEGER DEFAULT 0, last_attempt TIMESTAMP, blocked_until TIMESTAMP);"))

        try:
            p_hash = bcrypt.hashpw(ADMIN_DEFAULT_PASS.encode(), bcrypt.gensalt()).decode()
            s.execute(text("INSERT INTO users (username, password, role) VALUES ('admin', :p, 'admin') ON CONFLICT (username) DO NOTHING"), {"p": p_hash})
            s.commit()
        except: s.rollback()
    return True
ensure_schema()

# --- HELPERS ---
def get_baku_now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=4))).replace(tzinfo=None)
def run_query(q, p=None): return conn.query(q, params=p if p else {}, ttl=0)
def run_action(q, p=None): 
    with conn.session as s: s.execute(text(q), p if p else {}); s.commit()
    return True
def hash_password(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def verify_password(p, h): 
    try: return bcrypt.checkpw(p.encode(), h.encode()) if h.startswith('$2b$') else p == h
    except: return False
def log_system(user, action, cid=None):
    try: run_action("INSERT INTO system_logs (username, action, customer_id, created_at) VALUES (:u, :a, :c, :t)", {"u":user, "a":action, "c":cid, "t":get_baku_now()})
    except: pass
def delete_sales_transaction(ids, user):
    try:
        with conn.session as s:
            for i in ids: s.execute(text("DELETE FROM sales WHERE id=:id"), {"id": i})
            s.execute(text("INSERT INTO system_logs (username, action, created_at) VALUES (:u, :a, :t)"), {"u": user, "a": f"Satış Silindi ({len(ids)} ədəd)", "t": get_baku_now()})
            s.commit()
    except Exception as e: st.error(f"Xəta: {e}")
def get_setting(key, default=""):
    try: return run_query("SELECT value FROM settings WHERE key=:k", {"k":key}).iloc[0]['value']
    except: return default
def set_setting(key, value): run_action("INSERT INTO settings (key, value) VALUES (:k, :v) ON CONFLICT (key) DO UPDATE SET value=:v", {"k":key, "v":value})
def image_to_base64(image_file): return base64.b64encode(image_file.getvalue()).decode()
def generate_styled_qr(data):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=1)
    qr.add_data(data); qr.make(fit=True)
    img = qr.make_image(image_factory=StyledPilImage, module_drawer=SquareModuleDrawer(), color_mask=SolidFillColorMask(front_color=(0, 128, 0, 255), back_color=(255, 255, 255, 0)))
    buf = BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()
def send_email(to_email, subject, body):
    if not RESEND_API_KEY: return "API_KEY_MISSING"
    try: requests.post("https://api.resend.com/emails", json={"from": f"{BRAND_NAME} <{DEFAULT_SENDER_EMAIL}>", "to": [to_email], "subject": subject, "html": body}, headers={"Authorization": f"Bearer {RESEND_API_KEY}"}); return "OK"
    except: return "Error"
def create_session(username, role):
    token = secrets.token_urlsafe(32)
    run_action("INSERT INTO active_sessions (token, username, role, created_at) VALUES (:t, :u, :r, :c)", {"t":token, "u":username, "r":role, "c":get_baku_now()})
    return token
def validate_session():
    if not st.session_state.session_token: return False
    res = run_query("SELECT * FROM active_sessions WHERE token=:t", {"t":st.session_state.session_token})
    return not res.empty
def clear_customer_data():
    st.session_state.current_customer_ta = None
def format_qty(val): return int(val) if val % 1 == 0 else val

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

def get_low_stock_map():
    low_stock_items = []
    try:
        q = "SELECT DISTINCT r.menu_item_name FROM recipes r JOIN ingredients i ON r.ingredient_name = i.name WHERE i.stock_qty <= i.min_limit"
        df = run_query(q)
        if not df.empty: low_stock_items = df['menu_item_name'].tolist()
    except: pass
    return low_stock_items

def calculate_smart_total(cart, customer=None, is_table=False):
    total = 0.0; discounted_total = 0.0; status_discount_rate = 0.0; thermos_discount_rate = 0.0; current_stars = 0
    if customer:
        current_stars = customer.get('stars', 0); ctype = customer.get('type', 'standard')
        if ctype == 'golden': status_discount_rate = 0.05
        elif ctype == 'platinum': status_discount_rate = 0.10
        elif ctype == 'elite': status_discount_rate = 0.20
        elif ctype == 'thermos': thermos_discount_rate = 0.20 
    cart_coffee_count = sum([item['qty'] for item in cart if item.get('is_coffee')])
    total_star_pool = current_stars + cart_coffee_count; potential_free = int(total_star_pool // 10); free_coffees_to_apply = min(potential_free, cart_coffee_count)
    final_items_total = 0.0
    for item in cart:
        line_total = item['qty'] * item['price']; total += line_total
        if item.get('is_coffee'):
            applicable_rate = max(status_discount_rate, thermos_discount_rate); discount_amt = line_total * applicable_rate; final_items_total += (line_total - discount_amt)
        else: final_items_total += line_total
    discounted_total = final_items_total
    if is_table: discounted_total += discounted_total * 0.07
    return total, discounted_total, max(status_discount_rate, thermos_discount_rate), free_coffees_to_apply, total_star_pool, 0, False

# ==========================================
# === RECEIPT GENERATOR (PURE HTML STRING) ===
# ==========================================
def get_receipt_html_string(cart, total):
    store = get_setting("receipt_store_name", BRAND_NAME)
    addr = get_setting("receipt_address", "Bakı, Azərbaycan")
    phone = get_setting("receipt_phone", "+994 50 000 00 00")
    foot = get_setting("receipt_footer", "TƏŞƏKKÜRLƏR!")
    logo = get_setting("receipt_logo_base64")
    time_str = get_baku_now().strftime('%d/%m/%Y %H:%M')
    
    img_tag = f'<div style="text-align:center;"><img src="data:image/png;base64,{logo}" class="rec-logo" style="width:80px;filter:grayscale(100%);"></div>' if logo else ""
    
    # SIMPLE HTML STRUCTURE FOR EMAIL & COMPONENT
    html = f"""
    <div style="font-family:'Courier New', monospace; color:black; background:white; padding:15px; border:1px solid #eee; width:300px; margin:0 auto;">
        {img_tag}
        <div style="text-align:center; font-weight:bold; font-size:16px; margin-bottom:5px; text-transform:uppercase;">SATIŞ ÇEKİ<br>{store}</div>
        <div style="text-align:center; font-size:12px; margin-bottom:10px;">{addr}<br>Tel: {phone}</div>
        <div style="border-bottom:1px dashed black; margin:10px 0;"></div>
        <div style="text-align:center; font-size:12px;">{time_str}</div>
        <div style="border-bottom:1px dashed black; margin:10px 0;"></div>
        
        <table style="width:100%; border-collapse:collapse; font-size:12px; text-align:left;">
            <tr>
                <th style="padding-bottom:5px; border-bottom:1px dashed black; width:15%;">SAY</th>
                <th style="padding-bottom:5px; border-bottom:1px dashed black; width:55%;">MƏHSUL</th>
                <th style="padding-bottom:5px; border-bottom:1px dashed black; width:30%; text-align:right;">MƏBLƏĞ</th>
            </tr>
    """
    for i in cart:
        html += f"""
            <tr>
                <td style="padding:5px 0;">{int(i['qty'])}</td>
                <td style="padding:5px 0;">{i['item_name']}</td>
                <td style="padding:5px 0; text-align:right;">{i['qty']*i['price']:.2f} ₼</td>
            </tr>
        """
    
    html += f"""
        </table>
        <div style="border-bottom:1px dashed black; margin:10px 0;"></div>
        <div style="display:flex; justify-content:space-between; font-weight:bold; font-size:16px;">
            <span>YEKUN</span>
            <span>{total:.2f} ₼</span>
        </div>
        <div style="border-bottom:1px dashed black; margin:10px 0;"></div>
        <div style="text-align:center; margin-top:20px; font-size:12px; font-weight:bold;">{foot}</div>
    </div>
    """
    return html

@st.dialog("Ödəniş & Çek")
def show_receipt_dialog(cart_data, total_amt, cust_email):
    # 1. RENDER RECEIPT VISUALLY (IFRAME SAFE)
    html_content = get_receipt_html_string(cart_data, total_amt)
    components.html(html_content, height=500, scrolling=True)
    
    # 2. INJECT HIDDEN DIV FOR PRINTING (Appears only on Print)
    # Using st.markdown to inject raw HTML into DOM
    st.markdown(f'<div id="hidden-print-area">{html_content}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        # JS PRINT BUTTON
        components.html(f"""
            <button onclick="window.print()" style="background-color:#2E7D32; color:white; padding:12px 24px; border:none; border-radius:8px; font-weight:bold; font-size:16px; cursor:pointer; width:100%; font-family:sans-serif;">
                🖨️ ÇAP ET
            </button>
        """, height=60)
        
    with c2:
        if cust_email:
            if st.button("📧 Email Göndər", use_container_width=True):
                res = send_email(cust_email, "Sizin Çekiniz", html_content)
                if res == "OK": st.success("Göndərildi!")
                else: st.error(f"Xəta: {res}")
        else: st.caption("⛔ Email yoxdur")
        
    if st.button("❌ Bağla", use_container_width=True):
        st.session_state.show_receipt_popup = False
        st.session_state.last_receipt_data = None
        st.rerun()

@st.dialog("🔐 Admin Təsdiqi")
def admin_confirm_dialog(action_name, callback, *args):
    st.warning(f"⚠️ {action_name}")
    with st.form("admin_conf_form"):
        pwd = st.text_input("Admin Şifrəsi", type="password")
        if st.form_submit_button("Təsdiqlə"):
            adm = run_query("SELECT password FROM users WHERE role='admin' LIMIT 1")
            if not adm.empty and verify_password(pwd, adm.iloc[0]['password']):
                callback(*args); st.success("İcra olundu!"); time.sleep(1); st.rerun()
            else: st.error("Yanlış Şifrə!")

@st.dialog("🗑️ Seçilən Satışları Sil")
def smart_bulk_delete_dialog(selected_sales):
    cnt = len(selected_sales); total_val = selected_sales['total'].sum()
    st.warning(f"Seçilən Satış Sayı: {cnt}"); st.error(f"Cəmi Məbləğ: {total_val:.2f} ₼")
    st.write("---"); st.write("❓ **NİYƏ SİLİRSİNİZ?**")
    reason = st.radio("Səbəb seçin:", ["🅰️ Səhv Vurulub / Test (Mallar Anbara Qayıtsın) 🔄", "🅱️ Zay Olub / Dağılıb (Mallar Qayıtmasın) 🗑️"])
    if st.button("🔴 TƏSDİQLƏ VƏ SİL"):
        try:
            restore_stock = "Səhv" in reason; ids_to_del = selected_sales['id'].tolist()
            with conn.session as s:
                if restore_stock:
                    for idx, row in selected_sales.iterrows():
                        if row['items']:
                            parts = str(row['items']).split(", ")
                            for p in parts:
                                match = re.match(r"(.+) x(\d+)", p)
                                if match:
                                    iname = match.group(1).strip(); iqty = int(match.group(2))
                                    recs = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m"), {"m":iname}).fetchall()
                                    for r in recs:
                                        qty_to_add = float(r[1]) * iqty
                                        s.execute(text("UPDATE ingredients SET stock_qty = stock_qty + :q WHERE name=:n"), {"q":qty_to_add, "n":r[0]})
                for i in ids_to_del: s.execute(text("DELETE FROM sales WHERE id=:id"), {"id":int(i)})
                s.commit()
            log_system(st.session_state.user, f"Toplu Silmə ({cnt} ədəd) - {'Stok Bərpa' if restore_stock else 'Stok Silindi'}")
            st.success("Uğurla Silindi!"); time.sleep(1.5); st.rerun()
        except Exception as e: st.error(f"Xəta: {e}")

# ==========================================
# === CUSTOMER VIEW INTERFACE ===
# ==========================================
query_params = st.query_params
if "id" in query_params:
    card_id = query_params["id"]; token = query_params.get("t")
    c1, c2, c3 = st.columns([1,2,1]); logo_b64 = get_setting("receipt_logo_base64")
    cust_title = get_setting("customer_ui_title", BRAND_NAME)
    with c2:
        if logo_b64: st.markdown(f'<div style="text-align:center; margin-bottom:10px;"><img src="data:image/png;base64,{logo_b64}" width="160"></div>', unsafe_allow_html=True)
        else: st.markdown(f"<h1 style='text-align:center; color:#D32F2F'>{cust_title}</h1>", unsafe_allow_html=True)
    try: df = run_query("SELECT * FROM customers WHERE card_id = :id", {"id": card_id})
    except: st.stop()
    if not df.empty:
        user = df.iloc[0]
        if user['secret_token'] and token and user['secret_token'] != token: st.warning("⚠️ QR kod köhnəlib.")
        
        comp = random.choice(CARTOON_QUOTES)
        st.markdown(f"<div class='cartoon-quote'>{comp}</div>", unsafe_allow_html=True)

        public_msg = get_setting("public_msg", "")
        if public_msg: st.info(f"📢 {public_msg}")

        notifs = run_query("SELECT * FROM notifications WHERE card_id = :id AND is_read = FALSE", {"id": card_id})
        for _, row in notifs.iterrows():
            with st.container(border=True):
                st.info(f"💌 {row['message']}")
                if row['attached_coupon']: st.success(f"🎁 HƏDİYYƏ: {row['attached_coupon']}")
                if st.button("OXUDUM ✅", key=f"read_{row['id']}"):
                    run_action("UPDATE notifications SET is_read = TRUE WHERE id = :nid", {"nid": row['id']}); st.rerun()

        if not user['is_active']:
            st.warning(f"🎉 Xoş Gəldiniz!")
            with st.form("act"):
                em = st.text_input("📧 Email", key="reg_email"); dob = st.date_input("🎂 Doğum Tarixi", min_value=datetime.date(1950, 1, 1))
                with st.expander("📜 Qaydalar"): st.markdown(get_setting("customer_terms", DEFAULT_TERMS), unsafe_allow_html=True)
                if st.form_submit_button("Təsdiqlə"):
                    run_action("UPDATE customers SET email=:e, birth_date=:b, is_active=TRUE, activated_at=:t WHERE card_id=:i", {"e":em, "b":dob.strftime("%Y-%m-%d"), "i":card_id, "t":get_baku_now()}); st.rerun()
            st.stop()

        # RED STAMP CARD
        ctype = user['type']; st_label = "MEMBER"; disc_txt = ""; border_col = "#B71C1C"
        if ctype == 'golden': st_label="GOLDEN MEMBER"; disc_txt="✨ 5% ENDİRİM"; border_col="#D4AF37"
        elif ctype == 'platinum': st_label="PLATINUM MEMBER"; disc_txt="✨ 10% ENDİRİM"; border_col="#78909C"
        elif ctype == 'elite': st_label="ELITE VIP"; disc_txt="✨ 20% ENDİRİM"; border_col="#B71C1C"
        elif ctype == 'thermos': st_label="EKO-TERM MEMBER"; disc_txt="🌿 20% ENDİRİM"; border_col="#2E7D32"

        st.markdown(f"""
        <div class="stamp-container">
            <div class="stamp-card" style="border-color: {border_col}; color: {border_col}; box-shadow: 0 0 0 4px white, 0 0 0 7px {border_col};">
                <div class="stamp-title">{st_label}</div>
                <div>{disc_txt}</div>
                <div class="stamp-stars">{user['stars']} / 10</div>
                <div class="stamp-footer">ULDUZ BALANSI</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # GREEN CUPS GRID
        html = '<div class="coffee-grid-container">'
        for i in range(10):
            icon = "https://cdn-icons-png.flaticon.com/512/751/751621.png"
            if i < user['stars']:
                if i == 9: html += f'<img src="{icon}" class="cup-earned cup-anim">'
                else: html += f'<img src="{icon}" class="cup-earned coffee-icon-img">'
            else:
                html += f'<img src="{icon}" class="cup-empty coffee-icon-img">'
        st.markdown(html + '</div>', unsafe_allow_html=True)
        if user['stars'] >= 9: st.balloons()

        cps = run_query("SELECT * FROM customer_coupons WHERE card_id = :id AND is_used = FALSE AND (expires_at IS NULL OR expires_at > NOW())", {"id": card_id})
        for _, cp in cps.iterrows(): st.success(f"🎫 KUPON: {cp['coupon_type']}")

        # BIG RED FEEDBACK
        st.markdown('<div class="feedback-container"><div class="feedback-title">RƏYİNİZ BİZİM ÜÇÜN ÖNƏMLİDİR</div>', unsafe_allow_html=True)
        with st.form("feed"):
            s = st.feedback("stars")
            m = st.text_input("Şərhiniz", key="feed_msg", placeholder="Fikirlərinizi yazın...")
            if st.form_submit_button("Göndər") and s:
                run_action("INSERT INTO feedbacks (card_id, rating, comment, created_at) VALUES (:i,:r,:m, :t)", {"i":card_id, "r":s+1, "m":m, "t":get_baku_now()}); st.success("Təşəkkürlər!")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider(); qr_url = f"{APP_URL}/?id={card_id}&t={user['secret_token']}"
        st.download_button("📥 KARTI YÜKLƏ", generate_custom_qr(qr_url, card_id), f"{card_id}.png", "image/png", use_container_width=True)
    else: st.error("Kart tapılmadı")
    st.stop() 

# ==========================================
# === STAFF & ADMIN INTERFACE ===
# ==========================================

# --- CHECK FOR RECEIPT POPUP ON RERUN ---
if st.session_state.show_receipt_popup and st.session_state.last_receipt_data:
    show_receipt_dialog(st.session_state.last_receipt_data['cart'], 
                        st.session_state.last_receipt_data['total'], 
                        st.session_state.last_receipt_data['email'])

if st.session_state.logged_in:
    if not validate_session():
        st.session_state.logged_in=False; st.session_state.session_token=None; st.error("Sessiya bitib."); st.rerun()

if not st.session_state.logged_in:
    c1,c2,c3 = st.columns([1,1,1])
    with c2:
        st.markdown(f"<h1 style='text-align:center; color:#D32F2F;'>{BRAND_NAME}</h1><h5 style='text-align:center;'>{VERSION}</h5>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["STAFF", "ADMIN"])
        with t1:
            with st.form("sl"):
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("Giriş", use_container_width=True):
                    is_blocked, mins = check_login_block(p)
                    if is_blocked: st.error(f"Blok: {mins} dəq"); st.stop()
                    u = run_query("SELECT * FROM users WHERE role IN ('staff','manager')")
                    found = False
                    for _,r in u.iterrows():
                        if verify_password(p, r['password']):
                            clear_failed_login(r['username'])
                            st.session_state.logged_in=True; st.session_state.user=r['username']; st.session_state.role=r['role']; st.session_state.session_token=create_session(r['username'],r['role']); st.rerun()
                            found = True
                    if not found:
                         st.error("Səhv PIN")
                         time.sleep(2)
        with t2:
            with st.form("al"):
                u = st.text_input("User"); p = st.text_input("Pass", type="password")
                if st.form_submit_button("Login"):
                    is_blocked, mins = check_login_block(u)
                    if is_blocked: st.error(f"Blok: {mins} dəq"); st.stop()
                    ud = run_query("SELECT * FROM users WHERE username=:u", {"u":u})
                    if not ud.empty and verify_password(p, ud.iloc[0]['password']):
                        clear_failed_login(u)
                        st.session_state.logged_in=True; st.session_state.user=u; st.session_state.role=ud.iloc[0]['role']; st.session_state.session_token=create_session(u,ud.iloc[0]['role']); st.rerun()
                    else: 
                        register_failed_login(u)
                        st.error("Səhv")
                        time.sleep(2)
else:
    if st.session_state.show_receipt_popup and st.session_state.last_receipt_data:
        show_receipt_dialog(st.session_state.last_receipt_data['cart'], st.session_state.last_receipt_data['total'], st.session_state.last_receipt_data['email'])

    h1, h2, h3 = st.columns([4,1,1])
    with h1: st.markdown(f"**👤 {st.session_state.user}** | {st.session_state.role.upper()}")
    with h2: 
        if st.button("🔄"): st.rerun()
    with h3: 
        if st.button("🚪", type="primary"): 
            run_action("DELETE FROM active_sessions WHERE token=:t", {"t":st.session_state.session_token}); st.session_state.logged_in=False; st.rerun()
    st.divider()

    role = st.session_state.role
    
    tabs_list = []
    if role in ['admin', 'manager', 'staff']:
        tabs_list.append("🏃‍♂️ AL-APAR")
    
    show_tables_for_staff = get_setting("staff_show_tables", "TRUE") == "TRUE"
    show_tables_for_manager = get_setting("manager_show_tables", "TRUE") == "TRUE"
    
    if role == 'admin':
        tabs_list.append("🍽️ MASALAR")
    elif role == 'manager' and show_tables_for_manager:
        tabs_list.append("🍽️ MASALAR")
    elif role == 'staff' and show_tables_for_staff:
        tabs_list.append("🍽️ MASALAR")

    if role in ['admin', 'manager']:
        tabs_list.extend(["💰 Maliyyə", "📦 Anbar", "📊 Analitika", "📜 Loglar", "👥 CRM"])

    if role == 'manager':
         if get_setting("manager_perm_menu", "FALSE") == "TRUE": tabs_list.append("📋 Menyu")
         if get_setting("manager_perm_recipes", "FALSE") == "TRUE": tabs_list.append("📜 Resept")

    if role == 'admin':
        if "📋 Menyu" not in tabs_list: tabs_list.append("📋 Menyu")
        if "📜 Resept" not in tabs_list: tabs_list.append("📜 Resept")
        tabs_list.extend(["📝 Qeydlər", "⚙️ Ayarlar", "💾 Baza", "QR"])
    
    if role in ['staff', 'manager']:
        tabs_list.append("📊 Z-Hesabat")

    my_tabs = st.tabs(tabs_list)
    tab_map = {name: tab for name, tab in zip(tabs_list, my_tabs)}

    if "🏃‍♂️ AL-APAR" in tab_map:
        with tab_map["🏃‍♂️ AL-APAR"]:
            render_takeaway()

    if "🍽️ MASALAR" in tab_map:
        with tab_map["🍽️ MASALAR"]:
            render_tables_main()

    if "📦 Anbar" in tab_map:
        with tab_map["📦 Anbar"]:
            st.subheader("📦 Anbar İdarəetməsi")
            
            if role == 'admin' or role == 'manager':
                with st.expander("➕ Mədaxil / Yeni Mal", expanded=False):
                     st.info("💡 Məs: Qaymaq (0.48 L) = 5.29 AZN. Sistem özü 1 Litrin qiymətini tapacaq.")
                     with st.form("smart_add_item", clear_on_submit=True):
                        c1, c2, c3 = st.columns(3)
                        mn_name = c1.text_input("Malın Adı (Məs: Dom Qaymaq)")
                        sel_cat = c2.selectbox("Kateqoriya", PRESET_CATEGORIES + ["➕ Yeni Yarat..."])
                        mn_unit = c3.selectbox("Əsas Vahid (Resept üçün)", ["L", "KQ", "ƏDƏD"])
                        
                        mn_cat_final = sel_cat
                        if sel_cat == "➕ Yeni Yarat...":
                             mn_cat_final = st.text_input("Yeni Kateqoriya Adı (Məs: Tütün Məmulatları)")
                        
                        st.write("---")
                        c4, c5, c6 = st.columns(3)
                        pack_size = c4.number_input("Aldığın Qabın Həcmi/Çəkisi", min_value=0.001, step=0.001, help="Məs: 0.48 (Litr) və ya 0.5 (KQ)")
                        pack_price = c5.number_input("Aldığın Qabın Qiyməti (AZN)", min_value=0.01, step=0.01, help="Məs: 5.29")
                        pack_count = c6.number_input("Neçə ədəd/qutu almısan?", min_value=0.0, step=0.5, value=1.0)
                        mn_type = st.selectbox("Növ", ["ingredient", "consumable"], index=0)
                        
                        if st.form_submit_button("Hesabla və Yarat / Artır"):
                             if mn_name and pack_size > 0:
                                 calc_unit_cost = pack_price / pack_size 
                                 total_stock_add = pack_size * pack_count 
                                 run_action("""
                                     INSERT INTO ingredients (name, stock_qty, unit, category, type, unit_cost, approx_count) 
                                     VALUES (:n, :q, :u, :c, :t, :uc, 1) 
                                     ON CONFLICT (name) DO UPDATE SET stock_qty = ingredients.stock_qty + :q, unit_cost = :uc
                                 """, {"n":mn_name, "q":total_stock_add, "u":mn_unit, "c":mn_cat_final, "t":mn_type, "uc":calc_unit_cost})
                                 st.success(f"✅ {mn_name} stoka əlavə olundu!")
                                 time.sleep(2); st.rerun()

            c1, c2 = st.columns([3,1])
            search_query = st.text_input("🔍 Axtarış (Bütün Anbar)...", placeholder="Malın adı...")
            if search_query:
                df_i = run_query("SELECT id, name, stock_qty, unit, unit_cost, approx_count, category, type FROM ingredients WHERE name ILIKE :s ORDER BY name", {"s":f"%{search_query}%"})
            else:
                df_i = run_query("SELECT id, name, stock_qty, unit, unit_cost, approx_count, category, type FROM ingredients ORDER BY name")
            
            rows_per_page = st.selectbox("Səhifədə neçə mal olsun?", [20, 40, 60], index=0)
            if rows_per_page != st.session_state.anbar_rows_per_page: st.session_state.anbar_rows_per_page = rows_per_page; st.session_state.anbar_page = 0
            total_rows = len(df_i); total_pages = math.ceil(total_rows / rows_per_page); start_idx = st.session_state.anbar_page * rows_per_page; end_idx = start_idx + rows_per_page
            
            df_page = df_i.iloc[start_idx:end_idx].copy()
            
            if role == 'manager':
                df_page_display = df_page[['id', 'name', 'stock_qty', 'unit', 'category']]
                st.dataframe(df_page_display, hide_index=True, use_container_width=True)
            else:
                df_page['Total Value'] = df_page['stock_qty'] * df_page['unit_cost']
                df_page.insert(0, "Seç", False)
                edited_df = st.data_editor(df_page, hide_index=True, column_config={"Seç": st.column_config.CheckboxColumn(required=True), "unit_cost": st.column_config.NumberColumn(format="%.5f"), "Total Value": st.column_config.NumberColumn(format="%.2f")}, disabled=["id", "name", "stock_qty", "unit", "unit_cost", "approx_count", "category", "Total Value", "type"], use_container_width=True, key="anbar_editor")
                sel_rows = edited_df[edited_df["Seç"]]; sel_ids = sel_rows['id'].tolist(); sel_count = len(sel_ids)
                st.divider(); ab1, ab2, ab3 = st.columns(3)
                with ab1:
                    if sel_count == 1:
                        if st.button("➕ Seçilənə Mədaxil", use_container_width=True, type="secondary", key="btn_restock_active"): st.session_state.restock_item_id = int(sel_ids[0]); st.rerun()
                with ab2:
                    if sel_count == 1:
                        if st.button("✏️ Seçilənə Düzəliş", use_container_width=True, type="secondary", key="btn_edit_anbar_active"): st.session_state.edit_item_id = int(sel_ids[0]); st.rerun()
                with ab3:
                    if sel_count > 0:
                        if st.button(f"🗑️ Sil ({sel_count})", use_container_width=True, type="primary"): 
                             for i in sel_ids: run_action("DELETE FROM ingredients WHERE id=:id", {"id":int(i)})
                             st.success("Silindi!"); time.sleep(1); st.rerun()

            pc1, pc2, pc3 = st.columns([1,2,1])
            with pc1: 
                if st.button("⬅️ Əvvəlki", disabled=(st.session_state.anbar_page == 0)): st.session_state.anbar_page -= 1; st.rerun()
            with pc2: st.markdown(f"<div style='text-align:center; padding-top:10px;'>Səhifə {st.session_state.anbar_page + 1} / {max(1, total_pages)}</div>", unsafe_allow_html=True)
            with pc3: 
                if st.button("Növbəti ➡️", disabled=(st.session_state.anbar_page >= total_pages - 1)): st.session_state.anbar_page += 1; st.rerun()
            
            if role == 'admin':
                with st.expander("📤 İmport / Export (Excel)"):
                    with st.form("anbar_import_form"):
                        upl = st.file_uploader("📥 Import", type="xlsx"); import_type = st.selectbox("Yüklənəcək Malın Növü", ["Ərzaq (Ingredient)", "Sərfiyyat (Consumable)"])
                        if st.form_submit_button("Yüklə (Anbar)"):
                            if upl:
                                try:
                                    df = pd.read_excel(upl); df.columns = [str(c).lower().strip() for c in df.columns]
                                    header_map = {"ad": "name", "mal": "name", "say": "stock_qty", "vahid": "unit", "kateqoriya": "category", "qiymət": "unit_cost", "qutu sayı": "approx_count"}
                                    df.rename(columns=header_map, inplace=True)
                                    if not all(col in df.columns for col in ['name', 'stock_qty', 'unit', 'category', 'unit_cost']): st.error("Sütunlar əskikdir")
                                    else:
                                        df['stock_qty'] = pd.to_numeric(df['stock_qty'], errors='coerce').fillna(0); df['unit_cost'] = pd.to_numeric(df['unit_cost'], errors='coerce').fillna(0); db_type = 'ingredient' if import_type.startswith("Ərzaq") else 'consumable'; count = 0
                                        with conn.session as s:
                                            for _, row in df.iterrows():
                                                if pd.isna(row['name']) or str(row['name']).strip() == "": continue
                                                ac = row['approx_count'] if 'approx_count' in df.columns else 1
                                                s.execute(text("""INSERT INTO ingredients (name, stock_qty, unit, category, type, unit_cost, approx_count) VALUES (:n, :q, :u, :c, :t, :uc, :ac) ON CONFLICT (name) DO UPDATE SET stock_qty = ingredients.stock_qty + :q, unit_cost = :uc"""), {"n": str(row['name']).strip(), "q": float(row['stock_qty']), "u": str(row['unit']).strip(), "c": str(row['category']).strip(), "t": db_type, "uc": float(row['unit_cost']), "ac": int(ac)}); count += 1
                                            s.commit()
                                        log_system(st.session_state.user, f"Anbar Import: {count} mal"); st.success(f"{count} mal yükləndi!")
                                except Exception as e: st.error(f"Xəta: {e}")
                    if st.button("📤 Anbarı Excel Kimi Endir"): out = BytesIO(); run_query("SELECT * FROM ingredients").to_excel(out, index=False); st.download_button("⬇️ Endir (anbar.xlsx)", out.getvalue(), "anbar.xlsx")

            if st.session_state.restock_item_id:
                r_item = run_query("SELECT * FROM ingredients WHERE id=:id", {"id":st.session_state.restock_item_id})
                if not r_item.empty:
                    row = r_item.iloc[0]
                    @st.dialog("➕ Mədaxil")
                    def show_restock(r):
                        st.write(f"**{r['name']}**")
                        with st.form("rs_form", clear_on_submit=True):
                            c1, c2 = st.columns(2); packs = c1.number_input("Neçə ədəd/qutu?", 1); per_pack = c2.number_input(f"Birinin Çəkisi ({r['unit']})", min_value=0.001, step=0.001, value=1.0, format="%.3f"); tot_price = st.number_input("Yekun Məbləğ (AZN)", 0.0)
                            if st.form_submit_button("Təsdiq"):
                                total_new_qty = packs * per_pack; new_cost = tot_price / total_new_qty if total_new_qty > 0 else r['unit_cost']
                                final_cost = new_cost if tot_price > 0 else r['unit_cost']
                                run_action("UPDATE ingredients SET stock_qty=stock_qty+:q, unit_cost=:uc, approx_count=:ac WHERE id=:id", {"q":total_new_qty,"id":int(r['id']), "uc":final_cost, "ac":packs})
                                log_system(st.session_state.user, f"Mədaxil: {r['name']} (+{total_new_qty})"); st.session_state.restock_item_id = None; st.rerun()
                    show_restock(row)

            if st.session_state.edit_item_id and role == 'admin':
                r_item = run_query("SELECT * FROM ingredients WHERE id=:id", {"id":st.session_state.edit_item_id})
                if not r_item.empty:
                    row = r_item.iloc[0]
                    @st.dialog("✏️ Düzəliş")
                    def show_edit(r):
                        with st.form("ed_form"):
                            en = st.text_input("Ad", r['name']); 
                            current_cat = r['category']; idx = 0
                            if current_cat in PRESET_CATEGORIES: idx = PRESET_CATEGORIES.index(current_cat)
                            ec = st.selectbox("Kateqoriya", PRESET_CATEGORIES + ["➕ Yeni Yarat..."], index=idx); 
                            eu = st.selectbox("Vahid", ["KQ", "L", "ƏDƏD"], index=["KQ", "L", "ƏDƏD"].index(r['unit']) if r['unit'] in ["KQ", "L", "ƏDƏD"] else 0); et = st.selectbox("Növ", ["ingredient","consumable"], index=0 if r['type']=='ingredient' else 1); ecost = st.number_input("Maya Dəyəri", value=float(r['unit_cost']), format="%.5f")
                            if ec == "➕ Yeni Yarat...": ec = st.text_input("Yeni Kateqoriya Adı")
                            if st.form_submit_button("Yadda Saxla"):
                                run_action("UPDATE ingredients SET name=:n, category=:c, unit=:u, unit_cost=:uc, type=:t WHERE id=:id", {"n":en, "c":ec, "u":eu, "uc":ecost, "t":et, "id":int(r['id'])}); log_system(st.session_state.user, f"Düzəliş: {en}"); st.session_state.edit_item_id = None; st.rerun()
                    show_edit(row)

    if "💰 Maliyyə" in tab_map:
        with tab_map["💰 Maliyyə"]:
            st.subheader("💰 Maliyyə Mərkəzi")
            with st.expander("🔓 Səhər Kassanı Aç (Opening Balance)"):
                st.info("💡 Səhər kassanı açanda bu düyməyə bas.")
                op_bal = st.number_input("Kassada nə qədər pul var? (AZN)", min_value=0.0, step=0.1)
                if st.button("✅ Kassanı Bu Məbləğlə Aç"):
                    set_setting("cash_limit", str(op_bal))
                    st.success(f"Gün {op_bal} AZN ilə başladı!")
                    time.sleep(1); st.rerun()

            view_mode = st.radio("Görünüş Rejimi:", ["🕒 Bu Növbə (08:00+)", "📅 Ümumi Balans (Yekun)"], horizontal=True)
            now = get_baku_now()
            if now.hour >= 8: shift_start = now.replace(hour=8, minute=0, second=0, microsecond=0)
            else: shift_start = (now - datetime.timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
            
            if "Növbə" in view_mode:
                sales_cash = run_query("SELECT SUM(total) as s FROM sales WHERE payment_method='Cash' AND created_at >= :d", {"d":shift_start}).iloc[0]['s'] or 0.0
                sales_card = run_query("SELECT SUM(total) as s FROM sales WHERE payment_method='Card' AND created_at >= :d", {"d":shift_start}).iloc[0]['s'] or 0.0
                exp_cash = run_query("SELECT SUM(amount) as e FROM finance WHERE source='Kassa' AND type='out' AND created_at >= :d", {"d":shift_start}).iloc[0]['e'] or 0.0
                inc_cash = run_query("SELECT SUM(amount) as i FROM finance WHERE source='Kassa' AND type='in' AND created_at >= :d", {"d":shift_start}).iloc[0]['i'] or 0.0
                start_lim = float(get_setting("cash_limit", "0.0"))
                disp_cash = start_lim + float(sales_cash) + float(inc_cash) - float(exp_cash)
                disp_card = float(sales_card) 
                inc_safe = run_query("SELECT SUM(amount) as i FROM finance WHERE source='Seyf' AND type='in' AND created_at >= :d", {"d":shift_start}).iloc[0]['i'] or 0.0
                out_safe = run_query("SELECT SUM(amount) as o FROM finance WHERE source='Seyf' AND type='out' AND created_at >= :d", {"d":shift_start}).iloc[0]['o'] or 0.0
                disp_safe = float(inc_safe) - float(out_safe)
                inv_shift_out = run_query("SELECT SUM(amount) as o FROM finance WHERE source='Investor' AND type='out' AND created_at >= :d", {"d":shift_start}).iloc[0]['o'] or 0.0
                disp_investor = float(inv_shift_out)
            else:
                last_z = get_setting("last_z_report_time")
                if last_z: last_z_dt = datetime.datetime.fromisoformat(last_z)
                else: last_z_dt = datetime.datetime.now() - datetime.timedelta(days=365)
                s_cash = run_query("SELECT SUM(total) as s FROM sales WHERE payment_method='Cash' AND created_at > :d", {"d":last_z_dt}).iloc[0]['s'] or 0.0
                e_cash = run_query("SELECT SUM(amount) as e FROM finance WHERE source='Kassa' AND type='out' AND created_at > :d", {"d":last_z_dt}).iloc[0]['e'] or 0.0
                i_cash = run_query("SELECT SUM(amount) as i FROM finance WHERE source='Kassa' AND type='in' AND created_at > :d", {"d":last_z_dt}).iloc[0]['i'] or 0.0
                start_lim = float(get_setting("cash_limit", "100.0"))
                disp_cash = start_lim + float(s_cash) + float(i_cash) - float(e_cash)
                s_card = run_query("SELECT SUM(total) as s FROM sales WHERE payment_method='Card'").iloc[0]['s'] or 0.0
                f_card_in = run_query("SELECT SUM(amount) as i FROM finance WHERE source='Bank Kartı' AND type='in'").iloc[0]['i'] or 0.0
                f_card_out = run_query("SELECT SUM(amount) as o FROM finance WHERE source='Bank Kartı' AND type='out'").iloc[0]['o'] or 0.0
                disp_card = float(s_card) + float(f_card_in) - float(f_card_out)
                f_safe_in = run_query("SELECT SUM(amount) as i FROM finance WHERE source='Seyf' AND type='in'").iloc[0]['i'] or 0.0
                f_safe_out = run_query("SELECT SUM(amount) as o FROM finance WHERE source='Seyf' AND type='out'").iloc[0]['o'] or 0.0
                disp_safe = float(f_safe_in) - float(f_safe_out)
                inv_total_out = run_query("SELECT SUM(amount) as o FROM finance WHERE source='Investor' AND type='out'").iloc[0]['o'] or 0.0
                inv_total_in = run_query("SELECT SUM(amount) as i FROM finance WHERE source='Investor' AND type='in'").iloc[0]['i'] or 0.0
                disp_investor = float(inv_total_out) - float(inv_total_in)

            st.divider(); m1, m2, m3, m4 = st.columns(4)
            m1.metric("🏪 Kassa (Cibdə)", f"{disp_cash:.2f} ₼"); m2.metric("💳 Bank Kartı", f"{disp_card:.2f} ₼"); m3.metric("🏦 Seyf", f"{disp_safe:.2f} ₼"); m4.metric("👤 Investor (Borc)", f"{disp_investor:.2f} ₼")
            if role == 'admin' and "Ümumi" in view_mode:
                with st.expander("🛠️ Bank Kartı Balansını Düzəlt (Reset)"):
                    target_val = st.number_input("Kartda Hal-hazırda Olan Real Məbləğ", value=disp_card, step=0.01)
                    if st.button("Balansı Düzəlt"):
                        diff = target_val - disp_card
                        if diff != 0:
                            ftype = 'in' if diff > 0 else 'out'
                            run_action("INSERT INTO finance (type, category, amount, source, description, created_by) VALUES (:t, 'Düzəliş', :a, 'Bank Kartı', 'Admin Reset', :u)", {"t":ftype, "a":abs(diff), "u":st.session_state.user}); st.success("Balans düzəldildi!"); time.sleep(1); st.rerun()
            st.markdown("---")
            with st.expander("➕ Yeni Əməliyyat", expanded=True):
                with st.form("new_fin_trx"):
                    c1, c2, c3 = st.columns(3); f_type = c1.selectbox("Növ", ["Məxaric (Çıxış) 🔴", "Mədaxil (Giriş) 🟢"]); f_source = c2.selectbox("Mənbə", ["Kassa", "Bank Kartı", "Seyf", "Investor"]); f_subj = c3.selectbox("Subyekt", SUBJECTS)
                    c4, c5 = st.columns(2); f_cat = c4.selectbox("Kateqoriya", ["Xammal Alışı", "Maaş/Avans", "Borc Ödənişi", "İnvestisiya", "Təsərrüfat", "Kassa Kəsiri / Bərpası", "İnkassasiya (Seyfə)", "Digər"]); f_amt = c5.number_input("Məbləğ (AZN)", min_value=0.01, step=0.01); f_desc = st.text_input("Qeyd")
                    if st.form_submit_button("Təsdiqlə"):
                        db_type = 'out' if "Məxaric" in f_type else 'in'
                        run_action("INSERT INTO finance (type, category, amount, source, description, created_by, subject) VALUES (:t, :c, :a, :s, :d, :u, :sb)", {"t":db_type, "c":f_cat, "a":f_amt, "s":f_source, "d":f_desc, "u":st.session_state.user, "sb":f_subj})
                        if db_type == 'out': run_action("INSERT INTO expenses (amount, reason, spender, source) VALUES (:a, :r, :s, :src)", {"a":f_amt, "r":f"{f_subj} - {f_desc}", "s":st.session_state.user, "src":f_source})
                        log_system(st.session_state.user, f"Maliyyə: {db_type.upper()} {f_amt} ({f_cat})"); st.success("Yazıldı!"); st.rerun()
            st.write("📜 Son Əməliyyatlar"); fin_df = run_query("SELECT * FROM finance"); st.dataframe(fin_df.sort_values(by="created_at", ascending=False).head(20), hide_index=True, use_container_width=True)

    if "📝 Qeydlər" in tab_map:
        with tab_map["📝 Qeydlər"]:
            st.subheader("📝 Şəxsi Qeydlər (Admin)")
            st.info("💡 Bu qeydlər Maliyyəyə və Anbara təsir etmir. Yalnız sizin üçündür.")
            
            # Add Note
            with st.form("add_note_form", clear_on_submit=True):
                new_note = st.text_input("Yeni Qeyd (Məs: Bazarlıq pulunu cibimdən verdim - 50 AZN)")
                if st.form_submit_button("➕ Əlavə Et"):
                    if new_note:
                        run_action("INSERT INTO admin_notes (note) VALUES (:n)", {"n":new_note})
                        st.success("Qeyd əlavə olundu!"); st.rerun()
            
            # List Notes
            notes = run_query("SELECT * FROM admin_notes ORDER BY created_at DESC")
            if not notes.empty:
                for _, row in notes.iterrows():
                    c1, c2 = st.columns([4, 1])
                    with c1: st.write(f"📅 {row['created_at'].strftime('%d/%m %H:%M')} - **{row['note']}**")
                    with c2: 
                        if st.button("❌ Sil", key=f"del_note_{row['id']}"):
                            run_action("DELETE FROM admin_notes WHERE id=:id", {"id":row['id']})
                            st.rerun()
            else:
                st.write("Hələ ki qeyd yoxdur.")

    if "📜 Resept" in tab_map:
        with tab_map["📜 Resept"]:
            st.subheader("📜 Resept")
            sel_prod = st.selectbox("Məhsul", ["(Seçin)"] + run_query("SELECT item_name FROM menu WHERE is_active=TRUE")['item_name'].tolist())
            if sel_prod != "(Seçin)":
                recs = run_query("SELECT id, ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:n ORDER BY id", {"n":sel_prod})
                recs.insert(0, "Seç", False)
                ed_recs = st.data_editor(recs, hide_index=True, column_config={"Seç": st.column_config.CheckboxColumn(required=True), "quantity_required": st.column_config.NumberColumn(label="Miqdar", min_value=0.0, step=0.001, format="%.3f")}, disabled=["id", "ingredient_name"], use_container_width=True, key="rec_editor")
                sel_rows = ed_recs[ed_recs["Seç"]]; del_ids = sel_rows['id'].tolist()
                c_del, c_upd = st.columns(2)
                with c_del:
                    if role == 'admin':
                        if del_ids and st.button(f"🗑️ Seçilənləri Sil ({len(del_ids)})", type="primary"):
                            for i in del_ids: run_action("DELETE FROM recipes WHERE id=:id", {"id":int(i)})
                            log_system(st.session_state.user, f"Resept Silinmə: {sel_prod} ({len(del_ids)} sətir)"); st.success("Silindi!"); time.sleep(0.5); st.rerun()
                with c_upd:
                    if role == 'admin':
                        if st.button("💾 Dəyişiklikləri Yadda Saxla"):
                            with conn.session as s:
                                for _, row in ed_recs.iterrows():
                                    if not row['Seç']: s.execute(text("UPDATE recipes SET quantity_required=:q WHERE id=:id"), {"q":float(row['quantity_required']), "id":int(row['id'])})
                                s.commit()
                            st.success("Yeniləndi!"); time.sleep(0.5); st.rerun()
                st.divider()
                if role in ['admin', 'manager']: # Allow manager too
                    with st.form("add_rec", clear_on_submit=True):
                        ing_data = run_query("SELECT name, stock_qty, unit FROM ingredients ORDER BY name")
                        ing_options = {f"{r['name']} (Stok: {r['stock_qty']} {r['unit']})": r['name'] for _, r in ing_data.iterrows()}
                        s_label = st.selectbox("Xammal Seç (Stok Görüntülü)", list(ing_options.keys()))
                        real_ing_name = ing_options[s_label]
                        def_val = 1.0 if sel_prod == real_ing_name else 0.0
                        s_q = st.number_input("Miqdar", value=def_val, step=0.001)
                        if st.form_submit_button("Əlavə Et"): 
                            run_action("INSERT INTO recipes (menu_item_name,ingredient_name,quantity_required) VALUES (:m,:i,:q)",{"m":sel_prod,"i":real_ing_name,"q":s_q}); st.rerun()
            
            if role == 'admin':
                with st.expander("📤 Reseptləri İmport / Export (Excel)"):
                    if st.button("⚠️ Bütün Reseptləri Sil (Təmizlə)", type="primary"):
                        admin_confirm_dialog("Bütün reseptlər silinsin? Geri qaytarmaq olmayacaq!", lambda: run_action("DELETE FROM recipes"))
                    with st.form("recipe_import_form"):
                        upl_rec = st.file_uploader("📥 Import", type="xlsx")
                        if st.form_submit_button("Reseptləri Yüklə"):
                            if upl_rec:
                                try:
                                    df_r = pd.read_excel(upl_rec); df_r.columns = [str(c).lower().strip() for c in df_r.columns]; req = ['menu_item_name', 'ingredient_name', 'quantity_required']; r_map = {"mal": "menu_item_name", "məhsul": "menu_item_name", "xammal": "ingredient_name", "miqdar": "quantity_required"}; df_r.rename(columns=r_map, inplace=True)
                                    if not all(col in df_r.columns for col in req): st.error("Sütunlar əskikdir")
                                    else:
                                        cnt = 0; 
                                        with conn.session as s:
                                            for _, r in df_r.iterrows():
                                                if pd.isna(r['menu_item_name']): continue
                                                s.execute(text("INSERT INTO recipes (menu_item_name, ingredient_name, quantity_required) VALUES (:m, :i, :q)"), {"m":str(r['menu_item_name']), "i":str(r['ingredient_name']), "q":float(r['quantity_required'])}); cnt += 1
                                            s.commit()
                                        log_system(st.session_state.user, f"Resept Import: {cnt} sətir"); st.success(f"{cnt} resept sətri yükləndi!")
                                except Exception as e: st.error(f"Xəta: {e}")
                    if st.button("📤 Reseptləri Excel Kimi Endir"): out = BytesIO(); run_query("SELECT * FROM recipes").to_excel(out, index=False); st.download_button("⬇️ Endir (recipes.xlsx)", out.getvalue(), "recipes.xlsx")

    if "📊 Analitika" in tab_map:
        with tab_map["📊 Analitika"]:
            st.subheader("📊 Analitika & Mənfəət")
            c1, c2 = st.columns(2); 
            d1 = c1.date_input("Start", datetime.date.today(), key="ana_date_start"); 
            d2 = c2.date_input("End", datetime.date.today(), key="ana_date_end"); 
            t1 = c1.time_input("Saat Başla", datetime.time(8,0)); t2 = c2.time_input("Saat Bit", datetime.time(23,59)); ts_start = datetime.datetime.combine(d1, t1); ts_end = datetime.datetime.combine(d2 + datetime.timedelta(days=1 if t2 < t1 else 0), t2)
            sales = run_query("SELECT * FROM sales WHERE created_at BETWEEN :s AND :e", {"s":ts_start, "e":ts_end})
            exps = run_query("SELECT * FROM expenses WHERE created_at BETWEEN :s AND :e", {"s":ts_start, "e":ts_end})
            
            total_rev = sales['total'].sum() if not sales.empty else 0.0
            rev_cash = sales[sales['payment_method']=='Cash']['total'].sum() if not sales.empty else 0.0
            rev_card = sales[sales['payment_method']=='Card']['total'].sum() if not sales.empty else 0.0
            total_exp = exps['amount'].sum() if not exps.empty else 0.0
            
            est_cogs = 0.0
            if not sales.empty and role == 'admin':
                all_recs = run_query("SELECT r.menu_item_name, r.quantity_required, i.unit_cost FROM recipes r JOIN ingredients i ON r.ingredient_name = i.name")
                item_costs = {}
                for _, r in all_recs.iterrows():
                    nm = r['menu_item_name']
                    cost = float(r['quantity_required']) * float(r['unit_cost'])
                    item_costs[nm] = item_costs.get(nm, 0.0) + cost
                for items_str in sales['items']:
                    if items_str:
                        parts = items_str.split(", ")
                        for p in parts:
                            try:
                                match = re.match(r"(.+) x(\d+)", p)
                                if match:
                                    iname = match.group(1).strip(); iqty = int(match.group(2))
                                    if iname in item_costs: est_cogs += (item_costs[iname] * iqty)
                            except: pass
            
            gross_profit = total_rev - est_cogs
            
            m1, m2, m3 = st.columns(3); m1.metric("Toplam Satış", f"{total_rev:.2f} ₼"); m2.metric("💳 Kartla", f"{rev_card:.2f} ₼"); m3.metric("💵 Nağd (Kassa)", f"{rev_cash:.2f} ₼")
            st.markdown("---"); k1, k2, k3 = st.columns(3)
            
            if role == 'admin':
                k1.metric("Kassa Xərci (Real)", f"{total_exp:.2f} ₼", help="Kassadan çıxan canlı pul"); k2.metric("Təxmini Maya Dəyəri", f"{est_cogs:.2f} ₼", help="Resept əsasında silinən mal"); k3.metric("Təxmini Mənfəət", f"{gross_profit:.2f} ₼", delta_color="normal")
            else:
                k1.metric("Kassa Xərci (Real)", "***"); k2.metric("Təxmini Maya Dəyəri", "***"); k3.metric("Təxmini Mənfəət", "***")

            if role == 'admin' or role == 'manager':
                st.markdown("### 🗑️ Satışların İdarəedilməsi")
                df_to_edit = sales.copy()
                df_to_edit.insert(0, "Seç", False)
                edited_sales = st.data_editor(
                    df_to_edit, 
                    hide_index=True, 
                    column_config={"Seç": st.column_config.CheckboxColumn(required=True)},
                    disabled=["id", "items", "total", "payment_method", "cashier", "created_at", "customer_card_id"],
                    use_container_width=True
                )
                
                selected_sales = edited_sales[edited_sales["Seç"]]
                if not selected_sales.empty:
                    if st.button(f"🗑️ Seçilən {len(selected_sales)} Satışı Sil"):
                        smart_bulk_delete_dialog(selected_sales)
                
            else: st.dataframe(sales, hide_index=True)

    if "📜 Loglar" in tab_map:
        with tab_map["📜 Loglar"]:
            st.dataframe(run_query("SELECT * FROM system_logs ORDER BY created_at DESC LIMIT 100"), hide_index=True)
    
    if "👥 CRM" in tab_map:
        with tab_map["👥 CRM"]:
            st.subheader("👥 CRM & Promo"); cust_df = run_query("SELECT card_id, type, stars, email FROM customers"); cust_df.insert(0, "Seç", False); ed_cust = st.data_editor(cust_df, hide_index=True, column_config={"Seç": st.column_config.CheckboxColumn(required=True)}, key="crm_sel"); sel_cust_ids = ed_cust[ed_cust["Seç"]]['card_id'].tolist()
            st.divider(); c1, c2 = st.columns(2)
            with c1:
                msg = st.text_area("Ekran Mesajı"); promo_list = ["(Kuponsuz)"] + run_query("SELECT code FROM promo_codes")['code'].tolist(); sel_promo = st.selectbox("Promo Yapışdır (Seçilənlərə)", promo_list)
                if st.button("📢 Seçilənlərə Göndər / Tətbiq Et"):
                    if sel_cust_ids:
                        for cid in sel_cust_ids:
                            if msg: run_action("INSERT INTO notifications (card_id, message) VALUES (:c, :m)", {"c":cid, "m":msg})
                            if sel_promo != "(Kuponsuz)": exp = get_baku_now() + datetime.timedelta(days=30); run_action("INSERT INTO customer_coupons (card_id, coupon_type, expires_at) VALUES (:c, :t, :e)", {"c":cid, "t":sel_promo, "e":exp})
                        st.success(f"{len(sel_cust_ids)} nəfərə tətbiq edildi!")
                    else: st.warning("Müştəri seçin!")

    if "📋 Menyu" in tab_map:
        with tab_map["📋 Menyu"]:
            st.subheader("📋 Menyu"); 
            if role in ['admin', 'manager']: # Allow manager too
                with st.expander("➕ Tək Mal Əlavə Et (Menu)"):
                    with st.form("nm", clear_on_submit=True):
                        n=st.text_input("Ad"); p=st.number_input("Qiymət"); c=st.text_input("Kat"); ic=st.checkbox("Kofe?")
                        if st.form_submit_button("Yarat"): run_action("INSERT INTO menu (item_name,price,category,is_active,is_coffee) VALUES (:n,:p,:c,TRUE,:ic)", {"n":n,"p":p,"c":c,"ic":ic}); st.rerun()
            ml = run_query("SELECT * FROM menu ORDER BY category, item_name"); ml.insert(0, "Seç", False)
            ed_m = st.data_editor(ml, hide_index=True, column_config={"Seç": st.column_config.CheckboxColumn(required=True)}, disabled=["id","item_name","price","category","is_active","is_coffee"], use_container_width=True)
            sel_m_rows = ed_m[ed_m["Seç"]]; sel_m_ids = sel_m_rows['id'].tolist(); m_cnt = len(sel_m_ids)
            st.divider(); mc1, mc2, mc3 = st.columns(3)
            with mc1:
                if m_cnt == 1 and st.button("✏️ Düzəliş", use_container_width=True, key="btn_edit_menu_active"): st.session_state.menu_edit_id = int(sel_m_ids[0]); st.rerun()
            with mc2:
                if role == 'admin' and m_cnt > 0 and st.button(f"🗑️ Sil ({m_cnt})", type="primary", use_container_width=True, key="btn_del_menu_active"): admin_confirm_dialog(f"{m_cnt} mal menyudan silinsin?", lambda: [run_action("DELETE FROM menu WHERE id=:id", {"id":int(i)}) for i in sel_m_ids])
            if st.session_state.menu_edit_id:
                m_item = run_query("SELECT * FROM menu WHERE id=:id", {"id":st.session_state.menu_edit_id})
                if not m_item.empty:
                    mr = m_item.iloc[0]
                    @st.dialog("✏️ Menyu Düzəliş")
                    def edit_menu_dialog(r):
                        with st.form("emu"):
                            en = st.text_input("Ad", r['item_name']); ep = st.number_input("Qiymət", value=float(r['price'])); ec = st.text_input("Kateqoriya", r['category']); eic = st.checkbox("Kofe?", value=r['is_coffee'])
                            if st.form_submit_button("Yadda Saxla"): run_action("UPDATE menu SET item_name=:n, price=:p, category=:c, is_coffee=:ic WHERE id=:id", {"n":en,"p":ep,"c":ec,"ic":eic,"id":int(r['id'])}); log_system(st.session_state.user, f"Menyu Düzəliş: {en}"); st.session_state.menu_edit_id = None; st.rerun()
                    edit_menu_dialog(mr)
            
            if role == 'admin':
                with st.expander("📤 Menyu İmport / Export (Excel)"):
                    with st.form("menu_imp_form"):
                        upl_m = st.file_uploader("📥 Import Menu", type="xlsx")
                        if st.form_submit_button("Yüklə (Menu)"):
                            if upl_m:
                                try:
                                    df_m = pd.read_excel(upl_m); df_m.columns = [str(c).lower().strip() for c in df_m.columns]; menu_map = {"ad": "item_name", "mal": "item_name", "qiymət": "price", "kateqoriya": "category", "kofe": "is_coffee"}; df_m.rename(columns=menu_map, inplace=True); req = ['item_name', 'price', 'category', 'is_coffee']
                                    if not all(col in df_m.columns for col in req): st.error("Sütunlar əskikdir")
                                    else:
                                        cnt = 0; 
                                        with conn.session as s:
                                            for _, r in df_m.iterrows():
                                                if pd.isna(r['item_name']): continue
                                                existing = s.execute(text("SELECT id FROM menu WHERE item_name=:n"), {"n":str(r['item_name'])}).fetchall()
                                                if existing: s.execute(text("UPDATE menu SET price=:p, category=:c, is_coffee=:ic WHERE id=:id"), {"p":float(r['price']), "c":str(r['category']), "ic":bool(r['is_coffee']), "id":int(existing[0][0])})
                                                else: s.execute(text("INSERT INTO menu (item_name, price, category, is_active, is_coffee) VALUES (:n, :p, :c, TRUE, :ic)"), {"n":str(r['item_name']), "p":float(r['price']), "c":str(r['category']), "ic":bool(r['is_coffee'])})
                                                cnt += 1
                                            s.commit()
                                        log_system(st.session_state.user, f"Menyu Import: {cnt} mal"); st.success(f"{cnt} mal yükləndi!")
                                except Exception as e: st.error(f"Xəta: {e}")
                    if st.button("📤 Menyu Excel Kimi Endir"): out = BytesIO(); run_query("SELECT item_name, price, category, is_coffee FROM menu").to_excel(out, index=False); st.download_button("⬇️ Endir (menu.xlsx)", out.getvalue(), "menu.xlsx")

    if "⚙️ Ayarlar" in tab_map:
        with tab_map["⚙️ Ayarlar"]: # FIXED ALL TAB REFERENCES
            st.subheader("⚙️ Ayarlar")
            st.markdown("### 🛠️ Menecer Səlahiyyətləri")
            col_mp1, col_mp2, col_mp3, col_mp4 = st.columns(4)
            perm_menu = col_mp1.checkbox("✅ Menyu (Düzəliş)", value=(get_setting("manager_perm_menu", "FALSE") == "TRUE"))
            if col_mp1.button("Yadda Saxla (Menu)"): set_setting("manager_perm_menu", "TRUE" if perm_menu else "FALSE"); st.success("OK"); time.sleep(0.5); st.rerun()
            perm_tables = col_mp2.checkbox("✅ Masalar", value=(get_setting("manager_show_tables", "TRUE") == "TRUE"))
            if col_mp2.button("Yadda Saxla (Tables)", key="save_mgr_tables"): set_setting("manager_show_tables", "TRUE" if perm_tables else "FALSE"); st.success("OK"); time.sleep(0.5); st.rerun()
            perm_crm = col_mp3.checkbox("✅ CRM (Müştəri)", value=(get_setting("manager_perm_crm", "TRUE") == "TRUE")) 
            if col_mp3.button("Yadda Saxla (CRM)"): set_setting("manager_perm_crm", "TRUE" if perm_crm else "FALSE"); st.success("OK"); time.sleep(0.5); st.rerun()
            perm_recipes = col_mp4.checkbox("✅ Reseptlər", value=(get_setting("manager_perm_recipes", "FALSE") == "TRUE"))
            if col_mp4.button("Yadda Saxla (Resept)"): set_setting("manager_perm_recipes", "TRUE" if perm_recipes else "FALSE"); st.success("OK"); time.sleep(0.5); st.rerun()
            st.divider()

            with st.expander("👤 Rolu Dəyişdir (Promote/Demote)"):
                with st.form("change_role_form"):
                    all_users = run_query("SELECT username, role FROM users")
                    target_user = st.selectbox("İşçi Seç", all_users['username'].tolist())
                    new_role = st.selectbox("Yeni Rol", ["staff", "manager", "admin"])
                    if st.form_submit_button("Rolu Dəyiş"):
                        run_action("UPDATE users SET role=:r WHERE username=:u", {"r":new_role, "u":target_user})
                        st.success(f"{target_user} artıq {new_role} oldu!")
                        time.sleep(1); st.rerun()

            with st.expander("⚡ Tarixçə Bərpası (01.02.2026)"):
                st.info("Bu düymə dünənki 11 satışı bazaya yazacaq.")
                if st.button("📅 Dünənki Satışları Yüklə"):
                    history_data = [
                        {"time": "2026-02-01 10:36:05", "cashier": "Sabina", "method": "Cash", "total": 13.4, "items": "Şokoladlı Cookie x2, Cappuccino M x1, Americano M x1"},
                        {"time": "2026-02-01 11:17:54", "cashier": "Sabina", "method": "Card", "total": 1.5, "items": "Şokoladlı Cookie x1"},
                        {"time": "2026-02-01 11:43:41", "cashier": "Sabina", "method": "Card", "total": 5.9, "items": "Americano L x1"},
                        {"time": "2026-02-01 13:27:16", "cashier": "Sabina", "method": "Card", "total": 9.0, "items": "Cappuccino S x2"},
                        {"time": "2026-02-01 13:34:30", "cashier": "Sabina", "method": "Cash", "total": 4.7, "items": "Mocha S x1"},
                        {"time": "2026-02-01 14:18:10", "cashier": "Sabina", "method": "Card", "total": 3.9, "items": "Americano S x1"},
                        {"time": "2026-02-01 14:27:33", "cashier": "Sabina", "method": "Cash", "total": 6.7, "items": "Su (500ml) x1, Raf S x1"},
                        {"time": "2026-02-01 15:44:27", "cashier": "Sabina", "method": "Cash", "total": 13.0, "items": "Cappuccino L x2"},
                        {"time": "2026-02-01 17:02:10", "cashier": "Samir", "method": "Cash", "total": 15.0, "items": "Cappuccino M x1, Cappuccino L x1, Ekler x2"},
                        {"time": "2026-02-01 18:25:44", "cashier": "Samir", "method": "Card", "total": 6.5, "items": "Cappuccino L x1"},
                        {"time": "2026-02-01 19:15:50", "cashier": "Samir", "method": "Cash", "total": 2.0, "items": "Çay L x1"}
                    ]
                    try:
                        with conn.session as s:
                            count = 0
                            for h in history_data:
                                exist = s.execute(text("SELECT id FROM sales WHERE created_at=:t AND total=:tot"), {"t":h['time'], "tot":h['total']}).fetchone()
                                if not exist:
                                    s.execute(text("INSERT INTO sales (items, total, payment_method, cashier, created_at, original_total, discount_amount) VALUES (:i, :t, :p, :c, :tm, :t, 0)"), 
                                                {"i":h['items'], "t":h['total'], "p":h['method'], "c":h['cashier'], "tm":h['time']})
                                    count += 1
                            s.commit()
                        st.success(f"✅ {count} ədəd satış tarixçəyə yazıldı!")
                        
                        run_action("INSERT INTO finance (type, category, amount, source, description, created_by, created_at) VALUES ('out', 'Maaş/Xərc', 58.80, 'Kassa', 'Dünənki balans fərqi (Maaşlar+)', 'Admin', '2026-02-01 23:59:00')")
                        run_action("INSERT INTO expenses (amount, reason, spender, source, created_at) VALUES (58.80, 'Dünənki balans fərqi', 'Admin', 'Kassa', '2026-02-01 23:59:00')")
                        st.success("✅ Kassa balansı 99 AZN-ə bərabərləşdirildi (58.80 Xərc silindi).")
                    except Exception as e: st.error(f"Xəta: {e}")

            with st.expander("🔑 Şifrə Dəyişmə"):
                users = run_query("SELECT username FROM users"); sel_u_pass = st.selectbox("İşçi Seç", users['username'].tolist(), key="pass_change_sel"); new_pass = st.text_input("Yeni Şifrə", type="password")
                if st.button("Şifrəni Yenilə"): run_action("UPDATE users SET password=:p WHERE username=:u", {"p":hash_password(new_pass), "u":sel_u_pass}); st.success("Yeniləndi!")
            
            with st.expander("👥 İşçi İdarə"):
                with st.form("nu"):
                    u = st.text_input("İstifadəçi"); p = st.text_input("Şifrə"); r = st.selectbox("Rol", ["staff","manager","admin"])
                    if st.form_submit_button("Yarat"): run_action("INSERT INTO users (username, password, role) VALUES (:u, :p, :r) ON CONFLICT (username) DO NOTHING", {"u":u, "p":hash_password(p), "r":r}); st.success("OK"); st.rerun()
                du = st.selectbox("Silinəcək", users['username'].tolist(), key="del_user_sel")
                if st.button("İşçini Sil"): admin_confirm_dialog(f"Sil: {du}?", lambda: run_action("DELETE FROM users WHERE username=:u", {"u":du}))
            
            with st.expander("🔧 Sistem"):
                st_tbl = st.checkbox("Staff Masaları Görsün?", value=(get_setting("staff_show_tables","TRUE")=="TRUE"))
                if st.button("Yadda Saxla (Tables)", key="save_staff_tables"): set_setting("staff_show_tables", "TRUE" if st_tbl else "FALSE"); st.rerun()
                test_mode = st.checkbox("Z-Hesabat [TEST MODE]?", value=(get_setting("z_report_test_mode") == "TRUE"))
                if st.button("Yadda Saxla (Test Mode)"): set_setting("z_report_test_mode", "TRUE" if test_mode else "FALSE"); st.success("Dəyişdirildi!"); st.rerun()
                c_lim = st.number_input("Standart Kassa Limiti (Z-Hesabat üçün)", value=float(get_setting("cash_limit", "100.0")))
                if st.button("Limiti Yenilə"): set_setting("cash_limit", str(c_lim)); st.success("Yeniləndi!")
                rules = st.text_area("Qaydalar", value=get_setting("customer_rules", DEFAULT_TERMS))
                if st.button("Qaydaları Yenilə"): set_setting("customer_rules", rules); st.success("Yeniləndi")
            lg = st.file_uploader("Logo"); 
            if lg: set_setting("receipt_logo_base64", image_to_base64(lg)); st.success("Yükləndi")

    if "💾 Baza" in tab_map:
         with tab_map["💾 Baza"]:
             c_b1, c_b2 = st.columns(2)
             with c_b1:
                 st.markdown("#### 📥 YEDƏKLƏMƏ (Backup)")
                 if st.button("FULL BACKUP Yüklə", type="primary"):
                    log_system(st.session_state.user, "Downloaded Backup")
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                        for t in ["users","menu","sales","ingredients","recipes","customers","customer_coupons","notifications","coupon_templates","settings","expenses","finance","system_logs"]:
                            try: run_query(f"SELECT * FROM {t}").to_excel(writer, sheet_name=t, index=False)
                            except: pass
                    st.download_button("⬇️ Endir", out.getvalue(), "Backup_Full.xlsx")
            
             with c_b2:
                 st.markdown("#### 🔄 BƏRPA (Restore)")
                 rf = st.file_uploader("Backup Faylı (.xlsx)", key="rest_file")
                 rp = st.text_input("Admin Şifrəsi", type="password", key="rest_pass")
                 if rf and st.button("⚠️ Bərpa Et", key="btn_rest"):
                     adm = run_query("SELECT password FROM users WHERE role='admin' LIMIT 1")
                     if verify_password(rp, adm.iloc[0]['password']):
                         xls = pd.ExcelFile(rf)
                         try:
                             for t in xls.sheet_names: run_action(f"DELETE FROM {t}"); pd.read_excel(xls, t).to_sql(t, conn.engine, if_exists='append', index=False)
                             log_system(st.session_state.user, "Restored Backup"); st.success("Uğurla Bərpa Olundu!")
                         except: st.error("Fayl Xətası")
                     else: st.error("Şifrə Səhvdir")
        
    if "QR" in tab_map:
        with tab_map["QR"]:
            st.subheader("QR Kodlar")
            cnt = st.number_input("Say",1,100)
            k = st.selectbox("Növ", ["Golden (5%)", "Platinum (10%)", "Elite (20%)", "Termos (20%)", "Ikram (100%)"])
            if st.button("QR Yarat"): 
                type_map = {"Golden (5%)":"golden", "Platinum (10%)":"platinum", "Elite (20%)":"elite", "Thermos (20%)":"thermos", "Ikram (100%)":"ikram"}
                generated_qrs = []
                for _ in range(cnt):
                    cid = str(random.randint(10000000,99999999)); tok = secrets.token_hex(8)
                    run_action("INSERT INTO customers (card_id, stars, type, secret_token) VALUES (:i, 0, :t, :s)", {"i":cid, "t":type_map[k], "s":tok})
                    url = f"{APP_URL}/?id={cid}&t={tok}"
                    img_bytes = generate_styled_qr(url)
                    generated_qrs.append((cid, img_bytes))
                zip_buf = BytesIO()
                with zipfile.ZipFile(zip_buf, "w") as zf:
                    for cid, img in generated_qrs: zf.writestr(f"{cid}_{type_map[k]}.png", img)
                st.success(f"{cnt} QR Kod yaradıldı!")
                st.download_button("📦 Hamsını Endir (ZIP)", zip_buf.getvalue(), "qrcodes.zip", "application/zip")

    if role == 'staff' or role == 'manager':
        if "📊 Z-Hesabat" in tab_map:
            with tab_map["📊 Z-Hesabat"]:
                st.subheader("📊 Z-Hesabat & Satışlar")
                sc1, sc2 = st.columns([1,3])
                with sc1:
                    @st.dialog("💸 Xərc Çıxart")
                    def staff_expense_dialog():
                        with st.form("staff_exp"):
                            e_cat = st.selectbox("Nə üçün?", ["Kommunal (İşıq/Su)", "Xammal Alışı", "Təmizlik", "Digər"]); e_amt = st.number_input("Məbləğ (AZN)", min_value=0.1); e_desc = st.text_input("Qeyd")
                            if st.form_submit_button("Təsdiqlə"):
                                run_action("INSERT INTO finance (type, category, amount, source, description, created_by) VALUES ('out', :c, :a, 'Kassa', :d, :u)", {"c":e_cat, "a":e_amt, "d":e_desc, "u":st.session_state.user})
                                run_action("INSERT INTO expenses (amount, reason, spender, source) VALUES (:a, :r, :s, 'Kassa')", {"a":e_amt, "r":f"{e_cat} - {e_desc}", "s":st.session_state.user})
                                st.success("Xərc qeydə alındı!"); st.rerun()
                    if st.button("💸 Xərc Çıxart", use_container_width=True): 
                        if st.session_state.show_receipt_popup: st.error("Əvvəl çeki bağlayın!")
                        else: staff_expense_dialog()
                with sc2:
                    btn_lbl = "🔴 Günü Bitir (Z-Hesabat)"
                    if get_setting("z_report_test_mode") == "TRUE": btn_lbl += " [TEST MODE]"
                    if st.button(btn_lbl, type="primary", use_container_width=True): 
                        if st.session_state.show_receipt_popup: st.error("Əvvəl çeki bağlayın!")
                        else:
                            st.session_state.z_report_active = True; st.session_state.z_calculated = False; st.rerun()
                
                if st.session_state.z_report_active and not st.session_state.show_receipt_popup:
                    @st.dialog("📊 GÜNÜN BAĞLANIŞI")
                    def z_report_dialog():
                        st.write("---"); st.write("💸 **GÜNLÜK MAAŞLAR ÖDƏNİLDİ?**")
                        c1, c2 = st.columns(2)
                        pay_staff = c1.checkbox("Staff (20 AZN)", key="z_chk_staff"); pay_manager = c2.checkbox("Manager (25 AZN)", key="z_chk_mgr")
                        st.write("---")
                        if st.button("🧮 HESABLA"): st.session_state.z_calculated = True
                        
                        if st.session_state.z_calculated:
                            now = get_baku_now()
                            if now.hour >= 8: shift_start = now.replace(hour=8, minute=0, second=0, microsecond=0)
                            else: shift_start = (now - datetime.timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
                            sales_cash = run_query("SELECT SUM(total) as s FROM sales WHERE payment_method='Cash' AND created_at >= :d", {"d":shift_start}).iloc[0]['s'] or 0.0
                            exp_cash = run_query("SELECT SUM(amount) as e FROM finance WHERE source='Kassa' AND type='out' AND created_at >= :d", {"d":shift_start}).iloc[0]['e'] or 0.0
                            inc_cash = run_query("SELECT SUM(amount) as i FROM finance WHERE source='Kassa' AND type='in' AND created_at >= :d", {"d":shift_start}).iloc[0]['i'] or 0.0
                            
                            salary_deduction = 0
                            if pay_staff: salary_deduction += 20
                            if pay_manager: salary_deduction += 25
                            
                            start_limit = float(get_setting("cash_limit", "100.0"))
                            current_bal = start_limit + float(sales_cash) + float(inc_cash) - float(exp_cash) - salary_deduction
                            diff = current_bal - start_limit
                            
                            st.markdown(f"**Başlanğıc:** {start_limit:.2f} ₼"); st.markdown(f"**+ Satış (Nəğd):** {float(sales_cash):.2f} ₼")
                            st.markdown(f"**- Maaşlar:** {salary_deduction:.2f} ₼"); st.markdown(f"**- Xərclər (Kassa):** {float(exp_cash):.2f} ₼")
                            st.divider(); st.markdown(f"### KASSADA OLMALIDIR: {current_bal:.2f} ₼")
                            if diff > 0: st.info(f"📥 {diff:.2f} AZN Seyfə qoyulacaq.")
                            elif diff < 0: st.error(f"📤 {abs(diff):.2f} AZN Seyfdən götürüləcək.")
                            st.divider()
                            if st.button("✅ TƏSDİQLƏ VƏ GÜNÜ BAĞLA", type="primary"):
                                if pay_staff: run_action("INSERT INTO finance (type, category, amount, source, description, created_by) VALUES ('out', 'Maaş', 20, 'Kassa', 'Z-Hesabat: Staff', :u)", {"u":st.session_state.user})
                                if pay_manager: run_action("INSERT INTO finance (type, category, amount, source, description, created_by) VALUES ('out', 'Maaş', 25, 'Kassa', 'Z-Hesabat: Manager', :u)", {"u":st.session_state.user})
                                if diff > 0:
                                    run_action("INSERT INTO finance (type, category, amount, source, description, created_by) VALUES ('out', 'İnkassasiya', :a, 'Kassa', 'Z-Hesabat: Seyfə Transfer', :u)", {"a":diff, "u":st.session_state.user})
                                    run_action("INSERT INTO finance (type, category, amount, source, description, created_by) VALUES ('in', 'İnkassasiya', :a, 'Seyf', 'Z-Hesabat: Kassadan Gələn', :u)", {"a":diff, "u":st.session_state.user})
                                elif diff < 0:
                                    needed = abs(diff)
                                    run_action("INSERT INTO finance (type, category, amount, source, description, created_by) VALUES ('in', 'Kassa Tamamlama', :a, 'Kassa', 'Z-Hesabat: Seyfdən Gələn', :u)", {"a":needed, "u":st.session_state.user})
                                    run_action("INSERT INTO finance (type, category, amount, source, description, created_by) VALUES ('out', 'Kassa Tamamlama', :a, 'Seyf', 'Z-Hesabat: Kassaya Gedən', :u)", {"a":needed, "u":st.session_state.user})
                                
                                set_setting("last_z_report_time", get_baku_now().isoformat())
                                log_system(st.session_state.user, f"Z-Hesabat Bağlandı. Qalıq: {current_bal}")
                                st.session_state.z_report_active = False; st.session_state.z_calculated = False; st.success("Gün Uğurla Bağlandı! 🎉"); time.sleep(2); st.rerun()
                    z_report_dialog()

                st.divider(); st.markdown("### 🔍 Mənim Satışlarım")
                c1, c2 = st.columns(2); 
                d1 = c1.date_input("Start", datetime.date.today(), key="staff_date_start"); 
                d2 = c2.date_input("End", datetime.date.today(), key="staff_date_end"); 
                ts_start = datetime.datetime.combine(d1, datetime.time(0,0)); ts_end = datetime.datetime.combine(d2, datetime.time(23,59))
                
                q_staff = """SELECT s.created_at AS "Tarix", s.items AS "Mallar", s.original_total AS "Məbləğ (Endirimsiz)", s.discount_amount AS "Endirim", s.total AS "Yekun", s.payment_method AS "Ödəniş", s.customer_card_id AS "Müştəri ID" FROM sales s WHERE s.cashier = :u AND s.created_at BETWEEN :s AND :e ORDER BY s.created_at DESC"""
                mys = run_query(q_staff, {"u":st.session_state.user, "s":ts_start, "e":ts_end})
                total_sales = mys['Yekun'].sum() if not mys.empty else 0.0
                st.metric(f"Seçilən Tarix Üzrə Cəm", f"{total_sales:.2f} ₼")
                st.dataframe(mys, hide_index=True, use_container_width=True)

    st.markdown(f"<div class='footer'>Ironwaves POS {VERSION} | © 2026</div>", unsafe_allow_html=True)
