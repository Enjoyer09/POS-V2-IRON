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
# === IRONWAVES POS - VERSION 2.7 BETA ===
# === (SMART POS GROUPING & FULL MANAGEMENT) ===
# ==========================================

# --- CONFIG ---
st.set_page_config(page_title="Ironwaves POS v2.7", page_icon="☕", layout="wide", initial_sidebar_state="collapsed")

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
    # Digər məhsullar Excel-dən gələcək...
]

# --- INFRA ---
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
DOMAIN = "emalatxana.ironwaves.store" 
APP_URL = f"https://{DOMAIN}"
DEFAULT_SENDER_EMAIL = "info@ironwaves.store" 

# --- CSS ---
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
        border-color: #FF6B35 !important;
        color: #FF6B35 !important;
        background-color: #FFF3E0 !important;
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
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #FF6B35, #FF8C00) !important; color: white !important; }

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
        with st.form("login"):
            u = st.text_input("User"); p = st.text_input("Pass", type="password")
            if st.form_submit_button("Giriş", use_container_width=True):
                udf = run_query("SELECT * FROM users WHERE LOWER(username)=LOWER(:u)", {"u":u})
                if not udf.empty and verify_password(p, udf.iloc[0]['password']):
                    st.session_state.logged_in = True; st.session_state.user = u; st.session_state.role = udf.iloc[0]['role']
                    tok = secrets.token_urlsafe(16)
                    run_action("INSERT INTO active_sessions (token, username, role) VALUES (:t, :u, :r)", {"t":tok, "u":u, "r":st.session_state.role})
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
    
    # --- TABS ---
    TABS = ["POS", "📦 Anbar", "📜 Resept", "Analitika", "CRM", "Menyu", "⚙️ Ayarlar", "Admin", "QR"]
    if role == 'staff': TABS = ["POS"]
    tabs = st.tabs(TABS)
    
    # --- TAB 1: POS (GROUPED) ---
    with tabs[0]:
        c1, c2 = st.columns([1.5, 3])
        
        # --- LEFT: CART ---
        with c1:
            st.info("🧾 Çek")
            
            # Customer
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

            # Cart Items
            if st.session_state.cart:
                total_bill = 0
                for i, item in enumerate(st.session_state.cart):
                    item_total = item['qty'] * item['price']
                    total_bill += item_total
                    st.markdown(f"""
                    <div class="cart-item">
                        <div style="flex:2;"><b>{item['item_name']}</b></div>
                        <div style="flex:1;">{item['price']}</div>
                        <div style="flex:1; color:orange;">x{item['qty']}</div>
                        <div style="flex:1; text-align:right;">{item_total:.1f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    b1, b2, b3 = st.columns([1,1,4])
                    if b1.button("➖", key=f"m_{i}"):
                        if item['qty'] > 1: item['qty'] -= 1
                        else: st.session_state.cart.pop(i)
                        st.rerun()
                    if b2.button("➕", key=f"p_{i}"): item['qty'] += 1; st.rerun()

                st.markdown(f"<h2 style='text-align:right; color:#D35400'>{total_bill:.2f} ₼</h2>", unsafe_allow_html=True)
                
                pay_m = st.radio("Ödəniş:", ["Nəğd", "Kart"], horizontal=True)
                
                if st.button("✅ ÖDƏNİŞ ET", type="primary", use_container_width=True):
                    try:
                        items_str = ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart])
                        run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i, :t, :p, :c, NOW())", 
                                   {"i":items_str, "t":total_bill, "p":("Cash" if pay_m=="Nəğd" else "Card"), "c":st.session_state.user})
                        
                        # Inventory & Loyalty Logic
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
                        
                        st.session_state.cart = []
                        st.success("Satıldı!"); time.sleep(1); st.rerun()
                    except Exception as e: st.error(f"Xəta: {e}")
            else: st.info("Səbət boşdur")

        # --- RIGHT: PRODUCTS (GROUPED UI) ---
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
                
                # --- GROUPING LOGIC ---
                grouped = {}
                for _, row in prods.iterrows():
                    name = row['item_name']
                    parts = name.split()
                    # Əgər son söz S, M, L, XL, Double, Single kimidirsə qruplaşdır
                    if len(parts) > 1 and parts[-1] in ['S', 'M', 'L', 'XL', 'Single', 'Double']:
                        base = " ".join(parts[:-1])
                        grouped.setdefault(base, []).append(row)
                    else:
                        grouped[name] = [row] # Single item list
                
                # --- RENDER GRID ---
                cols = st.columns(4)
                i = 0
                
                @st.dialog("Variant Seçimi")
                def show_variants(base_name, items):
                    st.write(f"### {base_name}")
                    for item in items:
                        label = item['item_name'].replace(base_name, "").strip()
                        c_btn, c_pr = st.columns([3, 1])
                        if c_btn.button(f"{label} ({item['price']} ₼)", key=f"v_{item['id']}", use_container_width=True):
                            st.session_state.cart.append({'item_name': item['item_name'], 'price': float(item['price']), 'qty': 1, 'is_coffee': item['is_coffee']})
                            st.rerun()

                for base_name, items in grouped.items():
                    with cols[i % 4]:
                        with st.container(border=True):
                            # Əgər qrupdursa (məs: Americano S, M, L) -> Dialog aç
                            if len(items) > 1:
                                st.markdown(f"<div style='text-align:center; font-weight:bold;'>{base_name}</div>", unsafe_allow_html=True)
                                st.caption(f"{len(items)} ölçü")
                                if st.button("SEÇ", key=f"grp_{base_name}", use_container_width=True):
                                    show_variants(base_name, items)
                            else:
                                # Tək məhsul
                                item = items[0]
                                st.markdown(f"<div style='text-align:center; font-weight:bold;'>{item['item_name']}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div style='text-align:center; color:orange;'>{item['price']} ₼</div>", unsafe_allow_html=True)
                                if st.button("ƏLAVƏ ET", key=f"SNG_{item['id']}", use_container_width=True):
                                    st.session_state.cart.append({'item_name': item['item_name'], 'price': float(item['price']), 'qty': 1, 'is_coffee': item['is_coffee']})
                                    st.rerun()
                    i += 1

    # --- TAB 2: ANBAR ---
    if role == 'admin':
        with tabs[1]:
            st.subheader("📦 Anbar")
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown("#### Əməliyyat")
                op = st.selectbox("Seç:", ["Artır/Yarat", "Sil"])
                if op == "Artır/Yarat":
                    with st.form("stk"):
                        n = st.text_input("Ad"); q = st.number_input("Say"); u = st.selectbox("Vahid", ["gr","ml","ədəd"])
                        c = st.selectbox("Kat", ["Bar","Süd","Sirop","Qablaşdırma","Digər"])
                        l = st.number_input("Limit", 10.0)
                        if st.form_submit_button("Yadda Saxla"):
                            run_action("INSERT INTO ingredients (name,stock_qty,unit,category,min_limit) VALUES (:n,:q,:u,:c,:l) ON CONFLICT (name) DO UPDATE SET stock_qty=ingredients.stock_qty+:q", {"n":n,"q":q,"u":u,"c":c,"l":l})
                            st.success("OK"); st.rerun()
                else:
                    dlist = run_query("SELECT name FROM ingredients")
                    if not dlist.empty:
                        d = st.selectbox("Silinəcək", dlist['name'])
                        if st.button("Sil"): run_action("DELETE FROM ingredients WHERE name=:n",{"n":d}); st.rerun()
            with c2:
                df = run_query("SELECT * FROM ingredients ORDER BY category, name")
                if not df.empty:
                    st.dataframe(df, use_container_width=True)

        # --- TAB 3: RESEPT ---
        with tabs[2]:
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

        # --- TAB 4: ANALITIKA ---
        with tabs[3]:
            st.subheader("📊 Analitika")
            df = run_query("SELECT * FROM sales ORDER BY created_at DESC LIMIT 100")
            if not df.empty:
                st.metric("Son 100 Satış Cəmi", f"{df['total'].sum():.2f} ₼")
                st.dataframe(df)
            else: st.info("Satış yoxdur")

        # --- TAB 5: CRM (NEW & FULL) ---
        with tabs[4]:
            st.subheader("👥 CRM & Müştərilər")
            
            # Customer List & Action
            custs = run_query("SELECT * FROM customers")
            if not custs.empty:
                st.dataframe(custs)
                
                st.divider()
                st.markdown("#### 📢 Kampaniya Göndər")
                
                c_msg, c_btn = st.columns([3, 1])
                msg = c_msg.text_area("Mesaj Mətni (Email & Bildiriş)", "Hörmətli müştəri, sizə özəl kampaniyamız var!")
                if c_btn.button("Bütün Müştərilərə Göndər"):
                    cnt = 0
                    for _, row in custs.iterrows():
                        if row['email']:
                            send_email(row['email'], "Emalatxana Xəbərləri", msg)
                            run_action("INSERT INTO notifications (card_id, message) VALUES (:id, :m)", {"id":row['card_id'], "m":msg})
                            cnt += 1
                    st.success(f"{cnt} müştəriyə göndərildi!")
            else:
                st.info("Hələ müştəri yoxdur.")

        # --- TAB 6: MENYU (SMART IMPORT) ---
        with tabs[5]:
            st.subheader("📋 Menyu İdarəetməsi")
            
            with st.expander("📥 Excel Import (Ağıllı)", expanded=True):
                strategy = st.radio("Dublikat Strategiyası:", 
                                    ["Yenilə (Qiyməti dəyiş)", "Ötür (Yalnız yeniləri)", "Tam Təmizlə və Yaz"])
                
                up = st.file_uploader("Excel Faylı", type=['xlsx'])
                if up and st.button("Yüklə"):
                    try:
                        df = pd.read_excel(up)
                        if 'item_name' not in df.columns: st.error("item_name sütunu yoxdur!"); st.stop()
                        
                        if strategy == "Tam Təmizlə və Yaz":
                            run_action("DELETE FROM menu")
                        
                        cnt = 0
                        for _, row in df.iterrows():
                            nm = str(row['item_name']); pr = float(row['price']); cat = str(row['category'])
                            is_cof = row.get('is_coffee', False)
                            
                            exists = not run_query("SELECT id FROM menu WHERE item_name=:n", {"n":nm}).empty
                            
                            if strategy == "Ötür (Yalnız yeniləri)" and exists: continue
                            
                            if strategy == "Yenilə (Qiyməti dəyiş)" and exists:
                                run_action("UPDATE menu SET price=:p, category=:c WHERE item_name=:n", {"p":pr, "c":cat, "n":nm})
                            else:
                                run_action("INSERT INTO menu (item_name, price, category, is_active, is_coffee) VALUES (:n,:p,:c,TRUE,:ic)", 
                                           {"n":nm, "p":pr, "c":cat, "ic":is_cof})
                            cnt += 1
                        st.success(f"{cnt} əməliyyat yerinə yetirildi!")
                        time.sleep(1); st.rerun()
                    except Exception as e: st.error(f"Xəta: {e}")

            # Manual Add
            with st.form("manual_menu"):
                c1, c2 = st.columns(2)
                n = c1.text_input("Ad"); p = c2.number_input("Qiymət")
                cat = c1.text_input("Kateqoriya"); ic = c2.checkbox("Kofedir?")
                if st.form_submit_button("Əlavə Et"):
                    run_action("INSERT INTO menu (item_name, price, category, is_active, is_coffee) VALUES (:n,:p,:c,TRUE,:ic)", {"n":n,"p":p,"c":cat,"ic":ic})
                    st.rerun()

        # --- TAB 7: AYARLAR (FULL USER MGMT) ---
        with tabs[6]:
            st.subheader("⚙️ Ayarlar")
            
            st.markdown("#### 👥 İşçi İdarəetməsi")
            users = run_query("SELECT username, role FROM users")
            st.dataframe(users, use_container_width=True)
            
            c_new, c_edit = st.columns(2)
            
            with c_new:
                st.write("**Yeni İşçi**")
                with st.form("new_u"):
                    u = st.text_input("Login"); p = st.text_input("Pass"); r = st.selectbox("Role", ["staff", "admin"])
                    if st.form_submit_button("Yarat"):
                        try:
                            run_action("INSERT INTO users (username, password, role) VALUES (:u,:p,:r)", {"u":u,"p":hash_password(p),"r":r})
                            st.success("Yaradıldı!"); st.rerun()
                        except: st.error("Bu ad var!")
            
            with c_edit:
                st.write("**Düzəliş / Silmə**")
                target_u = st.selectbox("İşçi Seç", users['username'].tolist())
                action = st.radio("Əməliyyat", ["Şifrə Dəyiş", "Sil"])
                
                if action == "Şifrə Dəyiş":
                    np = st.text_input("Yeni Şifrə", type="password")
                    if st.button("Dəyiş"):
                        run_action("UPDATE users SET password=:p WHERE username=:u", {"p":hash_password(np), "u":target_u})
                        st.success("Dəyişdirildi!")
                else:
                    if st.button("❌ İSTİFADƏÇİNİ SİL", type="primary"):
                        if target_u == 'admin': st.error("Admin silinə bilməz!")
                        else:
                            run_action("DELETE FROM users WHERE username=:u", {"u":target_u})
                            st.success("Silindi!"); st.rerun()

        # --- TAB 8: ADMIN (BACKUP) ---
        with tabs[7]:
            st.subheader("🔧 Admin Tools")
            if st.button("📥 Bütün Bazanı Yüklə (Backup)"):
                try:
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                        clean_df_for_excel(run_query("SELECT * FROM customers")).to_excel(writer, sheet_name='Customers')
                        clean_df_for_excel(run_query("SELECT * FROM sales")).to_excel(writer, sheet_name='Sales')
                        clean_df_for_excel(run_query("SELECT * FROM menu")).to_excel(writer, sheet_name='Menu')
                    st.download_button("⬇️ Backup.xlsx", out.getvalue(), "Backup.xlsx")
                except Exception as e: st.error(e)

        # --- TAB 9: QR (GENERATOR) ---
        with tabs[8]:
            st.subheader("🖨️ QR Generator")
            st.info("Müştərilər və ya Termoslar üçün QR kodlar yaradın.")
            
            cnt = st.number_input("Neçə ədəd?", 1, 50)
            is_th = st.checkbox("Termos QR-ı olsun? (Xüsusi endirim)")
            
            if st.button("QR Kodları Yarat"):
                ids = [str(random.randint(10000000, 99999999)) for _ in range(cnt)]
                zip_buffer = BytesIO(); has_multiple = cnt > 1
                
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for i in ids:
                        # Create customer placeholder
                        token = secrets.token_hex(8)
                        ctype = "thermos" if is_th else "standard"
                        run_action("INSERT INTO customers (card_id, stars, type, secret_token) VALUES (:i, 0, :t, :st)", {"i":i, "t":ctype, "st":token})
                        
                        if is_th:
                            run_action("INSERT INTO customer_coupons (card_id, coupon_type) VALUES (:i, 'thermos_welcome')", {"i":i})
                        
                        # Generate Image
                        url = f"{APP_URL}/?id={i}&t={token}"
                        img_data = generate_custom_qr(url, i)
                        zf.writestr(f"QR_{i}.png", img_data)
                        
                        if not has_multiple:
                            st.image(BytesIO(img_data), caption=f"ID: {i}", width=200)
                            single_data = img_data
                
                if has_multiple:
                    st.download_button("📥 ZIP Yüklə", zip_buffer.getvalue(), "qrcodes.zip", "application/zip")
                else:
                    st.download_button("⬇️ Şəkli Yüklə", single_data, f"{ids[0]}.png", "image/png")

    elif role == 'staff': render_pos()
