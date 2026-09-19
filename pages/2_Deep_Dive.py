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
from pillow_heif import register_heif_opener
register_heif_opener()

from db_utils import get_valid_db_connection
from auth import enforce_admin_or_whitelisted_access, render_page_header

# 1. Enforce security gate
enforce_admin_or_whitelisted_access()

# 2. Render centralized header with profile picture and logout dropdown
render_page_header("Deep Dive Matcher")

st.write("Compare two specific documents or spreadsheets sheet-by-sheet to extract exact matching sentences or true paragraphs.")

# Retrieve global reference text if available
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

if global_ref_deep:
    st.info("💡 Global Smart Filtering is active: Assignment prompt/reference text will be automatically filtered out during matching.")

supported_exts = ("docx", "pdf", "txt", "rtf", "md", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "tif", "heic", "heif", "webp")

col1, col2 = st.columns(2)
with col1:
    file1 = st.file_uploader("Select Student A Document (Max 5MB)", type=list(supported_exts), max_upload_size=5, key=f"deep_file1_{st.session_state.get('reset_count_beta', 0)}")
with col2:
    file2 = st.file_uploader("Select Student B Document (Max 5MB)", type=list(supported_exts), max_upload_size=5, key=f"deep_file2_{st.session_state.get('reset_count_beta', 0)}")

rc = st.session_state.get('reset_count_beta', 0)

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
    try:
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
            if len(full_text_pdf.strip()) < 15:
                with open(file_path, "rb") as f: pdf_bytes = f.read()
                from pdf2image import convert_from_bytes
                images = convert_from_bytes(pdf_bytes)
                for img in images:
                    img_gray = img.convert('L')
                    img_enhanced = ImageEnhance.Contrast(img_gray).enhance(2.0)
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
            image = ImageEnhance.Contrast(image).enhance(2.0)
            full_text_img = pytesseract.image_to_string(image, lang='hin+eng')
            raw_blocks = [b.replace('\n', ' ').strip() for b in re.split(r'\n\s*\n', full_text_img) if b.strip()]
    except Exception:
        pass
    
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

def get_document_true_paragraphs(file_path, reference_text=""):
    ext = os.path.splitext(file_path)[1].lower()
    raw_blocks = []
    try:
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
    except Exception:
        pass
    
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
            sheet_data["paraphrase_pairs" if paraphrase_mode else "common_sentences"] = []
            sheet_data["count"] = 0
        breakdown_results.append(sheet_data)
    return breakdown_results

if file1 and file2:
    is_excel_comparison = file1.name.lower().endswith(('.xlsx', '.xls')) and file2.name.lower().endswith(('.xlsx', '.xls'))
    analysis_type = st.radio("Select Match Type", ["Sheet-by-Sheet Analysis", "Sentence Comparison", "Paragraph Comparison"], key=f"deep_match_type_{rc}") if is_excel_comparison else st.radio("Select Match Type", ["Sentence Comparison", "Paragraph Comparison"], key=f"deep_match_type_{rc}")
    
    col_deep1, col_deep2 = st.columns(2)
    with col_deep1: run_deep = st.button("Run Deep Dive Matcher", type="primary", key=f"run_deep_dive_{rc}")
    with col_deep2: run_deep_para = st.button("🔍 Run Paraphrase Matcher", type="secondary", key=f"run_deep_para_{rc}")

    if run_deep or run_deep_para:
        path1 = get_file_bytes_temp(file1)
        path2 = get_file_bytes_temp(file2)
        try:
            user_is_logged_in = getattr(st.user, "is_logged_in", False)
            user_email = getattr(st.user, "email", "User") if user_is_logged_in else ""
            user_name = getattr(st.user, "name", "Google User") if user_is_logged_in else ""

            if is_excel_comparison and analysis_type == "Sheet-by-Sheet Analysis":
                if run_deep_para:
                    breakdown = get_excel_sheet_breakdown(path1, path2, global_ref_deep, paraphrase_mode=True)
                    st.session_state.deep_result_type = "excel_sheets_paraphrase"
                    st.session_state.deep_excel_breakdown = breakdown
                    report_content = f"Excel Sheet-by-Sheet Paraphrase Report\nComparing '{file1.name}' and '{file2.name}'\n" + "="*70 + "\n\n"
                    for item in breakdown:
                        report_content += f"Sheet Name: {item['sheet']}\n"
                        if item['in_both']:
                            for p1, p2, score in item['paraphrase_pairs']:
                                report_content += f"  • [Similarity: {score}%]\n    - A: {p1}\n    - B: {p2}\n"
                    st.session_state.deep_report_content = report_content
                    st.session_state.deep_filename = "excel_sheet_paraphrase_report.txt"
                else:
                    breakdown = get_excel_sheet_breakdown(path1, path2, global_ref_deep, paraphrase_mode=False)
                    st.session_state.deep_result_type = "excel_sheets"
                    st.session_state.deep_excel_breakdown = breakdown
                    report_content = f"Excel Sheet-by-Sheet Comparison Report\nComparing '{file1.name}' and '{file2.name}'\n" + "="*70 + "\n\n"
                    for item in breakdown:
                        report_content += f"Sheet Name: {item['sheet']}\n"
                        if item['in_both']:
                            for s in item['common_sentences']: report_content += f"  • {s}\n"
                    st.session_state.deep_report_content = report_content
                    st.session_state.deep_filename = "excel_sheet_comparison_report.txt"

            elif analysis_type == "Sentence Comparison":
                if run_deep_para:
                    units1 = list(get_document_lines_and_sentences(path1, global_ref_deep))
                    units2 = list(get_document_lines_and_sentences(path2, global_ref_deep))
                    pairs = [(u1, u2, round(difflib.SequenceMatcher(None, u1.lower(), u2.lower()).ratio() * 100, 1)) for u1 in units1 for u2 in units2 if u1 != u2 and 0.65 <= difflib.SequenceMatcher(None, u1.lower(), u2.lower()).ratio() < 1.0]
                    pairs.sort(key=lambda x: x[2], reverse=True)
                    st.session_state.deep_result_type = "paraphrased_matches"
                    st.session_state.deep_para_pairs = pairs
                    report_content = f"Paraphrase Deep Dive Report (Sentences)\n" + "="*70 + "\n\n"
                    for p1, p2, score in pairs: report_content += f"[Similarity: {score}%]\n- Doc A: {p1}\n- Doc B: {p2}\n\n"
                    st.session_state.deep_report_content = report_content
                    st.session_state.deep_filename = "paraphrase_sentences_report.txt"
                else:
                    common = sorted(get_document_lines_and_sentences(path1, global_ref_deep).intersection(get_document_lines_and_sentences(path2, global_ref_deep)))
                    st.session_state.deep_result_type = "empty_sentences" if not common else "sentences"
                    st.session_state.deep_count = len(common)
                    st.session_state.deep_report_content = "\n\n".join(common)
                    st.session_state.deep_filename = "sentences_report.txt"

            else:  # Paragraph Comparison
                if run_deep_para:
                    paras1 = list(get_document_true_paragraphs(path1, global_ref_deep))
                    paras2 = list(get_document_true_paragraphs(path2, global_ref_deep))
                    para_pairs = [(p1, p2, round(difflib.SequenceMatcher(None, p1.lower(), p2.lower()).ratio() * 100, 1)) for p1 in paras1 for p2 in paras2 if p1 != p2 and 0.65 <= difflib.SequenceMatcher(None, p1.lower(), p2.lower()).ratio() < 1.0]
                    para_pairs.sort(key=lambda x: x[2], reverse=True)
                    st.session_state.deep_result_type = "paraphrased_paragraphs"
                    st.session_state.deep_para_pairs = para_pairs
                    report_content = f"Paraphrase Deep Dive Report (Paragraphs)\n" + "="*70 + "\n\n"
                    for p1, p2, score in para_pairs: report_content += f"[Similarity: {score}%]\n- Para A: {p1}\n- Para B: {p2}\n\n" + "="*50 + "\n\n"
                    st.session_state.deep_report_content = report_content
                    st.session_state.deep_filename = "paraphrase_paragraphs_report.txt"
                else:
                    common = sorted(set(get_document_true_paragraphs(path1, global_ref_deep)).intersection(set(get_document_true_paragraphs(path2, global_ref_deep))))
                    st.session_state.deep_result_type = "empty_paras" if not common else "paragraphs"
                    st.session_state.deep_count = len(common)
                    st.session_state.deep_report_content = "\n\n".join(common)
                    st.session_state.deep_filename = "paragraphs_report.txt"
            
            try:
                conn = get_valid_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        insert into beta_deep_dive_activity (
                            user_email, user_name, timestamp, doc_a_name, doc_b_name, 
                            high_match_count_over_50pct, top_matches_summary
                        ) values (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        user_email, user_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        file1.name, file2.name, 1, f"Deep dive {analysis_type} executed"
                    ))
                    conn.commit()
                    cursor.close()
                    conn.close()
            except Exception:
                pass
        finally:
            if os.path.exists(path1): os.unlink(path1)
            if os.path.exists(path2): os.unlink(path2)

# --- RENDER RESULTS ---
if st.session_state.get("deep_result_type") == "empty_sentences":
    st.info("Found 0 matching sentences/lines.")
elif st.session_state.get("deep_result_type") == "empty_paras":
    st.info("Found 0 matching paragraphs.")
elif st.session_state.get("deep_result_type") in ["paraphrased_matches", "paraphrased_paragraphs"]:
    pairs = st.session_state.deep_para_pairs
    mode_label = "sentence" if st.session_state.get("deep_result_type") == "paraphrased_matches" else "paragraph"
    if not pairs:
        st.info(f"Found 0 potential paraphrased {mode_label} matches.")
    else:
        st.success(f"Found {len(pairs)} potential paraphrased {mode_label} match(es)!")
        for p1, p2, score in pairs:
            with st.expander(f"Similarity Score: {score}%"):
                st.markdown(f"**Document A:** {p1}")
                st.markdown(f"**Document B:** {p2}")
        st.text_area("Paraphrase Deep Dive Report", st.session_state.deep_report_content, height=300, key=f"deep_preview_para_{rc}")
        st.download_button(f"📥 Download Paraphrase Report (.txt)", data=st.session_state.deep_report_content, file_name=st.session_state.deep_filename, mime="text/plain", key=f"download_deep_para_{rc}")

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
