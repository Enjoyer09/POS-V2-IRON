import streamlit as st
import pandas as pd
import random
import time
from sqlalchemy import text
import os
import bcrypt
import secrets
import datetime
import html
import requests

# =========================
# CONFIG & PAGE SETUP
# =========================
VERSION = "v7.1-STABLE"
BRAND_NAME = "Emalatkhana Daily Drinks and Coffee"
APP_URL = "https://demo.ironwaves.store"

st.set_page_config(
    page_title=BRAND_NAME,
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================
# SECURITY & DB ENV
# =========================
ADMIN_DEFAULT_PASS = os.environ.get("ADMIN_PASS", "admin123")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

db_url = os.environ.get("STREAMLIT_CONNECTIONS_NEON_URL") or os.environ.get("DATABASE_URL")

if not db_url:
    st.error("DATABASE_URL tapılmadı! Zəhmət olmasa Secrets bölməsində qeyd edin.")
    st.stop()

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

conn = st.connection("neon", type="sql", url=db_url)

# =========================
# HELPERS
# =========================
def run_query(q, p=None):
    return conn.query(q, params=p if p else {}, ttl=0)

def run_action(q, p=None):
    with conn.session as s:
        s.execute(text(q), p if p else {})
        s.commit()

def get_baku_now():
    return datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=4))
    ).replace(tzinfo=None)

# =========================
# DATABASE MIGRATIONS (Fixes the "Column Not Found" errors)
# =========================
def apply_migrations():
    # Cədvəllər yoxdursa yaradırıq
    run_action("""
    CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT);
    CREATE TABLE IF NOT EXISTS active_sessions (token TEXT PRIMARY KEY, username TEXT, role TEXT, created_at TIMESTAMP, expires_at TIMESTAMP);
    CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, items TEXT, total DECIMAL(10,2), payment_method TEXT, cashier TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS menu (id SERIAL PRIMARY KEY, item_name TEXT, price DECIMAL(10,2), category TEXT, is_active BOOLEAN DEFAULT TRUE, is_coffee BOOLEAN DEFAULT FALSE);
    CREATE TABLE IF NOT EXISTS customers (card_id TEXT PRIMARY KEY, stars INTEGER DEFAULT 0, email TEXT);
    CREATE TABLE IF NOT EXISTS ingredients (id SERIAL PRIMARY KEY, name TEXT UNIQUE, stock_qty DECIMAL(12,3) DEFAULT 0, unit TEXT, unit_cost DECIMAL(12,4) DEFAULT 0);
    CREATE TABLE IF NOT EXISTS recipes (id SERIAL PRIMARY KEY, menu_item_name TEXT, ingredient_name TEXT, qty DECIMAL(12,3));
    CREATE TABLE IF NOT EXISTS finance (id SERIAL PRIMARY KEY, type TEXT, category TEXT, amount DECIMAL(12,2), note TEXT, created_at TIMESTAMP);
    """)
    
    # Sütunları tək-tək yoxlayıb əlavə edirik (ProgrammingError qarşısını almaq üçün)
    migrations = [
        ("users", "failed_attempts", "INTEGER DEFAULT 0"),
        ("users", "last_seen", "TIMESTAMP"),
        ("sales", "original_total", "DECIMAL(10,2) DEFAULT 0"),
        ("sales", "discount_amount", "DECIMAL(10,2) DEFAULT 0"),
        ("sales", "note", "TEXT"),
        ("finance", "subject", "TEXT")
    ]
    for table, col, col_type in migrations:
        try:
            run_action(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}")
        except:
            pass

    # Admin user check
    pw_hash = bcrypt.hashpw(ADMIN_DEFAULT_PASS.encode(), bcrypt.gensalt()).decode()
    run_action("INSERT INTO users (username, password, role) VALUES ('admin', :p, 'admin') ON CONFLICT DO NOTHING", {"p": pw_hash})

apply_migrations()

# =========================
# SESSION STATE
# =========================
if "logged_in" not in st.session_state:
    st.session_state.update({
        "logged_in": False, "session_token": None, "user": None, "role": None, "cart_takeaway": []
    })

# =========================
# AUTH FUNCTIONS
# =========================
def verify_password(p, h):
    try: return bcrypt.checkpw(p.encode(), h.encode())
    except: return p == h

def validate_session():
    if not st.session_state.session_token: return False
    res = run_query("SELECT * FROM active_sessions WHERE token=:t AND expires_at > :n", 
                    {"t": st.session_state.session_token, "n": get_baku_now()})
    return not res.empty

def logout():
    run_action("DELETE FROM active_sessions WHERE token=:t", {"t": st.session_state.session_token})
    st.session_state.update({"logged_in": False, "session_token": None})
    st.rerun()

# =========================
# LOGIN UI
# =========================
if not st.session_state.logged_in:
    st.title(BRAND_NAME)
    with st.form("login_form"):
        u_input = st.text_input("İstifadəçi")
        p_input = st.text_input("Şifrə", type="password")
        if st.form_submit_button("Giriş"):
            user_row = run_query("SELECT * FROM users WHERE username=:u", {"u": u_input})
            if not user_row.empty:
                r = user_row.iloc[0]
                if r.get("failed_attempts", 0) >= 5:
                    st.error("Hesab bloklanıb!")
                elif verify_password(p_input, r["password"]):
                    token = secrets.token_urlsafe(32)
                    run_action("INSERT INTO active_sessions (token, username, role, created_at, expires_at) VALUES (:t,:u,:r,:c,:e)",
                               {"t": token, "u": u_input, "r": r["role"], "c": get_baku_now(), "e": get_baku_now() + datetime.timedelta(hours=8)})
                    run_action("UPDATE users SET failed_attempts=0 WHERE username=:u", {"u": u_input})
                    st.session_state.update({"logged_in": True, "session_token": token, "user": u_input, "role": r["role"]})
                    st.rerun()
                else:
                    run_action("UPDATE users SET failed_attempts = failed_attempts + 1 WHERE username=:u", {"u": u_input})
                    st.error("Şifrə yanlışdır!")
            else:
                st.error("İstifadəçi tapılmadı!")
    st.stop()

if not validate_session(): logout()

# =========================
# MAIN APP UI
# =========================
st.sidebar.title(f"👤 {st.session_state.user}")
if st.sidebar.button("Çıxış"): logout()

t1, t2, t3, t4 = st.tabs(["🛒 POS", "📦 Anbar", "💰 Maliyyə", "👥 CRM"])

# --- POS TAB ---
with t1:
    col1, col2 = st.columns([1.5, 3])
    with col1:
        st.subheader("🧾 Səbət")
        cust_id = st.text_input("Müştəri Kartı")
        for idx, item in enumerate(st.session_state.cart_takeaway):
            c_a, c_b = st.columns([3, 1])
            c_a.write(f"{item['name']} x{item['qty']}")
            if c_b.button("❌", key=f"del_{idx}"):
                st.session_state.cart_takeaway.pop(idx)
                st.rerun()
        
        total_price = sum(i['price'] * i['qty'] for i in st.session_state.cart_takeaway)
        st.markdown(f"### Cəm: {total_price:.2f} ₼")
        method = st.radio("Ödəniş", ["Cash", "Card"], horizontal=True)
        if st.button("Satışı Bitir", type="primary", use_container_width=True):
            if st.session_state.cart_takeaway:
                items_text = ", ".join([f"{i['name']}x{i['qty']}" for i in st.session_state.cart_takeaway])
                run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i,:t,:p,:c,:d)",
                           {"i": items_text, "t": total_price, "p": method, "c": st.session_state.user, "d": get_baku_now()})
                st.session_state.cart_takeaway = []
                st.success("Satış uğurla tamamlandı!")
                st.rerun()

    with col2:
        st.subheader("☕ Menyu")
        m_df = run_query("SELECT * FROM menu WHERE is_active=TRUE")
        if not m_df.empty:
            m_cols = st.columns(3)
            for i, r in m_df.iterrows():
                with m_cols[i % 3]:
                    if st.button(f"{r['item_name']}\n{r['price']} ₼", key=f"m_{r['id']}", use_container_width=True):
                        found = False
                        for ci in st.session_state.cart_takeaway:
                            if ci['name'] == r['item_name']:
                                ci['qty'] += 1
                                found = True
                                break
                        if not found:
                            st.session_state.cart_takeaway.append({"name": r['item_name'], "price": float(r['price']), "qty": 1, "is_coffee": r['is_coffee']})
                        st.rerun()

# --- INVENTORY TAB ---
with t2:
    st.subheader("Anbar İdarəetmə")
    sub_t1, sub_t2 = st.tabs(["Xammal", "Menyu Ayarları"])
    with sub_t1:
        with st.form("ing_form"):
            in_name = st.text_input("Ad")
            in_qty = st.number_input("Miqdar", 0.0)
            in_unit = st.text_input("Vahid")
            if st.form_submit_button("Əlavə et"):
                run_action("INSERT INTO ingredients (name, stock_qty, unit) VALUES (:n,:q,:u) ON CONFLICT (name) DO UPDATE SET stock_qty = ingredients.stock_qty + :q",
                           {"n": in_name, "q": in_qty, "u": in_unit})
                st.rerun()
        st.dataframe(run_query("SELECT * FROM ingredients"), use_container_width=True)

    with sub_t2:
        with st.form("menu_form"):
            m_n = st.text_input("Məhsul adı")
            m_p = st.number_input("Qiymət", 0.0)
            m_c = st.text_input("Kateqoriya")
            m_isc = st.checkbox("Kofedir?")
            if st.form_submit_button("Menyuya əlavə et"):
                run_action("INSERT INTO menu (item_name, price, category, is_coffee) VALUES (:n,:p,:c,:isc)",
                           {"n": m_n, "p": m_p, "c": m_c, "isc": m_isc})
                st.rerun()

# --- FINANCE TAB ---
with t3:
    st.subheader("Maliyyə Hesabatı")
    f_df = run_query("SELECT SUM(total) as total FROM sales WHERE DATE(created_at) = CURRENT_DATE")
    daily = f_df.iloc[0]['total'] or 0
    st.metric("Bugünkü Satış", f"{daily:.2f} ₼")
    st.bar_chart(run_query("SELECT DATE(created_at) as date, SUM(total) as total FROM sales GROUP BY date").set_index("date"))

# --- CRM TAB ---
with t4:
    st.subheader("Müştərilər")
    with st.form("cust_form"):
        c_email = st.text_input("Email")
        if st.form_submit_button("Yeni Müştəri Yarad"):
            new_id = secrets.token_hex(4)
            run_action("INSERT INTO customers (card_id, email) VALUES (:i, :e)", {"i": new_id, "e": c_email})
            st.success(f"Müştəri yaradıldı! ID: {new_id}")
    st.dataframe(run_query("SELECT * FROM customers"), use_container_width=True)
