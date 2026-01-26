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
# === IRONWAVES POS - VERSION 2.2 BETA (RECIPE & BULK IMPORT) ===
# ==========================================

# --- CONFIG ---
st.set_page_config(page_title="Ironwaves POS v2.2", page_icon="☕", layout="wide", initial_sidebar_state="expanded")

# --- CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700;900&display=swap');
    .stApp { font-family: 'Oswald', sans-serif !important; background-color: #FAFAFA; }
    div.stButton > button { border-radius: 12px !important; height: 60px !important; font-weight: bold !important; }
    
    /* STOCK STATUS */
    .stock-ok { border-left: 5px solid green; padding: 10px; background: white; margin-bottom: 5px; border-radius: 5px; }
    .stock-low { border-left: 5px solid red; padding: 10px; background: #fff0f0; margin-bottom: 5px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- DB CONNECTION ---
try:
    db_url = os.environ.get("STREAMLIT_CONNECTIONS_NEON_URL") or os.environ.get("DATABASE_URL")
    if not db_url: st.error("Database URL not found!"); st.stop()
    if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    conn = st.connection("neon", type="sql", url=db_url, pool_pre_ping=True)
except Exception as e: st.error(f"DB Error: {e}"); st.stop()

# --- SCHEMA ---
def ensure_schema():
    with conn.session as s:
        s.execute(text("CREATE TABLE IF NOT EXISTS menu (id SERIAL PRIMARY KEY, item_name TEXT, price DECIMAL(10,2), category TEXT, is_active BOOLEAN DEFAULT FALSE);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, items TEXT, total DECIMAL(10,2), payment_method TEXT, cashier TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, last_seen TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS active_sessions (token TEXT PRIMARY KEY, username TEXT, role TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS ingredients (id SERIAL PRIMARY KEY, name TEXT UNIQUE, stock_qty DECIMAL(10,2) DEFAULT 0, unit TEXT, category TEXT, min_limit DECIMAL(10,2) DEFAULT 10);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS recipes (id SERIAL PRIMARY KEY, menu_item_name TEXT, ingredient_name TEXT, quantity_required DECIMAL(10,2));"))
        
        # Admin check
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
if 'selected_recipe_product' not in st.session_state: st.session_state.selected_recipe_product = None

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
# === LOGIN ===
# ==========================================
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.title("🔐 POS Giriş")
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
    # === MAIN APP ===
    # ==========================================
    st.markdown(f"### 👤 {st.session_state.user} | {st.session_state.role.upper()}")
    
    if st.session_state.role == 'admin':
        tabs = st.tabs(["🛒 POS", "📦 Stok (Anbar)", "📜 Resept Qurucusu", "📋 Menyu (Excel)", "⚙️ Ayarlar"])
        
        # --- TAB 1: POS (Satış) ---
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
                    
                    if st.button("✅ SATIŞI TƏSDİQLƏ", type="primary", use_container_width=True):
                        try:
                            items_str = ", ".join([x['item_name'] for x in st.session_state.cart])
                            run_action("INSERT INTO sales (items, total, payment_method, cashier, created_at) VALUES (:i, :t, 'Cash', :c, NOW())", 
                                       {"i":items_str, "t":total, "c":st.session_state.user})
                            
                            # STOKDAN ÇIXILMA (MƏNTİQ)
                            log = []
                            with conn.session as s:
                                for item in st.session_state.cart:
                                    # Hər məhsulun reseptini tapırıq
                                    recipes = s.execute(text("SELECT ingredient_name, quantity_required FROM recipes WHERE menu_item_name = :m"), {"m": item['item_name']}).fetchall()
                                    if recipes:
                                        for r in recipes:
                                            ing_name = r[0]
                                            qty_needed = r[1]
                                            s.execute(text("UPDATE ingredients SET stock_qty = stock_qty - :q WHERE name = :n"), {"q":qty_needed, "n":ing_name})
                                            log.append(f"{ing_name}: -{qty_needed}")
                                s.commit()
                            
                            if log: st.toast(f"Stok: {', '.join(set(log))}")
                            st.session_state.cart = []
                            st.success("Satıldı!")
                            time.sleep(1); st.rerun()
                        except Exception as e: st.error(f"Xəta: {e}")
                else: st.warning("Səbət boşdur")

            with c2:
                # KATEQORIYA
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

        # --- TAB 2: ANBAR (STOK) ---
        with tabs[1]:
            st.subheader("📦 Anbarın İdarə Edilməsi")
            
            c_add, c_list = st.columns([1, 2])
            
            with c_add:
                st.markdown("#### ➕ / ➖ İdarəetmə")
                mode = st.radio("Əməliyyat:", ["Əlavə Et / Artır", "Sil (Delete)"])
                
                if mode == "Əlavə Et / Artır":
                    with st.form("add_ing_form"):
                        name = st.text_input("Xammal Adı (Unikal)")
                        cat = st.selectbox("Kateqoriya", ["Bar", "Süd", "Siroplar", "Qablaşdırma", "Hazır Mal"])
                        qty = st.number_input("Miqdar", min_value=0.0)
                        unit = st.selectbox("Vahid", ["gr", "ml", "ədəd", "kq", "litr"])
                        limit = st.number_input("Limit (Xəbərdarlıq)", value=10.0)
                        if st.form_submit_button("Yadda Saxla"):
                            try:
                                run_action("""
                                    INSERT INTO ingredients (name, stock_qty, unit, category, min_limit) 
                                    VALUES (:n, :q, :u, :c, :l) 
                                    ON CONFLICT (name) DO UPDATE SET stock_qty = ingredients.stock_qty + :q
                                    """, {"n":name, "q":qty, "u":unit, "c":cat, "l":limit})
                                st.success(f"{name} uğurla yeniləndi!")
                                st.rerun()
                            except Exception as e: st.error(str(e))
                else:
                    # SİLMƏK REJİMİ
                    del_ing_list = run_query("SELECT name FROM ingredients")
                    if not del_ing_list.empty:
                        with st.form("del_ing_form"):
                            to_del = st.selectbox("Silinəcək Xammal", del_ing_list['name'].tolist())
                            if st.form_submit_button("Bazadan Sil"):
                                run_action("DELETE FROM ingredients WHERE name=:n", {"n":to_del})
                                st.warning(f"{to_del} silindi!")
                                st.rerun()

            with c_list:
                st.markdown("#### 📊 Anbar Vəziyyəti")
                ing_df = run_query("SELECT * FROM ingredients ORDER BY name")
                if not ing_df.empty:
                    for _, row in ing_df.iterrows():
                        color_cls = "stock-low" if row['stock_qty'] <= row['min_limit'] else "stock-ok"
                        msg = "⚠️ BİTİR!" if row['stock_qty'] <= row['min_limit'] else "✅"
                        st.markdown(f"""
                        <div class="{color_cls}">
                            <div style="display:flex; justify-content:space-between;">
                                <span><b>{row['name']}</b> ({row['category']})</span>
                                <span>{row['stock_qty']} {row['unit']}</span>
                            </div>
                            <div style="font-size:12px; color:gray;">Min: {row['min_limit']} | {msg}</div>
                        </div>
                        """, unsafe_allow_html=True)

        # --- TAB 3: RESEPT QURUCUSU (TƏKMİL) ---
        with tabs[2]:
            st.subheader("📜 Məhsul Reseptləri")
            st.info("Bir məhsula birdən çox xammal əlavə edə bilərsiniz.")
            
            c_sel, c_build = st.columns([1, 2])
            
            # 1. Məhsul Seçimi (Session State-də saxlayırıq)
            with c_sel:
                menu_items = run_query("SELECT item_name FROM menu WHERE is_active=TRUE")
                if not menu_items.empty:
                    sel_prod = st.selectbox("1. Resepti qurulacaq məhsulu seç:", menu_items['item_name'].unique())
                    st.session_state.selected_recipe_product = sel_prod
                else:
                    st.warning("Menyu boşdur.")
                    st.stop()

            # 2. Reseptin Yığılması
            with c_build:
                prod_name = st.session_state.selected_recipe_product
                st.markdown(f"#### 🛠️ {prod_name} tərkibi:")
                
                # --- İNDİKİ RESEPTİ GÖSTƏR ---
                curr_recipe = run_query("SELECT id, ingredient_name, quantity_required FROM recipes WHERE menu_item_name=:m", {"m":prod_name})
                
                if not curr_recipe.empty:
                    st.table(curr_recipe)
                    
                    # Reseptdən Silmə (Tək-tək)
                    del_rec_id = st.selectbox("Reseptdən silmək üçün ID seç:", curr_recipe['id'].tolist(), key="del_rec_sel")
                    if st.button("Seçilən sətri sil"):
                        run_action("DELETE FROM recipes WHERE id=:id", {"id":del_rec_id})
                        st.rerun()
                else:
                    st.info("Bu məhsul üçün hələ resept yoxdur.")

                st.divider()
                
                # --- YENİ XAMMAL ƏLAVƏ ET ---
                st.markdown("➕ Tərkib əlavə et:")
                all_ings = run_query("SELECT name, unit FROM ingredients ORDER BY name")
                
                if not all_ings.empty:
                    with st.form("add_rec_item"):
                        c_i1, c_i2 = st.columns(2)
                        sel_ing_row = c_i1.selectbox("Xammal", all_ings['name'].unique())
                        
                        # Vahidi tapmaq
                        u = all_ings[all_ings['name']==sel_ing_row].iloc[0]['unit']
                        qty_req = c_i2.number_input(f"Miqdar ({u})", min_value=0.1, step=0.1)
                        
                        if st.form_submit_button("Əlavə Et"):
                            run_action("INSERT INTO recipes (menu_item_name, ingredient_name, quantity_required) VALUES (:m, :i, :q)",
                                       {"m":prod_name, "i":sel_ing_row, "q":qty_req})
                            st.success("Əlavə edildi!")
                            st.rerun()
                else:
                    st.warning("Anbar boşdur. Əvvəlcə 'Stok' bölməsinə xammal əlavə edin.")

        # --- TAB 4: MENYU (BULK IMPORT) ---
        with tabs[3]:
            st.subheader("📋 Menyu İdarəetməsi & Excel Import")
            
            with st.expander("📥 Excel-dən Menyu Yüklə (Bulk Import)", expanded=False):
                st.info("Excel faylında bu sütunlar olmalıdır: item_name, price, category")
                up_file = st.file_uploader("Excel faylı (.xlsx)", type=['xlsx'])
                
                if up_file:
                    if st.button("Faylı Oxu və Bazaya Yaz"):
                        try:
                            df = pd.read_excel(up_file)
                            # Sütun yoxlanışı
                            if not {'item_name', 'price', 'category'}.issubset(df.columns):
                                st.error("Sütunlar düzgün deyil! (item_name, price, category) olmalıdır.")
                            else:
                                count = 0
                                for _, row in df.iterrows():
                                    if pd.isna(row['item_name']): continue
                                    # Insert
                                    run_action("""
                                        INSERT INTO menu (item_name, price, category, is_active) 
                                        VALUES (:n, :p, :c, TRUE)
                                        """, {"n":str(row['item_name']), "p":float(row['price']), "c":str(row['category'])})
                                    count += 1
                                st.success(f"✅ {count} məhsul menyuya əlavə edildi!")
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Xəta: {e}")

            st.divider()
            
            # TƏK-TƏK ƏLAVƏ ET
            with st.form("single_menu_add"):
                c1, c2, c3 = st.columns(3)
                n = c1.text_input("Ad")
                p = c2.number_input("Qiymət", min_value=0.0)
                c = c3.text_input("Kateqoriya")
                if st.form_submit_button("Tək Məhsul Yarat"):
                    run_action("INSERT INTO menu (item_name, price, category, is_active) VALUES (:n, :p, :c, TRUE)", {"n":n, "p":p, "c":c})
                    st.rerun()

            # MÖVCUD MENYU
            st.markdown("#### Mövcud Menyu")
            menu_df = run_query("SELECT * FROM menu ORDER BY category, item_name")
            st.dataframe(menu_df, use_container_width=True)

        # --- TAB 5: AYARLAR ---
        with tabs[4]:
            if st.button("Sistemdən Çıxış"):
                run_action("DELETE FROM active_sessions WHERE token=:t", {"t":st.query_params.get("token")})
                st.session_state.logged_in = False
                st.rerun()

    elif role == 'staff':
        # Staff yalnız POS-u görür (kod təkrarı olmasın deyə bura sadələşdirilmiş versiya qoyuruq)
        st.warning("Staff Rejimi") 
        # (Admin panelindəki POS kodunun eynisini bura da əlavə edə bilərsiniz)
