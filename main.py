import streamlit as st
import pandas as pd
import random
import time
from sqlalchemy import text
import os
import bcrypt
import secrets
import datetime

# ==========================================
# === IRONWAVES POS - VERSION 2.4 BETA (AUTO RECIPES) ===
# ==========================================

# --- CONFIG ---
st.set_page_config(page_title="Ironwaves POS v2.4", page_icon="☕", layout="wide", initial_sidebar_state="expanded")

# --- HAZIR MENYU DATASI ---
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

# --- HAZIR XAMMAL DATASI (STANDARD) ---
INITIAL_INGREDIENTS = [
    # Bar
    {"name": "Kofe Dənəsi", "cat": "Bar (Qəhvə/Çay/Kakao)", "unit": "gr", "qty": 5000, "min": 1000},
    {"name": "Kakao/Şokolad Tozu", "cat": "Bar (Qəhvə/Çay/Kakao)", "unit": "gr", "qty": 2000, "min": 500},
    {"name": "Çay (Quru)", "cat": "Bar (Qəhvə/Çay/Kakao)", "unit": "gr", "qty": 1000, "min": 200},
    # Süd
    {"name": "Süd (Adi)", "cat": "Süd Məhsulları & Qaymaq", "unit": "ml", "qty": 20000, "min": 5000},
    {"name": "Qaymaq (10-20%)", "cat": "Süd Məhsulları & Qaymaq", "unit": "ml", "qty": 5000, "min": 1000},
    # Siroplar
    {"name": "Sirop (Karamel)", "cat": "Siroplar & Souslar", "unit": "ml", "qty": 1000, "min": 200},
    {"name": "Sirop (Vanil)", "cat": "Siroplar & Souslar", "unit": "ml", "qty": 1000, "min": 200},
    # Qablaşdırma
    {"name": "Stəkan S (Kağız)", "cat": "Qablaşdırma (Stəkan/Qapaq/Salfet)", "unit": "ədəd", "qty": 500, "min": 50},
    {"name": "Stəkan M (Kağız)", "cat": "Qablaşdırma (Stəkan/Qapaq/Salfet)", "unit": "ədəd", "qty": 500, "min": 50},
    {"name": "Stəkan L (Kağız)", "cat": "Qablaşdırma (Stəkan/Qapaq/Salfet)", "unit": "ədəd", "qty": 500, "min": 50},
    {"name": "Stəkan XS (Espresso)", "cat": "Qablaşdırma (Stəkan/Qapaq/Salfet)", "unit": "ədəd", "qty": 200, "min": 20},
    {"name": "Stəkan Plastik (Buzlu)", "cat": "Qablaşdırma (Stəkan/Qapaq/Salfet)", "unit": "ədəd", "qty": 300, "min": 50},
    {"name": "Qapaq (Universal)", "cat": "Qablaşdırma (Stəkan/Qapaq/Salfet)", "unit": "ədəd", "qty": 1500, "min": 100},
]

# --- HAZIR RESEPT DATASI (SCA STANDARD) ---
# Format: "Menu Item": {"Ing1": qty, "Ing2": qty...}
INITIAL_RECIPES = {
    # Espresso & Ristretto
    "Espresso S": {"Kofe Dənəsi": 10, "Stəkan XS (Espresso)": 1},
    "Espresso M": {"Kofe Dənəsi": 20, "Stəkan XS (Espresso)": 1}, # Double
    "Ristretto S": {"Kofe Dənəsi": 10, "Stəkan XS (Espresso)": 1},
    
    # Americano
    "Americano S": {"Kofe Dənəsi": 10, "Stəkan S (Kağız)": 1, "Qapaq (Universal)": 1},
    "Americano M": {"Kofe Dənəsi": 20, "Stəkan M (Kağız)": 1, "Qapaq (Universal)": 1},
    "Americano L": {"Kofe Dənəsi": 20, "Stəkan L (Kağız)": 1, "Qapaq (Universal)": 1},
    
    # Cappuccino (Süd: S-160ml, M-220ml, L-300ml)
    "Cappuccino S": {"Kofe Dənəsi": 10, "Süd (Adi)": 160, "Stəkan S (Kağız)": 1, "Qapaq (Universal)": 1},
    "Cappuccino M": {"Kofe Dənəsi": 20, "Süd (Adi)": 220, "Stəkan M (Kağız)": 1, "Qapaq (Universal)": 1},
    "Cappuccino L": {"Kofe Dənəsi": 20, "Süd (Adi)": 300, "Stəkan L (Kağız)": 1, "Qapaq (Universal)": 1},
    
    # Latte (Süd: S-200ml, M-280ml, L-380ml)
    "Latte S": {"Kofe Dənəsi": 10, "Süd (Adi)": 200, "Stəkan S (Kağız)": 1, "Qapaq (Universal)": 1},
    "Latte M": {"Kofe Dənəsi": 20, "Süd (Adi)": 280, "Stəkan M (Kağız)": 1, "Qapaq (Universal)": 1},
    "Latte L": {"Kofe Dənəsi": 20, "Süd (Adi)": 380, "Stəkan L (Kağız)": 1, "Qapaq (Universal)": 1},
    
    # Raf (Qaymaq: S-200ml, M-280ml, L-380ml + Sirop)
    "Raf S": {"Kofe Dənəsi": 10, "Qaymaq (10-20%)": 200, "Sirop (Vanil)": 15, "Stəkan S (Kağız)": 1, "Qapaq (Universal)": 1},
    "Raf M": {"Kofe Dənəsi": 20, "Qaymaq (10-20%)": 280, "Sirop (Vanil)": 25, "Stəkan M (Kağız)": 1, "Qapaq (Universal)": 1},
    "Raf L": {"Kofe Dənəsi": 20, "Qaymaq (10-20%)": 380, "Sirop (Vanil)": 35, "Stəkan L (Kağız)": 1, "Qapaq (Universal)": 1},
    
    # Mocha (Süd + Şokolad)
    "Mocha S": {"Kofe Dənəsi": 10, "Süd (Adi)": 180, "Kakao/Şokolad Tozu": 20, "Stəkan S (Kağız)": 1, "Qapaq (Universal)": 1},
    "Mocha M": {"Kofe Dənəsi": 20, "Süd (Adi)": 260, "Kakao/Şokolad Tozu": 30, "Stəkan M (Kağız)": 1, "Qapaq (Universal)": 1},
    
    # Iced Drinks (Plastik Stəkan)
    "Ice Americano M": {"Kofe Dənəsi": 20, "Stəkan Plastik (Buzlu)": 1},
    "Iced Latte M": {"Kofe Dənəsi": 20, "Süd (Adi)": 180, "Stəkan Plastik (Buzlu)": 1},
}

# --- CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700;900&display=swap');
    .stApp { font-family: 'Oswald', sans-serif !important; background-color: #FAFAFA; }
    div.stButton > button { border-radius: 12px !important; height: 50px !important; font-weight: bold !important; }
    .cart-item { background: white; border-radius: 8px; padding: 10px; margin-bottom: 5px; border: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
    .stock-ok { border-left: 5px solid green; padding: 10px; background: white; margin-bottom: 5px; border-radius: 5px; }
    .stock-low { border-left: 5px solid red; padding: 10px; background: #fff0f0; margin-bottom: 5px; border-radius: 5px; }
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
    with conn.session as s: s.execute(text(q), p); s.commit()
    return True
def hash_password(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def verify_password(p, h): 
    try: return bcrypt.checkpw(p.encode(), h.encode()) if h.startswith('$2b$') else p == h
    except: return False

# --- SESSION ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []
if 'selected_recipe_product' not in st.session_state: st.session_state.selected_recipe_product = None

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

# ==========================================
# === LOGIN ===
# ==========================================
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.title("🔐 POS Giriş")
        with st.form("login"):
            u = st.text_input("User"); p = st.text_input("Pass", type="password")
            if st.form_submit_button("Giriş", use_container_width=True):
                udf = run_query("SELECT * FROM users WHERE LOWER(username)=LOWER(:u)", {"u":u})
                if not udf.empty and verify_password(p, udf.iloc[0]['password']):
                    st.session_state.logged_in = True
                    st.session_state.user = u
                    st.session_state.role = udf.iloc[0]['role']
                    tok = secrets.token_urlsafe(16)
                    run_action("INSERT INTO active_sessions (token, username, role) VALUES (:t, :u, :r)", {"t":tok, "u":u, "r":st.session_state.role})
                    st.query_params["token"] = tok
                    st.rerun()
                else: st.error("Səhv!")
else:
    # ==========================================
    # === MAIN APP ===
    # ==========================================
    st.markdown(f"### 👤 {st.session_state.user} | {st.session_state.role.upper()}")
    
    if st.session_state.role == 'admin':
        tabs = st.tabs(["🛒 Smart POS", "📦 Anbar (Stok)", "📜 Reseptlər", "📋 Menyu", "⚙️ Ayarlar"])
        
        # --- TAB 1: SMART POS ---
        with tabs[0]:
            c1, c2 = st.columns([1.5, 3])
            
            with c1:
                st.info("🧾 Çek (Smart Səbət)")
                if st.session_state.cart:
                    total_bill = 0
                    for i, item in enumerate(st.session_state.cart):
                        item_total = item['qty'] * item['price']
                        total_bill += item_total
                        
                        c_nm, c_btn1, c_qty, c_btn2, c_pr, c_del = st.columns([3, 1, 1, 1, 1.5, 1])
                        c_nm.write(f"**{item['item_name']}**")
                        if c_btn1.button("➖", key=f"min_{i}"):
                            if item['qty'] > 1: item['qty'] -= 1
                            else: st.session_state.cart.pop(i)
                            st.rerun()
                        c_qty.write(f"{item['qty']}")
                        if c_btn2.button("➕", key=f"pls_{i}"): item['qty'] += 1; st.rerun()
                        c_pr.write(f"{item_total:.1f}")
                        if c_del.button("🗑️", key=f"del_{i}"): st.session_state.cart.pop(i); st.rerun()
                        st.markdown("---")

                    st.markdown(f"<h3 style='text-align:right; color:#2E7D32'>YEKUN: {total_bill:.2f} ₼</h3>", unsafe_allow_html=True)
                    
                    if st.button("✅ SATIŞI TƏSDİQLƏ", type="primary", use_container_width=True):
                        try:
                            items_str = ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart])
                            run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i, :t, 'Cash', :c, NOW())", 
                                       {"i":items_str, "t":total_bill, "c":st.session_state.user})
                            
                            # STOKDAN SİLMƏ
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
                                s.commit()
                            
                            if log: st.toast(f"Stokdan silindi: {len(log)} komponent")
                            st.session_state.cart = []
                            st.success("Satıldı!")
                            time.sleep(1); st.rerun()
                        except Exception as e: st.error(f"Xəta: {e}")
                else: st.warning("Səbət boşdur")

            with c2:
                cats = run_query("SELECT DISTINCT category FROM menu WHERE is_active=TRUE")
                if not cats.empty:
                    cat_list = ["Hamısı"] + sorted(cats['category'].tolist())
                    sel_cat = st.radio("Kataloq", cat_list, horizontal=True)
                    sql = "SELECT * FROM menu WHERE is_active=TRUE"
                    params = {}
                    if sel_cat != "Hamısı":
                        sql += " AND category=:c"
                        params["c"] = sel_cat
                    sql += " ORDER BY price ASC"
                    prods = run_query(sql, params)
                    cols = st.columns(4)
                    for idx, row in prods.iterrows():
                        with cols[idx % 4]:
                            if st.button(f"{row['item_name']}\n{row['price']}₼", key=f"p{row['id']}", use_container_width=True):
                                existing = next((x for x in st.session_state.cart if x['item_name'] == row['item_name']), None)
                                if existing: existing['qty'] += 1
                                else: st.session_state.cart.append({'item_name': row['item_name'], 'price': float(row['price']), 'qty': 1})
                                st.rerun()

        # --- TAB 2: ANBAR ---
        with tabs[1]:
            st.subheader("📦 Anbarın İdarə Edilməsi")
            c_add, c_list = st.columns([1, 2])
            with c_add:
                st.markdown("#### ➕ / ➖ İdarəetmə")
                mode = st.radio("Əməliyyat:", ["Əlavə Et / Artır", "Sil (Delete)"])
                if mode == "Əlavə Et / Artır":
                    with st.form("add_ing_form"):
                        name = st.text_input("Xammal Adı (Unikal)")
                        cat = st.selectbox("Kateqoriya", ["Bar (Qəhvə/Çay/Kakao)", "Süd Məhsulları & Qaymaq", "Siroplar & Souslar", "Qablaşdırma (Stəkan/Qapaq/Salfet)", "Hazır Məhsul", "Təsərrüfat"])
                        qty = st.number_input("Miqdar", min_value=0.0)
                        unit = st.selectbox("Vahid", ["gr", "ml", "ədəd", "kq", "litr"])
                        limit = st.number_input("Kritik Limit", value=10.0)
                        if st.form_submit_button("Yadda Saxla"):
                            try:
                                run_action("""INSERT INTO ingredients (name, stock_qty, unit, category, min_limit) VALUES (:n, :q, :u, :c, :l) 
                                    ON CONFLICT (name) DO UPDATE SET stock_qty = ingredients.stock_qty + :q, category = :c""", 
                                    {"n":name, "q":qty, "u":unit, "c":cat, "l":limit})
                                st.success("Yeniləndi!"); st.rerun()
                            except Exception as e: st.error(str(e))
                else:
                    del_ing_list = run_query("SELECT name FROM ingredients")
                    if not del_ing_list.empty:
                        with st.form("del_ing_form"):
                            to_del = st.selectbox("Silinəcək Xammal", del_ing_list['name'].tolist())
                            if st.form_submit_button("Bazadan Sil"):
                                run_action("DELETE FROM ingredients WHERE name=:n", {"n":to_del})
                                st.warning("Silindi!"); st.rerun()

            with c_list:
                st.markdown("#### 📊 Anbar Vəziyyəti")
                ing_df = run_query("SELECT * FROM ingredients ORDER BY category, name")
                if not ing_df.empty:
                    for _, row in ing_df.iterrows():
                        color_cls = "stock-low" if row['stock_qty'] <= row['min_limit'] else "stock-ok"
                        msg = "⚠️ BİTİR!" if row['stock_qty'] <= row['min_limit'] else "✅"
                        st.markdown(f"<div class='{color_cls}'><div style='display:flex; justify-content:space-between;'><span><b>{row['name']}</b> <i style='color:#666'>({row['category']})</i></span><span>{row['stock_qty']} {row['unit']}</span></div><div style='font-size:12px; color:gray;'>Min: {row['min_limit']} | {msg}</div></div>", unsafe_allow_html=True)
                else: st.info("Anbar boşdur.")

        # --- TAB 3: RESEPT ---
        with tabs[2]:
            st.subheader("📜 Məhsul Reseptləri")
            c_sel, c_build = st.columns([1, 2])
            with c_sel:
                menu_items = run_query("SELECT item_name FROM menu WHERE is_active=TRUE")
                if not menu_items.empty:
                    sel_prod = st.selectbox("1. Məhsul Seç:", sorted(menu_items['item_name'].unique()))
                    st.session_state.selected_recipe_product = sel_prod
                else: st.warning("Menyu boşdur.")

            with c_build:
                prod_name = st.session_state.selected_recipe_product
                if prod_name:
                    st.markdown(f"#### 🛠️ {prod_name} tərkibi:")
                    curr_recipe = run_query("SELECT id, ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m", {"m":prod_name})
                    if not curr_recipe.empty:
                        st.table(curr_recipe)
                        del_rec_id = st.selectbox("Silmək üçün ID:", curr_recipe['id'].tolist(), key="del_rec_sel")
                        if st.button("Sətri Sil"):
                            run_action("DELETE FROM recipes WHERE id=:id", {"id":del_rec_id})
                            st.rerun()
                    else: st.info("Resept yoxdur.")
                    st.divider()
                    all_ings = run_query("SELECT name, unit FROM ingredients ORDER BY name")
                    if not all_ings.empty:
                        with st.form("add_rec_item"):
                            c_i1, c_i2 = st.columns(2)
                            sel_ing_row = c_i1.selectbox("Xammal", all_ings['name'].unique())
                            u = all_ings[all_ings['name']==sel_ing_row].iloc[0]['unit']
                            qty_req = c_i2.number_input(f"Miqdar ({u})", min_value=0.1, step=0.1)
                            if st.form_submit_button("Əlavə Et"):
                                run_action("INSERT INTO recipes (menu_item_name, ingredient_name, quantity_required) VALUES (:m, :i, :q)",
                                           {"m":prod_name, "i":sel_ing_row, "q":qty_req})
                                st.success("Əlavə edildi!"); st.rerun()

        # --- TAB 4: MENYU ---
        with tabs[3]:
            st.subheader("📋 Menyu")
            m = run_query("SELECT * FROM menu ORDER BY category, item_name")
            st.dataframe(m, use_container_width=True)

        # --- TAB 5: AYARLAR (AUTO SETUP) ---
        with tabs[4]:
            st.subheader("⚙️ Sistemi Sıfırla & Hazırla")
            
            with st.expander("🛠️ Standart Anbar və Reseptləri Yüklə (Reset)", expanded=True):
                st.warning("DİQQƏT: Bu əməliyyat Menyu, Anbar və Reseptləri silib, standart (SCA) versiyaları yazacaq!")
                if st.button("🚀 BÜTÜN SİSTEMİ QUR (AUTO-SETUP)"):
                    try:
                        # 1. Clear Tables
                        run_action("DELETE FROM recipes")
                        run_action("DELETE FROM ingredients")
                        run_action("DELETE FROM menu")
                        
                        # 2. Insert Menu
                        mc = 0
                        for item in FIXED_MENU_DATA:
                            run_action("INSERT INTO menu (item_name, price, category, is_active, is_coffee) VALUES (:n, :p, :c, TRUE, :ic)", 
                                       {"n":item['name'], "p":item['price'], "c":item['cat'], "ic":item['is_coffee']})
                            mc += 1
                            
                        # 3. Insert Ingredients
                        ic = 0
                        for ing in INITIAL_INGREDIENTS:
                            run_action("INSERT INTO ingredients (name, stock_qty, unit, category, min_limit) VALUES (:n, :q, :u, :c, :l)",
                                       {"n":ing['name'], "q":ing['qty'], "u":ing['unit'], "c":ing['cat'], "l":ing['min']})
                            ic += 1
                            
                        # 4. Insert Recipes
                        rc = 0
                        for menu_item, rec_data in INITIAL_RECIPES.items():
                            for ing_name, qty in rec_data.items():
                                run_action("INSERT INTO recipes (menu_item_name, ingredient_name, quantity_required) VALUES (:m, :i, :q)",
                                           {"m":menu_item, "i":ing_name, "q":qty})
                                rc += 1
                                
                        st.success(f"✅ Sistem Hazırdır! ({mc} məhsul, {ic} xammal, {rc} resept sətri yükləndi)")
                        time.sleep(2); st.rerun()
                    except Exception as e: st.error(f"Xəta: {e}")

            if st.button("Çıxış"):
                run_action("DELETE FROM active_sessions WHERE token=:t", {"t":st.query_params.get("token")})
                st.session_state.logged_in = False
                st.rerun()

    elif role == 'staff': st.warning("Staff Rejimi")
