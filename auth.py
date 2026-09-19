# auth.py
import streamlit as st
from db_utils import get_valid_db_connection

def enforce_admin_or_whitelisted_access():
    # Inject custom CSS for the pill-shaped Google login button
    st.markdown("""
        <style>
            .google-login-btn {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
                background-color: #ffffff;
                color: #3c4043 !important;
                border: 1px solid #dadce0;
                border-radius: 24px;
                font-family: 'Roboto', sans-serif;
                font-weight: 500;
                font-size: 14px;
                padding: 8px 22px;
                text-decoration: none !important;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                transition: background-color 0.2s, box-shadow 0.2s, border-color 0.2s;
            }
            .google-login-btn:hover {
                background-color: #f8f9fa;
                border-color: #dadce0;
                box-shadow: 0 1px 3px rgba(60,64,67,0.2);
                color: #202124 !important;
            }
            .google-login-btn svg {
                width: 18px;
                height: 18px;
            }
        </style>
    """, unsafe_allow_html=True)

    # Handle login via query parameters if action=login is triggered
    if "action" in st.query_params and st.query_params["action"] == "login":
        try:
            st.login("google")
        except Exception as e:
            st.error(f"Authentication configuration error: {e}")
            st.stop()

    user_is_logged_in = getattr(st.user, "is_logged_in", False)
    user_email = getattr(st.user, "email", "")
    
    if not user_is_logged_in:
        st.title("🔒 Authentication Required")
        st.markdown("Please sign in with your approved Google account to access this suite.")
        
        # Render the custom pill-shaped Google button with SVG logo
        st.markdown("""
            <div style="padding-top: 15px;">
                <a href="?action=login" target="_self" class="google-login-btn">
                    <svg version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
                        <path fill="#EA4335" d="M24 9.5c3.54 0 6.7 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                        <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                        <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.46-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48 z"/>
                    </svg>
                    Sign in with Google
                </a>
            </div>
        """, unsafe_allow_html=True)
        st.stop()

    if user_email.lower() == "arunpeswani@gmail.com":
        return True

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

    st.error(f"Access Denied for `{user_email}`. This account is not authorized or is pending approval.")
    if st.button("Sign Out", type="secondary"):
        st.logout()
    st.stop()

# --- USER PROFILE & ACCOUNT POPOVER HEADER - Arun---
def render_page_header(page_title):
    user_is_logged_in = getattr(st.user, "is_logged_in", False)
    user_email = getattr(st.user, "email", "User") if user_is_logged_in else ""
    user_name = getattr(st.user, "name", "Google User") if user_is_logged_in else ""
    user_avatar = (getattr(st.user, "picture", None) or getattr(st.user, "image", None)) if user_is_logged_in else "https://www.w3schools.com/howto/img_avatar.png"

    if "reset_count_beta" not in st.session_state:
        st.session_state.reset_count_beta = 0
    rc = st.session_state.reset_count_beta

    header_col1, header_col2 = st.columns([0.6, 0.4])
    with header_col1:
        st.header(page_title)
    with header_col2:
        avatar_col, menu_col = st.columns([0.3, 0.7])
        with avatar_col:
            st.markdown(f"""
                <div style="padding-top: 4px; text-align: right;">
                    <img src="{user_avatar}" style="width: 38px; height: 38px; border-radius: 50%; border: 2px solid #1a73e8; object-fit: cover;">
                </div>
            """, unsafe_allow_html=True)
        with menu_col:
            with st.popover("Account"):
                st.markdown(f"""
                    <div style="text-align: center; padding: 10px 0px;">
                        <img src="{user_avatar}" style="width: 60px; height: 60px; border-radius: 50%; border: 2px solid #1a73e8; object-fit: cover; margin-bottom: 6px;">
                        <div style="font-weight: 600; font-size: 14px; color: #202124;">{user_name}</div>
                        <div style="font-size: 12px; color: #5f6368; margin-top: 2px; word-break: break-all;">{user_email}</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown("---")
                if st.button("Sign Out", type="secondary", use_container_width=True, key=f"sign_out_shared_{rc}"):
                    st.logout()
