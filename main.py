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
# === IronWaves.Store POS - V6.0 (STABLE) ===
# ==========================================

VERSION = "v6.0 DEMO (Reorganized & Stable)"
BRAND_NAME = "IronWaves.Store POS (DEMO REJİMİ)"

# --- CONFIG ---
st.set_page_config(page_title=BRAND_NAME, page_icon="🧪", layout="wide", initial_sidebar_state="collapsed")
ADMIN_DEFAULT_PASS = os.environ.get("ADMIN_PASS", "admin123")

# --- CONSTANTS ---
DEFAULT_TERMS = """
<div style="font-family: 'Arial', sans-serif; color: #333; line-height: 1.6; font-size: 14px;">
    <h4 style="color: #D32F2F; border-bottom: 2px solid #D32F2F; padding-bottom: 10px; margin-top: 0;">
        🧪 DEMO REJİMİ
    </h4>
    <p>Bu sistem test məqsədlidir.</p>
</div>
"""
CARTOON_QUOTES = ["Bu gün sənin günündür! 🚀", "Qəhrəman kimi parılda! ⭐", "Bir fincan kofe = Xoşbəxtlik! ☕"]
SUBJECTS = ["Admin", "Abbas (Manager)", "Nicat (Investor)", "Elvin (Investor)", "Təchizatçı", "Digər"]
PRESET_CATEGORIES = ["Kofe (Dənələr)", "Süd Məhsulları", "Bar Məhsulları (Su/Buz)", "Siroplar", "Soslar", "Qablaşdırma", "Şirniyyat", "İçkilər", "Meyvə", "Təsərrüfat"]

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
def clear_customer_data(): st.session_state.current_customer_ta = None
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
            if new_count >= 5: blocked_until = now + datetime.timedelta(minutes=5)
            run_action("UPDATE failed_logins SET attempt_count=:c, last_attempt=:t, blocked_until=:b WHERE username=:u", {"c":new_count, "t":now, "b":blocked_until, "u":username})
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

def get_receipt_html_string(cart, total):
    store = get_setting("receipt_store_name", BRAND_NAME)
    addr = get_setting("receipt_address", "Bakı, Azərbaycan")
    phone = get_setting("receipt_phone", "+994 50 000 00 00")
    foot = get_setting("receipt_footer", "TƏŞƏKKÜRLƏR!")
    logo = get_setting("receipt_logo_base64")
    time_str = get_baku_now().strftime('%d/%m/%Y %H:%M')
    img_tag = f'<div style="text-align:center;"><img src="data:image/png;base64,{logo}" class="rec-logo" style="width:80px;filter:grayscale(100%);"></div>' if logo else ""
    html = f"""<div style="font-family:'Courier New', monospace; color:black; background:white; padding:15px; border:1px solid #eee; width:300px; margin:0 auto;">{img_tag}<div style="text-align:center; font-weight:bold; font-size:16px; margin-bottom:5px; text-transform:uppercase;">SATIŞ ÇEKİ<br>{store}</div><div style="text-align:center; font-size:12px; margin-bottom:10px;">{addr}<br>Tel: {phone}</div><div style="border-bottom:1px dashed black; margin:10px 0;"></div><div style="text-align:center; font-size:12px;">{time_str}</div><div style="border-bottom:1px dashed black; margin:10px 0;"></div><table style="width:100%; border-collapse:collapse; font-size:12px; text-align:left;"><tr><th style="padding-bottom:5px; border-bottom:1px dashed black; width:15%;">SAY</th><th style="padding-bottom:5px; border-bottom:1px dashed black; width:55%;">MƏHSUL</th><th style="padding-bottom:5px; border-bottom:1px dashed black; width:30%; text-align:right;">MƏBLƏĞ</th></tr>"""
    for i in cart: html += f"""<tr><td style="padding:5px 0;">{int(i['qty'])}</td><td style="padding:5px 0;">{i['item_name']}</td><td style="padding:5px 0; text-align:right;">{i['qty']*i['price']:.2f} ₼</td></tr>"""
    html += f"""</table><div style="border-bottom:1px dashed black; margin:10px 0;"></div><div style="display:flex; justify-content:space-between; font-weight:bold; font-size:16px;"><span>YEKUN</span><span>{total:.2f} ₼</span></div><div style="border-bottom:1px dashed black; margin:10px 0;"></div><div style="text-align:center; margin-top:20px; font-size:12px; font-weight:bold;">{foot}</div></div>"""
    return html

# ==========================================
# === UI RENDER FUNCTIONS (TOP LEVEL) ===
# ==========================================
@st.dialog("Ödəniş & Çek")
def show_receipt_dialog(cart_data, total_amt, cust_email):
    html_content = get_receipt_html_string(cart_data, total_amt)
    components.html(html_content, height=500, scrolling=True)
    st.markdown(f'<div id="hidden-print-area">{html_content}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: components.html(f"""<button onclick="window.print()" style="background-color:#2E7D32; color:white; padding:12px 24px; border:none; border-radius:8px; font-weight:bold; font-size:16px; cursor:pointer; width:100%; font-family:sans-serif;">🖨️ ÇAP ET</button>""", height=60)
    with c2:
        if cust_email:
            if st.button("📧 Email Göndər", use_container_width=True):
                res = send_email(cust_email, "Sizin Çekiniz", html_content)
                if res == "OK": st.success("Göndərildi!")
                else: st.error(f"Xəta: {res}")
        else: st.caption("⛔ Email yoxdur")
    if st.button("❌ Bağla", use_container_width=True):
        st.session_state.show_receipt_popup = False; st.session_state.last_receipt_data = None; st.rerun()

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

@st.dialog("Auth")
def admin_auth_dialog(item_idx=None, sale_to_delete=None):
    st.warning("Admin/Manager Approval"); reason = st.text_input("Reason"); pin = st.text_input("PIN", type="password")
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
                log_system(st.session_state.user, f"Deleted Sale #{sale_to_delete}. Reason: {reason}"); st.success("Deleted!"); st.rerun()
            else: 
                item = st.session_state.cart_table[item_idx]
                run_action("INSERT INTO void_logs (item_name, qty, reason, deleted_by, created_at) VALUES (:n, :q, :r, :u, :t)", {"n":item['item_name'], "q":item['qty'], "r":reason, "u":f"{st.session_state.user} ({approver_role})", "t":get_baku_now()})
                st.session_state.cart_table.pop(item_idx)
                run_action("UPDATE tables SET items=:i WHERE id=:id", {"i":json.dumps(st.session_state.cart_table), "id":st.session_state.selected_table['id']})
                st.success("Voided!"); st.rerun()
        else: st.error("Invalid PIN")

def add_to_cart(cart_ref, item):
    try: r = run_query("SELECT printer_target, price_half FROM menu WHERE item_name=:n", {"n":item['item_name']}).iloc[0]; item['printer_target'] = r['printer_target']; item['price_half'] = float(r['price_half']) if r['price_half'] else None
    except: item['printer_target'] = 'kitchen'; item['price_half'] = None
    for ex in cart_ref:
        if ex['item_name'] == item['item_name'] and ex.get('status') == 'new' and ex.get('qty') % 1 == 0: ex['qty'] += 1; return
    cart_ref.append(item)

def render_menu_grid(cart_ref, key_prefix):
    low_stock = get_low_stock_map()
    cats = run_query("SELECT DISTINCT category FROM menu WHERE is_active=TRUE")
    cat_list = ["Hamısı"] + sorted(cats['category'].tolist()) if not cats.empty else ["Hamısı"]
    sc = st.radio("Kataloq", cat_list, horizontal=True, label_visibility="collapsed", key=f"cat_{key_prefix}")
    sql = "SELECT id, item_name, price, is_coffee FROM menu WHERE is_active=TRUE"; p = {}
    if sc != "Hamısı": sql += " AND category=:c"; p["c"] = sc
    sql += " ORDER BY price ASC"; prods = run_query(sql, p)
    if not prods.empty:
        gr = {}
        for _, r in prods.iterrows():
            n = r['item_name']; pts = n.split(); base = n
            if len(pts)>1 and pts[-1] in ['S','M','L','XL','Single','Double']: base = " ".join(pts[:-1]); gr.setdefault(base, []).append(r)
            else: gr[n] = [r]
        cols = st.columns(4); i=0
        @st.dialog("Seçim")
        def show_v(bn, its):
            for it in its:
                marker = " 🟡" if it['item_name'] in low_stock else ""
                if st.button(f"{it['item_name'].replace(bn,'').strip()}{marker}\n{it['price']} ₼", key=f"v_{it['id']}_{key_prefix}", use_container_width=True):
                    add_to_cart(cart_ref, {'item_name':it['item_name'], 'price':float(it['price']), 'qty':1, 'is_coffee':it['is_coffee'], 'status':'new'}); st.rerun()
        for bn, its in gr.items():
            with cols[i%4]:
                marker = " 🟡" if any(x['item_name'] in low_stock for x in its) else ""
                if len(its)>1:
                    if st.button(f"{bn}{marker}\n(Seçim)", key=f"g_{bn}_{key_prefix}", use_container_width=True): show_v(bn, its)
                else:
                    it = its[0]
                    if st.button(f"{it['item_name']}{marker}\n{it['price']} ₼", key=f"s_{it['id']}_{key_prefix}", use_container_width=True):
                        add_to_cart(cart_ref, {'item_name':it['item_name'], 'price':float(it['price']), 'qty':1, 'is_coffee':it['is_coffee'], 'status':'new'}); st.rerun()
            i+=1

def render_takeaway():
    c1, c2 = st.columns([1.5, 3])
    with c1:
        st.info("🧾 Al-Apar Çek")
        with st.form("sc_ta", clear_on_submit=True):
            ci, cb = st.columns([3,1]); qv = ci.text_input("Müştəri", label_visibility="collapsed", placeholder="Skan...", key="ta_inp"); 
            if cb.form_submit_button("🔍") or qv:
                try: 
                    cid = qv.strip().split("id=")[1].split("&")[0] if "id=" in qv else qv.strip()
                    r = run_query("SELECT * FROM customers WHERE card_id=:id", {"id":cid})
                    if not r.empty: st.session_state.current_customer_ta = r.iloc[0].to_dict(); st.toast(f"✅ Müştəri Tanındı: {cid}"); st.rerun()
                    else: st.error("Tapılmadı")
                except: pass
        if st.session_state.current_customer_ta:
            c = st.session_state.current_customer_ta
            st.markdown(f"<div style='padding:10px; border:1px solid #ddd; border-radius:10px; margin-bottom:10px;'>👤 <b>{c['card_id']}</b><br>⭐ {c['stars']}</div>", unsafe_allow_html=True)
            if st.button("Ləğv Et", key="ta_cl"): st.session_state.current_customer_ta=None; st.rerun()
        
        raw_total, final_total, _, free_count, _, _, is_ikram = calculate_smart_total(st.session_state.cart_takeaway, st.session_state.current_customer_ta, is_table=False)
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
        
        st.markdown(f"<h3 style='text-align:right; color:#777; text-decoration: line-through;'>{raw_total:.2f} ₼</h3>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:right; color:#E65100'>{final_total:.2f} ₼</h2>", unsafe_allow_html=True)
        if free_count > 0: st.success(f"🎁 {free_count} Kofe HƏDİYYƏ!")

        pm = st.radio("Metod", ["Nəğd", "Kart"], horizontal=True, key="pm_ta")
        if st.button("✅ ÖDƏNİŞ ET", type="primary", use_container_width=True, key="pay_ta"):
            if not st.session_state.cart_takeaway: st.error("Boşdur!"); st.stop()
            try:
                istr = ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart_takeaway])
                cust_id = st.session_state.current_customer_ta['card_id'] if st.session_state.current_customer_ta else None
                cust_email = st.session_state.current_customer_ta['email'] if st.session_state.current_customer_ta else None
                
                run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at, customer_card_id) VALUES (:i,:t,:p,:c,:time, :cid)", 
                           {"i":istr,"t":final_total,"p":("Cash" if pm=="Nəğd" else "Card"),"c":st.session_state.user, "time":get_baku_now(), "cid":cust_id})
                
                with conn.session as s:
                    for it in st.session_state.cart_takeaway:
                        rs = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m"), {"m":it['item_name']}).fetchall()
                        for r in rs: s.execute(text("UPDATE ingredients SET stock_qty=stock_qty-:q WHERE name=:n"), {"q":float(r[1])*it['qty'], "n":r[0]})
                    if st.session_state.current_customer_ta:
                        new_stars_balance = (st.session_state.current_customer_ta['stars'] + sum([item['qty'] for item in st.session_state.cart_takeaway if item.get('is_coffee')])) - (free_count * 10)
                        s.execute(text("UPDATE customers SET stars=:s WHERE card_id=:id"), {"s":new_stars_balance, "id":cust_id})
                    s.commit()
                
                st.session_state.last_receipt_data = {'cart': st.session_state.cart_takeaway.copy(), 'total': final_total, 'email': cust_email}
                st.session_state.show_receipt_popup = True
                st.session_state.cart_takeaway = []
                clear_customer_data()
                st.rerun()
            except Exception as e: st.error(str(e))
    with c2: render_menu_grid(st.session_state.cart_takeaway, "ta")

def render_tables_main():
    if st.session_state.selected_table: 
        tbl = st.session_state.selected_table
        c_back, c_trans = st.columns([3, 1])
        if c_back.button("⬅️ Masalara Qayıt", key="back_tbl", use_container_width=True, type="secondary"): st.session_state.selected_table = None; st.session_state.cart_table = []; st.rerun()
        st.markdown(f"### 📝 Sifariş: {tbl['label']}")
        c1, c2 = st.columns([1.5, 3])
        with c1:
            st.info("Masa Sifarişi"); db_cust_id = tbl.get('active_customer_id')
            if db_cust_id and not st.session_state.current_customer_tb:
                 r = run_query("SELECT * FROM customers WHERE card_id=:id", {"id":db_cust_id})
                 if not r.empty: st.session_state.current_customer_tb = r.iloc[0].to_dict()
            if st.session_state.current_customer_tb:
                c = st.session_state.current_customer_tb; st.success(f"👤 {c['card_id']} | ⭐ {c['stars']}")
                
            raw_total, final_total, _, _, _, serv_chg, _ = calculate_smart_total(st.session_state.cart_table, st.session_state.current_customer_tb, is_table=True)
            if st.session_state.cart_table:
                for i, it in enumerate(st.session_state.cart_table):
                    status = it.get('status', 'new'); bg_col = "#e3f2fd" if status == 'sent' else "white"
                    st.markdown(f"<div style='background:{bg_col};padding:10px;margin-bottom:5px;border-radius:8px;display:flex;justify-content:space-between;align-items:center;border:1px solid #ddd;'><div style='flex:2'><b>{it['item_name']}</b></div><div style='flex:1'>{it['price']}</div><div style='flex:1;color:#E65100'>x{it['qty']}</div><div style='flex:1;text-align:right'>{it['qty']*it['price']:.1f}</div></div>", unsafe_allow_html=True)
                    b1,b2,b3=st.columns([1,1,1])
                    with b1:
                        st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                        if st.button("➖", key=f"m_tb_{i}"): 
                            if status != 'sent': st.session_state.cart_table.pop(i); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with b2:
                        st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                        if st.button("➕", key=f"p_tb_{i}"): it['qty']+=1; st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align:right; color:#777; text-decoration: line-through;'>{raw_total:.2f} ₼</h3>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align:right; color:#E65100'>{final_total:.2f} ₼</h2>", unsafe_allow_html=True)
            if serv_chg > 0: st.caption(f"ℹ️ Servis Haqqı (7%): {serv_chg:.2f} ₼ daxildir")
            col_s, col_p = st.columns(2)
            if col_s.button("🔥 MƏTBƏXƏ GÖNDƏR", key="save_tbl", use_container_width=True):
                for x in st.session_state.cart_table: x['status'] = 'sent'
                run_action("UPDATE tables SET is_occupied=TRUE, items=:i, total=:t WHERE id=:id", {"i":json.dumps(st.session_state.cart_table), "t":final_total, "id":tbl['id']}); st.success("Göndərildi!"); time.sleep(1); st.rerun()
            if col_p.button("✅ ÖDƏNİŞ ET", key="pay_tbl", type="primary", use_container_width=True):
                if not st.session_state.cart_table: st.error("Boşdur!"); st.stop()
                run_action("UPDATE tables SET is_occupied=FALSE, items='[]', total=0, active_customer_id=NULL WHERE id=:id", {"id":tbl['id']}); 
                
                cust_email = st.session_state.current_customer_tb['email'] if st.session_state.current_customer_tb else None
                st.session_state.last_receipt_data = {'cart': st.session_state.cart_table.copy(), 'total': final_total, 'email': cust_email}
                st.session_state.show_receipt_popup = True
                st.session_state.selected_table = None; st.session_state.cart_table = [] 
                st.rerun()

        with c2: render_menu_grid(st.session_state.cart_table, "tb")
    else: 
        if st.session_state.role in ['admin', 'manager']:
            with st.expander("🛠️ Masa İdarəetməsi"):
                n_l = st.text_input("Masa Adı"); 
                if st.button("➕ Yarat"): run_action("INSERT INTO tables (label) VALUES (:l)", {"l":n_l}); st.rerun()
                d_l = st.selectbox("Silinəcək", run_query("SELECT label FROM tables")['label'].tolist() if not run_query("SELECT label FROM tables").empty else [])
                if st.button("❌ Sil"): run_action("DELETE FROM tables WHERE label=:l", {"l":d_l}); st.rerun()
        st.markdown("### 🍽️ ZAL PLAN")
        tables = run_query("SELECT * FROM tables ORDER BY id"); cols = st.columns(3)
        for idx, row in tables.iterrows():
            with cols[idx % 3]:
                if st.button(f"{row['label']}\n\n{row['total']} ₼", key=f"tbl_btn_{row['id']}", use_container_width=True, type="primary" if row['is_occupied'] else "secondary"):
                    items = json.loads(row['items']) if row['items'] else []
                    st.session_state.selected_table = row.to_dict(); st.session_state.cart_table = items; st.rerun()

# ==========================================
# === MAIN APP ===
# ==========================================

# --- CHECK FOR RECEIPT POPUP ON RERUN ---
if st.session_state.show_receipt_popup and st.session_state.last_receipt_data:
    show_receipt_dialog(st.session_state.last_receipt_data['cart'], 
                        st.session_state.last_receipt_data['total'], 
                        st.session_state.last_receipt_data['email'])

# --- LOGGED OUT STATE ---
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        # CUSTOMER QR LOGIC IN LOGGED OUT STATE
        qp = st.query_params
        if "id" in qp:
            card_id = qp["id"]; token = qp.get("t")
            c_head, c_logo, _ = st.columns([1,2,1]); logo_b64 = get_setting("receipt_logo_base64")
            with c_logo:
                if logo_b64: st.markdown(f'<div style="text-align:center; margin-bottom:10px;"><img src="data:image/png;base64,{logo_b64}" width="160"></div>', unsafe_allow_html=True)
                else: st.markdown(f"<h1 style='text-align:center; color:#D32F2F'>{BRAND_NAME}</h1>", unsafe_allow_html=True)
            
            st.markdown("""<style>.stApp { background-color: #FFFFFF !important; } h1, h2, h3, h4, h5, h6, p, div, span, label, li { color: #000000 !important; }</style>""", unsafe_allow_html=True)
            
            try: df = run_query("SELECT * FROM customers WHERE card_id = :id", {"id": card_id})
            except: st.stop()
            if not df.empty:
                user = df.iloc[0]
                if user['secret_token'] and token and user['secret_token'] != token: st.warning("⚠️ QR kod köhnəlib.")
                st.markdown(f"<div class='cartoon-quote'>{random.choice(CARTOON_QUOTES)}</div>", unsafe_allow_html=True)
                
                if not user['is_active']:
                    st.info("🎉 Xoş Gəldiniz!")
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

                st.markdown(f"""<div class="stamp-container"><div class="stamp-card" style="border-color: {border_col}; color: {border_col}; box-shadow: 0 0 0 4px white, 0 0 0 7px {border_col};"><div class="stamp-title">{st_label}</div><div>{disc_txt}</div><div class="stamp-stars">{user['stars']} / 10</div><div class="stamp-footer">ULDUZ BALANSI</div></div></div>""", unsafe_allow_html=True)
                
                # GREEN CUPS GRID
                html = '<div class="coffee-grid-container">'
                for i in range(10):
                    icon = "https://cdn-icons-png.flaticon.com/512/751/751621.png"
                    if i < user['stars']:
                        if i == 9: html += f'<img src="{icon}" class="cup-earned cup-anim">'
                        else: html += f'<img src="{icon}" class="cup-earned coffee-icon-img">'
                    else: html += f'<img src="{icon}" class="cup-empty coffee-icon-img">'
                st.markdown(html + '</div>', unsafe_allow_html=True)
                if user['stars'] >= 10: st.balloons()
                
                # FEEDBACK
                st.markdown('<div class="feedback-container"><div class="feedback-title">RƏYİNİZ BİZİM ÜÇÜN ÖNƏMLİDİR</div>', unsafe_allow_html=True)
                with st.form("feed"):
                    s = st.feedback("stars"); m = st.text_input("Şərhiniz", key="feed_msg", placeholder="Fikirlərinizi yazın...")
                    if st.form_submit_button("Göndər") and s:
                        run_action("INSERT INTO feedbacks (card_id, rating, comment, created_at) VALUES (:i,:r,:m, :t)", {"i":card_id, "r":s+1, "m":m, "t":get_baku_now()}); st.success("Təşəkkürlər!")
                st.markdown('</div>', unsafe_allow_html=True)
                st.stop()

        # LOGIN TABS
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
                    if not found: st.error("Səhv PIN"); time.sleep(2)
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
                    else: register_failed_login(u); st.error("Səhv"); time.sleep(2)

# --- LOGGED IN STATE ---
else:
    if not validate_session(): st.session_state.logged_in=False; st.session_state.session_token=None; st.error("Sessiya bitib."); st.rerun()

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
    if role in ['admin', 'manager', 'staff']: tabs_list.append("🏃‍♂️ AL-APAR")
    if role == 'admin' or (role == 'manager' and get_setting("manager_show_tables", "TRUE") == "TRUE") or (role == 'staff' and get_setting("staff_show_tables", "TRUE") == "TRUE"): tabs_list.append("🍽️ MASALAR")
    if role in ['admin', 'manager']: tabs_list.extend(["💰 Maliyyə", "📦 Anbar", "📊 Analitika", "📜 Loglar", "👥 CRM"])
    if role == 'manager':
         if get_setting("manager_perm_menu", "FALSE") == "TRUE": tabs_list.append("📋 Menyu")
         if get_setting("manager_perm_recipes", "FALSE") == "TRUE": tabs_list.append("📜 Resept")
    if role == 'admin':
        if "📋 Menyu" not in tabs_list: tabs_list.append("📋 Menyu")
        if "📜 Resept" not in tabs_list: tabs_list.append("📜 Resept")
        tabs_list.extend(["📝 Qeydlər", "⚙️ Ayarlar", "💾 Baza", "QR"])
    if role in ['staff', 'manager']: tabs_list.append("📊 Z-Hesabat")

    my_tabs = st.tabs(tabs_list)
    tab_map = {name: tab for name, tab in zip(tabs_list, my_tabs)}

    if "🏃‍♂️ AL-APAR" in tab_map:
        with tab_map["🏃‍♂️ AL-APAR"]: render_takeaway()

    if "🍽️ MASALAR" in tab_map:
        with tab_map["🍽️ MASALAR"]: render_tables_main()

    if "📦 Anbar" in tab_map:
        with tab_map["📦 Anbar"]:
            st.subheader("📦 Anbar İdarəetməsi")
            if role == 'admin' or role == 'manager':
                with st.expander("➕ Mədaxil / Yeni Mal", expanded=False):
                     with st.form("smart_add_item", clear_on_submit=True):
                        c1, c2, c3 = st.columns(3)
                        mn_name = c1.text_input("Malın Adı (Məs: Dom Qaymaq)")
                        sel_cat = c2.selectbox("Kateqoriya", PRESET_CATEGORIES + ["➕ Yeni Yarat..."])
                        mn_unit = c3.selectbox("Əsas Vahid (Resept üçün)", ["L", "KQ", "ƏDƏD"])
                        mn_cat_final = sel_cat
                        if sel_cat == "➕ Yeni Yarat...": mn_cat_final = st.text_input("Yeni Kateqoriya Adı")
                        st.write("---")
                        c4, c5, c6 = st.columns(3)
                        pack_size = c4.number_input("Aldığın Qabın Həcmi/Çəkisi", min_value=0.001, step=0.001)
                        pack_price = c5.number_input("Aldığın Qabın Qiyməti (AZN)", min_value=0.01, step=0.01)
                        pack_count = c6.number_input("Neçə ədəd/qutu almısan?", min_value=0.0, step=0.5, value=1.0)
                        mn_type = st.selectbox("Növ", ["ingredient", "consumable"], index=0)
                        if st.form_submit_button("Hesabla və Yarat / Artır"):
                             if mn_name and pack_size > 0:
                                 calc_unit_cost = pack_price / pack_size 
                                 total_stock_add = pack_size * pack_count 
                                 run_action("INSERT INTO ingredients (name, stock_qty, unit, category, type, unit_cost, approx_count) VALUES (:n, :q, :u, :c, :t, :uc, 1) ON CONFLICT (name) DO UPDATE SET stock_qty = ingredients.stock_qty + :q, unit_cost = :uc", {"n":mn_name, "q":total_stock_add, "u":mn_unit, "c":mn_cat_final, "t":mn_type, "uc":calc_unit_cost})
                                 st.success(f"✅ {mn_name} stoka əlavə olundu!"); time.sleep(2); st.rerun()

            c1, c2 = st.columns([3,1])
            search_query = st.text_input("🔍 Axtarış...", placeholder="Malın adı...")
            sql = "SELECT * FROM ingredients" + (f" WHERE name ILIKE '%{search_query}%'" if search_query else "") + " ORDER BY name"
            df_i = run_query(sql)
            
            rows_per_page = st.selectbox("Səhifədə neçə mal olsun?", [20, 40, 60], index=0)
            if rows_per_page != st.session_state.anbar_rows_per_page: st.session_state.anbar_rows_per_page = rows_per_page; st.session_state.anbar_page = 0
            total_rows = len(df_i); total_pages = math.ceil(total_rows / rows_per_page); start_idx = st.session_state.anbar_page * rows_per_page; end_idx = start_idx + rows_per_page
            df_page = df_i.iloc[start_idx:end_idx].copy()
            
            if role == 'manager':
                st.dataframe(df_page[['id', 'name', 'stock_qty', 'unit', 'category']], hide_index=True, use_container_width=True)
            else:
                df_page['Total Value'] = df_page['stock_qty'] * df_page['unit_cost']
                df_page.insert(0, "Seç", False)
                edited_df = st.data_editor(df_page, hide_index=True, column_config={"Seç": st.column_config.CheckboxColumn(required=True)}, disabled=["id", "name", "stock_qty", "unit", "unit_cost", "approx_count", "category", "Total Value", "type"], use_container_width=True, key="anbar_editor")
                sel_ids = edited_df[edited_df["Seç"]]['id'].tolist()
                st.divider(); ab1, ab2, ab3 = st.columns(3)
                with ab1:
                    if len(sel_ids) == 1 and st.button("➕ Seçilənə Mədaxil", use_container_width=True, type="secondary"): st.session_state.restock_item_id = int(sel_ids[0]); st.rerun()
                with ab2:
                    if len(sel_ids) == 1 and st.button("✏️ Seçilənə Düzəliş", use_container_width=True, type="secondary"): st.session_state.edit_item_id = int(sel_ids[0]); st.rerun()
                with ab3:
                    if len(sel_ids) > 0 and st.button(f"🗑️ Sil ({len(sel_ids)})", use_container_width=True, type="primary"): 
                         for i in sel_ids: run_action("DELETE FROM ingredients WHERE id=:id", {"id":int(i)})
                         st.success("Silindi!"); time.sleep(1); st.rerun()

            pc1, pc2, pc3 = st.columns([1,2,1])
            with pc1: 
                if st.button("⬅️ Əvvəlki", disabled=(st.session_state.anbar_page == 0)): st.session_state.anbar_page -= 1; st.rerun()
            with pc2: st.markdown(f"<div style='text-align:center; padding-top:10px;'>Səhifə {st.session_state.anbar_page + 1} / {max(1, total_pages)}</div>", unsafe_allow_html=True)
            with pc3: 
                if st.button("Növbəti ➡️", disabled=(st.session_state.anbar_page >= total_pages - 1)): st.session_state.anbar_page += 1; st.rerun()

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
                            ec = st.selectbox("Kateqoriya", PRESET_CATEGORIES + ["➕ Yeni Yarat..."], index=0); 
                            eu = st.selectbox("Vahid", ["KQ", "L", "ƏDƏD"], index=["KQ", "L", "ƏDƏD"].index(r['unit']) if r['unit'] in ["KQ", "L", "ƏDƏD"] else 0); et = st.selectbox("Növ", ["ingredient","consumable"], index=0 if r['type']=='ingredient' else 1); ecost = st.number_input("Maya Dəyəri", value=float(r['unit_cost']), format="%.5f")
                            if ec == "➕ Yeni Yarat...": ec = st.text_input("Yeni Kateqoriya Adı")
                            if st.form_submit_button("Yadda Saxla"):
                                run_action("UPDATE ingredients SET name=:n, category=:c, unit=:u, unit_cost=:uc, type=:t WHERE id=:id", {"n":en, "c":ec, "u":eu, "uc":ecost, "t":et, "id":int(r['id'])}); log_system(st.session_state.user, f"Düzəliş: {en}"); st.session_state.edit_item_id = None; st.rerun()
                    show_edit(row)

    if "💰 Maliyyə" in tab_map:
        with tab_map["💰 Maliyyə"]:
            st.subheader("💰 Maliyyə Mərkəzi")
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
                st.metric("🏪 Kassa (Cibdə)", f"{disp_cash:.2f} ₼"); st.metric("💳 Bank Kartı (Növbə)", f"{disp_card:.2f} ₼")
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
                
                st.metric("🏪 Kassa (Cibdə)", f"{disp_cash:.2f} ₼"); st.metric("💳 Bank Kartı (Ümumi)", f"{disp_card:.2f} ₼")

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

    if "📊 Analitika" in tab_map:
        with tab_map["📊 Analitika"]:
            render_analytics(role='admin' if role=='admin' else 'manager')

    st.markdown(f"<div class='footer'>Ironwaves POS {VERSION} | © 2026</div>", unsafe_allow_html=True)
