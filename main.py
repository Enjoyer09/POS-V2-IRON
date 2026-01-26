import streamlit as st
import psycopg2
import pandas as pd
from datetime import date
import random
import string
import os  # Railway dəyişənlərini oxumaq üçün vacibdir

# === KONFIQURASIYA ===
st.set_page_config(page_title="IronWaves Kofe POS", layout="wide", page_icon="☕")

# === DATABASE BAĞLANTISI ===
# 1. Railway-də "DATABASE_URL" dəyişəni varsa, onu götürür.
# 2. Əgər yoxdursa (lokal test edirsinizsə), ikinci dırnaq içindəki linki götürür.
# VACİB: Aşağıdakı "postgres://..." yerinə öz REAL Neon.tech linkinizi yapışdırın ki, lokalda da işləsin.
DB_URL = os.environ.get("DATABASE_URL", "postgres://user:password@ep-sizinki.neon.tech/neondb?sslmode=require")

# === DATABASE FUNKSİYALARI ===
def run_query(query, params=None, fetch=False):
    # Əgər DB_URL hələ təyin olunmayıbsa xəbərdarlıq et
    if "ep-sizinki.neon.tech" in DB_URL:
        st.error("XƏTA: Verilənlər bazası ünvanı düzgün deyil. Railway-də 'DATABASE_URL' dəyişənini təyin etdiyinizə əmin olun.")
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
    st.title("☕ GIDEONS COFFEE SHOP - Giriş")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Sistemə Giriş")
        username = st.text_input("İstifadəçi adı")
        password = st.text_input("Şifrə", type="password")
        
        if st.button("Daxil ol"):
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
            
            st.error("Yanlış istifadəçi adı və ya şifrə")

    with col2:
        st.subheader("Qonaq Qeydiyyatı")
        new_fullname = st.text_input("Tam Ad")
        new_user = st.text_input("Yeni İstifadəçi adı")
        new_pass = st.text_input("Yeni Şifrə", type="password")
        if st.button("Hesab Yarat"):
            run_query("INSERT INTO Guest_Account (guest_fullname, guest_username, guest_password) VALUES (%s, %s, %s)", 
                      (new_fullname, new_user, new_pass))
            st.success("Hesab yaradıldı! Zəhmət olmasa daxil olun.")

def dashboard():
    st.sidebar.title(f"👤 {st.session_state.user_name}")
    
    # Rolların tərcüməsi
    rol_aze = {
        "admin": "Admin",
        "employee": "İşçi",
        "guest": "Qonaq"
    }
    gosterilen_rol = rol_aze.get(st.session_state.user_role, "Naməlum")
    
    st.sidebar.text(f"Vəzifə: {gosterilen_rol}")
    
    menu_options = ["Ana Səhifə"]
    
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
        st.success(f"Sistem aktivdir. Xoş gəldiniz, {st.session_state.user_name}!")
        st.metric(label="Sistem Statusu", value="Aktiv", delta="Onlayn")

    elif choice == "Məhsullar":
        manage_products()

    elif choice == "POS (Satış)":
        pos_system()
        
    elif choice == "Tarixcə":
        view_history()
        
    elif choice == "İstifadəçiləri İdarə Et":
        manage_users()

def manage_products():
    st.header("Kofe Məhsullarını İdarə Et")
    
    # Yeni Məhsul Əlavə Etmə Forması
    with st.expander("Yeni Məhsul Əlavə Et"):
        c1, c2, c3 = st.columns(3)
        p_id = c1.text_input("Kofe ID")
        p_name = c2.text_input("Ad")
        p_type = c3.text_input("Növ")
        
        c4, c5, c6 = st.columns(3)
        p_stock = c4.number_input("Stok (Say)", min_value=0)
        p_price = c5.number_input("Qiymət ($)", min_value=0.0)
        p_disc = c6.number_input("Endirim (%)", min_value=0)
        
        if st.button("Məhsulu Əlavə Et"):
            run_query("INSERT INTO Coffee_Category (coffee_id, coffee_name, type, in_stock, coffee_price, discount) VALUES (%s, %s, %s, %s, %s, %s)",
                      (p_id, p_name, p_type, p_stock, p_price, p_disc))
            st.success("Əlavə edildi!")

    # Məhsul Siyahısı
    st.subheader("Məhsul Siyahısı")
    data = run_query("SELECT * FROM Coffee_Category", fetch=True)
    if data:
        df = pd.DataFrame(data, columns=['ID', 'Ad', 'Növ', 'Endirim', 'Stok', 'Qiymət'])
        st.dataframe(df)
        
        del_id = st.text_input("Silmək üçün ID daxil edin")
        if st.button("Məhsulu Sil") and del_id:
            run_query("DELETE FROM Coffee_Category WHERE coffee_id=%s", (del_id,))
            st.warning("Silindi!")
            st.rerun()

def pos_system():
    st.header("Satış Nöqtəsi (POS)")
    
    # 1. Məhsul Seçimi
    products = run_query("SELECT coffee_name, coffee_price, in_stock FROM Coffee_Category", fetch=True)
    
    if not products:
        st.warning("Bazada məhsul yoxdur.")
        return

    p_names = [p[0] for p in products]
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        selected_coffee = st.selectbox("Kofe Seçin", p_names)
        qty = st.number_input("Miqdar", min_value=1, value=1)
        
        if st.button("Səbətə At"):
            # Detalları gətir
            for p in products:
                if p[0] == selected_coffee:
                    price = p[1]
                    stock = p[2]
                    if stock >= qty:
                        st.session_state.cart.append({"name": selected_coffee, "qty": qty, "price": price, "total": price * qty})
                        st.success(f"{selected_coffee} əlavə edildi!")
                    else:
                        st.error(f"Stokda kifayət qədər yoxdur! (Mövcud: {stock})")
                    break

    with c2:
        st.subheader("Səbət")
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            # Sütun adlarını dəyişək
            cart_df.columns = ["Ad", "Miqdar", "Qiymət", "Cəmi"]
            st.dataframe(cart_df)
            
            total_bill = sum(item['total'] for item in st.session_state.cart)
            st.markdown(f"### Cəmi: ${total_bill}")
            
            if st.button("Səbəti Təmizlə"):
                st.session_state.cart = []
                st.rerun()
                
            st.divider()
            cust_name = st.text_input("Müştəri Adı")
            cust_contact = st.text_input("Əlaqə Nömrəsi")
            
            if st.button("Qəbz Yarat"):
                if cust_name:
                    bill_no = "BB" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                    bill_date = str(date.today())
                    details = str(st.session_state.cart)
                    
                    # Inventory-ə yaz
                    run_query("INSERT INTO Inventory (bill_number, date, cashier_name, contact, bill_details) VALUES (%s, %s, %s, %s, %s)",
                              (bill_no, bill_date, st.session_state.user_name, cust_contact, details))
                    
                    # Stoku yenilə
                    for item in st.session_state.cart:
                        run_query("UPDATE Coffee_Category SET in_stock = in_stock - %s WHERE coffee_name = %s", (item['qty'], item['name']))
                    
                    st.session_state.cart = []
                    st.success(f"Qəbz Yaradıldı! #{bill_no}")
                else:
                    st.error("Müştəri adını daxil edin")

def view_history():
    st.header("Əməliyyat Tarixcəsi")
    data = run_query("SELECT * FROM Inventory", fetch=True)
    if data:
        df = pd.DataFrame(data, columns=['Qəbz #', 'Tarix', 'Kassir', 'Əlaqə', 'Detallar'])
        st.dataframe(df)
    else:
        st.info("Hələ heç bir satış olmayıb.")

def manage_users():
    st.header("İstifadəçilərin İdarə Edilməsi (Admin)")
    
    tab1, tab2 = st.tabs(["İşçilər", "Adminlər"])
    
    with tab1:
        e_id = st.text_input("İşçi ID")
        e_name = st.text_input("İşçi Adı")
        e_user = st.text_input("İşçi İstifadəçi adı")
        e_pass = st.text_input("İşçi Şifrəsi")
        if st.button("İşçi Əlavə Et"):
            run_query("INSERT INTO Employee_Account VALUES (%s, %s, %s, %s)", (e_id, e_name, e_user, e_pass))
            st.success("İşçi əlavə edildi")
            
        emps = run_query("SELECT * FROM Employee_Account", fetch=True)
        if emps:
            st.dataframe(pd.DataFrame(emps, columns=['ID', 'Ad', 'Login', 'Şifrə']))

    with tab2:
        st.write("Mövcud Adminlər:")
        admins = run_query("SELECT * FROM Admin_Account", fetch=True)
        if admins:
            st.dataframe(pd.DataFrame(admins, columns=['ID', 'Ad', 'Login', 'Şifrə']))

# === PROQRAMIN GİRİŞ NÖQTƏSİ ===
if __name__ == "__main__":
    if st.session_state.logged_in:
        dashboard()
    else:
        login_page()
