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
from urllib.parse import urlparse, parse_qs 

# ==========================================
# === IRONWAVES POS - V2.1.1 BETA (ULTIMATE) ===
# ==========================================

VERSION = "v2.1.1 BETA"

# --- INFRA ---
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
DOMAIN = "demo.ironwaves.store" 
APP_URL = f"https://{DOMAIN}"
DEFAULT_SENDER_EMAIL = "info@ironwaves.store" 

# --- CONFIG ---
st.set_page_config(page_title=f"Ironwaves POS {VERSION}", page_icon="☕", layout="wide", initial_sidebar_state="collapsed")

# --- CSS (RƏNGLİ VƏ ESTETİK) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700;900&display=swap');
    .stApp { font-family: 'Oswald', sans-serif !important; background-color: #F4F6F9; }
    
    /* GİZLİ HİSSƏLƏR */
    header {visibility: hidden;} #MainMenu {visibility: hidden;} footer {visibility: hidden;} [data-testid="stSidebar"] { display: none; }
    .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
    
    /* TABS */
    button[data-baseweb="tab"] {
        font-family: 'Oswald', sans-serif !important; font-size: 16px !important; font-weight: 700 !important;
        background-color: white !important; border: 1px solid #E0E0E0 !important; border-radius: 8px !important;
        margin: 0 4px !important; color: #555 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        border-color: #FF6B35 !important; color: #FF6B35 !important; background-color: #FFF3E0 !important;
    }
    
    /* DÜYMƏLƏR (GRADIENT GERİ QAYITDI) */
    div.stButton > button {
        border-radius: 10px !important; height: 48px !important; font-weight: 700 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important; transition: all 0.2s !important;
        border: none !important;
    }
    div.stButton > button:active { transform: translateY(3px) !important; box-shadow: none !important; }
    div.stButton > button[kind="primary"] { 
        background: linear-gradient(135deg, #FF6B35 0%, #FF8C00 100%) !important; color: white !important; 
    }
    div.stButton > button[kind="secondary"] { 
        background: white !important; color: #333 !important; border: 1px solid #ddd !important;
    }

    /* POS CARD */
    .pos-card-header {
        background: linear-gradient(135deg, #2E7D32, #43A047); color: white; padding: 10px; 
        border-radius: 10px 10px 0 0; text-align: center; font-weight: bold; font-size: 14px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .pos-card-body {
        background: white; border: 1px solid #eee; border-top: none; border-radius: 0 0 10px 10px; 
        padding: 10px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 10px;
    }
    .pos-price { font-size: 18px; color: #2E7D32; font-weight: bold; }

    /* ANBAR KARTI (INTERAKTIV) */
    .stock-card {
        background: white; border-radius: 12px; padding: 15px; margin-bottom: 10px;
        box-shadow: 0 3px 6px rgba(0,0,0,0.05); border: 1px solid #eee; position: relative;
        transition: transform 0.2s;
    }
    .stock-card:hover { transform: scale(1.01); border-color: #FF6B35; }
    .stock-id { 
        position: absolute; top: 5px; right: 8px; font-size: 10px; 
        color: #999; background: #f0f0f0; padding: 2px 5px; border-radius: 4px;
    }
    .stock-card.low { border-left: 5px solid #E74C3C; background: #FFF5F5; }
    .stock-card.ok { border-left: 5px solid #2ECC71; }

    /* FOOTER */
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background: #eee; color: #777; text-align: center; padding: 2px; font-size: 10px; z-index: 999; }
    </style>
""", unsafe_allow_html=True)

# --- DB CONNECTION ---
try:
    db_url = os.environ.get("STREAMLIT_CONNECTIONS_NEON_URL") or os.environ.get("DATABASE_URL")
    if not db_url: st.error("DB URL Not Found"); st.stop()
    if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    conn = st.connection("neon", type="sql", url=db_url, pool_pre_ping=True)
except Exception as e: st.error(f"DB Error: {e}"); st.stop()

# --- SCHEMA (YENİLİK: LOGS & EXPENSES) ---
def ensure_schema():
    with conn.session as s:
        # Core Tables
        s.execute(text("CREATE TABLE IF NOT EXISTS menu (id SERIAL PRIMARY KEY, item_name TEXT, price DECIMAL(10,2), category TEXT, is_active BOOLEAN DEFAULT FALSE, is_coffee BOOLEAN DEFAULT FALSE);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, items TEXT, total DECIMAL(10,2), payment_method TEXT, cashier TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, last_seen TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS active_sessions (token TEXT PRIMARY KEY, username TEXT, role TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS ingredients (id SERIAL PRIMARY KEY, name TEXT UNIQUE, stock_qty DECIMAL(10,2) DEFAULT 0, unit TEXT, category TEXT, min_limit DECIMAL(10,2) DEFAULT 10);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS recipes (id SERIAL PRIMARY KEY, menu_item_name TEXT, ingredient_name TEXT, quantity_required DECIMAL(10,2));"))
        # CRM & Settings
        s.execute(text("CREATE TABLE IF NOT EXISTS customers (card_id TEXT PRIMARY KEY, stars INTEGER DEFAULT 0, type TEXT, email TEXT, birth_date TEXT, is_active BOOLEAN DEFAULT FALSE, last_visit TIMESTAMP, secret_token TEXT, gender TEXT);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS customer_coupons (id SERIAL PRIMARY KEY, card_id TEXT, coupon_type TEXT, is_used BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, card_id TEXT, message TEXT, is_read BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
        
        # --- NEW TABLES FOR V2.1.1 ---
        # 1. System Logs (Giriş/Çıxış izləmə)
        s.execute(text("CREATE TABLE IF NOT EXISTS system_logs (id SERIAL PRIMARY KEY, username TEXT, action TEXT, ip TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        # 2. Expenses (Xərclər)
        s.execute(text("CREATE TABLE IF NOT EXISTS expenses (id SERIAL PRIMARY KEY, title TEXT, amount DECIMAL(10,2), category TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        
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
def log_system(user, action):
    try: run_action("INSERT INTO system_logs (username, action) VALUES (:u, :a)", {"u":user, "a":action})
    except: pass
def get_setting(key, default=""):
    try:
        r = run_query("SELECT value FROM settings WHERE key=:k", {"k":key})
        return r.iloc[0]['value'] if not r.empty else default
    except: return default
def set_setting(key, value):
    run_action("INSERT INTO settings (key, value) VALUES (:k, :v) ON CONFLICT (key) DO UPDATE SET value=:v", {"k":key, "v":value})

# --- SESSION ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []
if 'current_customer' not in st.session_state: st.session_state.current_customer = None

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
# === LOGIN SCREEN ===
# ==========================================
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown(f"<h1 style='text-align:center; color:#2E7D32;'>☕ EMALATXANA</h1><h5 style='text-align:center; color:#777;'>{VERSION}</h5>", unsafe_allow_html=True)
        tabs = st.tabs(["İŞÇİ (PIN)", "ADMİN"])
        with tabs[0]:
            with st.form("staff_login"):
                pin = st.text_input("PIN Kod", type="password", placeholder="****")
                if st.form_submit_button("Sistemə Giriş", use_container_width=True):
                    udf = run_query("SELECT * FROM users WHERE role='staff'")
                    found = False
                    for _, row in udf.iterrows():
                        if verify_password(pin, row['password']):
                            st.session_state.logged_in=True; st.session_state.user=row['username']; st.session_state.role='staff'
                            tok=secrets.token_urlsafe(16); run_action("INSERT INTO active_sessions (token,username,role) VALUES (:t,:u,:r)", {"t":tok,"u":row['username'],"r":'staff'})
                            log_system(row['username'], "Login (PIN)")
                            st.query_params["token"] = tok; st.rerun(); found=True; break
                    if not found: st.error("Yanlış PIN!")
        with tabs[1]:
            with st.form("admin_login"):
                u = st.text_input("User"); p = st.text_input("Pass", type="password")
                if st.form_submit_button("Admin Giriş", use_container_width=True):
                    udf = run_query("SELECT * FROM users WHERE LOWER(username)=LOWER(:u) AND role='admin'", {"u":u})
                    if not udf.empty and verify_password(p, udf.iloc[0]['password']):
                        st.session_state.logged_in=True; st.session_state.user=u; st.session_state.role='admin'
                        tok=secrets.token_urlsafe(16); run_action("INSERT INTO active_sessions (token,username,role) VALUES (:t,:u,:r)", {"t":tok,"u":u,"r":'admin'})
                        log_system(u, "Login (Admin)")
                        st.query_params["token"] = tok; st.rerun()
                    else: st.error("Səhv!")
else:
    # --- HEADER ---
    h1, h2, h3 = st.columns([4, 1, 1])
    with h1: st.markdown(f"**👤 {st.session_state.user}** | {st.session_state.role.upper()}")
    with h2: 
        if st.button("🔄 Yenilə", use_container_width=True): st.rerun()
    with h3: 
        if st.button("🚪 Çıxış", type="primary", use_container_width=True):
            run_action("DELETE FROM active_sessions WHERE token=:t", {"t":st.query_params.get("token")})
            log_system(st.session_state.user, "Logout")
            st.session_state.logged_in = False; st.rerun()
    st.divider()

    role = st.session_state.role
    
    # --- ANALYTICS FUNC ---
    def render_analytics(is_admin=False):
        atabs = st.tabs(["Satışlar", "Xərclər & Mənfəət", "Sistem Logları"])
        
        with atabs[0]:
            st.markdown("### 📊 Satış Hesabatı")
            f_mode = st.radio("Vaxt", ["Günlük", "Aylıq"], horizontal=True, key=f"am_{is_admin}")
            sql = "SELECT * FROM sales"; p = {}
            if not is_admin: sql += " WHERE cashier = :u"; p['u'] = st.session_state.user
            else: sql += " WHERE 1=1" 

            if f_mode == "Günlük":
                d = st.date_input("Gün", datetime.date.today(), key=f"d_{is_admin}")
                sql += " AND DATE(created_at AT TIME ZONE 'Asia/Baku') = :d"; p['d'] = d
            else:
                d = st.date_input("Ay", datetime.date.today(), key=f"m_{is_admin}")
                sql += " AND TO_CHAR(created_at AT TIME ZONE 'Asia/Baku', 'YYYY-MM') = :m"; p['m'] = d.strftime("%Y-%m")
            
            sql += " ORDER BY created_at DESC"
            sales = run_query(sql, p)
            if not sales.empty:
                t = sales['total'].sum()
                st.metric("Dövriyyə", f"{t:.2f} ₼")
                st.dataframe(sales, use_container_width=True)
            else: st.info("Satış yoxdur")

        with atabs[1]:
            if is_admin:
                st.markdown("### 💰 Xalis Mənfəət (P&L)")
                # Add Expense
                with st.expander("➕ Xərc Əlavə Et (İcarə, Maaş...)"):
                    with st.form("add_exp"):
                        ex_t = st.text_input("Təyinat (Məs: İşıq pulu)")
                        ex_a = st.number_input("Məbləğ (AZN)", min_value=0.0)
                        ex_c = st.selectbox("Kateqoriya", ["İcarə", "Kommunal", "Maaş", "Təchizat", "Digər"])
                        if st.form_submit_button("Əlavə Et"):
                            run_action("INSERT INTO expenses (title, amount, category) VALUES (:t, :a, :c)", {"t":ex_t, "a":ex_a, "c":ex_c})
                            st.success("Yazıldı!"); st.rerun()
                
                # Calc
                total_sales = run_query("SELECT SUM(total) as t FROM sales").iloc[0]['t'] or 0
                total_exp = run_query("SELECT SUM(amount) as t FROM expenses").iloc[0]['t'] or 0
                net_profit = total_sales - total_exp
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Ümumi Satış", f"{total_sales:.2f} ₼")
                c2.metric("Ümumi Xərclər", f"{total_exp:.2f} ₼", delta_color="inverse")
                c3.metric("XALİS MƏNFƏƏT", f"{net_profit:.2f} ₼", delta=f"{net_profit:.2f}")
                
                st.markdown("**Son Xərclər:**")
                st.dataframe(run_query("SELECT * FROM expenses ORDER BY created_at DESC LIMIT 50"), use_container_width=True)
            else: st.info("Bu bölmə yalnız admin üçündür.")

        with atabs[2]:
            st.markdown("### 🕵️‍♂️ Giriş/Çıxış Tarixçəsi")
            logs = run_query("SELECT * FROM system_logs ORDER BY created_at DESC LIMIT 100")
            st.dataframe(logs, use_container_width=True)

    # --- POS FUNC ---
    def render_pos_interface():
        c1, c2 = st.columns([1.5, 3])
        # LEFT: CART
        with c1:
            st.info("🧾 Çek")
            with st.form("scanner_form", clear_on_submit=True):
                c_i, c_b = st.columns([3, 1])
                qv = c_i.text_input("Müştəri", label_visibility="collapsed", placeholder="Skan..."); sb = c_b.form_submit_button("🔍")
                if sb or qv:
                    if qv:
                        try:
                            cid = qv.strip().split("id=")[1].split("&")[0] if "id=" in qv else qv.strip()
                            r = run_query("SELECT * FROM customers WHERE card_id=:id", {"id":cid})
                            if not r.empty: st.session_state.current_customer=r.iloc[0].to_dict(); st.toast("✅"); st.rerun()
                            else: st.error("Tapılmadı")
                        except: st.error("Xəta")
            
            if st.session_state.current_customer:
                c = st.session_state.current_customer
                st.success(f"👤 {c['card_id']} | ⭐ {c['stars']}")
                if st.button("Ləğv Et", use_container_width=True): st.session_state.current_customer=None; st.rerun()

            if st.session_state.cart:
                tb = 0
                for i, it in enumerate(st.session_state.cart):
                    sub = it['qty']*it['price']; tb+=sub
                    st.markdown(f"<div class='cart-item'><div style='flex:2'><b>{it['item_name']}</b></div><div style='flex:1'>{it['price']}</div><div style='flex:1;color:#E65100'>x{it['qty']}</div><div style='flex:1;text-align:right'>{sub:.1f}</div></div>", unsafe_allow_html=True)
                    b1,b2,b3=st.columns([1,1,4])
                    if b1.button("➖", key=f"m_{i}"): 
                        if it['qty']>1: it['qty']-=1 
                        else: st.session_state.cart.pop(i)
                        st.rerun()
                    if b2.button("➕", key=f"p_{i}"): it['qty']+=1; st.rerun()
                
                st.markdown(f"<h2 style='text-align:right; color:#E65100'>{tb:.2f} ₼</h2>", unsafe_allow_html=True)
                pm = st.radio("Ödəniş:", ["Nəğd", "Kart"], horizontal=True)
                
                if st.button("✅ ÖDƏNİŞ ET", type="primary", use_container_width=True):
                    # Sale Logic
                    istr = ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart])
                    run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i,:t,:p,:c,NOW())", 
                               {"i":istr,"t":tb,"p":("Cash" if pm=="Nəğd" else "Card"),"c":st.session_state.user})
                    
                    # Inventory
                    with conn.session as s:
                        for it in st.session_state.cart:
                            rs = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m"), {"m":it['item_name']}).fetchall()
                            for r in rs: s.execute(text("UPDATE ingredients SET stock_qty=stock_qty-:q WHERE name=:n"), {"q":float(r[1])*it['qty'], "n":r[0]})
                        if st.session_state.current_customer:
                            cid = st.session_state.current_customer['card_id']
                            gain = sum([x['qty'] for x in st.session_state.cart if x.get('is_coffee')])
                            s.execute(text("UPDATE customers SET stars=stars+:s WHERE card_id=:id"), {"s":gain, "id":cid})
                        s.commit()
                    
                    # RECEIPT MODAL
                    st.session_state.last_sale = {"id": int(time.time()), "items": istr, "total": tb, "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
                    st.session_state.cart=[]
                    st.rerun()
            else: st.info("Səbət boşdur")

        # --- RIGHT: PRODUCTS ---
        with c2:
            cats = run_query("SELECT DISTINCT category FROM menu WHERE is_active=TRUE")
            if not cats.empty:
                cl = ["Hamısı"] + sorted(cats['category'].tolist())
                sc = st.radio("Kat", cl, horizontal=True, label_visibility="collapsed")
                sql = "SELECT * FROM menu WHERE is_active=TRUE"; p = {}
                if sc != "Hamısı": sql += " AND category=:c"; p["c"] = sc
                sql += " ORDER BY price ASC"
                prods = run_query(sql, p)
                gr = {}
                for _, r in prods.iterrows():
                    n = r['item_name']; pts = n.split()
                    if len(pts)>1 and pts[-1] in ['S','M','L','XL','Single','Double']:
                        base = " ".join(pts[:-1]); gr.setdefault(base, []).append(r)
                    else: gr[n] = [r]
                
                cols = st.columns(4); i=0
                
                @st.dialog("Seçim")
                def show_v(bn, its):
                    st.write(f"### {bn}")
                    for it in its:
                        lbl = it['item_name'].replace(bn, "").strip()
                        c_b, c_p = st.columns([3,1])
                        if c_b.button(f"{lbl}", key=f"v_{it['id']}", use_container_width=True):
                            st.session_state.cart.append({'item_name':it['item_name'], 'price':float(it['price']), 'qty':1, 'is_coffee':it['is_coffee']}); st.rerun()
                        c_p.write(f"{it['price']}")

                for bn, its in gr.items():
                    with cols[i%4]:
                        if len(its)>1:
                            st.markdown(f"<div class='pos-card-header'>{bn}</div><div class='pos-card-body'>Seçim</div>", unsafe_allow_html=True)
                            if st.button("SEÇ", key=f"g_{bn}", use_container_width=True): show_v(bn, its)
                        else:
                            it = its[0]
                            st.markdown(f"<div class='pos-card-header'>{it['item_name']}</div><div class='pos-card-body'><div class='pos-price'>{it['price']}</div></div>", unsafe_allow_html=True)
                            if st.button("ƏLAVƏ", key=f"s_{it['id']}", use_container_width=True):
                                st.session_state.cart.append({'item_name':it['item_name'], 'price':float(it['price']), 'qty':1, 'is_coffee':it['is_coffee']}); st.rerun()
                    i+=1

    # --- RECEIPT DIALOG ---
    @st.dialog("Çap Edin")
    def show_receipt():
        if 'last_sale' in st.session_state:
            ls = st.session_state.last_sale
            h = get_setting("receipt_header", "EMALATXANA COFFEE")
            f = get_setting("receipt_footer", "Bizi seçdiyiniz üçün təşəkkürlər!")
            st.markdown(f"""
            <div style="width:300px; background:white; padding:20px; font-family:monospace; border:1px dashed #333; margin:0 auto;">
                <h3 style="text-align:center; margin:0;">{h}</h3>
                <p style="text-align:center; font-size:12px;">Tarix: {ls['date']}<br>Çek №: {ls['id']}</p>
                <hr>
                <div style="font-size:14px;">{ls['items'].replace(',', '<br>')}</div>
                <hr>
                <h2 style="text-align:right;">CƏM: {ls['total']:.2f} ₼</h2>
                <hr>
                <p style="text-align:center; font-size:12px;">{f}</p>
            </div>
            """, unsafe_allow_html=True)
            st.info("Printerdən (Ctrl+P) çap edin.")

    if 'last_sale' in st.session_state and st.session_state.last_sale:
        show_receipt()
        st.session_state.last_sale = None

    if role == 'admin':
        tabs = st.tabs(["POS", "📦 Anbar", "📜 Resept", "Analitika", "CRM", "Menyu", "⚙️ Ayarlar", "Admin", "QR"])
        with tabs[0]: render_pos_interface()
        
        with tabs[1]: # Anbar
            st.subheader("📦 Anbar")
            cats = run_query("SELECT DISTINCT category FROM ingredients")
            all_cats = ["Hamısı"] + (cats['category'].tolist() if not cats.empty else [])
            f_cat = st.selectbox("Kateqoriya", all_cats)
            
            c_add, c_list = st.columns([1, 2])
            with c_add:
                with st.form("stk"):
                    st.write("Yeni Mal"); n=st.text_input("Ad"); q=st.number_input("Say"); u=st.selectbox("Vahid",["gr","ml","ədəd"]); c=st.selectbox("Kat",["Bar","Süd","Sirop","Qablaşdırma"])
                    if st.form_submit_button("Əlavə Et"):
                        run_action("INSERT INTO ingredients (name,stock_qty,unit,category) VALUES (:n,:q,:u,:c) ON CONFLICT (name) DO UPDATE SET stock_qty=ingredients.stock_qty+:q", {"n":n,"q":q,"u":u,"c":c}); st.rerun()
            
            # --- INTERAKTIV ANBAR KARTLARI (DIALOG EDIT) ---
            @st.dialog("Mal Düzəlişi")
            def edit_stock(item_id, item_name, current_qty):
                st.write(f"**{item_name}** (# {item_id})")
                new_q = st.number_input("Yeni Stok", value=float(current_qty))
                if st.button("Yadda Saxla"):
                    run_action("UPDATE ingredients SET stock_qty=:q WHERE id=:id", {"q":new_q, "id":item_id})
                    st.success("Yeniləndi!"); st.rerun()

            with c_list:
                sql = "SELECT * FROM ingredients"; p = {}
                if f_cat != "Hamısı": sql += " WHERE category=:c"; p['c'] = f_cat
                sql += " ORDER BY category, name"
                df = run_query(sql, p)
                if not df.empty:
                    # 2 sütunlu grid
                    cols = st.columns(2)
                    for idx, r in df.iterrows():
                        with cols[idx % 2]:
                            stat = "low" if r['stock_qty'] <= r['min_limit'] else "ok"
                            # CLICKABLE CARD SIMULATION
                            if st.button(f"{r['name']} ({r['stock_qty']})", key=f"ed_{r['id']}", use_container_width=True):
                                edit_stock(r['id'], r['name'], r['stock_qty'])
                            st.caption(f"ID: #{r['id']} | {r['category']}")

        with tabs[2]: # Resept
            st.subheader("📜 Reseptlər")
            c1, c2 = st.columns([1, 2])
            with c1:
                ms = run_query("SELECT item_name FROM menu WHERE is_active=TRUE")
                if not ms.empty: st.session_state.selected_recipe_product = st.selectbox("Məhsul", sorted(ms['item_name'].unique()))
            with c2:
                if st.session_state.selected_recipe_product:
                    p = st.session_state.selected_recipe_product
                    st.write(f"**{p}** Tərkibi:")
                    rs = run_query("SELECT id, ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m", {"m":p})
                    st.dataframe(rs, hide_index=True, use_container_width=True)
                    if not rs.empty:
                        rid = st.selectbox("Silmək üçün", rs['id'])
                        if st.button("Sətri Sil"): run_action("DELETE FROM recipes WHERE id=:id", {"id":rid}); st.rerun()
                    st.divider()
                    ings = run_query("SELECT name, unit FROM ingredients")
                    if not ings.empty:
                        with st.form("add_r"):
                            c_i, c_q = st.columns(2)
                            i = c_i.selectbox("Xammal", ings['name'])
                            un = ings[ings['name']==i].iloc[0]['unit']
                            q = c_q.number_input(f"Miqdar ({un})", 0.1)
                            if st.form_submit_button("Əlavə Et"):
                                run_action("INSERT INTO recipes (menu_item_name, ingredient_name, quantity_required) VALUES (:m,:i,:q)", {"m":p,"i":i,"q":q}); st.rerun()

        with tabs[3]: render_analytics(is_admin=True)

        with tabs[4]: # CRM
            st.subheader("👥 CRM & Kuponlar")
            c_cp, c_mail = st.columns(2)
            with c_cp:
                st.markdown("#### 🎫 Kupon Yarat")
                k_type = st.selectbox("Növ", ["🎂 Ad Günü (24 Saat)", "🏷️ 20% Endirim", "🏷️ 30% Endirim", "🏷️ 50% Endirim"])
                if st.button("Bütün Müştərilərə Payla"):
                    custs = run_query("SELECT card_id FROM customers")
                    days = 1 if "Ad Günü" in k_type else 7
                    code = "disc_100_coffee" if "Ad Günü" in k_type else "disc_20" if "20%" in k_type else "disc_30" if "30%" in k_type else "disc_50"
                    for _, r in custs.iterrows():
                        run_action("INSERT INTO customer_coupons (card_id, coupon_type, expires_at) VALUES (:i, :c, NOW() + INTERVAL :d)", {"i":r['card_id'], "c":code, "d":f"{days} days"})
                    st.success("Paylandı!")
            st.divider(); st.dataframe(run_query("SELECT * FROM customers"))

        with tabs[5]: # Menyu
            st.subheader("📋 Menyu")
            with st.form("add_m"):
                n = st.text_input("Ad"); p = st.number_input("Qiymət"); c = st.text_input("Kateqoriya"); ic = st.checkbox("Kofedir?")
                if st.form_submit_button("Əlavə Et"):
                    run_action("INSERT INTO menu (item_name,price,category,is_active,is_coffee) VALUES (:n,:p,:c,TRUE,:ic)", {"n":n,"p":p,"c":c,"ic":ic}); st.rerun()
            st.dataframe(run_query("SELECT * FROM menu ORDER BY category, item_name"))

        with tabs[6]: # Ayarlar
            st.subheader("⚙️ Ayarlar & Çek Dizayneri")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Çek Tənzimləmələri**")
                rh = st.text_input("Çek Başlığı (Header)", value=get_setting("receipt_header", "EMALATXANA"))
                rf = st.text_input("Çek Sonu (Footer)", value=get_setting("receipt_footer", "Təşəkkürlər!"))
                if st.button("Yadda Saxla"): set_setting("receipt_header", rh); set_setting("receipt_footer", rf); st.success("Oldu!")
            with c2:
                st.markdown("**İşçi İdarəetməsi**")
                with st.form("new_u"):
                    u = st.text_input("Ad"); p = st.text_input("PIN"); r = st.selectbox("Rol", ["staff", "admin"])
                    if st.form_submit_button("Yarat"):
                        try: run_action("INSERT INTO users (username,password,role) VALUES (:u,:p,:r)", {"u":u,"p":hash_password(p),"r":r}); st.success("OK")
                        except: st.error("Bu ad var")

        with tabs[7]: # Admin
            st.subheader("🔧 Admin Backup")
            if st.button("📥 FULL BACKUP (XLSX)", type="primary"):
                try:
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                        clean_df_for_excel(run_query("SELECT * FROM customers")).to_excel(writer, sheet_name='Customers')
                        clean_df_for_excel(run_query("SELECT * FROM sales")).to_excel(writer, sheet_name='Sales')
                        clean_df_for_excel(run_query("SELECT * FROM menu")).to_excel(writer, sheet_name='Menu')
                        clean_df_for_excel(run_query("SELECT * FROM expenses")).to_excel(writer, sheet_name='Expenses')
                        clean_df_for_excel(run_query("SELECT * FROM system_logs")).to_excel(writer, sheet_name='Logs')
                    st.download_button("⬇️ Backup.xlsx", out.getvalue(), "Backup.xlsx")
                except Exception as e: st.error(e)

        with tabs[8]: # QR
            st.subheader("🖨️ QR Generator")
            cnt = st.number_input("Say", 1, 50)
            if st.button("Yarat"):
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for _ in range(cnt):
                        i = str(random.randint(10000000, 99999999)); tok = secrets.token_hex(8)
                        run_action("INSERT INTO customers (card_id, stars, type, secret_token) VALUES (:i, 0, 'standard', :st)", {"i":i, "st":tok})
                        img_data = generate_custom_qr(f"{APP_URL}/?id={i}&t={tok}", i)
                        zf.writestr(f"QR_{i}.png", img_data)
                st.download_button("📥 ZIP Yüklə", zip_buffer.getvalue(), "qrcodes.zip")

    elif role == 'staff':
        staff_tabs = st.tabs(["POS", "Mənim Satışlarım"])
        with staff_tabs[0]: render_pos_interface()
        with staff_tabs[1]: render_analytics(is_admin=False)

    # FOOTER
    st.markdown(f"<div class='footer'>Ironwaves POS {VERSION} | © 2026</div>", unsafe_allow_html=True)
