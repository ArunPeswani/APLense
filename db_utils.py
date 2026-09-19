# db_utils.py
import streamlit as st
import psycopg2
import pandas as pd
import os

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
        # Check Streamlit secrets first, fallback to OS environment variables if reloading
        db_url = None
        try:
            db_url = st.secrets.get("DATABASE_URL")
        except Exception:
            pass
            
        if not db_url:
            db_url = os.environ.get("DATABASE_URL")

        if not db_url:
            return None

        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
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
