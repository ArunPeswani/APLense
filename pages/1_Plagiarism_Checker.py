# ==========================================
# MODE 1: PLAGIARISM CHECKER
# ==========================================
if app_mode == "Plagiarism Checker":
    st.header("File Similarity Matrix Analysis")
    st.write("Upload student submissions. If LMS Number and Assignment Name are provided, submissions will automatically be compared against historical submissions stored for that specific course and assignment.")

    col_lms1, col_lms2 = st.columns(2)
    with col_lms1:
        lms_number_input = st.text_input("🏫 LMS Number", placeholder="e.g., 48921", key=f"lms_num_{rc}")
    with col_lms2:
        assignment_name_input = st.text_input("📝 Assignment Name", placeholder="e.g., Assignment A", key=f"assign_name_{rc}")

    lms_val = lms_number_input.strip()
    assign_val = assignment_name_input.strip()
    is_cumulative = bool(lms_val and assign_val)

    global_reference_text = ""
    if reference_file:
        global_reference_text, _ = extract_text_and_images_from_file(reference_file, reference_file.name.lower())
        if is_cumulative:
            try:
                conn = get_valid_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("delete from course_metadata where lms_number = %s and assignment_name = %s", (lms_val, assign_val))
                    cursor.execute("""
                        insert into course_metadata (lms_number, assignment_name, reference_text, timestamp)
                        values (%s, %s, %s, %s)
                    """, (lms_val, assign_val, global_reference_text, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success("📌 Instructions file uploaded and saved to vault for future runs under this LMS and Assignment!")
            except Exception:
                pass
    elif is_cumulative:
        try:
            conn = get_valid_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("select reference_text from course_metadata where lms_number = %s and assignment_name = %s", (lms_val, assign_val))
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                if row and row[0]:
                    global_reference_text = row[0]
                    st.info(f"💡 Automatically loaded saved assignment instructions/syllabus from vault for LMS: **{lms_val}** | Assignment: **{assign_val}**")
        except Exception:
            pass

    try:
        conn = get_valid_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("select distinct lms_number, assignment_name from course_document_vault")
            past_records = cursor.fetchall()
            cursor.close()
            conn.close()
            if past_records:
                past_lms_list = sorted(list(set(r[0] for r in past_records if r[0])))
                if past_lms_list:
                    st.caption(f"💡 Previously used LMS Numbers in Vault: {', '.join(past_lms_list)}")
    except Exception:
        pass

    upload_choice = st.radio("Select Upload Type", ["Individual Files", "Direct Folder Selection", "ZIP Archive (.zip)"], key=f"folder_upload_choice_{rc}")

    raw_uploaded_files = []
    directory_uploaded_files = []
    zip_uploaded_file = None

    if upload_choice == "Individual Files":
        raw_uploaded_files = st.file_uploader(
            "Upload Student Submission Documents",
            type=list(supported_exts),
            accept_multiple_files=True,
            max_upload_size=5,
            key=f"folder_indiv_files_{rc}"
        )
    elif upload_choice == "Direct Folder Selection":
        directory_uploaded_files = st.file_uploader(
            "Select an entire folder containing student submissions",
            type=list(supported_exts),
            accept_multiple_files="directory",
            max_upload_size=5,
            key=f"folder_dir_files_{rc}"
        )
    else:
        zip_uploaded_file = st.file_uploader(
            "Upload ZIP Folder Archive containing student submissions",
            type=["zip"],
            max_upload_size=100,
            key=f"folder_zip_file_{rc}"
        )

    processed_files = []
    if upload_choice == "Individual Files" and raw_uploaded_files:
        processed_files = raw_uploaded_files
    elif upload_choice == "Direct Folder Selection" and directory_uploaded_files:
        for file_obj in directory_uploaded_files:
            if file_obj.name.lower().endswith(supported_exts) and '__MACOSX' not in file_obj.name:
                processed_files.append(file_obj)
    elif upload_choice == "ZIP Archive (.zip)" and zip_uploaded_file:
        try:
            with zipfile.ZipFile(zip_uploaded_file, 'r') as z:
                for filename in z.namelist():
                    if filename.lower().endswith(supported_exts) and not filename.startswith('__MACOSX/'):
                        with z.open(filename) as f:
                            file_bytes = io.BytesIO(f.read())
                            file_bytes.name = os.path.basename(filename)
                            if file_bytes.name:
                                processed_files.append(file_bytes)
        except Exception as e:
            st.error(f"Could not read ZIP archive: {e}")

    if processed_files:
        st.info(f"Loaded {len(processed_files)} file(s) successfully.")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            run_standard = st.button("Run Plagiarism Analysis", type="primary", key=f"run_folder_analysis_{rc}")
        with col_btn2:
            run_paraphrase = st.button("🔍 Run Paraphrase Analysis", type="secondary", key=f"run_folder_paraphrase_{rc}")

        if run_standard or run_paraphrase:
            analysis_mode_label = ("Cumulative Paraphrased Plagiarism Analysis" if is_cumulative else "Paraphrased Plagiarism Analysis") if run_paraphrase else ("Cumulative Standard Plagiarism Analysis" if is_cumulative else "Standard Plagiarism Analysis")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            status_text.text("Initializing analysis...")
            progress_bar.progress(10)
            
            historical_filenames = []
            historical_texts = []
            existing_filenames_set = set()
            
            if is_cumulative:
                status_text.text("Retrieving historical submissions from document vault...")
                try:
                    conn = get_valid_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("select filename, extracted_text from course_document_vault where lms_number = %s and assignment_name = %s", (lms_val, assign_val))
                        vault_rows = cursor.fetchall()
                        cursor.close()
                        conn.close()
                        for r in vault_rows:
                            f_name, f_text = r[0], r[1]
                            historical_filenames.append(f"📁 [Past] {f_name}")
                            historical_texts.append(f_text)
                            existing_filenames_set.add(f_name)
                except Exception:
                    pass

            documents = list(historical_texts)
            filenames = list(historical_filenames)
            
            status_text.text("Processing student submission files...")
            progress_bar.progress(30)
            
            new_files_to_vault = []
            total_to_process = len(processed_files)
            
            for idx, file in enumerate(processed_files):
                status_text.text(f"Extracting text from file {idx+1} of {total_to_process}: {file.name} (OCR active)")
                progress_bar.progress(30 + int(40 * (idx + 1) / total_to_process))
                
                txt, _ = extract_text_and_images_from_file(file, file.name.lower())
                
                if global_reference_text.strip():
                    prompt_words = set(global_reference_text.split())
                    cleaned_txt = " ".join([w for w in txt.split() if w not in prompt_words or len(prompt_words) < 5])
                    if len(cleaned_txt.strip()) > 3:
                        txt = cleaned_txt
                
                documents.append(txt)
                unique_name = f"🆕 [New] {file.name}" if is_cumulative else f"{idx+1}. {file.name}"
                filenames.append(unique_name)
                
                if is_cumulative and file.name not in existing_filenames_set:
                    new_files_to_vault.append((lms_val, assign_val, file.name, txt, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

            if len(documents) < 2:
                st.error("Total comparison pool has fewer than 2 documents. Please upload at least 2 files.")
            else:
                status_text.text("Calculating similarity matrix across documents...")
                progress_bar.progress(85)
                
                n = len(documents)
                similarity_matrix = [[0.0]*n for _ in range(n)]
                
                if run_paraphrase:
                    for i in range(n):
                        for j in range(n):
                            if i == j:
                                similarity_matrix[i][j] = 100.0
                            else:
                                s = difflib.SequenceMatcher(None, documents[i].lower(), documents[j].lower())
                                words1 = set(documents[i].lower().split())
                                words2 = set(documents[j].lower().split())
                                jaccard = len(words1.intersection(words2)) / max(len(words1.union(words2)), 1)
                                score = ((s.ratio() * 0.5) + (jaccard * 0.5)) * 100
                                similarity_matrix[i][j] = min(round(score * 1.4, 2), 100.0)
                else:
                    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(min_words, max_words), max_features=10000)
                    tfidf_matrix = vectorizer.fit_transform(documents)
                    similarity_matrix = (cosine_similarity(tfidf_matrix) * 100).tolist()
                
                if is_cumulative and new_files_to_vault:
                    try:
                        conn = get_valid_db_connection()
                        if conn:
                            cursor = conn.cursor()
                            cursor.executemany("""
                                insert into course_document_vault (lms_number, assignment_name, filename, extracted_text, timestamp)
                                values (%s, %s, %s, %s, %s)
                            """, new_files_to_vault)
                            conn.commit()
                            cursor.close()
                            conn.close()
                    except Exception:
                        pass

                progress_bar.progress(100)
                status_text.text("Analysis complete!")
                
                df = pd.DataFrame(similarity_matrix, index=filenames, columns=filenames)
                
                st.session_state.folder_df = df
                st.session_state.folder_similarity_matrix = similarity_matrix
                st.session_state.folder_filenames = filenames
                st.session_state.folder_analyzed = True
                st.session_state.analysis_type_run = analysis_mode_label
                st.session_state.beta_course = f"LMS: {lms_val} | Assignment: {assign_val}" if is_cumulative else (assign_val or "General Assignment")

                total_files = len(filenames)
                flat_scores = [similarity_matrix[i][j] for i in range(total_files) for j in range(total_files) if i != j]
                max_sim = max(flat_scores) if flat_scores else 0.0
                avg_sim = sum(flat_scores) / len(flat_scores) if flat_scores else 0.0
                flagged_pairs_count = sum(1 for score in flat_scores if score >= similarity_threshold)
                current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                try:
                    conn = get_valid_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            insert into beta_user_activity (
                                user_email, user_name, timestamp, course, analysis_type, 
                                files_scanned, min_ngram_words, max_ngram_words, 
                                flagging_threshold, max_similarity, avg_similarity, flagged_pairs_count
                            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            user_email, user_name, current_timestamp, st.session_state.beta_course, analysis_mode_label,
                            total_files, min_words, max_words, similarity_threshold,
                            round(max_sim, 2), round(avg_sim, 2), flagged_pairs_count
                        ))
                        conn.commit()
                        cursor.close()
                        conn.close()
                except Exception:
                    pass

                if save_reports_toggle:
                    st.session_state.saved_reports.append({
                        "timestamp": current_timestamp,
                        "type": analysis_mode_label,
                        "course": st.session_state.beta_course,
                        "files_count": len(filenames),
                        "df": df,
                        "expiry": expiry_date
                    })
                
                progress_bar.empty()
                status_text.empty()
                st.rerun()

    if st.session_state.get("folder_analyzed", False):
        df = st.session_state.folder_df
        similarity_matrix = st.session_state.folder_similarity_matrix
        filenames = st.session_state.folder_filenames
        run_label = st.session_state.get("analysis_type_run", "Analysis")
        current_course = st.session_state.get("beta_course", "Assignment")

        st.success(f"{run_label} Complete for **{current_course}**!")
        
        total_files = len(filenames)
        flat_scores = [similarity_matrix[i][j] for i in range(total_files) for j in range(total_files) if i != j]
        max_sim = max(flat_scores) if flat_scores else 0.0
        avg_sim = sum(flat_scores) / len(flat_scores) if flat_scores else 0.0
        flagged_pairs_count = sum(1 for score in flat_scores if score >= similarity_threshold)

        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        with mcol1:
            st.metric("📁 Total Pool Files", total_files)
        with mcol2:
            st.metric("📈 Max Similarity", f"{max_sim:.1f}%")
        with mcol3:
            st.metric("📊 Average Similarity", f"{avg_sim:.1f}%")
        with mcol4:
            st.metric("🚨 Flagged Pairs (≥{}%)".format(similarity_threshold), flagged_pairs_count)

        if flagged_pairs_count > 0:
            st.warning(f"⚠️ **Attention:** Found **{flagged_pairs_count} document pair(s)** meeting or exceeding the **{similarity_threshold}%** threshold limit.")
        else:
            st.info(f"✅ **All clear:** No document pairs exceed the **{similarity_threshold}%** threshold limit.")

        st.subheader(f"Visual Heatmap ({run_label})")
        truncated_names = [name if len(name) <= 25 else name[:22] + "..." for name in filenames]
        chart_dimension = max(900, total_files * 35)
        
        fig = go.Figure(data=go.Heatmap(
            z=similarity_matrix,
            x=truncated_names,
            y=truncated_names,
            customdata=filenames,
            hovertemplate="<b>Row:</b> %{y}<br><b>Col:</b> %{x}<br><b>Similarity:</b> %{z:.1f}%<extra></extra>",
            colorscale="Reds" if "Paraphrase" not in run_label else "Oranges",
            zmin=0,
            zmax=100
        ))
        fig.update_layout(width=chart_dimension, height=chart_dimension, margin=dict(l=180, r=50, t=50, b=180), xaxis=dict(tickangle=-45, type='category'), yaxis=dict(autorange='reversed', type='category'))
        st.plotly_chart(fig, use_container_width=False)

        st.subheader("Similarity Matrix Report (%)")
        st.dataframe(df.style.format("{:.2f}%"))
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Plagiarism Report')
        
        st.download_button(
            label="📥 Download Plagiarism Report (Excel)",
            data=output.getvalue(),
            file_name=f"plagiarism_report_{current_course.replace(' | ', '_').replace(': ', '_').replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_excel_report_{rc}"
        )
