import streamlit as st
import pandas as pd
import random
import qrcode
from io import BytesIO
import zipfile
from PIL import Image, ImageDraw, ImageFont
import time
from sqlalchemy import text
import os
import bcrypt
import requests
import datetime
import secrets
import threading

# ==========================================
# === IRONWAVES POS - VERSION 2.0 BETA (INVENTORY TRACKING) ===
# ==========================================

# --- INFRASTRUKTUR ---
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
DOMAIN = "emalatxana.ironwaves.store" 
APP_URL = f"https://{DOMAIN}"
DEFAULT_SENDER_EMAIL = "info@ironwaves.store" 

# --- SƏHİFƏ AYARLARI ---
st.set_page_config(page_title="Ironwaves POS v2 Beta", page_icon="☕", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# === STİL VƏ CSS ===
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700;900&display=swap');
    .stApp { font-family: 'Oswald', sans-serif !important; background-color: #FAFAFA; }
    
    /* POS DÜYMƏLƏRİ */
    div.stButton > button {
        border-radius: 12px !important;
        font-weight: bold !important;
        height: 60px !important;
        transition: all 0.2s;
    }
    div.stButton > button:hover { transform: scale(1.02); }

    /* KPI KARTLARI */
    .kpi-card {
        background: white; border-radius: 10px; padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #2E7D32;
        text-align: center;
    }
    .kpi-val { font-size: 24px; font-weight: bold; color: #333; }
    .kpi-lbl { font-size: 14px; color: #666; }
    
    /* STATUS İŞIQLARI */
    .status-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 5px; }
    .status-online { background-color: #4CAF50; box-shadow: 0 0 5px #4CAF50; }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
try:
    db_url = os.environ.get("STREAMLIT_CONNECTIONS_NEON_URL")
    if not db_url: st.error("DB URL not found!"); st.stop()
    if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    conn = st.connection("neon", type="sql", url=db_url, pool_pre_ping=True)
except Exception as e: st.error(f"DB Error: {e}"); st.stop()

# --- SCHEMA (V2 YENİLƏNMƏSİ) ---
def ensure_schema():
    with conn.session as s:
        # KÖHNƏ CƏDVƏLLƏR
        s.execute(text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS customers (card_id TEXT PRIMARY KEY, stars INTEGER DEFAULT 0, type TEXT, email TEXT, birth_date TEXT, is_active BOOLEAN DEFAULT FALSE, last_visit TIMESTAMP, secret_token TEXT, gender TEXT);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS menu (id SERIAL PRIMARY KEY, item_name TEXT, price DECIMAL(10,2), category TEXT, is_coffee BOOLEAN DEFAULT FALSE, is_active BOOLEAN DEFAULT TRUE);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, items TEXT, total DECIMAL(10,2), payment_method TEXT, cashier TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS customer_coupons (id SERIAL PRIMARY KEY, card_id TEXT, coupon_type TEXT, is_used BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, card_id TEXT, message TEXT, is_read BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS feedback (id SERIAL PRIMARY KEY, card_id TEXT, rating INTEGER, message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, last_seen TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS active_sessions (token TEXT PRIMARY KEY, username TEXT, role TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        
        # --- V2 YENİ CƏDVƏLLƏR (ANBAR & RESEPT) ---
        # 1. Ingredients (Xammal): Kofe dənəsi, Süd, Şəkər və s.
        s.execute(text("CREATE TABLE IF NOT EXISTS ingredients (id SERIAL PRIMARY KEY, name TEXT UNIQUE, stock_qty DECIMAL(10,2) DEFAULT 0, unit TEXT);"))
        
        # 2. Recipes (Reseptlər): Hansı məhsula nə qədər xammal gedir
        s.execute(text("CREATE TABLE IF NOT EXISTS recipes (id SERIAL PRIMARY KEY, menu_item_name TEXT, ingredient_name TEXT, quantity_required DECIMAL(10,2));"))
        
        s.commit()
ensure_schema()

# --- HELPERS ---
def get_config(key, default=""):
    try:
        df = conn.query("SELECT value FROM settings WHERE key = :k", params={"k": key})
        return df.iloc[0]['value'] if not df.empty else default
    except: return default

def run_query(q, p=None): return conn.query(q, params=p, ttl=0)

def run_action(q, p=None): 
    with conn.session as s: s.execute(text(q), p); s.commit()
    return True

def hash_password(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def verify_password(p, h): 
    try: return bcrypt.checkpw(p.encode(), h.encode()) if h.startswith('$2b$') else p == h
    except: return False

SHOP_NAME = get_config("shop_name", "Emalatxana Coffee")
LOGO_BASE64 = get_config("shop_logo_base64", "")

# --- SESSION CHECK ---
def check_session_token():
    token = st.query_params.get("token")
    if token:
        try:
            res = run_query("SELECT username, role FROM active_sessions WHERE token=:t", {"t":token})
            if not res.empty:
                st.session_state.logged_in = True
                st.session_state.user = res.iloc[0]['username']
                st.session_state.role = res.iloc[0]['role']
                run_action("UPDATE users SET last_seen = NOW() WHERE username = :u", {"u": st.session_state.user})
        except: pass
check_session_token()

if 'cart' not in st.session_state: st.session_state.cart = []

# ==========================================
# === ADMIN PANEL & POS ===
# ==========================================

if not st.session_state.get('logged_in'):
    # --- LOGIN SCREEN ---
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.title("🔐 Giriş")
        with st.form("login"):
            u = st.text_input("İstifadəçi"); p = st.text_input("Şifrə", type="password")
            if st.form_submit_button("Daxil Ol", use_container_width=True):
                udf = run_query("SELECT * FROM users WHERE LOWER(username)=LOWER(:u)", {"u":u})
                if not udf.empty and verify_password(p, udf.iloc[0]['password']):
                    st.session_state.logged_in = True
                    st.session_state.role = udf.iloc[0]['role']
                    st.session_state.user = u
                    tok = secrets.token_urlsafe(16)
                    run_action("INSERT INTO active_sessions (token, username, role) VALUES (:t, :u, :r)", {"t":tok, "u":u, "r":st.session_state.role})
                    st.query_params["token"] = tok
                    st.rerun()
                else: st.error("Səhv məlumat!")

else:
    # --- MAIN APP ---
    role = st.session_state.role
    
    # HEADER
    c1, c2 = st.columns([5,1])
    with c1: st.markdown(f"### 👋 Xoş gəldin, {st.session_state.user} ({role.upper()})")
    with c2: 
        if st.button("Çıxış"): 
            run_action("DELETE FROM active_sessions WHERE token=:t", {"t":st.query_params.get("token")})
            st.session_state.logged_in = False; st.query_params.clear(); st.rerun()
    st.divider()

    if role == 'admin':
        tabs = st.tabs(["🛒 POS", "📦 Stok & Resept", "📊 Hesabat", "📋 Menyu", "👥 İstifadəçilər"])
        
        # --- TAB 1: POS ---
        with tabs[0]:
            c_pos1, c_pos2 = st.columns([1.5, 3])
            
            with c_pos1:
                st.success("🧾 Səbət")
                if st.session_state.cart:
                    for i, item in enumerate(st.session_state.cart):
                        cc1, cc2, cc3 = st.columns([3,1,1])
                        cc1.write(f"**{item['item_name']}**")
                        cc2.write(f"{item['price']}")
                        if cc3.button("x", key=f"del_{i}"): st.session_state.cart.pop(i); st.rerun()
                    
                    total = sum(d['price'] for d in st.session_state.cart)
                    st.markdown(f"<h3 style='text-align:right'>CƏM: {total:.2f} ₼</h3>", unsafe_allow_html=True)
                    
                    if st.button("✅ SATIŞI TAMAMLA", type="primary", use_container_width=True):
                        # 1. Satışı Qeyd Et
                        items_str = ", ".join([x['item_name'] for x in st.session_state.cart])
                        run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i, :t, 'Cash', :c, NOW())", 
                                   {"i":items_str, "t":total, "c":st.session_state.user})
                        
                        # 2. V2 BETA: STOKDAN SİLMƏ (DEDUCTION)
                        try:
                            deducted_log = []
                            with conn.session as s:
                                for item in st.session_state.cart:
                                    # Resepti tap
                                    recipes = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name = :m"), {"m": item['item_name']}).fetchall()
                                    if recipes:
                                        for r in recipes:
                                            ing_name = r[0]
                                            qty_needed = r[1]
                                            # Stokdan çıx
                                            s.execute(text("UPDATE ingredients SET stock_qty = stock_qty - :q WHERE name = :n"), {"q":qty_needed, "n":ing_name})
                                            deducted_log.append(f"{ing_name}: -{qty_needed}")
                                s.commit()
                            if deducted_log:
                                st.toast(f"Stokdan silindi: {', '.join(deducted_log)}")
                        except Exception as e:
                            st.error(f"Stok xətası: {e}")

                        st.session_state.cart = []
                        st.success("Satış uğurlu!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.info("Səbət boşdur")

            with c_pos2:
                st.info("🛍️ Məhsullar")
                cats = run_query("SELECT DISTINCT category FROM menu WHERE is_active=TRUE")
                if not cats.empty:
                    sel_cat = st.radio("Kateqoriya", cats['category'].tolist(), horizontal=True)
                    products = run_query("SELECT * FROM menu WHERE category=:c AND is_active=TRUE", {"c":sel_cat})
                    
                    cols = st.columns(4)
                    for idx, row in products.iterrows():
                        with cols[idx % 4]:
                            if st.button(f"{row['item_name']}\n{row['price']}₼", key=f"p_{row['id']}", use_container_width=True):
                                st.session_state.cart.append(row.to_dict())
                                st.rerun()

        # --- TAB 2: STOK & RESEPT (V2 NEW) ---
        with tabs[1]:
            st.markdown("### 🧪 Anbar və Resept İdarəetməsi (V2 Beta)")
            t_stk1, t_stk2 = st.tabs(["📦 Xammal Anbarı", "📜 Resept Qurucusu"])
            
            with t_stk1:
                st.caption("Burada kofe dənələri, süd, sirop və s. əlavə edin.")
                
                # Yeni Xammal Əlavə Et
                with st.form("add_ing"):
                    c1, c2, c3 = st.columns(3)
                    i_name = c1.text_input("Xammal Adı (Məs: Kofe Dənəsi)")
                    i_qty = c2.number_input("Stok Miqdarı", min_value=0.0, step=0.1)
                    i_unit = c3.selectbox("Vahid", ["gr", "ml", "ədəd", "kq", "litr"])
                    if st.form_submit_button("Stoka Əlavə Et"):
                        try:
                            run_action("INSERT INTO ingredients (name, stock_qty, unit) VALUES (:n, :q, :u) ON CONFLICT (name) DO UPDATE SET stock_qty = ingredients.stock_qty + :q", 
                                       {"n":i_name, "q":i_qty, "u":i_unit})
                            st.success(f"{i_name} əlavə edildi!")
                            st.rerun()
                        except Exception as e: st.error(str(e))
                
                # Anbar Cədvəli
                st.divider()
                st.subheader("Hazırkı Anbar Vəziyyəti")
                ing_df = run_query("SELECT * FROM ingredients ORDER BY name")
                if not ing_df.empty:
                    # Kritik stok yoxlanışı
                    ing_df['Status'] = ing_df['stock_qty'].apply(lambda x: "⚠️ AZALIB" if x < 50 else "✅ OK")
                    st.dataframe(ing_df, use_container_width=True)
                else:
                    st.info("Anbar boşdur.")

            with t_stk2:
                st.caption("Məhsul satılanda anbardan nə silinsin?")
                
                # Məhsul Seç
                menu_items = run_query("SELECT item_name FROM menu WHERE is_active=TRUE")
                all_ingredients = run_query("SELECT name, unit FROM ingredients")
                
                if not menu_items.empty and not all_ingredients.empty:
                    c1, c2, c3 = st.columns(3)
                    sel_menu = c1.selectbox("Məhsul Seç", menu_items['item_name'].tolist())
                    sel_ing = c2.selectbox("Xammal Seç", all_ingredients['name'].tolist())
                    sel_qty = c3.number_input("Sərfiyyat Miqdarı", min_value=0.1, step=0.1)
                    
                    if st.button("Reseptə Bağla 🔗"):
                        run_action("INSERT INTO recipes (menu_item_name, ingredient_name, quantity_required) VALUES (:m, :i, :q)",
                                   {"m":sel_menu, "i":sel_ing, "q":sel_qty})
                        st.success(f"{sel_menu} satılanda {sel_qty} {sel_ing} silinəcək.")
                        st.rerun()
                    
                    st.divider()
                    st.subheader(f"{sel_menu} üçün Resept:")
                    curr_recipe = run_query("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m", {"m":sel_menu})
                    if not curr_recipe.empty:
                        st.table(curr_recipe)
                        if st.button("Resepti Sıfırla"):
                            run_action("DELETE FROM recipes WHERE menu_item_name=:m", {"m":sel_menu})
                            st.rerun()
                    else:
                        st.info("Bu məhsul üçün resept yoxdur.")
                else:
                    st.warning("Əvvəlcə Menyu və Anbar (Xammal) dolmalıdır.")

        # --- TAB 3: HESABAT ---
        with tabs[2]:
            st.subheader("📊 Satış Statistikası")
            sales = run_query("SELECT * FROM sales ORDER BY created_at DESC")
            if not sales.empty:
                total_rev = sales['total'].sum()
                total_tx = len(sales)
                
                k1, k2, k3 = st.columns(3)
                k1.markdown(f"<div class='kpi-card'><div class='kpi-val'>{total_rev:.2f} ₼</div><div class='kpi-lbl'>Ümumi Gəlir</div></div>", unsafe_allow_html=True)
                k2.markdown(f"<div class='kpi-card'><div class='kpi-val'>{total_tx}</div><div class='kpi-lbl'>Satış Sayı</div></div>", unsafe_allow_html=True)
                
                st.divider()
                st.dataframe(sales, use_container_width=True)
            else:
                st.info("Hələ satış yoxdur")

        # --- TAB 4: MENYU ---
        with tabs[3]:
            st.subheader("📋 Menyu Redaktə")
            with st.form("new_prod"):
                c1, c2, c3 = st.columns(3)
                n = c1.text_input("Ad")
                p = c2.number_input("Qiymət", min_value=0.0)
                c = c3.text_input("Kateqoriya (Qəhvə, Desert...)")
                if st.form_submit_button("Əlavə Et"):
                    run_action("INSERT INTO menu (item_name, price, category) VALUES (:n, :p, :c)", {"n":n,"p":p,"c":c})
                    st.rerun()
            
            md = run_query("SELECT * FROM menu")
            st.dataframe(md, use_container_width=True)

        # --- TAB 5: USERS ---
        with tabs[4]:
            st.subheader("👥 İstifadəçilər")
            users = run_query("SELECT username, role, last_seen FROM users")
            st.dataframe(users)

    elif role == 'staff':
        st.warning("Staff rejimi yalnız POS-u görür (Məhdud Giriş)")
        # Staff yalnız POS hissəsini görəcək (kod təkrarı olmaması üçün sadə saxladım)
