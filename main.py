import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, datetime
import random
import string
import os
import ast 
import plotly.express as px

# === KONFIQURASIYA (Ad Dəyişdirildi) ===
st.set_page_config(page_title="iRonwaves POS ALPHA LAB", layout="wide", page_icon="🧪")

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

# === SƏHİFƏLƏR ===

def login_page():
    st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>🧪 iRonwaves POS ALPHA LAB</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Gələcəyin POS Sistemi - İndi Sizinlə</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # st.form istifadə edirik ki, ENTER düyməsi işləsin
        with st.form("login_form"):
            st.subheader("Sistemə Giriş")
            username = st.text_input("İstifadəçi adı")
            password = st.text_input("Şifrə", type="password")
            
            # Form submit button (Enter vuranda bu işləyir)
            submitted = st.form_submit_button("Daxil ol", use_container_width=True)
            
            if submitted:
                # Admin Yoxlanışı
                admin = run_query("SELECT * FROM Admin_Account WHERE admin_username=%s AND admin_password=%s", (username, password), fetch=True)
                if admin:
                    st.session_state.logged_in = True
                    st.session_state.user_role = "admin"
                    st.session_state.user_name = admin[0][1]
                    st.rerun()
                
                # İşçi Yoxlanışı
                emp = run_query("SELECT * FROM Employee_Account WHERE employee_username=%s AND employee_password=%s", (username, password), fetch=True)
                if emp:
                    st.session_state.logged_in = True
                    st.session_state.user_role = "employee"
                    st.session_state.user_name = emp[0][1]
                    st.rerun()

                # Qonaq Yoxlanışı
                guest = run_query("SELECT * FROM Guest_Account WHERE guest_username=%s AND guest_password=%s", (username, password), fetch=True)
                if guest:
                    st.session_state.logged_in = True
                    st.session_state.user_role = "guest"
                    st.session_state.user_name = guest[0][1]
                    st.rerun()
                
                st.error("⚠️ Yanlış istifadəçi adı və ya şifrə")

def dashboard():
    st.sidebar.title(f"👨‍💻 {st.session_state.user_name}")
    
    rol_aze = {"admin": "Admin", "employee": "İşçi", "guest": "Qonaq"}
    gosterilen_rol = rol_aze.get(st.session_state.user_role, "Naməlum")
    st.sidebar.caption(f"Status: {gosterilen_rol} | Versiya: v2.02 Alpha")
    
    menu_options = ["Ana Səhifə"]
    
    if st.session_state.user_role == "admin":
        menu_options.append("📊 Analitika")
    
    if st.session_state.user_role in ["admin", "employee"]:
        menu_options.extend(["POS (Satış)", "Məhsullar", "Tarixcə"])
    
    if st.session_state.user_role == "admin":
        menu_options.append("İstifadəçilər")
        
    menu_options.append("Çıxış")
    
    choice = st.sidebar.radio("Naviqasiya", menu_options)
    
    if choice == "Çıxış":
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.cart = []
        st.rerun()
    elif choice == "Ana Səhifə":
        st.title("🧪 iRonwaves ALPHA LAB")
        c1, c2, c3 = st.columns(3)
        c1.metric("Server", "Neon.tech", "Online")
        c2.metric("Framework", "Streamlit", "v1.40")
        c3.metric("POS Status", "Active", "Stable")
        st.image("https://media.giphy.com/media/Q81NcsY6YxK7jxnr4v/giphy.gif", width=600)
    elif choice == "📊 Analitika":
        analytics_page()
    elif choice == "Məhsullar":
        manage_products()
    elif choice == "POS (Satış)":
        pos_system()
    elif choice == "Tarixcə":
        view_history()
    elif choice == "İstifadəçilər":
        manage_users()

def analytics_page():
    st.title("📊 Biznes Analitikası")
    data = run_query("SELECT * FROM Inventory", fetch=True)
    if not data:
        st.warning("Məlumat yoxdur.")
        return

    df = pd.DataFrame(data, columns=['Bill_No', 'Date', 'Cashier', 'Contact', 'Details'])
    
    all_sold_items = []
    total_revenue = 0

    for index, row in df.iterrows():
        try:
            items = ast.literal_eval(row['Details'])
            for item in items:
                all_sold_items.append(item)
                total_revenue += item['total']
        except:
            pass
            
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("💰 Ümumi Gəlir", f"${total_revenue:,.2f}")
    kpi2.metric("🧾 Sifarişlər", len(df))
    avg_order = total_revenue / len(df) if len(df) > 0 else 0
    kpi3.metric("📈 Orta Səbət", f"${avg_order:,.2f}")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Günlük Satış")
        daily_sales = df.groupby('Date').size().reset_index(name='Sifariş Sayı')
        fig_daily = px.bar(daily_sales, x='Date', y='Sifariş Sayı', color='Sifariş Sayı', color_continuous_scale='Viridis')
        st.plotly_chart(fig_daily, use_container_width=True)

    with col2:
        st.subheader("Top Məhsullar")
        if all_sold_items:
            items_df = pd.DataFrame(all_sold_items)
            top_products = items_df.groupby('name')['qty'].sum().reset_index().sort_values(by='qty', ascending=False)
            fig_pie = px.pie(top_products, values='qty', names='name', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

def manage_products():
    st.header("Məhsul İdarəetməsi")
    with st.expander("➕ Yeni Məhsul Əlavə Et", expanded=False):
        with st.form("add_product_form"):
            c1, c2, c3 = st.columns(3)
            p_id = c1.text_input("ID")
            p_name = c2.text_input("Ad")
            p_type = c3.text_input("Növ")
            c4, c5, c6 = st.columns(3)
            p_stock = c4.number_input("Stok", min_value=0)
            p_price = c5.number_input("Qiymət ($)", min_value=0.0)
            p_disc = c6.number_input("Endirim (%)", min_value=0)
            
            if st.form_submit_button("Yadda Saxla"):
                run_query("INSERT INTO Coffee_Category VALUES (%s, %s, %s, %s, %s, %s)", (p_id, p_name, p_type, p_stock, p_price, p_disc))
                st.success("Əlavə edildi!")
                st.rerun()
            
    data = run_query("SELECT * FROM Coffee_Category", fetch=True)
    if data:
        st.dataframe(pd.DataFrame(data, columns=['ID', 'Ad', 'Növ', 'Endirim', 'Stok', 'Qiymət']), use_container_width=True)
        
        with st.form("delete_product_form"):
            del_id = st.text_input("Silmək üçün ID")
            if st.form_submit_button("Sil"):
                run_query("DELETE FROM Coffee_Category WHERE coffee_id=%s", (del_id,))
                st.warning("Silindi!")
                st.rerun()

def pos_system():
    st.header("🛒 Satış Terminalı")
    products = run_query("SELECT coffee_name, coffee_price, in_stock FROM Coffee_Category", fetch=True)
    if not products: return
    p_names = [p[0] for p in products]
    
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        st.subheader("Məhsul Seçimi")
        # Buranı da form edirik ki, Enter işləsin
        with st.form("add_to_cart_form"):
            selected_coffee = st.selectbox("Kofe", p_names)
            col_q1, col_q2 = st.columns(2)
            qty = col_q1.number_input("Miqdar", min_value=1, value=1)
            # Burada əlavə notlar (modifier) ideyası üçün yer
            note = col_q2.text_input("Qeyd (məs: Şəkərsiz)")
            
            add_btn = st.form_submit_button("➕ Əlavə et (Enter)", use_container_width=True)
            
            if add_btn:
                for p in products:
                    if p[0] == selected_coffee:
                        if p[2] >= qty:
                            item_name = f"{selected_coffee} ({note})" if note else selected_coffee
                            st.session_state.cart.append({"name": item_name, "raw_name": p[0], "qty": qty, "price": p[1], "total": p[1]*qty})
                            st.success(f"{item_name} səbətdə!")
                        else:
                            st.error(f"Stok bitib! Qalıq: {p[2]}")
                        break

    with c2:
        st.subheader("🧾 Səbət")
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.dataframe(cart_df[["name", "qty", "total"]], use_container_width=True, hide_index=True)
            
            total_bill = sum(item['total'] for item in st.session_state.cart)
            st.markdown(f"<h3 style='text-align: right;'>Cəmi: ${total_bill:,.2f}</h3>", unsafe_allow_html=True)
            
            col_b1, col_b2 = st.columns(2)
            if col_b1.button("🗑️ Təmizlə", use_container_width=True):
                st.session_state.cart = []
                st.rerun()
            
            with st.expander("Ödəniş və Qəbz", expanded=True):
                cust_name = st.text_input("Müştəri Adı")
                cust_contact = st.text_input("Əlaqə")
                pay_method = st.selectbox("Ödəniş Növü", ["Nağd", "Kart", "Kaspi", "Apple Pay"])
                
                if st.button("✅ Satışı Tamamla", type="primary", use_container_width=True):
                    if cust_name:
                        bill_no = "BW-" + ''.join(random.choices(string.digits, k=6))
                        bill_date = str(date.today())
                        
                        # Inventory-ə yaz
                        details_str = str(st.session_state.cart) + f" | Method: {pay_method}"
                        run_query("INSERT INTO Inventory (bill_number, date, cashier_name, contact, bill_details) VALUES (%s, %s, %s, %s, %s)",
                                  (bill_no, bill_date, st.session_state.user_name, cust_contact, details_str))
                        
                        # Stoku yenilə
                        for item in st.session_state.cart:
                            run_query("UPDATE Coffee_Category SET in_stock = in_stock - %s WHERE coffee_name = %s", (item['qty'], item['raw_name']))
                        
                        st.session_state.cart = []
                        st.balloons()
                        st.success(f"Satış Uğurlu! Qəbz: #{bill_no}")
                    else:
                        st.warning("Müştəri adını daxil edin")

def view_history():
    st.header("Əməliyyat Tarixcəsi")
    data = run_query("SELECT * FROM Inventory ORDER BY bill_number DESC", fetch=True)
    if data: 
        st.dataframe(pd.DataFrame(data, columns=['Qəbz', 'Tarix', 'Kassir', 'Əlaqə', 'Detallar']), use_container_width=True)

def manage_users():
    st.header("İstifadəçi İdarəetməsi")
    t1, t2 = st.tabs(["İşçilər", "Adminlər"])
    with t1:
        with st.form("add_emp"):
            c1, c2 = st.columns(2)
            id = c1.text_input("ID")
            name = c2.text_input("Ad")
            user = c1.text_input("Login")
            pw = c2.text_input("Pass")
            if st.form_submit_button("Əlavə et"):
                run_query("INSERT INTO Employee_Account VALUES (%s, %s, %s, %s)", (id, name, user, pw))
                st.success("Oldu!")
                st.rerun()
        
        data = run_query("SELECT * FROM Employee_Account", fetch=True)
        if data: st.dataframe(pd.DataFrame(data, columns=['ID', 'Ad', 'Login', 'Pass']))

    with t2:
        st.info("Adminlər burada görünür.")
        admins = run_query("SELECT * FROM Admin_Account", fetch=True)
        if admins: st.dataframe(pd.DataFrame(admins, columns=['ID', 'Ad', 'Login', 'Pass']))

# === PROQRAMIN GİRİŞ NÖQTƏSİ ===
if __name__ == "__main__":
    if st.session_state.logged_in:
        dashboard()
    else:
        login_page()
