import streamlit as st

st.set_page_config(page_title="APLens Beta - Google Sign-In", page_icon="🧪", layout="centered")

# --- SAFE USER DATA EXTRACTION ---
user_email = getattr(st.user, "email", "User") if st.user.is_logged_in else ""
user_name = getattr(st.user, "name", "Google User") if st.user.is_logged_in else ""
user_avatar = (getattr(st.user, "picture", None) or getattr(st.user, "image", None)) if st.user.is_logged_in else ""

if not user_avatar:
    user_avatar = "https://www.w3schools.com/howto/img_avatar.png"

# --- CUSTOM CSS FOR DIRECT PILL BUTTON ---
if not st.user.is_logged_in:
    st.markdown("""
        <style>
            /* Style Streamlit's direct button into a clean pill-shaped button */
            div.stButton > button {
                border-radius: 24px !important;
                border: 1px solid #dadce0 !important;
                background-color: #ffffff !important;
                color: #3c4043 !important;
                font-family: 'Roboto', sans-serif !important;
                font-weight: 500 !important;
                font-size: 14px !important;
                padding: 6px 20px !important;
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
        # Logged Out State: Direct Button that instantly triggers Google Login with no dropdown
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
