import streamlit as st
from scraper import login
from scraper_utils import export_athlete_csv

# ---------- session state ----------
if "session" not in st.session_state:
    st.session_state.session = None

if "csv_data" not in st.session_state:
    st.session_state.csv_data = None


# ---------- login page ----------
if st.session_state.session is None:
    st.title("maxi-tools")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        try:
            st.session_state.session = login(username, password)
            st.rerun()
        except ValueError:
            st.error("Login failed")

    st.stop()


# ---------- tools page ----------
st.title("maxi-tools")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Create Athlete CSV"):
        st.session_state.csv_data = export_athlete_csv(
            st.session_state.session
        )


# ---------- download area ----------
def clear_csv():
    st.session_state.csv_data = None


if st.session_state.csv_data is not None:
    st.download_button(
        label="Download athlete CSV",
        data=st.session_state.csv_data,
        file_name="athletes.csv",
        mime="text/csv",
        on_click=clear_csv,
    )