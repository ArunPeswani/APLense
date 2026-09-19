# ==========================================
# MODE 6: USER GUIDE & HELP
# ==========================================
elif app_mode == "💡 User Guide & Help":
    st.header("💡 Grader Guide & Help Center")
    st.write("Welcome to the APLens Beta Suite. This comprehensive guide is designed for graders to help you navigate login security, cumulative late submissions, AI rubric grading, and report tracking.")

    st.markdown("---")

    st.subheader("1. Gated Google Authentication & Access Control")
    st.write(
        "* **Secure Whitelist Approval:** Only pre-approved email addresses can access APLens Beta. New users must submit an approval request with their name and remarks upon signing in.\n"
        "* **Admin Access Management:** Arun Peswani (`arunpeswani@gmail.com`) can review, select, and approve incoming requests, as well as manage or unregister active users via the Access Requests Management panel."
    )

    st.subheader("2. AI Grader, Rate-Limiting & Multimodal Evaluation")
    st.write(
        "* **Automated RPM Rate-Limiting:** The app intelligently tracks request frequencies and automatically paces batches to respect Google AI Studio free tier limits (10–15 RPM) with built-in exponential backoff retries.\n"
        "* **Multi-File ZIP Grouping:** Submissions packed in ZIP archives are automatically grouped by student name so each student gets one holistic evaluation row.\n"
        "* **Exemplary Badge Allocation:** Specify the top percentage of students to receive Exemplary Badges based on rubric performance."
    )

    st.subheader("3. How to Get Your Free Google AI Studio API Key (BYOK)")
    st.write(
        "To use the AI Grader, you will need a personal API key from Google AI Studio. Follow these simple steps to generate yours:\n\n"
        "1. Open your web browser and go to **[Google AI Studio](https://aistudio.google.com/)**.\n"
        "2. Sign in using your Google account.\n"
        "3. In the left-hand sidebar or top navigation bar, click on **'Dashboard'**.\n"
        "4. In the left-hand sidebar, click on **'API keys'**.\n"
        "5. A default key is auto-generated on the right side in the API Keys table. Copy your API key.\n"
        "6. Return to APLens Beta, paste your key into the sidebar input field under **'🔑 AI Grader API Key (BYOK)'**, and it will be securely saved to your account for future sessions!"
    )

    st.subheader("4. Cumulative Late Submissions, 60-Day Retention & Purge")
    st.write(
        "* **Conditional Cumulative Trigger:** Cumulative checking and AI grading history **only** load/save if **both** LMS Number and Assignment Name are provided.\n"
        "* **Default 60-Day Retention:** Reports automatically schedule deletion after 60 days (customizable via the sidebar dropdown).\n"
        "* **Manual Purge:** Use the Course Data Purge tool in the Report History dashboard to instantly delete records for a specific LMS number and assignment."
    )

    st.subheader("5. Support & Contact")
    st.write(
        "For assistance, please contact **Arun Peswani**."
    )
