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
# SECURITY — ADMIN PASS REQUIRED
# =========================

ADMIN_DEFAULT_PASS = os.environ.get("ADMIN_PASS")
if not ADMIN_DEFAULT_PASS:
    st.error("ADMIN_PASS environment variable tələb olunur!")
    st.stop()

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

# =========================
# SESSION STATE DEFAULTS
# =========================

defaults = {
    "logged_in": False,
    "session_token": None,
    "cart_takeaway": [],
    "current_customer_ta": None,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =========================
# DATABASE CONNECTION
# =========================

db_url = os.environ.get("STREAMLIT_CONNECTIONS_NEON_URL") or os.environ.get("DATABASE_URL")

if not db_url:
    st.error("DATABASE_URL tapılmadı")
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
# SCHEMA ENSURE (SAFE)
# =========================

@st.cache_resource
def ensure_schema():
    with conn.session as s:

        s.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT,
            failed_attempts INTEGER DEFAULT 0
        )
        """))

        s.execute(text("""
        CREATE TABLE IF NOT EXISTS active_sessions (
            token TEXT PRIMARY KEY,
            username TEXT,
            role TEXT,
            created_at TIMESTAMP,
            expires_at TIMESTAMP
        )
        """))

        s.execute(text("""
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            items TEXT,
            total DECIMAL(10,2),
            payment_method TEXT,
            cashier TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        # create admin user if not exists
        pw_hash = bcrypt.hashpw(
            ADMIN_DEFAULT_PASS.encode(),
            bcrypt.gensalt()
        ).decode()

        s.execute(text("""
        INSERT INTO users (username, password, role)
        VALUES ('admin', :p, 'admin')
        ON CONFLICT (username) DO NOTHING
        """), {"p": pw_hash})

        s.commit()

ensure_schema()

# =========================
# PASSWORD HELPERS
# =========================

def hash_password(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_password(p, h):
    try:
        if h.startswith("$2"):
            return bcrypt.checkpw(p.encode(), h.encode())
        return p == h
    except:
        return False

# =========================
# SESSION MANAGEMENT (TTL)
# =========================

SESSION_HOURS = 8

def create_session(username, role):
    token = secrets.token_urlsafe(32)
    expires = get_baku_now() + datetime.timedelta(hours=SESSION_HOURS)

    run_action("""
    INSERT INTO active_sessions
    (token, username, role, created_at, expires_at)
    VALUES (:t,:u,:r,:c,:e)
    """, {
        "t": token,
        "u": username,
        "r": role,
        "c": get_baku_now(),
        "e": expires
    })

    return token


def validate_session():
    if not st.session_state.session_token:
        return False

    r = run_query("""
    SELECT * FROM active_sessions
    WHERE token=:t AND expires_at > :n
    """, {
        "t": st.session_state.session_token,
        "n": get_baku_now()
    })

    return not r.empty


def logout_user():
    if st.session_state.session_token:
        run_action(
            "DELETE FROM active_sessions WHERE token=:t",
            {"t": st.session_state.session_token}
        )

    st.session_state.logged_in = False
    st.session_state.session_token = None
    st.rerun()

# =========================
# EMAIL (SAFE)
# =========================

def send_email(to_email, subject, body):
    if not RESEND_API_KEY:
        return "NO_KEY"

    try:
        r = requests.post(
            "https://api.resend.com/emails",
            json={
                "from": f"{BRAND_NAME} <info@demo.ironwaves.store>",
                "to": [to_email],
                "subject": subject,
                "html": body
            },
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
        )

        if r.status_code == 200:
            return "OK"
        return "FAIL"

    except:
        return "ERR"

# =========================
# QR SAFE ID
# =========================

def generate_card_id():
    return secrets.token_hex(5)

# =========================
# HTML SAFE RECEIPT ROW
# =========================

def safe_item_name(x):
    return html.escape(str(x))

# =========================
# LOGIN PAGE
# =========================

if not st.session_state.logged_in:

    st.title(BRAND_NAME)
    st.caption(VERSION)

    with st.form("login"):
        u = st.text_input("User")
        p = st.text_input("Pass", type="password")

        if st.form_submit_button("Login"):

            row = run_query(
                "SELECT * FROM users WHERE username=:u",
                {"u": u}
            )

            if row.empty:
                st.error("Tapılmadı")
                st.stop()

            r = row.iloc[0]

            if r["failed_attempts"] >= 5:
                st.error("Hesab bloklanıb")
                st.stop()

            if verify_password(p, r["password"]):

                run_action("""
                UPDATE users SET failed_attempts=0
                WHERE username=:u
                """, {"u": u})

                token = create_session(u, r["role"])

                st.session_state.logged_in = True
                st.session_state.session_token = token
                st.session_state.user = u
                st.session_state.role = r["role"]

                st.rerun()

            else:
                run_action("""
                UPDATE users
                SET failed_attempts = failed_attempts + 1
                WHERE username=:u
                """, {"u": u})

                st.error("Şifrə səhv")

    st.stop()

# =========================
# AUTH CHECK
# =========================

if not validate_session():
    logout_user()

# =========================
# DASHBOARD HEADER
# =========================

st.success(f"👤 {st.session_state.user} | {st.session_state.role}")

if st.button("Logout"):
    logout_user()

st.divider()

st.info("PART 1 yükləndi — növbəti hissədə POS sistemi gəlir")
# =========================
# PART 2 — POS TAKEAWAY
# =========================

# --- MENU TABLE ENSURE ---

@st.cache_resource
def ensure_menu_table():
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

ensure_menu_table()


@st.cache_data(ttl=120)
def get_menu():
    return run_query("SELECT * FROM menu WHERE is_active=TRUE ORDER BY category, price")


# --- CUSTOMER TABLE ---

@st.cache_resource
def ensure_customer_table():
    run_action("""
    CREATE TABLE IF NOT EXISTS customers (
        card_id TEXT PRIMARY KEY,
        stars INTEGER DEFAULT 0,
        email TEXT
    )
    """)

ensure_customer_table()


def find_customer(cid):
    r = run_query(
        "SELECT * FROM customers WHERE card_id=:c",
        {"c": cid}
    )
    if r.empty:
        return None
    return r.iloc[0].to_dict()


# --- CART HELPERS ---

def add_to_cart(item):
    for i in st.session_state.cart_takeaway:
        if i["item_name"] == item["item_name"]:
            i["qty"] += 1
            return

    st.session_state.cart_takeaway.append({
        "item_name": item["item_name"],
        "price": float(item["price"]),
        "qty": 1,
        "is_coffee": bool(item["is_coffee"])
    })


def cart_total():
    return sum(i["qty"] * i["price"] for i in st.session_state.cart_takeaway)


# --- UI ---

st.subheader("🏃‍♂️ POS — Al Apar")

col_left, col_right = st.columns([1.4, 3])

# =========================
# LEFT — CART
# =========================

with col_left:

    st.markdown("### 🧾 Səbət")

    cust_code = st.text_input("Müştəri kartı (opsional)")

    customer = None
    if cust_code:
        customer = find_customer(cust_code)
        if customer:
            st.success(f"⭐ Balans: {customer['stars']}")
        else:
            st.warning("Tapılmadı")

    if st.session_state.cart_takeaway:

        for idx, it in enumerate(st.session_state.cart_takeaway):

            c1, c2, c3 = st.columns([3,1,1])

            c1.write(f"{safe_item_name(it['item_name'])} x{it['qty']}")

            if c2.button("➖", key=f"dec_{idx}"):
                if it["qty"] > 1:
                    it["qty"] -= 1
                else:
                    st.session_state.cart_takeaway.pop(idx)
                st.rerun()

            if c3.button("➕", key=f"inc_{idx}"):
                it["qty"] += 1
                st.rerun()

    total = cart_total()

    st.markdown(f"## 💰 {total:.2f} ₼")

    pay_method = st.radio(
        "Ödəniş",
        ["Cash", "Card"],
        horizontal=True
    )

    if st.button("✅ Satışı Bitir", type="primary", use_container_width=True):

        if not st.session_state.cart_takeaway:
            st.error("Səbət boşdur")
            st.stop()

        items_str = ", ".join([
            f"{i['item_name']} x{i['qty']}"
            for i in st.session_state.cart_takeaway
        ])

        run_action("""
        INSERT INTO sales
        (items, total, payment_method, cashier, created_at)
        VALUES (:i,:t,:p,:c,:d)
        """, {
            "i": items_str,
            "t": total,
            "p": pay_method,
            "c": st.session_state.user,
            "d": get_baku_now()
        })

        # loyalty stars
        if customer:
            coffee_count = sum(
                i["qty"]
                for i in st.session_state.cart_takeaway
                if i["is_coffee"]
            )

            if coffee_count > 0:
                run_action("""
                UPDATE customers
                SET stars = stars + :s
                WHERE card_id=:c
                """, {
                    "s": coffee_count,
                    "c": cust_code
                })

        st.success("Satış yazıldı")

        st.session_state.cart_takeaway = []
        st.rerun()


# =========================
# RIGHT — MENU
# =========================

with col_right:

    st.markdown("### ☕ Menyu")

    menu_df = get_menu()

    if menu_df.empty:
        st.warning("Menu boşdur — əvvəl məhsul əlavə et")
    else:

        cats = ["Hamısı"] + sorted(menu_df["category"].unique())

        sel_cat = st.radio(
            "Kateqoriya",
            cats,
            horizontal=True
        )

        if sel_cat != "Hamısı":
            menu_df = menu_df[menu_df["category"] == sel_cat]

        cols = st.columns(4)

        for i, row in menu_df.iterrows():

            with cols[i % 4]:

                if st.button(
                    f"{row['item_name']}\n{row['price']} ₼",
                    key=f"menu_{row['id']}",
                    use_container_width=True
                ):
                    add_to_cart(row.to_dict())
                    st.rerun()
# =========================
# PART 3 — INVENTORY + RECIPES
# =========================

# ---------- TABLES ----------

@st.cache_resource
def ensure_inventory_tables():

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

ensure_inventory_tables()


# ---------- CACHE ----------

@st.cache_data(ttl=120)
def get_ingredients():
    return run_query("SELECT * FROM ingredients ORDER BY name")

@st.cache_data(ttl=120)
def get_recipes():
    return run_query("SELECT * FROM recipes")


# ---------- STOCK ENGINE ----------

def check_and_deduct_stock(cart_items):

    with conn.session as s:

        # əvvəl yoxla
        for item in cart_items:

            recs = s.execute(text("""
            SELECT ingredient_name, qty
            FROM recipes
            WHERE menu_item_name=:m
            """), {"m": item["item_name"]}).fetchall()

            for ing_name, qty_need in recs:

                need = float(qty_need) * item["qty"]

                stock = s.execute(text("""
                SELECT stock_qty
                FROM ingredients
                WHERE name=:n
                """), {"n": ing_name}).fetchone()

                if not stock or float(stock[0]) < need:
                    raise Exception(f"Stok azdır: {ing_name}")

        # sonra düş
        for item in cart_items:

            recs = s.execute(text("""
            SELECT ingredient_name, qty
            FROM recipes
            WHERE menu_item_name=:m
            """), {"m": item["item_name"]}).fetchall()

            for ing_name, qty_need in recs:

                need = float(qty_need) * item["qty"]

                res = s.execute(text("""
                UPDATE ingredients
                SET stock_qty = stock_qty - :q
                WHERE name=:n AND stock_qty >= :q
                """), {"q": need, "n": ing_name})

                if res.rowcount == 0:
                    raise Exception(f"Race condition: {ing_name}")

        s.commit()


# ---------- INVENTORY UI ----------

st.divider()
st.subheader("📦 Anbar")

inv_tab1, inv_tab2 = st.tabs(["Mallar", "Resept"])

# =========================
# INGREDIENTS TAB
# =========================

with inv_tab1:

    st.markdown("### ➕ Yeni Xammal")

    with st.form("add_ing"):

        n = st.text_input("Ad")
        q = st.number_input("Miqdar", 0.0)
        u = st.text_input("Vahid")
        c = st.number_input("Vahid Maya Dəyəri", 0.0)

        if st.form_submit_button("Əlavə Et"):

            run_action("""
            INSERT INTO ingredients
            (name, stock_qty, unit, unit_cost)
            VALUES (:n,:q,:u,:c)
            ON CONFLICT (name)
            DO UPDATE SET stock_qty = ingredients.stock_qty + :q
            """, {
                "n": n,
                "q": q,
                "u": u,
                "c": c
            })

            st.success("Yazıldı")
            st.cache_data.clear()
            st.rerun()

    df_ing = get_ingredients()

    if not df_ing.empty:

        df_ing["total_value"] = (
            df_ing["stock_qty"] * df_ing["unit_cost"]
        )

        st.dataframe(df_ing, use_container_width=True)


# =========================
# RECIPES TAB
# =========================

with inv_tab2:

    st.markdown("### 🍽 Resept Bağla")

    menu_df = get_menu()
    ing_df = get_ingredients()

    if not menu_df.empty and not ing_df.empty:

        with st.form("add_recipe"):

            m = st.selectbox(
                "Menu Məhsulu",
                menu_df["item_name"].tolist()
            )

            ing = st.selectbox(
                "Xammal",
                ing_df["name"].tolist()
            )

            qty = st.number_input("Miqdar", 0.001)

            if st.form_submit_button("Bağla"):

                run_action("""
                INSERT INTO recipes
                (menu_item_name, ingredient_name, qty)
                VALUES (:m,:i,:q)
                """, {
                    "m": m,
                    "i": ing,
                    "q": qty
                })

                st.success("Resept əlavə olundu")
                st.cache_data.clear()
                st.rerun()

    rec_df = get_recipes()

    if not rec_df.empty:
        st.dataframe(rec_df, use_container_width=True)


# =========================
# PATCH POS PAYMENT — STOCK CHECK
# =========================

st.info("Stock engine aktivdir")

def safe_finalize_sale(cart, total, pay_method, cashier):

    check_and_deduct_stock(cart)

    items_str = ", ".join([
        f"{i['item_name']} x{i['qty']}"
        for i in cart
    ])

    run_action("""
    INSERT INTO sales
    (items,total,payment_method,cashier,created_at)
    VALUES (:i,:t,:p,:c,:d)
    """, {
        "i": items_str,
        "t": total,
        "p": pay_method,
        "c": cashier,
        "d": get_baku_now()
    })
# =========================
# PART 4 — FINANCE + CRM
# =========================

# ---------- TABLES ----------

@st.cache_resource
def ensure_fin_tables():

    run_action("""
    CREATE TABLE IF NOT EXISTS finance (
        id SERIAL PRIMARY KEY,
        type TEXT,
        category TEXT,
        amount DECIMAL(12,2),
        note TEXT,
        created_at TIMESTAMP
    )
    """)

ensure_fin_tables()


# ---------- FINANCE UI ----------

st.divider()
st.subheader("💰 Maliyyə")

fin_tab1, fin_tab2 = st.tabs(["Əməliyyat", "Z-Hesabat"])

# =========================
# ADD FINANCE RECORD
# =========================

with fin_tab1:

    with st.form("fin_add"):

        f_type = st.selectbox(
            "Tip",
            ["Giriş", "Çıxış"]
        )

        f_cat = st.text_input("Kateqoriya")
        f_amt = st.number_input("Məbləğ", 0.01)
        f_note = st.text_input("Qeyd")

        if st.form_submit_button("Yaz"):

            run_action("""
            INSERT INTO finance
            (type,category,amount,note,created_at)
            VALUES (:t,:c,:a,:n,:d)
            """, {
                "t": f_type,
                "c": f_cat,
                "a": f_amt,
                "n": f_note,
                "d": get_baku_now()
            })

            st.success("Yazıldı")
            st.rerun()

    fin_df = run_query("""
    SELECT * FROM finance
    ORDER BY created_at DESC
    LIMIT 50
    """)

    if not fin_df.empty:
        st.dataframe(fin_df, use_container_width=True)


# =========================
# Z REPORT
# =========================

with fin_tab2:

    st.markdown("### 📊 Günlük Hesabat")

    today = get_baku_now().date()

    sales_today = run_query("""
    SELECT SUM(total) s
    FROM sales
    WHERE DATE(created_at)=:d
    """, {"d": today}).iloc[0]["s"] or 0

    fin_in = run_query("""
    SELECT SUM(amount) s
    FROM finance
    WHERE type='Giriş'
    AND DATE(created_at)=:d
    """, {"d": today}).iloc[0]["s"] or 0

    fin_out = run_query("""
    SELECT SUM(amount) s
    FROM finance
    WHERE type='Çıxış'
    AND DATE(created_at)=:d
    """, {"d": today}).iloc[0]["s"] or 0

    net = float(sales_today) + float(fin_in) - float(fin_out)

    c1, c2, c3 = st.columns(3)

    c1.metric("Satış", f"{sales_today:.2f}")
    c2.metric("Əlavə Giriş", f"{fin_in:.2f}")
    c3.metric("Xərc", f"{fin_out:.2f}")

    st.markdown(f"## 🧾 Net: {net:.2f} ₼")


# =========================
# CRM
# =========================

st.divider()
st.subheader("👥 CRM")

crm_tab1, crm_tab2 = st.tabs(["Yeni Müştəri", "Siyahı"])

# ---------- ADD CUSTOMER ----------

with crm_tab1:

    with st.form("add_cust"):

        cid = generate_card_id()
        email = st.text_input("Email")

        if st.form_submit_button("Yarat"):

            run_action("""
            INSERT INTO customers
            (card_id,stars,email)
            VALUES (:c,0,:e)
            """, {
                "c": cid,
                "e": email
            })

            link = f"{APP_URL}/?id={cid}"

            st.success("Yaradıldı")
            st.code(link)


# ---------- LIST CUSTOMERS ----------

with crm_tab2:

    cdf = run_query("""
    SELECT card_id, stars, email
    FROM customers
    ORDER BY stars DESC
    """)

    if not cdf.empty:
        st.dataframe(cdf, use_container_width=True)


# =========================
# QR LINK TOOL
# =========================

st.divider()
st.subheader("🔗 QR Link Generator")

cid_in = st.text_input("Card ID")

if cid_in:
    st.code(f"{APP_URL}/?id={cid_in}")


# =========================
# SIMPLE ANALYTICS
# =========================

st.divider()
st.subheader("📈 Analitika")

sales_df = run_query("""
SELECT DATE(created_at) d, SUM(total) s
FROM sales
GROUP BY d
ORDER BY d DESC
LIMIT 14
""")

if not sales_df.empty:
    st.bar_chart(
        sales_df.set_index("d")["s"]
    )


# =========================
# EMAIL TEST
# =========================

st.divider()
st.subheader("📧 Email Test")

test_email = st.text_input("Email")

if st.button("Test Göndər"):

    res = send_email(
        test_email,
        "Demo POS",
        "<h3>Test OK</h3>"
    )

    if res == "OK":
        st.success("Göndərildi")
    else:
        st.error(f"Xəta: {res}")
