import streamlit as st
import psycopg2
import pandas as pd
from datetime import date
import random
import string
import os
import ast 
import plotly.express as px

# === KONFIQURASIYA (v2.02 Alpha) ===
st.set_page_config(page_title="iRonwaves POS ALPHA LAB", layout="wide", page_icon="🧪")

# === DATABASE BAĞLANTISI ===
# Railway-də DATABASE_URL varsa onu, yoxdursa (lokalda) ikinci linki götürür.
DB_URL = os.environ.get("DATABASE_URL", "postgres://user:password@ep-sizinki.neon.tech/neondb?sslmode=require")

# === DATABASE FUNKSİYALARI ===
def run_query(query, params=None, fetch=False):
    # URL yoxdursa xəbərdarlıq
    if "ep-sizinki.neon.tech" in DB_URL:
        st.error("XƏTA: Database URL təyin edilməyib. Railway Variables bölməsini yoxlayın.")
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

# === SESSION STATE (Yaddaş) ===
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
    st.markdown("<p style='text-align: center;'>Gələcəyin POS Sistemi - v2.02</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # st.form istifadə edirik ki, ENTER düyməsi işləsin
        with st.form("login_form"):
            st.subheader("Sistemə Giriş")
            username = st.text_input("İstifadəçi adı")
            password = st.text_input("Şifrə", type="password")
            
            # Form submit button
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
    st.sidebar.caption(f"Status: {gosterilen_rol} | v2.02 Alpha")
    
    menu_options = ["Ana Səhifə"]
    
    if st.session_state.user_role == "admin":
        menu_options.append("📊 Analitika")
    
    if st.session_state.user_role in ["admin", "employee"]:
        menu_options.extend(["🛒 POS Terminal", "📦 Məhsullar", "📜 Tarixcə"])
    
    if st.session_state.user_role == "admin":
        menu_options.append("👥 İstifadəçilər")
        
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
        c3.metric("POS Status", "Active", "Touch Ready")
        
        # Əgər images qovluğunda home_bg varsa onu göstər, yoxdursa URL
        if os.path.exists("images/home_bg.jpg"):
            st.image("images/home_bg.jpg", use_container_width=True)
        else:
            st.info("Xoş gəlmisiniz! Satışa başlamaq üçün sol menyudan 'POS Terminal' seçin.")

    elif choice == "📊 Analitika":
        analytics_page()
    elif choice == "📦 Məhsullar":
        manage_products()
    elif choice == "🛒 POS Terminal":
        pos_system()
    elif choice == "📜 Tarixcə":
        view_history()
    elif choice == "👥 İstifadəçilər":
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
    # CSS ilə düymələri böyüdək ki, Touch Screen-də rahat olsun
    st.markdown("""
    <style>
    div.stButton > button:first-child {
        height: 3em;
        width: 100%;
        border-radius: 10px;
        font-weight: bold;
        border: 2px solid #FF4B4B;
    }
    .price-tag {
        font-size: 20px;
        font-weight: bold;
        color: #2e7bcf;
        text-align: center;
    }
    .product-name {
        font-size: 16px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.header("🛒 Satış Terminalı (Touch)")
    
    # Ekranı iki yerə bölürük: Məhsullar (70%) və Səbət (30%)
    col_products, col_cart = st.columns([2.5, 1.2])
    
    # === SOL TƏRƏF: MƏHSUL VİTRİNİ ===
    with col_products:
        # Kateqoriyalar (Tabs)
        tabs = st.tabs(["☕ İsti Kofe", "🥤 Soyuq İçkilər", "🍰 Desertlər", "🥪 Qəlyanaltı"])
        
        # Demo üçün hamısını birinci tabda göstəririk
        with tabs[0]:
            products = run_query("SELECT coffee_name, coffee_price, in_stock FROM Coffee_Category", fetch=True)
            
            if products:
                # Grid sistemi: hər sətirdə 3 məhsul
                cols = st.columns(3)
                
                # Şəkillər siyahısı (Sizin yüklədiyiniz fayllar)
                img_list = ["images/menu-1.png", "images/menu-2.png", "images/menu-3.png", 
                            "images/menu-4.png", "images/menu-5.png", "images/menu-6.png"]
                
                for index, product in enumerate(products):
                    p_name = product[0]
                    p_price = product[1]
                    p_stock = product[2]
                    
                    # Məhsulları sütunlara bölüşdürürük (mod 3 ilə)
                    with cols[index % 3]:
                        # Konteyner yaradırıq (Kart effekti üçün)
                        with st.container(border=True):
                            # Şəkil (Təsadüfi və ya sırayla seçilir)
                            img_path = img_list[index % len(img_list)]
                            
                            # Şəkli yoxla
                            if os.path.exists(img_path):
                                st.image(img_path, use_container_width=True)
                            else:
                                st.warning(f"Fayl yoxdur: {img_path}")
                            
                            st.markdown(f"<div class='product-name'>{p_name}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div class='price-tag'>${p_price}</div>", unsafe_allow_html=True)
                            
                            # Stok vəziyyəti
                            if p_stock < 5:
                                st.caption(f"⚠️ Son {p_stock} ədəd!")
                            else:
                                st.caption(f"Stok: {p_stock}")

                            # Əlavə et düyməsi (Unique Key vacibdir!)
                            if st.button("SƏBƏTƏ AT ➕", key=f"btn_{index}"):
                                if p_stock > 0:
                                    st.session_state.cart.append({
                                        "name": p_name, 
                                        "qty": 1, 
                                        "price": p_price, 
                                        "total": p_price,
                                        "raw_name": p_name # Update üçün lazımdır
                                    })
                                    st.toast(f"{p_name} əlavə edildi!", icon='🛒')
                                    st.rerun() # Səbəti yeniləmək üçün
                                else:
                                    st.error("Stok bitib!")

    # === SAĞ TƏRƏF: SƏBƏT ===
    with col_cart:
        st.subheader("🧾 Sifariş")
        
        if st.session_state.cart:
            # Səbəti DataFrame kimi göstər
            # cart_df = pd.DataFrame(st.session_state.cart)
            
            # Siyahı görünüşü
            for i, item in enumerate(st.session_state.cart):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"**{item['name']}**")
                c2.write(f"${item['price']}")
                if c3.button("❌", key=f"del_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
            
            st.divider()
            
            # Hesablama
            total_bill = sum(item['total'] for item in st.session_state.cart)
            tax = total_bill * 0.18 # 18% ƏDV nümunəsi
            final_total = total_bill + tax
            
            st.markdown(f"**Ara Cəmi:** ${total_bill:,.2f}")
            st.markdown(f"**ƏDV (18%):** ${tax:,.2f}")
            st.markdown(f"<h2 style='text-align: right; color: green;'>CƏMİ: ${final_total:,.2f}</h2>", unsafe_allow_html=True)
            
            # Ödəniş Forması
            with st.form("checkout_form"):
                cust_name = st.text_input("Müştəri Adı")
                pay_method = st.selectbox("Ödəniş", ["Nəğd", "Kart", "Apple Pay"])
                
                # Enter düyməsi ilə işləyən Submit
                if st.form_submit_button("✅ ÖDƏNİŞİ TƏSDİQLƏ", type="primary"):
                    if cust_name:
                        bill_no = "ORD-" + ''.join(random.choices(string.digits, k=5))
                        bill_date = str(date.today())
                        details_str = str(st.session_state.cart)
                        
                        # Inventory-ə yaz
                        run_query("INSERT INTO Inventory (bill_number, date, cashier_name, contact, bill_details) VALUES (%s, %s, %s, %s, %s)",
                                  (bill_no, bill_date, st.session_state.user_name, "N/A", details_str))
                        
                        # Stoku yenilə
                        for item in st.session_state.cart:
                            run_query("UPDATE Coffee_Category SET in_stock = in_stock - %s WHERE coffee_name = %s", (1, item['raw_name']))
                        
                        st.session_state.cart = []
                        st.balloons()
                        st.success(f"Uğurlu! Qəbz: #{bill_no}")
                        st.rerun()
                    else:
                        st.warning("Müştəri adını yazın!")
            
            if st.button("🗑️ Səbəti Boşalt"):
                st.session_state.cart = []
                st.rerun()
        else:
            st.info("Səbət boşdur. Sol tərəfdən məhsul seçin.")

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
