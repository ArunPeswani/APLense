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

st.set_page_config(page_title="APLens - Beta Testing Suite", page_icon="🧪", layout="wide")

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
if "beta_reset_count" not in st.session_state:
    st.session_state.beta_reset_count = 0
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "user_provider" not in st.session_state:
    st.session_state.user_provider = ""
if "saved_reports" not in st.session_state:
    st.session_state.saved_reports = []

rc = st.session_state.beta_reset_count

# Handle login query parameters from custom buttons
params = st.query_params
if "login" in params:
    provider = params["login"].capitalize()
    st.session_state.logged_in = True
    st.session_state.user_provider = provider
    st.query_params.clear()
    st.rerun()

# ==========================================
# TOP HEADER & OPTIONAL LOGIN BAR
# ==========================================
header_col1, header_col2 = st.columns([0.75, 0.25])

with header_col1:
    st.title("🧪 APLens - Beta Testing Suite")

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
            
            st.markdown("""
                <div class="login-container">
                    <a href="?login=google" target="_self" class="social-login-btn">
                        <svg viewBox="0 0 24 24"><path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"/><path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.13 0-5.78-2.11-6.73-4.96H1.18v3.15C3.15 21.32 7.22 24 12 24z"/><path fill="#FBBC05" d="M5.27 14.24c-.25-.72-.38-1.49-.38-2.24s.13-1.52.38-2.24V6.61H1.18C.43 8.13 0 9.87 0 11.75s.43 3.62 1.18 5.14l4.09-3.15z"/><path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.22 0 3.15 2.68 1.18 6.61l4.09 3.15c.95-2.85 3.6-4.96 6.73-4.96z"/></svg>
                        Sign in with Google
                    </a>
                    <a href="?login=microsoft" target="_self" class="social-login-btn">
                        <svg viewBox="0 0 23 23"><path fill="#f35325" d="M1 1h10v10H1z"/><path fill="#81bc06" d="M12 1h10v10H12z"/><path fill="#05a6f0" d="M1 12h10v10H1z"/><path fill="#ffba08" d="M12 12h10v10H12z"/></svg>
                        Sign in with Microsoft
                    </a>
                    <a href="?login=apple" target="_self" class="social-login-btn">
                        <svg viewBox="0 0 170 170"><path fill="#000000" d="M150.37 130.25c-2.45 5.66-5.35 10.87-8.71 15.66-4.58 6.53-8.33 11.05-11.22 13.56-4.48 4.12-9.28 6.23-14.42 6.35-3.69 0-8.14-1.05-13.32-3.18-5.19-2.12-9.97-3.17-14.34-3.17-4.58 0-9.49 1.05-14.75 3.17-5.26 2.13-9.5 3.24-12.74 3.35-4.35.13-9.16-1.9-14.42-6.08-3.59-2.92-7.5-7.66-11.73-14.22-6.2-9.73-11.17-20.4-14.91-32.02-3.75-11.62-5.62-22.7-5.62-33.23 0-14.35 3.75-26.04 11.24-35.07 7.5-9.03 16.74-13.62 27.72-13.78 4.9 0 10.3 1.25 16.2 3.75 5.89 2.5 9.77 3.76 11.63 3.76 1.52 0 5.6-1.39 12.24-4.17 6.64-2.77 12.58-4.02 17.82-3.75 16.2.76 28.77 7.02 37.71 18.78-14.12 8.68-21.05 20.27-20.78 34.78.27 12.04 5.09 21.84 14.45 29.39 4.35 3.59 9.4 6.13 15.16 7.64-1.95 5.66-4.34 11.2-7.18 16.63z"/></svg>
                        Sign in with Apple
                    </a>
                    <a href="?login=facebook" target="_self" class="social-login-btn">
                        <svg viewBox="0 0 24 24"><path fill="#1877F2" d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
                        Sign in with Facebook
                    </a>
                    <a href="?login=linkedin" target="_self" class="social-login-btn">
                        <svg viewBox="0 0 24 24"><path fill="#0A66C2" d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>
                        Sign in with LinkedIn
                    </a>
                </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# SIDEBAR SETUP
# ==========================================
nav_options = ["Plagiarism Checker", "Deep Dive (2-Doc Comparison)", "📁 Report History Dashboard", "💡 User Guide & Help"]
app_mode = st.sidebar.radio("Navigation", nav_options, key=f"beta_nav_{rc}")

st.sidebar.markdown("---")

st.sidebar.subheader("Analysis Settings")
min_words = st.sidebar.slider("Minimum N-Gram Words", 1, 10, 4, key=f"beta_min_{rc}")
max_words = st.sidebar.slider("Maximum N-Gram Words", 1, 10, 6, key=f"beta_max_{rc}")
similarity_threshold = st.sidebar.slider("🚨 Flagging Threshold (%)", 10, 100, 40, step=5, key=f"beta_thresh_{rc}")

st.sidebar.markdown("---")

st.sidebar.subheader("Report History Settings")
if st.session_state.logged_in:
    save_reports_toggle = st.sidebar.toggle("💾 Save Generated Reports", value=True, key=f"beta_save_{rc}")
    retention_intervals = ["1 day", "1 week", "10 days", "A Fortnight", "3 weeks", "A Month"]
    selected_interval = st.sidebar.selectbox("Retention Period", retention_intervals, index=1, key=f"beta_ret_{rc}")
    interval_days_map = {"1 day": 1, "1 week": 7, "10 days": 10, "A Fortnight": 14, "3 weeks": 21, "A Month": 30}
    expiry_date = (datetime.datetime.now() + datetime.timedelta(days=interval_days_map.get(selected_interval, 7))).strftime("%Y-%m-%d")
    st.sidebar.caption(f"📅 Auto-deletion date: **{expiry_date}**")
else:
    save_reports_toggle = False
    st.sidebar.info("💡 **Sign in** (via top-right icon) to enable automated report history storage.")

st.sidebar.markdown("---")

reference_file = st.sidebar.file_uploader(
    "Upload Assignment Instructions/Syllabus (Optional)",
    type=["docx", "pdf", "txt", "rtf", "md", "xlsx", "xls"],
    key=f"beta_ref_{rc}",
    max_upload_size=5
)

st.sidebar.markdown("---")

if st.sidebar.button("🔄 Reset Beta Session", type="secondary"):
    st.session_state.beta_reset_count += 1
    keys_to_clear = [k for k in list(st.session_state.keys()) if k not in ["beta_reset_count", "logged_in", "user_email", "user_provider", "saved_reports"]]
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
                tokens = [str(val).strip() for val in df.values.flatten() if pd.notna(val) and str(val).strip().lower() != 'nan']
                text += f" [Sheet: {sheet_name}] " + " ".join(tokens) + " "
    except Exception:
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
    st.header("File Similarity Matrix Analysis (Beta)")
    course_assignment_name = st.text_input("📚 Course Name / Assignment Title", placeholder="e.g., CS101 - Final Research Paper", key=f"beta_course_{rc}")
    st.write("Upload multiple student submissions below.")

    upload_choice = st.radio("Select Upload Type", ["Individual Files", "Direct Folder Selection", "ZIP Archive (.zip)"], key=f"beta_upload_choice_{rc}")

    raw_uploaded_files, directory_uploaded_files, zip_uploaded_file = [], [], None
    supported_exts = ("docx", "pdf", "txt", "rtf", "md", "xlsx", "xls")

    if upload_choice == "Individual Files":
        raw_uploaded_files = st.file_uploader("Upload Student Documents", type=list(supported_exts), accept_multiple_files=True, max_upload_size=5, key=f"beta_indiv_{rc}")
    elif upload_choice == "Direct Folder Selection":
        directory_uploaded_files = st.file_uploader("Select Folder", type=list(supported_exts), accept_multiple_files="directory", max_upload_size=5, key=f"beta_dir_{rc}")
    else:
        zip_uploaded_file = st.file_uploader("Upload ZIP Archive", type=["zip"], max_upload_size=100, key=f"beta_zip_{rc}")

    processed_files = []
    if upload_choice == "Individual Files" and raw_uploaded_files:
        processed_files = raw_uploaded_files
    elif upload_choice == "Direct Folder Selection" and directory_uploaded_files:
        processed_files = [f for f in directory_uploaded_files if f.name.lower().endswith(supported_exts) and '__MACOSX' not in f.name]
    elif upload_choice == "ZIP Archive (.zip)" and zip_uploaded_file:
        try:
            with zipfile.ZipFile(zip_uploaded_file, 'r') as z:
                for filename in z.namelist():
                    if filename.lower().endswith(supported_exts) and not filename.startswith('__MACOSX/'):
                        with z.open(filename) as f:
                            fb = io.BytesIO(f.read())
                            fb.name = os.path.basename(filename)
                            if fb.name: processed_files.append(fb)
        except Exception as e:
            st.error(f"Could not read ZIP: {e}")

    if processed_files:
        st.info(f"Loaded {len(processed_files)} file(s) successfully.")
        c1, c2 = st.columns(2)
        with c1: run_standard = st.button("Run Plagiarism Analysis", type="primary", key=f"beta_run_std_{rc}")
        with c2: run_paraphrase = st.button("🔍 Run Paraphrase Analysis", type="secondary", key=f"beta_run_para_{rc}")

        if run_standard or run_paraphrase:
            if len(processed_files) < 2:
                st.error("Please upload at least 2 documents.")
            else:
                analysis_mode_label = "Paraphrased Plagiarism Analysis" if run_paraphrase else "Standard Plagiarism Analysis"
                documents, filenames = [], []
                for file in processed_files:
                    file.seek(0)
                    txt = extract_text_from_file_obj(file, file.name.lower())
                    if txt.strip():
                        if global_reference_text.strip():
                            prompt_words = set(global_reference_text.split())
                            cleaned = " ".join([w for w in txt.split() if w not in prompt_words or len(prompt_words) < 5])
                            if len(cleaned.strip()) > 50: txt = cleaned
                        documents.append(txt)
                        filenames.append(file.name)
                
                n = len(documents)
                similarity_matrix = [[0.0]*n for _ in range(n)]
                if run_paraphrase:
                    for i in range(n):
                        for j in range(n):
                            if i == j: similarity_matrix[i][j] = 100.0
                            else:
                                s = difflib.SequenceMatcher(None, documents[i].lower(), documents[j].lower())
                                w1, w2 = set(documents[i].lower().split()), set(documents[j].lower().split())
                                jaccard = len(w1.intersection(w2)) / max(len(w1.union(w2)), 1)
                                similarity_matrix[i][j] = min(round(((s.ratio() * 0.5) + (jaccard * 0.5)) * 140, 2), 100.0)
                else:
                    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(min_words, max_words), max_features=10000)
                    similarity_matrix = (cosine_similarity(vectorizer.fit_transform(documents)) * 100).tolist()

                df = pd.DataFrame(similarity_matrix, index=filenames, columns=filenames)
                st.session_state.beta_df = df
                st.session_state.beta_matrix = similarity_matrix
                st.session_state.beta_filenames = filenames
                st.session_state.beta_analyzed = True
                st.session_state.beta_run_label = analysis_mode_label
                st.session_state.beta_course = course_assignment_name.strip() or "Unnamed Assignment"

                if st.session_state.logged_in and save_reports_toggle:
                    st.session_state.saved_reports.append({
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "type": analysis_mode_label,
                        "course": st.session_state.beta_course,
                        "files_count": len(filenames),
                        "df": df,
                        "matrix": similarity_matrix,
                        "filenames": filenames,
                        "expiry": expiry_date
                    })
                st.rerun()

    if st.session_state.get("beta_analyzed", False):
        df = st.session_state.beta_df
        sm = st.session_state.beta_matrix
        fns = st.session_state.beta_filenames
        r_label = st.session_state.beta_run_label
        c_name = st.session_state.beta_course

        st.success(f"{r_label} Complete for: **{c_name}**!")
        flat = [sm[i][j] for i in range(len(fns)) for j in range(len(fns)) if i != j]
        flagged = sum(1 for sc in flat if sc >= similarity_threshold)

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("📁 Files Scanned", len(fns))
        mc2.metric("📈 Max Similarity", f"{(max(flat) if flat else 0):.1f}%")
        mc3.metric("📊 Average Similarity", f"{(sum(flat)/len(flat) if flat else 0):.1f}%")
        mc4.metric(f"🚨 Flagged (≥{similarity_threshold}%)", flagged)

        fig = go.Figure(data=go.Heatmap(z=sm, x=fns, y=fns, colorscale="Reds", zmin=0, zmax=100))
        fig.update_layout(height=650, yaxis=dict(autorange='reversed'))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df.style.format("{:.2f}%"))

# ==========================================
# MODE 2: DEEP DIVE
# ==========================================
elif app_mode == "Deep Dive (2-Doc Comparison)":
    st.header("Deep Dive Matcher (Beta)")
    st.write("Compare two specific documents.")
    col1, col2 = st.columns(2)
    file1 = col1.file_uploader("Student A Document", type=["docx", "pdf", "txt", "xlsx"], key=f"beta_d1_{rc}")
    file2 = col2.file_uploader("Student B Document", type=["docx", "pdf", "txt", "xlsx"], key=f"beta_d2_{rc}")
    if file1 and file2:
        st.info("Upload complete. Ready for deep dive comparisons.")

# ==========================================
# MODE 3: REPORT HISTORY DASHBOARD
# ==========================================
elif app_mode == "📁 Report History Dashboard":
    st.header("📁 Saved Report History Dashboard")
    if not st.session_state.logged_in:
        st.warning("🔒 Please sign in using the **Sign In** button at the top right to access and view your saved report history.")
    else:
        if not st.session_state.saved_reports:
            st.info("No reports saved yet. Enable the save toggle and run an analysis!")
        else:
            if st.button("🗑️ Clear All Saved History"):
                st.session_state.saved_reports = []
                st.rerun()
            for idx, rep in enumerate(reversed(st.session_state.saved_reports)):
                with st.expander(f"📌 [{rep['timestamp']}] Course: {rep['course']} — Type: {rep['type']}"):
                    st.dataframe(rep['df'].style.format("{:.2f}%"), height=150)

# ==========================================
# MODE 4: USER GUIDE
# ==========================================
elif app_mode == "💡 User Guide & Help":
    st.header("💡 Beta Testing Guide")
    st.write("Welcome to the APLens Beta Testing environment. Here we test experimental social logins, custom course tagging, and session history management.")
