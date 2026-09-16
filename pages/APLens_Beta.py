import streamlit as st

st.set_page_config(page_title="APLens Beta - Native Google Auth", page_icon="🧪", layout="centered")

# --- TOP HEADER & NATIVE AUTH BAR ---
header_col1, header_col2 = st.columns([0.7, 0.3])

with header_col1:
    st.title("🧪 APLens Beta - Plagiarism Suite")

with header_col2:
    # Check if the user is authenticated natively via Streamlit
    if st.user.is_logged_in:
        st.markdown(f"<div style='text-align: right; padding-top: 15px;'>👤 <b>{st.user.email}</b></div>", unsafe_allow_html=True)
        if st.button("Sign Out", type="secondary"):
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
    st.write(f"Welcome, {getattr(st.user, 'name', 'User')}! Your native Google authentication session is active.")
    
    # Placeholder for your beta tools or assignment checks
    st.info("You have full access to the Beta suite features.")
else:
    st.warning("🔒 Please sign in using the top-right **Account Login** button to unlock the Beta suite.")
    st.write("Streamlit's native OIDC authentication handles Google login securely and seamlessly without third-party callback routing errors.")
