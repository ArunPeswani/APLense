from auth import enforce_admin_or_whitelisted_access # (or whatever function you named it in auth.py)
enforce_admin_or_whitelisted_access()

# ==========================================
# MODE 5: REPORT HISTORY DASHBOARD & ADMIN AUDIT TRAIL
# ==========================================
elif app_mode == "📁 Report History Dashboard":
    st.header("📁 Saved Report History & Course Data Management")
    
    st.subheader("🗑️ Manual Course / Assignment Data Purge")
    st.write("Select or type an LMS Number and Assignment Name to completely clear its stored document vault, instructions, and AI grades.")
    
    col_purge1, col_purge2, col_purge3 = st.columns([1, 1, 1])
    with col_purge1:
        purge_lms = st.text_input("LMS Number to Purge", placeholder="e.g., 48921", key=f"purge_lms_{rc}")
    with col_purge2:
        purge_assign = st.text_input("Assignment Name to Purge", placeholder="e.g., Assignment A", key=f"purge_assign_{rc}")
    with col_purge3:
        st.markdown("<div style='padding-top: 24px;'></div>", unsafe_allow_html=True)
        if st.button("🗑️ Purge Course Records", type="secondary", key=f"purge_btn_{rc}"):
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
                        st.success(f"Successfully purged all vaults and reports for LMS: {purge_lms} | Assignment: {purge_assign}")
                except Exception as ex:
                    st.error(f"Error purging records: {ex}")
            else:
                st.warning("Please provide both LMS Number and Assignment Name to purge.")

    st.markdown("---")

    if is_admin:
        col_h1, col_h2 = st.columns([0.8, 0.2])
        with col_h2:
            if st.button("Fetch Reports", type="secondary", key=f"fetch_reports_btn_{rc}"):
                st.rerun()
                
        tab_my_reports, tab_audit_log, tab_deep_log = st.tabs(["My Saved Reports", "📊 User Activity & Settings Log", "🔍 Deep Dive (>50%) Log"])
    else:
        tab_my_reports, = st.tabs(["My Saved Reports"])
    
    with tab_my_reports:
        if not st.session_state.saved_reports:
            st.info("No reports saved yet. Run a Plagiarism Analysis with 'Save Generated Reports' enabled to populate your history.")
        else:
            col_dash1, col_dash2 = st.columns([0.8, 0.2])
            with col_dash2:
                if st.button("🗑️ Clear All Local Session History", type="secondary", key=f"clear_hist_btn_{rc}"):
                    st.session_state.saved_reports = []
                    st.rerun()

            for idx, rep in enumerate(reversed(st.session_state.saved_reports)):
                with st.expander(f"📌 [{rep['timestamp']}] {rep['course']} — {rep['type']} ({rep['files_count']} files, Expires: {rep['expiry']})"):
                    st.write(f"**Course/Assignment:** {rep['course']}")
                    st.write(f"**Analysis Mode:** {rep['type']}")
                    st.write(f"**Files Processed:** {rep['files_count']}")
                    st.write(f"**Scheduled Expiry:** {rep['expiry']}")
                    
                    st.dataframe(rep['df'].style.format("{:.2f}%"))
                    
                    h_output = io.BytesIO()
                    with pd.ExcelWriter(h_output, engine='openpyxl') as writer:
                        rep['df'].to_excel(writer, sheet_name='Report History')
                    
                    st.download_button(
                        label=f"📥 Download Report ({rep['timestamp']})",
                        data=h_output.getvalue(),
                        file_name=f"history_report_{rep['course'].replace(' | ', '_').replace(': ', '_').replace(' ', '_')}_{idx}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"hist_dl_{idx}_{rc}"
                    )
    
    if is_admin:
        with tab_audit_log:
            st.subheader("Plagiarism Checker Activity & Settings Audit Trail")
            try:
                conn = get_valid_db_connection()
                if conn:
                    df_logs = pd.read_sql_query("select * from beta_user_activity order by timestamp desc", conn)
                    conn.close()
                else:
                    df_logs = pd.DataFrame()
                
                if not df_logs.empty:
                    st.dataframe(df_logs, use_container_width=True)
                    csv_data = df_logs.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Plagiarism Activity Log (CSV)",
                        data=csv_data,
                        file_name="beta_user_activity_audit_trail.csv",
                        mime="text/csv",
                        key=f"dl_audit_csv_{rc}"
                    )
                else:
                    st.info("No user activity logs recorded yet.")
            except Exception as ex:
                st.warning(f"Could not load logs: {ex}")

        with tab_deep_log:
            st.subheader("Deep Dive Matcher (>50% Instances) Log")
            try:
                conn = get_valid_db_connection()
                if conn:
                    df_deep = pd.read_sql_query("select * from beta_deep_dive_activity order by timestamp desc", conn)
                    conn.close()
                else:
                    df_deep = pd.DataFrame()
                
                if not df_deep.empty:
                    st.dataframe(df_deep, use_container_width=True)
                    csv_deep = df_deep.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Deep Dive Activity Log (CSV)",
                        data=csv_deep,
                        file_name="beta_deep_dive_activity_log.csv",
                        mime="text/csv",
                        key=f"dl_deep_csv_{rc}"
                    )
                else:
                    st.info("No deep dive logs recorded yet.")
            except Exception as ex:
                st.warning(f"Could not load deep dive logs: {ex}")
