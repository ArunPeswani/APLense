# auth.py
import streamlit as st
from db_utils import get_valid_db_connection

def enforce_admin_or_whitelisted_access():
    user_is_logged_in = getattr(st.user, "is_logged_in", False)
    user_email = getattr(st.user, "email", "")
    if not user_is_logged_in:
        st.error("Please sign in.")
        st.stop()
    if user_email.lower() != "arunpeswani@gmail.com":
        # check database whitelist for beta/restricted pages
        ...
