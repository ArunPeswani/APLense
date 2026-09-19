import io
import streamlit as st
import pandas as pd

from db_utils import get_valid_db_connection
from auth import enforce_admin_or_whitelisted_access, render_page_header

# 1. Enforce security gate
enforce_admin_or_whitelisted_access()

# 2. Render the top header with profile picture and logout dropdown in one clean line
render_page_header("Deep Dive Matcher")

# --- RESTRICT TO ADMIN ONLY ---
user_email = getattr(st.user, "email", "")
if user_email.lower() != "arunpeswani@gmail.com":
    st.error("Access Denied. The Report History dashboard is currently restricted to the administrator.")
    st.stop()

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
                    cursor.execute("delete from course_metadata where lms_number = %s and assignment_name = %s", (purge_lms.strip(), purge_assign.strip()))
                    cursor.execute("delete from ai_grades_vault where lms_number = %s and assignment_name = %s", (purge_lms.strip(), purge_assign.strip()))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success("Successfully purged records!")
            except Exception as ex:
                st.error(f"Error: {ex}")
        else:
            st.warning("Provide both LMS Number and Assignment Name.")

st.markdown("---")
if is_admin:
    tab_my_reports, tab_audit_log, tab_deep_log = st.tabs(["My Saved Reports", "📊 User Activity & Settings Log", "🔍 Deep Dive Log"])
else:
    tab_my_reports, = st.tabs(["My Saved Reports"])

with tab_my_reports:
    saved_reports = st.session_state.get("saved_reports", [])
    if not saved_reports:
        st.info("No reports saved yet in this session.")
    else:
        for idx, rep in enumerate(reversed(saved_reports)):
            with st.expander(f"📌 [{rep['timestamp']}] {rep['course']} — {rep['type']} ({rep['files_count']} files)"):
                st.dataframe(rep['df'].style.format("{:.2f}%"))
                h_output = io.BytesIO()
                with pd.ExcelWriter(h_output, engine='openpyxl') as writer:
                    rep['df'].to_excel(writer, sheet_name='Report')
                st.download_button("📥 Download Report", data=h_output.getvalue(), file_name=f"report_{idx}.xlsx", key=f"hist_dl_{idx}_{rc}")

if is_admin:
    with tab_audit_log:
        st.subheader("Plagiarism Checker Activity Audit Trail")
        try:
            conn = get_valid_db_connection()
            if conn:
                df_logs = pd.read_sql_query("select * from beta_user_activity order by timestamp desc", conn)
                conn.close()
                st.dataframe(df_logs, use_container_width=True)
            else:
                st.info("No logs found.")
        except Exception as e:
            st.warning(f"Could not load logs: {e}")

    with tab_deep_log:
        st.subheader("Deep Dive Matcher Log")
        try:
            conn = get_valid_db_connection()
            if conn:
                df_deep = pd.read_sql_query("select * from beta_deep_dive_activity order by timestamp desc", conn)
                conn.close()
                st.dataframe(df_deep, use_container_width=True)
            else:
                st.info("No logs found.")
        except Exception as e:
            st.warning(f"Could not load logs: {e}")
