import streamlit as st

st.set_page_config(page_title="APLens Beta - Native Google Auth", page_icon="🧪", layout="centered")

st.title("🧪 APLens Beta - Native Google Authentication Test")
st.markdown("---")

# Check native Streamlit user session state
if not st.user.is_logged_in:
    st.info("Please sign in using Streamlit's native Google authentication.")
    if st.button("Sign in with Google", type="primary"):
        st.login("google")
else:
    # Successfully logged in natively via Google
    st.success(f"Successfully logged in as: **{st.user.email}**")
    st.write(f"Welcome, {st.user.name}!")
    
    if st.button("Sign Out", type="secondary"):
        st.logout()
