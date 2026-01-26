import streamlit as st
import psycopg2
import pandas as pd
from datetime import date
import random
import string
import os
import ast 
import plotly.express as px

# === KONFIQURASIYA (v2.03 Touch UI) ===
st.set_page_config(page_title="iRonwaves POS", layout="wide", page_icon="☕", initial_sidebar_state="collapsed")

# === CSS DİZAYN (NAVİQASİYA VƏ TOUCH) ===
st.markdown("""
    <style>
    /* Sidebar-ı gizlət */
    [data-testid="stSidebar"] {display: none;}
    
    /* Yuxarı Naviqasiya Paneli */
    .nav-container {
        display: flex;
        justify_content: center;
        gap: 15px;
        padding: 10px;
        background-color: #1E1E1E;
        border-radius: 15px;
        margin-bottom: 20px;
        position: sticky;
        top: 0;
        z-index: 999;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Naviqasiya Düymələri */
    div.stButton > button {
        width: 100%;
        height: 60px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 18px;
        border: none;
        transition: all 0.3s;
    }
    
    /* Məhsul Kartları */
    .product-card {
        background-color: #262730;
        border-radius: 15px;
        padding: 15px;
        text-align: center;
        border: 1px solid #333;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .price-tag {
        font-size: 22px;
        color: #FF4B4B;
        font-weight: bold;
    }
    .product-name {
        font-size: 16px;
        font-weight: 600;
        margin: 10px 0;
        height: 40px; /* Hündürlüyü fiksləyirik ki, sürüşməsin */
        display: flex;
        align-items: center;
        justify_content: center;
    }
    </style>
""", unsafe_allow_html=True)

# === DATABASE BAĞLANTISI ===
DB_URL = os.environ.get("DATABASE_URL", "postgres://user:password@ep-sizinki.neon.tech/neondb?sslmode=require")

# === EXCEL DATA (CSV-dən çıxarılıb kodun içinə qoyuldu) ===
# Exceldəki tarixləri və xətaları təmizləyən məntiq
DEFAULT_MENU = [
    {"name": "Su", "price": 2.0, "cat": "İçkilər", "type": "False"},
    {"name": "Çay (şirniyyat, fıstıq)", "price": 3.0, "cat": "İçkilər", "type": "False"},
    {"name": "Yaşıl çay - jasmin", "price": 4.0, "cat": "İçkilər", "type": "False"},
    {"name": "Meyvəli bitki çayı", "price": 4.0, "cat": "İçkilər", "type": "False"},
    {"name": "Portağal şirəsi (Təbii)", "price": 6.0, "cat": "İçkilər", "type": "False"},
    {"name": "Limonad (evsayağı)", "price": 6.0, "cat": "İçkilər", "type": "False"},
    {"name": "Kola", "price": 4.0, "cat": "İçkilər", "type": "False"},
    {"name": "Tonik", "price": 5.0, "cat": "İçkilər", "type": "False"},
    {"name": "Energetik (Redbull)", "price": 6.0, "cat": "İçkilər", "type": "False"},
    {"name": "Americano S", "price": 3.0, "cat": "Qəhvə", "type": "True"},
    {"name": "Americano M", "price": 4.0, "cat": "Qəhvə", "type": "True"},
    {"name": "Americano L", "price": 5.0, "cat": "Qəhvə", "type": "True"},
    {"name": "Cappuccino S", "price": 4.0, "cat": "Qəhvə", "type": "True"},
    {"name": "Cappuccino M", "price": 5.0, "cat": "Qəhvə", "type": "True"},
    {"name": "Cappuccino L", "price": 6.0, "cat": "Qəhvə", "type": "True"},
    {"name": "Latte S", "price": 4.5, "cat": "Qəhvə", "type": "True"},
    {"name": "Latte M", "price": 5.5, "cat": "Qəhvə", "type": "True"},
    {"name": "Latte L", "price": 6.5, "cat": "Qəhvə", "type": "True"},
    {"name": "Ristretto S", "price": 3.0, "cat": "Qəhvə", "type": "True"},
    {"name": "Espresso S", "price": 3.0, "cat": "Qəhvə", "type": "True"},
    {"name": "Raf S", "price": 5.0, "cat": "Qəhvə", "type": "True"},
    {"name": "Mocha S", "price": 5.0, "cat": "Qəhvə", "type": "True"},
]

# === DATABASE FUNKSİYALARI ===
def run_query(query, params=None, fetch=False):
    if "ep-sizinki.neon.tech" in DB_URL:
        st.error("XƏTA: Database URL təyin edilməyib.")
        st.stop()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute(query, params)
        if fetch:
            result = cur.fetchall()
            conn.close()
            return result
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"DB Xətası: {e}")
        return None

# === SESSION STATE ===
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = None
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'cart' not in st.session_state: st.session_state.cart = []
if 'active_tab' not in st.session_state: st.session_state.active_tab = "Home"

# === YENİ NAVİQASİYA PANELI (TOP BAR) ===
def navigation_bar():
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("🏠 Ana Səhifə", use_container_width=True):
            st.session_state.active_tab = "Home"
            st.rerun()
    with col2:
        if st.button("🛒 POS Terminal", use_container_width=True):
            st.session_state.active_tab = "POS"
            st.rerun()
    with col3:
        if st.button("📦 Məhsullar", use_container_width=True):
            st.session_state.active_tab = "Products"
            st.rerun()
    with col4:
        if st.button("📊 Analitika", use_container_width=True):
            st.session_state.active_tab = "Analytics"
            st.rerun()
    with col5:
        if st.button("🚪 Çıxış", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
    st.markdown("---")

# === LOGIN PAGE ===
def login_page():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.image("images/CoffeeShop-brand-logo.png", width=100) if os.path.exists("images/CoffeeShop-brand-logo.png") else None
        st.title("🔐 iRonwaves POS")
        
        with st.form("login"):
            user = st.text_input("İstifadəçi adı")
            pwd = st.text_input("Şifrə", type="password")
            if st.form_submit_button("Daxil Ol", use_container_width=True):
                admin = run_query("SELECT * FROM Admin_Account WHERE admin_username=%s AND admin_password=%s", (user, pwd), fetch=True)
                if admin:
                    st.session_state.logged_in = True
                    st.session_state.user_role = "admin"
                    st.session_state.user_name = admin[0][1]
                    st.rerun()
                
                emp = run_query("SELECT * FROM Employee_Account WHERE employee_username=%s AND employee_password=%s", (user, pwd), fetch=True)
                if emp:
                    st.session_state.logged_in = True
                    st.session_state.user_role = "employee"
                    st.session_state.user_name = emp[0][1]
                    st.rerun()
                st.error("Giriş uğursuz oldu.")

# === MAIN PAGES ===
def home_page():
    st.title(f"👋 Xoş Gəldin, {st.session_state.user_name}")
    st.markdown("### Bu gün nə etmək istəyirsən?")
    
    c1, c2 = st.columns(2)
    with c1:
        st.info("💡 POS Terminala keçmək üçün yuxarıdakı 'POS Terminal' düyməsinə bas.")
    with c2:
        st.success("✅ Server Statusu: Aktiv")

def analytics_page():
    st.title("📊 Satış Analitikası")
    data = run_query("SELECT * FROM Inventory", fetch=True)
    if data:
        df = pd.DataFrame(data, columns=['Bill', 'Date', 'Cashier', 'Contact', 'Details'])
        st.metric("Cəmi Sifariş", len(df))
        
        # Günlük qrafik
        daily = df.groupby('Date').size().reset_index(name='Count')
        st.bar_chart(daily, x='Date', y='Count')
    else:
        st.warning("Məlumat yoxdur.")

def manage_products_page():
    st.title("📦 Məhsul Bazası")
    
    # EXCEL IMPORT BUTTON
    with st.expander("📥 Excel Menyusunu Yüklə (Reset)", expanded=False):
        st.warning("Bu düymə bütün mövcud məhsulları silib, Excel-dəki məlumatları yazacaq!")
        if st.button("Bütün Menyunu Yenilə"):
            run_query("DELETE FROM Coffee_Category") # Təmizlə
            for item in DEFAULT_MENU:
                # ID yaratmaq (sadə məntiq)
                pid = ''.join(random.choices(string.ascii_uppercase, k=2)) + str(random.randint(10,99))
                run_query("INSERT INTO Coffee_Category VALUES (%s, %s, %s, %s, %s, %s)", 
                          (pid, item['name'], item['cat'], 100, item['price'], 0))
            st.success("Menyu uğurla yükləndi!")
            st.rerun()

    # Məhsul siyahısı
    data = run_query("SELECT * FROM Coffee_Category", fetch=True)
    if data:
        df = pd.DataFrame(data, columns=['ID', 'Ad', 'Kateqoriya', 'Endirim', 'Stok', 'Qiymət'])
        st.dataframe(df, use_container_width=True)

def pos_page():
    st.header("🛒 Satış Terminalı")
    
    col_prod, col_cart = st.columns([3, 1.2])
    
    with col_prod:
        # Kateqoriyalar
        cats = ["Qəhvə", "İçkilər", "Desertlər"]
        selected_cat = st.radio("Kateqoriya:", cats, horizontal=True, label_visibility="collapsed")
        
        st.divider()
        
        # Məhsulları çək
        products = run_query("SELECT coffee_name, coffee_price, in_stock FROM Coffee_Category WHERE type=%s", (selected_cat,), fetch=True)
        
        if not products and selected_cat == "Desertlər":
            st.info("Bu kateqoriyada məhsul yoxdur.")
            
        elif products:
            cols = st.columns(3) # Grid Layout
            img_list = ["images/menu-1.png", "images/menu-2.png", "images/menu-3.png", "images/menu-4.png"]
            
            for i, p in enumerate(products):
                name, price, stock = p
                with cols[i % 3]:
                    with st.container(border=True):
                        # Şəkil
                        img = img_list[i % len(img_list)]
                        if os.path.exists(img):
                            st.image(img, use_container_width=True)
                        else:
                            st.markdown("☕")
                        
                        st.markdown(f"<div class='product-name'>{name}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='price-tag'>${price}</div>", unsafe_allow_html=True)
                        
                        if st.button("ƏLAVƏ ET", key=f"add_{name}", use_container_width=True):
                             st.session_state.cart.append({"name": name, "price": price, "qty": 1, "total": price})
                             st.toast(f"{name} əlavə edildi")
                             st.rerun()

    with col_cart:
        st.subheader("🧾 Qəbz")
        if st.session_state.cart:
            for i, item in enumerate(st.session_state.cart):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(item['name'])
                c2.write(f"${item['price']}")
                if c3.button("🗑️", key=f"del_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
            
            total = sum(i['total'] for i in st.session_state.cart)
            st.markdown(f"### Cəmi: ${total:.2f}")
            
            if st.button("✅ Satışı Tamamla", type="primary", use_container_width=True):
                bill_no = "ORD-" + str(random.randint(1000, 9999))
                date_str = str(date.today())
                details = str(st.session_state.cart)
                run_query("INSERT INTO Inventory (bill_number, date, cashier_name, contact, bill_details) VALUES (%s, %s, %s, %s, %s)",
                          (bill_no, date_str, st.session_state.user_name, "Walk-in", details))
                st.session_state.cart = []
                st.balloons()
                st.success("Satış uğurlu!")
                st.rerun()
                
            if st.button("Təmizlə", use_container_width=True):
                st.session_state.cart = []
                st.rerun()

# === ENTRY POINT ===
if __name__ == "__main__":
    if st.session_state.logged_in:
        navigation_bar() # Yuxarı Naviqasiya
        
        if st.session_state.active_tab == "Home":
            home_page()
        elif st.session_state.active_tab == "POS":
            pos_page()
        elif st.session_state.active_tab == "Products":
            manage_products_page()
        elif st.session_state.active_tab == "Analytics":
            analytics_page()
    else:
        login_page()
