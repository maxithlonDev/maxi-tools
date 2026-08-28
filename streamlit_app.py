import streamlit as st
import time
import urls as url

from scraper import login
from scraper_utils import (
    export_athlete_csv,
    extract_logged_in_user_data,
)

from tools.competition_income_tools import get_official_comp_income_csv
from tools.inc_competition_ids_tool import get_inc_competitions_json


# -------------------------
# session state
# -------------------------
if "session" not in st.session_state:
    st.session_state.session = None

if "username" not in st.session_state:
    st.session_state.username = None

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "csv_data" not in st.session_state:
    st.session_state.csv_data = None

if "comp_income_csv_data" not in st.session_state:
    st.session_state.comp_income_csv_data = None

if "comp_income_name" not in st.session_state:
    st.session_state.comp_income_name = None

if "inc_competitions_json_data" not in st.session_state:
    st.session_state.inc_competitions_json_data = None

if "inc_competitions_summary" not in st.session_state:
    st.session_state.inc_competitions_summary = None

if "active_tool" not in st.session_state:
    st.session_state.active_tool = "Athlete CSV"


# -------------------------
# login page
# -------------------------
if st.session_state.session is None:
    st.title("maxi-tools")

    with st.form("login_form"):
        st.text_input("Username", key="login_username")
        st.text_input(
            "Password",
            type="password",
            key="login_password",
        )
        submitted = st.form_submit_button("Log in")

    if submitted:
        try:
            session, login_html = login(
                st.session_state.login_username,
                st.session_state.login_password,
            )

            username_display, user_id = (
                extract_logged_in_user_data(login_html)
            )

            st.session_state.session = session
            st.session_state.username = username_display
            st.session_state.user_id = user_id

            st.rerun()

        except Exception:
            st.session_state.session = None
            st.session_state.username = None
            st.session_state.user_id = None
            st.session_state.csv_data = None
            st.session_state.comp_income_csv_data = None
            st.session_state.comp_income_name = None
            st.session_state.inc_competitions_json_data = None
            st.session_state.inc_competitions_summary = None

            if "login_username" in st.session_state:
                del st.session_state["login_username"]

            if "login_password" in st.session_state:
                del st.session_state["login_password"]

            st.error("Login failed")
            st.rerun()

    st.stop()


def select_athlete_csv():
    st.session_state.active_tool = "Athlete CSV"
    st.session_state.comp_income_csv_data = None
    st.session_state.comp_income_name = None
    st.session_state.inc_competitions_json_data = None
    st.session_state.inc_competitions_summary = None


def select_official_comp_income():
    st.session_state.active_tool = "Official Competition Income"
    st.session_state.csv_data = None
    st.session_state.inc_competitions_json_data = None
    st.session_state.inc_competitions_summary = None


def select_inc_competition_ids():
    st.session_state.active_tool = "INC Competition IDs"
    st.session_state.csv_data = None
    st.session_state.comp_income_csv_data = None
    st.session_state.comp_income_name = None


def clear_csv():
    st.session_state.csv_data = None


def render_athlete_csv_tool():
    if st.button("Create Athlete CSV"):
        st.session_state.csv_data = export_athlete_csv(
            st.session_state.session
        )

    if st.session_state.csv_data is not None:
        st.download_button(
            label="Download athlete CSV",
            data=st.session_state.csv_data,
            file_name="athletes.csv",
            mime="text/csv",
            on_click=clear_csv,
        )


def render_official_comp_income_tool():
    with st.form("comp_form"):
        comp_id_str = st.text_input("Competition ID")
        submitted = st.form_submit_button("Get income CSV")

    comp_id = None

    if comp_id_str:
        if comp_id_str.isdigit() and int(comp_id_str) > 0:
            comp_id = int(comp_id_str)
        else:
            st.error("Enter a positive integer")

    if submitted:
        if comp_id is None:
            st.error("Invalid Competition ID")
        else:
            placeholder = st.empty()

            def update_progress(current, total, event_id):
                placeholder.button(
                    f"Processing event {current}/{total}",
                    disabled=True,
                    use_container_width=True,
                )

            try:
                placeholder.button(
                    "Processing event 0/52",
                    disabled=True,
                    use_container_width=True,
                )

                csv_data, comp_name = (
                    get_official_comp_income_csv(
                        st.session_state.session,
                        comp_id,
                        progress_callback=update_progress,
                    )
                )

                placeholder.empty()

                st.session_state.comp_income_csv_data = (
                    csv_data
                )
                st.session_state.comp_income_name = comp_name

            except ValueError as e:
                placeholder.empty()
                st.session_state.comp_income_csv_data = None
                st.session_state.comp_income_name = None
                st.error(str(e))

    if st.session_state.comp_income_csv_data is not None:
        st.download_button(
            label="Download income CSV",
            data=st.session_state.comp_income_csv_data,
            file_name=(
                f"Income "
                f"{st.session_state.comp_income_name}.csv"
            ),
            mime="text/csv",
        )


def render_inc_competition_ids_tool():
    if st.button("Build INC competition JSON"):
        placeholder = st.empty()

        def update_progress(
            current,
            total,
            country_id,
            country_name,
        ):
            placeholder.button(
                (
                    f"Processing country "
                    f"{current}/{total}: {country_name}"
                ),
                disabled=True,
                use_container_width=True,
            )

        try:
            placeholder.button(
                "Discovering countries...",
                disabled=True,
                use_container_width=True,
            )

            (
                json_data,
                country_count,
                competition_count,
                latest_season,
            ) = get_inc_competitions_json(
                st.session_state.session,
                progress_callback=update_progress,
            )

            placeholder.empty()

            st.session_state.inc_competitions_json_data = (
                json_data
            )
            st.session_state.inc_competitions_summary = (
                country_count,
                competition_count,
                latest_season,
            )

        except (ValueError, OSError) as e:
            placeholder.empty()
            st.session_state.inc_competitions_json_data = None
            st.session_state.inc_competitions_summary = None
            st.error(str(e))

    if st.session_state.inc_competitions_summary is not None:
        (
            country_count,
            competition_count,
            latest_season,
        ) = st.session_state.inc_competitions_summary

        st.write(
            f"Found {competition_count} INC competitions "
            f"across {country_count} countries. "
            f"Latest season: {latest_season}."
        )

    if st.session_state.inc_competitions_json_data is not None:
        st.download_button(
            label="Download INC competition JSON",
            data=st.session_state.inc_competitions_json_data,
            file_name="inc_competitions.json",
            mime="application/json",
        )


# -------------------------
# tools page
# -------------------------
st.markdown(
    f"### You are signed in as **{st.session_state.username}**"
)

if st.button("Logout"):
    sess = st.session_state.session

    if sess is not None:
        sess.get(url.LOGOUT_URL, timeout=5)

    st.success("Logout successful!")

    time.sleep(2)

    st.session_state.session = None
    st.session_state.username = None
    st.session_state.user_id = None
    st.session_state.csv_data = None
    st.session_state.comp_income_csv_data = None
    st.session_state.comp_income_name = None
    st.session_state.inc_competitions_json_data = None
    st.session_state.inc_competitions_summary = None

    st.rerun()

tool_col1, tool_col2, tool_col3 = st.columns(3)

with tool_col1:
    st.button(
        "Athlete CSV",
        on_click=select_athlete_csv,
    )

with tool_col2:
    st.button(
        "Official Competition Income",
        on_click=select_official_comp_income,
    )

with tool_col3:
    st.button(
        "INC Competition IDs",
        on_click=select_inc_competition_ids,
    )

st.markdown(f"## {st.session_state.active_tool}")

if st.session_state.active_tool == "Athlete CSV":
    render_athlete_csv_tool()

elif (
    st.session_state.active_tool
    == "Official Competition Income"
):
    render_official_comp_income_tool()

elif st.session_state.active_tool == "INC Competition IDs":
    render_inc_competition_ids_tool()
