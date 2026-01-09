import streamlit as st

from scraper import login
from scraper_utils import (
    export_athlete_csv,
    extract_logged_in_username,
)

# -------------------------
# session state
# -------------------------
if "session" not in st.session_state:
    st.session_state.session = None

if "username" not in st.session_state:
    st.session_state.username = None

if "csv_data" not in st.session_state:
    st.session_state.csv_data = None


# -------------------------
# login page
# -------------------------
if st.session_state.session is None:
    st.title("maxi-tools")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        try:
            session, login_html = login(username, password)
            display_name = extract_logged_in_username(login_html)

            st.session_state.session = session
            st.session_state.username = display_name
            st.rerun()

        except ValueError:
            st.error("Login failed")

    st.stop()


# -------------------------
# tools page
# -------------------------
st.markdown(
    f"### You are signed in as **{st.session_state.username}**"
)

# logout button (simple + safe)
if st.button("Logout"):
    st.session_state.session = None
    st.session_state.username = None
    st.session_state.csv_data = None
    st.rerun()


col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Create Athlete CSV"):
        st.session_state.csv_data = export_athlete_csv(
            st.session_state.session
        )


def clear_csv():
    st.session_state.csv_data = None


# -------------------------
# download area
# -------------------------
if st.session_state.csv_data is not None:
    st.download_button(
        label="Download athlete CSV",
        data=st.session_state.csv_data,
        file_name="athletes.csv",
        mime="text/csv",
        on_click=clear_csv,
    )
