import streamlit as st

st.set_page_config(page_title="APLens Beta - Google Avatar Auth", page_icon="🧪", layout="centered")

# --- CUSTOM CSS FOR ROUND AVATAR POPOVER ---
st.markdown("""
    <style>
        /* Style the popover button to look like a clean profile container */
        [data-testid="stPopover"] > button {
            border-radius: 50% !important;
            width: 42px !important;
            height: 42px !important;
            padding: 0px !important;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid #dadce0;
            background-color: #f8f9fa;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            float: right;
        }
        [data-testid="stPopover"] > button:hover {
            border-color: #1a73e8;
            box-shadow: 0 2px 5px rgba(0,0,0,0.15);
        }
    </style>
""", unsafe_allow_html=True)

# --- TOP HEADER & GOOGLE-STYLE AVATAR BAR ---
header_col1, header_col2 = st.columns([0.7, 0.3])

with header_col1:
    st.title("🧪 APLens Beta - Plagiarism Suite")

with header_col2:
    if st.user.is_logged_in:
        # Extract user profile image and email safely from native session
        user_email = getattr(st.user, "email", "User")
        user_name = getattr(st.user, "name", "Google User")
        
        # Google OIDC profile image attribute can be 'picture' or 'image'
        user_avatar = getattr(st.user, "picture", None) or getattr(st.user, "image", None)
        
        # Fallback to a clean default user icon if avatar URL isn't present
        if not user_avatar:
            user_avatar = "https://www.w3schools.com/howto/img_avatar.png"

        # Render a Google-style Account Menu Popover
        with st.popover(""):
            # Custom HTML to display avatar and email inside the dropdown card
            st.markdown(f"""
                <div style="text-align: center; padding: 10px 0px;">
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
    st.success(f"Successfully logged in as: **{st.user.email}**")
    st.write(f"Welcome, {getattr(st.user, 'name', 'User')}! Your Google profile image and native authentication session are active.")
    
    st.info("You have full access to the Beta suite features.")
else:
    st.warning("🔒 Please sign in using the top-right profile button to unlock the Beta suite.")
    st.write("Streamlit's native OIDC authentication handles Google login securely and seamlessly.")
