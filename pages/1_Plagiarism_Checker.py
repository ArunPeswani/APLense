import io
import os
import zipfile
import datetime
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
from db_utils import get_valid_db_connection
from auth import enforce_admin_or_whitelisted_access

enforce_admin_or_whitelisted_access()

user_is_logged_in = getattr(st.user, "is_logged_in", False)
user_email = getattr(st.user, "email", "User") if user_is_logged_in else ""
user_name = getattr(st.user, "name", "Google User") if user_is_logged_in else ""

if "reset_count_beta" not in st.session_state:
    st.session_state.reset_count_beta = 0
rc = st.session_state.reset_count_beta

supported_exts = ("docx", "pdf", "txt", "rtf", "md", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "tif", "heic", "heif", "webp")

st.sidebar.subheader("Analysis Settings")
min_words = st.sidebar.slider("Minimum N-Gram Words", min_value=1, max_value=10, value=4, key=f"min_words_{rc}")
max_words = st.sidebar.slider("Maximum N-Gram Words", min_value=1, max_value=10, value=6, key=f"max_words_{rc}")
similarity_threshold = st.sidebar.slider("🚨 Flagging Threshold (%)", min_value=10, max_value=100, value=40, step=5, key=f"sim_threshold_{rc}")
save_reports_toggle = st.sidebar.toggle("💾 Save Generated Reports", value=True, key=f"save_toggle_{rc}")
expiry_date = (datetime.datetime.now() + datetime.timedelta(days=60)).strftime("%Y-%m-%d")

reference_file = st.sidebar.file_uploader(
    "Upload Assignment Instructions/Syllabus (Optional)",
    type=list(supported_exts),
    key=f"global_ref_file_{rc}",
    max_upload_size=5
)

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
    # helper extraction inline or imported
    pass

upload_choice = st.radio("Select Upload Type", ["Individual Files", "Direct Folder Selection", "ZIP Archive (.zip)"], key=f"folder_upload_choice_{rc}")
# (Rest of Plagiarism Checker logic follows directly without any leading elif wrapper)
