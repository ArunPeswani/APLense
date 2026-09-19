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

user_is_logged_in = getattr(st.user, "is_logged_in", False)
user_email = getattr(st.user, "email", "User") if user_is_logged_in else ""
user_name = getattr(st.user, "name", "Google User") if user_is_logged_in else ""

if "reset_count_beta" not in st.session_state:
    st.session_state.reset_count_beta = 0
rc = st.session_state.reset_count_beta
supported_exts = ("docx", "pdf", "txt", "rtf", "md", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "tif", "heic", "heif", "webp")

st.header("Deep Dive Matcher")
st.write("Compare two specific documents or spreadsheets sheet-by-sheet to extract exact matching sentences or true paragraphs.")
# (Rest of Deep Dive logic follows directly)
