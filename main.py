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
from io import BytesIO
import requests
import base64
import json
import re

# =========================
# CONFIG
# =========================

VERSION = "v7.0 SECURE"
BRAND_NAME = "Emalatkhana Daily Drinks and Coffee"
APP_URL = "https://demo.ironwaves.store"

st.set_page_config(
    page_title=BRAND_NAME,
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================
# SECURITY
# =========================

ADMIN_DEFAULT_PASS = os.environ.get("ADMIN_PASS", "admin123") # Default əlavə edildi
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

# =========================
# SESSION STATE DEFAULTS
# =========================

defaults = {
    "logged_in": False,
    "session_token": None,
    "cart_takeaway": [],
    "current_customer_ta": None,
    "user": None,
    "role": None
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =========================
# DATABASE CONNECTION
# =========================

db_url = os.environ.get("STREAMLIT_CONNECTIONS_NEON_URL") or os.environ.get("DATABASE_URL")

if not db_url:
    st.error("DATABASE_URL tapılmadı. Zəhmət olmasa Secrets-də qeyd edin.")
    st.stop()

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

conn = st.connection(
    "neon",
    type="sql",
    url=db_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# =========================
# DB HELPERS
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
# AUTO DB MIGRATION & SCHEMA
# =========================

def safe_add_column(table, column_def):
    try:
        run_action(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column_def}")
    except:
        pass

@st.cache_resource
def ensure_schema():
    run_action("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT,
        failed_attempts INTEGER DEFAULT 0,
        last_seen TIMESTAMP
    )
    """)
    run_action("""
    CREATE TABLE IF NOT EXISTS active_sessions (
        token TEXT PRIMARY KEY,
        username TEXT,
        role TEXT,
        created_at TIMESTAMP,
        expires_at TIMESTAMP
    )
    """)
    run_action("""
    CREATE TABLE IF NOT EXISTS sales (
        id SERIAL PRIMARY KEY,
        items TEXT,
        total DECIMAL(10,2),
        payment_method TEXT,
        cashier TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        original_total DECIMAL(10,2) DEFAULT 0,
        discount_amount DECIMAL(10,2) DEFAULT 0,
        note TEXT
    )
    """)
    run_action("""
    CREATE TABLE IF NOT EXISTS menu (
        id SERIAL PRIMARY KEY,
        item_name TEXT,
        price DECIMAL(10,2),
        category TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        is_coffee BOOLEAN DEFAULT FALSE
    )
    """)
    run_action("""
    CREATE TABLE IF NOT EXISTS customers (
        card_id TEXT PRIMARY KEY,
        stars INTEGER DEFAULT 0,
        email TEXT
    )
    """)
    run_action("""
    CREATE TABLE IF NOT EXISTS ingredients (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE,
        stock_qty DECIMAL(12,3) DEFAULT 0,
        unit TEXT,
        unit_cost DECIMAL(12,4) DEFAULT 0
    )
    """)
    run_action("""
    CREATE TABLE IF NOT EXISTS recipes (
        id SERIAL PRIMARY KEY,
        menu_item_name TEXT,
        ingredient_name TEXT,
        qty DECIMAL(12,3)
    )
    """)
    run_action("""
    CREATE TABLE IF NOT EXISTS finance (
        id SERIAL PRIMARY KEY,
        type TEXT,
        category TEXT,
        subject TEXT,
        amount DECIMAL(12,2),
        note TEXT,
        created_at TIMESTAMP
    )
    """)

    # Admin user creation
    pw_hash = bcrypt.hashpw(ADMIN_DEFAULT_PASS.encode(), bcrypt.gensalt()).decode()
    run_action("""
    INSERT INTO users (username, password, role)
    VALUES ('admin', :p, 'admin')
    ON CONFLICT (username) DO NOTHING
    """, {"p": pw_hash})

ensure_schema()

# =========================
# AUTH HELPERS
# =========================

def verify_password(p, h):
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except:
        return p == h

def create_session(username, role):
    token = secrets.token_urlsafe(32)
    expires = get_baku_now() + datetime.timedelta(hours=8)
    run_action("""
    INSERT INTO active_sessions (token, username, role, created_at, expires_at)
    VALUES (:t,:u,:r,:c,:e)
    """, {"t": token, "u": username, "r": role, "c": get_baku_now(), "e": expires})
    return token

def validate_session():
    if not st.session_state.session_token:
        return False
    r = run_query("SELECT * FROM active_sessions WHERE token=:t AND expires_at > :n", 
                 {"t": st.session_state.session_token, "n": get_baku_now()})
    return not r.empty

def logout_user():
    if st.session_state.session_token:
        run_action("DELETE FROM active_sessions WHERE token=:t", {"t": st.session_state.session_token})
    st.session_state.logged_in = False
    st.session_state.session_token = None
    st.rerun()

# =========================
# LOGIN LOGIC
# =========================

if not st.session_state.logged_in:
    st.title(BRAND_NAME)
    st.caption(VERSION)
    with st.form("login"):
        u = st.text_input("İstifadəçi adı")
        p = st.text_input("Şifrə", type="password")
        if st.form_submit_button("Giriş"):
            row = run_query("SELECT * FROM users WHERE username=:u", {"u": u})
            if not row.empty:
                r = row.iloc[0]
                if r.get("failed_attempts", 0) >= 5:
                    st.error("Hesab bloklanıb")
                elif verify_password(p, r["password"]):
                    run_action("UPDATE users SET failed_attempts=0 WHERE username=:u", {"u": u})
                    token = create_session(u, r["role"])
                    st.session_state.logged_in = True
                    st.session_state.session_token = token
                    st.session_state.user = u
                    st.session_state.role = r["role"]
                    st.rerun()
                else:
                    run_action("UPDATE users SET failed_attempts = failed_attempts + 1 WHERE username=:u", {"u": u})
                    st.error("Şifrə səhvdir")
            else:
                st.error("İstifadəçi tapılmadı")
    st.stop()

if not validate_session():
    logout_user()

# =========================
# DASHBOARD UI
# =========================

st.sidebar.title(f"👤 {st.session_state.user}")
st.sidebar.info(f"Rol: {st.session_state.role}")
if st.sidebar.button("Çıxış"):
    logout_user()

tab_pos, tab_inv, tab_fin, tab_crm = st.tabs(["🏃‍♂️ POS", "📦 Anbar", "💰 Maliyyə", "👥 CRM"])

# =========================
# POS TAB
# =========================

with tab_pos:
    col_left, col_right = st.columns([1.5, 3])
    
    with col_left:
        st.subheader("🧾 Səbət")
        cust_code = st.text_input("Müştəri kartı (ID)")
        
        customer = None
        if cust_code:
            res = run_query("SELECT * FROM customers WHERE card_id=:c", {"c": cust_code})
            if not res.empty:
                customer = res.iloc[0]
                st.success(f"⭐ Balans: {customer['stars']}")

        if st.session_state.cart_takeaway:
            for idx, it in enumerate(st.session_state.cart_takeaway):
                c1, c2, c3 = st.columns([3,1,1])
                c1.write(f"{it['item_name']} x{it['qty']}")
                if c2.button("➖", key=f"dec_{idx}"):
                    if it["qty"] > 1: it["qty"] -= 1
                    else: st.session_state.cart_takeaway.pop(idx)
                    st.rerun()
                if c3.button("➕", key=f"inc_{idx}"):
                    it["qty"] += 1
                    st.rerun()

        total = sum(i["qty"] * i["price"] for i in st.session_state.cart_takeaway)
        st.markdown(f"### Cəm: {total:.2f} ₼")
        
        pay_method = st.radio("Ödəniş", ["Cash", "Card"], horizontal=True)
        
        if st.button("✅ Satışı Bitir", type="primary", use_container_width=True):
            if not st.session_state.cart_takeaway:
                st.error("Səbət boşdur")
            else:
                items_str = ", ".join([f"{i['item_name']} x{i['qty']}" for i in st.session_state.cart_takeaway])
                run_action("""
                INSERT INTO sales (items, total, payment_method, cashier, created_at)
                VALUES (:i, :t, :p, :c, :d)
                """, {"i": items_str, "t": total, "p": pay_method, "c": st.session_state.user, "d": get_baku_now()})
                
                if customer is not None:
                    coffee_q = sum(i["qty"] for i in st.session_state.cart_takeaway if i["is_coffee"])
                    if coffee_q > 0:
                        run_action("UPDATE customers SET stars = stars + :s WHERE card_id=:c", {"s": coffee_q, "c": cust_code})
                
                st.session_state.cart_takeaway = []
                st.success("Satış uğurla tamamlandı!")
                st.rerun()

    with col_right:
        st.subheader("☕ Menyu")
        menu_df = run_query("SELECT * FROM menu WHERE is_active=TRUE")
        if menu_df.empty:
            st.warning("Menyu boşdur. Anbar bölməsindən məhsul əlavə edin.")
        else:
            cats = ["Hamısı"] + sorted(menu_df["category"].unique().tolist())
            sel_cat = st.selectbox("Kateqoriya", cats)
            filtered_menu = menu_df if sel_cat == "Hamısı" else menu_df[menu_df["category"] == sel_cat]
            
            cols = st.columns(3)
            for i, row in filtered_menu.reset_index().iterrows():
                with cols[i % 3]:
                    if st.button(f"{row['item_name']}\n{row['price']} ₼", key=f"btn_{row['id']}", use_container_width=True):
                        # Add to cart logic
                        found = False
                        for item in st.session_state.cart_takeaway:
                            if item["item_name"] == row["item_name"]:
                                item["qty"] += 1
                                found = True
                                break
                        if not found:
                            st.session_state.cart_takeaway.append({
                                "item_name": row["item_name"], "price": float(row["price"]), 
                                "qty": 1, "is_coffee": bool(row["is_coffee"])
                            })
                        st.rerun()

# =========================
# INVENTORY TAB
# =========================

with tab_inv:
    st.subheader("📦 Mallar və Reseptlər")
    inv_t1, inv_t2, inv_t3 = st.tabs(["Xammallar", "Reseptlər", "Menyu İdarəetmə"])
    
    with inv_t1:
        with st.form("new_ing"):
            n = st.text_input("Xammal adı")
            q = st.number_input("Miqdar", 0.0)
            u = st.text_input("Vahid (kq, litr, ədəd)")
            c = st.number_input("Maya dəyəri", 0.0)
            if st.form_submit_button("Əlavə et"):
                run_action("""
                INSERT INTO ingredients (name, stock_qty, unit, unit_cost) VALUES (:n,:q,:u,:c)
                ON CONFLICT (name) DO UPDATE SET stock_qty = ingredients.stock_qty + :q
                """, {"n": n, "q": q, "u": u, "c": c})
                st.success("Yadda saxlanıldı")
                st.rerun()
        st.dataframe(run_query("SELECT * FROM ingredients"), use_container_width=True)

    with inv_t2:
        # Simple recipe view
        st.dataframe(run_query("SELECT * FROM recipes"), use_container_width=True)

    with inv_t3:
        with st.form("new_menu"):
            mn = st.text_input("Məhsul adı")
            mp = st.number_input("Qiymət", 0.0)
            mc = st.text_input("Kateqoriya")
            isc = st.checkbox("Kofedir?")
            if st.form_submit_button("Menyuya əlavə et"):
                run_action("INSERT INTO menu (item_name, price, category, is_coffee) VALUES (:n,:p,:c,:isc)",
                           {"n": mn, "p": mp, "c": mc, "isc": isc})
                st.rerun()

# =========================
# FINANCE TAB
# =========================

with tab_fin:
    st.subheader("📊 Maliyyə Hesabatı")
    today = get_baku_now().date()
    sales_today = run_query("SELECT SUM(total) as s FROM sales WHERE DATE(created_at)=:d", {"d": today}).iloc[0]['s'] or 0
    st.metric("Bugünkü Satış", f"{sales_today:.2f} ₼")
    
    st.bar_chart(run_query("SELECT DATE(created_at) as date, SUM(total) as total FROM sales GROUP BY date ORDER BY date DESC LIMIT 7").set_index("date"))

# =========================
# CRM TAB
# =========================

with tab_crm:
    st.subheader("👥 Müştəri Bazası")
    with st.form("new_cust"):
        cid = secrets.token_hex(4)
        em = st.text_input("Email")
        if st.form_submit_button("Müştəri yarat"):
            run_action("INSERT INTO customers (card_id, email) VALUES (:c, :e)", {"c": cid, "e": em})
            st.success(f"Yaradıldı! ID: {cid}")
    st.dataframe(run_query("SELECT * FROM customers"), use_container_width=True)
