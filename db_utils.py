# db_utils.py
import streamlit as st
import psycopg2
import pandas as pd

@st.cache_resource
def get_db_connection():
    return None

def get_valid_db_connection():
    conn = get_db_connection()
    try:
        if conn is not None:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return conn
    except Exception:
        pass
    
    try:
        db_url = st.secrets["DATABASE_URL"]
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

@st.cache_data(ttl=30)
def get_cached_requests_and_users():
    try:
        conn = get_valid_db_connection()
        if not conn:
            return pd.DataFrame(), pd.DataFrame()
        df_reqs = pd.read_sql_query("select id, name, email, remarks, timestamp from access_requests order by timestamp desc", conn)
        df_regs = pd.read_sql_query("select email, name, requested_at, approved_at from authorized_users order by approved_at desc", conn)
        conn.close()
        return df_reqs, df_regs
    except Exception:
        return pd.DataFrame(), pd.DataFrame()
