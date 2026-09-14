import io
import os
import zipfile
import datetime
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

st.set_page_config(page_title="APLens - Plagiarism & Matcher", page_icon="📄", layout="wide")

# --- COMPACT SIDEBAR CSS & PILL-SHAPED SOCIAL BUTTONS ---
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
        /* Custom Pill Button Styling to match brand reference */
        .social-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            background-color: #ffffff;
            color: #3c4043;
            border: 1px solid #dadce0;
            padding: 10px 16px;
            border-radius: 24px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            margin-bottom: 8px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            transition: background-color 0.2s;
        }
        .social-btn:hover {
            background-color: #f8f9fa;
            border-color: #c6c6c6;
        }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "reset_count" not in st.session_state:
    st.session_state.reset_count = 0
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "user_provider" not in st.session_state:
    st.session_state.user_provider = ""
if "saved_reports" not in st.session_state:
    st.session_state.saved_reports = []

rc = st.session_state.reset_count

# ==========================================
# TOP HEADER & OPTIONAL LOGIN BAR
# ==========================================
header_col1, header_col2 = st.columns([0.75, 0.25])

with header_col1:
    st.title("📄 APLens - Plagiarism Suite")

with header_col2:
    if st.session_state.logged_in:
        st.markdown(f"<div style='text-align: right; padding-top: 15px;'>👤 <b>{st.session_state.user_provider} User</b></div>", unsafe_allow_html=True)
        if st.button("Sign Out", key=f"sign_out_top_{rc}", type="secondary"):
            st.session_state.logged_in = False
            st.rerun()
    else:
        with st.popover("🔐 Sign In"):
            st.markdown("### Choose an Identity Provider")
            st.caption("No personal data or profile information is stored. Authentication is used solely for session preferences and report history.")
            
            # Simulated Social Logins with Branded Names
            if st.button("🟢 Sign in with Google", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.user_email = "user@gmail.com"
                st.session_state.user_provider = "Google"
                st.rerun()
            if st.button("🟦 Sign in with Microsoft", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.user_email = "user@outlook.com"
                st.session_state.user_provider = "Microsoft"
                st.rerun()
            if st.button("🍎 Sign in with Apple", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.user_email = "user@appleid.com"
                st.session_state.user_provider = "Apple"
                st.rerun()
            if st.button("📘 Sign in with Facebook", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.user_email = "user@facebook.com"
                st.session_state.user_provider = "Facebook"
                st.rerun()
            if st.button("💼 Sign in with LinkedIn", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.user_email = "user@linkedin.com"
                st.session_state.user_provider = "LinkedIn"
                st.rerun()

st.markdown("---")

# ==========================================
# SIDEBAR SETUP (State Persistence & Settings)
# ==========================================
# 1. Navigation Radio Buttons (Persisted in state)
nav_options = ["Plagiarism Checker", "Deep Dive (2-Doc Comparison)", "📁 Report History Dashboard", "💡 User Guide & Help"]
default_nav_idx = st.session_state.get("last_nav_idx", 0)
app_mode = st.sidebar.radio(
    "Navigation", 
    nav_options, 
    index=min(default_nav_idx, len(nav_options)-1),
    key=f"nav_mode_{rc}"
)
st.session_state.last_nav_idx = nav_options.index(app_mode)

st.sidebar.markdown("---")

# 2. Analysis Settings & Persistence
st.sidebar.subheader("Analysis Settings")
default_min = st.session_state.get("saved_min_words", 4)
default_max = st.session_state.get("saved_max_words", 6)
default_thresh = st.session_state.get("saved_threshold", 40)

min_words = st.sidebar.slider("Minimum N-Gram Words", min_value=1, max_value=10, value=default_min, key=f"min_words_{rc}")
max_words = st.sidebar.slider("Maximum N-Gram Words", min_value=1, max_value=10, value=default_max, key=f"max_words_{rc}")
similarity_threshold = st.sidebar.slider("🚨 Flagging Threshold (%)", min_value=10, max_value=100, value=default_thresh, step=5, key=f"sim_threshold_{rc}", help="Pairs exceeding this similarity percentage will be flagged as high risk.")

st.session_state.saved_min_words = min_words
st.session_state.saved_max_words = max_words
st.session_state.saved_threshold = similarity_threshold

st.sidebar.markdown("---")

# 3. Report History Controls (Only active or functional when logged in)
st.sidebar.subheader("Report History Settings")
if st.session_state.logged_in:
    save_reports_toggle = st.sidebar.toggle("💾 Save Generated Reports", value=True, key=f"save_reports_toggle_{rc}")
    retention_intervals = ["1 day", "1 week", "10 days", "A Fortnight", "3 weeks", "A Month"]
    selected_interval = st.sidebar.selectbox("Retention Period", retention_intervals, index=1, key=f"retention_interval_{rc}")

    interval_days_map = {"1 day": 1, "1 week": 7, "10 days": 10, "A Fortnight": 14, "3 weeks": 21, "A Month": 30}
    days_to_add = interval_days_map.get(selected_interval, 7)
    expiry_date = (datetime.datetime.now() + datetime.timedelta(days=days_to_add)).strftime("%Y-%m-%d")
    st.sidebar.caption(f"📅 Auto-deletion date: **{expiry_date}**")
else:
    save_reports_toggle = False
    st.sidebar.info("💡 **Sign in** (via top-right icon) to enable automated report history storage and custom retention settings.")

st.sidebar.markdown("---")

# 4. Global Smart Filtering
st.sidebar.subheader("Global Smart Filtering")
reference_file = st.sidebar.file_uploader(
    "Upload Assignment Instructions/Syllabus (Optional)",
    type=["docx", "pdf", "txt", "rtf", "md", "xlsx", "xls"],
    key=f"global_ref_file_{rc}",
    max_upload_size=5,
    help="Upload the assignment prompt or reference file once (Max 5MB)."
)

st.sidebar.markdown("---")

# 5. Reset Button
if st.sidebar.button("🔄 Reset Everything", type="secondary"):
    st.session_state.reset_count += 1
    keys_to_clear = [k for k in list(st.session_state.keys()) if k not in ["reset_count", "logged_in", "user_email", "user_provider", "saved_reports"]]
    for key in keys_to_clear:
        del st.session_state[key]
    st.rerun()

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

global_reference_text = ""
if reference_file:
    reference_file.seek(0)
    global_reference_text = extract_text_from_file_obj(reference_file, reference_file.name.lower())


# ==========================================
# MODE 1: PLAGIARISM CHECKER
# ==========================================
if app_mode == "Plagiarism Checker":
    st.header("File Similarity Matrix Analysis")
    
    course_assignment_name = st.text_input("📚 Course Name / Assignment Title", placeholder="e.g., CS101 - Final Research Paper", key=f"plag_course_name_{rc}")
    st.write("Upload multiple student submissions (including Word, PDF, Excel, Markdown), a direct folder, or a ZIP archive below.")

    default_upload_idx = st.session_state.get("saved_upload_type_idx", 0)
    upload_types = ["Individual Files", "Direct Folder Selection", "ZIP Archive (.zip)"]
    upload_choice = st.radio(
        "Select Upload Type", 
        upload_types, 
        index=min(default_upload_idx, len(upload_types)-1),
        key=f"folder_upload_choice_{rc}"
    )
    st.session_state.saved_upload_type_idx = upload_types.index(upload_choice)

    raw_uploaded_files = []
    directory_uploaded_files = []
    zip_uploaded_file = None
    supported_exts = ("docx", "pdf", "txt", "rtf", "md", "xlsx", "xls")

    if upload_choice == "Individual Files":
        raw_uploaded_files = st.file_uploader(
            "Upload Student Submission Documents (.docx, .pdf, .txt, .rtf, .md, .xlsx, .xls) - Max 5MB per file",
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
            "Upload ZIP Folder Archive containing student submissions (Allows up to 100MB for batch archives)",
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
            if len(processed_files) < 2:
                st.error("Please upload at least 2 documents to perform a comparison.")
            else:
                analysis_mode_label = "Paraphrased Plagiarism Analysis" if run_paraphrase else "Standard Plagiarism Analysis"
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text(f"Initializing {analysis_mode_label}...")
                progress_bar.progress(10)
                
                documents, filenames = [], []
                total_to_process = len(processed_files)
                
                for idx, file in enumerate(processed_files):
                    status_text.text(f"Extracting text from file {idx+1} of {total_to_process}: {file.name}")
                    progress_bar.progress(10 + int(60 * (idx + 1) / total_to_process))
                    
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
                    progress_bar.empty()
                    status_text.empty()
                    st.error("Not enough valid text found in the uploaded documents.")
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
                        vectorizer = TfidfVectorizer(
                            stop_words='english', 
                            ngram_range=(min_words, max_words), 
                            max_features=10000
                        )
                        tfidf_matrix = vectorizer.fit_transform(documents)
                        similarity_matrix = (cosine_similarity(tfidf_matrix) * 100).tolist()
                    
                    progress_bar.progress(100)
                    status_text.text("Analysis complete!")
                    
                    df = pd.DataFrame(similarity_matrix, index=filenames, columns=filenames)
                    
                    st.session_state.folder_df = df
                    st.session_state.folder_similarity_matrix = similarity_matrix
                    st.session_state.folder_filenames = filenames
                    st.session_state.folder_analyzed = True
                    st.session_state.analysis_type_run = analysis_mode_label
                    st.session_state.active_course_name = course_assignment_name.strip() or "Unnamed Assignment"
                    
                    if st.session_state.logged_in and save_reports_toggle:
                        report_entry = {
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "type": analysis_mode_label,
                            "course": st.session_state.active_course_name,
                            "files_count": len(filenames),
                            "df": df,
                            "matrix": similarity_matrix,
                            "filenames": filenames,
                            "expiry": expiry_date
                        }
                        st.session_state.saved_reports.append(report_entry)
                    
                    progress_bar.empty()
                    status_text.empty()
                    st.rerun()

    if st.session_state.get("folder_analyzed", False):
        df = st.session_state.folder_df
        similarity_matrix = st.session_state.folder_similarity_matrix
        filenames = st.session_state.folder_filenames
        run_label = st.session_state.get("analysis_type_run", "Analysis")
        current_course = st.session_state.get("active_course_name", "General Report")

        st.success(f"{run_label} Complete for: **{current_course}**!")

        total_files = len(filenames)
        flat_scores = [similarity_matrix[i][j] for i in range(total_files) for j in range(total_files) if i != j]
        max_sim = max(flat_scores) if flat_scores else 0.0
        avg_sim = sum(flat_scores) / len(flat_scores) if flat_scores else 0.0
        
        flagged_pairs_count = sum(1 for score in flat_scores if score >= similarity_threshold)

        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        with mcol1:
            st.metric("📁 Files Scanned", total_files)
        with mcol2:
            st.metric("📈 Max Similarity", f"{max_sim:.1f}%")
        with mcol3:
            st.metric("📊 Average Similarity", f"{avg_sim:.1f}%")
        with mcol4:
            st.metric("🚨 Flagged Pairs (≥{}%)".format(similarity_threshold), flagged_pairs_count)

        if flagged_pairs_count > 0:
            st.warning(f"⚠️ **Attention:** Found **{flagged_pairs_count} document pair(s)** meeting or exceeding the **{similarity_threshold}%** threshold limit out of {len(flat_scores)} total pairings.")
        else:
            st.info(f"✅ **All clear:** No document pairs exceed the **{similarity_threshold}%** threshold limit.")

        st.subheader(f"Visual Heatmap ({run_label})")
        st.write("💡 *Tip: Use Plotly's toolbar on the top right to zoom, pan, or inspect matrix coordinates.*")
        
        truncated_names = [name if len(name) <= 20 else name[:17] + "..." for name in filenames]
        
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
        fig.update_layout(
            height=750,
            margin=dict(l=150, r=50, t=50, b=150),
            xaxis=dict(tickangle=-45),
            yaxis=dict(autorange='reversed')
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
            file_name=f"plagiarism_report_{current_course.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_excel_report_{rc}"
        )

# ==========================================
# MODE 2: DEEP DIVE COMPARISON
# ==========================================
elif app_mode == "Deep Dive (2-Doc Comparison)":
    st.header("Deep Dive Matcher")
    
    course_assignment_name = st.text_input("📚 Course Name / Assignment Title", placeholder="e.g., CS101 - Assignment 2 Check", key=f"deep_course_name_{rc}")
    st.write("Compare two specific documents or spreadsheets sheet-by-sheet to extract exact matching sentences or true paragraphs.")
    
    if global_reference_text:
        st.info("💡 Global Smart Filtering is active: Assignment prompt/reference text will be automatically filtered out during matching.")

    col1, col2 = st.columns(2)
    with col1:
        file1 = st.file_uploader("Select Student A Document (Max 5MB)", type=["docx", "pdf", "txt", "rtf", "md", "xlsx", "xls"], max_upload_size=5, key=f"deep_file1_{rc}")
    with col2:
        file2 = st.file_uploader("Select Student B Document (Max 5MB)", type=["docx", "pdf", "txt", "rtf", "md", "xlsx", "xls"], max_upload_size=5, key=f"deep_file2_{rc}")

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
            c_name = course_assignment_name.strip() or "2-Doc Comparison"
            
            try:
                if is_excel_comparison and analysis_type == "Sheet-by-Sheet Analysis" and run_deep_para:
                    breakdown = get_excel_sheet_breakdown(path1, path2, global_reference_text, paraphrase_mode=True)
                    st.session_state.deep_result_type = "excel_sheets_paraphrase"
                    st.session_state.deep_excel_breakdown = breakdown
                    
                    report_content = f"Excel Sheet-by-Sheet Paraphrase Report ({c_name})\nComparing '{file1.name}' and '{file2.name}'\n" + "="*70 + "\n\n"
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
                    
                    report_content = f"Excel Sheet-by-Sheet Comparison Report ({c_name})\nComparing '{file1.name}' and '{file2.name}'\n" + "="*70 + "\n\n"
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
                    
                    report_content = f"Paraphrase Deep Dive Report ({c_name}): Comparing '{file1.name}' and '{file2.name}'\n"
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
                        report_content = f"Comparison Report ({c_name}): Comparing '{file1.name}' and '{file2.name}'\n"
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
                        report_content = f"Comparison Report ({c_name}): Comparing '{file1.name}' and '{file2.name}'\n"
                        report_content += f"Found {len(common_paras)} matching paragraphs:\n" + "="*70 + "\n\n"
                        for p in common_paras: report_content += p + "\n\n" + "="*50 + "\n\n"
                        
                        st.session_state.deep_result_type = "paragraphs"
                        st.session_state.deep_count = len(common_paras)
                        st.session_state.deep_report_content = report_content
                        st.session_state.deep_filename = "common_paragraphs_report.txt"
                
                if st.session_state.logged_in and save_reports_toggle and "deep_report_content" in st.session_state:
                    deep_entry = {
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "type": f"Deep Dive ({analysis_type})",
                        "course": c_name,
                        "files_compared": f"{file1.name} vs {file2.name}",
                        "content": st.session_state.deep_report_content,
                        "filename": st.session_state.deep_filename,
                        "expiry": expiry_date
                    }
                    st.session_state.saved_reports.append(deep_entry)

            finally:
                if os.path.exists(path1): os.unlink(path1)
                if os.path.exists(path2): os.unlink(path2)

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

    elif st.session_state.get("deep_result_type") in ["excel_sheets_paraphrase", "excel_sheets"]:
        st.success("Excel Sheet-by-Sheet analysis complete!")
        for item in st.session_state.deep_excel_breakdown:
            title_text = f"Sheet: {item['sheet']} ({item.get('count', 0)} matches found)"
            with st.expander(title_text):
                if not item['in_both']:
                    st.warning("This sheet name exists in only one of the uploaded workbooks.")
                else:
                    if 'paraphrase_pairs' in item and item['paraphrase_pairs']:
                        for p1, p2, score in item['paraphrase_pairs']:
                            st.markdown(f"- **[Similarity: {score}%]**\n  * **Doc A:** {p1}\n  * **Doc B:** {p2}")
                    elif 'common_sentences' in item and item['common_sentences']:
                        for s in item['common_sentences']:
                            st.markdown(f"- {s}")
                    else:
                        st.info("No significant matches found in this sheet.")
        st.text_area("Full Breakdown Report", st.session_state.deep_report_content, height=300, key=f"deep_preview_excel_{rc}")
        st.download_button("📥 Download Report (.txt)", data=st.session_state.deep_report_content, file_name=st.session_state.deep_filename, mime="text/plain", key=f"download_deep_excel_{rc}")

    elif st.session_state.get("deep_result_type") in ["sentences", "paragraphs"]:
        count = st.session_state.deep_count
        label_text = "matching sentence(s)/line(s)!" if st.session_state.deep_result_type == "sentences" else "matching paragraph(s)!"
        st.success(f"Found {count} {label_text}")
        st.text_area("Matching Preview", st.session_state.deep_report_content, height=300, key=f"deep_preview_area_{rc}")
        st.download_button("📥 Download Report (.txt)", data=st.session_state.deep_report_content, file_name=st.session_state.deep_filename, mime="text/plain", key=f"download_deep_report_{rc}")

    if not file1 or not file2:
        st.warning("Please upload both Student A and Student B documents to run Deep Dive.")

# ==========================================
# MODE 3: REPORT HISTORY DASHBOARD
# ==========================================
elif app_mode == "📁 Report History Dashboard":
    st.header("📁 Saved Report History Dashboard")
    
    if not st.session_state.logged_in:
        st.warning("🔒 Please sign in using the **Sign In** button at the top right to access and view your saved report history.")
    else:
        st.write("Review, reload, or download your previously generated batch and deep-dive comparison reports stored during your session.")

        if not st.session_state.saved_reports:
            st.info("No reports saved yet. Enable the **Save Generated Reports** toggle in the sidebar and run an analysis to populate your history dashboard!")
        else:
            if st.button("🗑️ Clear All Saved History", type="secondary"):
                st.session_state.saved_reports = []
                st.rerun()

            for idx, rep in enumerate(reversed(st.session_state.saved_reports)):
                with st.expander(f"📌 [{rep['timestamp']}] Course: {rep['course']} — Type: {rep['type']} (Expires: {rep['expiry']})"):
                    st.write(f"**Analysis Type:** {rep['type']}")
                    st.write(f"**Course/Assignment:** {rep['course']}")
                    st.write(f"**Auto-Deletion Expiry Date:** {rep['expiry']}")

                    if "df" in rep:
                        st.write(f"**Files Scanned:** {rep['files_count']}")
                        st.dataframe(rep['df'].style.format("{:.2f}%"), height=200)
                        
                        out_hist = io.BytesIO()
                        with pd.ExcelWriter(out_hist, engine='openpyxl') as writer:
                            rep['df'].to_excel(writer, sheet_name='Plagiarism Report')
                        hist_excel_data = out_hist.getvalue()
                        
                        st.download_button(
                            label=f"📥 Download Excel Report [{rep['timestamp']}]",
                            data=hist_excel_data,
                            file_name=f"report_{rep['course'].replace(' ', '_')}_{idx}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"hist_dl_excel_{idx}"
                        )
                    elif "content" in rep:
                        st.write(f"**Files Compared:** {rep['files_compared']}")
                        st.text_area("Report Content Preview", rep['content'], height=200, key=f"hist_preview_{idx}")
                        st.download_button(
                            label=f"📥 Download Text Report [{rep['timestamp']}]",
                            data=rep['content'],
                            file_name=rep['filename'],
                            mime="text/plain",
                            key=f"hist_dl_txt_{idx}"
                        )

# ==========================================
# MODE 4: USER GUIDE & HELP
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
        "* **Optional Authentication:** Sign in optionally via Google, Microsoft, Apple, Facebook, or LinkedIn to manage report history.\n"
        "* **Course & Assignment Tagging:** Organize reports cleanly by entering course names and assignment titles.\n"
        "* **Report History Dashboard & Auto-Deletion:** Save reports on demand with retention windows ranging from 1 day to 1 month.\n"
        "* **Sidebar Preference Persistence:** Remembers your N-gram slider ranges, flagging thresholds, and upload method preferences.\n"
        "* **Global Smart Filtering:** Upload instructions once to automatically strip out boilerplate text across student papers.\n"
        "* **Batch Upload & File Size Limits:** Upload individual files (5MB), folders, or `.zip` archives (100MB)."
    )

    st.subheader("3. How to Read the Output Files")
    st.write(
        "When you run the **Plagiarism Checker**, you can download an Excel report (`plagiarism_report.xlsx`). "
        "Both rows and columns represent student files. The diagonal shows 100% (self-comparison). Look for off-diagonal scores "
        "meeting or exceeding your flagging threshold to investigate potential overlap."
    )

    st.subheader("4. Support, Contact & Feedback")
    st.write(
        "If you encounter any issues, require assistance, or have ideas on how to make APLens even better, please feel free to reach out. "
        "You can contact **Arun Peswani** for any help required. Your suggestions, feedback, and feature requests are always warmly welcomed!"
    )
