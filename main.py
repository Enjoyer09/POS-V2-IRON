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
# === EMALATKHANA POS - V4.9.1 (FIXED BACKUP) ===
# ==========================================

VERSION = "v4.9.1 DEMO (Fixed)"
BRAND_NAME = "Emalatkhana (TEST REJİMİ)" # Vizual xəbərdarlıq

# --- INFRA ---
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
# DEMO DOMAIN
DOMAIN = "demo.ironwaves.store" 
APP_URL = f"https://{DOMAIN}"
DEFAULT_SENDER_EMAIL = "info@ironwaves.store" 

# --- CONFIG ---
st.set_page_config(page_title=BRAND_NAME, page_icon="🧪", layout="wide", initial_sidebar_state="collapsed")

# --- INIT STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart_takeaway' not in st.session_state: st.session_state.cart_takeaway = []
if 'cart_table' not in st.session_state: st.session_state.cart_table = []
if 'current_customer_ta' not in st.session_state: st.session_state.current_customer_ta = None
if 'current_customer_tb' not in st.session_state: st.session_state.current_customer_tb = None
if 'last_sale' not in st.session_state: st.session_state.last_sale = None
if 'selected_table' not in st.session_state: st.session_state.selected_table = None
if 'selected_recipe_product' not in st.session_state: st.session_state.selected_recipe_product = None

# --- CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Courier+Prime&display=swap');

    .stApp { font-family: 'Oswald', sans-serif !important; background-color: #F4F6F9; }
    header, #MainMenu, footer, [data-testid="stSidebar"] { display: none !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
    
    /* DEMO SPECIFIC HEADER COLOR */
    h1 { color: #D32F2F !important; } 

    button[data-baseweb="tab"] {
        font-family: 'Oswald', sans-serif !important; font-size: 18px !important; font-weight: 700 !important;
        background-color: white !important; border: 2px solid #FFCCBC !important; border-radius: 12px !important;
        margin: 0 4px !important; color: #555 !important; flex-grow: 1;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #FF6B35, #FF8C00) !important; border-color: #FF6B35 !important; color: white !important;
        box-shadow: 0 4px 12px rgba(255, 107, 53, 0.4);
    }
    
    div[data-testid="stRadio"] > label { display: none !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] { flex-direction: row; flex-wrap: wrap; gap: 8px; }
    div[data-testid="stRadio"] label[data-baseweb="radio"] { 
        background: white; border: 1px solid #ddd; padding: 5px 15px; border-radius: 20px; 
        font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s;
    }
    div[data-testid="stRadio"] label[aria-checked="true"] {
        background: #D32F2F; color: white; border-color: #D32F2F;
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

# --- SCHEMA (CACHED) ---
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
    payload = {"from": f"{BRAND_NAME} <{DEFAULT_SENDER_EMAIL}>", "to": [to_email], "subject": subject, "html": body}
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
    
    sql = "SELECT id, item_name, price, is_coffee FROM menu WHERE is_active=TRUE"
    p = {}
    if sc != "Hamısı": 
        sql += " AND category=:c"
        p["c"] = sc
    sql += " ORDER BY price ASC"
    
    prods = run_query(sql, p)

    if not prods.empty:
        gr = {}
        for _, r in prods.iterrows():
            n = r['item_name']; pts = n.split()
            if len(pts)>1 and pts[-1] in ['S','M','L','XL','Single','Double']: base = " ".join(pts[:-1]); gr.setdefault(base, []).append(r)
            else: gr[n] = [r]
        cols = st.columns(4); i=0
        @st.dialog("Ölçü Seçimi")
        def show_v(bn, its):
            st.write(f"### {bn}")
            for it in its:
                if st.button(f"{it['item_name'].replace(bn,'').strip()}\n{it['price']} ₼", key=f"v_{it['id']}_{key_prefix}", use_container_width=True):
                    add_to_cart(cart_ref, {'item_name':it['item_name'], 'price':float(it['price']), 'qty':1, 'is_coffee':it['is_coffee'], 'status':'new'}); st.rerun()
        for bn, its in gr.items():
            with cols[i%4]:
                if len(its)>1:
                    if st.button(f"{bn}\n(Seçim)", key=f"g_{bn}_{key_prefix}", use_container_width=True): show_v(bn, its)
                else:
                    it = its[0]
                    if st.button(f"{it['item_name']}\n{it['price']} ₼", key=f"s_{it['id']}_{key_prefix}", use_container_width=True):
                        add_to_cart(cart_ref, {'item_name':it['item_name'], 'price':float(it['price']), 'qty':1, 'is_coffee':it['is_coffee'], 'status':'new'}); st.rerun()
            i+=1

def render_takeaway():
    c1, c2 = st.columns([1.5, 3])
    with c1:
        st.info("🧾 Al-Apar Çek")
        with st.form("sc_ta", clear_on_submit=True):
            ci, cb = st.columns([3,1]); qv = ci.text_input("Müştəri", label_visibility="collapsed", placeholder="Skan..."); 
            if cb.form_submit_button("🔍") or qv:
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

        pm = st.radio("Metod", ["Nəğd", "Kart"], horizontal=True, key="pm_ta")
        if st.button("✅ ÖDƏNİŞ ET", type="primary", use_container_width=True, key="pay_ta"):
            if not st.session_state.cart_takeaway: st.error("Boşdur!"); st.stop()
            try:
                istr = ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart_takeaway])
                cust_id = st.session_state.current_customer_ta['card_id'] if st.session_state.current_customer_ta else None
                cust_email = st.session_state.current_customer_ta.get('email') if st.session_state.current_customer_ta else None
                run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at, customer_card_id) VALUES (:i,:t,:p,:c,:time, :cid)", 
                           {"i":istr,"t":final_total,"p":("Cash" if pm=="Nəğd" else "Card"),"c":st.session_state.user, "time":get_baku_now(), "cid":cust_id})
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
                if st.button("➕ Yarat", key="add_table_btn"): 
                    run_action("INSERT INTO tables (label) VALUES (:l)", {"l":new_l})
                    log_system(st.session_state.user, f"Created Table: {new_l}")
                    st.rerun()
            with c_del:
                tabs = run_query("SELECT label FROM tables")
                d_l = st.selectbox("Silinəcək", tabs['label'].tolist() if not tabs.empty else [], key="del_table_select")
                if st.button("❌ Sil", key="del_table_btn"): 
                    run_action("DELETE FROM tables WHERE label=:l", {"l":d_l})
                    log_system(st.session_state.user, f"Deleted Table: {d_l}")
                    st.rerun()
    st.markdown("### 🍽️ ZAL PLAN")
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
                if has_unsent: label_extra = "\n🟡 Sifariş Yığılır"
                else: label_extra = "\n🔴 Hazırlanır"
            
            label = f"{row['label']}\n{row['total']} ₼{label_extra}" if is_occ else f"{row['label']}\n(BOŞ)"
            kind = "primary" if is_occ else "secondary"
            if st.button(label, key=f"tbl_btn_{row['id']}", type=kind, use_container_width=True):
                st.session_state.selected_table = row.to_dict(); st.session_state.cart_table = items; st.rerun()

def render_table_order():
    tbl = st.session_state.selected_table
    c_back, c_trans = st.columns([3, 1])
    if c_back.button("⬅️ Masalara Qayıt", key="back_tbl", use_container_width=True): st.session_state.selected_table = None; st.session_state.cart_table = []; st.rerun()
    if c_trans.button("➡️ Köçür", use_container_width=True): show_transfer_dialog(tbl['id'])
    
    st.markdown(f"### 📝 Sifariş: {tbl['label']}")
    c1, c2 = st.columns([1.5, 3])
    with c1:
        st.info("Masa Sifarişi")
        db_cust_id = tbl.get('active_customer_id')
        if db_cust_id and not st.session_state.current_customer_tb:
             r = run_query("SELECT * FROM customers WHERE card_id=:id", {"id":db_cust_id})
             if not r.empty: st.session_state.current_customer_tb = r.iloc[0].to_dict()

        with st.form("sc_tb", clear_on_submit=True):
            ci, cb = st.columns([3,1]); qv = ci.text_input("Müştəri", label_visibility="collapsed", placeholder="Skan..."); 
            if cb.form_submit_button("🔍") or qv:
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
        
        col_s, col_p = st.columns(2)
        if col_s.button("🔥 MƏTBƏXƏ GÖNDƏR", key="save_tbl", use_container_width=True):
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

        if col_p.button("✅ ÖDƏNİŞ ET", key="pay_tbl", type="primary", use_container_width=True):
            if not st.session_state.cart_table: st.error("Boşdur!"); st.stop()
            show_payment_dialog(tbl['id'])
        
        if st.button("🖨️ Hesabı Gətir (Ara Çek)", use_container_width=True):
            show_pre_check_dialog(raw_total, final_total, serv_chg, st.session_state.cart_table, tbl['label'], get_baku_now().strftime("%Y-%m-%d %H:%M"))

    with c2: render_menu_grid(st.session_state.cart_table, "tb")

@st.dialog("Təsdiq Tələb Olunur (Manager/Admin)")
def admin_auth_dialog(item_idx=None, sale_to_delete=None):
    if sale_to_delete:
        st.warning("🔴 Satış bazadan silinəcək! Bu əməliyyat geri qaytarıla bilməz.")
    else:
        st.warning("🔴 Təsdiqlənmiş mal silinir!")
    
    reason = st.text_input("Səbəb (Məcburi)")
    pin = st.text_input("PIN Kodu", type="password")
    
    if st.button("Təsdiqlə"):
        if not reason:
            st.error("Səbəb yazmalısınız!")
            return

        target_roles = ['admin'] if sale_to_delete else ['admin', 'manager']
        role_ph = ",".join([f"'{r}'" for r in target_roles])
        approvers = run_query(f"SELECT password, role FROM users WHERE role IN ({role_ph})")
        
        approved = False
        approver_role = ""
        
        for _, row in approvers.iterrows():
            if verify_password(pin, row['password']):
                approved = True
                approver_role = row['role']
                break
        
        if approved:
            if sale_to_delete: 
                s_info = run_query("SELECT * FROM sales WHERE id=:id", {"id":int(sale_to_delete)}).iloc[0]
                run_action("DELETE FROM sales WHERE id=:id", {"id":int(sale_to_delete)})
                log_system(st.session_state.user, f"Deleted Sale #{sale_to_delete} ({s_info['total']} AZN). Reason: {reason} (Auth: {approver_role})")
                st.success("Satış silindi!"); st.rerun()
            else: 
                item = st.session_state.cart_table[item_idx]
                run_action("INSERT INTO void_logs (item_name, qty, reason, deleted_by, created_at) VALUES (:n, :q, :r, :u, :t)", 
                           {"n":item['item_name'], "q":item['qty'], "r":reason, "u":f"{st.session_state.user} (by {approver_role})", "t":get_baku_now()})
                st.session_state.cart_table.pop(item_idx)
                run_action("UPDATE tables SET items=:i WHERE id=:id", {"i":json.dumps(st.session_state.cart_table), "id":st.session_state.selected_table['id']})
                st.success("Silindi!"); st.rerun()
        else: 
            st.error(f"Səhv PIN! ({'Admin' if sale_to_delete else 'Admin/Manager'} tələb olunur)")

def render_analytics(is_admin=False, is_manager=False):
    tab_list = ["Satışlar"]
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
        st.markdown(f"<h1 style='text-align:center; color:#D32F2F;'>{BRAND_NAME}</h1><h5 style='text-align:center; color:#777;'>{VERSION}</h5>", unsafe_allow_html=True)
        tabs = st.tabs(["İŞÇİ (STAFF)", "İDARƏETMƏ (ADMIN/MANAGER)"])
        with tabs[0]:
            with st.form("staff_login"):
                pin = st.text_input("PIN", type="password"); 
                if st.form_submit_button("Giriş", use_container_width=True):
                    is_blocked, mins = check_login_block(pin) 
                    if is_blocked: st.error(f"Çox sayda uğursuz cəhd. {mins} dəqiqə gözləyin."); st.stop()
                    
                    udf = run_query("SELECT * FROM users WHERE role='staff'")
                    found = False
                    for _, row in udf.iterrows():
                        if verify_password(pin, row['password']):
                            clear_failed_login(row['username'])
                            st.session_state.logged_in=True; st.session_state.user=row['username']; st.session_state.role='staff'
                            tok=secrets.token_urlsafe(16); run_action("INSERT INTO active_sessions (token,username,role,created_at) VALUES (:t,:u,:r,:time)", {"t":tok,"u":row['username'],"r":'staff',"time":get_baku_now()})
                            log_system(row['username'], "Login (Staff)"); st.query_params["token"] = tok; st.rerun(); found=True; break
                    
                    if not found:
                        st.error("Yanlış PIN!")
                        time.sleep(2)

        with tabs[1]:
            with st.form("admin_login"):
                u = st.text_input("İstifadəçi"); p = st.text_input("Şifrə/PIN", type="password")
                if st.form_submit_button("Daxil Ol", use_container_width=True):
                    is_blocked, mins = check_login_block(u)
                    if is_blocked: st.error(f"Hesab bloklanıb. {mins} dəqiqə gözləyin."); st.stop()

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
                            st.error("Səhv Məlumat!")
                    else:
                        st.error("Səhv Məlumat!") 
                        time.sleep(1)
else:
    h1, h2, h3 = st.columns([4, 1, 1])
    with h1: st.markdown(f"**👤 {st.session_state.user}** | {st.session_state.role.upper()}")
    with h2: 
        if st.button("🔄 Yenilə", use_container_width=True): st.rerun()
    with h3: 
        if st.button("🚪 Çıxış", type="primary", use_container_width=True):
            run_action("DELETE FROM active_sessions WHERE token=:t", {"t":st.query_params.get("token")})
            log_system(st.session_state.user, "Logout"); st.session_state.logged_in = False; st.rerun()
    st.divider()

    role = st.session_state.role
    
    if role == 'admin':
        # ADMIN: Full Access
        tabs = st.tabs(["🏃‍♂️ AL-APAR", "🍽️ MASALAR", "📦 Anbar", "📜 Resept", "Analitika", "👥 CRM", "Menyu", "⚙️ Ayarlar", "Admin", "QR"])
        with tabs[0]: render_takeaway()
        with tabs[1]: render_tables_main()
        with tabs[2]: # Anbar
            st.subheader("📦 Anbar")
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
            st.subheader("📜 Reseptlər")
            rc1, rc2 = st.columns([1, 2])
            with rc1: 
                search_menu = st.text_input("🔍 Axtar", key="rec_search")
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
            st.subheader("👥 CRM"); c_cp, c_mail, c_fb = st.columns([1,1,1])
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
            st.subheader("📋 Menyu")
            with st.expander("📥 Excel"):
                up = st.file_uploader("Fayl", type=['xlsx'])
                if up and st.button("Yüklə", key="xl_load"):
                    df = pd.read_excel(up); run_action("DELETE FROM menu")
                    for _, row in df.iterrows(): 
                        pt = row.get('printer_target', 'kitchen')
                        ph = row.get('price_half', None)
                        run_action("INSERT INTO menu (item_name,price,category,is_active,is_coffee,printer_target,price_half) VALUES (:n,:p,:c,TRUE,:ic,:pt,:ph)", 
                                   {"n":row['item_name'],"p":row['price'],"c":row['category'],"ic":row.get('is_coffee',False),"pt":pt,"ph":ph})
                    st.rerun()
            with st.form("nm"):
                c1, c2, c3 = st.columns(3)
                with c1: n=st.text_input("Ad"); p=st.number_input("Qiymət", min_value=0.0, key="menu_p")
                with c2: c=st.text_input("Kat"); ic=st.checkbox("Kofe?"); pt=st.selectbox("Printer", ["kitchen", "bar"])
                with c3: ph=st.number_input("Yarım Qiymət (Seçimli)", min_value=0.0, value=0.0)
                
                if st.form_submit_button("Əlavə"): 
                    ph_val = ph if ph > 0 else None
                    run_action("INSERT INTO menu (item_name,price,category,is_active,is_coffee,printer_target,price_half) VALUES (:n,:p,:c,TRUE,:ic,:pt,:ph)", 
                               {"n":n,"p":p,"c":c,"ic":ic,"pt":pt,"ph":ph_val}); st.rerun()
            
            ml = run_query("SELECT * FROM menu")
            if not ml.empty:
                ml.insert(0, "Seç", False)
                edited_menu = st.data_editor(ml, column_config={"Seç": st.column_config.CheckboxColumn(required=True)}, hide_index=True, use_container_width=True)
                to_del_menu = edited_menu[edited_menu['Seç']]['item_name'].tolist()
                if to_del_menu and st.button(f"Seçilənləri Sil ({len(to_del_menu)})", type="primary", key="del_menu_bulk"):
                    for i_n in to_del_menu: run_action("DELETE FROM menu WHERE item_name=:n", {"n":i_n})
                    st.rerun()

        with tabs[7]: # Ayarlar (User Management Here)
            st.subheader("⚙️ Ayarlar")
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
                if st.button("Yadda Saxla", key="sv_sys"):
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
                                        run_action("INSERT INTO menu (item_name,price,category,is_active,is_coffee) VALUES (:n,:p,:c,TRUE,:ic)", 
                                                   {"n":row['item_name'],"p":row['price'],"c":row['category'],"ic":row.get('is_coffee',False)})
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
        tabs = st.tabs(["🏃‍♂️ AL-APAR", "🍽️ MASALAR", "📦 Anbar", "📜 Resept", "Analitika", "👥 CRM", "Menyu"])
        with tabs[0]: render_takeaway()
        with tabs[1]: render_tables_main()
        with tabs[2]: # Anbar (Manager Access)
            st.subheader("📦 Anbar")
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
            st.subheader("📜 Reseptlər")
            rc1, rc2 = st.columns([1, 2])
            with rc1: 
                search_menu = st.text_input("🔍 Axtar", key="rec_search")
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
            st.subheader("👥 CRM")
            fbs = run_query("SELECT * FROM feedbacks ORDER BY created_at DESC")
            if not fbs.empty:
                for _, fb in fbs.iterrows():
                    stars = "⭐️" * fb['rating']
                    st.markdown(f"**ID:** {fb['card_id']} | {stars}")
                    st.info(fb['comment'] or "(Rəy yazılmayıb)")
                    st.divider()
            else: st.info("Hələ rəy yoxdur")

        with tabs[6]: # Menyu (Manager Edit)
            st.subheader("📋 Menyu")
            with st.form("nm"):
                c1, c2, c3 = st.columns(3)
                with c1: n=st.text_input("Ad"); p=st.number_input("Qiymət", min_value=0.0, key="menu_p")
                with c2: c=st.text_input("Kat"); ic=st.checkbox("Kofe?"); pt=st.selectbox("Printer", ["kitchen", "bar"])
                with c3: ph=st.number_input("Yarım Qiymət (Seçimli)", min_value=0.0, value=0.0)
                if st.form_submit_button("Əlavə"): 
                    ph_val = ph if ph > 0 else None
                    run_action("INSERT INTO menu (item_name,price,category,is_active,is_coffee,printer_target,price_half) VALUES (:n,:p,:c,TRUE,:ic,:pt,:ph)", 
                               {"n":n,"p":p,"c":c,"ic":ic,"pt":pt,"ph":ph_val})
                    log_system(st.session_state.user, f"Manager Added Item: {n}")
                    st.rerun()
            ml = run_query("SELECT * FROM menu")
            if not ml.empty:
                ml.insert(0, "Seç", False)
                edited_menu = st.data_editor(ml, column_config={"Seç": st.column_config.CheckboxColumn(required=True)}, hide_index=True, use_container_width=True)
                to_del_menu = edited_menu[edited_menu['Seç']]['item_name'].tolist()
                if to_del_menu and st.button(f"Seçilənləri Sil ({len(to_del_menu)})", type="primary", key="del_menu_bulk"):
                    for i_n in to_del_menu: 
                        run_action("DELETE FROM menu WHERE item_name=:n", {"n":i_n})
                        log_system(st.session_state.user, f"Manager Deleted Item: {i_n}")
                    st.rerun()

    elif role == 'staff':
        # DYNAMIC STAFF TABS (V4.2)
        show_tables = (get_setting("staff_show_tables", "TRUE") == "TRUE")
        if show_tables:
            staff_tabs = st.tabs(["🏃‍♂️ AL-APAR", "🍽️ MASALAR", "Mənim Satışlarım"])
            with staff_tabs[0]: render_takeaway()
            with staff_tabs[1]: render_tables_main()
            with staff_tabs[2]: render_analytics(is_admin=False)
        else:
            staff_tabs = st.tabs(["🏃‍♂️ AL-APAR", "Mənim Satışlarım"])
            with staff_tabs[0]: render_takeaway()
            with staff_tabs[1]: render_analytics(is_admin=False)

    st.markdown(f"<div class='footer'>Ironwaves POS {VERSION} | © 2026</div>", unsafe_allow_html=True)
