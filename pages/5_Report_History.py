import io
import streamlit as st
import pandas as pd
from db_utils import get_valid_db_connection
from auth import enforce_admin_or_whitelisted_access

enforce_admin_or_whitelisted_access()

user_is_logged_in = getattr(st.user, "is_logged_in", False)
user_email = getattr(st.user, "email", "")
is_admin = user_email.lower() == "arunpeswani@gmail.com"

if "reset_count_beta" not in st.session_state:
    st.session_state.reset_count_beta = 0
rc = st.session_state.reset_count_beta

st.header("📁 Saved Report History & Course Data Management")
# (Rest of Report History logic follows directly)
