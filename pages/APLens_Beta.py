import streamlit as st

st.set_page_config(page_title="APLens Beta - Google Sign-In", page_icon="🧪", layout="centered")

# --- SAFE USER DATA EXTRACTION ---
user_email = getattr(st.user, "email", "User") if st.user.is_logged_in else ""
user_name = getattr(st.user, "name", "Google User") if st.user.is_logged_in else ""
user_avatar = (getattr(st.user, "picture", None) or getattr(st.user, "image", None)) if st.user.is_logged_in else ""

if not user_avatar:
    user_avatar = "https://www.w3schools.com/howto/img_avatar.png"

# --- CUSTOM CSS FOR BUTTON WITH GOOGLE LOGO ---
if not st.user.is_logged_in:
    st.markdown("""
        <style>
            /* Style Streamlit button into an official Google Sign-In button with logo */
            div.stButton > button {
                border-radius: 24px !important;
                border: 1px solid #dadce0 !important;
                background-color: #ffffff !important;
                color: #3c4043 !important;
                font-family: 'Roboto', sans-serif !important;
                font-weight: 500 !important;
                font-size: 14px !important;
                padding: 8px 20px 8px 48px !important;
                background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 48 48"><path fill="%23EA4335" d="M24 9.5c3.54 0 6.7 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="%234285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="%23FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="%2334A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.46-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>') !important;
                background-repeat: no-repeat !important;
                background-position: 16px center !important;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                float: right;
            }
            div.stButton > button:hover {
                background-color: #f8f9fa !important;
                border-color: #dadce0 !important;
                box-shadow: 0 1px 3px rgba(60,64,67,0.2);
                color: #202124 !important;
            }
        </style>
    """, unsafe_allow_html=True)

# --- TOP HEADER & AUTHENTICATION BAR ---
header_col1, header_col2 = st.columns([0.6, 0.4])

with header_col1:
    st.title("🧪 APLens Beta - Plagiarism Suite")

with header_col2:
    if st.user.is_logged_in:
        # Authenticated State: Profile Avatar + Account Menu Popover
        avatar_col, menu_col = st.columns([0.3, 0.7])
        
        with avatar_col:
            st.markdown(f"""
                <div style="padding-top: 12px; text-align: right;">
                    <img src="{user_avatar}" style="width: 38px; height: 38px; border-radius: 50%; border: 2px solid #1a73e8; object-fit: cover;">
                </div>
            """, unsafe_allow_html=True)
            
        with menu_col:
            st.markdown("<div style='padding-top: 6px;'></div>", unsafe_allow_html=True)
            with st.popover("Account"):
                st.markdown(f"""
                    <div style="text-align: center; padding: 10px 0px;">
                        <img src="{user_avatar}" style="width: 60px; height: 60px; border-radius: 50%; border: 2px solid #1a73e8; object-fit: cover; margin-bottom: 6px;">
                        <div style="font-weight: 600; font-size: 14px; color: #202124;">{user_name}</div>
                        <div style="font-size: 12px; color: #5f6368; margin-top: 2px; word-break: break-all;">{user_email}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                if st.button("Sign Out", type="secondary", use_container_width=True):
                    st.logout()
    else:
        # Logged Out State: Direct button with Google logo built into CSS
        if st.button("Sign in with Google"):
            st.login("google")

st.markdown("---")

# --- MAIN PAGE CONTENT ---
if st.user.is_logged_in:
    st.success(f"Successfully logged in as: **{user_email}**")
    st.write(f"Welcome, {user_name}! Your Google session is active.")
    
    st.info("You have full access to the Beta suite features.")
else:
    st.warning("🔒 Please sign in using the top-right button to unlock the Beta suite.")
    st.write("Streamlit's native OIDC authentication handles Google login securely and seamlessly.")
