import streamlit as st

from scraper_utils import export_athlete_csv
from tools.competition_income_tools import (
    get_official_comp_income_csv,
)


def clear_athlete_csv():
    st.session_state.csv_data = None


def render_athlete_csv_tool(
    session,
):
    if st.button(
        "Create Athlete CSV"
    ):
        st.session_state.csv_data = (
            export_athlete_csv(
                session
            )
        )

    if st.session_state.csv_data is None:
        return

    st.download_button(
        label="Download athlete CSV",
        data=st.session_state.csv_data,
        file_name="athletes.csv",
        mime="text/csv",
        on_click=clear_athlete_csv,
    )


def fetch_competition_income(
    session,
    comp_id: int,
):
    placeholder = st.empty()

    def update_progress(
        current,
        total,
        event_id,
    ):
        placeholder.button(
            f"Processing event {current}/{total}",
            disabled=True,
            use_container_width=True,
        )

    try:
        placeholder.button(
            "Processing events",
            disabled=True,
            use_container_width=True,
        )

        (
            csv_data,
            comp_name,
        ) = get_official_comp_income_csv(
            session,
            comp_id,
            progress_callback=update_progress,
        )

        placeholder.empty()

        st.session_state.comp_income_csv_data = (
            csv_data
        )
        st.session_state.comp_income_name = (
            comp_name
        )

    except ValueError as exc:
        placeholder.empty()

        st.session_state.comp_income_csv_data = (
            None
        )
        st.session_state.comp_income_name = None

        st.error(
            str(exc)
        )


def render_official_comp_income_tool(
    session,
):
    with st.form("comp_form"):
        comp_id_str = st.text_input(
            "Competition ID"
        )

        submitted = st.form_submit_button(
            "Get income CSV"
        )

    comp_id = None

    if comp_id_str:
        if (
            comp_id_str.isdigit()
            and int(comp_id_str) > 0
        ):
            comp_id = int(
                comp_id_str
            )
        else:
            st.error(
                "Enter a positive integer"
            )

    if submitted:
        if comp_id is None:
            st.error(
                "Invalid Competition ID"
            )
        else:
            fetch_competition_income(
                session,
                comp_id,
            )

    if (
        st.session_state.comp_income_csv_data
        is None
    ):
        return

    st.download_button(
        label="Download income CSV",
        data=(
            st.session_state
            .comp_income_csv_data
        ),
        file_name=(
            "Income "
            f"{st.session_state.comp_income_name}"
            ".csv"
        ),
        mime="text/csv",
    )
