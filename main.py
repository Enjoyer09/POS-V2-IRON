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
# === IRONWAVES POS - VERSION 2.1 BETA (SMART INVENTORY) ===
# ==========================================

# --- CONFIG ---
st.set_page_config(page_title="Ironwaves POS v2.1", page_icon="☕", layout="wide", initial_sidebar_state="expanded")

# --- CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700;900&display=swap');
    .stApp { font-family: 'Oswald', sans-serif !important; background-color: #FAFAFA; }
    div.stButton > button { border-radius: 12px !important; height: 60px !important; font-weight: bold !important; }
    
    /* ANBAR KARTLARI */
    .stock-card {
        background: white; border: 1px solid #ddd; border-radius: 8px; padding: 10px; margin-bottom: 5px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .stock-low { border-left: 5px solid red; background: #fff5f5; }
    .stock-ok { border-left: 5px solid green; }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
try:
    db_url = os.environ.get("STREAMLIT_CONNECTIONS_NEON_URL") or os.environ.get("DATABASE_URL")
    if not db_url: st.error("Database URL not found!"); st.stop()
    if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    conn = st.connection("neon", type="sql", url=db_url, pool_pre_ping=True)
except Exception as e: st.error(f"DB Error: {e}"); st.stop()

# --- SCHEMA MIGRATION ---
def ensure_schema():
    with conn.session as s:
        # Standard Tables
        s.execute(text("CREATE TABLE IF NOT EXISTS menu (id SERIAL PRIMARY KEY, item_name TEXT, price DECIMAL(10,2), category TEXT, is_active BOOLEAN DEFAULT FALSE);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, items TEXT, total DECIMAL(10,2), payment_method TEXT, cashier TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, last_seen TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS active_sessions (token TEXT PRIMARY KEY, username TEXT, role TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        
        # INVENTORY TABLES (Updated)
        s.execute(text("CREATE TABLE IF NOT EXISTS ingredients (id SERIAL PRIMARY KEY, name TEXT UNIQUE, stock_qty DECIMAL(10,2) DEFAULT 0, unit TEXT, category TEXT, min_limit DECIMAL(10,2) DEFAULT 10);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS recipes (id SERIAL PRIMARY KEY, menu_item_name TEXT, ingredient_name TEXT, quantity_required DECIMAL(10,2));"))

        # MIGRATION: Add 'category' and 'min_limit' if they don't exist
        try: s.execute(text("ALTER TABLE ingredients ADD COLUMN category TEXT;"))
        except: pass
        try: s.execute(text("ALTER TABLE ingredients ADD COLUMN min_limit DECIMAL(10,2) DEFAULT 10;"))
        except: pass
        
        # Default Admin
        chk = s.execute(text("SELECT * FROM users WHERE username='admin'")).fetchone()
        if not chk:
            p_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
            s.execute(text("INSERT INTO users (username, password, role) VALUES ('admin', :p, 'admin')"), {"p": p_hash})
        s.commit()
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
# === LOGIN PAGE ===
# ==========================================
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.title("🔐 Giriş")
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
    # === MAIN SYSTEM ===
    # ==========================================
    st.markdown(f"### 👤 {st.session_state.user} | {st.session_state.role.upper()}")
    
    if st.session_state.role == 'admin':
        tabs = st.tabs(["🛒 POS", "📦 Anbar (Stok)", "📜 Reseptlər", "📋 Menyu", "⚙️ Ayarlar"])
        
        # --- 1. POS ---
        with tabs[0]:
            c1, c2 = st.columns([1.5, 3])
            with c1:
                st.info("🧾 Çek")
                if st.session_state.cart:
                    for i, item in enumerate(st.session_state.cart):
                        cc1, cc2, cc3 = st.columns([3, 1, 1])
                        cc1.write(f"**{item['item_name']}**")
                        cc2.write(f"{item['price']}")
                        if cc3.button("x", key=f"d{i}"): st.session_state.cart.pop(i); st.rerun()
                    
                    total = sum(x['price'] for x in st.session_state.cart)
                    st.markdown(f"### CƏM: {total:.2f} ₼")
                    
                    if st.button("✅ SATIŞ", type="primary", use_container_width=True):
                        # Transaction
                        try:
                            items_str = ", ".join([x['item_name'] for x in st.session_state.cart])
                            run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i, :t, 'Cash', :c, NOW())", 
                                       {"i":items_str, "t":total, "c":st.session_state.user})
                            
                            # STOKDAN SİLMƏ (COMPLEX DEDUCTION)
                            log = []
                            with conn.session as s:
                                for item in st.session_state.cart:
                                    # Resepti tap
                                    recipes = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name = :m"), {"m": item['item_name']}).fetchall()
                                    if recipes:
                                        for r in recipes:
                                            ing_name = r[0]
                                            qty_needed = r[1]
                                            s.execute(text("UPDATE ingredients SET stock_qty = stock_qty - :q WHERE name = :n"), {"q":qty_needed, "n":ing_name})
                                            log.append(f"{ing_name}: -{qty_needed}")
                                s.commit()
                            
                            if log: st.toast(f"Anbardan silindi: {', '.join(set(log))}")
                            st.session_state.cart = []
                            st.success("Satıldı!")
                            time.sleep(1); st.rerun()
                        except Exception as e: st.error(f"Xəta: {e}")
                else: st.warning("Səbət boşdur")

            with c2:
                # KATEQORIYA FILTERI
                cats = run_query("SELECT DISTINCT category FROM menu")
                if not cats.empty:
                    cat_list = ["Hamısı"] + cats['category'].tolist()
                    sel_cat = st.radio("Kataloq", cat_list, horizontal=True)
                    
                    sql = "SELECT * FROM menu WHERE is_active=TRUE"
                    params = {}
                    if sel_cat != "Hamısı":
                        sql += " AND category=:c"
                        params["c"] = sel_cat
                    
                    prods = run_query(sql, params)
                    cols = st.columns(4)
                    for idx, row in prods.iterrows():
                        with cols[idx % 4]:
                            if st.button(f"{row['item_name']}\n{row['price']}₼", key=f"p{row['id']}", use_container_width=True):
                                st.session_state.cart.append(row.to_dict())
                                st.rerun()

        # --- 2. ANBAR (YENİLƏNMİŞ) ---
        with tabs[1]:
            st.subheader("📦 Anbar İdarəetməsi")
            
            # XAMMAL KATEQORIYALARI
            ING_CATS = [
                "Bar Xammalı (Kofe, Kakao)", 
                "Süd Məhsulları", 
                "Siroplar", 
                "Qablaşdırma (Stəkan, Qapaq)", 
                "Hazır Məhsul (Redbull, Su)",
                "Təmizlik & Digər"
            ]

            with st.expander("➕ Yeni Xammal / Məhsul Əlavə Et", expanded=False):
                with st.form("add_ing"):
                    c1, c2 = st.columns(2)
                    name = c1.text_input("Məhsul Adı (məs: Stəkan L, Kofe Dənəsi)")
                    cat = c2.selectbox("Kateqoriya", ING_CATS)
                    
                    c3, c4, c5 = st.columns(3)
                    qty = c3.number_input("Miqdar", min_value=0.0)
                    unit = c4.selectbox("Vahid", ["ədəd", "gr", "ml", "kq", "litr"])
                    limit = c5.number_input("Kritik Limit (Xəbərdarlıq üçün)", value=10.0)
                    
                    if st.form_submit_button("Anbara Vur"):
                        try:
                            run_action("""
                                INSERT INTO ingredients (name, stock_qty, unit, category, min_limit) 
                                VALUES (:n, :q, :u, :c, :l) 
                                ON CONFLICT (name) DO UPDATE SET stock_qty = ingredients.stock_qty + :q
                                """, {"n":name, "q":qty, "u":unit, "c":cat, "l":limit})
                            st.success(f"{name} artırıldı!")
                            st.rerun()
                        except Exception as e: st.error(str(e))

            # ANBAR SİYAHISI (Vizual)
            st.divider()
            filter_cat = st.selectbox("Filtlə", ["Hamısı"] + ING_CATS)
            
            sql = "SELECT * FROM ingredients"
            p = {}
            if filter_cat != "Hamısı":
                sql += " WHERE category = :c"
                p['c'] = filter_cat
            sql += " ORDER BY name"
            
            stock_data = run_query(sql, p)
            
            if not stock_data.empty:
                for _, row in stock_data.iterrows():
                    # Status rəngi
                    status_class = "stock-low" if row['stock_qty'] <= row['min_limit'] else "stock-ok"
                    status_icon = "⚠️ BİTİR!" if row['stock_qty'] <= row['min_limit'] else "✅"
                    
                    st.markdown(f"""
                    <div class="stock-card {status_class}">
                        <div>
                            <div style="font-weight:bold; font-size:18px;">{row['name']}</div>
                            <div style="color:#666; font-size:12px;">{row['category']}</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:20px; font-weight:bold;">{row['stock_qty']} <span style="font-size:14px;">{row['unit']}</span></div>
                            <div style="font-size:12px;">Min: {row['min_limit']} | {status_icon}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Anbar boşdur.")

        # --- 3. RESEPTLƏR (MÜRƏKKƏB MƏNTİQ) ---
        with tabs[2]:
            st.subheader("📜 Resept Qurucusu")
            st.info("Burada bir məhsul satılanda anbardan nələrin silinəcəyini təyin edirik.")
            
            c1, c2 = st.columns([1, 2])
            
            with c1:
                st.markdown("#### Resept Yarat")
                menus = run_query("SELECT item_name FROM menu WHERE is_active=TRUE")
                ings = run_query("SELECT name, unit FROM ingredients")
                
                if not menus.empty and not ings.empty:
                    sel_menu = st.selectbox("Menyu Məhsulu", menus['item_name'].unique())
                    sel_ing = st.selectbox("Xammal (Tərkib)", ings['name'].unique())
                    
                    # Vahidi tapmaq üçün
                    curr_unit = ings[ings['name']==sel_ing].iloc[0]['unit']
                    req_qty = st.number_input(f"Lazım olan miqdar ({curr_unit})", min_value=0.1, step=0.1)
                    
                    if st.button("Əlaqələndir 🔗"):
                        run_action("INSERT INTO recipes (menu_item_name, ingredient_name, quantity_required) VALUES (:m, :i, :q)",
                                   {"m":sel_menu, "i":sel_ing, "q":req_qty})
                        st.success("Reseptə əlavə edildi!")
                        st.rerun()
                else:
                    st.warning("Əvvəlcə menyu və anbarı doldurun.")

            with c2:
                st.markdown(f"#### {sel_menu if 'sel_menu' in locals() else ''} üçün Resept:")
                if 'sel_menu' in locals():
                    r_data = run_query("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m", {"m":sel_menu})
                    if not r_data.empty:
                        st.table(r_data)
                        if st.button("Bütün Resepti Sil"):
                            run_action("DELETE FROM recipes WHERE menu_item_name=:m", {"m":sel_menu})
                            st.rerun()
                    else:
                        st.info("Hələ heç nə əlavə edilməyib.")

        # --- 4. MENYU ---
        with tabs[3]:
            st.subheader("Menyu")
            with st.form("add_menu"):
                c1, c2, c3 = st.columns(3)
                n = c1.text_input("Ad (məs: Amerikano L)")
                p = c2.number_input("Qiymət", min_value=0.0)
                c = c3.selectbox("Kateqoriya", ["Qəhvə", "İçkilər", "Desert", "Yemək"])
                if st.form_submit_button("Yarat"):
                    run_action("INSERT INTO menu (item_name, price, category, is_active) VALUES (:n, :p, :c, TRUE)", {"n":n,"p":p,"c":c})
                    st.rerun()
            
            # Siyahı
            m = run_query("SELECT * FROM menu ORDER BY category, item_name")
            st.dataframe(m, use_container_width=True)

        # --- 5. AYARLAR ---
        with tabs[4]:
            if st.button("Çıxış"):
                run_action("DELETE FROM active_sessions WHERE token=:t", {"t":st.query_params.get("token")})
                st.session_state.logged_in = False
                st.rerun()
