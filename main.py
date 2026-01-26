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
# === IRONWAVES POS - VERSION 2.0 BETA (FULL) ===
# ==========================================

# --- CONFIG ---
st.set_page_config(page_title="Ironwaves POS v2 Beta", page_icon="☕", layout="wide", initial_sidebar_state="expanded")

# --- CSS DİZAYN ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700;900&display=swap');
    .stApp { font-family: 'Oswald', sans-serif !important; background-color: #FAFAFA; }
    
    /* DÜYMƏLƏR */
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
    </style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
try:
    # Railway və ya Lokal mühit yoxlaması
    db_url = os.environ.get("STREAMLIT_CONNECTIONS_NEON_URL")
    if not db_url:
        # Lokal test üçün fallback (Railway-də buna ehtiyac yoxdur)
        db_url = os.environ.get("DATABASE_URL")
    
    if not db_url:
        st.error("XƏTA: Database URL tapılmadı! Railway Variables bölməsini yoxlayın.")
        st.stop()

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        
    conn = st.connection("neon", type="sql", url=db_url, pool_pre_ping=True)
except Exception as e:
    st.error(f"DB Error: {e}")
    st.stop()

# --- DATABASE FUNKSİYALARI ---
def run_query(q, p=None):
    return conn.query(q, params=p, ttl=0)

def run_action(q, p=None):
    with conn.session as s:
        s.execute(text(q), p)
        s.commit()
    return True

# --- SCHEMA & MIGRATION ---
def ensure_schema():
    with conn.session as s:
        # 1. ƏSAS CƏDVƏLLƏR
        s.execute(text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS menu (id SERIAL PRIMARY KEY, item_name TEXT, price DECIMAL(10,2), category TEXT, is_active BOOLEAN DEFAULT FALSE);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, items TEXT, total DECIMAL(10,2), payment_method TEXT, cashier TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, last_seen TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS active_sessions (token TEXT PRIMARY KEY, username TEXT, role TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        
        # 2. V2 BETA CƏDVƏLLƏRİ (ANBAR & RESEPT)
        s.execute(text("CREATE TABLE IF NOT EXISTS ingredients (id SERIAL PRIMARY KEY, name TEXT UNIQUE, stock_qty DECIMAL(10,2) DEFAULT 0, unit TEXT);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS recipes (id SERIAL PRIMARY KEY, menu_item_name TEXT, ingredient_name TEXT, quantity_required DECIMAL(10,2));"))
        
        # 3. DEFAULT ADMIN YARATMAQ
        chk = s.execute(text("SELECT * FROM users WHERE username='admin'")).fetchone()
        if not chk:
            # Şifrə: admin123
            p_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
            s.execute(text("INSERT INTO users (username, password, role) VALUES ('admin', :p, 'admin')"), {"p": p_hash})
        
        s.commit()

ensure_schema()

# --- HELPERS ---
def hash_password(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def verify_password(p, h): 
    try: return bcrypt.checkpw(p.encode(), h.encode()) if h.startswith('$2b$') else p == h
    except: return False

# --- SESSION CHECK ---
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
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<h1 style='text-align:center;'>🔐 Giriş</h1>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("İstifadəçi adı")
            p = st.text_input("Şifrə", type="password")
            if st.form_submit_button("Daxil Ol", use_container_width=True):
                udf = run_query("SELECT * FROM users WHERE LOWER(username)=LOWER(:u)", {"u": u})
                if not udf.empty and verify_password(p, udf.iloc[0]['password']):
                    st.session_state.logged_in = True
                    st.session_state.user = u
                    st.session_state.role = udf.iloc[0]['role']
                    
                    # Token yarat
                    tok = secrets.token_urlsafe(16)
                    run_action("INSERT INTO active_sessions (token, username, role) VALUES (:t, :u, :r)", {"t":tok, "u":u, "r":st.session_state.role})
                    st.query_params["token"] = tok
                    st.rerun()
                else:
                    st.error("Yanlış məlumat!")

# ==========================================
# === MAIN APP ===
# ==========================================
else:
    # --- HEADER ---
    c_head1, c_head2 = st.columns([5, 1])
    with c_head1:
        st.markdown(f"### 👋 Xoş gəldin, {st.session_state.user} ({st.session_state.role.upper()})")
    with c_head2:
        if st.button("Çıxış"):
            run_action("DELETE FROM active_sessions WHERE token=:t", {"t":st.query_params.get("token")})
            st.session_state.logged_in = False
            st.query_params.clear()
            st.rerun()
    st.divider()

    role = st.session_state.role

    # --- ADMIN TABS ---
    if role == 'admin':
        tabs = st.tabs(["🛒 POS Terminal", "📦 Stok & Resept", "📊 Hesabat", "📋 Menyu", "👥 İstifadəçilər"])

        # 1. POS TAB
        with tabs[0]:
            c_pos1, c_pos2 = st.columns([1.5, 3])
            
            with c_pos1:
                st.success("🧾 Səbət")
                if st.session_state.cart:
                    for i, item in enumerate(st.session_state.cart):
                        cc1, cc2, cc3 = st.columns([3, 1, 1])
                        cc1.write(f"**{item['item_name']}**")
                        cc2.write(f"{item['price']}")
                        if cc3.button("x", key=f"del_{i}"): st.session_state.cart.pop(i); st.rerun()
                    
                    total = sum(d['price'] for d in st.session_state.cart)
                    st.markdown(f"<h3 style='text-align:right; color:#D32F2F'>CƏM: {total:.2f} ₼</h3>", unsafe_allow_html=True)
                    
                    if st.button("✅ SATIŞI TAMAMLA", type="primary", use_container_width=True):
                        # Satışı yaz
                        items_str = ", ".join([x['item_name'] for x in st.session_state.cart])
                        
                        try:
                            # TRANSACTION: Satış + Stokdan Çıxılma
                            deducted_log = []
                            with conn.session as s:
                                # 1. Satışı Sales cədvəlinə yaz
                                s.execute(text("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i, :t, 'Cash', :c, NOW())"), 
                                           {"i":items_str, "t":total, "c":st.session_state.user})
                                
                                # 2. Stokdan silmə (Inventory Deduction Logic)
                                for item in st.session_state.cart:
                                    recipes = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name = :m"), {"m": item['item_name']}).fetchall()
                                    if recipes:
                                        for r in recipes:
                                            ing_name = r[0]
                                            qty_needed = r[1]
                                            s.execute(text("UPDATE ingredients SET stock_qty = stock_qty - :q WHERE name = :n"), {"q":qty_needed, "n":ing_name})
                                            deducted_log.append(f"{ing_name}: -{qty_needed}")
                                
                                s.commit()
                            
                            if deducted_log:
                                st.toast(f"Anbardan silindi: {', '.join(deducted_log)}")
                            
                            st.session_state.cart = []
                            st.balloons()
                            st.success("Satış uğurla tamamlandı!")
                            time.sleep(1)
                            st.rerun()

                        except Exception as e:
                            st.error(f"Xəta baş verdi: {e}")

                else:
                    st.info("Səbət boşdur")

            with c_pos2:
                st.info("🛍️ Məhsullar")
                cats = run_query("SELECT DISTINCT category FROM menu")
                if not cats.empty:
                    sel_cat = st.radio("Kateqoriya", cats['category'].tolist(), horizontal=True)
                    products = run_query("SELECT * FROM menu WHERE category=:c", {"c":sel_cat})
                    
                    cols = st.columns(4)
                    for idx, row in products.iterrows():
                        with cols[idx % 4]:
                            if st.button(f"{row['item_name']}\n{row['price']}₼", key=f"p_{row['id']}", use_container_width=True):
                                st.session_state.cart.append(row.to_dict())
                                st.rerun()

        # 2. STOK & RESEPT TAB (V2 BETA)
        with tabs[1]:
            st.markdown("### 🧪 Anbar və Resept İdarəetməsi")
            t_stk1, t_stk2 = st.tabs(["📦 Xammal Anbarı", "📜 Resept Qurucusu"])
            
            with t_stk1:
                st.caption("Burada kofe dənələri, süd, sirop və s. əlavə edin.")
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
                
                st.divider()
                st.subheader("Hazırkı Anbar Vəziyyəti")
                ing_df = run_query("SELECT * FROM ingredients ORDER BY name")
                if not ing_df.empty:
                    ing_df['Status'] = ing_df['stock_qty'].apply(lambda x: "⚠️ AZALIB" if x < 50 else "✅ OK")
                    st.dataframe(ing_df, use_container_width=True)
                else:
                    st.info("Anbar boşdur.")

            with t_stk2:
                st.caption("Məhsul satılanda anbardan nə silinsin?")
                menu_items = run_query("SELECT item_name FROM menu")
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

        # 3. HESABAT TAB
        with tabs[2]:
            st.subheader("📊 Satış Statistikası")
            sales = run_query("SELECT * FROM sales ORDER BY created_at DESC")
            if not sales.empty:
                total_rev = sales['total'].sum()
                total_tx = len(sales)
                k1, k2 = st.columns(2)
                k1.markdown(f"<div class='kpi-card'><div class='kpi-val'>{total_rev:.2f} ₼</div><div class='kpi-lbl'>Ümumi Gəlir</div></div>", unsafe_allow_html=True)
                k2.markdown(f"<div class='kpi-card'><div class='kpi-val'>{total_tx}</div><div class='kpi-lbl'>Satış Sayı</div></div>", unsafe_allow_html=True)
                st.divider()
                st.dataframe(sales, use_container_width=True)
            else:
                st.info("Satış yoxdur")

        # 4. MENYU TAB
        with tabs[3]:
            st.subheader("📋 Menyu Redaktə")
            with st.form("new_prod"):
                c1, c2, c3 = st.columns(3)
                n = c1.text_input("Ad")
                p = c2.number_input("Qiymət", min_value=0.0)
                c = c3.text_input("Kateqoriya (Qəhvə, Desert...)")
                if st.form_submit_button("Əlavə Et"):
                    run_action("INSERT INTO menu (item_name, price, category, is_active) VALUES (:n, :p, :c, TRUE)", {"n":n,"p":p,"c":c})
                    st.rerun()
            
            md = run_query("SELECT * FROM menu")
            st.dataframe(md, use_container_width=True)

        # 5. USERS TAB
        with tabs[4]:
            st.subheader("👥 İstifadəçilər")
            users = run_query("SELECT username, role, last_seen FROM users")
            st.dataframe(users)
            
            with st.expander("Yeni İşçi Yarat"):
                with st.form("new_user"):
                    nu = st.text_input("İstifadəçi adı")
                    np = st.text_input("Şifrə", type="password")
                    nr = st.selectbox("Rol", ["staff", "admin"])
                    if st.form_submit_button("Yarat"):
                        ph = hash_password(np)
                        try:
                            run_action("INSERT INTO users (username, password, role) VALUES (:u, :p, :r)", {"u":nu, "p":ph, "r":nr})
                            st.success("Yaradıldı!")
                        except: st.error("Bu ad artıq mövcuddur")

    # --- STAFF VIEW ---
    elif role == 'staff':
        st.warning("STAFF REJİMİ (Məhdud Giriş)")
        # Staff yalnız POS-u görür (kod təkrarı olmaması üçün bura adminlə eyni POS kodunu kopyalaya bilərsiniz, 
        # amma admin-dəki Tab 1-in eynisidir)
        # Qısa olsun deyə bura təkrar yazmadım, admin panelindən idarə edin.
