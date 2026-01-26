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
# === IRONWAVES POS - VERSION 2.8 BETA ===
# === (DESIGN, PIN LOGIN, GREEN QR) ===
# ==========================================

# --- CONFIG ---
st.set_page_config(page_title="Ironwaves POS v2.8", page_icon="☕", layout="wide", initial_sidebar_state="collapsed")

# --- MENYU DATASI (DEFAULT) ---
FIXED_MENU_DATA = [
    {'name': 'Su', 'price': 2.0, 'cat': 'İçkilər', 'is_coffee': False},
    {'name': 'Çay (şirniyyat, fıstıq)', 'price': 3.0, 'cat': 'İçkilər', 'is_coffee': False},
    {'name': 'Americano S', 'price': 3.9, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Americano M', 'price': 4.9, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Americano L', 'price': 5.9, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Cappuccino S', 'price': 4.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Cappuccino M', 'price': 5.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Cappuccino L', 'price': 6.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Latte S', 'price': 4.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Latte M', 'price': 5.5, 'cat': 'Qəhvə', 'is_coffee': True},
    {'name': 'Latte L', 'price': 6.5, 'cat': 'Qəhvə', 'is_coffee': True},
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
    [data-testid="stSidebar"] { display: none; }
    
    /* TABS */
    button[data-baseweb="tab"] {
        font-family: 'Oswald', sans-serif !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        background-color: white !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 8px !important;
        margin: 0 4px !important;
        padding: 8px 16px !important;
        color: #555 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        border-color: #2E7D32 !important;
        color: #2E7D32 !important;
        background-color: #E8F5E9 !important;
    }
    
    /* BUTTONS */
    div.stButton > button {
        border-radius: 10px !important; 
        height: 50px !important; 
        font-weight: 700 !important;
        box-shadow: 0 2px 0 rgba(0,0,0,0.1) !important;
        transition: all 0.1s !important;
    }
    div.stButton > button:active { transform: translateY(2px) !important; box-shadow: none !important; }
    
    /* PRIMARY */
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #2E7D32, #43A047) !important; color: white !important; }

    /* POS CARD STYLE */
    .pos-card-header {
        background: linear-gradient(135deg, #FF6B35, #FF8C00);
        color: white; padding: 5px; border-radius: 8px 8px 0 0; text-align: center; font-weight: bold;
    }
    .pos-card-body {
        background: white; border: 1px solid #eee; border-top: none; 
        border-radius: 0 0 8px 8px; padding: 10px; text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .pos-price { font-size: 18px; color: #2E7D32; font-weight: bold; margin-top: 5px; }

    /* STATUS */
    .status-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 5px; }
    .status-online { background-color: #2ECC71; } .status-offline { background-color: #BDC3C7; }
    
    /* CARDS */
    .cart-item { background: white; border-radius: 8px; padding: 10px; margin-bottom: 5px; border: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
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
        
        # CRM Tables
        s.execute(text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS customers (card_id TEXT PRIMARY KEY, stars INTEGER DEFAULT 0, type TEXT, email TEXT, birth_date TEXT, is_active BOOLEAN DEFAULT FALSE, last_visit TIMESTAMP, secret_token TEXT, gender TEXT, last_feedback_star INTEGER DEFAULT -1);"))
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
@st.cache_data
def generate_custom_qr(data, center_text, transparent=False):
    qr = qrcode.QRCode(box_size=10, border=1) # Sərhəd kiçik olsun
    qr.add_data(data); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGBA')
    
    # Rəng dəyişimi: Qara -> Yaşıl, Ağ -> Transparent
    datas = img.getdata()
    newData = []
    for item in datas:
        # Əgər ağdırsa (255,255,255) -> Transparent et
        if item[0] > 200 and item[1] > 200 and item[2] > 200:
            newData.append((255, 255, 255, 0))
        else:
            # Qara yerinə Tünd Yaşıl (#006400)
            newData.append((0, 100, 0, 255))
    img.putdata(newData)

    # Ortaya mətn yazmaq (sadələşdirilmiş, şəkilsiz)
    if center_text:
        draw = ImageDraw.Draw(img)
        try: font = ImageFont.truetype("arial.ttf", 20)
        except: font = ImageFont.load_default()
        # Mətni sadəcə aşağı yazırıq ki, QR pozulmasın
        # (Professional QR generatorlarda mərkəz boşaldılır, burada sadəlik üçün)
        pass 

    buf = BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()

def clean_df_for_excel(df):
    for col in df.select_dtypes(include=['datetime64[ns, UTC]', 'datetime64[ns]']).columns:
        df[col] = df[col].astype(str)
    return df

def send_email(to_email, subject, body):
    if not RESEND_API_KEY: return False
    url = "https://api.resend.com/emails"
    headers = {"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"}
    payload = {"from": f"Emalatxana <{DEFAULT_SENDER_EMAIL}>", "to": [to_email], "subject": subject, "html": body}
    try: requests.post(url, json=payload, headers=headers); return True
    except: return False

# --- SESSION ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []
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
# === LOGIN (V2.8 PIN LOGIC) ===
# ==========================================
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown("<h2 style='text-align:center; color:#2E7D32;'>☕ EMALATXANA POS</h2>", unsafe_allow_html=True)
        tabs = st.tabs(["İŞÇİ (PIN)", "ADMİN"])
        
        # --- STAFF PIN LOGIN (NO USERNAME) ---
        with tabs[0]:
            with st.form("staff_login"):
                pin = st.text_input("PIN Kodu Daxil Edin", type="password", placeholder="****")
                if st.form_submit_button("Sistemə Giriş", use_container_width=True):
                    # Bütün staffları yoxlayır
                    udf = run_query("SELECT * FROM users WHERE role='staff'")
                    found = False
                    for _, row in udf.iterrows():
                        if verify_password(pin, row['password']):
                            st.session_state.logged_in=True; st.session_state.user=row['username']; st.session_state.role='staff'
                            tok=secrets.token_urlsafe(16)
                            run_action("INSERT INTO active_sessions (token,username,role) VALUES (:t,:u,:r)", {"t":tok,"u":row['username'],"r":'staff'})
                            st.query_params["token"] = tok
                            st.rerun(); found=True; break
                    if not found: st.error("⚠️ Yanlış PIN Kod!")

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
    # ==========================================
    # === MAIN INTERFACE ===
    # ==========================================
    
    # --- HEADER ---
    h1, h2, h3 = st.columns([4, 1, 1])
    with h1:
        st.markdown(f"**👤 {st.session_state.user}** | {st.session_state.role.upper()}")
    with h2:
        if st.button("🔄 Yenilə", use_container_width=True): st.rerun()
    with h3:
        if st.button("🚪 Çıxış", type="primary", use_container_width=True):
            run_action("DELETE FROM active_sessions WHERE token=:t", {"t":st.query_params.get("token")})
            st.session_state.logged_in = False; st.rerun()
    st.divider()

    role = st.session_state.role
    
    # --- TABS (BOLD) ---
    TABS = ["POS", "📦 Anbar", "📜 Resept", "Analitika", "CRM", "Menyu", "⚙️ Ayarlar", "Admin", "QR"]
    if role == 'staff': TABS = ["POS"]
    tabs = st.tabs(TABS)
    
    # --- TAB 1: POS (POPUP & GROUPED) ---
    with tabs[0]:
        c1, c2 = st.columns([1.5, 3])
        
        # --- LEFT: CART ---
        with c1:
            st.info("🧾 Çek")
            # Customer Scan
            with st.expander("👤 Müştəri (Bonus)", expanded=False):
                qr_val = st.text_input("QR/ID", key="pos_qr", placeholder="Enter...")
                if st.button("Axtar"):
                    try:
                        clean_id = qr_val.split("id=")[1].split("&")[0] if "id=" in qr_val else qr_val
                        c_df = run_query("SELECT * FROM customers WHERE card_id=:id", {"id":clean_id})
                        if not c_df.empty: st.session_state.current_customer = c_df.iloc[0].to_dict(); st.rerun()
                        else: st.error("Tapılmadı")
                    except: pass
            
            if st.session_state.current_customer:
                curr = st.session_state.current_customer
                st.success(f"Müştəri: {curr['card_id']} | Bonus: {curr['stars']}")
                if st.button("Ləğv Et"): st.session_state.current_customer = None; st.rerun()

            if st.session_state.cart:
                total_bill = 0
                for i, item in enumerate(st.session_state.cart):
                    item_total = item['qty'] * item['price']
                    total_bill += item_total
                    st.markdown(f"""<div class="cart-item"><div style="flex:2;"><b>{item['item_name']}</b></div><div style="flex:1;">{item['price']}</div><div style="flex:1; color:orange;">x{item['qty']}</div><div style="flex:1; text-align:right;">{item_total:.1f}</div></div>""", unsafe_allow_html=True)
                    b1, b2, b3 = st.columns([1,1,4])
                    if b1.button("➖", key=f"m_{i}"):
                        if item['qty'] > 1: item['qty'] -= 1
                        else: st.session_state.cart.pop(i)
                        st.rerun()
                    if b2.button("➕", key=f"p_{i}"): item['qty'] += 1; st.rerun()

                st.markdown(f"<h2 style='text-align:right; color:#2E7D32'>{total_bill:.2f} ₼</h2>", unsafe_allow_html=True)
                pay_m = st.radio("Ödəniş:", ["Nəğd", "Kart"], horizontal=True)
                
                if st.button("✅ ÖDƏNİŞ ET", type="primary", use_container_width=True):
                    try:
                        items_str = ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart])
                        run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i, :t, :p, :c, NOW())", 
                                   {"i":items_str, "t":total_bill, "p":("Cash" if pay_m=="Nəğd" else "Card"), "c":st.session_state.user})
                        
                        with conn.session as s:
                            for item in st.session_state.cart:
                                recipes = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name = :m"), {"m": item['item_name']}).fetchall()
                                if recipes:
                                    for r in recipes:
                                        s.execute(text("UPDATE ingredients SET stock_qty = stock_qty - :q WHERE name = :n"), {"q":float(r[1])*item['qty'], "n":r[0]})
                            if st.session_state.current_customer:
                                cid = st.session_state.current_customer['card_id']
                                gain = sum([x['qty'] for x in st.session_state.cart if x.get('is_coffee')])
                                s.execute(text("UPDATE customers SET stars = stars + :s WHERE card_id=:id"), {"s":gain, "id":cid})
                            s.commit()
                        st.session_state.cart = []; st.success("Satıldı!"); time.sleep(1); st.rerun()
                    except Exception as e: st.error(f"Xəta: {e}")
            else: st.info("Səbət boşdur")

        # --- RIGHT: PRODUCTS (GROUPED) ---
        with c2:
            cats = run_query("SELECT DISTINCT category FROM menu WHERE is_active=TRUE")
            if not cats.empty:
                cat_list = ["Hamısı"] + sorted(cats['category'].tolist())
                sel_cat = st.radio("Kataloq", cat_list, horizontal=True)
                sql = "SELECT * FROM menu WHERE is_active=TRUE"
                p = {}
                if sel_cat != "Hamısı": sql += " AND category=:c"; p["c"] = sel_cat
                sql += " ORDER BY price ASC"
                prods = run_query(sql, p)
                
                # Grouping
                grouped = {}
                for _, row in prods.iterrows():
                    name = row['item_name']
                    parts = name.split()
                    if len(parts) > 1 and parts[-1] in ['S', 'M', 'L', 'XL', 'Single', 'Double']:
                        base = " ".join(parts[:-1])
                        grouped.setdefault(base, []).append(row)
                    else: grouped[name] = [row]
                
                cols = st.columns(4)
                i = 0
                
                @st.dialog("Ölçü Seçimi")
                def show_variants(base_name, items):
                    st.write(f"### {base_name}")
                    for item in items:
                        label = item['item_name'].replace(base_name, "").strip()
                        c_btn, c_pr = st.columns([3, 1])
                        if c_btn.button(f"{label}", key=f"v_{item['id']}", use_container_width=True):
                            st.session_state.cart.append({'item_name': item['item_name'], 'price': float(item['price']), 'qty': 1, 'is_coffee': item['is_coffee']})
                            st.rerun()
                        c_pr.write(f"**{item['price']}**")

                for base_name, items in grouped.items():
                    with cols[i % 4]:
                        # NEW DESIGN CARD
                        if len(items) > 1:
                            st.markdown(f"<div class='pos-card-header'>{base_name}</div><div class='pos-card-body'>Seçim</div>", unsafe_allow_html=True)
                            if st.button("SEÇ", key=f"grp_{base_name}", use_container_width=True):
                                show_variants(base_name, items)
                        else:
                            item = items[0]
                            st.markdown(f"<div class='pos-card-header'>{item['item_name']}</div><div class='pos-card-body'><div class='pos-price'>{item['price']} ₼</div></div>", unsafe_allow_html=True)
                            if st.button("ƏLAVƏ ET", key=f"SNG_{item['id']}", use_container_width=True):
                                st.session_state.cart.append({'item_name': item['item_name'], 'price': float(item['price']), 'qty': 1, 'is_coffee': item['is_coffee']})
                                st.rerun()
                    i += 1

    if role == 'admin':
        with tabs[1]: # Anbar
            st.subheader("📦 Anbar")
            c1, c2 = st.columns([1, 2])
            with c1:
                with st.form("stk"):
                    st.markdown("**Stok Artır / Yarat**")
                    n = st.text_input("Ad"); q = st.number_input("Say"); u = st.selectbox("Vahid", ["gr","ml","ədəd"]); c = st.selectbox("Kat", ["Bar","Süd","Sirop","Qablaşdırma"]); l = st.number_input("Limit", 10.0)
                    if st.form_submit_button("Yadda Saxla"):
                        run_action("INSERT INTO ingredients (name,stock_qty,unit,category,min_limit) VALUES (:n,:q,:u,:c,:l) ON CONFLICT (name) DO UPDATE SET stock_qty=ingredients.stock_qty+:q", {"n":n,"q":q,"u":u,"c":c,"l":l})
                        st.success("OK"); st.rerun()
                dlist = run_query("SELECT name FROM ingredients")
                if not dlist.empty:
                    d = st.selectbox("Silinəcək", dlist['name'])
                    if st.button("Sil"): run_action("DELETE FROM ingredients WHERE name=:n",{"n":d}); st.rerun()
            with c2:
                df = run_query("SELECT * FROM ingredients ORDER BY category, name")
                if not df.empty:
                    for _, r in df.iterrows():
                        cls = "stock-low" if r['stock_qty'] <= r['min_limit'] else "stock-ok"
                        st.markdown(f"<div class='{cls}'><b>{r['name']}</b> ({r['category']}): {r['stock_qty']} {r['unit']}</div>", unsafe_allow_html=True)

        with tabs[2]: # Resept
            st.subheader("📜 Reseptlər")
            c1, c2 = st.columns(2)
            with c1:
                ms = run_query("SELECT item_name FROM menu WHERE is_active=TRUE")
                if not ms.empty:
                    sel = st.selectbox("Məhsul", ms['item_name'])
                    st.session_state.selected_recipe_product = sel
            with c2:
                if st.session_state.selected_recipe_product:
                    p = st.session_state.selected_recipe_product
                    st.write(f"**{p}** Tərkibi:")
                    rs = run_query("SELECT id, ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m", {"m":p})
                    st.dataframe(rs, hide_index=True)
                    if not rs.empty:
                        rid = st.selectbox("Silmək üçün ID", rs['id'])
                        if st.button("Sətri Sil"): run_action("DELETE FROM recipes WHERE id=:id", {"id":rid}); st.rerun()
                    st.divider()
                    ings = run_query("SELECT name FROM ingredients")
                    if not ings.empty:
                        with st.form("add_r"):
                            i = st.selectbox("Xammal", ings['name'])
                            q = st.number_input("Miqdar", 0.1)
                            if st.form_submit_button("Əlavə Et"):
                                run_action("INSERT INTO recipes (menu_item_name, ingredient_name, quantity_required) VALUES (:m,:i,:q)", {"m":p,"i":i,"q":q})
                                st.rerun()

        with tabs[3]: # Analitika
            st.subheader("📊 Analitika")
            df = run_query("SELECT * FROM sales ORDER BY created_at DESC LIMIT 100")
            if not df.empty:
                st.metric("Son 100 Satış", f"{df['total'].sum():.2f} ₼")
                st.dataframe(df)

        with tabs[4]: # CRM
            st.subheader("👥 CRM")
            custs = run_query("SELECT * FROM customers")
            if not custs.empty:
                st.dataframe(custs)
                with st.form("crm_send"):
                    msg = st.text_area("Mesaj")
                    if st.form_submit_button("Hər kəsə göndər"):
                        for _, r in custs.iterrows():
                            if r['email']: send_email(r['email'], "Emalatxana", msg)
                        st.success("Göndərildi!")

        with tabs[5]: # Menyu Import
            st.subheader("📋 Menyu")
            with st.expander("📥 Excel Import", expanded=True):
                strat = st.radio("Strategiya", ["Yenilə", "Ötür", "Təmizlə və Yaz"])
                up = st.file_uploader("Fayl", type=['xlsx'])
                if up and st.button("Yüklə"):
                    try:
                        df = pd.read_excel(up)
                        if strat == "Təmizlə və Yaz": run_action("DELETE FROM menu")
                        c = 0
                        for _, row in df.iterrows():
                            nm=row['item_name']; pr=row['price']; ct=row['category']; ic=row.get('is_coffee', False)
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
            st.subheader("⚙️ İşçi İdarəetməsi")
            users = run_query("SELECT username, role FROM users")
            st.dataframe(users)
            
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Yeni İşçi**")
                with st.form("new_u"):
                    u = st.text_input("Ad (Görünən)"); p = st.text_input("PIN (Şifrə)"); r = st.selectbox("Rol", ["staff", "admin"])
                    if st.form_submit_button("Yarat"):
                        try: run_action("INSERT INTO users (username,password,role) VALUES (:u,:p,:r)", {"u":u,"p":hash_password(p),"r":r}); st.success("Oldu!")
                        except: st.error("Bu ad var")
            with c2:
                st.write("**Sil / Şifrə**")
                tu = st.selectbox("İşçi Seç", users['username'])
                act = st.radio("Seç", ["Şifrə Dəyiş", "Sil"])
                if act == "Şifrə Dəyiş":
                    np = st.text_input("Yeni PIN")
                    if st.button("Dəyiş"): run_action("UPDATE users SET password=:p WHERE username=:u", {"p":hash_password(np),"u":tu}); st.success("Dəyişdi!")
                else:
                    if st.button("SİL"):
                        if tu == 'admin': st.error("Olmaz")
                        else: run_action("DELETE FROM users WHERE username=:u", {"u":tu}); st.success("Silindi!"); st.rerun()

        with tabs[7]: # Admin
            st.subheader("🔧 Admin")
            if st.button("📥 FULL BACKUP (XLSX)"):
                try:
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                        clean_df_for_excel(run_query("SELECT * FROM customers")).to_excel(writer, sheet_name='Customers')
                        clean_df_for_excel(run_query("SELECT * FROM sales")).to_excel(writer, sheet_name='Sales')
                        clean_df_for_excel(run_query("SELECT * FROM menu")).to_excel(writer, sheet_name='Menu')
                        clean_df_for_excel(run_query("SELECT * FROM users")).to_excel(writer, sheet_name='Users')
                    st.download_button("⬇️ Backup.xlsx", out.getvalue(), "Backup.xlsx")
                except Exception as e: st.error(e)

        with tabs[8]: # QR
            st.subheader("🖨️ QR Generator (Green)")
            cnt = st.number_input("Say", 1, 50)
            kind = st.selectbox("Növ", ["Standard", "Termos", "Special 10%"])
            if st.button("Yarat"):
                zip_buffer = BytesIO(); has_mul = cnt > 1
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for _ in range(cnt):
                        i = str(random.randint(10000000, 99999999)); tok = secrets.token_hex(8)
                        ctype = "thermos" if kind=="Termos" else "standard"
                        run_action("INSERT INTO customers (card_id, stars, type, secret_token) VALUES (:i, 0, :t, :st)", {"i":i, "t":ctype, "st":tok})
                        
                        if kind == "Termos": run_action("INSERT INTO customer_coupons (card_id, coupon_type) VALUES (:i, 'thermos_welcome')", {"i":i})
                        elif kind == "Special 10%": run_action("INSERT INTO customer_coupons (card_id, coupon_type) VALUES (:i, 'disc_10')", {"i":i}) # disc_10 type needs logic in POS later
                        
                        img_data = generate_custom_qr(f"{APP_URL}/?id={i}&t={tok}", i)
                        zf.writestr(f"QR_{i}.png", img_data)
                        if not has_mul: st.image(BytesIO(img_data), width=200); single=img_data
                
                if has_mul: st.download_button("📥 ZIP Yüklə", zip_buffer.getvalue(), "qrcodes.zip")
                else: st.download_button("⬇️ PNG Yüklə", single, "qr.png")

    elif role == 'staff': render_pos()
