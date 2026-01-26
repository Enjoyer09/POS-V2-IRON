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
# === IRONWAVES POS - V2.1 STABLE (FINAL) ===
# ==========================================

VERSION = "v2.1 STABLE"

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
    .stApp { font-family: 'Oswald', sans-serif !important; background-color: #F4F6F9; }
    
    /* GİZLİ HİSSƏLƏR */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stSidebar"] { display: none; }
    
    .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
    
    /* ELEMENTLƏR */
    button[data-baseweb="tab"] {
        font-family: 'Oswald', sans-serif !important; font-weight: 700 !important;
        background-color: white !important; border: 1px solid #E0E0E0 !important; border-radius: 8px !important;
        margin: 0 4px !important; color: #555 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        border-color: #FF6B35 !important; color: #FF6B35 !important; background-color: #FFF3E0 !important;
    }
    div.stButton > button {
        border-radius: 10px !important; height: 48px !important; font-weight: 700 !important;
        box-shadow: 0 3px 0 rgba(0,0,0,0.1) !important; transition: all 0.1s !important;
    }
    div.stButton > button:active { transform: translateY(3px) !important; box-shadow: none !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #2E7D32, #43A047) !important; color: white !important; }

    /* MÜŞTƏRİ PORTALI STİLİ */
    .digital-card {
        background: white; border-radius: 20px; padding: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #eee;
        text-align: center; margin-bottom: 20px;
    }
    .thermos-vip {
        background: linear-gradient(135deg, #2E7D32, #66BB6A); color: white;
        padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 15px;
        box-shadow: 0 5px 15px rgba(46, 125, 50, 0.4);
    }
    .coffee-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; justify-items: center; margin-top: 20px; }
    .coffee-icon { width: 40px; opacity: 0.2; filter: grayscale(100%); transition: all 0.5s; }
    .coffee-icon.active { opacity: 1; filter: none; transform: scale(1.1); }
    .gift-box { width: 50px; animation: bounce 2s infinite; }
    
    @keyframes bounce { 0%, 20%, 50%, 80%, 100% {transform: translateY(0);} 40% {transform: translateY(-10px);} 60% {transform: translateY(-5px);} }
    </style>
""", unsafe_allow_html=True)

# --- DB CONNECTION ---
try:
    db_url = os.environ.get("STREAMLIT_CONNECTIONS_NEON_URL") or os.environ.get("DATABASE_URL")
    if not db_url: st.error("DB URL not found!"); st.stop()
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
        # CRM
        s.execute(text("CREATE TABLE IF NOT EXISTS customers (card_id TEXT PRIMARY KEY, stars INTEGER DEFAULT 0, type TEXT, email TEXT, birth_date TEXT, is_active BOOLEAN DEFAULT FALSE, last_visit TIMESTAMP, secret_token TEXT, gender TEXT, last_feedback_star INTEGER DEFAULT -1);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS customer_coupons (id SERIAL PRIMARY KEY, card_id TEXT, coupon_type TEXT, is_used BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, card_id TEXT, message TEXT, is_read BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS feedback (id SERIAL PRIMARY KEY, card_id TEXT, rating INTEGER, message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
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
def clean_df_for_excel(df):
    for col in df.select_dtypes(include=['datetime64[ns, UTC]', 'datetime64[ns]']).columns: df[col] = df[col].astype(str)
    return df
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

# =======================================================
# === MÜŞTƏRİ PORTALI (V1.1.2 MƏNTİQİ GERİ QAYTARILDI) ===
# =======================================================
query_params = st.query_params
if "id" in query_params:
    # URL-dən ID-ni al
    card_id = query_params["id"]
    token = query_params.get("t")
    
    # 1. Header (Logo/Ad)
    c1, c2, c3 = st.columns([1,2,1])
    with c2: st.markdown(f"<h2 style='text-align:center; color:#2E7D32'>☕ EMALATXANA</h2>", unsafe_allow_html=True)
    
    # 2. Bazadan yoxla
    try: 
        user_df = run_query("SELECT * FROM customers WHERE card_id = :id", {"id": card_id})
    except: 
        st.error("Sistem xətası."); st.stop()

    if not user_df.empty:
        user = user_df.iloc[0]
        
        # Token Security Check (Opsional)
        if user['secret_token'] and token and user['secret_token'] != token:
            st.warning("⚠️ Bu QR kod köhnəlib. Zəhmət olmasa yenisini istəyin.")
        
        # --- AKTİV OLMAYAN MÜŞTƏRİ (QEYDİYYAT & QAYDALAR) ---
        if not user['is_active']:
            st.info("🎉 Xoş gəlmisiniz! Zəhmət olmasa qeydiyyatı tamamlayın.")
            
            with st.form("activation_form"):
                em = st.text_input("📧 Email Ünvanı")
                dob = st.date_input("🎂 Doğum Tarixi", min_value=datetime.date(1950, 1, 1), max_value=datetime.date.today())
                gen = st.radio("Cinsiyyət:", ["Kişi", "Qadın", "Qeyd etmirəm"], horizontal=True)
                
                # --- İSTİFADƏÇİ RAZILAŞMASI (V1.1.2 Feature) ---
                with st.expander("📜 İstifadəçi Razılaşması və Qaydalar"):
                    st.markdown("""
                    **Emalatxana Loyallıq Proqramı Qaydaları:**
                    1. Hər kofe alışı 1 ulduz qazandırır.
                    2. 10 ulduz topladıqda 1 kofe hədiyyə olunur.
                    3. Qazanılan bonuslar nağd pula çevrilə bilməz.
                    4. Şirkət qaydaları dəyişdirmək hüququnu özündə saxlayır.
                    5. Sizin məlumatlarınız (Email, Doğum tarixi) yalnız bizdə saxlanılır və 3-cü tərəflərlə paylaşılmır.
                    """)
                
                agree = st.checkbox("Qaydalarla tanış oldum və razıyam")
                
                if st.form_submit_button("✅ Qeydiyyatı Tamamla"):
                    if agree and em:
                        g_code = "M" if gen=="Kişi" else "F" if gen=="Qadın" else "U"
                        run_action("UPDATE customers SET email=:e, birth_date=:b, gender=:g, is_active=TRUE WHERE card_id=:i", 
                                   {"e":em, "b":dob, "g":g_code, "i":card_id})
                        st.balloons()
                        st.success("Təbriklər! Hesabınız aktivləşdi.")
                        time.sleep(2); st.rerun()
                    else:
                        st.error("Zəhmət olmasa E-poçt yazın və Qaydaları qəbul edin.")
            st.stop() # Login ekranına keçməsin

        # --- AKTİV MÜŞTƏRİ (DASHBOARD) ---
        
        # Bildirişlər
        notifs = run_query("SELECT * FROM notifications WHERE card_id = :id AND is_read = FALSE", {"id": card_id})
        for _, n in notifs.iterrows():
            st.info(f"📩 {n['message']}")
            run_action("UPDATE notifications SET is_read = TRUE WHERE id = :nid", {"nid": n['id']})

        # Termos Statusu
        if user['type'] == 'thermos':
            st.markdown("""<div class="thermos-vip"><h3>♻️ EKO-TERM KLUBU (VIP)</h3><p>Təbiəti qoruduğun üçün təşəkkürlər!</p></div>""", unsafe_allow_html=True)

        # Kart & Ulduzlar
        st.markdown(f"""
        <div class="digital-card">
            <h4 style="margin:0; color:#555;">SİZİN BALANS</h4>
            <h1 style="color:#2E7D32; font-size: 48px; margin:0;">{user['stars']} / 10</h1>
            <p style="color:#888;">ID: {card_id}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Kofe Qridi (Vizual)
        html_grid = '<div class="coffee-grid">'
        for i in range(10):
            icon_url = "https://cdn-icons-png.flaticon.com/512/751/751621.png"
            cls = "coffee-icon"
            style = ""
            if i == 9: # Hədiyyə qutusu
                icon_url = "https://cdn-icons-png.flaticon.com/512/3209/3209955.png"
                if user['stars'] >= 10: cls += " gift-box active"; style="opacity:1; filter:none;"
            elif i < user['stars']: 
                cls += " active"; style="opacity:1; filter:none;"
            
            html_grid += f'<img src="{icon_url}" class="{cls}" style="{style}">'
        html_grid += '</div>'
        st.markdown(html_grid, unsafe_allow_html=True)
        
        st.write("")
        # Aktiv Kuponlar
        cps = run_query("SELECT * FROM customer_coupons WHERE card_id=:id AND is_used=FALSE AND (expires_at IS NULL OR expires_at > NOW())", {"id":card_id})
        if not cps.empty:
            st.markdown("#### 🎁 Sizin Hədiyyələr:")
            for _, cp in cps.iterrows():
                name = cp['coupon_type']
                if name == "disc_100_coffee": name = "🎂 Ad Günü: 1 Pulsuz Kofe"
                elif name == "disc_20": name = "🏷️ 20% Endirim"
                elif name == "disc_30": name = "🏷️ 30% Endirim"
                elif name == "disc_50": name = "🏷️ 50% Endirim"
                elif name == "thermos_welcome": name = "♻️ Xoşgəldin: İlk Kofe Bizdən!"
                st.success(name)

        st.divider()
        if st.button("🔴 Hesabdan Çıx"): st.query_params.clear(); st.rerun()
        
        # MÜŞTƏRİ GÖRÜNTÜSÜ BURADA BİTİR, LOGİNƏ KEÇMİR
        st.stop() 

    else:
        st.error("Kart tapılmadı! Adminə müraciət edin.")
        st.stop()


# ==========================================
# === STAFF / ADMIN AREA STARTS HERE ===
# ==========================================

# --- SESSION CHECK ---
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
            st.session_state.logged_in = False; st.rerun()
    st.divider()

    role = st.session_state.role
    
    # --- ANALYTICS FUNC ---
    def render_analytics(is_admin=False):
        st.markdown("### 📊 Satış Hesabatı")
        f_mode = st.radio("Rejim:", ["Günlük", "Aylıq", "Aralıq"], horizontal=True, key=f"an_m_{is_admin}")
        sql = "SELECT * FROM sales"; p = {}
        if not is_admin: sql += " WHERE cashier = :u"; p['u'] = st.session_state.user
        else: sql += " WHERE 1=1" 

        if f_mode == "Günlük":
            d = st.date_input("Gün", datetime.date.today(), key=f"d_{is_admin}")
            sql += " AND DATE(created_at AT TIME ZONE 'Asia/Baku') = :d"; p['d'] = d
        elif f_mode == "Aylıq":
            d = st.date_input("Ay", datetime.date.today(), key=f"m_{is_admin}")
            sql += " AND TO_CHAR(created_at AT TIME ZONE 'Asia/Baku', 'YYYY-MM') = :m"; p['m'] = d.strftime("%Y-%m")
        else:
            d1 = st.date_input("Başlanğıc", datetime.date.today(), key=f"d1_{is_admin}")
            d2 = st.date_input("Bitmə", datetime.date.today(), key=f"d2_{is_admin}")
            sql += " AND DATE(created_at AT TIME ZONE 'Asia/Baku') BETWEEN :d1 AND :d2"; p['d1'] = d1; p['d2'] = d2
        
        sql += " ORDER BY created_at DESC"
        sales = run_query(sql, p)
        if not sales.empty:
            sales['created_at'] = pd.to_datetime(sales['created_at']) + pd.Timedelta(hours=4)
            m1, m2, m3 = st.columns(3)
            m1.metric("Cəm Gəlir", f"{sales['total'].sum():.2f} ₼")
            m2.metric("Nağd", f"{sales[sales['payment_method']=='Cash']['total'].sum():.2f}")
            m3.metric("Kart", f"{sales[sales['payment_method']=='Card']['total'].sum():.2f}")
            st.dataframe(sales[['id', 'created_at', 'items', 'total', 'payment_method', 'cashier']], hide_index=True, use_container_width=True)
            if is_admin:
                with st.expander("🗑️ Satış Ləğvi (Admin)"):
                    with st.form("del_sale"):
                        sid = st.number_input("Satış ID", min_value=1)
                        apass = st.text_input("Admin Şifrə", type="password")
                        if st.form_submit_button("Sil"):
                            adm = run_query("SELECT password FROM users WHERE role='admin' LIMIT 1")
                            if not adm.empty and verify_password(apass, adm.iloc[0]['password']):
                                run_action("DELETE FROM sales WHERE id=:id", {"id":sid}); st.success("Silindi!"); time.sleep(1); st.rerun()
                            else: st.error("Şifrə yanlışdır")
        else: st.info("Satış yoxdur.")

    # --- POS INTERFACE FUNC ---
    def render_pos_interface():
        c1, c2 = st.columns([1.5, 3])
        # LEFT: CART
        with c1:
            st.info("🧾 Çek")
            # QR SCANNER
            with st.form("scanner_form", clear_on_submit=True):
                col_in, col_go = st.columns([3, 1])
                qr_val = col_in.text_input("Müştəri Kartı", label_visibility="collapsed", placeholder="Skan edin...")
                scan_btn = col_go.form_submit_button("🔍")
                if scan_btn or qr_val:
                    if qr_val:
                        try:
                            clean_input = qr_val.strip()
                            cid = clean_input
                            if "http" in clean_input or "id=" in clean_input:
                                try:
                                    parsed = urlparse(clean_input)
                                    qs = parse_qs(parsed.query)
                                    if 'id' in qs: cid = qs['id'][0]
                                except: pass
                            res = run_query("SELECT * FROM customers WHERE card_id=:id", {"id":cid})
                            if not res.empty: st.session_state.current_customer = res.iloc[0].to_dict(); st.toast(f"✅ {cid}"); st.rerun()
                            else: st.error(f"❌ Tapılmadı: {cid}")
                        except: st.error("Xəta")
            
            if st.session_state.current_customer:
                c = st.session_state.current_customer
                st.success(f"👤 {c['card_id']} | ⭐ **{c['stars']}**")
                if st.button("Ləğv Et", use_container_width=True): st.session_state.current_customer = None; st.rerun()

            # CART ITEMS
            if st.session_state.cart:
                tb = 0
                for i, it in enumerate(st.session_state.cart):
                    sub = it['qty'] * it['price']; tb += sub
                    st.markdown(f"""<div class="cart-item"><div style="flex:2; font-weight:bold;">{it['item_name']}</div><div style="flex:1;">{it['price']}</div><div style="flex:1; color:#E65100;">x{it['qty']}</div><div style="flex:1; text-align:right;">{sub:.1f}</div></div>""", unsafe_allow_html=True)
                    b1, b2, b3 = st.columns([1,1,4])
                    if b1.button("➖", key=f"m_{i}"):
                        if it['qty']>1: it['qty']-=1
                        else: st.session_state.cart.pop(i)
                        st.rerun()
                    if b2.button("➕", key=f"p_{i}"): it['qty']+=1; st.rerun()
                
                st.markdown(f"<h2 style='text-align:right; color:#E65100'>{tb:.2f} ₼</h2>", unsafe_allow_html=True)
                pm = st.radio("Ödəniş:", ["Nəğd", "Kart"], horizontal=True)
                if st.button("✅ ÖDƏNİŞ ET", type="primary", use_container_width=True):
                    try:
                        istr = ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart])
                        run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i,:t,:p,:c,NOW())", 
                                   {"i":istr,"t":tb,"p":("Cash" if pm=="Nəğd" else "Card"),"c":st.session_state.user})
                        with conn.session as s:
                            for item in st.session_state.cart:
                                rs = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m"), {"m":item['item_name']}).fetchall()
                                for r in rs: s.execute(text("UPDATE ingredients SET stock_qty=stock_qty-:q WHERE name=:n"), {"q":float(r[1])*item['qty'], "n":r[0]})
                            if st.session_state.current_customer:
                                cid = st.session_state.current_customer['card_id']
                                gain = sum([x['qty'] for x in st.session_state.cart if x.get('is_coffee')])
                                s.execute(text("UPDATE customers SET stars=stars+:s WHERE card_id=:id"), {"s":gain, "id":cid})
                            s.commit()
                        st.session_state.cart=[]; st.success("Satıldı!"); time.sleep(1); st.rerun()
                    except Exception as e: st.error(str(e))
            else: st.info("Səbət boşdur")

        # --- RIGHT: PRODUCTS ---
        with c2:
            cats = run_query("SELECT DISTINCT category FROM menu WHERE is_active=TRUE")
            if not cats.empty:
                cat_list = ["Hamısı"] + sorted(cats['category'].tolist())
                sc = st.radio("Kataloq", cat_list, horizontal=True, label_visibility="collapsed")
                sql = "SELECT * FROM menu WHERE is_active=TRUE"
                p = {}; 
                if sc != "Hamısı": sql += " AND category=:c"; p["c"] = sc
                sql += " ORDER BY price ASC"
                prods = run_query(sql, p)
                gr = {}
                for _, r in prods.iterrows():
                    n = r['item_name']; pts = n.split()
                    if len(pts)>1 and pts[-1] in ['S','M','L','XL','Single','Double']:
                        base = " ".join(pts[:-1])
                        gr.setdefault(base, []).append(r)
                    else: gr[n] = [r]
                
                cols = st.columns(4); i=0
                @st.dialog("Variant Seçimi")
                def show_v(bn, its):
                    st.markdown(f"### {bn}")
                    for it in its:
                        lbl = it['item_name'].replace(bn, "").strip()
                        c_b, c_p = st.columns([3,1])
                        if c_b.button(f"{lbl}", key=f"v_{it['id']}", use_container_width=True):
                            st.session_state.cart.append({'item_name':it['item_name'], 'price':float(it['price']), 'qty':1, 'is_coffee':it['is_coffee']}); st.rerun()
                        c_p.markdown(f"**{it['price']}**")

                for bn, its in gr.items():
                    with cols[i%4]:
                        if len(its)>1:
                            st.markdown(f"<div class='pos-card-header'>{bn}</div><div class='pos-card-body'>Seçim</div>", unsafe_allow_html=True)
                            if st.button("SEÇ", key=f"g_{bn}", use_container_width=True): show_v(bn, its)
                        else:
                            it = its[0]
                            st.markdown(f"<div class='pos-card-header'>{it['item_name']}</div><div class='pos-card-body'><div class='pos-price'>{it['price']} ₼</div></div>", unsafe_allow_html=True)
                            if st.button("ƏLAVƏ ET", key=f"s_{it['id']}", use_container_width=True):
                                st.session_state.cart.append({'item_name':it['item_name'], 'price':float(it['price']), 'qty':1, 'is_coffee':it['is_coffee']}); st.rerun()
                    i+=1

    if role == 'admin':
        tabs = st.tabs(["POS", "📦 Anbar", "📜 Resept", "Analitika", "CRM", "Menyu", "⚙️ Ayarlar", "Admin", "QR"])
        with tabs[0]: render_pos_interface()
        with tabs[1]: # Anbar
            st.subheader("📦 Anbar")
            cats = run_query("SELECT DISTINCT category FROM ingredients")
            all_cats = ["Hamısı"] + (cats['category'].tolist() if not cats.empty else [])
            f_cat = st.selectbox("Kateqoriya Filtr", all_cats)
            c1, c2 = st.columns([1, 2])
            with c1:
                with st.form("stk"):
                    st.markdown("**Stok Artır**")
                    n=st.text_input("Ad"); q=st.number_input("Say"); u=st.selectbox("Vahid",["gr","ml","ədəd"]); c=st.selectbox("Kat",["Bar","Süd","Sirop","Qablaşdırma","Təsərrüfat"])
                    l=st.number_input("Limit", 10.0)
                    if st.form_submit_button("Yadda Saxla"):
                        run_action("INSERT INTO ingredients (name,stock_qty,unit,category,min_limit) VALUES (:n,:q,:u,:c,:l) ON CONFLICT (name) DO UPDATE SET stock_qty=ingredients.stock_qty+:q", {"n":n,"q":q,"u":u,"c":c,"l":l}); st.rerun()
                dlist = run_query("SELECT name FROM ingredients")
                if not dlist.empty:
                    d = st.selectbox("Silinəcək", dlist['name'])
                    if st.button("Sil"): run_action("DELETE FROM ingredients WHERE name=:n",{"n":d}); st.rerun()
            with c2:
                sql = "SELECT * FROM ingredients"; p = {}
                if f_cat != "Hamısı": sql += " WHERE category=:c"; p['c'] = f_cat
                sql += " ORDER BY category, name"
                df = run_query(sql, p)
                if not df.empty:
                    for _, r in df.iterrows():
                        stat = "low" if r['stock_qty'] <= r['min_limit'] else "ok"
                        icon = "⚠️ AZALIB" if stat == "low" else "✅"
                        st.markdown(f"<div class='stock-card {stat}'><div><div class='stock-title'>{r['name']}</div><div class='stock-meta'>{r['category']}</div></div><div style='text-align:right'><div class='stock-val'>{r['stock_qty']} {r['unit']}</div><div class='stock-meta'>{icon}</div></div></div>", unsafe_allow_html=True)

        with tabs[2]: # Resept
            st.subheader("📜 Reseptlər")
            c1, c2 = st.columns([1, 2])
            with c1:
                ms = run_query("SELECT item_name FROM menu WHERE is_active=TRUE")
                if not ms.empty:
                    sel = st.selectbox("Məhsul", sorted(ms['item_name'].unique()))
                    st.session_state.selected_recipe_product = sel
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
                st.markdown("#### 🎫 Kupon Yarat (Kütləvi)")
                k_type = st.selectbox("Növ", ["🎂 Ad Günü (24 Saat)", "🏷️ 20% Endirim", "🏷️ 30% Endirim", "🏷️ 50% Endirim"])
                if st.button("Bütün Müştərilərə Payla"):
                    custs = run_query("SELECT card_id FROM customers")
                    days = 1 if "Ad Günü" in k_type else 7
                    code = "disc_100_coffee" if "Ad Günü" in k_type else "disc_20" if "20%" in k_type else "disc_30" if "30%" in k_type else "disc_50"
                    for _, r in custs.iterrows():
                        run_action("INSERT INTO customer_coupons (card_id, coupon_type, expires_at) VALUES (:i, :c, NOW() + INTERVAL :d)", {"i":r['card_id'], "c":code, "d":f"{days} days"})
                    st.success("Paylandı!")
            with c_mail:
                st.markdown("#### 📧 Email Marketinq")
                msg = st.text_area("Mesaj")
                if st.button("Göndər"):
                    custs = run_query("SELECT email FROM customers WHERE email IS NOT NULL")
                    for _, r in custs.iterrows(): send_email(r['email'], "Emalatxana", msg)
                    st.success("Göndərildi!")
            st.divider()
            st.dataframe(run_query("SELECT * FROM customers"))

        with tabs[5]: # Menyu
            st.subheader("📋 Menyu")
            with st.expander("📥 Excel Import"):
                strat = st.radio("Strategiya", ["Yenilə", "Ötür", "Təmizlə və Yaz"])
                up = st.file_uploader("Fayl", type=['xlsx'])
                if up and st.button("Yüklə"):
                    try:
                        df = pd.read_excel(up)
                        if strat == "Təmizlə və Yaz": run_action("DELETE FROM menu")
                        c = 0
                        for _, row in df.iterrows():
                            nm=row['item_name']; pr=float(row['price']); ct=row['category']; ic=row.get('is_coffee', False)
                            ex = not run_query("SELECT id FROM menu WHERE item_name=:n", {"n":nm}).empty
                            if strat=="Ötür" and ex: continue
                            if strat=="Yenilə" and ex: run_action("UPDATE menu SET price=:p, category=:c WHERE item_name=:n", {"p":pr,"c":ct,"n":nm})
                            else: run_action("INSERT INTO menu (item_name,price,category,is_active,is_coffee) VALUES (:n,:p,:c,TRUE,:ic)", {"n":nm,"p":pr,"c":ct,"ic":ic})
                            c+=1
                        st.success(f"{c} əməliyyat!")
                    except Exception as e: st.error(str(e))
            with st.form("add_m"):
                n = st.text_input("Ad"); p = st.number_input("Qiymət"); c = st.text_input("Kateqoriya"); ic = st.checkbox("Kofedir?")
                if st.form_submit_button("Əlavə Et"):
                    run_action("INSERT INTO menu (item_name,price,category,is_active,is_coffee) VALUES (:n,:p,:c,TRUE,:ic)", {"n":n,"p":p,"c":c,"ic":ic}); st.rerun()
            st.dataframe(run_query("SELECT * FROM menu ORDER BY category, item_name"))

        with tabs[6]: # Ayarlar
            st.subheader("⚙️ Ayarlar")
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Yeni İşçi**")
                with st.form("new_u"):
                    u = st.text_input("Ad (Görünən)"); p = st.text_input("PIN (Şifrə)"); r = st.selectbox("Rol", ["staff", "admin"])
                    if st.form_submit_button("Yarat"):
                        try: run_action("INSERT INTO users (username,password,role) VALUES (:u,:p,:r)", {"u":u,"p":hash_password(p),"r":r}); st.success("OK")
                        except: st.error("Bu ad var")
            with c2:
                st.write("**İdarəetmə**")
                us = run_query("SELECT username FROM users")
                tu = st.selectbox("Seç", us['username'])
                op = st.radio("Seçim", ["Şifrə Dəyiş", "Sil"])
                if op == "Sil":
                    if st.button("SİL"):
                        if tu=='admin': st.error("Admin silinə bilməz")
                        else: run_action("DELETE FROM users WHERE username=:u",{"u":tu}); st.rerun()
                else:
                    np = st.text_input("Yeni PIN")
                    if st.button("Dəyiş"): run_action("UPDATE users SET password=:p WHERE username=:u", {"p":hash_password(np),"u":tu}); st.success("Oldu")

        with tabs[7]: # Admin Restore
            st.subheader("🔧 Admin & Restore")
            c_back, c_rest = st.columns(2)
            with c_back:
                if st.button("📥 FULL BACKUP (XLSX)", type="primary"):
                    try:
                        out = BytesIO()
                        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                            clean_df_for_excel(run_query("SELECT * FROM customers")).to_excel(writer, sheet_name='Customers')
                            clean_df_for_excel(run_query("SELECT * FROM sales")).to_excel(writer, sheet_name='Sales')
                            clean_df_for_excel(run_query("SELECT * FROM menu")).to_excel(writer, sheet_name='Menu')
                            clean_df_for_excel(run_query("SELECT * FROM users")).to_excel(writer, sheet_name='Users')
                            clean_df_for_excel(run_query("SELECT * FROM ingredients")).to_excel(writer, sheet_name='Inventory')
                            clean_df_for_excel(run_query("SELECT * FROM recipes")).to_excel(writer, sheet_name='Recipes')
                        st.download_button("⬇️ Backup.xlsx", out.getvalue(), "Backup.xlsx")
                    except Exception as e: st.error(e)
            with c_rest:
                st.markdown("**⚠️ BAZANI GERİ YÜKLƏ (RESTORE)**")
                with st.form("restore_db"):
                    r_file = st.file_uploader("Backup Faylı (.xlsx)")
                    a_pass = st.text_input("Admin Şifrəsi", type="password")
                    if st.form_submit_button("🚨 YÜKLƏ VƏ KÖHNƏNİ SİL"):
                        adm = run_query("SELECT password FROM users WHERE role='admin' LIMIT 1")
                        if not adm.empty and verify_password(a_pass, adm.iloc[0]['password']):
                            if r_file:
                                try:
                                    xls = pd.ExcelFile(r_file)
                                    run_action("TRUNCATE TABLE sales, menu, ingredients, recipes, customers, users CASCADE")
                                    if 'Users' in xls.sheet_names:
                                        for _, r in pd.read_excel(xls, 'Users').iterrows():
                                            run_action("INSERT INTO users (username, password, role) VALUES (:u, :p, :r)", {"u":r['username'], "p":r['password'], "r":r['role']})
                                    if 'Menu' in xls.sheet_names:
                                        for _, r in pd.read_excel(xls, 'Menu').iterrows():
                                            run_action("INSERT INTO menu (item_name, price, category, is_active, is_coffee) VALUES (:n, :p, :c, TRUE, :ic)", {"n":r['item_name'], "p":r['price'], "c":r['category'], "ic":r['is_coffee']})
                                    if 'Inventory' in xls.sheet_names:
                                        for _, r in pd.read_excel(xls, 'Inventory').iterrows():
                                            run_action("INSERT INTO ingredients (name, stock_qty, unit, category, min_limit) VALUES (:n, :q, :u, :c, :l)", {"n":r['name'], "q":r['stock_qty'], "u":r['unit'], "c":r['category'], "l":r['min_limit']})
                                    st.success("Baza bərpa olundu!")
                                except Exception as e: st.error(f"Xəta: {e}")
                        else: st.error("Şifrə yanlışdır")

        with tabs[8]: # QR
            st.subheader("🖨️ QR Generator (Green & Transparent)")
            cnt = st.number_input("Say", 1, 50)
            kind = st.selectbox("Növ", ["Standard", "Termos", "Special 10% Discount"])
            if st.button("Yarat"):
                zip_buffer = BytesIO(); has_mul = cnt > 1
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for _ in range(cnt):
                        i = str(random.randint(10000000, 99999999)); tok = secrets.token_hex(8)
                        ctype = "thermos" if kind=="Termos" else "standard"
                        run_action("INSERT INTO customers (card_id, stars, type, secret_token) VALUES (:i, 0, :t, :st)", {"i":i, "t":ctype, "st":tok})
                        if kind == "Termos": run_action("INSERT INTO customer_coupons (card_id, coupon_type) VALUES (:i, 'thermos_welcome')", {"i":i})
                        elif "10%" in kind: run_action("INSERT INTO customer_coupons (card_id, coupon_type) VALUES (:i, 'disc_10')", {"i":i})
                        img_data = generate_custom_qr(f"{APP_URL}/?id={i}&t={tok}", i)
                        zf.writestr(f"QR_{i}.png", img_data)
                        if not has_mul: st.image(BytesIO(img_data), width=200); single=img_data
                if has_mul: st.download_button("📥 ZIP Yüklə", zip_buffer.getvalue(), "qrcodes.zip")
                else: st.download_button("⬇️ PNG Yüklə", single, "qr.png")

    elif role == 'staff':
        staff_tabs = st.tabs(["POS", "Mənim Satışlarım"])
        with staff_tabs[0]: render_pos_interface()
        with staff_tabs[1]: render_analytics(is_admin=False)

    # FOOTER
    st.markdown(f"<div class='footer'>Ironwaves POS {VERSION} | © 2026</div>", unsafe_allow_html=True)
