import streamlit as st
import pandas as pd
import datetime
import secrets
import bcrypt
from sqlalchemy import text
import os
import time

# ==========================================
# === EMERGERNT POS v7.0 - FULL DEMO ===
# ==========================================

st.set_page_config(page_title="Emalatkhana Emergent", layout="wide")

# --- DATABASE ---
@st.cache_resource
def get_connection():
    try:
        db_url = os.environ.get("DATABASE_URL")
        if db_url and db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        return st.connection("neon", type="sql", url=db_url, pool_pre_ping=True, connect_args={"sslmode": "require"})
    except: return None

conn = get_connection()

def run_action(q, p=None):
    with conn.session as s:
        s.execute(text(q), p if p else {})
        s.commit()

# --- MIGRATIONS & INITIAL DATA ---
def init_system():
    # Cədvəllər
    tables = [
        "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)",
        "CREATE TABLE IF NOT EXISTS active_sessions (token TEXT PRIMARY KEY, username TEXT, role TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS menu (id SERIAL PRIMARY KEY, item_name TEXT, price DECIMAL(10,2), category TEXT, is_active BOOLEAN DEFAULT TRUE)",
        "CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, items TEXT, total DECIMAL(10,2), cashier TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    ]
    for sql in tables: run_action(sql)
    
    # İlkin Admin yarat (Şifrə: admin123)
    p_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
    run_action("INSERT INTO users (username, password, role) VALUES ('admin', :p, 'admin') ON CONFLICT DO NOTHING", {"p": p_hash})

if conn: init_system()

# --- AUTH LOGIC ---
def check_auth():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    
    # 1. URL Token yoxla
    token = st.query_params.get("token")
    if token and not st.session_state.logged_in:
        res = conn.query("SELECT username, role FROM active_sessions WHERE token=:t", params={"t":token})
        if not res.empty:
            st.session_state.logged_in = True
            st.session_state.user = res.iloc[0]['username']
            st.query_params.clear()
            st.rerun()

# --- UI ---
def login_ui():
    st.markdown("<h1 style='text-align:center;'>🚀 Emergent POS Login</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        with st.form("login"):
            u = st.text_input("İstifadəçi")
            p = st.text_input("Şifrə", type="password")
            if st.form_submit_button("Giriş", use_container_width=True):
                res = conn.query("SELECT password, role FROM users WHERE username=:u", params={"u":u})
                if not res.empty and bcrypt.checkpw(p.encode(), res.iloc[0]['password'].encode()):
                    st.session_state.logged_in = True
                    st.session_state.user = u
                    st.rerun()
                else: st.error("Məlumatlar yanlışdır.")

def pos_ui():
    st.sidebar.write(f"👤 {st.session_state.user}")
    if st.sidebar.button("Çıxış"):
        st.session_state.logged_in = False
        st.rerun()
    
    # Kassa interfeysi (70/30)
    m_col, c_col = st.columns([2.5, 1])
    with m_col:
        st.subheader("☕ Menyu")
        # Test məhsulları əlavə etmək üçün düymə (Əgər menyu boşdursa)
        if st.button("➕ Test Məhsulu Əlavə Et (Demo)"):
            run_action("INSERT INTO menu (item_name, price, category) VALUES ('Espresso', 3.5, 'Kofe')")
            st.rerun()
            
        menu = conn.query("SELECT * FROM menu WHERE is_active=True")
        if not menu.empty:
            cols = st.columns(3)
            for idx, row in menu.iterrows():
                with cols[idx%3]:
                    if st.button(f"{row['item_name']}\n{row['price']} AZN", use_container_width=True):
                        st.toast(f"{row['item_name']} əlavə edildi")
        else: st.info("Menyu boşdur.")

# --- RUN ---
check_auth()
if st.session_state.logged_in:
    pos_ui()
else:
    login_ui()
