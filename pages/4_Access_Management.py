import streamlit as st
import pandas as pd
import time
import datetime

from db_utils import get_valid_db_connection, get_cached_requests_and_users
from auth import enforce_admin_or_whitelisted_access

enforce_admin_or_whitelisted_access()

user_is_logged_in = getattr(st.user, "is_logged_in", False)
user_email = getattr(st.user, "email", "")
is_admin = user_email.lower() == "arunpeswani@gmail.com"

if not is_admin:
    st.error("Access Denied. Restricted to administrator.")
    st.stop()

if "reset_count_beta" not in st.session_state:
    st.session_state.reset_count_beta = 0
rc = st.session_state.reset_count_beta

st.header("🔐 Access Requests Management")
st.write("Review, approve, or manage user access requests and registered users for APLens Beta.")

df_requests, df_registered = get_cached_requests_and_users()
tab_pending, tab_registered = st.tabs(["⏳ Pending Requests", "👥 Registered Users"])

with tab_pending:
    if df_requests.empty:
        st.info("✅ No pending access requests at this time.")
    else:
        st.dataframe(df_requests, use_container_width=True)

with tab_registered:
    if df_registered.empty:
        st.info("No registered users found.")
    else:
        st.dataframe(df_registered, use_container_width=True)
