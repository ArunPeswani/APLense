import io
import os
import zipfile
import datetime
import json
import time
import streamlit as st
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai

from db_utils import get_valid_db_connection
from auth import enforce_admin_or_whitelisted_access

enforce_admin_or_whitelisted_access()

if "reset_count_beta" not in st.session_state:
    st.session_state.reset_count_beta = 0
rc = st.session_state.reset_count_beta
supported_exts = ("docx", "pdf", "txt", "rtf", "md", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "tif", "heic", "heif", "webp")

st.header("🤖 AI Grader & Rubric Evaluation Suite")
st.write("Upload assignment instructions, a grading rubric, and student submission files for evaluation.")

user_gemini_key = st.sidebar.text_input("Google AI Studio API Key", type="password", key=f"user_gemini_key_{rc}")

if not user_gemini_key.strip():
    st.warning("⚠️ Please enter your Google AI Studio API Key in the sidebar.")
else:
    col_ai_lms1, col_ai_lms2 = st.columns(2)
    with col_ai_lms1: ai_lms_input = st.text_input("🏫 LMS Number", key=f"ai_lms_{rc}")
    with col_ai_lms2: ai_assign_input = st.text_input("📝 Assignment Name", key=f"ai_assign_{rc}")

    rubric_file = st.file_uploader("Upload Grading Rubric", type=list(supported_exts), key=f"ai_rubric_{rc}")
    instructions_file = st.file_uploader("Upload Assignment Instructions", type=list(supported_exts), key=f"ai_instructions_{rc}")
    
    st.info("Configure settings above to run student batch grading.")
