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

st.subheader("🗑️ Manual Course / Assignment Data Purge")
col_purge1, col_purge2, col_purge3 = st.columns([1, 1, 1])
with col_purge1: purge_lms = st.text_input("LMS Number to Purge", key=f"purge_lms_{rc}")
with col_purge2: purge_assign = st.text_input("Assignment Name to Purge", key=f"purge_assign_{rc}")
with col_purge3:
    st.markdown("<div style='padding-top: 24px;'></div>", unsafe_allow_html=True)
    if st.button("🗑️ Purge Records", type="secondary", key=f"purge_btn_{rc}"):
        if purge_lms.strip() and purge_assign.strip():
            try:
                conn = get_valid_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("delete from course_document_vault where lms_number = %s and assignment_name = %s", (purge_lms.strip(), purge_assign.strip()))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success("Successfully purged records!")
            except Exception as ex:
                st.error(f"Error: {ex}")
        else:
            st.warning("Provide both LMS Number and Assignment Name.")
