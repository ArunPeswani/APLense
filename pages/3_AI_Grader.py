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

# --- RESTRICT TO ADMIN ONLY ---
user_email = getattr(st.user, "email", "")
if user_email.lower() != "arunpeswani@gmail.com":
    st.error("Access Denied. The AI Grader suite is currently restricted to the administrator.")
    st.stop()

user_is_logged_in = getattr(st.user, "is_logged_in", False)
user_email = getattr(st.user, "email", "User") if user_is_logged_in else ""
user_name = getattr(st.user, "name", "Google User") if user_is_logged_in else ""

if "reset_count_beta" not in st.session_state:
    st.session_state.reset_count_beta = 0
rc = st.session_state.reset_count_beta
supported_exts = ("docx", "pdf", "txt", "rtf", "md", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "tif", "heic", "heif", "webp")

@st.cache_data(ttl=300)
def get_user_api_key(email):
    try:
        conn = get_valid_db_connection()
        if not conn: return ""
        cursor = conn.cursor()
        cursor.execute("select api_key from grader_api_keys where email = %s", (email,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row[0] if row else ""
    except Exception:
        return ""

def save_user_api_key(email, key):
    try:
        conn = get_valid_db_connection()
        if not conn: return
        cursor = conn.cursor()
        cursor.execute("""
            insert into grader_api_keys (email, api_key, updated_at) 
            values (%s, %s, %s) 
            on conflict (email) do update set api_key = EXCLUDED.api_key, updated_at = EXCLUDED.updated_at
        """, (email, key, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        cursor.close()
        conn.close()
        get_user_api_key.clear()
    except Exception:
        pass

st.sidebar.subheader("🔑 AI Grader API Key (BYOK)")
stored_key = get_user_api_key(user_email)
if stored_key and not st.session_state.get("edit_api_key_toggled", False):
    st.sidebar.text_input("Google AI Studio API Key", value="•" * 24, disabled=True, key=f"masked_api_key_{rc}")
    if st.sidebar.button("✏️ Edit API Key", key=f"unlock_api_btn_{rc}"):
        st.session_state.edit_api_key_toggled = True
        st.rerun()
    user_gemini_key = stored_key
else:
    user_gemini_key = st.sidebar.text_input("Google AI Studio API Key", type="password", key=f"user_gemini_key_{rc}")
    if user_gemini_key != stored_key and user_gemini_key.strip():
        save_user_api_key(user_email, user_gemini_key.strip())
        st.session_state.edit_api_key_toggled = False
        st.sidebar.success("API key saved securely!")
        time.sleep(1)
        st.rerun()

st.header("🤖 AI Grader & Rubric Evaluation Suite")
st.write("Upload assignment instructions, a grading rubric, and student submission files. Gemini will evaluate each student holistically with robust rate-limiting safeguards, run an integrated similarity check if enabled, and generate question scores and Exemplary Badges.")

if not user_gemini_key.strip():
    st.warning("⚠️ Please enter your Google AI Studio API Key in the sidebar under **🔑 AI Grader API Key (BYOK)** to use the AI Grader.")
else:
    col_ai_lms1, col_ai_lms2 = st.columns(2)
    with col_ai_lms1: ai_lms_input = st.text_input("🏫 LMS Number", placeholder="e.g., 48921", key=f"ai_lms_{rc}")
    with col_ai_lms2: ai_assign_input = st.text_input("📝 Assignment Name", placeholder="e.g., Assignment A", key=f"ai_assign_{rc}")

    ai_lms_val = ai_lms_input.strip()
    ai_assign_val = ai_assign_input.strip()
    ai_is_cumulative = bool(ai_lms_val and ai_assign_val)

    ai_col1, ai_col2 = st.columns(2)
    with ai_col1: rubric_file = st.file_uploader("Upload Grading Rubric", type=list(supported_exts), key=f"ai_rubric_{rc}", max_upload_size=5)
    with ai_col2: instructions_file = st.file_uploader("Upload Assignment Instructions", type=list(supported_exts), key=f"ai_instructions_{rc}", max_upload_size=5)

    exemplary_badge_pct = st.slider("🏆 Exemplary Badge Allocation Top %", min_value=0, max_value=50, value=15, step=5)
    run_plagiarism_with_ai = st.checkbox("🔍 Also Run Integrated Plagiarism Check on Submissions", value=True)
    ai_upload_choice = st.radio("Student Submissions Upload Type", ["Individual Files / Student ZIP Archives (.zip)", "Direct Folder Selection"], key=f"ai_up_choice_{rc}")

    st.info("Upload your rubric, instructions, and student submission files above to execute batch evaluation.")
