import streamlit as st

# Custom CSS & HTML Component for Pill-Shaped Social Login Buttons with Official SVG Logos
st.markdown("""
    <style>
        .login-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
            width: 100%;
            max-width: 360px;
            margin: 0 auto;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        .social-login-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            width: 100%;
            height: 44px;
            background-color: #ffffff;
            color: #3c4043;
            border: 1px solid #dadce0;
            border-radius: 22px; /* Perfect pill shape */
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            transition: background-color 0.2s, box-shadow 0.2s, border-color 0.2s;
        }
        .social-login-btn:hover {
            background-color: #f8f9fa;
            border-color: #bdc1c6;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        .social-login-btn svg {
            width: 18px;
            height: 18px;
        }
    </style>

    <div class="login-container">
        <!-- Google -->
        <a href="?login=google" target="_self" class="social-login-btn">
            <svg viewBox="0 0 24 24">
                <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"/>
                <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.13 0-5.78-2.11-6.73-4.96H1.18v3.15C3.15 21.32 7.22 24 12 24z"/>
                <path fill="#FBBC05" d="M5.27 14.24c-.25-.72-.38-1.49-.38-2.24s.13-1.52.38-2.24V6.61H1.18C.43 8.13 0 9.87 0 11.75s.43 3.62 1.18 5.14l4.09-3.15z"/>
                <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.22 0 3.15 2.68 1.18 6.61l4.09 3.15c.95-2.85 3.6-4.96 6.73-4.96z"/>
            </svg>
            Sign in with Google
        </a>

        <!-- Microsoft -->
        <a href="?login=microsoft" target="_self" class="social-login-btn">
            <svg viewBox="0 0 23 23">
                <path fill="#f3f3f3" d="M0 0h23v23H0z"/>
                <path fill="#f35325" d="M1 1h10v10H1z"/>
                <path fill="#81bc06" d="M12 1h10v10H12z"/>
                <path fill="#05a6f0" d="M1 12h10v10H1z"/>
                <path fill="#ffba08" d="M12 12h10v10H12z"/>
            </svg>
            Sign in with Microsoft
        </a>

        <!-- Apple -->
        <a href="?login=apple" target="_self" class="social-login-btn">
            <svg viewBox="0 0 170 170">
                <path fill="#000000" d="M150.37 130.25c-2.45 5.66-5.35 10.87-8.71 15.66-4.58 6.53-8.33 11.05-11.22 13.56-4.48 4.12-9.28 6.23-14.42 6.35-3.69 0-8.14-1.05-13.32-3.18-5.19-2.12-9.97-3.17-14.34-3.17-4.58 0-9.49 1.05-14.75 3.17-5.26 2.13-9.5 3.24-12.74 3.35-4.35.13-9.16-1.9-14.42-6.08-3.59-2.92-7.5-7.66-11.73-14.22-6.2-9.73-11.17-20.4-14.91-32.02-3.75-11.62-5.62-22.7-5.62-33.23 0-14.35 3.75-26.04 11.24-35.07 7.5-9.03 16.74-13.62 27.72-13.78 4.9 0 10.3 1.25 16.2 3.75 5.89 2.5 9.77 3.76 11.63 3.76 1.52 0 5.6-1.39 12.24-4.17 6.64-2.77 12.58-4.02 17.82-3.75 16.2.76 28.77 7.02 37.71 18.78-14.12 8.68-21.05 20.27-20.78 34.78.27 12.04 5.09 21.84 14.45 29.39 4.35 3.59 9.4 6.13 15.16 7.64-1.95 5.66-4.34 11.2-7.18 16.63zM119.22 31.85c0-7.85 2.82-15.14 8.46-21.87 5.64-6.73 12.75-10.45 21.32-11.18.27 1.25.41 2.39.41 3.42 0 7.73-2.94 15.14-8.82 22.23-5.88 7.08-13.07 10.87-21.57 11.36-.26-1.3-.4-2.5-.4-3.96z"/>
            </svg>
            Sign in with Apple
        </a>

        <!-- Facebook -->
        <a href="?login=facebook" target="_self" class="social-link-btn">
            <!-- (Wrapped similarly) -->
        </a>
    </div>
""", unsafe_allow_html=True)
