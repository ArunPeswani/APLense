import io
import os
import streamlit as st
import pandas as pd
from pypdf import PdfReader
import docx2txt
import tempfile
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="APLens - Plagiarism & Matcher", page_icon="📄", layout="centered")

st.title("📄 APLens Plagiarism Suite")

# --- NAVIGATION MENU ---
app_mode = st.sidebar.radio("Navigation", ["Folder Plagiarism Checker", "Deep Dive (2-Doc Comparison)", "💡 User Guide & Help"])

# ==========================================
# MODE 1: FOLDER PLAGIARISM CHECKER
# ==========================================
if app_mode == "Folder Plagiarism Checker":
    st.header("Folder Similarity Matrix Analysis")
    st.write("Upload multiple student submissions below to check cross-document similarities.")

    st.sidebar.header("Analysis Settings")
    min_words = st.sidebar.slider("Minimum N-Gram Words", min_value=1, max_value=10, value=4)
    max_words = st.sidebar.slider("Maximum N-Gram Words", min_value=1, max_value=10, value=6)

    # Privacy notice placed below the sliders for Folder mode
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

    uploaded_files = st.file_uploader(
        "Upload Student Submission Documents (.docx or .pdf only). PDFs should be text based only. Scanned images will not produce desired results.",
        type=["docx", "pdf"],
        accept_multiple_files=True
    )

    def extract_text_from_file(uploaded_file):
        text = ""
        filename = uploaded_file.name.lower()
        try:
            if filename.endswith('.pdf'):
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted: text += extracted + " "
            elif filename.endswith('.docx'):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                text = docx2txt.process(tmp_path)
                os.unlink(tmp_path)
        except Exception as e:
            st.warning(f"Could not read {uploaded_file.name}: {e}")
        return text

    if uploaded_files:
        st.info(f"Loaded {len(uploaded_files)} file(s) successfully.")
        
        if st.button("Run Plagiarism Analysis", type="primary"):
            if len(uploaded_files) < 2:
                st.error("Please upload at least 2 documents to perform a comparison.")
            else:
                with st.spinner("Analyzing documents and calculating similarity matrix..."):
                    documents, filenames = [], []
                    
                    for file in uploaded_files:
                        txt = extract_text_from_file(file)
                        if txt.strip():
                            documents.append(txt)
                            filenames.append(file.name)
                    
                    if len(documents) < 2:
                        st.error("Not enough valid text found in the uploaded documents.")
                    else:
                        vectorizer = TfidfVectorizer(
                            stop_words='english', 
                            ngram_range=(min_words, max_words), 
                            max_features=10000
                        )
                        tfidf_matrix = vectorizer.fit_transform(documents)
                        similarity_matrix = cosine_similarity(tfidf_matrix) * 100
                        
                        df = pd.DataFrame(similarity_matrix, index=filenames, columns=filenames)
                        
                        st.success("Analysis complete!")
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
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

# ==========================================
# MODE 2: DEEP DIVE COMPARISON
# ==========================================
elif app_mode == "Deep Dive (2-Doc Comparison)":
    st.header("Deep Dive Matcher")
    st.write("Compare two specific documents to extract exact matching sentences or true paragraphs.")

    # Privacy notice placed right under the radio menu for Deep Dive mode
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

    col1, col2 = st.columns(2)
    with col1:
        file1 = st.file_uploader("Select Student A Document", type=["docx", "pdf"], key="file1")
    with col2:
        file2 = st.file_uploader("Select Student B Document", type=["docx", "pdf"], key="file2")

    def get_file_bytes_temp(uploaded_file):
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.getvalue())
            return tmp.name

    def get_document_lines_and_sentences(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        raw_blocks = []
        if ext == '.docx':
            import docx
            doc = docx.Document(file_path)
            raw_blocks = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        elif ext == '.pdf':
            reader = PdfReader(file_path)
            full_text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted: full_text += extracted + "\n\n"
            raw_blocks = [b.replace('\n', ' ').strip() for b in re.split(r'\n\s*\n', full_text) if b.strip()]
        
        units = set()
        for block in raw_blocks:
            cleaned_block = re.sub(r'\s+', ' ', block)
            if not cleaned_block: continue
            sub_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned_block) if s.strip()]
            if len(sub_sentences) <= 1:
                units.add(cleaned_block)
            else:
                for s in sub_sentences: units.add(s)
        return units

    def get_document_true_paragraphs(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        raw_blocks = []
        if ext == '.docx':
            import docx
            doc = docx.Document(file_path)
            raw_blocks = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        elif ext == '.pdf':
            reader = PdfReader(file_path)
            full_text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted: full_text += extracted + "\n\n"
            raw_blocks = [b.replace('\n', ' ').strip() for b in re.split(r'\n\s*\n', full_text) if b.strip()]
        
        valid_paragraphs = []
        for block in raw_blocks:
            cleaned_block = re.sub(r'\s+', ' ', block)
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned_block) if s.strip()]
            if len(sentences) >= 2:
                valid_paragraphs.append(cleaned_block)
        return valid_paragraphs

    if file1 and file2:
        analysis_type = st.radio("Select Match Type", ["Sentence Comparison", "Paragraph Comparison"])
        
        if st.button("Run Deep Dive Matcher", type="primary"):
            path1 = get_file_bytes_temp(file1)
            path2 = get_file_bytes_temp(file2)
            
            try:
                if analysis_type == "Sentence Comparison":
                    units1 = get_document_lines_and_sentences(path1)
                    units2 = get_document_lines_and_sentences(path2)
                    common_units = sorted(units1.intersection(units2))
                    
                    if not common_units:
                        st.info("Found 0 matching sentences/lines.")
                    else:
                        st.success(f"Found {len(common_units)} matching sentence(s)/line(s)!")
                        report_content = f"Comparison Report: Comparing '{file1.name}' and '{file2.name}'\n"
                        report_content += f"Found {len(common_units)} matching sentences:\n" + "="*70 + "\n\n"
                        for u in common_units: report_content += u + "\n\n"
                        
                        st.text_area("Matching Sentences Preview", report_content, height=300)
                        st.download_button("📥 Download Sentence Report (.txt)", data=report_content, file_name="common_sentences_report.txt", mime="text/plain")
                
                else:
                    paras1 = get_document_true_paragraphs(path1)
                    paras2 = get_document_true_paragraphs(path2)
                    common_paras = sorted(set(paras1).intersection(set(paras2)))
                    
                    if not common_paras:
                        st.info("Found 0 matching paragraphs (with at least 2 sentences).")
                    else:
                        st.success(f"Found {len(common_paras)} matching paragraph(s)!")
                        report_content = f"Comparison Report: Comparing '{file1.name}' and '{file2.name}'\n"
                        report_content += f"Found {len(common_paras)} matching paragraphs:\n" + "="*70 + "\n\n"
                        for p in common_paras: report_content += p + "\n\n" + "="*50 + "\n\n"
                        
                        st.text_area("Matching Paragraphs Preview", report_content, height=300)
                        st.download_button("📥 Download Paragraph Report (.txt)", data=report_content, file_name="common_paragraphs_report.txt", mime="text/plain")
            
            finally:
                if os.path.exists(path1): os.unlink(path1)
                if os.path.exists(path2): os.unlink(path2)
    else:
        st.warning("Please upload both Student A and Student B documents to run Deep Dive.")

# ==========================================
# MODE 3: USER GUIDE & HELP
# ==========================================
elif app_mode == "💡 User Guide & Help":
    # Privacy notice placed in sidebar for Help mode as well
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

    st.header("💡 APLens User Guide & Help Center")
    st.write("Welcome to APLens! This guide explains what the program is, how it works, and how to interpret your results.")

    st.markdown("---")

    st.subheader("1. What is APLens & What Does It Do?")
    st.write(
        "APLens is a specialized peer-to-peer plagiarism detection and document comparison web suite designed "
        "for educators, instructors, and researchers. It allows you to analyze a batch of student submissions "
        "to find cross-document similarities or perform deep-dive text matches between two specific files."
    )

    st.subheader("2. How It Works")
    st.write(
        "APLens offers two distinct analysis modes:\n\n"
        "* **Folder Plagiarism Checker:** Upload multiple `.docx` or `.pdf` files simultaneously. The app extracts "
        "their text, converts words into numerical token vectors using **TF-IDF (Term Frequency-Inverse Document Frequency)**, "
        "and calculates a **Cosine Similarity** percentage matrix across every possible pair of documents.\n"
        "* **Deep Dive Matcher:** Upload two specific documents to isolate and extract exact overlapping sentences "
        "or true multi-sentence paragraphs using custom structural regex matching."
    )

    st.subheader("3. How to Read the Output Files (Especially the .xlsx File)")
    st.write(
        "When you run the **Folder Plagiarism Checker**, you can download an Excel report (`plagiarism_report.xlsx`). Here is how to read it:\n\n"
        "* **The Matrix Structure:** The Excel spreadsheet is a symmetric cross-comparison table. Both the **Rows** and **Columns** "
        "represent the file names of the uploaded student submissions.\n"
        "* **Reading Cell Values:** Each cell contains a percentage value (from 0% to 100%) indicating how much textual overlap exists "
        "between the document in that row and the document in that column.\n"
        "* **The Diagonal (100%):** The cells running diagonally from top-left to bottom-right will always show **100%**, because a document "
        "is being compared against itself.\n"
        "* **Identifying Potential Plagiarism:** Look for high percentage scores off the diagonal (e.g., 40% to 90%+). A high score "
        "means those two particular student submissions share substantial matching text sequences and warrant a closer manual review."
    )

    st.subheader("4. Support, Contact & Feedback")
    st.write(
        "If you encounter any issues, require assistance, or have ideas on how to make APLens even better, please feel free to reach out. "
        "You can contact **Arun Peswani** for any help required. Your suggestions, feedback, and feature requests are always warmly welcomed!"
    )
