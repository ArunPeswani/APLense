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
    st.error("Access Denied. Please contact Arun Peswani for access approvals.")
    st.stop()

if "reset_count_beta" not in st.session_state:
    st.session_state.reset_count_beta = 0
rc = st.session_state.reset_count_beta

st.header("🔐 Access Requests Management")
st.write("Review, approve, or manage user access requests and registered users for APLens Beta.")

df_requests, df_registered = get_cached_requests_and_users()
tab_pending, tab_registered = st.tabs(["⏳ Pending Requests", "👥 Registered Users"])

with tab_pending:
    if st.button("🔄 Refresh Requests", type="secondary", key=f"refresh_reqs_{rc}"):
        get_cached_requests_and_users.clear()
        st.rerun()

    if df_requests.empty:
        st.info("✅ No pending access requests at this time.")
    else:
        editor_rows = [{"Select": False, "id": row["id"], "Name": row["name"], "Email ID": row["email"], "Remarks": row["remarks"], "Timestamp": row["timestamp"]} for idx, row in df_requests.iterrows()]
        edited_pending_df = st.data_editor(pd.DataFrame(editor_rows), column_config={"Select": st.column_config.CheckboxColumn("Select", default=False), "id": None}, disabled=["Name", "Email ID", "Remarks", "Timestamp"], hide_index=True, use_container_width=True, key=f"pending_editor_{rc}")

        col_act1, col_act2, _ = st.columns([1, 1, 2])
        with col_act1: approve_selected = st.button("Approve Selected", type="primary", use_container_width=True, key=f"approve_sel_{rc}")
        with col_act2: delete_selected = st.button("Delete Selected", type="secondary", use_container_width=True, key=f"delete_sel_{rc}")

        if approve_selected or delete_selected:
            target_requests = [(row["Email ID"], row["Name"], row["Timestamp"], row["id"]) for idx, row in edited_pending_df.iterrows() if row["Select"]]
            if target_requests:
                try:
                    conn = get_valid_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        for email, name, req_ts, req_id in target_requests:
                            if delete_selected:
                                cursor.execute("delete from access_requests where id = %s", (req_id,))
                            else:
                                cursor.execute("insert into authorized_users (email, name, requested_at, approved_at) values (%s, %s, %s, %s) on conflict (email) do nothing", (email.lower(), name, req_ts, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                cursor.execute("delete from access_requests where id = %s", (req_id,))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        get_cached_requests_and_users.clear()
                        st.success("Action processed successfully!")
                        time.sleep(1)
                        st.rerun()
                except Exception as ex:
                    st.error(f"Error: {ex}")

with tab_registered:
    if st.button("🔄 Refresh Registered Users", type="secondary", key=f"refresh_regs_{rc}"):
        get_cached_requests_and_users.clear()
        st.rerun()

    if df_registered.empty:
        st.info("No registered users found.")
    else:
        reg_editor_rows = [{"Select": False, "Name": row["name"] or "N/A", "Email ID": row["email"], "Request Timestamp": row["requested_at"] or "N/A", "Approval Timestamp": row["approved_at"] or "N/A"} for idx, row in df_registered.iterrows()]
        edited_reg_df = st.data_editor(pd.DataFrame(reg_editor_rows), column_config={"Select": st.column_config.CheckboxColumn("Select", default=False)}, disabled=["Name", "Email ID", "Request Timestamp", "Approval Timestamp"], hide_index=True, use_container_width=True, key=f"registered_editor_{rc}")
        
        if st.button("Unregister Selected Users", type="primary", key=f"unreg_sel_{rc}"):
            users_to_unregister = [(row["Email ID"], row["Name"], row["Request Timestamp"]) for idx, row in edited_reg_df.iterrows() if row["Email ID"].lower() != "arunpeswani@gmail.com" and row["Select"]]
            if users_to_unregister:
                try:
                    conn = get_valid_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        for email, name, req_ts in users_to_unregister:
                            cursor.execute("delete from authorized_users where email = %s", (email.lower(),))
                            cursor.execute("insert into access_requests (name, email, remarks, timestamp) values (%s, %s, %s, %s) on conflict (email) do nothing", (name, email.lower(), "Unregistered by admin.", req_ts))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        get_cached_requests_and_users.clear()
                        st.success("Successfully unregistered selected users!")
                        time.sleep(1)
                        st.rerun()
                except Exception as ex:
                    st.error(f"Error: {ex}")
