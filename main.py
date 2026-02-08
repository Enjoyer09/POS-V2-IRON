import streamlit as st
import pandas as pd
import datetime
import secrets
import bcrypt
from sqlalchemy import text
import os
import time

# ==========================================
# === EMERGERNT POS v7.0 (DEMO CORE) ===
# ==========================================

# --- PAGE CONFIG ---
st.set_page_config(page_title="Emergent Demo", layout="wide", initial_sidebar_state="collapsed")

# --- DATABASE CONNECTION (NeonDB) ---
try:
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    conn = st.connection("neon", type="sql", url=db_url, pool_pre_ping=True, pool_recycle=1800)
except Exception as e:
    st.error(f"Bağlantı xətası: {e}")
    st.stop()

# --- SECURITY & SESSION LAYER ---
def secure_login_manager():
    """Tokeni URL-dən oxuyur, yoxlayır və dərhal silir."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    token = st.query_params.get("token")
    if token and not st.session_state.logged_in:
        with conn.session as s:
            res = s.execute(text("""
                SELECT username, role FROM active_sessions 
                WHERE token = :t AND created_at > NOW() - INTERVAL '8 hours'
            """), {"t": token}).fetchone()
            
            if res:
                st.session_state.logged_in = True
                st.session_state.user = res[0]
                st.session_state.role = res[1]
                st.session_state.token = token
                st.query_params.clear() # URL təmizlənir
                st.rerun()

# --- ATOMIC SALES ENGINE ---
def process_sale_atomic(cart, customer_id, cashier, payment_method):
    """Bütün satışı tək bir 'transaction' daxilində edir."""
    try:
        with conn.session as s:
            total_amt = 0
            items_list = []
            
            for item in cart:
                # 1. Stok yoxla və azalt
                res = s.execute(text("""
                    UPDATE ingredients SET stock_qty = stock_qty - :q 
                    WHERE name IN (SELECT ingredient_name FROM recipes WHERE menu_item_name = :m)
                    AND stock_qty >= :q
                """), {"q": item['qty'], "m": item['item_name']})
                
                # Qeyd: Bu sadələşdirilmiş stok məntiqidir, resept sayına görə mürəkkəbləşdirilə bilər.
                
                total_amt += item['price'] * item['qty']
                items_list.append(f"{item['item_name']} x{item['qty']}")

            # 2. Satışı qeyd et
            s.execute(text("""
                INSERT INTO sales (items, total, payment_method, cashier, created_at, customer_card_id)
                VALUES (:i, :t, :p, :c, NOW(), :cid)
            """), {
                "i": ", ".join(items_list), "t": total_amt, 
                "p": payment_method, "c": cashier, "cid": customer_id
            })
            
            s.commit()
            return True, total_amt
    except Exception as e:
        return False, str(e)

# --- MODERN UI COMPONENTS ---
def render_v7_pos():
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] { 
            background-color: #f0f2f6; border-radius: 5px; padding: 10px; 
        }
        </style>
    """, unsafe_allow_html=True)
    
    col_menu, col_cart = st.columns([2.2, 1], gap="medium")
    
    with col_menu:
        st.subheader("☕ Menyu")
        # Kateqoriya Tabları
        menu_data = conn.query("SELECT * FROM menu WHERE is_active=True", ttl=300)
        categories = menu_data['category'].unique()
        tabs = st.tabs(list(categories))
        
        for i, cat in enumerate(categories):
            with tabs[i]:
                items = menu_data[menu_data['category'] == cat]
                cols = st.columns(3)
                for idx, row in items.reset_index().iterrows():
                    with cols[idx % 3]:
                        if st.button(f"{row['item_name']}\n{row['price']} AZN", key=f"it_{row['id']}", use_container_width=True):
                            # Səbətə əlavə etmə məntiqi
                            if 'cart' not in st.session_state: st.session_state.cart = []
                            st.session_state.cart.append({'item_name': row['item_name'], 'price': float(row['price']), 'qty': 1})
                            st.rerun()

    with col_cart:
        st.subheader("🛒 Səbət")
        if 'cart' in st.session_state and st.session_state.cart:
            for i, item in enumerate(st.session_state.cart):
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{item['item_name']}**")
                    if c2.button("🗑️", key=f"del_{i}"):
                        st.session_state.cart.pop(i)
                        st.rerun()
            
            st.divider()
            total = sum(i['price'] * i['qty'] for i in st.session_state.cart)
            st.markdown(f"### Yekun: {total:.2f} AZN")
            
            if st.button("✅ ÖDƏNİŞİ TAMAMLA", type="primary", use_container_width=True):
                success, msg = process_sale_atomic(st.session_state.cart, None, st.session_state.user, "Cash")
                if success:
                    st.success("Satış uğurludur!")
                    st.session_state.cart = []
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Xəta: {msg}")
        else:
            st.info("Səbət boşdur")

# --- MAIN APP ---
secure_login_manager()

if st.session_state.logged_in:
    render_v7_pos()
else:
    st.title("Emergent POS - Demo Login")
    st.info("Zəhmət olmasa təhlükəsiz link ilə giriş edin.")
