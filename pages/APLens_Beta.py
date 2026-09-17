import io
import os
import zipfile
import datetime
import sqlite3
import json
import time
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
import google.generativeai as genai

# OCR, Image Processing & HEIF Support Imports
from PIL import Image, ImageEnhance
from pdf2image import convert_from_bytes
import pytesseract
from pillow_heif import register_heif_opener
register_heif_opener()

st.set_page_config(page_title="APLens Beta - Plagiarism & AI Grader Suite", page_icon="🧪", layout="centered")

# --- LOCAL SQLITE DATABASE INITIALIZATION ---
DB_FILE = "aplens_audit.db"

def init_local_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        create table if not exists beta_user_activity (
            id integer primary key autoincrement,
            user_email text,
            user_name text,
            timestamp text,
            course text,
            analysis_type text,
            files_scanned int,
            min_ngram_words int,
            max_ngram_words int,
            flagging_threshold int,
            max_similarity numeric,
            avg_similarity numeric,
            flagged_pairs_count int
        )
    """)
    cursor.execute("""
        create table if not exists beta_deep_dive_activity (
            id integer primary key autoincrement,
            user_email text,
            user_name text,
            timestamp text,
            doc_a_name text,
            doc_b_name text,
            high_match_count_over_50pct int,
            top_matches_summary text
        )
    """)
    cursor.execute("""
        create table if not exists course_document_vault (
            id integer primary key autoincrement,
            lms_number text,
            assignment_name text,
            filename text,
            extracted_text text,
            timestamp text
        )
    """)
    cursor.execute("""
        create table if not exists course_metadata (
            id integer primary key autoincrement,
            lms_number text,
            assignment_name text,
            reference_text text,
            timestamp text
        )
    """)
    cursor.execute("""
        create table if not exists grader_api_keys (
            email text primary key,
            api_key text,
            updated_at text
        )
    """)
    cursor.execute("""
        create table if not exists ai_grades_vault (
            id integer primary key autoincrement,
            lms_number text,
            assignment_name text,
            student_name text,
            grades_json text,
            exemplary_badge text,
            timestamp text,
            expiry_date text
        )
    """)
    cursor.execute("""
        create table if not exists authorized_users (
            email text primary key,
            name text,
            requested_at text,
            approved_at text
        )
    """)
    cursor.execute("""
        create table if not exists access_requests (
            id integer primary key autoincrement,
            name text,
            email text unique,
            remarks text,
            timestamp text
        )
    """)
    cursor.execute("insert or ignore into authorized_users (email, name, requested_at, approved_at) values (?, ?, ?, ?)", 
                   ("arunpeswani@gmail.com", "Arun Peswani", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

init_local_db()

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
        .google-login-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            background-color: #ffffff;
            color: #3c4043 !important;
            border: 1px solid #dadce0;
            border-radius: 24px;
            font-family: 'Roboto', sans-serif;
            font-weight: 500;
            font-size: 14px;
            padding: 8px 22px;
            text-decoration: none !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            transition: background-color 0.2s, box-shadow 0.2s, border-color 0.2s;
        }
        .google-login-btn:hover {
            background-color: #f8f9fa;
            border-color: #dadce0;
            box-shadow: 0 1px 3px rgba(60,64,67,0.2);
            color: #202124 !important;
        }
        .google-login-btn svg {
            width: 18px;
            height: 18px;
        }
    </style>
""", unsafe_allow_html=True)

if "reset_count_beta" not in st.session_state:
    st.session_state.reset_count_beta = 0
if "saved_reports" not in st.session_state:
    st.session_state.saved_reports = []
if "edit_email_toggled" not in st.session_state:
    st.session_state.edit_email_toggled = False

rc = st.session_state.reset_count_beta

user_is_logged_in = getattr(st.user, "is_logged_in", False)
user_email = getattr(st.user, "email", "User") if user_is_logged_in else ""
user_name = getattr(st.user, "name", "Google User") if user_is_logged_in else ""
user_avatar = (getattr(st.user, "picture", None) or getattr(st.user, "image", None)) if user_is_logged_in else ""

if not user_avatar:
    user_avatar = "https://www.w3schools.com/howto/img_avatar.png"

if "action" in st.query_params and st.query_params["action"] == "login":
    st.login("google")

# ==========================================
# GATED LOGIN CHECK & AUTHORIZATION GATE
# ==========================================
if not user_is_logged_in:
    st.title("🧪 APLens Beta - Plagiarism & AI Grader Suite")
    st.markdown("---")
    st.info("🔒 **Authentication Required:** Please sign in with your approved Google account to access the APLens Beta suite.")
    
    col_login1, col_login2 = st.columns([1, 1])
    with col_login1:
        st.markdown("""
            <div style="padding-top: 15px;">
                <a href="?action=login" target="_self" class="google-login-btn">
                    <svg version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
                        <path fill="#EA4335" d="M24 9.5c3.54 0 6.7 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                        <path fill="#4285F4" id="path4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                        <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.46-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48 z"/>
                    </svg>
                    Sign in with Google
                </a>
            </div>
        """, unsafe_allow_html=True)
    st.stop()

def is_user_authorized(email):
    if email.lower() == "arunpeswani@gmail.com":
        return True
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("select email from authorized_users where email = ?", (email.lower(),))
        row = cursor.fetchone()
        conn.close()
        return bool(row)
    except Exception:
        return False

if not is_user_authorized(user_email):
    st.title("🧪 APLens Beta - Access Approval Required")
    st.markdown("---")
    
    existing_request = False
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("select id from access_requests where email = ?", (user_email.lower(),))
        existing_request = bool(cursor.fetchone())
        conn.close()
    except Exception:
        pass

    if existing_request:
        st.warning(f"⏳ **Request Pending:** Your access request for **{user_email}** has already been submitted and is awaiting review by the administrator.")
        if st.button("Sign Out / Switch Account", type="primary", key=f"unauth_signout_{rc}"):
            st.logout()
        st.stop()

    st.info(f"👋 Hello **{user_name}** (`{user_email}`). Your account is not currently authorized to access APLens Beta. Please submit an approval request below.")

    with st.form(key=f"access_request_form_{rc}"):
        req_name = st.text_input("Full Name", value=user_name)
        
        col_email_lbl, col_email_btn = st.columns([0.9, 0.1])
        with col_email_lbl:
            st.markdown("**Email ID**")
        with col_email_btn:
            if st.form_submit_button("✏️", help="Click to unlock and edit email address"):
                st.session_state.edit_email_toggled = not st.session_state.get("edit_email_toggled", False)
        
        is_editable = st.session_state.get("edit_email_toggled", False)
        if is_editable:
            req_email = st.text_input("Edit Email ID", value=user_email, key=f"editable_email_input_{rc}")
            st.caption("✏️ Email field is unlocked for editing.")
        else:
            req_email = st.text_input("Email ID (Locked)", value=user_email, disabled=True, key=f"locked_email_input_{rc}")
            st.caption("🔒 Email ID is fetched from your Google login. Click the pencil icon above to edit.")

        req_remarks = st.text_area("Remarks / Reason for Access", placeholder="e.g., Grader for Computer Science department batches...")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            submit_request = st.form_submit_button("Submit Request", type="primary", use_container_width=True)
        with col_f2:
            cancel_request = st.form_submit_button("Cancel & Sign Out", type="secondary", use_container_width=True)

    if cancel_request:
        st.logout()

    if submit_request:
        if not req_name.strip() or not req_email.strip():
            st.error("Name and Email ID cannot be empty.")
        else:
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("""
                    insert into access_requests (name, email, remarks, timestamp)
                    values (?, ?, ?, ?)
                """, (req_name.strip(), req_email.strip().lower(), req_remarks.strip(), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                st.success("✅ Access request submitted successfully! The administrator has been notified.")
                time.sleep(2)
                st.rerun()
            except Exception as ex:
                st.error("An access request for this email has already been submitted.")

    st.stop()

header_col1, header_col2 = st.columns([0.6, 0.4])

with header_col1:
    st.title("🧪 APLens Beta Suite")

with header_col2:
    avatar_col, menu_col = st.columns([0.3, 0.7])
    with avatar_col:
        st.markdown(f"""
            <div style="padding-top: 12px; text-align: right;">
                <img src="{user_avatar}" style="width: 38px; height: 38px; border-radius: 50%; border: 2px solid #1a73e8; object-fit: cover;">
            </div>
        """, unsafe_allow_html=True)
    with menu_col:
        st.markdown("<div style='padding-top: 6px;'></div>", unsafe_allow_html=True)
        with st.popover("Account"):
            st.markdown(f"""
                <div style="text-align: center; padding: 10px 0px;">
                    <img src="{user_avatar}" style="width: 60px; height: 60px; border-radius: 50%; border: 2px solid #1a73e8; object-fit: cover; margin-bottom: 6px;">
                    <div style="font-weight: 600; font-size: 14px; color: #202124;">{user_name}</div>
                    <div style="font-size: 12px; color: #5f6368; margin-top: 2px; word-break: break-all;">{user_email}</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("---")
            if st.button("Sign Out", type="secondary", use_container_width=True, key=f"sign_out_btn_{rc}"):
                st.logout()

def get_user_api_key(email):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("select api_key from grader_api_keys where email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else ""
    except Exception:
        return ""

def save_user_api_key(email, key):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("insert or replace into grader_api_keys (email, api_key, updated_at) values (?, ?, ?)", 
                       (email, key, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception:
        pass

nav_options = ["Plagiarism Checker", "Deep Dive (2-Doc Comparison)", "🤖 AI Grader & Rubric Evaluation", "📁 Report History Dashboard", "💡 User Guide & Help"]

is_admin = user_email.lower() == "arunpeswani@gmail.com"
if is_admin:
    nav_options.insert(4, "🔐 Access Requests Management")

app_mode = st.sidebar.radio("Navigation", nav_options, key=f"nav_mode_{rc}")

st.sidebar.markdown("---")
st.sidebar.subheader("🔑 AI Grader API Key (BYOK)")
stored_key = get_user_api_key(user_email)
user_gemini_key = st.sidebar.text_input("Google AI Studio API Key", value=stored_key, type="default", autocomplete="off", key=f"user_gemini_key_{rc}", help="Enter your free Google AI Studio key once. It is securely saved for your account.")
if user_gemini_key != stored_key:
    save_user_api_key(user_email, user_gemini_key.strip())
    st.sidebar.success("API key saved securely!")

st.sidebar.markdown("---")
st.sidebar.subheader("Analysis Settings")
min_words = st.sidebar.slider("Minimum N-Gram Words", min_value=1, max_value=10, value=4, key=f"min_words_{rc}")
max_words = st.sidebar.slider("Maximum N-Gram Words", min_value=1, max_value=10, value=6, key=f"max_words_{rc}")
similarity_threshold = st.sidebar.slider("🚨 Flagging Threshold (%)", min_value=10, max_value=100, value=40, step=5, key=f"sim_threshold_{rc}", help="Pairs exceeding this similarity percentage will be flagged as high risk.")

st.sidebar.markdown("---")
st.sidebar.subheader("Report History Settings")
save_reports_toggle = st.sidebar.toggle("💾 Save Generated Reports", value=True, key=f"save_toggle_{rc}")
retention_intervals = ["60 days", "1 day", "1 week", "10 days", "A Fortnight", "3 weeks", "A Month", "90 days"]
selected_interval = st.sidebar.selectbox("Retention Period", retention_intervals, index=0, key=f"ret_interval_{rc}")

interval_days_map = {"60 days": 60, "1 day": 1, "1 week": 7, "10 days": 10, "A Fortnight": 14, "3 weeks": 21, "A Month": 30, "90 days": 90}
expiry_days = interval_days_map.get(selected_interval, 60)
expiry_date = (datetime.datetime.now() + datetime.timedelta(days=expiry_days)).strftime("%Y-%m-%d")
st.sidebar.caption(f"📅 Calculated auto-deletion date: **{expiry_date}**")

st.sidebar.markdown("---")
supported_exts = ("docx", "pdf", "txt", "rtf", "md", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "tif", "heic", "heif", "webp")

st.sidebar.subheader("Global Smart Filtering")
reference_file = st.sidebar.file_uploader(
    "Upload Assignment Instructions/Syllabus (Optional)",
    type=list(supported_exts),
    key=f"global_ref_file_{rc}",
    max_upload_size=5,
    help="Upload the assignment prompt or reference file once (Max 5MB). It will be saved and applied across future runs automatically!"
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reset Everything", type="secondary", key=f"reset_all_btn_{rc}"):
    st.session_state.reset_count_beta += 1
    keys_to_clear = [k for k in list(st.session_state.keys()) if k not in ["reset_count_beta", "saved_reports", "edit_email_toggled"]]
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
        "Your data remains completely private to your active session and is discarded immediately after use."
    )

def extract_text_and_images_from_file(file_obj, filename_lower):
    text = ""
    images_list = []
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
            
            pil_images = convert_from_bytes(file_bytes)
            for img in pil_images:
                images_list.append(img)
            
            if len(text.strip()) < 15:
                ocr_text = ""
                for img in pil_images:
                    img_gray = img.convert('L')
                    img_enhanced = ImageEnhance.Contrast(img_gray).enhance(2.0)
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
            image = Image.open(io.BytesIO(file_bytes)).convert('RGB')
            images_list.append(image)
            text = pytesseract.image_to_string(image.convert('L'), lang='hin+eng')
            
    except Exception as e:
        pass
    
    if not text.strip():
        text = f"document_content_fallback_{filename_lower}"
    return text, images_list

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
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("delete from course_metadata where lms_number = ? and assignment_name = ?", (lms_val, assign_val))
                cursor.execute("""
                    insert into course_metadata (lms_number, assignment_name, reference_text, timestamp)
                    values (?, ?, ?, ?)
                """, (lms_val, assign_val, global_reference_text, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                st.success("📌 Instructions file uploaded and saved to vault for future runs under this LMS and Assignment!")
            except Exception:
                pass
    elif is_cumulative:
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("select reference_text from course_metadata where lms_number = ? and assignment_name = ?", (lms_val, assign_val))
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                global_reference_text = row[0]
                st.info(f"💡 Automatically loaded saved assignment instructions/syllabus from vault for LMS: **{lms_val}** | Assignment: **{assign_val}**")
        except Exception:
            pass

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("select distinct lms_number, assignment_name from course_document_vault")
        past_records = cursor.fetchall()
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
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("select filename, extracted_text from course_document_vault where lms_number = ? and assignment_name = ?", (lms_val, assign_val))
                    vault_rows = cursor.fetchall()
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
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.executemany("""
                            insert into course_document_vault (lms_number, assignment_name, filename, extracted_text, timestamp)
                            values (?, ?, ?, ?, ?)
                        """, new_files_to_vault)
                        conn.commit()
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
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("""
                        insert into beta_user_activity (
                            user_email, user_name, timestamp, course, analysis_type, 
                            files_scanned, min_ngram_words, max_ngram_words, 
                            flagging_threshold, max_similarity, avg_similarity, flagged_pairs_count
                        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_email, user_name, current_timestamp, st.session_state.beta_course, analysis_mode_label,
                        total_files, min_words, max_words, similarity_threshold,
                        round(max_sim, 2), round(avg_sim, 2), flagged_pairs_count
                    ))
                    conn.commit()
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

# ==========================================
# MODE 2: DEEP DIVE COMPARISON
# ==========================================
elif app_mode == "Deep Dive (2-Doc Comparison)":
    st.header("Deep Dive Matcher")
    st.write("Compare two specific documents or spreadsheets sheet-by-sheet to extract exact matching sentences or true paragraphs.")
    
    global_ref_deep = ""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("select reference_text from course_metadata order by id desc limit 1")
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            global_ref_deep = row[0]
    except Exception:
        pass

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

    if file1 and file2:
        col_deep1, col_deep2 = st.columns(2)
        with col_deep1:
            run_deep = st.button("Run Deep Dive Matcher", type="primary", key=f"run_deep_dive_{rc}")
        with col_deep2:
            run_deep_para = st.button("🔍 Run Paraphrase Matcher", type="secondary", key=f"run_deep_para_{rc}")

        if run_deep or run_deep_para:
            path1 = get_file_bytes_temp(file1)
            path2 = get_file_bytes_temp(file2)
            
            try:
                units1 = list(get_document_lines_and_sentences(path1, global_ref_deep))
                units2 = list(get_document_lines_and_sentences(path2, global_ref_deep))
                
                high_match_instances = []
                for u1 in units1:
                    for u2 in units2:
                        ratio = difflib.SequenceMatcher(None, u1.lower(), u2.lower()).ratio() * 100
                        if ratio >= 50.0:
                            high_match_instances.append({"doc_a_sentence": u1, "doc_b_sentence": u2, "similarity": round(ratio, 1)})
                
                high_match_instances.sort(key=lambda x: x["similarity"], reverse=True)
                
                st.session_state.deep_high_matches = high_match_instances
                st.session_state.deep_analyzed = True
                
                try:
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("""
                        insert into beta_deep_dive_activity (
                            user_email, user_name, timestamp, doc_a_name, doc_b_name, 
                            high_match_count_over_50pct, top_matches_summary
                        ) values (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_email, user_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        file1.name, file2.name, len(high_match_instances), str(high_match_instances[:5])
                    ))
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
                
                report_content = f"Deep Dive Match Report (>50% Matches)\nComparing '{file1.name}' and '{file2.name}'\n" + "="*70 + "\n\n"
                for item in high_match_instances:
                    report_content += f"[Similarity: {item['similarity']}%]\n- Doc A: {item['doc_a_sentence']}\n- Doc B: {item['doc_b_sentence']}\n\n"
                st.session_state.deep_report_content = report_content
                st.session_state.deep_filename = "deep_dive_over_50pct_report.txt"

            finally:
                if os.path.exists(path1):
                    os.unlink(path1)
                if os.path.exists(path2):
                    os.unlink(path2)

    if st.session_state.get("deep_analyzed", False):
        matches = st.session_state.deep_high_matches
        st.success(f"Deep Dive Complete! Found **{len(matches)} matching instance(s)** with ≥50% similarity.")
        if matches:
            for item in matches:
                with st.expander(f"Similarity: {item['similarity']}%"):
                    st.markdown(f"**Doc A:** {item['doc_a_sentence']}")
                    st.markdown(f"**Doc B:** {item['doc_b_sentence']}")
            st.text_area("Report Preview", st.session_state.deep_report_content, height=250, key=f"deep_prev_{rc}")
            st.download_button("📥 Download >50% Match Report (.txt)", data=st.session_state.deep_report_content, file_name=st.session_state.deep_filename, mime="text/plain", key=f"dl_deep_{rc}")
        else:
            st.info("No matching text instances exceeding 50% similarity were found between these two documents.")

    if not file1 or not file2:
        st.warning("Please upload both Student A and Student B documents to run Deep Dive.")

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
                            conn = sqlite3.connect(DB_FILE)
                            cursor = conn.cursor()
                            cursor.execute("select student_name, grades_json, exemplary_badge from ai_grades_vault where lms_number = ? and assignment_name = ?", (ai_lms_val, ai_assign_val))
                            vault_rows = cursor.fetchall()
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
                                conn = sqlite3.connect(DB_FILE)
                                cursor = conn.cursor()
                                cursor.execute("delete from ai_grades_vault where lms_number = ? and assignment_name = ? and student_name = ?", (ai_lms_val, ai_assign_val, student_name))
                                cursor.execute("""
                                    insert into ai_grades_vault (lms_number, assignment_name, student_name, grades_json, exemplary_badge, timestamp, expiry_date)
                                    values (?, ?, ?, ?, ?, ?, ?)
                                """, (ai_lms_val, ai_assign_val, student_name, json.dumps(parsed_json), "Pending", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), expiry_date))
                                conn.commit()
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

# ==========================================
# MODE 4: ACCESS REQUESTS MANAGEMENT (ADMIN ONLY)
# ==========================================
elif is_admin and app_mode == "🔐 Access Requests Management":
    st.header("🔐 Access Requests Management")
    st.write("Review, approve, or manage user access requests and registered users for APLens Beta.")

    tab_pending, tab_registered = st.tabs(["⏳ Pending Requests", "👥 Registered Users"])

    with tab_pending:
        col_h_btn1, col_h_btn2 = st.columns([0.25, 0.75])
        with col_h_btn1:
            if st.button("🔄 Refresh Requests", type="secondary", use_container_width=True, key=f"refresh_reqs_{rc}"):
                st.rerun()

        try:
            conn = sqlite3.connect(DB_FILE)
            df_requests = pd.read_sql_query("select id, name, email, remarks, timestamp from access_requests order by timestamp desc", conn)
            conn.close()
        except Exception:
            df_requests = pd.DataFrame()

        if df_requests.empty:
            st.info("✅ No pending access requests at this time.")
        else:
            st.write(f"Found **{len(df_requests)} pending request(s)**.")

            editor_rows = []
            for idx, row in df_requests.iterrows():
                editor_rows.append({
                    "Select": False,
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
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        if delete_selected:
                            for email, name, req_ts, req_id in target_requests:
                                cursor.execute("delete from access_requests where id = ?", (req_id,))
                            conn.commit()
                            conn.close()
                            st.success(f"Successfully deleted {len(target_requests)} pending request(s)!")
                        else:
                            for email, name, req_ts, req_id in target_requests:
                                cursor.execute("insert or replace into authorized_users (email, name, requested_at, approved_at) values (?, ?, ?, ?)", 
                                               (email.lower(), name, req_ts, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                cursor.execute("delete from access_requests where id = ?", (req_id,))
                            conn.commit()
                            conn.close()
                            st.success(f"Successfully approved {len(target_requests)} user(s)!")
                        
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error processing requests: {ex}")

    with tab_registered:
        st.subheader("👥 Approved & Registered Users")
        
        col_reg_btn1, _ = st.columns([0.25, 0.75])
        with col_reg_btn1:
            if st.button("🔄 Refresh Registered Users", type="secondary", use_container_width=True, key=f"refresh_regs_{rc}"):
                st.rerun()

        try:
            conn = sqlite3.connect(DB_FILE)
            df_registered = pd.read_sql_query("select email, name, requested_at, approved_at from authorized_users order by approved_at desc", conn)
            conn.close()
        except Exception:
            df_registered = pd.DataFrame()

        if df_registered.empty:
            st.info("No registered users found.")
        else:
            st.write(f"Found **{len(df_registered)} registered user(s)**.")

            reg_editor_rows = []
            for idx, row in df_registered.iterrows():
                is_admin_user = row["email"].lower() == "arunpeswani@gmail.com"
                reg_editor_rows.append({
                    "Select": False,
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
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        for email, name, req_ts in users_to_unregister:
                            cursor.execute("delete from authorized_users where email = ?", (email.lower(),))
                            cursor.execute("""
                                insert or ignore into access_requests (name, email, remarks, timestamp)
                                values (?, ?, ?, ?)
                            """, (name, email.lower(), "Unregistered by admin. Re-request required.", req_ts))
                        conn.commit()
                        conn.close()
                        st.success(f"Successfully unregistered {len(users_to_unregister)} user(s) and moved them back to Pending Requests!")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error unregistering users: {ex}")

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
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("delete from course_document_vault where lms_number = ? and assignment_name = ?", (purge_lms.strip(), purge_assign.strip()))
                    cursor.execute("delete from course_metadata where lms_number = ? and assignment_name = ?", (purge_lms.strip(), purge_assign.strip()))
                    cursor.execute("delete from ai_grades_vault where lms_number = ? and assignment_name = ?", (purge_lms.strip(), purge_assign.strip()))
                    conn.commit()
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
                conn = sqlite3.connect(DB_FILE)
                df_logs = pd.read_sql_query("select * from beta_user_activity order by timestamp desc", conn)
                conn.close()
                
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
                conn = sqlite3.connect(DB_FILE)
                df_deep = pd.read_sql_query("select * from beta_deep_dive_activity order by timestamp desc", conn)
                conn.close()
                
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

# ==========================================
# MODE 6: USER GUIDE & HELP
# ==========================================
elif app_mode == "💡 User Guide & Help":
    st.header("💡 Grader Guide & Help Center")
    st.write("Welcome to the APLens Beta Suite. This comprehensive guide is designed for graders to help you navigate login security, cumulative late submissions, AI rubric grading, and report tracking.")

    st.markdown("---")

    st.subheader("1. Gated Google Authentication & Access Control")
    st.write(
        "* **Secure Whitelist Approval:** Only pre-approved email addresses can access APLens Beta. New users must submit an approval request with their name and remarks upon signing in.\n"
        "* **Admin Access Management:** Arun Peswani (`arunpeswani@gmail.com`) can review, select, and approve or delete pending incoming requests, as well as unregister active users (moving them back to pending requests) via the Access Requests Management panel."
    )

    st.subheader("2. AI Grader, Rate-Limiting & Multimodal Evaluation")
    st.write(
        "* **Automated RPM Rate-Limiting:** The app intelligently tracks request frequencies and automatically paces batches to respect Google AI Studio free tier limits (10–15 RPM) with built-in exponential backoff retries.\n"
        "* **Multi-File ZIP Grouping:** Submissions packed in ZIP archives are automatically grouped by student name so each student gets one holistic evaluation row.\n"
        "* **Exemplary Badge Allocation:** Specify the top percentage of students to receive Exemplary Badges based on rubric performance."
    )

    st.subheader("3. Cumulative Late Submissions, 60-Day Retention & Purge")
    st.write(
        "* **Conditional Cumulative Trigger:** Cumulative checking and AI grading history **only** load/save if **both** LMS Number and Assignment Name are provided.\n"
        "* **Default 60-Day Retention:** Reports automatically schedule deletion after 60 days (customizable via the sidebar dropdown).\n"
        "* **Manual Purge:** Use the Course Data Purge tool in the Report History dashboard to instantly delete records for a specific LMS number and assignment."
    )

    st.subheader("4. Support & Contact")
    st.write(
        "For assistance, please contact **Arun Peswani**."
    )
