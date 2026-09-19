import datetime
import time
import streamlit as st
import pandas as pd
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
# (Rest of Access Management logic follows directly)
