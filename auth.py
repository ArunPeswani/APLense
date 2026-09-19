import streamlit as st
from db_utils import get_valid_db_connection

def enforce_admin_or_whitelisted_access():
    # 1. Check if user is logged in via Streamlit Google Auth
    user_is_logged_in = getattr(st.user, "is_logged_in", False)
    user_email = getattr(st.user, "email", "")
    
    if not user_is_logged_in:
        st.title("🔒 Authentication Required")
        st.info("Please sign in with your Google account to access this suite.")
        if st.button("Sign in with Google", type="primary"):
            st.login("google")
        st.stop()

    # 2. Check if user is the main administrator
    if user_email.lower() == "arunpeswani@gmail.com":
        return True # Admin has full access

    # 3. Check database whitelist for approved guest graders
    try:
        conn = get_valid_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("select email from authorized_users where email = %s", (user_email.lower(),))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                return True
    except Exception:
        pass

    # 4. If logged in but not authorized
    st.error(f"Access Denied for `{user_email}`. This account is not authorized or is pending approval.")
    if st.button("Sign Out", type="secondary"):
        st.logout()
    st.stop()
