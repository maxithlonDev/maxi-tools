import time

import requests
import streamlit as st
import urls as url

from medal_views import (
    render_event_specialty_medal_tool,
    render_inc_medals_tool,
    render_world_record_nation_tool,
)
from scraper import login
from scraper_utils import extract_logged_in_user_data
from tool_views import (
    render_athlete_csv_tool,
    render_official_comp_income_tool,
)


ATHLETE_CSV = "Athlete CSV"
OFFICIAL_COMP_INCOME = "Official Competition Income"
INC_MEDALS = "INC Medal Counts"
EVENT_SPECIALTY_MEDALS = "Event/Specialty Medal Aggregator"
WR_BY_NATION = "WR Stats"


def initialize_state():
    defaults = {
        "session": None,
        "public_session": None,
        "guest_mode": False,
        "username": None,
        "user_id": None,
        "csv_data": None,
        "comp_income_csv_data": None,
        "comp_income_name": None,
        "active_tool": OFFICIAL_COMP_INCOME,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_tool_output_state():
    st.session_state.csv_data = None
    st.session_state.comp_income_csv_data = None
    st.session_state.comp_income_name = None


def get_public_request_session():
    if st.session_state.session is not None:
        return st.session_state.session

    if st.session_state.public_session is None:
        st.session_state.public_session = requests.Session()

    return st.session_state.public_session


def select_tool(tool_name: str):
    st.session_state.active_tool = tool_name
    clear_tool_output_state()


def render_login_page():
    st.title("maxi-tools")

    with st.form("login_form"):
        st.text_input(
            "Username",
            key="login_username",
        )
        st.text_input(
            "Password",
            type="password",
            key="login_password",
        )
        submitted = st.form_submit_button("Log in")

    if st.button(
        "Use as guest",
        use_container_width=True,
    ):
        st.session_state.guest_mode = True
        st.session_state.active_tool = OFFICIAL_COMP_INCOME

        if st.session_state.public_session is None:
            st.session_state.public_session = requests.Session()

        st.rerun()

    if not submitted:
        return

    try:
        session, login_html = login(
            st.session_state.login_username,
            st.session_state.login_password,
        )

        username, user_id = extract_logged_in_user_data(
            login_html
        )

        st.session_state.session = session
        st.session_state.guest_mode = False
        st.session_state.username = username
        st.session_state.user_id = user_id

        st.rerun()

    except Exception:
        st.session_state.session = None
        st.session_state.username = None
        st.session_state.user_id = None

        clear_tool_output_state()

        st.session_state.pop("login_username", None)
        st.session_state.pop("login_password", None)

        st.error("Login failed")
        st.rerun()


def logout():
    session = st.session_state.session

    if session is not None:
        session.get(
            url.LOGOUT_URL,
            timeout=5,
        )

    st.success("Logout successful!")
    time.sleep(2)

    st.session_state.session = None
    st.session_state.guest_mode = False
    st.session_state.username = None
    st.session_state.user_id = None
    st.session_state.active_tool = OFFICIAL_COMP_INCOME

    clear_tool_output_state()
    st.rerun()


def render_navigation(
    is_authenticated: bool,
):
    if is_authenticated:
        tools = (
            ATHLETE_CSV,
            OFFICIAL_COMP_INCOME,
            INC_MEDALS,
            EVENT_SPECIALTY_MEDALS,
            WR_BY_NATION,
        )
    else:
        tools = (
            OFFICIAL_COMP_INCOME,
            INC_MEDALS,
            WR_BY_NATION,
        )

    columns = st.columns(
        len(tools)
    )

    for column, tool_name in zip(
        columns,
        tools,
    ):
        with column:
            st.button(
                tool_name,
                on_click=select_tool,
                args=(tool_name,),
                use_container_width=True,
            )


def render_active_tool(
    is_authenticated: bool,
):
    active_tool = (
        st.session_state.active_tool
    )

    st.markdown(
        f"## {active_tool}"
    )

    if (
        active_tool == ATHLETE_CSV
        and is_authenticated
    ):
        render_athlete_csv_tool(
            st.session_state.session
        )

    elif active_tool == OFFICIAL_COMP_INCOME:
        render_official_comp_income_tool(
            get_public_request_session()
        )

    elif active_tool == INC_MEDALS:
        render_inc_medals_tool()

    elif (
        active_tool == EVENT_SPECIALTY_MEDALS
        and is_authenticated
    ):
        render_event_specialty_medal_tool()

    elif active_tool == WR_BY_NATION:
        render_world_record_nation_tool()


initialize_state()

if (
    st.session_state.session is None
    and not st.session_state.guest_mode
):
    render_login_page()
    st.stop()


is_authenticated = (
    st.session_state.session is not None
)

authenticated_only_tools = {
    ATHLETE_CSV,
    EVENT_SPECIALTY_MEDALS,
}

if (
    not is_authenticated
    and st.session_state.active_tool
    in authenticated_only_tools
):
    st.session_state.active_tool = (
        OFFICIAL_COMP_INCOME
    )


if is_authenticated:
    st.markdown(
        (
            "### You are signed in as "
            f"**{st.session_state.username}**"
        )
    )

    if st.button("Logout"):
        logout()

else:
    st.markdown("### Guest")

    if st.button("Sign in"):
        st.session_state.guest_mode = False
        st.session_state.active_tool = (
            OFFICIAL_COMP_INCOME
        )
        st.rerun()


render_navigation(
    is_authenticated
)

render_active_tool(
    is_authenticated
)
