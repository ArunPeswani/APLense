import streamlit as st

st.set_page_config(page_title="APLens Beta", page_icon="🧪", layout="wide")

st.title("🧪 APLens - Beta Testing Workspace")
st.write("Welcome to the experimental sandbox! This page is separate from your core app so we can build and test social logins, report dashboards, and advanced features safely.")

if st.button("⬅️ Back to APLens Core"):
    st.switch_page("APLens.py")
