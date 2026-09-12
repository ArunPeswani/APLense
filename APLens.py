import io
import os
import streamlit as st
import pandas as pd
from pypdf import PdfReader
import docx2txt
import tempfile
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="APLens - Plagiarism Checker", page_icon="📄", layout="centered")

st.title("📄 APLens Plagiarism Checker")
st.write("Upload student submissions below to generate a cross-comparison similarity matrix.")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("Analysis Settings")
min_words = st.sidebar.slider("Minimum N-Gram Words", min_value=1, max_value=10, value=4)
max_words = st.sidebar.slider("Maximum N-Gram Words", min_value=1, max_value=10, value=6)

if min_words > max_words:
    st.sidebar.error("Min words cannot exceed Max words!")

# --- FILE UPLOADER ---
uploaded_files = st.file_uploader(
    "Upload Student Documents (.docx or .pdf)",
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
                if extracted:
                    text += extracted + " "
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
                documents = []
                filenames = []
                
                for file in uploaded_files:
                    txt = extract_text_from_file(file)
                    if txt.strip():
                        documents.append(txt)
                        filenames.append(file.name)
                
                if len(documents) < 2:
                    st.error("Not enough valid text found in the uploaded documents.")
                else:
                    # Vectorize and compute similarity
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
                    
                    # Prepare Excel for download in-memory
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