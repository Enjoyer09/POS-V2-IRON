import streamlit as st
import pandas as pd
import datetime
import secrets
import bcrypt
from sqlalchemy import text
import os
import time

# ==========================================
# === EMERGERNT POS v7.0 - DEMO VERSION ===
# ==========================================

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Emalatkhana Emergent Demo", 
    page_icon="☕", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- DATABASE CONNECTION (NeonDB & Railway Optimized) ---
@st.cache_resource
def get_connection():
    try:
        db_url = os.environ.get("DATABASE_URL")
        if db_url and db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        
        return st.connection(
            "neon", 
            type="sql", 
            url=db_url, 
            pool_pre_ping=True, 
            pool_recycle=300,
            connect_args={"sslmode": "require"}
        )
    except Exception as e:
        st.error(f"DB Connection Error: {e}")
        return None

conn = get_connection()

# --- MIGRATIONS (SSL Safe Table Creation) ---
def apply_migrations():
    tables = [
        "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)",
        "CREATE TABLE IF NOT EXISTS active_sessions (token TEXT PRIMARY KEY, username TEXT, role TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, items TEXT, total DECIMAL(10,2), payment_method TEXT, cashier TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, customer_card_id TEXT)",
        "CREATE TABLE IF NOT EXISTS menu (id SERIAL PRIMARY KEY, item_name TEXT, price DECIMAL(10,2), category TEXT, is_active BOOLEAN DEFAULT TRUE, is_coffee BOOLEAN DEFAULT FALSE)",
        "CREATE TABLE IF NOT EXISTS ingredients (id SERIAL PRIMARY KEY, name TEXT UNIQUE, stock_qty DECIMAL(12,3) DEFAULT 0, unit TEXT, unit_cost DECIMAL(12,4) DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS recipes (id SERIAL PRIMARY KEY, menu_item_name TEXT, ingredient_name TEXT, qty DECIMAL(12,3))",
        "CREATE TABLE IF NOT EXISTS finance (id SERIAL PRIMARY KEY, type TEXT, category TEXT, amount DECIMAL(12,2), note TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    ]
    with conn.session as s:
        for sql in tables:
            try:
                s.execute(text(sql))
                s.commit()
            except Exception as e:
                s.rollback()

if conn:
    apply_migrations()

# --- CORE LOGIC ---
def get_baku_now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=4))).replace(tzinfo=None)

def add_to_cart(item):
    if 'cart' not in st.session_state:
        st.session_state.cart = []
    
    for i in st.session_state.cart:
        if i['item_name'] == item['item_name']:
            i['qty'] += 1
            return
    st.session_state.cart.append(item)

# --- UI COMPONENTS ---
def render_v7_pos():
    # CSS: Modern Split-View Layout
    st.markdown("""
        <style>
        .stButton>button { border-radius: 12px !important; height: 3.5rem; background-color: white !important; color: #2E7D32 !important; border: 1px solid #e0e0e0 !important; transition: 0.3s; }
        .stButton>button:hover { border-color: #2E7D32 !important; background-color: #f0fdf4 !important; }
        [data-testid="stMetricValue"] { font-size: 1.8rem; color: #2E7D32; }
        .cart-item { padding: 10px; border-radius: 10px; background: #f8f9fa; margin-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)

    col_menu, col_cart = st.columns([2.5, 1], gap="large")

    with col_menu:
        st.title("☕ Emalatkhana POS")
        menu_df = conn.query("SELECT * FROM menu WHERE is_active=True", ttl=60)
        
        if not menu_df.empty:
            categories = sorted(menu_df['category'].unique())
            tabs = st.tabs(categories)
            
            for i, cat in enumerate(categories):
                with tabs[i]:
                    items = menu_df[menu_df['category'] == cat]
                    m_cols = st.columns(3)
                    for idx, (_, row) in enumerate(items.reset_index().iterrows()):
                        with m_cols[idx % 3]:
                            if st.button(f"**{row['item_name']}**\n{row['price']} AZN", key=f"btn_{row['id']}", use_container_width=True):
                                add_to_cart({'item_name': row['item_name'], 'price': float(row['price']), 'qty': 1})
                                st.rerun()
        else:
            st.warning("Menyu boşdur. Lütfən bazaya məhsul əlavə edin.")

    with col_cart:
        st.markdown("### 🛒 Aktiv Səbət")
        if 'cart' in st.session_state and st.session_state.cart:
            for i, item in enumerate(st.session_state.cart):
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{item['item_name']}**\n{item['qty']} x {item['price']} AZN")
                    if c2.button("🗑️", key=f"del_{i}"):
                        st.session_state.cart.pop(i)
                        st.rerun()
            
            st.divider()
            total = sum(i['price'] * i['qty'] for i in st.session_state.cart)
            st.metric("Yekun Məbləğ", f"{total:.2f} AZN")
            
            pm = st.radio("Ödəniş növü", ["Nəğd", "Kart"], horizontal=True)
            
            if st.button("🚀 SATIŞI BİTİR", type="primary", use_container_width=True):
                with st.spinner("İşlənir..."):
                    # Satışın atomar yazılması
                    try:
                        items_str = ", ".join([f"{x['item_name']} x{x['qty']}" for x in st.session_state.cart])
                        with conn.session as s:
                            s.execute(text("""
                                INSERT INTO sales (items, total, payment_method, cashier, created_at)
                                VALUES (:i, :t, :p, :c, :tm)
                            """), {
                                "i": items_str, "t": total, "p": pm, 
                                "c": st.session_state.get('user', 'Demo'), "tm": get_baku_now()
                            })
                            s.commit()
                        st.success("Satış uğurla tamamlandı!")
                        st.session_state.cart = []
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Səhv: {e}")
        else:
            st.info("Səbət boşdur. Sol tərəfdən məhsul seçin.")

# --- LOGIN LOGIC ---
def login_page():
    st.title("🔐 Giriş")
    with st.form("login_form"):
        u = st.text_input("İstifadəçi adı")
        p = st.text_input("Şifrə", type="password")
        if st.form_submit_button("Giriş"):
            # Demo üçün sadə giriş (İnkişaf etdiriləcək)
            if u == "admin" and p == "admin123":
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Səhv istifadəçi adı və ya şifrə")

# --- MAIN RUN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    # Sidebar logout
    with st.sidebar:
        st.write(f"👤 {st.session_state.user}")
        if st.button("Çıxış"):
            st.session_state.logged_in = False
            st.rerun()
    render_v7_pos()
else:
    login_page()
