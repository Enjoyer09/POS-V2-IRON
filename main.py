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
# === IRONWAVES POS - V2.7 STABLE (FIXED) ===
# ==========================================

VERSION = "v2.7 STABLE (Customer Fixed)"

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
    header, #MainMenu, footer, [data-testid="stSidebar"] { display: none !important; }
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

    /* BUTTONS */
    div.stButton > button { 
        border-radius: 12px !important; height: 60px !important; font-weight: 700 !important; 
        box-shadow: 0 4px 0 rgba(0,0,0,0.1) !important; transition: all 0.1s !important; 
    }
    div.stButton > button:active { transform: translateY(3px) !important; box-shadow: none !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #FF6B35, #FF8C00) !important; color: white !important; }

    /* TABLE BUTTONS */
    div.stButton > button[kind="secondary"] {
        background: linear-gradient(135deg, #43A047, #2E7D32) !important;
        color: white !important; border: 2px solid #1B5E20 !important;
        height: 120px !important; font-size: 24px !important; white-space: pre-wrap !important;
    }
    /* Occupied Table (Red) */
    .element-container button:disabled { opacity: 1 !important; } 
    
    /* CUSTOMER PORTAL STYLES */
    .cust-card {
        background: white; border-radius: 20px; padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08); text-align: center; margin-bottom: 20px;
        border: 1px solid #eee;
    }
    .coffee-grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-top: 20px; }
    .coffee-icon { width: 45px; opacity: 0.2; filter: grayscale(100%); transition: all 0.5s; }
    .coffee-icon.active { opacity: 1; filter: none; transform: scale(1.1); }
    
    /* RECEIPT */
    .paper-receipt {
        background-color: #fff; width: 100%; max-width: 350px; padding: 20px; margin: 0 auto;
        box-shadow: 0 0 15px rgba(0,0,0,0.1); font-family: 'Courier Prime', monospace; font-size: 13px; color: #000; border: 1px solid #ddd;
    }
    .receipt-cut-line { border-bottom: 2px dashed #000; margin: 15px 0; }
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
        
        # Init Tables
        res = s.execute(text("SELECT count(*) FROM tables")).fetchone()
        if res[0] == 0:
            for i in range(1, 7): s.execute(text("INSERT INTO tables (label, is_occupied) VALUES (:l, FALSE)"), {"l": f"MASA {i}"})
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
    if not RESEND_API_KEY: return False
    url = "https://api.resend.com/emails"
    headers = {"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"}
    payload = {"from": f"Emalatxana <{DEFAULT_SENDER_EMAIL}>", "to": [to_email], "subject": subject, "html": body}
    try: requests.post(url, json=payload, headers=headers); return True
    except: return False
def format_qty(val):
    if val % 1 == 0: return int(val)
    return val

# --- 1. MÜŞTƏRİ PORTALI (QR SCAN ENTRY POINT) ---
# Bu hissə login yoxlanışından ƏVVƏL gəlir!
qp = st.query_params
if "id" in qp:
    card_id = qp["id"]
    # Header
    c1, c2, c3 = st.columns([1,2,1])
    with c2: st.markdown(f"<h2 style='text-align:center; color:#FF6B35'>☕ EMALATXANA</h2>", unsafe_allow_html=True)
    
    user_df = run_query("SELECT * FROM customers WHERE card_id = :id", {"id": card_id})
    if not user_df.empty:
        user = user_df.iloc[0]
        
        # Qeydiyyat
        if not user['is_active']:
            st.info("🎉 Xoş gəlmisiniz! Qeydiyyatı tamamlayın.")
            with st.form("act_form"):
                em = st.text_input("Email"); dob = st.date_input("Doğum Tarixi", min_value=datetime.date(1950,1,1))
                if st.form_submit_button("Tamamla"):
                    run_action("UPDATE customers SET email=:e, birth_date=:b, is_active=TRUE WHERE card_id=:i", {"e":em, "b":dob, "i":card_id})
                    st.success("Hazırdır!"); st.rerun()
            st.stop()

        # Dashboard
        st.markdown(f"""
        <div class="cust-card">
            <h4 style="margin:0; color:#888;">BALANS</h4>
            <h1 style="color:#2E7D32; font-size: 48px; margin:0;">{user['stars']} / 10</h1>
            <p style="color:#555;">ID: {card_id}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Grid
        html_grid = '<div class="coffee-grid">'
        for i in range(10):
            icon_url = "https://cdn-icons-png.flaticon.com/512/751/751621.png"
            cls = "coffee-icon"
            style = ""
            if i == 9: 
                icon_url = "https://cdn-icons-png.flaticon.com/512/3209/3209955.png"
                if user['stars'] >= 10: style="opacity:1; filter:none; animation: bounce 1s infinite;"
            elif i < user['stars']: 
                style="opacity:1; filter:none;"
            html_grid += f'<img src="{icon_url}" class="{cls}" style="{style}">'
        html_grid += '</div>'
        st.markdown(html_grid, unsafe_allow_html=True)
        
        st.divider()
        if st.button("Çıxış"): st.query_params.clear(); st.rerun()
        st.stop() # POS ekranına keçməsin!

# --- SESSION & LOGIN MANAGER ---
def check_session_token():
    token = st.query_params.get("token")
    if token:
        try:
            res = run_query("SELECT username, role FROM active_sessions WHERE token=:t", {"t":token})
            if not res.empty:
                st.session_state.logged_in = True
                st.session_state.user = res.iloc[0]['username']
                st.session_state.role = res.iloc[0]['role']
                st.query_params.clear()
        except: pass

def cleanup_old_sessions():
    try: run_action("DELETE FROM active_sessions WHERE created_at < NOW() - INTERVAL '24 hours'")
    except: pass

# --- RECEIPT ---
def generate_receipt_html(sale_data):
    r_store = get_setting("receipt_store_name", "EMALATXANA")
    r_addr = get_setting("receipt_address", "Bakı ş., Mərkəz")
    r_phone = get_setting("receipt_phone", "+994 50 000 00 00")
    r_footer = get_setting("receipt_footer", "Bizi seçdiyiniz üçün təşəkkürlər!")
    r_logo_b64 = get_setting("receipt_logo_base64", "")
    logo_html = f'<div style="text-align:center;"><img src="data:image/png;base64,{r_logo_b64}" style="max-width:80px;"></div><br>' if r_logo_b64 else ''
    items_html = "<table style='width:100%; border-collapse: collapse; font-size:13px;'>"
    if isinstance(sale_data['items'], str):
        clean_items_str = sale_data['items']
        if clean_items_str.startswith("["):
             parts = clean_items_str.split("] ", 1)
             if len(parts) > 1: clean_items_str = parts[1]
        for item in clean_items_str.split(', '):
            if " x" in item: parts = item.rsplit(" x", 1); name = parts[0]; qty = parts[1]
            else: name = item; qty = "1"
            items_html += f"<tr><td style='text-align:left;'>{name}</td><td style='text-align:right;'>x{qty}</td></tr>"
    items_html += "</table>"
    header_extra = ""
    if sale_data['items'].startswith("["):
        header_extra = f"<div style='text-align:center; font-weight:bold; margin:5px 0;'>{sale_data['items'].split(']')[0][1:]}</div>"
    return f"""
    <div class="paper-receipt">
        {logo_html}<div style="text-align:center; font-weight:bold; font-size:18px;">{r_store}</div>
        <div style="text-align:center; font-size:12px; margin-bottom:5px;">{r_addr}</div>
        <div style="text-align:center; font-size:12px;">Tel: {r_phone}</div>
        <div class="receipt-cut-line"></div>
        <div style="font-size:12px;">TARİX: {sale_data['date']}<br>ÇEK №: {sale_data['id']}<br>KASSİR: {sale_data['cashier']}</div>
        {header_extra}<div class="receipt-cut-line"></div>{items_html}<div class="receipt-cut-line"></div>
        <div style="text-align:right; font-weight:bold; font-size:18px;">CƏM: {sale_data['total']:.2f} ₼</div>
        <div class="receipt-cut-line"></div><div style="text-align:center; font-size:12px; font-style:italic;">{r_footer}</div>
    </div>
    """

@st.dialog("Çap Edin")
def show_receipt_dialog():
    if 'last_sale' in st.session_state and st.session_state.last_sale:
        st.markdown(generate_receipt_html(st.session_state.last_sale), unsafe_allow_html=True)
        st.info("Çap etmək üçün: Ctrl + P")

# --- RENDERERS ---
def render_analytics(is_admin=False):
    tabs = st.tabs(["Satışlar", "Xərclər (P&L)", "Sistem Logları"]) if is_admin else st.tabs(["Mənim Satışlarım"])
    with tabs[0]:
        st.markdown("### 📊 Satış Hesabatı")
        f_mode = st.radio("Vaxt", ["Günlük", "Aylıq"], horizontal=True, key=f"am_{is_admin}")
        sql = "SELECT * FROM sales"; p = {}
        if not is_admin: sql += " WHERE cashier = :u"; p['u'] = st.session_state.user
        else: sql += " WHERE 1=1" 
        if f_mode == "Günlük": d = st.date_input("Gün", datetime.date.today(), key=f"d_{is_admin}"); sql += " AND DATE(created_at AT TIME ZONE 'Asia/Baku') = :d"; p['d'] = d
        else: d = st.date_input("Ay", datetime.date.today(), key=f"m_{is_admin}"); sql += " AND TO_CHAR(created_at AT TIME ZONE 'Asia/Baku', 'YYYY-MM') = :m"; p['m'] = d.strftime("%Y-%m")
        sql += " ORDER BY created_at DESC"; sales = run_query(sql, p)
        if not sales.empty:
            sales['created_at'] = pd.to_datetime(sales['created_at']) + pd.Timedelta(hours=4); t = sales['total'].sum()
            st.metric("Dövriyyə", f"{t:.2f} ₼"); st.dataframe(sales[['id', 'created_at', 'items', 'total', 'payment_method', 'cashier']], hide_index=True, use_container_width=True)
        else: st.info("Satış yoxdur")
    if is_admin and len(tabs) > 1:
        with tabs[1]:
            st.markdown("### 💰 Xalis Mənfəət (P&L)")
            with st.expander("➕ Xərc Əlavə Et"):
                with st.form("add_exp"):
                    t=st.text_input("Təyinat"); a=st.number_input("Məbləğ (AZN)", min_value=0.0); c=st.selectbox("Kat", ["İcarə","Kommunal","Maaş","Təchizat"]); 
                    if st.form_submit_button("Əlavə Et"): run_action("INSERT INTO expenses (title,amount,category,created_at) VALUES (:t,:a,:c,:time)",{"t":t,"a":a,"c":c, "time":get_baku_now()}); st.rerun()
            ts = run_query("SELECT SUM(total) as t FROM sales").iloc[0]['t'] or 0; te = run_query("SELECT SUM(amount) as t FROM expenses").iloc[0]['t'] or 0; np = ts - te
            c1,c2,c3 = st.columns(3); c1.metric("Gəlir", f"{ts:.2f} ₼"); c2.metric("Xərc", f"{te:.2f} ₼"); c3.metric("Mənfəət", f"{np:.2f} ₼", delta=np)
            st.dataframe(run_query("SELECT * FROM expenses ORDER BY created_at DESC LIMIT 50"), use_container_width=True)
        with tabs[2]:
            st.markdown("### 🕵️‍♂️ Giriş/Çıxış"); logs = run_query("SELECT * FROM system_logs ORDER BY created_at DESC LIMIT 100")
            if not logs.empty: logs['created_at'] = pd.to_datetime(logs['created_at']) + pd.Timedelta(hours=4); st.dataframe(logs, use_container_width=True)

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
            c = st.session_state.current_customer_ta
            st.success(f"👤 {c['card_id']} | ⭐ {c['stars']}")
            if st.button("Ləğv Et", key="ta_cl"): st.session_state.current_customer_ta=None; st.rerun()

        tb = 0
        if st.session_state.cart_takeaway:
            for i, it in enumerate(st.session_state.cart_takeaway):
                sub = it['qty']*it['price']; tb+=sub
                st.markdown(f"<div style='background:white;padding:10px;margin-bottom:5px;border-radius:8px;display:flex;justify-content:space-between;align-items:center;border:1px solid #ddd;'><div style='flex:2'><b>{it['item_name']}</b></div><div style='flex:1'>{it['price']}</div><div style='flex:1;color:#E65100'>x{it['qty']}</div><div style='flex:1;text-align:right'>{sub:.1f}</div></div>", unsafe_allow_html=True)
                b1,b2,b3=st.columns([1,1,4])
                if b1.button("➖", key=f"m_ta_{i}"): 
                    if it['qty']>1: it['qty']-=1 
                    else: st.session_state.cart_takeaway.pop(i)
                    st.rerun()
                if b2.button("➕", key=f"p_ta_{i}"): it['qty']+=1; st.rerun()
        
        st.markdown(f"<h2 style='text-align:right; color:#E65100'>{tb:.2f} ₼</h2>", unsafe_allow_html=True)
        pm = st.radio("Metod", ["Nəğd", "Kart"], horizontal=True, key="pm_ta")
        if st.button("✅ ÖDƏNİŞ ET", type="primary", use_container_width=True, key="pay_ta"):
            if not st.session_state.cart_takeaway: st.error("Boşdur!"); st.stop()
            try:
                istr = ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart_takeaway])
                run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i,:t,:p,:c,:time)", 
                           {"i":istr,"t":tb,"p":("Cash" if pm=="Nəğd" else "Card"),"c":st.session_state.user, "time":get_baku_now()})
                with conn.session as s:
                    for it in st.session_state.cart_takeaway:
                        rs = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m"), {"m":it['item_name']}).fetchall()
                        for r in rs: s.execute(text("UPDATE ingredients SET stock_qty=stock_qty-:q WHERE name=:n"), {"q":float(r[1])*it['qty'], "n":r[0]})
                    if st.session_state.current_customer_ta:
                        cid = st.session_state.current_customer_ta['card_id']
                        gain = sum([x['qty'] for x in st.session_state.cart_takeaway if x.get('is_coffee')])
                        s.execute(text("UPDATE customers SET stars=stars+:s WHERE card_id=:id"), {"s":gain, "id":cid})
                    s.commit()
                st.session_state.last_sale = {"id": int(time.time()), "items": istr, "total": tb, "date": get_baku_now().strftime("%Y-%m-%d %H:%M"), "cashier": st.session_state.user}
                st.session_state.cart_takeaway=[]; st.rerun()
            except Exception as e: st.error(str(e))
    with c2: render_menu_grid(st.session_state.cart_takeaway, "ta")

def render_tables_main():
    if st.session_state.selected_table: render_table_order()
    else: render_table_grid()

def render_table_grid():
    if st.session_state.role == 'admin':
        with st.expander("🛠️ Masa İdarəetməsi"):
            c_add, c_del = st.columns(2)
            with c_add:
                new_l = st.text_input("Masa Adı", key="new_table_input")
                if st.button("➕ Yarat", key="add_table_btn"): run_action("INSERT INTO tables (label) VALUES (:l)", {"l":new_l}); st.rerun()
            with c_del:
                tabs = run_query("SELECT label FROM tables")
                d_l = st.selectbox("Silinəcək", tabs['label'].tolist() if not tabs.empty else [], key="del_table_select")
                if st.button("❌ Sil", key="del_table_btn"): run_action("DELETE FROM tables WHERE label=:l", {"l":d_l}); st.rerun()
    st.markdown("### 🍽️ ZAL PLAN")
    tables = run_query("SELECT * FROM tables ORDER BY id")
    cols = st.columns(3)
    for idx, row in tables.iterrows():
        with cols[idx % 3]:
            is_occ = row['is_occupied']
            label = f"{row['label']}\n\n{row['total']} ₼" if is_occ else f"{row['label']}\n\n(BOŞ)"
            kind = "primary" if is_occ else "secondary"
            if st.button(label, key=f"tbl_btn_{row['id']}", type=kind, use_container_width=True):
                st.session_state.selected_table = row.to_dict()
                st.session_state.cart_table = json.loads(row['items']) if is_occ and row['items'] else []
                st.rerun()

def render_table_order():
    tbl = st.session_state.selected_table
    if st.button("⬅️ Masalara Qayıt", key="back_tbl", use_container_width=True):
        st.session_state.selected_table = None; st.session_state.cart_table = []; st.rerun()
    st.markdown(f"### 📝 Sifariş: {tbl['label']}")
    c1, c2 = st.columns([1.5, 3])
    with c1:
        st.info("Masa Sifarişi")
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
            c = st.session_state.current_customer_tb
            st.success(f"👤 {c['card_id']} | ⭐ {c['stars']}")
            if st.button("Ləğv Et", key="tb_cl"): st.session_state.current_customer_tb=None; st.rerun()
        tb = 0
        if st.session_state.cart_table:
            for i, it in enumerate(st.session_state.cart_table):
                sub = it['qty']*it['price']; tb+=sub
                st.markdown(f"<div style='background:white;padding:10px;margin-bottom:5px;border-radius:8px;display:flex;justify-content:space-between;align-items:center;border:1px solid #ddd;'><div style='flex:2'><b>{it['item_name']}</b></div><div style='flex:1'>{it['price']}</div><div style='flex:1;color:#E65100'>x{it['qty']}</div><div style='flex:1;text-align:right'>{sub:.1f}</div></div>", unsafe_allow_html=True)
                b1,b2,b3=st.columns([1,1,4])
                if b1.button("➖", key=f"m_tb_{i}"): 
                    if it['qty']>1: it['qty']-=1 
                    else: st.session_state.cart_table.pop(i)
                    st.rerun()
                if b2.button("➕", key=f"p_tb_{i}"): it['qty']+=1; st.rerun()
        st.markdown(f"<h2 style='text-align:right; color:#E65100'>{tb:.2f} ₼</h2>", unsafe_allow_html=True)
        col_s, col_p = st.columns(2)
        if col_s.button("💾 YADDA SAXLA", key="save_tbl", use_container_width=True):
            run_action("UPDATE tables SET is_occupied=TRUE, items=:i, total=:t WHERE id=:id", 
                       {"i":json.dumps(st.session_state.cart_table), "t":tb, "id":tbl['id']})
            st.success("Göndərildi!"); time.sleep(0.5); st.session_state.selected_table=None; st.rerun()
        pm = st.radio("Metod", ["Nəğd", "Kart"], horizontal=True, key="pm_tb")
        if col_p.button("✅ ÖDƏNİŞ ET", key="pay_tbl", type="primary", use_container_width=True):
            if not st.session_state.cart_table: st.error("Boşdur!"); st.stop()
            try:
                raw_items = ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart_table])
                istr = f"[{tbl['label']}] " + raw_items
                run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i,:t,:p,:c,:time)", 
                           {"i":istr,"t":tb,"p":("Cash" if pm=="Nəğd" else "Card"),"c":st.session_state.user, "time":get_baku_now()})
                with conn.session as s:
                    for it in st.session_state.cart_table:
                        rs = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m"), {"m":it['item_name']}).fetchall()
                        for r in rs: s.execute(text("UPDATE ingredients SET stock_qty=stock_qty-:q WHERE name=:n"), {"q":float(r[1])*it['qty'], "n":r[0]})
                    if st.session_state.current_customer_tb:
                        cid = st.session_state.current_customer_tb['card_id']
                        gain = sum([x['qty'] for x in st.session_state.cart_table if x.get('is_coffee')])
                        s.execute(text("UPDATE customers SET stars=stars+:s WHERE card_id=:id"), {"s":gain, "id":cid})
                    s.commit()
                run_action("UPDATE tables SET is_occupied=FALSE, items=NULL, total=0 WHERE id=:id", {"id":tbl['id']})
                st.session_state.last_sale = {"id": int(time.time()), "items": istr, "total": tb, "date": get_baku_now().strftime("%Y-%m-%d %H:%M"), "cashier": st.session_state.user}
                st.session_state.cart_table=[]; st.session_state.selected_table=None; st.rerun()
            except Exception as e: st.error(str(e))
    with c2: render_menu_grid(st.session_state.cart_table, "tb")

def render_menu_grid(cart_ref, key_prefix):
    cats = run_query("SELECT DISTINCT category FROM menu WHERE is_active=TRUE")
    if not cats.empty:
        cl = ["Hamısı"] + sorted(cats['category'].tolist())
        sc = st.radio("Kataloq", cl, horizontal=True, label_visibility="collapsed", key=f"cat_{key_prefix}")
        sql = "SELECT * FROM menu WHERE is_active=TRUE"; p = {}; 
        if sc != "Hamısı": sql += " AND category=:c"; p["c"] = sc
        sql += " ORDER BY price ASC"; prods = run_query(sql, p)
        gr = {}
        for _, r in prods.iterrows():
            n = r['item_name']; pts = n.split()
            if len(pts)>1 and pts[-1] in ['S','M','L','XL','Single','Double']:
                base = " ".join(pts[:-1]); gr.setdefault(base, []).append(r)
            else: gr[n] = [r]
        cols = st.columns(4); i=0
        @st.dialog("Ölçü Seçimi")
        def show_v(bn, its):
            st.write(f"### {bn}")
            for it in its:
                lbl = it['item_name'].replace(bn, "").strip()
                if st.button(f"{lbl}\n{it['price']} ₼", key=f"v_{it['id']}_{key_prefix}", use_container_width=True):
                    cart_ref.append({'item_name':it['item_name'], 'price':float(it['price']), 'qty':1, 'is_coffee':it['is_coffee']}); st.rerun()
        for bn, its in gr.items():
            with cols[i%4]:
                if len(its)>1:
                    label = f"{bn}\n(Seçim)"
                    if st.button(label, key=f"g_{bn}_{key_prefix}", use_container_width=True): show_v(bn, its)
                else:
                    it = its[0]; label = f"{it['item_name']}\n{it['price']} ₼"
                    if st.button(label, key=f"s_{it['id']}_{key_prefix}", use_container_width=True):
                        cart_ref.append({'item_name':it['item_name'], 'price':float(it['price']), 'qty':1, 'is_coffee':it['is_coffee']}); st.rerun()
            i+=1

# --- INIT STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart_takeaway' not in st.session_state: st.session_state.cart_takeaway = []
if 'cart_table' not in st.session_state: st.session_state.cart_table = []
if 'current_customer_ta' not in st.session_state: st.session_state.current_customer_ta = None
if 'current_customer_tb' not in st.session_state: st.session_state.current_customer_tb = None
if 'last_sale' not in st.session_state: st.session_state.last_sale = None
if 'selected_table' not in st.session_state: st.session_state.selected_table = None
if 'selected_recipe_product' not in st.session_state: st.session_state.selected_recipe_product = None

check_session_token()
if st.session_state.get('logged_in'):
    cleanup_old_sessions()
    run_action("UPDATE users SET last_seen = :t WHERE username = :u", {"t":get_baku_now(), "u": st.session_state.user})

if 'last_sale' in st.session_state and st.session_state.last_sale: show_receipt_dialog(); st.session_state.last_sale = None

# --- MAIN ---
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown(f"<h1 style='text-align:center; color:#FF6B35;'>☕ EMALATXANA</h1><h5 style='text-align:center; color:#777;'>{VERSION}</h5>", unsafe_allow_html=True)
        tabs = st.tabs(["İŞÇİ", "ADMİN"])
        with tabs[0]:
            with st.form("staff_login"):
                pin = st.text_input("PIN", type="password"); 
                if st.form_submit_button("Giriş", use_container_width=True):
                    udf = run_query("SELECT * FROM users WHERE role='staff'")
                    found = False
                    for _, row in udf.iterrows():
                        if verify_password(pin, row['password']):
                            st.session_state.logged_in=True; st.session_state.user=row['username']; st.session_state.role='staff'
                            tok=secrets.token_urlsafe(16); run_action("INSERT INTO active_sessions (token,username,role,created_at) VALUES (:t,:u,:r,:time)", {"t":tok,"u":row['username'],"r":'staff',"time":get_baku_now()})
                            log_system(row['username'], "Login (Staff)"); st.query_params["token"] = tok; st.rerun(); found=True; break
                    if not found: st.error("Yanlış PIN!")
        with tabs[1]:
            with st.form("admin_login"):
                u = st.text_input("User"); p = st.text_input("Pass", type="password")
                if st.form_submit_button("Admin Giriş", use_container_width=True):
                    udf = run_query("SELECT * FROM users WHERE LOWER(username)=LOWER(:u) AND role='admin'", {"u":u})
                    if not udf.empty and verify_password(p, udf.iloc[0]['password']):
                        st.session_state.logged_in=True; st.session_state.user=u; st.session_state.role='admin'
                        tok=secrets.token_urlsafe(16); run_action("INSERT INTO active_sessions (token,username,role,created_at) VALUES (:t,:u,:r,:time)", {"t":tok,"u":u,"r":'admin',"time":get_baku_now()})
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
        tabs = st.tabs(["🏃‍♂️ AL-APAR", "🍽️ MASALAR", "📦 Anbar", "📜 Resept", "Analitika", "CRM", "Menyu", "⚙️ Ayarlar", "Admin", "QR"])
        with tabs[0]: render_takeaway()
        with tabs[1]: render_tables_main()
        with tabs[2]: # Anbar (NEW LOGIC)
            st.subheader("📦 Anbar")
            inv_tabs = st.tabs(["Bütün Mallar", "Xammal", "Təchizat"])
            
            # --- Inventory Dialog ---
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

            def render_inventory_list(filter_cat=None):
                sql = "SELECT * FROM ingredients"
                p = {}
                if filter_cat:
                    if filter_cat == "Xammal":
                        sql += " WHERE category IN ('Bar', 'Süd', 'Sirop')" 
                    elif filter_cat == "Təchizat":
                        sql += " WHERE category IN ('Qablaşdırma', 'Təsərrüfat')"
                sql += " ORDER BY name"
                df = run_query(sql, p)
                
                if not df.empty:
                    cols = st.columns(4) 
                    for idx, r in df.iterrows():
                        with cols[idx % 4]:
                            # Fix: Unique key for each button
                            key_suffix = filter_cat if filter_cat else "main"
                            label = f"{r['name']}\n{format_qty(r['stock_qty'])} {r['unit']}"
                            if st.button(label, key=f"inv_c_{r['id']}_{key_suffix}", use_container_width=True):
                                manage_stock(r['id'], r['name'], r['stock_qty'], r['unit'])
                else:
                    st.info("Mal yoxdur.")

            with inv_tabs[0]: # All
                render_inventory_list()
                st.divider()
                with st.expander("➕ Yeni Mal Yarat"):
                    with st.form("new_inv"):
                        n=st.text_input("Ad"); q=st.number_input("Say", min_value=0.0, key="ni_q"); u=st.selectbox("Vahid",["gr","ml","ədəd","litr","kq"]); c=st.selectbox("Kateqoriya",["Bar","Süd","Sirop","Qablaşdırma","Təsərrüfat"])
                        if st.form_submit_button("Yarat"):
                            run_action("INSERT INTO ingredients (name,stock_qty,unit,category) VALUES (:n,:q,:u,:c)", {"n":n,"q":q,"u":u,"c":c}); st.rerun()

            with inv_tabs[1]: render_inventory_list("Xammal")
            with inv_tabs[2]: render_inventory_list("Təchizat")

        with tabs[3]: # Resept (NEW SPLIT VIEW)
            st.subheader("📜 Reseptlər")
            rc1, rc2 = st.columns([1, 2])
            
            with rc1: 
                search_menu = st.text_input("🔍 Axtar", key="rec_search")
                sql = "SELECT item_name FROM menu WHERE is_active=TRUE"
                if search_menu: sql += f" AND item_name ILIKE '%{search_menu}%'"
                sql += " ORDER BY item_name"
                menu_items = run_query(sql)
                
                if not menu_items.empty:
                    for _, r in menu_items.iterrows():
                        if st.button(r['item_name'], key=f"rm_{r['item_name']}", use_container_width=True):
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
                        
                        recs = run_query("SELECT id, ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:n", {"n":p_name})
                        if not recs.empty:
                            for _, r in recs.iterrows():
                                c_tag, c_del = st.columns([4, 1])
                                unit = run_query("SELECT unit FROM ingredients WHERE name=:n", {"n":r['ingredient_name']}).iloc[0]['unit']
                                c_tag.markdown(f"**{r['ingredient_name']}** — {format_qty(r['quantity_required'])} {unit}")
                                if c_del.button("🗑️", key=f"rdel_{r['id']}"):
                                    run_action("DELETE FROM recipes WHERE id=:id", {"id":r['id']}); st.rerun()
                        else:
                            st.info("Resept boşdur.")

                        st.divider()
                        st.markdown("➕ **İnqrediyent Əlavə Et**")
                        all_ings = run_query("SELECT name, unit FROM ingredients ORDER BY name")
                        if not all_ings.empty:
                            c_sel, c_qty, c_btn = st.columns([2, 1, 1])
                            sel_ing = c_sel.selectbox("Xammal", all_ings['name'].tolist(), label_visibility="collapsed", key="new_r_ing")
                            sel_unit = all_ings[all_ings['name']==sel_ing].iloc[0]['unit']
                            sel_qty = c_qty.number_input(f"Miqdar ({sel_unit})", min_value=0.0, step=1.0, label_visibility="collapsed", key="new_r_qty")
                            
                            if c_btn.button("Əlavə", type="primary", use_container_width=True):
                                run_action("INSERT INTO recipes (menu_item_name, ingredient_name, quantity_required) VALUES (:m,:i,:q)", 
                                           {"m":p_name, "i":sel_ing, "q":sel_qty}); st.rerun()
                else:
                    st.info("👈 Soldan məhsul seçin")

        with tabs[4]: render_analytics(is_admin=True)
        with tabs[5]: # CRM
            st.subheader("👥 CRM"); c_cp, c_mail = st.columns(2)
            with c_cp:
                st.markdown("#### 🎫 Kuponlar")
                c1, c2 = st.columns(2)
                if c1.button("🎂 Ad Günü"): 
                    for _, r in run_query("SELECT card_id FROM customers").iterrows(): run_action("INSERT INTO customer_coupons (card_id, coupon_type, expires_at) VALUES (:i, 'disc_100_coffee', NOW() + INTERVAL '1 day')", {"i":r['card_id']})
                    st.success("Paylandı!")
                if c2.button("🏷️ 20%"):
                    for _, r in run_query("SELECT card_id FROM customers").iterrows(): run_action("INSERT INTO customer_coupons (card_id, coupon_type, expires_at) VALUES (:i, 'disc_20', NOW() + INTERVAL '7 days')", {"i":r['card_id']})
                    st.success("Paylandı!")
            all_customers = run_query("SELECT card_id, email, stars, type FROM customers")
            all_customers.insert(0, "Seç", False)
            with c_mail:
                st.markdown("#### 📧 Email")
                edited_df = st.data_editor(all_customers, hide_index=True, use_container_width=True)
                selected_emails = edited_df[edited_df["Seç"] == True]['email'].tolist()
                with st.form("mail"):
                    sub = st.text_input("Mövzu"); msg = st.text_area("Mesaj"); 
                    if st.form_submit_button("Seçilənlərə Göndər"):
                        if not selected_emails: st.error("Heç kim seçilməyib!")
                        else:
                            c = 0
                            for e in selected_emails: 
                                if e and send_email(e, sub, msg): c+=1
                            st.success(f"{c} email getdi!")

        with tabs[6]: # Menyu
            st.subheader("📋 Menyu")
            with st.expander("📥 Excel"):
                up = st.file_uploader("Fayl", type=['xlsx'])
                if up and st.button("Yüklə", key="xl_load"):
                    df = pd.read_excel(up); run_action("DELETE FROM menu")
                    for _, row in df.iterrows(): run_action("INSERT INTO menu (item_name,price,category,is_active,is_coffee) VALUES (:n,:p,:c,TRUE,:ic)", {"n":row['item_name'],"p":row['price'],"c":row['category'],"ic":row.get('is_coffee',False)}); st.rerun()
            with st.form("nm"):
                n=st.text_input("Ad"); p=st.number_input("Qiymət", min_value=0.0, key="menu_p"); c=st.text_input("Kat"); ic=st.checkbox("Kofe?")
                if st.form_submit_button("Əlavə"): run_action("INSERT INTO menu (item_name,price,category,is_active,is_coffee) VALUES (:n,:p,:c,TRUE,:ic)", {"n":n,"p":p,"c":c,"ic":ic}); st.rerun()
            ml = run_query("SELECT * FROM menu"); st.dataframe(ml)
            if not ml.empty:
                dm = st.selectbox("Silinəcək Məhsul", ml['item_name'].unique(), key="del_menu_select")
                if st.button("❌ Məhsulu Sil", key="btn_del_menu_item"): run_action("DELETE FROM menu WHERE item_name=:n", {"n":dm}); st.rerun()
        with tabs[7]: # Ayarlar
            st.subheader("⚙️ Ayarlar")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🧾 Çek (Manual Info)**")
                r_name = st.text_input("Mağaza Adı", value=get_setting("receipt_store_name", "EMALATXANA"))
                r_addr = st.text_input("Ünvan", value=get_setting("receipt_address", "Bakı"))
                r_phone = st.text_input("Telefon", value=get_setting("receipt_phone", "+994 55 000 00 00"))
                r_foot = st.text_input("Footer", value=get_setting("receipt_footer", "Təşəkkürlər!"))
                lf = st.file_uploader("Logo"); 
                if lf and st.button("Logo Saxla", key="sv_lg"): set_setting("receipt_logo_base64", image_to_base64(lf)); st.success("OK")
                if st.button("Məlumatları Saxla", key="sv_txt"): 
                    set_setting("receipt_store_name", r_name); set_setting("receipt_address", r_addr)
                    set_setting("receipt_phone", r_phone); set_setting("receipt_footer", r_foot)
                    st.success("Yadda saxlanıldı!")
                prev_html = f"""<div class="paper-receipt"><div style="text-align:center; font-weight:bold; font-size:16px;">{r_name}</div><div style="text-align:center; font-size:12px;">{r_addr}</div><div style="text-align:center; font-size:12px;">Tel: {r_phone}</div><hr style="border-top: 1px dashed black;"><div style="font-size:12px;">Latte... 5.00<br>Su... 1.00</div><hr style="border-top: 1px dashed black;"><div style="text-align:right; font-weight:bold;">CƏM: 6.00 ₼</div><div style="text-align:center; font-size:12px;">{r_foot}</div></div>"""
                st.markdown(prev_html, unsafe_allow_html=True)
            with c2:
                st.markdown("**🔐 Şifrə Dəyişmə**")
                all_users = run_query("SELECT username FROM users")
                target_user = st.selectbox("İstifadəçi Seç", all_users['username'].tolist(), key="cp_user")
                new_pass = st.text_input("Yeni Şifrə / PIN", type="password", key="cp_pass")
                if st.button("Şifrəni Yenilə"):
                    run_action("UPDATE users SET password=:p WHERE username=:u", {"p":hash_password(new_pass), "u":target_user})
                    st.success("Yeniləndi!")
                st.divider()
                st.markdown("**Yeni İşçi Yarat**")
                with st.form("nu"):
                    u=st.text_input("Ad"); p=st.text_input("PIN"); r=st.selectbox("Rol",["staff","admin"])
                    if st.form_submit_button("Yarat"): run_action("INSERT INTO users (username,password,role) VALUES (:u,:p,:r)", {"u":u,"p":hash_password(p),"r":r}); st.success("OK")
        with tabs[8]: # Admin
            st.subheader("🔧 Admin Tools")
            if st.button("📥 FULL BACKUP", key="bkp_btn"):
                out = BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    for t in ["customers", "sales", "menu", "users", "ingredients", "recipes", "system_logs", "tables", "expenses"]:
                        clean_df_for_excel(run_query(f"SELECT * FROM {t}")).to_excel(writer, sheet_name=t.capitalize())
                st.download_button("⬇️ Endir", out.getvalue(), "Backup.xlsx")
            st.divider()
            st.markdown("**⚠️ Restore from Backup**")
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
                                st.success("Bərpa olundu!")
                            except Exception as e: st.error(f"Xəta: {e}")
                    else: st.error("Şifrə səhvdir")

        with tabs[9]: # QR
            cnt = st.number_input("Say", value=1, min_value=1, key="qr_cnt"); k = st.selectbox("Növ", ["Standard", "Termos", "10%", "20%", "50%"])
            if st.button("Yarat", key="gen_qr"):
                zb = BytesIO()
                with zipfile.ZipFile(zb, "w") as zf:
                    for _ in range(cnt):
                        i = str(random.randint(10000000, 99999999)); tok = secrets.token_hex(8); ct = "thermos" if k=="Termos" else "standard"
                        run_action("INSERT INTO customers (card_id, stars, type, secret_token) VALUES (:i, 0, :t, :st)", {"i":i, "t":ct, "st":tok})
                        code = None
                        if "10%" in k: code="disc_10"
                        elif "20%" in k: code="disc_20"
                        elif "50%" in k: code="disc_50"
                        if code: run_action("INSERT INTO customer_coupons (card_id, coupon_type) VALUES (:i, :c)", {"i":i, "c":code})
                        zf.writestr(f"QR_{i}.png", generate_custom_qr(f"{APP_URL}/?id={i}&t={tok}", i))
                st.download_button("📥 ZIP", zb.getvalue(), "qrcodes.zip")

    elif role == 'staff':
        staff_tabs = st.tabs(["🏃‍♂️ AL-APAR", "🍽️ MASALAR", "Mənim Satışlarım"])
        with staff_tabs[0]: render_takeaway()
        with staff_tabs[1]: render_tables_main()
        with staff_tabs[2]: render_analytics(is_admin=False)

    st.markdown(f"<div class='footer'>Ironwaves POS {VERSION} | © 2026</div>", unsafe_allow_html=True)
