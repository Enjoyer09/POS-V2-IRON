import streamlit as st
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

# ==========================================
# === IRONWAVES POS - VERSION 2.6 BETA (UI REDESIGN) ===
# ==========================================

# --- CONFIG ---
st.set_page_config(page_title="Ironwaves POS v2.6", page_icon="☕", layout="wide", initial_sidebar_state="collapsed")

# --- MENYU DATASI ---
FIXED_MENU_DATA = [
    {'name': 'Su', 'price': 2.0, 'cat': 'İçkilər', 'is_coffee': False},
    {'name': 'Çay (şirniyyat, fıstıq)', 'price': 3.0, 'cat': 'İçkilər', 'is_coffee': False},
    {'name': 'Yaşıl çay - jasmin', 'price': 4.0, 'cat': 'İçkilər', 'is_coffee': False},
    {'name': 'Meyvəli bitki çayı', 'price': 4.0, 'cat': 'İçkilər', 'is_coffee': False},
    {'name': 'Portağal şirəsi (Təbii)', 'price': 6.0, 'cat': 'İçkilər', 'is_coffee': False},
    {'name': 'Meyvə şirəsi', 'price': 4.0, 'cat': 'İçkilər', 'is_coffee': False},
    {'name': 'Limonad (evsayağı)', 'price': 6.0, 'cat': 'İçkilər', 'is_coffee': False},
    {'name': 'Kola', 'price': 4.0, 'cat': 'İçkilər', 'is_coffee': False},
    {'name': 'Tonik', 'price': 5.0, 'cat': 'İçkilər', 'is_coffee': False},
    {'name': 'Energetik (Redbull)', 'price': 6.0, 'cat': 'İçkilər', 'is_coffee': False},
    {'name': 'Americano S', 'price': 3.9, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Americano M', 'price': 4.9, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Americano L', 'price': 5.9, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Ice Americano S', 'price': 4.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Ice Americano M', 'price': 5.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Ice Americano L', 'price': 6.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Cappuccino S', 'price': 4.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Cappuccino M', 'price': 5.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Cappuccino L', 'price': 6.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Iced Cappuccino S', 'price': 4.7, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Iced Cappuccino M', 'price': 5.7, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Iced Cappuccino L', 'price': 6.7, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Latte S', 'price': 4.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Latte M', 'price': 5.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Latte L', 'price': 6.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Iced Latte S', 'price': 4.7, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Iced Latte M', 'price': 5.7, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Iced Latte L', 'price': 6.7, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Raf S', 'price': 4.7, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Raf M', 'price': 5.7, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Raf L', 'price': 6.7, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Mocha S', 'price': 4.7, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Mocha M', 'price': 5.7, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Mocha L', 'price': 6.7, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Ristretto S', 'price': 3.0, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Ristretto M', 'price': 4.0, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Ristretto L', 'price': 5.0, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Espresso S', 'price': 3.0, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Espresso M', 'price': 4.0, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Espresso L', 'price': 5.0, 'cat': 'Qəhvə', 'is_coffee': True}
]

# --- INFRA ---
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
DOMAIN = "emalatxana.ironwaves.store" 
APP_URL = f"https://{DOMAIN}"
DEFAULT_SENDER_EMAIL = "info@ironwaves.store" 

# --- CSS (YENİLƏNMİŞ DİZAYN) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700;900&display=swap');
    .stApp { font-family: 'Oswald', sans-serif !important; background-color: #F4F6F9; }
    
    /* GİZLİ SİDEBAR */
    [data-testid="stSidebar"] { display: none; }
    
    /* NAVİQASİYA TABLARI (ÇƏRCİVƏLİ & BOLD) */
    button[data-baseweb="tab"] {
        font-family: 'Oswald', sans-serif !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        background-color: white !important;
        border: 2px solid #E0E0E0 !important;
        border-radius: 10px !important;
        margin: 0 5px !important;
        padding: 10px 20px !important;
        color: #555 !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        border-color: #FF6B35 !important; /* Narıncı */
        color: #FF6B35 !important;
        background-color: #FFF3E0 !important;
    }
    
    /* POS DÜYMƏLƏRİ */
    div.stButton > button {
        border-radius: 12px !important; 
        height: 55px !important; 
        font-weight: 700 !important;
        border: none !important;
        box-shadow: 0 4px 0 rgba(0,0,0,0.1) !important;
        transition: all 0.1s !important;
    }
    div.stButton > button:active {
        transform: translateY(4px) !important;
        box-shadow: none !important;
    }
    
    /* PRIMARY BUTTONS */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #FF6B35, #FF8C00) !important;
        color: white !important;
    }

    /* STATUS DOTS */
    .status-dot { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-right: 5px; }
    .status-online { background-color: #2ECC71; box-shadow: 0 0 8px #2ECC71; }
    .status-offline { background-color: #BDC3C7; }
    
    /* CART & STOCK */
    .cart-item { background: white; border-radius: 10px; padding: 12px; margin-bottom: 8px; border: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }
    .stock-ok { border-left: 6px solid #2ECC71; padding: 12px; background: white; margin-bottom: 8px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .stock-low { border-left: 6px solid #E74C3C; padding: 12px; background: #FDEDEC; margin-bottom: 8px; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- DB CONNECTION ---
try:
    db_url = os.environ.get("STREAMLIT_CONNECTIONS_NEON_URL") or os.environ.get("DATABASE_URL")
    if not db_url: st.error("Database URL not found!"); st.stop()
    if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    conn = st.connection("neon", type="sql", url=db_url, pool_pre_ping=True)
except Exception as e: st.error(f"DB Error: {e}"); st.stop()

# --- SCHEMA ---
def ensure_schema():
    with conn.session as s:
        s.execute(text("CREATE TABLE IF NOT EXISTS menu (id SERIAL PRIMARY KEY, item_name TEXT, price DECIMAL(10,2), category TEXT, is_active BOOLEAN DEFAULT FALSE, is_coffee BOOLEAN DEFAULT FALSE);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, items TEXT, total DECIMAL(10,2), payment_method TEXT, cashier TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, last_seen TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS active_sessions (token TEXT PRIMARY KEY, username TEXT, role TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS ingredients (id SERIAL PRIMARY KEY, name TEXT UNIQUE, stock_qty DECIMAL(10,2) DEFAULT 0, unit TEXT, category TEXT, min_limit DECIMAL(10,2) DEFAULT 10);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS recipes (id SERIAL PRIMARY KEY, menu_item_name TEXT, ingredient_name TEXT, quantity_required DECIMAL(10,2));"))
        
        # --- V1 TABLES ---
        s.execute(text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS customers (card_id TEXT PRIMARY KEY, stars INTEGER DEFAULT 0, type TEXT, email TEXT, birth_date TEXT, is_active BOOLEAN DEFAULT FALSE, last_visit TIMESTAMP, secret_token TEXT);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS customer_coupons (id SERIAL PRIMARY KEY, card_id TEXT, coupon_type TEXT, is_used BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, card_id TEXT, message TEXT, is_read BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS feedback (id SERIAL PRIMARY KEY, card_id TEXT, rating INTEGER, message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        
        s.commit()
    
    # Default Admin
    with conn.session as s:
        try:
            chk = s.execute(text("SELECT * FROM users WHERE username='admin'")).fetchone()
            if not chk:
                p_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
                s.execute(text("INSERT INTO users (username, password, role) VALUES ('admin', :p, 'admin')"), {"p": p_hash})
                s.commit()
        except: s.rollback()

ensure_schema()

# --- HELPERS ---
def run_query(q, p=None): return conn.query(q, params=p, ttl=0)
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
def send_email(to_email, subject, body):
    if not RESEND_API_KEY: return False
    url = "https://api.resend.com/emails"
    headers = {"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"}
    payload = {"from": f"Emalatxana <{DEFAULT_SENDER_EMAIL}>", "to": [to_email], "subject": subject, "html": body}
    try: requests.post(url, json=payload, headers=headers); return True
    except: return False
@st.cache_data
def generate_custom_qr(data, center_text):
    qr = qrcode.QRCode(box_size=10, border=2); qr.add_data(data); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    draw = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("arial.ttf", 20)
    except: font = ImageFont.load_default()
    bbox = draw.textbbox((0,0), center_text, font=font); w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.rectangle([(img.size[0]-w)/2-5, (img.size[1]-h)/2-5, (img.size[0]+w)/2+5, (img.size[1]+h)/2+5], fill="white")
    draw.text(((img.size[0]-w)/2, (img.size[1]-h)/2), center_text, fill="black", font=font)
    buf = BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()

# --- SESSION ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []
if 'selected_recipe_product' not in st.session_state: st.session_state.selected_recipe_product = None
if 'current_customer' not in st.session_state: st.session_state.current_customer = None
if 'active_coupon' not in st.session_state: st.session_state.active_coupon = None

def check_session_token():
    token = st.query_params.get("token")
    if token:
        try:
            res = run_query("SELECT username, role FROM active_sessions WHERE token=:t", {"t":token})
            if not res.empty:
                st.session_state.logged_in = True
                st.session_state.user = res.iloc[0]['username']
                st.session_state.role = res.iloc[0]['role']
        except: pass
check_session_token()

if st.session_state.get('logged_in'):
    run_action("UPDATE users SET last_seen = NOW() WHERE username = :u", {"u": st.session_state.user})

# ==========================================
# === LOGIN ===
# ==========================================
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown("<h2 style='text-align:center;'>☕ EMALATXANA POS</h2>", unsafe_allow_html=True)
        tabs = st.tabs(["İŞÇİ (PIN)", "ADMİN"])
        with tabs[0]:
            with st.form("staff_login"):
                pin = st.text_input("PIN Kod", type="password")
                if st.form_submit_button("Daxil Ol", use_container_width=True):
                    udf = run_query("SELECT * FROM users WHERE role='staff'")
                    found = False
                    for _, row in udf.iterrows():
                        if verify_password(pin, row['password']):
                            st.session_state.logged_in=True; st.session_state.user=row['username']; st.session_state.role='staff'
                            tok=secrets.token_urlsafe(16); run_action("INSERT INTO active_sessions (token,username,role) VALUES (:t,:u,:r)", {"t":tok,"u":row['username'],"r":'staff'})
                            st.query_params["token"] = tok; st.rerun(); found=True; break
                    if not found: st.error("Yanlış PIN")
        with tabs[1]:
            with st.form("admin_login"):
                u = st.text_input("User"); p = st.text_input("Pass", type="password")
                if st.form_submit_button("Daxil Ol", use_container_width=True):
                    udf = run_query("SELECT * FROM users WHERE LOWER(username)=LOWER(:u) AND role='admin'", {"u":u})
                    if not udf.empty and verify_password(p, udf.iloc[0]['password']):
                        st.session_state.logged_in=True; st.session_state.user=u; st.session_state.role='admin'
                        tok=secrets.token_urlsafe(16); run_action("INSERT INTO active_sessions (token,username,role) VALUES (:t,:u,:r)", {"t":tok,"u":u,"r":'admin'})
                        st.query_params["token"] = tok; st.rerun()
                    else: st.error("Səhv")
else:
    # ==========================================
    # === MAIN APP (RE-DESIGNED) ===
    # ==========================================
    
    # --- YUXARI PANEL (HEADER) ---
    h1, h2, h3, h4 = st.columns([3, 3, 1, 1])
    with h1:
        st.markdown(f"#### 👤 {st.session_state.user} | {st.session_state.role.upper()}")
    with h2:
        # ONLINE STATUS GÖSTƏRİCİSİ (HEADERDƏ)
        try:
            users = run_query("SELECT username, last_seen FROM users")
            status_html = ""
            for _, r in users.iterrows():
                if r['last_seen']:
                    diff = datetime.datetime.now() - pd.to_datetime(r['last_seen'])
                    color = "#2ECC71" if diff.total_seconds() < 120 else "#BDC3C7"
                    status_html += f"<span style='color:{color}; font-weight:bold; margin-right:10px;'>● {r['username']}</span>"
            st.markdown(f"<div style='padding-top:5px;'>{status_html}</div>", unsafe_allow_html=True)
        except: pass
    with h3:
        if st.button("🔄 Yenilə", use_container_width=True): st.rerun()
    with h4:
        if st.button("🚪 Çıxış", type="primary", use_container_width=True):
            run_action("DELETE FROM active_sessions WHERE token=:t", {"t":st.query_params.get("token")})
            st.session_state.logged_in = False; st.rerun()
            
    st.divider()

    role = st.session_state.role
    
    # --- NAVİQASİYA (BOLD & FRAMED TABS) ---
    # Bu adlar CSS ilə çərçivəyə alınacaq
    TABS = ["POS", "📦 Anbar (Stok)", "📜 Reseptlər", "Analitika", "CRM", "Menyu", "⚙️ Ayarlar", "Admin", "QR"]
    if role == 'staff': TABS = ["POS"]
    
    tabs = st.tabs(TABS)
    
    # --- TAB 1: POS ---
    with tabs[0]:
        c1, c2 = st.columns([1.5, 3])
        
        with c1:
            st.info("🧾 Cari Sifariş")
            
            # MÜŞTƏRİ TANITMAQ
            with st.expander("👤 Müştəri Tanıt (Bonus)"):
                with st.form("scan_qr"):
                    qr_val = st.text_input("QR Kod / ID", placeholder="Skan et...")
                    if st.form_submit_button("Axtar"):
                        try:
                            clean_id = qr_val.split("id=")[1].split("&")[0] if "id=" in qr_val else qr_val
                            cust = run_query("SELECT * FROM customers WHERE card_id=:id", {"id":clean_id})
                            if not cust.empty:
                                st.session_state.current_customer = cust.iloc[0].to_dict()
                                st.success(f"Müştəri: {clean_id}")
                            else: st.error("Tapılmadı")
                        except: st.error("Xəta")
            
            if st.session_state.current_customer:
                curr = st.session_state.current_customer
                st.success(f"⭐ Bonuslar: {curr['stars']} / 10")
                if st.button("Müştərini Ləğv Et"): st.session_state.current_customer = None; st.rerun()

            # SƏBƏT
            if st.session_state.cart:
                total_bill = 0
                for i, item in enumerate(st.session_state.cart):
                    item_total = item['qty'] * item['price']
                    total_bill += item_total
                    
                    st.markdown(f"""
                    <div class="cart-item">
                        <div style="font-weight:bold; flex:2;">{item['item_name']}</div>
                        <div style="flex:1; text-align:center;">{item['price']}</div>
                        <div style="flex:1; text-align:center; font-weight:bold; color:#E65100;">x{item['qty']}</div>
                        <div style="flex:1; text-align:right;">{item_total:.1f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Mini idarəetmə düymələri
                    b1, b2, b3 = st.columns([1,1,4])
                    if b1.button("➖", key=f"mn_{i}"):
                        if item['qty'] > 1: item['qty'] -= 1
                        else: st.session_state.cart.pop(i)
                        st.rerun()
                    if b2.button("➕", key=f"pl_{i}"): item['qty'] += 1; st.rerun()

                # ENDİRİM HESABLAMA (V1 LOGIC)
                final_price = total_bill
                discount = 0
                if st.session_state.current_customer:
                    # Məsələn 9 ulduz varsa 1 kofe pulsuz
                    pass 

                st.markdown(f"<h2 style='text-align:right; color:#D35400'>CƏM: {final_price:.2f} ₼</h2>", unsafe_allow_html=True)
                
                pay_method = st.radio("Ödəniş:", ["Nəğd", "Kart"], horizontal=True)
                
                if st.button("✅ SATIŞI TƏSDİQLƏ", type="primary", use_container_width=True):
                    try:
                        # Transaction Start
                        items_str = ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart])
                        run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i, :t, :p, :c, NOW())", 
                                   {"i":items_str, "t":final_price, "p": ("Cash" if pay_method=="Nəğd" else "Card"), "c":st.session_state.user})
                        
                        # Inventory Deduction
                        log = []
                        with conn.session as s:
                            for item in st.session_state.cart:
                                recipes = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name = :m"), {"m": item['item_name']}).fetchall()
                                if recipes:
                                    for r in recipes:
                                        ing_name = r[0]
                                        qty_needed = float(r[1]) * int(item['qty'])
                                        s.execute(text("UPDATE ingredients SET stock_qty = stock_qty - :q WHERE name = :n"), {"q":qty_needed, "n":ing_name})
                                        log.append(f"{ing_name}: -{qty_needed}")
                            
                            # Loyalty Update
                            if st.session_state.current_customer:
                                cid = st.session_state.current_customer['card_id']
                                star_gain = sum([x['qty'] for x in st.session_state.cart if x.get('is_coffee')]) # Sadə məntiq
                                s.execute(text("UPDATE customers SET stars = stars + :s WHERE card_id=:id"), {"s":star_gain, "id":cid})
                            
                            s.commit()
                        
                        if log: st.toast(f"Stok: {len(log)} maddə silindi")
                        st.session_state.cart = []
                        st.success("Satıldı!")
                        time.sleep(1); st.rerun()
                    except Exception as e: st.error(f"Xəta: {e}")

            else: st.info("Səbət boşdur")

        with c2:
            # MƏHSUL VİTRİNİ
            cats = run_query("SELECT DISTINCT category FROM menu WHERE is_active=TRUE")
            if not cats.empty:
                cat_list = ["Hamısı"] + sorted(cats['category'].tolist())
                sel_cat = st.radio("Kataloq", cat_list, horizontal=True)
                
                sql = "SELECT * FROM menu WHERE is_active=TRUE"
                p = {}
                if sel_cat != "Hamısı":
                    sql += " AND category=:c"
                    p["c"] = sel_cat
                sql += " ORDER BY price ASC"
                
                prods = run_query(sql, p)
                
                cols = st.columns(4)
                for idx, row in prods.iterrows():
                    with cols[idx % 4]:
                        # Konteyner effekti
                        with st.container(border=True):
                            st.markdown(f"<div style='text-align:center; font-weight:bold; height:40px; overflow:hidden;'>{row['item_name']}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='text-align:center; color:#E65100; font-size:18px;'>{row['price']} ₼</div>", unsafe_allow_html=True)
                            
                            # Say seçimi (Mini input)
                            qty_add = st.number_input("Say", min_value=1, value=1, key=f"q_{row['id']}", label_visibility="collapsed")
                            
                            if st.button("SƏBƏTƏ", key=f"btn_{row['id']}", use_container_width=True):
                                existing = next((x for x in st.session_state.cart if x['item_name'] == row['item_name']), None)
                                if existing: existing['qty'] += qty_add
                                else: st.session_state.cart.append({'item_name': row['item_name'], 'price': float(row['price']), 'qty': qty_add, 'is_coffee': row['is_coffee']})
                                st.toast(f"{row['item_name']} x{qty_add} əlavə edildi!")
                                st.rerun()

    # --- TAB 2: ANBAR ---
    if role == 'admin':
        with tabs[1]:
            st.subheader("📦 Anbar Vəziyyəti")
            c_act, c_view = st.columns([1, 2])
            
            with c_act:
                st.markdown("#### Əməliyyatlar")
                op = st.selectbox("Seç:", ["Stok Artır/Yarat", "Sil"])
                if op == "Stok Artır/Yarat":
                    with st.form("stk_add"):
                        name = st.text_input("Ad")
                        cat = st.selectbox("Kateqoriya", ["Bar", "Süd", "Sirop", "Qablaşdırma", "Digər"])
                        qty = st.number_input("Miqdar", min_value=0.0)
                        unit = st.selectbox("Vahid", ["gr", "ml", "ədəd", "kq", "litr"])
                        limit = st.number_input("Limit", 10.0)
                        if st.form_submit_button("Yadda Saxla"):
                            run_action("INSERT INTO ingredients (name, stock_qty, unit, category, min_limit) VALUES (:n,:q,:u,:c,:l) ON CONFLICT (name) DO UPDATE SET stock_qty=ingredients.stock_qty+:q", {"n":name,"q":qty,"u":unit,"c":cat,"l":limit})
                            st.success("Oldu!"); st.rerun()
                else:
                    dlist = run_query("SELECT name FROM ingredients")
                    if not dlist.empty:
                        del_n = st.selectbox("Silinəcək", dlist['name'].unique())
                        if st.button("Sil"): run_action("DELETE FROM ingredients WHERE name=:n", {"n":del_n}); st.rerun()

            with c_view:
                st.markdown("#### Hazırki Stok")
                idf = run_query("SELECT * FROM ingredients ORDER BY category, name")
                if not idf.empty:
                    for _, r in idf.iterrows():
                        cls = "stock-low" if r['stock_qty'] <= r['min_limit'] else "stock-ok"
                        icon = "⚠️" if r['stock_qty'] <= r['min_limit'] else "✅"
                        st.markdown(f"<div class='{cls}'><div style='display:flex; justify-content:space-between;'><span><b>{r['name']}</b> ({r['category']})</span><span>{r['stock_qty']} {r['unit']}</span></div><div style='font-size:12px; color:gray;'>Limit: {r['min_limit']} | {icon}</div></div>", unsafe_allow_html=True)

        # --- TAB 3: RESEPT ---
        with tabs[2]:
            st.subheader("📜 Reseptur")
            c_l, c_r = st.columns([1, 2])
            with c_l:
                m_list = run_query("SELECT item_name FROM menu WHERE is_active=True")
                if not m_list.empty:
                    sel_p = st.selectbox("Məhsul", m_list['item_name'].unique())
                    st.session_state.selected_recipe_product = sel_p
            with c_r:
                if st.session_state.selected_recipe_product:
                    p = st.session_state.selected_recipe_product
                    st.markdown(f"**{p}** Tərkibi:")
                    recs = run_query("SELECT id, ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m", {"m":p})
                    st.dataframe(recs, hide_index=True, use_container_width=True)
                    
                    if st.button("Sətri Sil (ID ilə)"):
                        rid = st.number_input("Silinəcək ID", min_value=0)
                        if rid > 0: run_action("DELETE FROM recipes WHERE id=:id", {"id":rid}); st.rerun()
                    
                    st.divider()
                    st.markdown("➕ Əlavə et")
                    ings = run_query("SELECT name, unit FROM ingredients")
                    if not ings.empty:
                        with st.form("add_rec"):
                            c1, c2 = st.columns(2)
                            i_name = c1.selectbox("Xammal", ings['name'].unique())
                            u = ings[ings['name']==i_name].iloc[0]['unit']
                            qty = c2.number_input(f"Miqdar ({u})", 0.1)
                            if st.form_submit_button("Əlavə Et"):
                                run_action("INSERT INTO recipes (menu_item_name, ingredient_name, quantity_required) VALUES (:m,:i,:q)", {"m":p,"i":i_name,"q":qty})
                                st.rerun()

        # --- TAB 4: ANALITIKA ---
        with tabs[3]:
            st.markdown("### 📊 Hesabatlar")
            mode = st.radio("Filtr", ["Günlük", "Aylıq"], horizontal=True)
            sql = "SELECT * FROM sales"
            p = {}
            if mode == "Günlük":
                d = st.date_input("Tarix", datetime.date.today())
                sql += " WHERE DATE(created_at AT TIME ZONE 'Asia/Baku') = :d"
                p['d'] = d
            
            sql += " ORDER BY created_at DESC"
            sdf = run_query(sql, p)
            if not sdf.empty:
                t = sdf['total'].sum()
                c1, c2 = st.columns(2)
                c1.metric("Cəm Satış", f"{t:.2f} ₼")
                c2.metric("Sifariş Sayı", len(sdf))
                st.dataframe(sdf, use_container_width=True)
            else: st.info("Məlumat yoxdur")

        # --- DIGER TABLAR (Sadələşdirilmiş) ---
        with tabs[5]: # Menyu
            st.subheader("📋 Menyu")
            with st.expander("Yenilə / Reset"):
                if st.button("Standart Menyunu Yüklə"):
                    run_action("DELETE FROM menu")
                    for x in FIXED_MENU_DATA:
                        run_action("INSERT INTO menu (item_name, price, category, is_active, is_coffee) VALUES (:n,:p,:c,TRUE,:ic)", 
                                   {"n":x['name'],"p":x['price'],"c":x['cat'],"ic":x['is_coffee']})
                    st.success("Yükləndi!"); st.rerun()
            m = run_query("SELECT * FROM menu ORDER BY category, item_name")
            st.dataframe(m, use_container_width=True)

        with tabs[6]: # Ayarlar
            st.subheader("⚙️ Ayarlar")
            with st.expander("Yeni İşçi"):
                with st.form("new_u"):
                    u = st.text_input("Login"); p = st.text_input("Pass/PIN")
                    r = st.selectbox("Role", ["staff","admin"])
                    if st.form_submit_button("Yarat"):
                        run_action("INSERT INTO users (username, password, role) VALUES (:u,:p,:r)", {"u":u,"p":hash_password(p),"r":r})
                        st.success("OK")
