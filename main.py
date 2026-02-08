import streamlit as st
import pandas as pd
import datetime
import bcrypt
from sqlalchemy import text
import os
import time

# ==========================================
# === EMERGERNT POS v7.0 - ALL-IN-ONE ===
# ==========================================

st.set_page_config(page_title="Emalatkhana POS", layout="wide", page_icon="☕")

# --- DATABASE CONNECTION ---
@st.cache_resource
def get_connection():
    try:
        db_url = os.environ.get("DATABASE_URL")
        if db_url and db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        return st.connection("neon", type="sql", url=db_url, pool_pre_ping=True, connect_args={"sslmode": "require"})
    except:
        return None

conn = get_connection()

def run_action(q, p=None):
    with conn.session as s:
        s.execute(text(q), p if p else {})
        s.commit()

# --- INITIAL SYSTEM SETUP (Tabloları Otomatik Kurar) ---
def init_system():
    tables = [
        "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)",
        "CREATE TABLE IF NOT EXISTS menu (id SERIAL PRIMARY KEY, item_name TEXT, price DECIMAL(10,2), category TEXT, is_active BOOLEAN DEFAULT TRUE)",
        "CREATE TABLE IF NOT EXISTS ingredients (id SERIAL PRIMARY KEY, name TEXT UNIQUE, stock_qty DECIMAL(12,3) DEFAULT 0, unit TEXT)",
        "CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, items TEXT, total DECIMAL(10,2), cashier TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS recipes (id SERIAL PRIMARY KEY, menu_item_name TEXT, ingredient_name TEXT, qty_needed DECIMAL(12,3))"
    ]
    for sql in tables:
        run_action(sql)
    
    # Varsayılan Admin (admin / admin123)
    p_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
    run_action("INSERT INTO users (username, password, role) VALUES ('admin', :p, 'admin') ON CONFLICT DO NOTHING", {"p": p_hash})

if conn:
    init_system()

# --- HELPER FUNCTIONS ---
def get_baku_now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=4))).replace(tzinfo=None)

# --- UI SECTIONS ---

def inventory_page():
    st.header("📦 Anbar Paneli")
    
    # Yeni Malzeme Ekleme
    with st.expander("➕ Yeni Malzeme Ekle"):
        with st.form("new_ing"):
            name = st.text_input("Malzeme Adı (Örn: Süt, Kahve)")
            unit = st.selectbox("Birim", ["kg", "lt", "ədəd", "qr", "ml"])
            stock = st.number_input("Başlangıç Stoku", min_value=0.0)
            if st.form_submit_button("Anbara Əlavə Et"):
                run_action("INSERT INTO ingredients (name, stock_qty, unit) VALUES (:n, :s, :u) ON CONFLICT (name) DO UPDATE SET stock_qty = ingredients.stock_qty + :s", 
                           {"n": name, "s": stock, "u": unit})
                st.success(f"{name} əlavə edildi.")
                st.rerun()

    # Mevcut Stok Listesi
    st.subheader("Mövcud Stok")
    df = conn.query("SELECT name, stock_qty, unit FROM ingredients")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Anbar boşdur.")

def pos_page():
    col_menu, col_cart = st.columns([2.5, 1], gap="large")
    
    with col_menu:
        st.title("☕ Kassa")
        
        # Menü Yönetimi (Demo için hızlı ekleme)
        with st.sidebar.expander("🛠️ Menyuya Məhsul Əlavə Et"):
            m_name = st.text_input("Məhsul Adı")
            m_price = st.number_input("Qiymət", min_value=0.0)
            m_cat = st.selectbox("Kateqoriya", ["Kofe", "Çay", "Şirniyyat", "Digər"])
            if st.button("Menyuya Yaz"):
                run_action("INSERT INTO menu (item_name, price, category) VALUES (:n, :p, :c)", 
                           {"n": m_name, "p": m_price, "c": m_cat})
                st.rerun()

        # Menü Gösterimi
        menu_df = conn.query("SELECT * FROM menu WHERE is_active=True")
        if not menu_df.empty:
            cats = menu_df['category'].unique()
            tabs = st.tabs(list(cats))
            for i, cat in enumerate(cats):
                with tabs[i]:
                    items = menu_df[menu_df['category'] == cat]
                    m_cols = st.columns(3)
                    for idx, (_, row) in enumerate(items.iterrows()):
                        with m_cols[idx % 3]:
                            if st.button(f"**{row['item_name']}**\n{row['price']} AZN", key=f"it_{row['id']}", use_container_width=True):
                                if 'cart' not in st.session_state: st.session_state.cart = []
                                st.session_state.cart.append({'name': row['item_name'], 'price': float(row['price']), 'qty': 1})
                                st.rerun()
        else:
            st.info("Menyuda məhsul yoxdur.")

    with col_cart:
        st.subheader("🛒 Səbət")
        if 'cart' in st.session_state and st.session_state.cart:
            for i, item in enumerate(st.session_state.cart):
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{item['name']}**\n{item['price']} AZN")
                    if c2.button("🗑️", key=f"del_{i}"):
                        st.session_state.cart.pop(i)
                        st.rerun()
            
            st.divider()
            total = sum(i['price'] * i['qty'] for i in st.session_state.cart)
            st.metric("Yekun", f"{total:.2f} AZN")
            
            pay_type = st.radio("Ödəniş", ["Nağd", "Kart"], horizontal=True)
            
            if st.button("🚀 SATIŞI BİTİR", type="primary", use_container_width=True):
                items_str = ", ".join([f"{x['name']} x{x['qty']}" for x in st.session_state.cart])
                run_action("INSERT INTO sales (items, total, cashier, payment_method, created_at) VALUES (:i, :t, :c, :p, :tm)",
                           {"i": items_str, "t": total, "c": st.session_state.user, "p": pay_type, "tm": get_baku_now()})
                st.success("Satış uğurlu!")
                st.session_state.cart = []
                time.sleep(1)
                st.rerun()
        else:
            st.write("Səbət boşdur.")

# --- MAIN RUNNER ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Giriş")
    with st.form("login_form"):
        u = st.text_input("İstifadəçi")
        p = st.text_input("Şifrə", type="password")
        if st.form_submit_button("Giriş"):
            res = conn.query("SELECT password FROM users WHERE username=:u", params={"u":u})
            if not res.empty and bcrypt.checkpw(p.encode(), res.iloc[0]['password'].encode()):
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Xətalı məlumat!")
else:
    page = st.sidebar.radio("Menyu", ["Kassa", "Anbar", "Hesabatlar"])
    if st.sidebar.button("Çıxış"):
        st.session_state.logged_in = False
        st.rerun()
    
    if page == "Kassa": pos_page()
    elif page == "Anbar": inventory_page()
    elif page == "Hesabatlar":
        st.header("📊 Satış Hesabatları")
        sales_df = conn.query("SELECT * FROM sales ORDER BY created_at DESC")
        st.dataframe(sales_df, use_container_width=True)
