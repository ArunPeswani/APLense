import streamlit as st

st.set_page_config(page_title="APLens Beta - Google Profile Avatar", page_icon="🧪", layout="centered")

# --- SAFE USER DATA EXTRACTION ---
user_email = getattr(st.user, "email", "User") if st.user.is_logged_in else ""
user_name = getattr(st.user, "name", "Google User") if st.user.is_logged_in else ""
user_avatar = (getattr(st.user, "picture", None) or getattr(st.user, "image", None)) if st.user.is_logged_in else ""

if not user_avatar:
    user_avatar = "https://www.w3schools.com/howto/img_avatar.png"

# --- REFINED CSS TO FORCE PROFILE IMAGE ON THE POPOVER BUTTON ---
if st.user.is_logged_in:
    st.markdown(f"""
        <style>
            /* Target the popover button and enforce the Google profile picture background */
            div[data-testid="stPopover"] > button {{
                background-image: url("{user_avatar}") !important;
                background-size: cover !important;
                background-position: center !important;
                border-radius: 50% !important;
                width: 42px !important;
                height: 42px !important;
                border: 2px solid #dadce0 !important;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                padding: 0px !important;
                text-indent: -9999px !important;
                overflow: hidden !important;
            }}
            div[data-testid="stPopover"] > button:hover {{
                border-color: #1a73e8 !important;
                box-shadow: 0 2px 5px rgba(0,0,0,0.15);
            }}
            /* Hide Streamlit's default arrow icon and text wrappers */
            div[data-testid="stPopover"] > button svg,
            div[data-testid="stPopover"] > button span,
            div[data-testid="stPopover"] > button p {{
                display: none !important;
            }}
        </style>
    """, unsafe_allow_html=True)

# --- TOP HEADER & PROFILE MENU BAR ---
header_col1, header_col2 = st.columns([0.7, 0.3])

with header_col1:
    st.title("🧪 APLens Beta - Plagiarism Suite")

with header_col2:
    if st.user.is_logged_in:
        # Clicking the circular profile picture popover reveals the account menu
        with st.popover(""):
            st.markdown(f"""
                <div style="text-align: center; padding: 12px 5px 8px 5px;">
                    <img src="{user_avatar}" style="width: 64px; height: 64px; border-radius: 50%; border: 2px solid #1a73e8; object-fit: cover; margin-bottom: 8px;">
                    <div style="font-weight: 600; font-size: 15px; color: #202124;">{user_name}</div>
                    <div style="font-size: 13px; color: #5f6368; margin-top: 2px; word-break: break-all;">{user_email}</div>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            if st.button("Sign Out", type="secondary", use_container_width=True):
                st.logout()
    else:
        with st.popover("🔐 Account Login"):
            st.markdown("### Native Authentication")
            st.caption("Authenticate instantly via Streamlit native Google login:")
            
            if st.button("Sign in with Google", type="primary", use_container_width=True):
                st.login("google")

st.markdown("---")

# --- MAIN PAGE CONTENT ---
if st.user.is_logged_in:
    st.success(f"Successfully logged in as: **{user_email}**")
    st.write(f"Welcome, {user_name}! Your Google session is active, and your profile menu is tucked away neatly in the top right.")
    
    st.info("You have full access to the Beta suite features.")
else:
    st.warning("🔒 Please sign in using the top-right button to unlock the Beta suite.")
    st.write("Streamlit's native OIDC authentication handles Google login securely and seamlessly.")
