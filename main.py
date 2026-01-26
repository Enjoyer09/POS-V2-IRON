import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, datetime
import random
import string
import os
import ast # Mətn kimi saxlanılan siyahıları oxumaq üçün
import plotly.express as px # Qrafiklər üçün

# === VERSİYA KONFIQURASIYASI (V2.01 Alpha) ===
st.set_page_config(page_title="IronWaves POS V2.01 Alpha", layout="wide", page_icon="☕")

# === DATABASE BAĞLANTISI ===
DB_URL = os.environ.get("DATABASE_URL", "postgres://user:password@ep-sizinki.neon.tech/neondb?sslmode=require")

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
        st.error(f"Verilənlər Bazası Xətası: {e}")
        return None

# === SESSION STATE ===
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""
if 'cart' not in st.session_state:
    st.session_state.cart = []

# === YENİ ANALİTİKA SƏHİFƏSİ (V2.01) ===
def analytics_page():
    st.title("📊 Biznes Analitikası")
    st.markdown("Satışların detallı analizi və qrafiklər.")

    # Bazadan bütün satışları çək
    data = run_query("SELECT * FROM Inventory", fetch=True)
    
    if not data:
        st.warning("Hələ heç bir satış məlumatı yoxdur.")
        return

    # DataFrame yaradılması
    df = pd.DataFrame(data, columns=['Bill_No', 'Date', 'Cashier', 'Contact', 'Details'])
    
    # Detalları (string formatında olan listi) real məlumata çevirmək
    all_sold_items = []
    total_revenue = 0

    for index, row in df.iterrows():
        try:
            # 'Details' sütunundakı mətni listə çeviririk
            items = ast.literal_eval(row['Details'])
            for item in items:
                all_sold_items.append(item)
                total_revenue += item['total']
        except:
            pass
            
    # Əsas Metriklər (KPI)
    kpi1, kpi2, kpi3 = st.columns(3)
    
    with kpi1:
        st.metric("💰 Ümumi Gəlir", f"${total_revenue:,.2f}")
    with kpi2:
        st.metric("🧾 Ümumi Sifarişlər", len(df))
    with kpi3:
        avg_order = total_revenue / len(df) if len(df) > 0 else 0
        st.metric("📈 Orta Səbət Dəyəri", f"${avg_order:,.2f}")

    st.divider()

    # İki sütunlu qrafik sahəsi
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📅 Günlük Satış Dinamikası")
        # Tarixə görə qruplaşdırma
        daily_sales = df.groupby('Date').size().reset_index(name='Sifariş Sayı')
        fig_daily = px.bar(daily_sales, x='Date', y='Sifariş Sayı', color='Sifariş Sayı', 
                           color_continuous_scale='Blues')
        st.plotly_chart(fig_daily, use_container_width=True)

    with col2:
        st.subheader("🏆 Ən Çox Satılan Məhsullar")
        if all_sold_items:
            items_df = pd.DataFrame(all_sold_items)
            # Məhsul adına görə qruplaşdırıb miqdarı cəmləyirik
            top_products = items_df.groupby('name')['qty'].sum().reset_index().sort_values(by='qty', ascending=False)
            
            fig_pie = px.pie(top_products, values='qty', names='name', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Məhsul detalları tapılmadı.")

    # Kassir Performansı
    st.subheader("jh Kassir Performansı")
    cashier_perf = df.groupby('Cashier').size().reset_index(name='Satış Sayı')
    st.dataframe(cashier_perf, use_container_width=True)


# === DİGƏR SƏHİFƏLƏR (Köhnə kodlar olduğu kimi qalır, sadəcə birləşdirilir) ===

def login_page():
    st.title("☕ GIDEONS COFFEE SHOP - Giriş")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Sistemə Giriş")
        username = st.text_input("İstifadəçi adı")
        password = st.text_input("Şifrə", type="password")
        if st.button("Daxil ol"):
            # Rollar üzrə yoxlama...
            admin = run_query("SELECT * FROM Admin_Account WHERE admin_username=%s AND admin_password=%s", (username, password), fetch=True)
            if admin:
                st.session_state.logged_in = True
                st.session_state.user_role = "admin"
                st.session_state.user_name = admin[0][1]
                st.rerun()
            
            emp = run_query("SELECT * FROM Employee_Account WHERE employee_username=%s AND employee_password=%s", (username, password), fetch=True)
            if emp:
                st.session_state.logged_in = True
                st.session_state.user_role = "employee"
                st.session_state.user_name = emp[0][1]
                st.rerun()

            guest = run_query("SELECT * FROM Guest_Account WHERE guest_username=%s AND guest_password=%s", (username, password), fetch=True)
            if guest:
                st.session_state.logged_in = True
                st.session_state.user_role = "guest"
                st.session_state.user_name = guest[0][1]
                st.rerun()
            st.error("Yanlış istifadəçi adı və ya şifrə")

    with col2:
        st.subheader("Qonaq Qeydiyyatı")
        new_fullname = st.text_input("Tam Ad")
        new_user = st.text_input("Yeni İstifadəçi adı")
        new_pass = st.text_input("Yeni Şifrə", type="password")
        if st.button("Hesab Yarat"):
            run_query("INSERT INTO Guest_Account (guest_fullname, guest_username, guest_password) VALUES (%s, %s, %s)", 
                      (new_fullname, new_user, new_pass))
            st.success("Hesab yaradıldı!")

def dashboard():
    st.sidebar.title(f"👤 {st.session_state.user_name}")
    
    rol_aze = {"admin": "Admin", "employee": "İşçi", "guest": "Qonaq"}
    gosterilen_rol = rol_aze.get(st.session_state.user_role, "Naməlum")
    st.sidebar.text(f"Vəzifə: {gosterilen_rol}")
    
    # Menyu Seçimləri
    menu_options = ["Ana Səhifə"]
    
    if st.session_state.user_role == "admin":
        menu_options.append("📊 Analitika") # YENİ
    
    if st.session_state.user_role in ["admin", "employee"]:
        menu_options.extend(["POS (Satış)", "Məhsullar", "Tarixcə"])
    
    if st.session_state.user_role == "admin":
        menu_options.append("İstifadəçiləri İdarə Et")
        
    menu_options.append("Çıxış")
    
    choice = st.sidebar.radio("Menyu", menu_options)
    
    if choice == "Çıxış":
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.cart = []
        st.rerun()
    elif choice == "Ana Səhifə":
        st.header("İdarəetmə Panelinə Xoş Gəlmisiniz")
        st.metric(label="Sistem Statusu", value="V2.01 Alpha", delta="Stabil")
    elif choice == "📊 Analitika":
        analytics_page()
    elif choice == "Məhsullar":
        manage_products()
    elif choice == "POS (Satış)":
        pos_system()
    elif choice == "Tarixcə":
        view_history()
        # Tarixcəni Analitika səhifəsinə yönləndirmək də olar, amma hələlik saxlayırıq
        pass 
    elif choice == "İstifadəçiləri İdarə Et":
        manage_users()

def manage_products():
    st.header("Kofe Məhsullarını İdarə Et")
    with st.expander("Yeni Məhsul Əlavə Et"):
        c1, c2, c3 = st.columns(3)
        p_id = c1.text_input("Kofe ID")
        p_name = c2.text_input("Ad")
        p_type = c3.text_input("Növ")
        c4, c5, c6 = st.columns(3)
        p_stock = c4.number_input("Stok", min_value=0)
        p_price = c5.number_input("Qiymət ($)", min_value=0.0)
        p_disc = c6.number_input("Endirim (%)", min_value=0)
        if st.button("Məhsulu Əlavə Et"):
            run_query("INSERT INTO Coffee_Category VALUES (%s, %s, %s, %s, %s, %s)", (p_id, p_name, p_type, p_stock, p_price, p_disc))
            st.success("Əlavə edildi!")
            
    data = run_query("SELECT * FROM Coffee_Category", fetch=True)
    if data:
        st.dataframe(pd.DataFrame(data, columns=['ID', 'Ad', 'Növ', 'Endirim', 'Stok', 'Qiymət']))
        del_id = st.text_input("Silmək üçün ID")
        if st.button("Sil") and del_id:
            run_query("DELETE FROM Coffee_Category WHERE coffee_id=%s", (del_id,))
            st.rerun()

def pos_system():
    st.header("Satış Nöqtəsi (POS)")
    products = run_query("SELECT coffee_name, coffee_price, in_stock FROM Coffee_Category", fetch=True)
    if not products: return
    p_names = [p[0] for p in products]
    
    c1, c2 = st.columns([2, 1])
    with c1:
        selected_coffee = st.selectbox("Kofe Seçin", p_names)
        qty = st.number_input("Miqdar", min_value=1, value=1)
        if st.button("Səbətə At"):
            for p in products:
                if p[0] == selected_coffee:
                    if p[2] >= qty:
                        st.session_state.cart.append({"name": selected_coffee, "qty": qty, "price": p[1], "total": p[1]*qty})
                        st.success("Əlavə edildi!")
                    else:
                        st.error("Stok yoxdur!")
                    break
    with c2:
        if st.session_state.cart:
            df = pd.DataFrame(st.session_state.cart)
            st.dataframe(df)
            st.markdown(f"### Cəmi: ${sum(i['total'] for i in st.session_state.cart):,.2f}")
            if st.button("Təmizlə"):
                st.session_state.cart = []
                st.rerun()
            cust_name = st.text_input("Müştəri Adı")
            cust_contact = st.text_input("Əlaqə")
            if st.button("Qəbz Yarat") and cust_name:
                bill_no = "BB" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                bill_date = str(date.today())
                run_query("INSERT INTO Inventory VALUES (%s, %s, %s, %s, %s)", (bill_no, bill_date, st.session_state.user_name, cust_contact, str(st.session_state.cart)))
                for item in st.session_state.cart:
                    run_query("UPDATE Coffee_Category SET in_stock = in_stock - %s WHERE coffee_name = %s", (item['qty'], item['name']))
                st.session_state.cart = []
                st.success(f"Satış Uğurlu! #{bill_no}")

def view_history():
    st.header("Əməliyyat Tarixcəsi")
    data = run_query("SELECT * FROM Inventory", fetch=True)
    if data: st.dataframe(pd.DataFrame(data, columns=['Qəbz', 'Tarix', 'Kassir', 'Əlaqə', 'Detallar']))

def manage_users():
    st.header("İstifadəçi İdarəetməsi")
    t1, t2 = st.tabs(["İşçilər", "Adminlər"])
    with t1:
        id = st.text_input("ID")
        name = st.text_input("Ad")
        user = st.text_input("Login")
        pw = st.text_input("Pass")
        if st.button("Əlavə et"):
            run_query("INSERT INTO Employee_Account VALUES (%s, %s, %s, %s)", (id, name, user, pw))
            st.success("Oldu!")
        data = run_query("SELECT * FROM Employee_Account", fetch=True)
        if data: st.dataframe(pd.DataFrame(data, columns=['ID', 'Ad', 'Login', 'Pass']))

if __name__ == "__main__":
    if st.session_state.logged_in:
        dashboard()
    else:
        login_page()
