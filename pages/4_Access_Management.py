from auth import enforce_admin_or_whitelisted_access # (or whatever function you named it in auth.py)
enforce_admin_or_whitelisted_access()

# ==========================================
# MODE 4: ACCESS REQUESTS MANAGEMENT (ADMIN ONLY)
# ==========================================
elif is_admin and app_mode == "🔐 Access Requests Management":
    st.header("🔐 Access Requests Management")
    st.write("Review, approve, or manage user access requests and registered users for APLens Beta.")

    df_requests, df_registered = get_cached_requests_and_users()
    tab_pending, tab_registered = st.tabs(["⏳ Pending Requests", "👥 Registered Users"])

    with tab_pending:
        col_h_btn1, col_h_btn2 = st.columns([0.25, 0.75])
        with col_h_btn1:
            if st.button("🔄 Refresh Requests", type="secondary", use_container_width=True, key=f"refresh_reqs_{rc}"):
                get_cached_requests_and_users.clear()
                st.rerun()

        if df_requests.empty:
            st.info("✅ No pending access requests at this time.")
        else:
            st.write(f"Found **{len(df_requests)} pending request(s)**.")

            def pending_toggle_callback():
                st.session_state.pending_master_select = st.session_state[f"pending_master_toggle_{rc}"]

            st.checkbox(
                "Select / Unselect All", 
                value=st.session_state.get("pending_master_select", False), 
                key=f"pending_master_toggle_{rc}",
                on_change=pending_toggle_callback
            )

            editor_rows = []
            for idx, row in df_requests.iterrows():
                editor_rows.append({
                    "Select": st.session_state.get("pending_master_select", False),
                    "id": row["id"],
                    "Name": row["name"],
                    "Email ID": row["email"],
                    "Remarks": row["remarks"],
                    "Timestamp": row["timestamp"]
                })
            df_editor_input = pd.DataFrame(editor_rows)

            edited_pending_df = st.data_editor(
                df_editor_input,
                column_config={
                    "Select": st.column_config.CheckboxColumn("Select", default=False),
                    "id": None,
                },
                disabled=["Name", "Email ID", "Remarks", "Timestamp"],
                hide_index=True,
                use_container_width=True,
                key=f"pending_editor_{rc}"
            )

            col_act1, col_act2, col_act3, _ = st.columns([1, 1, 1, 1])
            with col_act1:
                approve_selected = st.button("Approve Selected", type="primary", use_container_width=True, key=f"approve_sel_{rc}")
            with col_act2:
                approve_all = st.button("Approve All", type="secondary", use_container_width=True, key=f"approve_all_{rc}")
            with col_act3:
                delete_selected = st.button("Delete Selected", type="secondary", use_container_width=True, key=f"delete_sel_{rc}")

            if approve_selected or approve_all or delete_selected:
                target_requests = []
                for idx, row in edited_pending_df.iterrows():
                    if approve_all or row["Select"]:
                        target_requests.append((row["Email ID"], row["Name"], row["Timestamp"], row["id"]))

                if not target_requests:
                    st.warning("No pending requests selected.")
                else:
                    try:
                        conn = get_valid_db_connection()
                        if conn:
                            cursor = conn.cursor()
                            if delete_selected:
                                for email, name, req_ts, req_id in target_requests:
                                    cursor.execute("delete from access_requests where id = %s", (req_id,))
                                conn.commit()
                                cursor.close()
                                conn.close()
                                st.success(f"Successfully deleted {len(target_requests)} pending request(s)!")
                            else:
                                for email, name, req_ts, req_id in target_requests:
                                    cursor.execute("insert into authorized_users (email, name, requested_at, approved_at) values (%s, %s, %s, %s) on conflict (email) do nothing", 
                                                   (email.lower(), name, req_ts, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                    cursor.execute("delete from access_requests where id = %s", (req_id,))
                                conn.commit()
                                cursor.close()
                                conn.close()
                                st.success(f"Successfully approved {len(target_requests)} user(s)!")
                            
                            get_cached_requests_and_users.clear()
                            time.sleep(1.5)
                            st.rerun()
                    except Exception as ex:
                        st.error(f"Error processing requests: {ex}")

    with tab_registered:
        st.subheader("👥 Approved & Registered Users")
        
        col_reg_btn1, _ = st.columns([0.25, 0.75])
        with col_reg_btn1:
            if st.button("🔄 Refresh Registered Users", type="secondary", use_container_width=True, key=f"refresh_regs_{rc}"):
                get_cached_requests_and_users.clear()
                st.rerun()

        if df_registered.empty:
            st.info("No registered users found.")
        else:
            st.write(f"Found **{len(df_registered)} registered user(s)**.")

            def reg_toggle_callback():
                st.session_state.reg_master_select = st.session_state[f"reg_master_toggle_{rc}"]

            st.checkbox(
                "Select / Unselect All", 
                value=st.session_state.get("reg_master_select", False), 
                key=f"reg_master_toggle_{rc}",
                on_change=reg_toggle_callback
            )

            reg_editor_rows = []
            for idx, row in df_registered.iterrows():
                is_admin_user = row["email"].lower() == "arunpeswani@gmail.com"
                sel_val = False if is_admin_user else st.session_state.get("reg_master_select", False)
                reg_editor_rows.append({
                    "Select": sel_val,
                    "Name": row["name"] or "N/A",
                    "Email ID": row["email"],
                    "Request Timestamp": row["requested_at"] or "N/A",
                    "Approval Timestamp": row["approved_at"] or "N/A"
                })
            df_reg_input = pd.DataFrame(reg_editor_rows)

            edited_reg_df = st.data_editor(
                df_reg_input,
                column_config={
                    "Select": st.column_config.CheckboxColumn("Select", default=False),
                },
                disabled=["Name", "Email ID", "Request Timestamp", "Approval Timestamp"],
                hide_index=True,
                use_container_width=True,
                key=f"registered_editor_{rc}"
            )

            col_unreg1, _ = st.columns([1, 2])
            with col_unreg1:
                unregister_selected = st.button("Unregister Selected Users", type="primary", use_container_width=True, key=f"unreg_sel_{rc}")

            if unregister_selected:
                users_to_unregister = []
                for idx, row in edited_reg_df.iterrows():
                    if row["Email ID"].lower() == "arunpeswani@gmail.com":
                        continue
                    if row["Select"]:
                        users_to_unregister.append((row["Email ID"], row["Name"], row["Request Timestamp"]))

                if not users_to_unregister:
                    st.warning("No valid users selected for unregistering.")
                else:
                    try:
                        conn = get_valid_db_connection()
                        if conn:
                            cursor = conn.cursor()
                            for email, name, req_ts in users_to_unregister:
                                cursor.execute("delete from authorized_users where email = %s", (email.lower(),))
                                cursor.execute("""
                                    insert into access_requests (name, email, remarks, timestamp)
                                    values (%s, %s, %s, %s)
                                    on conflict (email) do nothing
                                """, (name, email.lower(), "Unregistered by admin. Re-request required.", req_ts))
                            conn.commit()
                            cursor.close()
                            conn.close()
                            
                            get_cached_requests_and_users.clear()
                            st.success(f"Successfully unregistered {len(users_to_unregister)} user(s) and moved them back to Pending Requests!")
                            time.sleep(1.5)
                            st.rerun()
                    except Exception as ex:
                        st.error(f"Error unregistering users: {ex}")
