import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="APLens Beta - Login Test", page_icon="🧪", layout="centered")

# --- INITIALIZE SUPABASE CLIENT ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# --- JAVASCRIPT HASH CATCHER FOR IMPLICIT OAUTH ---
# This captures tokens from the URL fragment (#access_token=...&refresh_token=...) 
# and moves them into query parameters so Python can establish a real Supabase session.
st.markdown("""
    <script>
        (function () {
            const hash = window.location.hash;
            if (hash && hash.includes("access_token")) {
                const params = new URLSearchParams(hash.substring(1));
                const accessToken = params.get("access_token");
                const refreshToken = params.get("refresh_token");
                if (accessToken && refreshToken) {
                    const currentUrl =
                        window.location.origin +
                        window.location.pathname +
                        "?oauth_access_token=" +
                        encodeURIComponent(accessToken) +
                        "&oauth_refresh_token=" +
                        encodeURIComponent(refreshToken);
                    window.location.replace(currentUrl);
                }
            }
        })();
    </script>
""", unsafe_allow_html=True)

# --- PROCESS OAUTH TOKENS IN PYTHON ---
oauth_access_token = st.query_params.get("oauth_access_token")
oauth_refresh_token = st.query_params.get("oauth_refresh_token")

if oauth_access_token and oauth_refresh_token:
    try:
        # Establish the actual persistent Supabase session
        session_response = supabase.auth.set_session(oauth_access_token, oauth_refresh_token)
        if session_response and session_response.user:
            st.session_state.logged_in = True
            st.session_state.user_email = session_response.user.email or "Authenticated User"
            st.query_params.clear()
            st.rerun()
    except Exception as e:
        st.error(f"OAuth sign-in could not be completed: {e}")
        st.query_params.clear()

# --- FALLBACK: CHECK EXISTING SUPABASE SESSION ---
if not st.session_state.logged_in:
    try:
        current_session = supabase.auth.get_session()
        if current_session and current_session.user:
            st.session_state.logged_in = True
            st.session_state.user_email = current_session.user.email or "Authenticated User"
    except Exception:
        pass

# --- UI DISPLAY ---
st.title("🧪 APLens Beta - Google Social Login Test")
st.markdown("---")

if st.session_state.logged_in:
    st.success(f"Successfully logged in as: **{st.session_state.user_email}**")
    if st.button("Sign Out", type="secondary"):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()
else:
    st.info("Please sign in using Google to test the isolated OAuth workflow.")
    
    try:
        project_url = st.secrets["SUPABASE_URL"]
        redirect_target = "https://aplens.streamlit.app/APLens_Beta"
        google_url = f"{project_url}/auth/v1/authorize?provider=google&prompt=select_account&redirect_to={redirect_target}"
        
        st.markdown(f"""
            <div style="display: flex; justify-content: center; margin-top: 20px;">
                <a href="{google_url}" target="_blank" style="
                    display: flex; align-items: center; justify-content: center; gap: 12px;
                    width: 100%; max-width: 280px; height: 44px; background-color: #ffffff;
                    color: #3c4043; border: 1px solid #dadce0; border-radius: 22px;
                    font-size: 14px; font-weight: 500; text-decoration: none;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
                ">
                    <svg viewBox="0 0 24 24" width="18" height="18">
                        <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"/>
                        <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.13 0-5.78-2.11-6.73-4.96H1.18v3.15C3.15 21.32 7.22 24 12 24z"/>
                        <path fill="#FBBC05" d="M5.27 14.24c-.25-.72-.38-1.49-.38-2.24s.13-1.52.38-2.24V6.61H1.18C.43 8.13 0 9.87 0 11.75s.43 3.62 1.18 5.14l4.09-3.15z"/>
                        <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.22 0 3.15 2.68 1.18 6.61l4.09 3.15c.95-2.85 3.6-4.96 6.73-4.96z"/>
                    </svg>
                    Sign in with Google
                </a>
            </div>
        """, unsafe_allow_html=True)
    except Exception as ex:
        st.error(f"Could not load Google login link: {ex}")
