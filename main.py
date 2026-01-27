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
import base64
import json

# ==========================================
# === IRONWAVES POS - V3.0 TABLE EDITION ===
# ==========================================

VERSION = "v3.0 TABLE EDITION"

# --- INFRA ---
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
DOMAIN = "demo.ironwaves.store" 
APP_URL = f"https://{DOMAIN}"
DEFAULT_SENDER_EMAIL = "info@ironwaves.store" 

# --- CONFIG ---
st.set_page_config(page_title=f"Ironwaves POS {VERSION}", page_icon="☕", layout="wide", initial_sidebar_state="collapsed")

# --- CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Courier+Prime&display=swap');

    .stApp { font-family: 'Oswald', sans-serif !important; background-color: #F4F6F9; }
    header {visibility: hidden;} #MainMenu {visibility: hidden;} footer {visibility: hidden;} [data-testid="stSidebar"] { display: none; }
    .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
    
    /* TABS */
    button[data-baseweb="tab"] {
        font-family: 'Oswald', sans-serif !important; font-size: 18px !important; font-weight: 700 !important;
        background-color: white !important; border: 2px solid #FFCCBC !important; border-radius: 12px !important;
        margin: 0 4px !important; color: #555 !important; flex-grow: 1;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #FF6B35, #FF8C00) !important; border-color: #FF6B35 !important; color: white !important;
        box-shadow: 0 4px 12px rgba(255, 107, 53, 0.4);
    }

    /* POS CARDS */
    .pos-card-header { background: linear-gradient(135deg, #2E7D32, #43A047); color: white; padding: 10px; border-radius: 12px 12px 0 0; text-align: center; font-weight: bold; }
    .pos-card-body { background: white; border: 1px solid #ddd; border-top: none; border-radius: 0 0 12px 12px; padding: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .pos-price { font-size: 20px; color: #333; font-weight: bold; }

    /* TABLE CARDS (MASALAR) */
    .table-card {
        padding: 20px; border-radius: 15px; text-align: center; color: white; cursor: pointer;
        transition: transform 0.2s; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin-bottom: 15px;
    }
    .table-card:hover { transform: scale(1.03); }
    .table-empty { background: linear-gradient(135deg, #2E7D32, #66BB6A); border: 2px solid #1B5E20; }
    .table-occupied { background: linear-gradient(135deg, #C62828, #E53935); border: 2px solid #B71C1C; animation: pulse-red 2s infinite; }
    .table-num { font-size: 24px; font-weight: bold; }
    .table-bill { font-size: 18px; margin-top: 5px; font-weight: 500; }

    @keyframes pulse-red { 0% {box-shadow: 0 0 0 0 rgba(229, 57, 53, 0.4);} 70% {box-shadow: 0 0 0 10px rgba(229, 57, 53, 0);} 100% {box-shadow: 0 0 0 0 rgba(229, 57, 53, 0);} }

    /* BUTTONS */
    div.stButton > button { border-radius: 12px !important; height: 50px !important; font-weight: 700 !important; box-shadow: 0 4px 0 rgba(0,0,0,0.1) !important; transition: all 0.1s !important; }
    div.stButton > button:active { transform: translateY(3px) !important; box-shadow: none !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #FF6B35, #FF8C00) !important; color: white !important; }
    
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

# --- SCHEMA ---
def ensure_schema():
    with conn.session as s:
        # Tables for V3.0 Table Edition
        s.execute(text("CREATE TABLE IF NOT EXISTS tables (id SERIAL PRIMARY KEY, label TEXT, is_occupied BOOLEAN DEFAULT FALSE, items TEXT, total DECIMAL(10,2) DEFAULT 0, opened_at TIMESTAMP);"))
        
        # Existing Tables
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
        
        # Init 6 Tables if not exist
        res = s.execute(text("SELECT count(*) FROM tables")).fetchone()
        if res[0] == 0:
            for i in range(1, 7):
                s.execute(text("INSERT INTO tables (label, is_occupied) VALUES (:l, FALSE)"), {"l": f"Masa {i}"})
        
        s.commit()
        
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
def get_baku_now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=4))).replace(tzinfo=None)
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
    try: run_action("INSERT INTO system_logs (username, action, created_at) VALUES (:u, :a, NOW())", {"u":user, "a":action})
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
    if not RESEND_API_KEY: return False
    url = "https://api.resend.com/emails"
    headers = {"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"}
    payload = {"from": f"Emalatxana <{DEFAULT_SENDER_EMAIL}>", "to": [to_email], "subject": subject, "html": body}
    try: requests.post(url, json=payload, headers=headers); return True
    except: return False
def format_qty(val):
    if val % 1 == 0: return int(val)
    return val
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

# --- FUNCTIONS ---
def render_analytics(is_admin=False):
    tabs = st.tabs(["Satışlar", "Xərclər (P&L)", "Sistem Logları"]) if is_admin else st.tabs(["Mənim Satışlarım"])
    
    with tabs[0]:
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
            sales['created_at'] = pd.to_datetime(sales['created_at']) + pd.Timedelta(hours=4)
            t = sales['total'].sum()
            st.metric("Dövriyyə", f"{t:.2f} ₼")
            st.dataframe(sales[['id', 'created_at', 'items', 'total', 'payment_method', 'cashier']], hide_index=True, use_container_width=True)
        else: st.info("Satış yoxdur")

    if is_admin and len(tabs) > 1:
        with tabs[1]:
            st.markdown("### 💰 Xalis Mənfəət (P&L)")
            with st.expander("➕ Xərc Əlavə Et"):
                with st.form("add_exp"):
                    t=st.text_input("Təyinat"); a=st.number_input("Məbləğ",0.0); c=st.selectbox("Kat", ["İcarə","Kommunal","Maaş","Təchizat"]); 
                    if st.form_submit_button("Əlavə Et"): run_action("INSERT INTO expenses (title,amount,category) VALUES (:t,:a,:c)",{"t":t,"a":a,"c":c}); st.rerun()
            
            ts = run_query("SELECT SUM(total) as t FROM sales").iloc[0]['t'] or 0
            te = run_query("SELECT SUM(amount) as t FROM expenses").iloc[0]['t'] or 0
            np = ts - te
            c1,c2,c3 = st.columns(3)
            c1.metric("Gəlir", f"{ts:.2f} ₼"); c2.metric("Xərc", f"{te:.2f} ₼"); c3.metric("Mənfəət", f"{np:.2f} ₼", delta=np)
            st.dataframe(run_query("SELECT * FROM expenses ORDER BY created_at DESC LIMIT 50"), use_container_width=True)

        with tabs[2]:
            st.markdown("### 🕵️‍♂️ Giriş/Çıxış")
            logs = run_query("SELECT * FROM system_logs ORDER BY created_at DESC LIMIT 100")
            if not logs.empty:
                logs['created_at'] = pd.to_datetime(logs['created_at']) + pd.Timedelta(hours=4)
                st.dataframe(logs, use_container_width=True)

# --- TABLE MANAGEMENT LOGIC ---
def render_table_view():
    st.markdown("### 🍽️ MASALAR")
    tables = run_query("SELECT * FROM tables ORDER BY id")
    
    # Grid View (3 cols)
    cols = st.columns(3)
    for idx, row in tables.iterrows():
        with cols[idx % 3]:
            # Design based on status
            cls = "table-occupied" if row['is_occupied'] else "table-empty"
            status_text = f"{row['total']} ₼" if row['is_occupied'] else "BOŞ"
            
            # Clickable Card
            st.markdown(f"""
            <div class="table-card {cls}">
                <div class="table-num">{row['label']}</div>
                <div class="table-bill">{status_text}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action Button below card
            if st.button(f"{'👁️ Bax' if row['is_occupied'] else '➕ Sifariş'}", key=f"tbl_{row['id']}", use_container_width=True):
                st.session_state.selected_table = row.to_dict()
                # Load existing items to cart if occupied
                if row['is_occupied'] and row['items']:
                    try:
                        st.session_state.cart = json.loads(row['items'])
                    except: st.session_state.cart = []
                else:
                    st.session_state.cart = []
                st.rerun()

def render_order_interface():
    # Back Button
    if st.button("⬅️ Masalara Qayıt", use_container_width=True):
        st.session_state.selected_table = None
        st.session_state.cart = []
        st.rerun()

    tbl = st.session_state.selected_table
    st.markdown(f"### 📝 Sifariş: {tbl['label']}")
    
    c1, c2 = st.columns([1.5, 3])
    with c1:
        st.info("🧾 Cari Sifariş")
        
        # QR SCANNER
        with st.form("scanner_form", clear_on_submit=True):
            col_in, col_go = st.columns([3, 1])
            qr_val = col_in.text_input("Müştəri", label_visibility="collapsed", placeholder="Skan..."); sb = col_go.form_submit_button("🔍")
            if sb or qr_val:
                if qr_val:
                    try:
                        cid = qr_val.strip().split("id=")[1].split("&")[0] if "id=" in qr_val else qr_val.strip()
                        r = run_query("SELECT * FROM customers WHERE card_id=:id", {"id":cid})
                        if not r.empty: st.session_state.current_customer=r.iloc[0].to_dict(); st.toast("✅"); st.rerun()
                        else: st.error("Tapılmadı")
                    except: st.error("Xəta")
        
        if st.session_state.current_customer:
            c = st.session_state.current_customer
            st.success(f"👤 {c['card_id']} | ⭐ {c['stars']}")
            if st.button("Ləğv Et", key="cust_cl"): st.session_state.current_customer=None; st.rerun()

        # CART ITEMS
        tb = 0
        if st.session_state.cart:
            for i, it in enumerate(st.session_state.cart):
                sub = it['qty']*it['price']; tb+=sub
                st.markdown(f"<div style='background:white;padding:10px;margin-bottom:5px;border-radius:8px;display:flex;justify-content:space-between;align-items:center;border:1px solid #ddd;'><div style='flex:2'><b>{it['item_name']}</b></div><div style='flex:1'>{it['price']}</div><div style='flex:1;color:#E65100'>x{it['qty']}</div><div style='flex:1;text-align:right'>{sub:.1f}</div></div>", unsafe_allow_html=True)
                b1,b2,b3=st.columns([1,1,4])
                if b1.button("➖", key=f"m_{i}"): 
                    if it['qty']>1: it['qty']-=1 
                    else: st.session_state.cart.pop(i)
                    st.rerun()
                if b2.button("➕", key=f"p_{i}"): it['qty']+=1; st.rerun()
        
        st.markdown(f"<h2 style='text-align:right; color:#E65100'>{tb:.2f} ₼</h2>", unsafe_allow_html=True)
        
        # ACTIONS
        col_s, col_p = st.columns(2)
        if col_s.button("💾 YADDA SAXLA", use_container_width=True):
            items_json = json.dumps(st.session_state.cart)
            run_action("UPDATE tables SET is_occupied=TRUE, items=:i, total=:t WHERE id=:id", 
                       {"i":items_json, "t":tb, "id":tbl['id']})
            st.success("Sifariş Mətbəxə Göndərildi!")
            time.sleep(0.5)
            st.session_state.selected_table = None
            st.rerun()

        pm = st.radio("Ödəniş:", ["Nəğd", "Kart"], horizontal=True)
        if col_p.button("✅ ÖDƏNİŞ ET", type="primary", use_container_width=True):
            if not st.session_state.cart: st.error("Səbət boşdur!"); st.stop()
            
            try:
                istr = ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart])
                # 1. Record Sale
                run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i,:t,:p,:c,NOW())", 
                           {"i":istr,"t":tb,"p":("Cash" if pm=="Nəğd" else "Card"),"c":st.session_state.user})
                
                # 2. Deduct Inventory & Loyalty
                with conn.session as s:
                    for it in st.session_state.cart:
                        rs = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m"), {"m":it['item_name']}).fetchall()
                        for r in rs: s.execute(text("UPDATE ingredients SET stock_qty=stock_qty-:q WHERE name=:n"), {"q":float(r[1])*it['qty'], "n":r[0]})
                    if st.session_state.current_customer:
                        cid = st.session_state.current_customer['card_id']
                        gain = sum([x['qty'] for x in st.session_state.cart if x.get('is_coffee')])
                        s.execute(text("UPDATE customers SET stars=stars+:s WHERE card_id=:id"), {"s":gain, "id":cid})
                    s.commit()
                
                # 3. Clear Table
                run_action("UPDATE tables SET is_occupied=FALSE, items=NULL, total=0 WHERE id=:id", {"id":tbl['id']})
                
                st.session_state.last_sale = {"id": int(time.time()), "items": istr, "total": tb, "date": get_baku_now().strftime("%Y-%m-%d %H:%M"), "cashier": st.session_state.user}
                st.session_state.cart=[]
                st.session_state.selected_table = None
                st.rerun()
            except Exception as e: st.error(str(e))

    with c2:
        # MENU
        cats = run_query("SELECT DISTINCT category FROM menu WHERE is_active=TRUE")
        if not cats.empty:
            cl = ["Hamısı"] + sorted(cats['category'].tolist())
            sc = st.radio("Kat", cl, horizontal=True, label_visibility="collapsed")
            sql = "SELECT * FROM menu WHERE is_active=TRUE"; p = {}; 
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

# --- RECEIPT ---
def generate_receipt_html(sale_data):
    r_header = get_setting("receipt_header", "EMALATXANA")
    r_address = get_setting("receipt_address", "Bakı şəhəri")
    r_footer = get_setting("receipt_footer", "Təşəkkürlər!")
    r_logo_b64 = get_setting("receipt_logo_base64", "")
    s_logo = get_setting("receipt_show_logo", "True") == "True"
    s_date = get_setting("receipt_show_date", "True") == "True"
    s_cashier = get_setting("receipt_show_cashier", "True") == "True"
    s_id = get_setting("receipt_show_id", "True") == "True"
    
    logo_html = f'<img src="data:image/png;base64,{r_logo_b64}" class="receipt-logo"><br>' if s_logo and r_logo_b64 else ''
    items_html = "<table style='width:100%; border-collapse: collapse;'>"
    if isinstance(sale_data['items'], str):
        for item in sale_data['items'].split(', '):
            if " x" in item: parts = item.rsplit(" x", 1); name = parts[0]; qty = parts[1]
            else: name = item; qty = "1"
            items_html += f"<tr><td style='text-align:left;'>{name}</td><td style='text-align:right;'>x{qty}</td></tr>"
    items_html += "</table>"

    return f"""
    <div class="receipt-container">
        {logo_html}<div class="receipt-header">{r_header}</div>
        <div class="receipt-info">{r_address}<br>{'TARİX: ' + sale_data['date'] + '<br>' if s_date else ''}{'ÇEK №: ' + str(sale_data['id']) + '<br>' if s_id else ''}{'KASSİR: ' + sale_data['cashier'] if s_cashier else ''}</div>
        <div class="receipt-items">{items_html}</div>
        <div class="receipt-total">CƏM: {sale_data['total']:.2f} ₼</div>
        <div class="receipt-footer">{r_footer}<br>www.ironwaves.store</div>
    </div>
    """

@st.dialog("Çap Edin")
def show_receipt_dialog():
    if 'last_sale' in st.session_state and st.session_state.last_sale:
        st.markdown(generate_receipt_html(st.session_state.last_sale), unsafe_allow_html=True)
        st.info("Çap etmək üçün: Ctrl + P")

# --- MAIN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []
if 'current_customer' not in st.session_state: st.session_state.current_customer = None
if 'last_sale' not in st.session_state: st.session_state.last_sale = None
if 'selected_table' not in st.session_state: st.session_state.selected_table = None

check_session_token()
if st.session_state.get('logged_in'): run_action("UPDATE users SET last_seen = NOW() WHERE username = :u", {"u": st.session_state.user})
if 'last_sale' in st.session_state and st.session_state.last_sale: show_receipt_dialog(); st.session_state.last_sale = None

if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown(f"<h1 style='text-align:center; color:#FF6B35;'>☕ EMALATXANA</h1><h5 style='text-align:center; color:#777;'>{VERSION}</h5>", unsafe_allow_html=True)
        tabs = st.tabs(["İŞÇİ", "ADMİN"])
        with tabs[0]:
            with st.form("staff_login"):
                pin = st.text_input("PIN", type="password")
                if st.form_submit_button("Giriş", use_container_width=True):
                    udf = run_query("SELECT * FROM users WHERE role='staff'")
                    found = False
                    for _, row in udf.iterrows():
                        if verify_password(pin, row['password']):
                            st.session_state.logged_in=True; st.session_state.user=row['username']; st.session_state.role='staff'
                            tok=secrets.token_urlsafe(16); run_action("INSERT INTO active_sessions (token,username,role) VALUES (:t,:u,:r)", {"t":tok,"u":row['username'],"r":'staff'})
                            log_system(row['username'], "Login (Staff)"); st.query_params["token"] = tok; st.rerun(); found=True; break
                    if not found: st.error("Səhv PIN!")
        with tabs[1]:
            with st.form("admin_login"):
                u = st.text_input("User"); p = st.text_input("Pass", type="password")
                if st.form_submit_button("Admin Giriş", use_container_width=True):
                    udf = run_query("SELECT * FROM users WHERE LOWER(username)=LOWER(:u) AND role='admin'", {"u":u})
                    if not udf.empty and verify_password(p, udf.iloc[0]['password']):
                        st.session_state.logged_in=True; st.session_state.user=u; st.session_state.role='admin'
                        tok=secrets.token_urlsafe(16); run_action("INSERT INTO active_sessions (token,username,role) VALUES (:t,:u,:r)", {"t":tok,"u":u,"r":'admin'})
                        log_system(u, "Login (Admin)"); st.query_params["token"] = tok; st.rerun()
                    else: st.error("Səhv!")
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
        tabs = st.tabs(["POS (Masa)", "📦 Anbar", "📜 Resept", "Analitika", "CRM", "Menyu", "⚙️ Ayarlar", "Admin", "QR"])
        with tabs[0]:
            if st.session_state.selected_table: render_order_interface()
            else: render_table_view()
        
        with tabs[1]: # Anbar
            st.subheader("📦 Anbar")
            cats = run_query("SELECT DISTINCT category FROM ingredients")
            all_cats = ["Hamısı"] + (cats['category'].tolist() if not cats.empty else [])
            f_cat = st.selectbox("Filtr", all_cats)
            c1, c2 = st.columns([1, 2])
            with c1:
                with st.form("stk"):
                    st.write("Yeni Mal"); n=st.text_input("Ad"); q=st.number_input("Say"); u=st.selectbox("Vahid",["gr","ml","ədəd"]); c=st.selectbox("Kat",["Bar","Süd","Sirop","Qablaşdırma"])
                    if st.form_submit_button("Əlavə Et"): run_action("INSERT INTO ingredients (name,stock_qty,unit,category) VALUES (:n,:q,:u,:c) ON CONFLICT (name) DO UPDATE SET stock_qty=ingredients.stock_qty+:q", {"n":n,"q":q,"u":u,"c":c}); st.rerun()
            with c2:
                sql = "SELECT * FROM ingredients"; p = {}
                if f_cat != "Hamısı": sql += " WHERE category=:c"; p['c'] = f_cat
                sql += " ORDER BY category, name"; df = run_query(sql, p)
                @st.dialog("Düzəliş")
                def ed_stk(id, n, q):
                    nq = st.number_input("Yeni", value=float(q))
                    if st.button("Saxla"): run_action("UPDATE ingredients SET stock_qty=:q WHERE id=:id", {"q":nq,"id":id}); st.rerun()
                if not df.empty:
                    cols = st.columns(2)
                    for idx, r in df.iterrows():
                        with cols[idx%2]:
                            if st.button(f"{r['name']} ({format_qty(r['stock_qty'])})", key=f"iv_{r['id']}", use_container_width=True): ed_stk(r['id'], r['name'], r['stock_qty'])

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
                    for _, row in rs.iterrows():
                        rc1, rc2, rc3 = st.columns([3, 1, 1])
                        rc1.write(f"{row['ingredient_name']}")
                        new_q = rc2.text_input("Miqdar", value=str(row['quantity_required']), key=f"rq_{row['id']}", label_visibility="collapsed")
                        if rc3.button("Yenilə", key=f"rup_{row['id']}"): run_action("UPDATE recipes SET quantity_required=:q WHERE id=:id", {"q":float(new_q), "id":row['id']}); st.rerun()
                        if rc3.button("Sil", key=f"rdel_{row['id']}"): run_action("DELETE FROM recipes WHERE id=:id", {"id":row['id']}); st.rerun()
                    st.divider()
                    ings = run_query("SELECT name, unit FROM ingredients")
                    if not ings.empty:
                        with st.form("add_r"):
                            c_i, c_q = st.columns(2)
                            i = c_i.selectbox("Xammal", ings['name'])
                            un = ings[ings['name']==i].iloc[0]['unit']; q = c_q.number_input(f"Miqdar ({un})", 0.1)
                            if st.form_submit_button("Əlavə Et"): run_action("INSERT INTO recipes (menu_item_name, ingredient_name, quantity_required) VALUES (:m,:i,:q)", {"m":p,"i":i,"q":q}); st.rerun()

        with tabs[3]: render_analytics(is_admin=True)

        with tabs[4]: # CRM
            st.subheader("👥 CRM")
            c_cp, c_mail = st.columns(2)
            with c_cp:
                if st.button("Ad Günü Kuponu Payla"):
                    custs = run_query("SELECT card_id FROM customers")
                    for _, r in custs.iterrows(): run_action("INSERT INTO customer_coupons (card_id, coupon_type, expires_at) VALUES (:i, 'disc_100_coffee', NOW() + INTERVAL '1 day')", {"i":r['card_id']})
                    st.success("Paylandı!")
            with c_mail:
                with st.form("mail"):
                    sub = st.text_input("Mövzu"); msg = st.text_area("Mesaj"); 
                    if st.form_submit_button("Göndər"):
                        cs = run_query("SELECT email FROM customers WHERE email IS NOT NULL")
                        for _, r in cs.iterrows(): send_email(r['email'], sub, msg)
                        st.success("Getdi!")
            st.dataframe(run_query("SELECT * FROM customers"))

        with tabs[5]: # Menyu
            st.subheader("📋 Menyu")
            with st.expander("📥 Excel"):
                up = st.file_uploader("Fayl", type=['xlsx'])
                if up and st.button("Yüklə"):
                    df = pd.read_excel(up); run_action("DELETE FROM menu")
                    for _, row in df.iterrows(): run_action("INSERT INTO menu (item_name,price,category,is_active,is_coffee) VALUES (:n,:p,:c,TRUE,:ic)", {"n":row['item_name'],"p":row['price'],"c":row['category'],"ic":row.get('is_coffee',False)})
                    st.rerun()
            with st.form("nm"):
                n=st.text_input("Ad"); p=st.number_input("Qiymət"); c=st.text_input("Kat"); ic=st.checkbox("Kofe?")
                if st.form_submit_button("Əlavə"): run_action("INSERT INTO menu (item_name,price,category,is_active,is_coffee) VALUES (:n,:p,:c,TRUE,:ic)", {"n":n,"p":p,"c":c,"ic":ic}); st.rerun()
            st.dataframe(run_query("SELECT * FROM menu"))

        with tabs[6]: # Ayarlar
            st.subheader("⚙️ Ayarlar")
            c1, c2 = st.columns(2)
            with c1:
                rh = st.text_input("Çek Başlıq", value=get_setting("receipt_header", "EMALATXANA"))
                rf = st.text_input("Çek Footer", value=get_setting("receipt_footer", "Təşəkkürlər!"))
                lf = st.file_uploader("Logo")
                if lf and st.button("Logonu Yadda Saxla"): set_setting("receipt_logo_base64", image_to_base64(lf)); st.success("OK")
                if st.button("Mətni Saxla"): set_setting("receipt_header", rh); set_setting("receipt_footer", rf); st.success("OK")
            with c2:
                with st.form("nu"):
                    u=st.text_input("Ad"); p=st.text_input("PIN"); r=st.selectbox("Rol",["staff","admin"])
                    if st.form_submit_button("Yarat"): run_action("INSERT INTO users (username,password,role) VALUES (:u,:p,:r)", {"u":u,"p":hash_password(p),"r":r}); st.success("OK")

        with tabs[7]: # Admin
            if st.button("📥 FULL BACKUP"):
                out = BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    for t in ["customers", "sales", "menu", "users", "ingredients", "recipes", "system_logs", "tables"]:
                        clean_df_for_excel(run_query(f"SELECT * FROM {t}")).to_excel(writer, sheet_name=t.capitalize())
                st.download_button("⬇️ Endir", out.getvalue(), "Backup.xlsx")

        with tabs[8]: # QR
            cnt = st.number_input("Say", 1, 50); k = st.selectbox("Növ", ["Standard", "Termos", "10%", "20%"])
            if st.button("Yarat"):
                zb = BytesIO()
                with zipfile.ZipFile(zb, "w") as zf:
                    for _ in range(cnt):
                        i = str(random.randint(10000000, 99999999)); tok = secrets.token_hex(8)
                        ct = "thermos" if k=="Termos" else "standard"
                        run_action("INSERT INTO customers (card_id, stars, type, secret_token) VALUES (:i, 0, :t, :st)", {"i":i, "t":ct, "st":tok})
                        zf.writestr(f"QR_{i}.png", generate_custom_qr(f"{APP_URL}/?id={i}&t={tok}", i))
                st.download_button("📥 ZIP", zb.getvalue(), "qrcodes.zip")

    elif role == 'staff':
        staff_tabs = st.tabs(["POS (Masa)", "Mənim Satışlarım"])
        with staff_tabs[0]:
            if st.session_state.selected_table: render_order_interface()
            else: render_table_view()
        with staff_tabs[1]: render_analytics(is_admin=False)

    st.markdown(f"<div class='footer'>Ironwaves POS {VERSION} | © 2026</div>", unsafe_allow_html=True)
