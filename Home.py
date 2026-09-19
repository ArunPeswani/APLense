import streamlit as st
from db_utils import get_valid_db_connection, get_cached_requests_and_users
from auth import enforce_admin_or_whitelisted_access

st.set_page_config(page_title="APLens Beta Suite", page_icon="🧪", layout="centered")

# Enforce security gate on every page load
enforce_admin_or_whitelisted_access()

st.title("🧪 Welcome to APLens Beta Suite")
st.write("Select a tool from the sidebar navigation above to get started instantly without lag.")
