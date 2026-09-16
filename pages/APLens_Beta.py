import streamlit as st

st.set_page_config(page_title="APLens Beta - Profile Menu", page_icon="🧪", layout="centered")

# --- SAFE USER DATA EXTRACTION ---
user_email = getattr(st.user, "email", "User") if st.user.is_logged_in else ""
user_name = getattr(st.user, "name", "Google User") if st.user.is_logged_in else ""
user_avatar = (getattr(st.user, "picture", None) or getattr(st.user, "image", None)) if st.user.is_logged_in else ""

if not user_avatar:
    user_avatar = "https://www.w3schools.com/howto/img_avatar.png"

# --- CUSTOM CSS TO TURN THE EMPTY POPOVER BUTTON INTO YOUR PROFILE PHOTO ---
if st.user.is_logged_in:
    st.markdown(f"""
        <style>
            /* Style the empty popover button into a clean circular profile picture */
            div[data-testid="stPopover"] > button {{
                background-image: url("{user_avatar}") !important;
                background-size: cover !important;
                background-position: center !important;
                border-radius: 50% !important;
                width: 44px !important;
                height: 44px !important;
                border: 2px solid #dadce0 !important;
                padding: 0px !important;
                float: right;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            div[data-testid="stPopover"] > button:hover {{
                border-color: #1a73e8 !important;
                box-shadow: 0 2px 5px rgba(0,0,0,0.15);
            }}
            /* Hide the default dropdown chevron arrow inside the button */
            div[data-testid="stPopover"] > button svg {{
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
        # An empty string popover creates a clean button that we style into the profile avatar
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
    st.write(f"Welcome, {user_name}! Your Google session is active.")
    
    st.info("You have full access to the Beta suite features.")
else:
    st.warning("🔒 Please sign in using the top-right profile button to unlock the Beta suite.")
    st.write("Streamlit's native OIDC authentication handles Google login securely and seamlessly.")
