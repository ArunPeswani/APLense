import io
import os
import datetime
import streamlit as st
import pandas as pd
from pypdf import PdfReader
import tempfile
import re
import difflib
from PIL import Image, ImageEnhance
import pytesseract

from db_utils import get_valid_db_connection
from auth import enforce_admin_or_whitelisted_access

enforce_admin_or_whitelisted_access()

if "reset_count_beta" not in st.session_state:
    st.session_state.reset_count_beta = 0
rc = st.session_state.reset_count_beta
supported_exts = ("docx", "pdf", "txt", "rtf", "md", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "tif", "heic", "heif", "webp")

st.header("Deep Dive Matcher")
st.write("Compare two specific documents or spreadsheets sheet-by-sheet to extract exact matching sentences or true paragraphs.")

global_ref_deep = ""
try:
    conn = get_valid_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("select reference_text from course_metadata order by id desc limit 1")
        row = cursor.fetchone()
        cursor.close()
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
    if re.fullmatch(r'\d+\.?', s): return False
    if len(s.split()) < 2: return False
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
            tokens = [str(val).strip() for val in df.values.flatten() if pd.notna(val) and str(val).strip().lower() != 'nan']
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
        for s in sub_sentences:
            if is_valid_sentence(s): units.add(s)
    return units

if file1 and file2:
    if st.button("Run Deep Dive Matcher", type="primary", key=f"run_deep_dive_{rc}"):
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
        finally:
            if os.path.exists(path1): os.unlink(path1)
            if os.path.exists(path2): os.unlink(path2)

if st.session_state.get("deep_analyzed", False):
    matches = st.session_state.deep_high_matches
    st.success(f"Deep Dive Complete! Found **{len(matches)} matching instance(s)** with ≥50% similarity.")
    for item in matches:
        with st.expander(f"Similarity: {item['similarity']}%"):
            st.markdown(f"**Doc A:** {item['doc_a_sentence']}")
            st.markdown(f"**Doc B:** {item['doc_b_sentence']}")
