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

# OCR, Image Processing & HEIF Support Imports
from PIL import Image, ImageEnhance
from pdf2image import convert_from_bytes
import pytesseract
from pillow_heif import register_heif_opener
register_heif_opener()

# Supabase Client Import
from supabase import create_client, Client

st.set_page_config(page_title="APLens Beta - Plagiarism & Matcher Suite", page_icon="🧪", layout="centered")

# --- INITIALIZE SUPABASE CLIENT ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- COMPACT SIDEBAR CSS & SOCIAL LOGIN STYLING ---
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
        .login-container {
            display: flex;
            flex-direction: column;
            gap: 10px;
            width: 100%;
            max-width: 320px;
            margin: 0 auto;
        }
        .social-login-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            width: 100%;
            height: 44px;
            background-color: #ffffff;
            color: #3c4043;
            border: 1px solid #dadce0;
            border-radius: 22px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            transition: background-color 0.2s, box-shadow 0.2s, border-color 0.2s;
        }
        .social-login-btn:hover {
            background-color: #f8f9fa;
            border-color: #bdc1c6;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        .social-login-btn svg {
            width: 18px;
            height: 18px;
        }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "reset_count_beta" not in st.session_state:
    st.session_state.reset_count_beta = 0
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "saved_reports" not in st.session_state:
    st.session_state.saved_reports = []

rc = st.session_state.reset_count_beta

# Handle OAuth redirect query parameters from Supabase
query_params = st.query_params
if "access_token" in query_params or "code" in query_params:
    try:
        st.session_state.logged_in = True
        st.session_state.user_email = "Authenticated User"
        st.query_params.clear()
        st.rerun()
    except Exception:
        pass

# ==========================================
# TOP HEADER & REAL SUPABASE AUTH BAR
# ==========================================
header_col1, header_col2 = st.columns([0.7, 0.3])

with header_col1:
    st.title("🧪 APLens Beta - Plagiarism Suite")

with header_col2:
    if st.session_state.logged_in:
        st.markdown(f"<div style='text-align: right; padding-top: 15px;'>👤 <b>{st.session_state.user_email}</b></div>", unsafe_allow_html=True)
        if st.button("Sign Out", key=f"sign_out_top_{rc}", type="secondary"):
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
            st.session_state.logged_in = False
            st.session_state.user_email = ""
            st.rerun()
    else:
        with st.popover("🔐 Account Login"):
            st.markdown("### Supabase Authentication")
            auth_tab_in, auth_tab_up, auth_tab_social = st.tabs(["Sign In", "Sign Up", "Social Logins"])
            
            with auth_tab_in:
                with st.form(key=f"signin_form_{rc}"):
                    si_email = st.text_input("Email", key=f"si_email_{rc}")
                    si_password = st.text_input("Password", type="password", key=f"si_pass_{rc}")
                    si_submit = st.form_submit_button("Sign In", type="primary")
                    
                    if si_submit:
                        if not si_email or not si_password:
                            st.error("Please fill in both email and password.")
                        else:
                            try:
                                response = supabase.auth.sign_in_with_password({
                                    "email": si_email,
                                    "password": si_password
                                })
                                st.session_state.logged_in = True
                                st.session_state.user_email = si_email
                                st.success("Successfully signed in!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Sign-in failed: {e}")
            
            with auth_tab_up:
                with st.form(key=f"signup_form_{rc}"):
                    su_email = st.text_input("Email", key=f"su_email_{rc}")
                    su_password = st.text_input("Password (min 6 chars)", type="password", key=f"su_pass_{rc}")
                    su_submit = st.form_submit_button("Create Account", type="secondary")
                    
                    if su_submit:
                        if not su_email or len(su_password) < 6:
                            st.error("Please enter a valid email and a password of at least 6 characters.")
                        else:
                            try:
                                response = supabase.auth.sign_up({
                                    "email": su_email,
                                    "password": su_password
                                })
                                st.success("Account created successfully! You can now sign in.")
                            except Exception as e:
                                st.error(f"Sign-up failed: {e}")

            with auth_tab_social:
                st.caption("Authenticate instantly via Supabase OAuth providers:")
                try:
                    google_url = supabase.auth.get_sign_in_url({"provider": "google"})["url"]
                    github_url = supabase.auth.get_sign_in_url({"provider": "github"})["url"]
                    
                    st.markdown(f"""
                        <div class="login-container">
                            <a href="{google_url}" target="_self" class="social-login-btn">
                                <svg viewBox="0 0 24 24"><path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"/><path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.13 0-5.78-2.11-6.73-4.96H1.18v3.15C3.15 21.32 7.22 24 12 24z"/><path fill="#FBBC05" d="M5.27 14.24c-.25-.72-.38-1.49-.38-2.24s.13-1.52.38-2.24V6.61H1.18C.43 8.13 0 9.87 0 11.75s.43 3.62 1.18 5.14l4.09-3.15z"/><path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.22 0 3.15 2.68 1.18 6.61l4.09 3.15c.95-2.85 3.6-4.96 6.73-4.96z"/></svg>
                                Sign in with Google
                            </a>
                            <a href="{github_url}" target="_self" class="social-login-btn">
                                <svg viewBox="0 0 24 24"><path fill="#000000" d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02_000000 24 12c0-6.63-5.37-12-12-12z"/></svg>
                                Sign in with GitHub
                            </a>
                        </div>
                    """, unsafe_allow_html=True)
                except Exception as ex:
                    st.info("Configure your Supabase Project Authentication URL redirect settings to enable social login buttons.")

# ==========================================
# SIDEBAR SETUP
# ==========================================
app_mode = st.sidebar.radio(
    "Navigation", 
    ["Plagiarism Checker", "Deep Dive (2-Doc Comparison)", "📁 Report History Dashboard", "💡 User Guide & Help"], 
    key=f"nav_mode_{rc}"
)

st.sidebar.markdown("---")

st.sidebar.subheader("Analysis Settings")
min_words = st.sidebar.slider("Minimum N-Gram Words", min_value=1, max_value=10, value=4, key=f"min_words_{rc}")
max_words = st.sidebar.slider("Maximum N-Gram Words", min_value=1, max_value=10, value=6, key=f"max_words_{rc}")
similarity_threshold = st.sidebar.slider("🚨 Flagging Threshold (%)", min_value=10, max_value=100, value=40, step=5, key=f"sim_threshold_{rc}", help="Pairs exceeding this similarity percentage will be flagged as high risk.")

st.sidebar.markdown("---")

st.sidebar.subheader("Report History Settings")
if st.session_state.logged_in:
    save_reports_toggle = st.sidebar.toggle("💾 Save Generated Reports", value=True, key=f"save_toggle_{rc}")
    retention_intervals = ["1 day", "1 week", "10 days", "A Fortnight", "3 weeks", "A Month"]
    selected_interval = st.sidebar.selectbox("Retention Period", retention_intervals, index=1, key=f"ret_interval_{rc}")

    interval_days_map = {"1 day": 1, "1 week": 7, "10 days": 10, "A Fortnight": 14, "3 weeks": 21, "A Month": 30}
    expiry_date = (datetime.datetime.now() + datetime.timedelta(days=interval_days_map.get(selected_interval, 7))).strftime("%Y-%m-%d")
    st.sidebar.caption(f"📅 Calculated auto-deletion date: **{expiry_date}**")
else:
    save_reports_toggle = False
    st.sidebar.info("💡 **Sign in** via the top-right button to enable automated report history storage and custom retention windows.")

st.sidebar.markdown("---")

supported_exts = ("docx", "pdf", "txt", "rtf", "md", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "tif", "heic", "heif", "webp")

st.sidebar.subheader("Global Smart Filtering")
reference_file = st.sidebar.file_uploader(
    "Upload Assignment Instructions/Syllabus (Optional)",
    type=list(supported_exts),
    key=f"global_ref_file_{rc}",
    max_upload_size=5,
    help="Upload the assignment prompt or reference file once (Max 5MB). It will be applied across analysis modes!"
)

st.sidebar.markdown("---")

if st.sidebar.button("🔄 Reset Everything", type="secondary"):
    st.session_state.reset_count_beta += 1
    keys_to_clear = [k for k in list(st.session_state.keys()) if k not in ["reset_count_beta", "logged_in", "user_email", "saved_reports"]]
    for key in keys_to_clear:
        del st.session_state[key]
    st.rerun()

st.sidebar.markdown("---")

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

def extract_text_from_file_obj(file_obj, filename_lower):
    text = ""
    if hasattr(file_obj, 'seek'):
        file_obj.seek(0)
    file_bytes = file_obj.getvalue() if hasattr(file_obj, 'getvalue') else file_obj.read()
    try:
        if filename_lower.endswith('.pdf'):
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + " "
            
            if len(text.strip()) < 15:
                images = convert_from_bytes(file_bytes)
                ocr_text = ""
                for img in images:
                    img_gray = img.convert('L')
                    img_enhanced = ImageEnhance.Contrast(img_gray).enhance(2.5)
                    ocr_text += pytesseract.image_to_string(img_enhanced, lang='hin+eng') + " "
                if len(ocr_text.strip()) > len(text.strip()):
                    text = ocr_text

        elif filename_lower.endswith('.docx'):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            text = docx2txt.process(tmp_path)
            os.unlink(tmp_path)
            
        elif filename_lower.endswith(('.txt', '.rtf', '.md')):
            text = file_bytes.decode('utf-8', errors='ignore')
            
        elif filename_lower.endswith(('.xlsx', '.xls')):
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
                
        elif filename_lower.endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif', '.heic', '.heif', '.webp')):
            image = Image.open(io.BytesIO(file_bytes)).convert('L')
            image = ImageEnhance.Contrast(image).enhance(2.5)
            text = pytesseract.image_to_string(image, lang='hin+eng')
            
    except Exception as e:
        pass
    
    if not text.strip():
        text = f"document_content_fallback_{filename_lower}"
    return text

global_reference_text = ""
if reference_file:
    global_reference_text = extract_text_from_file_obj(reference_file, reference_file.name.lower())


# ==========================================
# MODE 1: PLAGIARISM CHECKER
# ==========================================
if app_mode == "Plagiarism Checker":
    st.header("File Similarity Matrix Analysis")
    st.write("Upload multiple student submissions (including Word, PDF, Excel, Markdown, Scans/Images), a direct folder, or a ZIP archive below.")

    course_assignment_name = st.text_input("📚 Course Name / Assignment Title (Optional)", placeholder="e.g., CS101 - Final Capstone Project", key=f"course_beta_{rc}")

    upload_choice = st.radio(
        "Select Upload Type", 
        ["Individual Files", "Direct Folder Selection", "ZIP Archive (.zip)"], 
        key=f"folder_upload_choice_{rc}"
    )

    raw_uploaded_files = []
    directory_uploaded_files = []
    zip_uploaded_file = None

    if upload_choice == "Individual Files":
        raw_uploaded_files = st.file_uploader(
            "Upload Student Submission Documents (.docx, .pdf, .txt, .rtf, .md, .xlsx, .xls, .png, .jpg, .jpeg, .tiff, .tif, .heic, .heif, .webp) - Max 5MB per file",
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
                    status_text.text(f"Extracting text from file {idx+1} of {total_to_process}: {file.name} (OCR active)")
                    progress_bar.progress(10 + int(60 * (idx + 1) / total_to_process))
                    
                    txt = extract_text_from_file_obj(file, file.name.lower())
                    
                    if global_reference_text.strip():
                        prompt_words = set(global_reference_text.split())
                        cleaned_txt = " ".join([w for w in txt.split() if w not in prompt_words or len(prompt_words) < 5])
                        if len(cleaned_txt.strip()) > 3:
                            txt = cleaned_txt
                    
                    documents.append(txt)
                    unique_name = f"{idx+1}. {file.name}"
                    filenames.append(unique_name)
                
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
                st.session_state.beta_course = course_assignment_name.strip() or "General Assignment"

                if st.session_state.logged_in and save_reports_toggle:
                    st.session_state.saved_reports.append({
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
            st.metric("📁 Files Scanned", total_files)
        with mcol2:
            st.metric("📈 Max Similarity", f"{max_sim:.1f}%")
        with mcol3:
            st.metric("📊 Average Similarity", f"{avg_sim:.1f}%")
        with mcol4:
            st.metric("🚨 Flagged Pairs (≥{}%)".format(similarity_threshold), flagged_pairs_count)

        if flagged_pairs_count > 0:
            st.warning(f"⚠️ **Attention:** Found **{flagged_pairs_count} document pair(s)** meeting or exceeding the **{similarity_threshold}%** threshold limit. Review the heatmap and report below.")
        else:
            st.info(f"✅ **All clear:** No document pairs exceed the **{similarity_threshold}%** threshold limit.")

        st.subheader(f"Visual Heatmap ({run_label})")
        st.write("💡 *Tip: Use the horizontal and vertical scrollbars around the chart to navigate the proportionate square matrix. Hover over any cell to see full names and exact scores.*")
        
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
        
        fig.update_layout(
            width=chart_dimension,
            height=chart_dimension,
            margin=dict(l=180, r=50, t=50, b=180),
            xaxis=dict(
                tickangle=-45, 
                type='category',
                tickmode='array',
                tickvals=list(range(len(truncated_names))),
                ticktext=truncated_names
            ),
            yaxis=dict(
                autorange='reversed', 
                type='category',
                tickmode='array',
                tickvals=list(range(len(truncated_names))),
                ticktext=truncated_names
            )
        )
        
        st.plotly_chart(fig, use_container_width=False)

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
    st.write("Compare two specific documents or spreadsheets sheet-by-sheet to extract exact matching sentences or true paragraphs.")
    
    if global_reference_text:
        st.info("💡 Global Smart Filtering is active: Assignment prompt/reference text will be automatically filtered out during matching.")

    col1, col2 = st.columns(2)
    with col1:
        file1 = st.file_uploader("Select Student A Document (Max 5MB)", type=list(supported_exts), max_upload_size=5, key=f"deep_file1_{rc}")
    with col2:
        file2 = st.file_uploader("Select Student B Document (Max 5MB)", type=list(supported_exts), max_upload_size=5, key=f"deep_file2_{rc}")

    def get_file_bytes_temp(uploaded_file):
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.getvalue())
            return tmp.name

    def is_valid_sentence(sentence):
        s = sentence.strip()
        if re.fullmatch(r'\d+\.?', s):
            return False
        if len(s.split()) < 2:
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
                if extracted:
                    full_text_pdf += extracted + "\n\n"
            if len(full_text_pdf.strip()) < 15:
                with open(file_path, "rb") as f:
                    pdf_bytes = f.read()
                images = convert_from_bytes(pdf_bytes)
                for img in images:
                    img_gray = img.convert('L')
                    img_enhanced = ImageEnhance.Contrast(img_gray).enhance(2.5)
                    full_text_pdf += pytesseract.image_to_string(img_enhanced, lang='hin+eng') + "\n\n"
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
        elif ext in ('.png', '.jpg', '.jpeg', '.tiff', '.tif', '.heic', '.heif', '.webp'):
            image = Image.open(file_path).convert('L')
            image = ImageEnhance.Contrast(image).enhance(2.5)
            full_text_img = pytesseract.image_to_string(image, lang='hin+eng')
            raw_blocks = [b.replace('\n', ' ').strip() for b in re.split(r'\n\s*\n', full_text_img) if b.strip()]
        
        prompt_words = set(reference_text.split()) if reference_text else set()
        units = set()
        for block in raw_blocks:
            cleaned_block = re.sub(r'\s+', ' ', block)
            if not cleaned_block:
                continue
            
            if prompt_words:
                cleaned_block = " ".join([w for w in cleaned_block.split() if w not in prompt_words or len(prompt_words) < 5])
            
            if not cleaned_block.strip():
                continue
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
                if extracted:
                    full_text_pdf += extracted + "\n\n"
            if len(full_text_pdf.strip()) < 15:
                with open(file_path, "rb") as f:
                    pdf_bytes = f.read()
                images = convert_from_bytes(pdf_bytes)
                for img in images:
                    img_gray = img.convert('L')
                    img_enhanced = ImageEnhance.Contrast(img_gray).enhance(2.5)
                    full_text_pdf += pytesseract.image_to_string(img_enhanced, lang='hin+eng') + "\n\n"
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
        elif ext in ('.png', '.jpg', '.jpeg', '.tiff', '.tif', '.heic', '.heif', '.webp'):
            image = Image.open(file_path).convert('L')
            image = ImageEnhance.Contrast(image).enhance(2.5)
            full_text_img = pytesseract.image_to_string(image, lang='hin+eng')
            raw_blocks = [b.replace('\n', ' ').strip() for b in re.split(r'\n\s*\n', full_text_img) if b.strip()]
        
        prompt_words = set(reference_text.split()) if reference_text else set()
        valid_paragraphs = []
        for block in raw_blocks:
            cleaned_block = re.sub(r'\s+', ' ', block)
            if prompt_words:
                cleaned_block = " ".join([w for w in cleaned_block.split() if w not in prompt_words or len(prompt_words) < 5])
            
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned_block) if s.strip()]
            if len(sentences) >= 1 and len(cleaned_block.split()) >= 4:
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
                            if u1 == u2:
                                continue
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
                            if u1 == u2:
                                continue
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
                        for u in common_units:
                            report_content += u + "\n\n"
                        
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
                        for p in common_paras:
                            report_content += p + "\n\n" + "="*50 + "\n\n"
                        
                        st.session_state.deep_result_type = "paragraphs"
                        st.session_state.deep_count = len(common_paras)
                        st.session_state.deep_report_content = report_content
                        st.session_state.deep_filename = "common_paragraphs_report.txt"
            
            finally:
                if os.path.exists(path1):
                    os.unlink(path1)
                if os.path.exists(path2):
                    os.unlink(path2)

    if st.session_state.get("deep_result_type") == "empty_sentences":
        st.info("Found 0 matching sentences/lines.")
    elif st.session_state.get("deep_result_type") == "empty_paras":
        st.info("Found 0 matching paragraphs.")
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
        "* **Global Smart Filtering:** Upload an assignment instructions file, prompt, or syllabus once in the sidebar. It persists across modes and automatically strips out shared common boilerplate text from student papers.\n"
        "* **Flexible File Formats & Scanned Handwriting Support:** Fully supports `.docx`, `.pdf`, `.txt`, `.rtf`, `.md`, `.xlsx`, `.xls`, and image formats (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.tif`, `.heic`, `.heif`, `.webp`). For scanned handwritten PDFs or image submissions, APLens automatically applies bilingual **OCR (Optical Character Recognition - Hindi & English)** to extract and compare the handwriting.\n"
        "* **Batch Upload & ZIP Archive Note:** Upload individual files (up to 5MB each), select entire folders directly, or upload batch `.zip` archives (configured up to 100MB for large classes of 90+ submissions).\n"
        "  * ⚠️ *Important ZIP Rule:* If you upload ZIP files for plagiarism checking, **there must be no nested ZIP files inside the uploaded ZIP**. If students submit ZIP files inside the batch archive, the program will not be able to read or check those nested files.\n"
        "* **Plagiarism & Paraphrase Checker:** Calculates cross-document similarity matrices using **TF-IDF cosine similarity** (for exact matching) or **Fuzzy Sequence Matching** (to detect paraphrased rewrites).\n"
        "* **Threshold Flagging & Metrics:** Set custom flagging thresholds in the sidebar to instantly highlight high-risk pairs, view summary metrics counters, and receive automated warning alerts.\n"
        "* **Proportionate Square Heatmap:** An interactive Plotly heatmap dynamically sizes into a proportionate square grid for large classes (e.g., 99 students) with native scrollbars and zoom tools.\n"
        "* **Deep Dive Matcher:** Upload two specific documents or multi-sheet Excel workbooks to perform sheet-by-sheet analysis, exact sentence matching, paragraph comparison, or paraphrase detection.\n"
        "* **Beta Feature - Real Supabase Authentication:** Secure user sign-in and sign-up using Supabase backend accounts.\n"
        "* **Beta Feature - Report History Dashboard:** Store reports temporarily in session state with configurable retention windows (1 day to 1 month)."
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
        "* **Identifying Potential Plagiarism:** Look for high percentage scores off the divider (e.g., matching or exceeding your configured **Flagging Threshold**). A high score "
        "means those two particular student submissions share substantial matching text sequences and warrant a closer manual review."
    )

    st.subheader("4. Support, Contact & Feedback")
    st.write(
        "If you encounter any issues, require assistance, or have ideas on how to make APLens even better, please feel free to reach out. "
        "You can contact **Arun Peswani** for any help required. Your suggestions, feedback, and feature requests are always warmly welcomed!"
    )
