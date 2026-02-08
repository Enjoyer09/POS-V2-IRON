import streamlit as st
import pandas as pd
import datetime
import bcrypt
import secrets
from sqlalchemy import text
import os
import time
import re
from io import BytesIO

# ==========================================
# === EMERGERNT POS v7.0 - FINAL CORE ===
# ==========================================

st.set_page_config(page_title="Emalatkhana POS v7", layout="wide", page_icon="☕")

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

# --- INITIAL SYSTEM SETUP ---
def init_system():
    tables = [
        "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, locked_until TIMESTAMP, failed_attempts INTEGER DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS menu (id SERIAL PRIMARY KEY, item_name TEXT, price DECIMAL(10,2), category TEXT, is_active BOOLEAN DEFAULT TRUE, is_coffee BOOLEAN DEFAULT FALSE)",
        "CREATE TABLE IF NOT EXISTS ingredients (id SERIAL PRIMARY KEY, name TEXT UNIQUE, stock_qty DECIMAL(12,3) DEFAULT 0, unit TEXT, unit_cost DECIMAL(12,4) DEFAULT 0, min_limit DECIMAL(12,2) DEFAULT 2)",
        "CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, items TEXT, total DECIMAL(10,2), original_total DECIMAL(10,2), discount_amount DECIMAL(10,2), cashier TEXT, payment_method TEXT, note TEXT, customer_card_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS recipes (id SERIAL PRIMARY KEY, menu_item_name TEXT, ingredient_name TEXT, quantity_required DECIMAL(12,3))",
        "CREATE TABLE IF NOT EXISTS finance (id SERIAL PRIMARY KEY, type TEXT, category TEXT, amount DECIMAL(12,2), source TEXT, description TEXT, subject TEXT, created_by TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS customers (card_id TEXT PRIMARY KEY, stars INTEGER DEFAULT 0, type TEXT DEFAULT 'standard', email TEXT, is_active BOOLEAN DEFAULT FALSE)",
        "CREATE TABLE IF NOT EXISTS system_logs (id SERIAL PRIMARY KEY, username TEXT, action TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    ]
    for sql in tables: run_action(sql)
    p_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
    run_action("INSERT INTO users (username, password, role) VALUES ('admin', :p, 'admin') ON CONFLICT DO NOTHING", {"p": p_hash})

if conn: init_system()

# --- HELPERS ---
def get_baku_now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=4))).replace(tzinfo=None)

def log_system(action):
    run_action("INSERT INTO system_logs (username, action, created_at) VALUES (:u, :a, :t)", 
               {"u": st.session_state.user, "a": action, "t": get_baku_now()})

# --- POS ENGINE ---
def finalize_sale_atomic(cart, customer, pay_method, discount_val, discount_note, is_eco):
    try:
        with conn.session as s:
            total_raw = sum(i['price'] * i['qty'] for i in cart)
            final_total = total_raw * (1 - discount_val/100)
            items_str = ", ".join([f"{x['item_name']} x{x['qty']}" for x in cart])
            
            for item in cart:
                # Stok çıxışı
                recs = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m"), {"m": item['item_name']}).fetchall()
                for r in recs:
                    ing_name, q_req = r[0], float(r[1]) * item['qty']
                    if is_eco and ("stəkan" in ing_name.lower() or "qapaq" in ing_name.lower()): continue
                    
                    res = s.execute(text("UPDATE ingredients SET stock_qty = stock_qty - :q WHERE name = :n AND stock_qty >= :q"), {"q": q_req, "n": ing_name})
                    if res.rowcount == 0: raise Exception(f"Stok yetmir: {ing_name}")

            # Satışı yaz
            s.execute(text("""INSERT INTO sales (items, total, original_total, discount_amount, cashier, payment_method, note, customer_card_id, created_at) 
                              VALUES (:i, :t, :ot, :da, :c, :p, :n, :cid, :tm)"""),
                {"i": items_str, "t": final_total, "ot": total_raw, "da": total_raw - final_total, 
                 "c": st.session_state.user, "p": pay_method, "n": discount_note, "cid": customer['card_id'] if customer else None, "tm": get_baku_now()})
            
            # Ulduz artımı
            if customer:
                cf_qty = sum(i['qty'] for i in cart if i.get('is_coffee'))
                s.execute(text("UPDATE customers SET stars = stars + :s WHERE card_id = :cid"), {"s": cf_qty, "cid": customer['card_id']})
            
            s.commit()
            return True, final_total
    except Exception as e:
        return False, str(e)

# --- UI MODULES ---

def pos_module():
    col_menu, col_cart = st.columns([2.5, 1], gap="medium")
    
    with col_menu:
        st.subheader("☕ Kassa")
        # Dashboad mini-stats
        today_start = get_baku_now().replace(hour=0, minute=0, second=0)
        daily = conn.query("SELECT SUM(total) as t FROM sales WHERE created_at >= :d", params={"d": today_start}).iloc[0]['t'] or 0.0
        st.info(f"📊 Bugünkü Cəmi Satış: **{daily:.2f} AZN**")
        
        menu_df = conn.query("SELECT * FROM menu WHERE is_active=True")
        if not menu_df.empty:
            tabs = st.tabs(list(menu_df['category'].unique()))
            for i, cat in enumerate(menu_df['category'].unique()):
                with tabs[i]:
                    items = menu_df[menu_df['category'] == cat]
                    m_cols = st.columns(3)
                    for idx, (_, row) in enumerate(items.iterrows()):
                        with m_cols[idx % 3]:
                            if st.button(f"{row['item_name']}\n{row['price']} AZN", key=f"it_{row['id']}", use_container_width=True):
                                if 'cart' not in st.session_state: st.session_state.cart = []
                                st.session_state.cart.append({'item_name': row['item_name'], 'price': float(row['price']), 'qty': 1, 'is_coffee': row['is_coffee']})
                                st.rerun()

    with col_cart:
        st.subheader("🛒 Səbət")
        # Müştəri Skan
        with st.expander("👤 Müştəri Tap", expanded=False):
            cid_inp = st.text_input("Kart ID / QR")
            if st.button("🔍 Tap"):
                res = conn.query("SELECT * FROM customers WHERE card_id=:c", params={"c": cid_inp})
                st.session_state.customer = res.iloc[0].to_dict() if not res.empty else None
        
        if st.session_state.get('customer'):
            c = st.session_state.customer
            st.success(f"Müştəri: {c['card_id']} | ⭐ {c['stars']}")
            if st.button("❌"): st.session_state.customer = None; st.rerun()

        if st.session_state.get('cart'):
            for i, item in enumerate(st.session_state.cart):
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{item['item_name']}**")
                    if c2.button("🗑️", key=f"del_{i}"):
                        st.session_state.cart.pop(i); st.rerun()
            
            st.divider()
            disc_val = st.selectbox("Endirim %", [0, 5, 10, 20, 50, 100])
            disc_note = st.text_input("Səbəb") if disc_val > 0 else ""
            eco = st.checkbox("🥡 Öz Stəkanı (Eko)")
            
            total_raw = sum(i['price'] * i['qty'] for i in st.session_state.cart)
            st.metric("Yekun", f"{total_raw * (1-disc_val/100):.2f} AZN")
            
            pm = st.radio("Metod", ["Nağd", "Kart"], horizontal=True)
            if st.button("✅ SATIŞI BİTİR", type="primary", use_container_width=True):
                ok, msg = finalize_sale_atomic(st.session_state.cart, st.session_state.get('customer'), pm, disc_val, disc_note, eco)
                if ok:
                    st.success("Uğurlu!"); st.session_state.cart = []; time.sleep(1); st.rerun()
                else: st.error(msg)
        else: st.info("Səbət boşdur")

def inventory_module():
    st.header("📦 Anbar və Resept")
    t1, t2 = st.tabs(["Stok İdarə", "Resept Yaradıcı"])
    
    with t1:
        with st.form("ing_add"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("Ad")
            u = c2.selectbox("Vahid", ["kg", "lt", "ədəd", "qr", "ml"])
            s = c3.number_input("Miqdar", min_value=0.0)
            if st.form_submit_button("Əlavə et"):
                run_action("INSERT INTO ingredients (name, unit, stock_qty) VALUES (:n, :u, :s) ON CONFLICT (name) DO UPDATE SET stock_qty = ingredients.stock_qty + :s", {"n":n, "u":u, "s":s})
                st.rerun()
        
        ings = conn.query("SELECT * FROM ingredients")
        for _, row in ings.iterrows():
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"**{row['name']}**: {row['stock_qty']} {row['unit']}")
            if row['stock_qty'] <= row['min_limit']: col_a.warning("⚠️ Stok azdır!")

    with t2:
        st.subheader("Məhsula Resept Yaz")
        m_list = conn.query("SELECT item_name FROM menu")['item_name'].tolist()
        i_list = conn.query("SELECT name FROM ingredients")['name'].tolist()
        with st.form("rec_form"):
            m_sel = st.selectbox("Məhsul", m_list)
            i_sel = st.selectbox("Xammal", i_list)
            q_req = st.number_input("Miqdar", format="%.3f")
            if st.form_submit_button("Bağla"):
                run_action("INSERT INTO recipes (menu_item_name, ingredient_name, quantity_required) VALUES (:m, :i, :q)", {"m":m_sel, "i":i_sel, "q":q_req})
                st.success("Yazıldı")

def finance_module():
    st.header("💰 Maliyyə Mərkəzi")
    # Kassa balansı hesablama
    sales_cash = conn.query("SELECT SUM(total) as s FROM sales WHERE payment_method='Nağd'").iloc[0]['s'] or 0.0
    exp = conn.query("SELECT SUM(amount) as e FROM finance WHERE type='out'").iloc[0]['e'] or 0.0
    st.metric("🏪 Kassada olan Nağd (Cəmi)", f"{sales_cash - exp:.2f} AZN")
    
    with st.expander("💸 Yeni Xərc / Mədaxil"):
        with st.form("fin"):
            c1, c2, c3 = st.columns(3)
            f_t = c1.selectbox("Növ", ["out", "in"])
            f_c = c2.selectbox("Kat", ["Xammal", "Maaş", "Kirayə", "Kommunal", "Digər"])
            f_a = c3.number_input("Məbləğ")
            f_d = st.text_input("Qeyd")
            if st.form_submit_button("Yadda Saxla"):
                run_action("INSERT INTO finance (type, category, amount, description, created_by) VALUES (:t,:c,:a,:d,:u)",
                           {"t":f_t, "c":f_c, "a":f_a, "d":f_d, "u":st.session_state.user})
                st.rerun()

def admin_module():
    st.header("⚙️ Admin Panel")
    with st.expander("📝 Menyu Redaktə"):
        menu = conn.query("SELECT * FROM menu")
        edited = st.data_editor(menu, num_rows="dynamic")
        if st.button("Menyunu Yenilə"):
            run_action("DELETE FROM menu")
            edited.to_sql("menu", conn.engine, if_exists="append", index=False)
            st.success("Menyu yeniləndi!")

# --- AUTH SYSTEM ---
def login():
    st.markdown("<h1 style='text-align:center;'>🚀 Emergent POS</h1>", unsafe_allow_html=True)
    with st.container():
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            with st.form("l"):
                u = st.text_input("İstifadəçi")
                p = st.text_input("Şifrə", type="password")
                if st.form_submit_button("Giriş", use_container_width=True):
                    res = conn.query("SELECT password, role FROM users WHERE username=:u", params={"u":u})
                    if not res.empty and bcrypt.checkpw(p.encode(), res.iloc[0]['password'].encode()):
                        st.session_state.logged_in = True
                        st.session_state.user = u
                        st.session_state.role = res.iloc[0]['role']
                        st.rerun()
                    else: st.error("Səhv!")

# --- MAIN RUNNER ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if st.session_state.logged_in:
    # Sidebar Navigation
    with st.sidebar:
        st.title("Emalatkhana")
        st.write(f"👤 {st.session_state.user} ({st.session_state.role})")
        page = st.radio("Menyu", ["Kassa", "Anbar/Resept", "Maliyyə", "Admin", "Hesabatlar"])
        if st.button("🚪 Çıxış"):
            st.session_state.logged_in = False
            st.rerun()

    if page == "Kassa": pos_module()
    elif page == "Anbar/Resept": inventory_module()
    elif page == "Maliyyə": finance_module()
    elif page == "Admin": admin_module()
    elif page == "Hesabatlar":
        st.subheader("📊 Satış Tarixçəsi")
        st.dataframe(conn.query("SELECT * FROM sales ORDER BY created_at DESC"), use_container_width=True)
else:
    login()
