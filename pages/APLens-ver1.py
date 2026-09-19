import io
import os
import zipfile
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pypdf import PdfReader
import docx2txt
import tempfile
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import difflib

st.set_page_config(page_title="APLens - Plagiarism & Matcher", page_icon="📄", layout="centered")

# --- COMPACT SIDEBAR CSS & CUSTOM BADGES ---
st.markdown("""
    <style>
        [data-testid="stSidebar"] div.stVerticalBlock > div {
            gap: 0.2rem;
        }
        .metric-card {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📄 APLens - Plagiarism Suite")

# Initialize reset counter for widget state management
if "reset_count" not in st.session_state:
    st.session_state.reset_count = 0

rc = st.session_state.reset_count

# ==========================================
# SIDEBAR SETUP (Strict Sequence with Separators)
# ==========================================

# 1. Navigation Radio Buttons
app_mode = st.sidebar.radio(
    "Navigation", 
    ["Plagiarism Checker", "Deep Dive (2-Doc Comparison)", "💡 User Guide & Help"], 
    key=f"nav_mode_{rc}"
)

st.sidebar.markdown("---")

# 2. Analysis Settings (Sliders & Threshold Warning)
st.sidebar.subheader("Analysis Settings")
min_words = st.sidebar.slider("Minimum N-Gram Words", min_value=1, max_value=10, value=4, key=f"min_words_{rc}")
max_words = st.sidebar.slider("Maximum N-Gram Words", min_value=1, max_value=10, value=6, key=f"max_words_{rc}")
similarity_threshold = st.sidebar.slider("🚨 Flagging Threshold (%)", min_value=10, max_value=100, value=40, step=5, key=f"sim_threshold_{rc}", help="Pairs exceeding this similarity percentage will be flagged as high risk.")

st.sidebar.markdown("---")

# 3. Global Smart Filtering
st.sidebar.subheader("Global Smart Filtering")
reference_file = st.sidebar.file_uploader(
    "Upload Assignment Instructions/Syllabus (Optional)",
    type=["docx", "pdf", "txt", "rtf", "md", "xlsx", "xls"],
    key=f"global_ref_file_{rc}",
    help="Upload the assignment prompt or reference file once. It will be applied across analysis modes!"
)

st.sidebar.markdown("---")

# 4. Reset Button
if st.sidebar.button("🔄 Reset Everything", type="secondary"):
    st.session_state.reset_count += 1
    keys_to_clear = [k for k in list(st.session_state.keys()) if k != "reset_count"]
    for key in keys_to_clear:
        del st.session_state[key]
    st.rerun()

st.sidebar.markdown("---")

# 5. Data Privacy & Security
with st.sidebar.expander("🔒 Data Privacy & Security"):
    st.write(
        "**Are my files secure?**\n\n"
        "Yes! Uploaded documents are processed entirely in memory "
        "for the duration of your analysis session. "
        "None of your files or text data are saved, logged, or "
        "permanently stored on the cloud server.\n\n"
        "* **Where they live in memory:** The uploaded documents are read into the temporary "
        "memory (RAM) or processed via short-lived temporary files (`tempfile`) on the cloud "
        "server specifically for the duration of that session.\n\n"
        "* **Temporary lifecycle & navigation:** Your uploaded files remain temporarily available "
        "only until your results are generated. As soon as you navigate away from the current page "
        "or switch views, the active file handles are safely cleared and discarded from memory.\n\n"
        "* **After running the analysis:** Once the similarity matrix or Deep Dive text-matching is "
        "complete and your report is generated, the application finishes executing that request. In "
        "the code, the temporary files are explicitly deleted using `os.unlink(path)` right after "
        "processing, or they are automatically garbage-collected.\n\n"
        "* **After closing the app/webpage:** As soon as you close your browser tab or your session "
        "times out due to inactivity, the Streamlit server completely destroys that active container "
        "session. **None of the student files are permanently stored on the cloud server's disk.**\n\n"
        "Your data remains completely private to your active session and is discarded immediately after "
        "use, making it safe and secure for checking sensitive submissions!"
    )

# Helper function to extract text from any file object
def extract_text_from_file_obj(file_obj, filename_lower):
    text = ""
    try:
        if filename_lower.endswith('.pdf'):
            reader = PdfReader(file_obj)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted: text += extracted + " "
        elif filename_lower.endswith('.docx'):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(file_obj.getvalue() if hasattr(file_obj, 'getvalue') else file_obj.read())
                tmp_path = tmp.name
            text = docx2txt.process(tmp_path)
            os.unlink(tmp_path)
        elif filename_lower.endswith(('.txt', '.rtf', '.md')):
            content = file_obj.getvalue() if hasattr(file_obj, 'getvalue') else file_obj.read()
            text = content.decode('utf-8', errors='ignore')
        elif filename_lower.endswith(('.xlsx', '.xls')):
            file_bytes = file_obj.getvalue() if hasattr(file_obj, 'getvalue') else file_obj.read()
            xls = pd.ExcelFile(io.BytesIO(file_bytes))
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                tokens = []
                for val in df.values.flatten():
                    if pd.notna(val):
                        val_str = str(val).strip()
                        if val_str and val_str.lower() != 'nan':
                            tokens.append(val_str)
                text += f" [Sheet: {sheet_name}] " + " ".join(tokens) + " "
    except Exception as e:
        pass
    return text

# Extract global reference text if uploaded
global_reference_text = ""
if reference_file:
    reference_file.seek(0)
    global_reference_text = extract_text_from_file_obj(reference_file, reference_file.name.lower())


# ==========================================
# MODE 1: PLAGIARISM CHECKER
# ==========================================
if app_mode == "Plagiarism Checker":
    st.header("File Similarity Matrix Analysis")
    st.write("Upload multiple student submissions (including Word, PDF, Excel, Markdown), a direct folder, or a ZIP archive below.")

    upload_choice = st.radio(
        "Select Upload Type", 
        ["Individual Files", "Direct Folder Selection", "ZIP Archive (.zip)"], 
        key=f"folder_upload_choice_{rc}"
    )

    raw_uploaded_files = []
    directory_uploaded_files = []
    zip_uploaded_file = None
    supported_exts = ("docx", "pdf", "txt", "rtf", "md", "xlsx", "xls")

    if upload_choice == "Individual Files":
        raw_uploaded_files = st.file_uploader(
            "Upload Student Submission Documents (.docx, .pdf, .txt, .rtf, .md, .xlsx, .xls)",
            type=list(supported_exts),
            accept_multiple_files=True,
            key=f"folder_indiv_files_{rc}"
        )
    elif upload_choice == "Direct Folder Selection":
        directory_uploaded_files = st.file_uploader(
            "Select an entire folder containing student submissions",
            type=list(supported_exts),
            accept_multiple_files="directory",
            key=f"folder_dir_files_{rc}"
        )
    else:
        zip_uploaded_file = st.file_uploader(
            "Upload ZIP Folder Archive containing student submissions",
            type=["zip"],
            key=f"folder_zip_file_{rc}"
        )

    # Process files based on upload selection
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
            if len(processed_files) < 2:
                st.error("Please upload at least 2 documents to perform a comparison.")
            else:
                analysis_mode_label = "Paraphrased Plagiarism Analysis" if run_paraphrase else "Standard Plagiarism Analysis"
                with st.spinner(f"Running {analysis_mode_label}..."):
                    documents, filenames = [], []
                    
                    for file in processed_files:
                        file.seek(0)
                        txt = extract_text_from_file_obj(file, file.name.lower())
                        if txt.strip():
                            if global_reference_text.strip():
                                prompt_words = set(global_reference_text.split())
                                cleaned_txt = " ".join([w for w in txt.split() if w not in prompt_words or len(prompt_words) < 5])
                                if len(cleaned_txt.strip()) > 50:
                                    txt = cleaned_txt
                            
                            documents.append(txt)
                            filenames.append(file.name)
                    
                    if len(documents) < 2:
                        st.error("Not enough valid text found in the uploaded documents.")
                    else:
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
                            vectorizer = TfidfVectorizer(
                                stop_words='english', 
                                ngram_range=(min_words, max_words), 
                                max_features=10000
                            )
                            tfidf_matrix = vectorizer.fit_transform(documents)
                            similarity_matrix = (cosine_similarity(tfidf_matrix) * 100).tolist()
                        
                        df = pd.DataFrame(similarity_matrix, index=filenames, columns=filenames)
                        
                        st.session_state.folder_df = df
                        st.session_state.folder_similarity_matrix = similarity_matrix
                        st.session_state.folder_filenames = filenames
                        st.session_state.folder_analyzed = True
                        st.session_state.analysis_type_run = analysis_mode_label

    # Render results if they exist in session state
    if st.session_state.get("folder_analyzed", False):
        df = st.session_state.folder_df
        similarity_matrix = st.session_state.folder_similarity_matrix
        filenames = st.session_state.folder_filenames
        run_label = st.session_state.get("analysis_type_run", "Analysis")

        st.success(f"{run_label} Complete!")
        
        # --- METRICS & SUMMARY CARDS (UI Enhancement) ---
        total_files = len(filenames)
        flat_scores = [similarity_matrix[i][j] for i in range(total_files) for j in range(total_files) if i != j]
        max_sim = max(flat_scores) if flat_scores else 0.0
        avg_sim = sum(flat_scores) / len(flat_scores) if flat_scores else 0.0
        
        # Count high-risk pairs exceeding threshold
        flagged_pairs_count = sum(1 for score in flat_scores if score >= similarity_threshold)

        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        with mcol1:
            st.metric("📁 Files Scanned", total_files)
        with mcol2:
            st.metric("📈 Max Similarity", f"{max_sim:.1f}%")
        with mcol3:
            st.metric("📊 Average Similarity", f"{avg_sim:.1f}%")
        with mcol4:
            st.metric("🚨 Flagged Pairs (≥{}%)".format(similarity_threshold), flagged_pairs_count, delta_color="inverse" if flagged_pairs_count > 0 else "off")

        # Threshold Flagging Warning Box
        if flagged_pairs_count > 0:
            st.warning(f"⚠️ **Attention:** Found **{flagged_pairs_count} document pair(s)** meeting or exceeding the **{similarity_threshold}%** threshold limit. Review the heatmap and report below.")
        else:
            st.info(f"✅ **All clear:** No document pairs exceed the **{similarity_threshold}%** threshold limit.")

        # --- VISUAL HEATMAP ---
        st.subheader(f"Visual Heatmap ({run_label})")
        text_annotations = [[f"{val:.1f}%" for val in row] for row in similarity_matrix]
        
        fig = go.Figure(data=go.Heatmap(
            z=similarity_matrix,
            x=filenames,
            y=filenames,
            text=text_annotations,
            texttemplate="%{text}",
            colorscale="Reds" if "Paraphrase" not in run_label else "Oranges",
            zmin=0,
            zmax=100
        ))
        fig.update_layout(
            height=500, 
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis=dict(tickangle=-45)
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Similarity Matrix Report (%)")
        st.dataframe(df.style.format("{:.2f}%"))
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Plagiarism Report')
        processed_data = output.getvalue()
        
        st.download_button(
            label="📥 Download Plagiarism Report (Excel)",
            data=processed_data,
            file_name="plagiarism_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_excel_report_{rc}"
        )

# ==========================================
# MODE 2: DEEP DIVE COMPARISON
# ==========================================
elif app_mode == "Deep Dive (2-Doc Comparison)":
    st.header("Deep Dive Matcher")
    st.write("Compare two specific documents or spreadsheets sheet-by-sheet to extract exact matching sentences or true paragraphs.")
    
    if global_reference_text:
        st.info("💡 Global Smart Filtering is active: Assignment prompt/reference text will be automatically filtered out during matching.")

    col1, col2 = st.columns(2)
    with col1:
        file1 = st.file_uploader("Select Student A Document", type=["docx", "pdf", "txt", "rtf", "md", "xlsx", "xls"], key=f"deep_file1_{rc}")
    with col2:
        file2 = st.file_uploader("Select Student B Document", type=["docx", "pdf", "txt", "rtf", "md", "xlsx", "xls"], key=f"deep_file2_{rc}")

    def get_file_bytes_temp(uploaded_file):
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.getvalue())
            return tmp.name

    def is_valid_sentence(sentence):
        s = sentence.strip()
        if re.fullmatch(r'\d+\.?', s):
            return False
        if len(s.split()) < 4:
            return False
        return True

    def get_document_lines_and_sentences(file_path, reference_text=""):
        ext = os.path.splitext(file_path)[1].lower()
        raw_blocks = []
        if ext == '.docx':
            import docx
            doc = docx.Document(file_path)
            raw_blocks = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        elif ext == '.pdf':
            reader = PdfReader(file_path)
            full_text_pdf = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted: full_text_pdf += extracted + "\n\n"
            raw_blocks = [b.replace('\n', ' ').strip() for b in re.split(r'\n\s*\n', full_text_pdf) if b.strip()]
        elif ext in ('.txt', '.rtf', '.md'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                full_text_txt = f.read()
            raw_blocks = [b.replace('\n', ' ').strip() for b in re.split(r'\n\s*\n', full_text_txt) if b.strip()]
        elif ext in ('.xlsx', '.xls'):
            xls = pd.ExcelFile(file_path)
            full_text_excel = ""
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                tokens = []
                for val in df.values.flatten():
                    if pd.notna(val):
                        val_str = str(val).strip()
                        if val_str and val_str.lower() != 'nan':
                            tokens.append(val_str)
                full_text_excel += f" [Sheet: {sheet_name}] " + " ".join(tokens) + " \n\n"
            raw_blocks = [b.replace('\n', ' ').strip() for b in re.split(r'\n\s*\n', full_text_excel) if b.strip()]
        
        prompt_words = set(reference_text.split()) if reference_text else set()
        units = set()
        for block in raw_blocks:
            cleaned_block = re.sub(r'\s+', ' ', block)
            if not cleaned_block: continue
            
            if prompt_words:
                cleaned_block = " ".join([w for w in cleaned_block.split() if w not in prompt_words or len(prompt_words) < 5])
            
            if not cleaned_block.strip(): continue
            sub_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned_block) if s.strip()]
            if len(sub_sentences) <= 1:
                if is_valid_sentence(cleaned_block):
                    units.add(cleaned_block)
            else:
                for s in sub_sentences:
                    if is_valid_sentence(s):
                        units.add(s)
        return units

    def get_document_true_paragraphs(file_path, reference_text=""):
        ext = os.path.splitext(file_path)[1].lower()
        raw_blocks = []
        if ext == '.docx':
            import docx
            doc = docx.Document(file_path)
            raw_blocks = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        elif ext == '.pdf':
            reader = PdfReader(file_path)
            full_text_pdf = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted: full_text_pdf += extracted + "\n\n"
            raw_blocks = [b.replace('\n', ' ').strip() for b in re.split(r'\n\s*\n', full_text_pdf) if b.strip()]
        elif ext in ('.txt', '.rtf', '.md'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                full_text_txt = f.read()
            raw_blocks = [b.replace('\n', ' ').strip() for b in re.split(r'\n\s*\n', full_text_txt) if b.strip()]
        elif ext in ('.xlsx', '.xls'):
            xls = pd.ExcelFile(file_path)
            full_text_excel = ""
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                tokens = []
                for val in df.values.flatten():
                    if pd.notna(val):
                        val_str = str(val).strip()
                        if val_str and val_str.lower() != 'nan':
                            tokens.append(val_str)
                full_text_excel += f" [Sheet: {sheet_name}] " + " ".join(tokens) + " \n\n"
            raw_blocks = [b.replace('\n', ' ').strip() for b in re.split(r'\n\s*\n', full_text_excel) if b.strip()]
        
        prompt_words = set(reference_text.split()) if reference_text else set()
        valid_paragraphs = []
        for block in raw_blocks:
            cleaned_block = re.sub(r'\s+', ' ', block)
            if prompt_words:
                cleaned_block = " ".join([w for w in cleaned_block.split() if w not in prompt_words or len(prompt_words) < 5])
            
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned_block) if s.strip()]
            if len(sentences) >= 2 and len(cleaned_block.split()) >= 8:
                valid_paragraphs.append(cleaned_block)
        return valid_paragraphs

    def get_excel_sheet_breakdown(path1, path2, reference_text="", paraphrase_mode=False):
        xls1 = pd.ExcelFile(path1)
        xls2 = pd.ExcelFile(path2)
        sheets1 = xls1.sheet_names
        sheets2 = xls2.sheet_names
        all_sheets = sorted(list(set(sheets1).union(set(sheets2))))
        
        prompt_words = set(reference_text.split()) if reference_text else set()
        breakdown_results = []
        
        for sname in all_sheets:
            sheet_data = {"sheet": sname, "in_both": sname in sheets1 and sname in sheets2}
            if sheet_data["in_both"]:
                df1 = pd.read_excel(xls1, sheet_name=sname, header=None).fillna("")
                df2 = pd.read_excel(xls2, sheet_name=sname, header=None).fillna("")
                
                def extract_sentences_from_df(df):
                    text_blob = " ".join([str(v).strip() for v in df.values.flatten() if str(v).strip() and str(v).lower() != 'nan'])
                    if prompt_words:
                        text_blob = " ".join([w for w in text_blob.split() if w not in prompt_words or len(prompt_words) < 5])
                    sub_sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text_blob) if s.strip()]
                    return [s for s in sub_sents if is_valid_sentence(s)]
                
                sents1 = extract_sentences_from_df(df1)
                sents2 = extract_sentences_from_df(df2)
                
                if paraphrase_mode:
                    matched_pairs = []
                    for u1 in sents1:
                        for u2 in sents2:
                            if u1 == u2: continue
                            ratio = difflib.SequenceMatcher(None, u1.lower(), u2.lower()).ratio()
                            if 0.65 <= ratio < 1.0:
                                matched_pairs.append((u1, u2, round(ratio * 100, 1)))
                    matched_pairs.sort(key=lambda x: x[2], reverse=True)
                    sheet_data["paraphrase_pairs"] = matched_pairs
                    sheet_data["count"] = len(matched_pairs)
                else:
                    common_sents = sorted(list(set(sents1).intersection(set(sents2))))
                    sheet_data["common_sentences"] = common_sents
                    sheet_data["count"] = len(common_sents)
            else:
                if paraphrase_mode:
                    sheet_data["paraphrase_pairs"] = []
                else:
                    sheet_data["common_sentences"] = []
                sheet_data["count"] = 0
            breakdown_results.append(sheet_data)
        return breakdown_results

    if file1 and file2:
        is_excel_comparison = file1.name.lower().endswith(('.xlsx', '.xls')) and file2.name.lower().endswith(('.xlsx', '.xls'))
        
        if is_excel_comparison:
            analysis_type = st.radio("Select Match Type", ["Sheet-by-Sheet Analysis", "Sentence Comparison", "Paragraph Comparison"], key=f"deep_match_type_{rc}")
        else:
            analysis_type = st.radio("Select Match Type", ["Sentence Comparison", "Paragraph Comparison"], key=f"deep_match_type_{rc}")
        
        col_deep1, col_deep2 = st.columns(2)
        with col_deep1:
            run_deep = st.button("Run Deep Dive Matcher", type="primary", key=f"run_deep_dive_{rc}")
        with col_deep2:
            run_deep_para = st.button("🔍 Run Paraphrase Matcher", type="secondary", key=f"run_deep_para_{rc}")

        if run_deep or run_deep_para:
            path1 = get_file_bytes_temp(file1)
            path2 = get_file_bytes_temp(file2)
            
            try:
                if is_excel_comparison and analysis_type == "Sheet-by-Sheet Analysis" and run_deep_para:
                    breakdown = get_excel_sheet_breakdown(path1, path2, global_reference_text, paraphrase_mode=True)
                    st.session_state.deep_result_type = "excel_sheets_paraphrase"
                    st.session_state.deep_excel_breakdown = breakdown
                    
                    report_content = f"Excel Sheet-by-Sheet Paraphrase Report\nComparing '{file1.name}' and '{file2.name}'\n" + "="*70 + "\n\n"
                    for item in breakdown:
                        report_content += f"Sheet Name: {item['sheet']}\n"
                        if not item['in_both']:
                            report_content += "  -> Note: Sheet exists in only one of the workbooks.\n\n"
                        else:
                            report_content += f"  -> Potential Paraphrased Pairs Found: {item['count']}\n"
                            for p1, p2, score in item['paraphrase_pairs']:
                                report_content += f"     • [Similarity: {score}%]\n       - A: {p1}\n       - B: {p2}\n"
                            report_content += "\n"
                    st.session_state.deep_report_content = report_content
                    st.session_state.deep_filename = "excel_sheet_paraphrase_report.txt"

                elif is_excel_comparison and analysis_type == "Sheet-by-Sheet Analysis":
                    breakdown = get_excel_sheet_breakdown(path1, path2, global_reference_text, paraphrase_mode=False)
                    st.session_state.deep_result_type = "excel_sheets"
                    st.session_state.deep_excel_breakdown = breakdown
                    
                    report_content = f"Excel Sheet-by-Sheet Comparison Report\nComparing '{file1.name}' and '{file2.name}'\n" + "="*70 + "\n\n"
                    for item in breakdown:
                        report_content += f"Sheet Name: {item['sheet']}\n"
                        if not item['in_both']:
                            report_content += "  -> Note: Sheet exists in only one of the workbooks.\n\n"
                        else:
                            report_content += f"  -> Matching Sentences Found: {item['count']}\n"
                            for s in item['common_sentences']:
                                report_content += f"     • {s}\n"
                            report_content += "\n"
                    st.session_state.deep_report_content = report_content
                    st.session_state.deep_filename = "excel_sheet_comparison_report.txt"

                elif run_deep_para:
                    units1 = list(get_document_lines_and_sentences(path1, global_reference_text))
                    units2 = list(get_document_lines_and_sentences(path2, global_reference_text))
                    pairs = []
                    for u1 in units1:
                        for u2 in units2:
                            if u1 == u2: continue
                            ratio = difflib.SequenceMatcher(None, u1.lower(), u2.lower()).ratio()
                            if 0.65 <= ratio < 1.0:
                                pairs.append((u1, u2, round(ratio * 100, 1)))
                    pairs.sort(key=lambda x: x[2], reverse=True)
                    
                    st.session_state.deep_result_type = "paraphrased_matches"
                    st.session_state.deep_para_pairs = pairs
                    
                    report_content = f"Paraphrase Deep Dive Report: Comparing '{file1.name}' and '{file2.name}'\n"
                    report_content += f"Found {len(pairs)} potential paraphrased sentence matches:\n" + "="*70 + "\n\n"
                    for p1, p2, score in pairs:
                        report_content += f"[Similarity: {score}%]\n- Doc A: {p1}\n- Doc B: {p2}\n\n"
                    st.session_state.deep_report_content = report_content
                    st.session_state.deep_filename = "paraphrase_deep_dive_report.txt"

                elif analysis_type == "Sentence Comparison":
                    units1 = get_document_lines_and_sentences(path1, global_reference_text)
                    units2 = get_document_lines_and_sentences(path2, global_reference_text)
                    common_units = sorted(units1.intersection(units2))
                    
                    if not common_units:
                        st.session_state.deep_result_type = "empty_sentences"
                    else:
                        report_content = f"Comparison Report: Comparing '{file1.name}' and '{file2.name}'\n"
                        report_content += f"Found {len(common_units)} matching sentences/lines:\n" + "="*70 + "\n\n"
                        for u in common_units: report_content += u + "\n\n"
                        
                        st.session_state.deep_result_type = "sentences"
                        st.session_state.deep_count = len(common_units)
                        st.session_state.deep_report_content = report_content
                        st.session_state.deep_filename = "common_sentences_report.txt"
                
                else:
                    paras1 = get_document_true_paragraphs(path1, global_reference_text)
                    paras2 = get_document_true_paragraphs(path2, global_reference_text)
                    common_paras = sorted(set(paras1).intersection(set(paras2)))
                    
                    if not common_paras:
                        st.session_state.deep_result_type = "empty_paras"
                    else:
                        report_content = f"Comparison Report: Comparing '{file1.name}' and '{file2.name}'\n"
                        report_content += f"Found {len(common_paras)} matching paragraphs:\n" + "="*70 + "\n\n"
                        for p in common_paras: report_content += p + "\n\n" + "="*50 + "\n\n"
                        
                        st.session_state.deep_result_type = "paragraphs"
                        st.session_state.deep_count = len(common_paras)
                        st.session_state.deep_report_content = report_content
                        st.session_state.deep_filename = "common_paragraphs_report.txt"
            
            finally:
                if os.path.exists(path1): os.unlink(path1)
                if os.path.exists(path2): os.unlink(path2)

    # Render deep dive results if they exist in session state
    if st.session_state.get("deep_result_type") == "empty_sentences":
        st.info("Found 0 matching sentences/lines.")
    elif st.session_state.get("deep_result_type") == "empty_paras":
        st.info("Found 0 matching paragraphs (with at least 2 sentences).")
    elif st.session_state.get("deep_result_type") == "paraphrased_matches":
        pairs = st.session_state.deep_para_pairs
        if not pairs:
            st.info("Found 0 potential paraphrased sentence matches.")
        else:
            st.success(f"Found {len(pairs)} potential paraphrased sentence match(es)!")
            for p1, p2, score in pairs:
                with st.expander(f"Similarity Score: {score}%"):
                    st.markdown(f"**Document A:** {p1}")
                    st.markdown(f"**Document B:** {p2}")
            st.text_area("Paraphrase Deep Dive Report", st.session_state.deep_report_content, height=300, key=f"deep_preview_para_{rc}")
            st.download_button("📥 Download Paraphrase Report (.txt)", data=st.session_state.deep_report_content, file_name=st.session_state.deep_filename, mime="text/plain", key=f"download_deep_para_{rc}")

    elif st.session_state.get("deep_result_type") == "excel_sheets_paraphrase":
        st.success("Excel Sheet-by-Sheet Paraphrase analysis complete!")
        for item in st.session_state.deep_excel_breakdown:
            with st.expander(f"Sheet: {item['sheet']} ({item.get('count', 0)} potential paraphrased pairs found)"):
                if not item['in_both']:
                    st.warning("This sheet name exists in only one of the uploaded workbooks.")
                else:
                    pairs = item['paraphrase_pairs']
                    if pairs:
                        st.write("**Paraphrased Sentence Pairs:**")
                        for p1, p2, score in pairs:
                            st.markdown(f"- **[Similarity: {score}%]**\n  * **Doc A:** {p1}\n  * **Doc B:** {p2}")
                    else:
                        st.info("No potential paraphrased sentence matches found in this sheet.")
        st.text_area("Full Sheet Paraphrase Breakdown Report", st.session_state.deep_report_content, height=300, key=f"deep_preview_excel_para_{rc}")
        st.download_button("📥 Download Excel Sheet Paraphrase Report (.txt)", data=st.session_state.deep_report_content, file_name=st.session_state.deep_filename, mime="text/plain", key=f"download_deep_excel_para_{rc}")

    elif st.session_state.get("deep_result_type") == "excel_sheets":
        st.success("Excel Sheet-by-Sheet analysis complete!")
        for item in st.session_state.deep_excel_breakdown:
            with st.expander(f"Sheet: {item['sheet']} ({item.get('count', 0)} matching sentences found)"):
                if not item['in_both']:
                    st.warning("This sheet name exists in only one of the uploaded workbooks.")
                else:
                    if item['common_sentences']:
                        st.write("**Matching Sentences / Text Answers:**")
                        for s in item['common_sentences']:
                            st.markdown(f"- {s}")
                    else:
                        st.info("No identical sentence matches found in this sheet.")
        st.text_area("Full Sheet Breakdown Report", st.session_state.deep_report_content, height=300, key=f"deep_preview_excel_{rc}")
        st.download_button("📥 Download Excel Sheet Report (.txt)", data=st.session_state.deep_report_content, file_name=st.session_state.deep_filename, mime="text/plain", key=f"download_deep_excel_{rc}")

    elif st.session_state.get("deep_result_type") in ["sentences", "paragraphs"]:
        count = st.session_state.deep_count
        label_text = "matching sentence(s)/line(s)!" if st.session_state.deep_result_type == "sentences" else "matching paragraph(s)!"
        st.success(f"Found {count} {label_text}")
        st.text_area("Matching Preview", st.session_state.deep_report_content, height=300, key=f"deep_preview_area_{rc}")
        st.download_button("📥 Download Report (.txt)", data=st.session_state.deep_report_content, file_name=st.session_state.deep_filename, mime="text/plain", key=f"download_deep_report_{rc}")

    if not file1 or not file2:
        st.warning("Please upload both Student A and Student B documents to run Deep Dive.")

# ==========================================
# MODE 3: USER GUIDE & HELP (Fully Updated)
# ==========================================
elif app_mode == "💡 User Guide & Help":
    st.header("💡 User Guide & Help Center")
    st.write("Welcome to APLens! This comprehensive guide explains all tools, analysis modes, and features available in the suite.")

    st.markdown("---")

    st.subheader("1. What is APLens & What Does It Do?")
    st.write(
        "APLens is a specialized peer-to-peer plagiarism detection and document comparison web suite designed "
        "for educators, instructors, and researchers. It allows you to analyze batches of student submissions "
        "to find cross-document similarities, detect paraphrased cheating, and perform deep-dive text or spreadsheet matches."
    )

    st.subheader("2. How It Works & Key Features")
    st.write(
        "APLens offers multiple advanced analysis modes and features:\n\n"
        "* **Global Smart Filtering:** Upload an assignment instructions file, prompt, or syllabus once in the sidebar. It persists across modes and automatically strips out shared common boilerplate text from student papers.\n"
        "* **Flexible File Formats:** Fully supports `.docx`, `.pdf`, `.txt`, `.rtf`, `.md`, `.xlsx`, and `.xls` submissions.\n"
        "* **Batch Upload Options:** Upload individual files, select an entire folder directly from your computer, or upload compressed `.zip` archives.\n"
        "* **Plagiarism & Paraphrase Checker:** Calculates cross-document similarity matrices using **TF-IDF cosine similarity** (for exact matching) or **Fuzzy Sequence Matching** (to detect paraphrased rewrites).\n"
        "* **Threshold Flagging & Metrics:** Set custom flagging thresholds in the sidebar to instantly highlight high-risk pairs and view summary metrics counters.\n"
        "* **Visual Similarity Heatmap:** An interactive, color-graded heatmap plots the entire similarity matrix so clusters of high overlap jump out instantly at a glance.\n"
        "* **Deep Dive Matcher:** Upload two specific documents or multi-sheet Excel workbooks to perform sheet-by-sheet analysis, exact sentence matching, paragraph comparison, or paraphrase detection."
    )

    st.subheader("3. How to Read the Output Files (Especially the .xlsx File)")
    st.write(
        "When you run the **Plagiarism Checker**, you can download an Excel report (`plagiarism_report.xlsx`). Here is how to read it:\n\n"
        "* **The Matrix Structure:** The Excel spreadsheet is a symmetric cross-comparison table. Both the **Rows** and **Columns** "
        "represent the file names of the uploaded student submissions.\n"
        "* **Reading Cell Values:** Each cell contains a percentage value (from 0% to 100%) indicating how much textual overlap exists "
        "between the document in that row and the document in that column.\n"
        "* **The Diagonal (100%):** The cells running diagonally from top-left to bottom-right will always show **100%**, because a document "
        "is being compared against itself.\n"
        "* **Identifying Potential Plagiarism:** Look for high percentage scores off the diagonal (e.g., matching or exceeding your configured **Flagging Threshold**). A high score "
        "means those two particular student submissions share substantial matching text sequences and warrant a closer manual review."
    )

    st.subheader("4. Support, Contact & Feedback")
    st.write(
        "If you encounter any issues, require assistance, or have ideas on how to make APLens even better, please feel free to reach out. "
        "You can contact **Arun Peswani** for any help required. Your suggestions, feedback, and feature requests are always warmly welcomed!"
    )
