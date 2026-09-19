from db_utils import get_valid_db_connection
from auth import enforce_admin_or_whitelisted_access # (or whatever function you named it in auth.py)
enforce_admin_or_whitelisted_access()

# ==========================================
# MODE 3: AI GRADER & RUBRIC EVALUATION
# ==========================================
elif app_mode == "🤖 AI Grader & Rubric Evaluation":
    st.header("🤖 AI Grader & Rubric Evaluation Suite")
    st.write("Upload assignment instructions, a grading rubric, and student submission files. Gemini will evaluate each student holistically with robust rate-limiting safeguards, run an integrated similarity check if enabled, and generate question scores and Exemplary Badges.")

    if not user_gemini_key.strip():
        st.warning("⚠️ Please enter your Google AI Studio API Key in the sidebar under **🔑 AI Grader API Key (BYOK)** to use the AI Grader.")
    else:
        col_ai_lms1, col_ai_lms2 = st.columns(2)
        with col_ai_lms1:
            ai_lms_input = st.text_input("🏫 LMS Number", placeholder="e.g., 48921", key=f"ai_lms_{rc}")
        with col_ai_lms2:
            ai_assign_input = st.text_input("📝 Assignment Name", placeholder="e.g., Assignment A", key=f"ai_assign_{rc}")

        ai_lms_val = ai_lms_input.strip()
        ai_assign_val = ai_assign_input.strip()
        ai_is_cumulative = bool(ai_lms_val and ai_assign_val)

        ai_col1, ai_col2 = st.columns(2)
        with ai_col1:
            rubric_file = st.file_uploader("Upload Grading Rubric (.docx, .pdf, images)", type=list(supported_exts), key=f"ai_rubric_{rc}", max_upload_size=5)
        with ai_col2:
            instructions_file = st.file_uploader("Upload Assignment Instructions (.docx, .pdf, images)", type=list(supported_exts), key=f"ai_instructions_{rc}", max_upload_size=5)

        st.markdown("---")
        exemplary_badge_pct = st.slider("🏆 Exemplary Badge Allocation Top %", min_value=0, max_value=50, value=15, step=5, help="Percentage of top-performing students to be awarded Exemplary Badges.")
        run_plagiarism_with_ai = st.checkbox("🔍 Also Run Integrated Plagiarism Check on Submissions", value=True, help="Automatically calculates cross-submission text similarity and adds max similarity scores to the grading sheet.")

        st.markdown("---")
        ai_upload_choice = st.radio("Student Submissions Upload Type", ["Individual Files / Student ZIP Archives (.zip)", "Direct Folder Selection"], key=f"ai_up_choice_{rc}")

        def parse_student_name_from_path(filename):
            clean_name = filename.replace('\\', '/')
            parts = clean_name.split('/')
            if len(parts) > 1:
                return parts[0]
            base = os.path.basename(clean_name)
            base_no_ext = os.path.splitext(base)[0]
            for sep in ['_', '-', ' ']:
                if sep in base_no_ext:
                    chunks = base_no_ext.split(sep)
                    if re.match(r'^(q\d+|ans\d+|assignment|part)', chunks[-1], re.IGNORECASE):
                        return sep.join(chunks[:-1])
            return base_no_ext

        student_files_map = {}

        if ai_upload_choice == "Individual Files / Student ZIP Archives (.zip)":
            ai_files = st.file_uploader("Upload Student Submission Files or Batch ZIP", type=list(supported_exts) + ["zip"], accept_multiple_files=True, max_upload_size=100, key=f"ai_files_{rc}")
            if ai_files:
                for f in ai_files:
                    if f.name.lower().endswith('.zip'):
                        try:
                            with zipfile.ZipFile(f, 'r') as z:
                                for zname in z.namelist():
                                    if zname.lower().endswith(supported_exts) and not zname.startswith('__MACOSX/'):
                                        with z.open(zname) as zf:
                                            b = io.BytesIO(zf.read())
                                            b.name = zname
                                            s_name = parse_student_name_from_path(zname)
                                            if s_name not in student_files_map:
                                                student_files_map[s_name] = []
                                            student_files_map[s_name].append(b)
                        except Exception as ex:
                            st.error(f"Error reading ZIP: {ex}")
                    else:
                        s_name = parse_student_name_from_path(f.name)
                        if s_name not in student_files_map:
                            student_files_map[s_name] = []
                        student_files_map[s_name].append(f)
        else:
            ai_dir_files = st.file_uploader("Select folder of student submissions", type=list(supported_exts), accept_multiple_files="directory", max_upload_size=5, key=f"ai_dir_{rc}")
            if ai_dir_files:
                for f in ai_dir_files:
                    if '__MACOSX' not in f.name:
                        s_name = parse_student_name_from_path(f.name)
                        if s_name not in student_files_map:
                            student_files_map[s_name] = []
                        student_files_map[s_name].append(f)

        if student_files_map and rubric_file and instructions_file:
            st.info(f"Grouped into {len(student_files_map)} unique student submission profiles ready for evaluation.")
            
            if st.button("🚀 Run AI Rubric Evaluation & Integrated Plagiarism Check", type="primary", key=f"run_ai_grading_{rc}"):
                try:
                    genai.configure(api_key=user_gemini_key.strip())
                    model = genai.GenerativeModel("gemini-3.5-flash")

                    rubric_text, rubric_imgs = extract_text_and_images_from_file(rubric_file, rubric_file.name.lower())
                    inst_text, inst_imgs = extract_text_and_images_from_file(instructions_file, instructions_file.name.lower())

                    similarity_scores_map = {}
                    if run_plagiarism_with_ai and len(student_files_map) >= 2:
                        all_student_texts = []
                        all_student_names = list(student_files_map.keys())
                        for s_name in all_student_names:
                            blob = ""
                            for sf in student_files_map[s_name]:
                                t_content, _ = extract_text_and_images_from_file(sf, sf.name.lower())
                                blob += t_content + " "
                            all_student_texts.append(blob)
                        
                        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(min_words, max_words), max_features=10000)
                        tfidf_mat = vectorizer.fit_transform(all_student_texts)
                        sim_mat = cosine_similarity(tfidf_mat) * 100
                        
                        for idx, s_name in enumerate(all_student_names):
                            peer_scores = [sim_mat[idx][j] for j in range(len(all_student_names)) if idx != j]
                            similarity_scores_map[s_name] = round(max(peer_scores), 1) if peer_scores else 0.0

                    historical_grades = []
                    if ai_is_cumulative:
                        try:
                            conn = get_valid_db_connection()
                            if conn:
                                cursor = conn.cursor()
                                cursor.execute("select student_name, grades_json, exemplary_badge from ai_grades_vault where lms_number = %s and assignment_name = %s", (ai_lms_val, ai_assign_val))
                                vault_rows = cursor.fetchall()
                                cursor.close()
                                conn.close()
                                for r in vault_rows:
                                    s_name, g_json, badge = r[0], r[1], r[2]
                                    try:
                                        parsed_g = json.loads(g_json)
                                    except Exception:
                                        parsed_g = {}
                                    historical_grades.append({"Student Name": f"📁 [Past] {s_name}", **parsed_g, "Max Peer Similarity (%)": "N/A (Vault)", "Exemplary Badge": badge})
                        except Exception:
                            pass

                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    new_evaluation_results = []
                    total_students = len(student_files_map)
                    request_timestamps = []

                    for idx, (student_name, file_list) in enumerate(student_files_map.items()):
                        now = time.time()
                        request_timestamps = [t for t in request_timestamps if now - t < 60.0]
                        if len(request_timestamps) >= 10:
                            sleep_duration = 65.0 - (now - request_timestamps[0])
                            if sleep_duration > 0:
                                status_text.text(f"⏳ Rate-limit safeguard: Pausing for {int(sleep_duration)}s to respect Google AI Studio RPM limits...")
                                time.sleep(sleep_duration)
                        request_timestamps.append(time.time())

                        status_text.text(f"Evaluating student {idx+1} of {total_students}: {student_name} (AI Rubric & Vision)...")
                        progress_bar.progress(int(100 * (idx + 1) / total_students))

                        combined_student_text = ""
                        combined_student_images = []

                        for s_file in file_list:
                            t_ext, i_ext = extract_text_and_images_from_file(s_file, s_file.name.lower())
                            combined_student_text += f"\n--- File: {s_file.name} ---\n{t_ext}\n"
                            combined_student_images.extend(i_ext)

                        prompt = f"""
                        You are an expert academic evaluator. Evaluate this student's submission bundle based strictly on the provided Assignment Instructions and Grading Rubric.
                        
                        ASSIGNMENT INSTRUCTIONS:
                        {inst_text}
                        
                        GRADING RUBRIC & POINT BREAKDOWN:
                        {rubric_text}
                        
                        STUDENT NAME: {student_name}
                        STUDENT SUBMISSION FILES EXTRACT:
                        {combined_student_text}
                        
                        TASK:
                        1. Identify all questions or sub-parts specified in the rubric/instructions (e.g., 1, 2, 3 or 1a, 1b, 2a, etc.).
                        2. Grade the submission for each question/sub-part.
                        3. Return your response STRICTLY as a valid JSON object where keys are the question identifiers (e.g., "1a", "1b", "2", "Total Score") and values are the points awarded (numeric or string score like "8/10"). Include a key named "Feedback" summarizing qualitative remarks. Do NOT include markdown code fences like ```json in your raw response, just output the raw JSON object.
                        """

                        contents = [prompt] + combined_student_images + rubric_imgs + inst_imgs
                        
                        max_retries = 3
                        retry_delay = 5.0
                        res_text = ""
                        
                        for attempt in range(max_retries):
                            try:
                                response = model.generate_content(contents)
                                res_text = response.text.strip()
                                break
                            except Exception as api_err:
                                if attempt == max_retries - 1:
                                    res_text = f'{{"Feedback": "API error after retries: {str(api_err)}", "Total Score": "0"}}'
                                else:
                                    time.sleep(retry_delay)
                                    retry_delay *= 2.0

                        if res_text.startswith("```"):
                            res_text = re.sub(r"^```(?:json)?\n?", "", res_text)
                            res_text = re.sub(r"\n?```$", "", res_text)

                        try:
                            parsed_json = json.loads(res_text)
                        except Exception:
                            parsed_json = {"Feedback": res_text, "Total Score": "Review Manually"}

                        row_data = {"Student Name": f"🆕 [New] {student_name}" if ai_is_cumulative else student_name}
                        row_data.update(parsed_json)
                        
                        max_sim_val = similarity_scores_map.get(student_name, 0.0)
                        row_data["Max Peer Similarity (%)"] = f"{max_sim_val}%" if run_plagiarism_with_ai else "Disabled"
                        row_data["Exemplary Badge"] = "Pending"
                        new_evaluation_results.append(row_data)

                        if ai_is_cumulative:
                            try:
                                conn = get_valid_db_connection()
                                if conn:
                                    cursor = conn.cursor()
                                    cursor.execute("delete from ai_grades_vault where lms_number = %s and assignment_name = %s and student_name = %s", (ai_lms_val, ai_assign_val, student_name))
                                    cursor.execute("""
                                        insert into ai_grades_vault (lms_number, assignment_name, student_name, grades_json, exemplary_badge, timestamp, expiry_date)
                                        values (%s, %s, %s, %s, %s, %s, %s)
                                    """, (ai_lms_val, ai_assign_val, student_name, json.dumps(parsed_json), "Pending", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), expiry_date))
                                    conn.commit()
                                    cursor.close()
                                    conn.close()
                            except Exception:
                                pass

                    progress_bar.empty()
                    status_text.empty()
                    st.success("AI Rubric Evaluation & Plagiarism Integration Complete!")

                    all_evals = historical_grades + new_evaluation_results
                    
                    def extract_score_val(item):
                        score_field = item.get("Total Score", "0")
                        match = re.search(r'([\d.]+)', str(score_field))
                        return float(match.group(1)) if match else 0.0

                    all_evals.sort(key=extract_score_val, reverse=True)
                    
                    badge_count = max(1, int(len(all_evals) * (exemplary_badge_pct / 100.0)))
                    for i, ev in enumerate(all_evals):
                        if i < badge_count:
                            ev["Exemplary Badge"] = "🌟 Awarded (Exemplary)"
                        else:
                            ev["Exemplary Badge"] = "-"

                    df_grades = pd.DataFrame(all_evals)
                    st.subheader("📊 Comprehensive Student Grades & Plagiarism Summary")
                    st.dataframe(df_grades, use_container_width=True)

                    out_excel = io.BytesIO()
                    with pd.ExcelWriter(out_excel, engine='openpyxl') as writer:
                        df_grades.to_excel(writer, index=False, sheet_name='AI Grades & Plagiarism')
                    
                    st.download_button(
                        label="📥 Download Combined Grading & Plagiarism Table (Excel)",
                        data=out_excel.getvalue(),
                        file_name=f"ai_grading_and_plagiarism_report_{ai_assign_val.replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_ai_excel_{rc}"
                    )

                except Exception as ex:
                    st.error(f"An error occurred during evaluation: {ex}")
        elif student_files_map and (not rubric_file or not instructions_file):
            st.warning("Please upload both the **Grading Rubric** and **Assignment Instructions** to run evaluation.")
