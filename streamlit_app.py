import json
import time

import streamlit as st
import urls as url

from scraper import login
from scraper_utils import (
    export_athlete_csv,
    extract_logged_in_user_data,
)

from tools.competition_income_tools import (
    get_official_comp_income_csv,
)
from tools.inc_competition_ids_tool import (
    get_inc_competitions_json,
)


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

if "inc_outputs" not in st.session_state:
    st.session_state.inc_outputs = None

if "inc_timings" not in st.session_state:
    st.session_state.inc_timings = None

if "inc_country_count" not in st.session_state:
    st.session_state.inc_country_count = None

if "inc_competition_count" not in st.session_state:
    st.session_state.inc_competition_count = None

if "inc_latest_season" not in st.session_state:
    st.session_state.inc_latest_season = None

if "active_tool" not in st.session_state:
    st.session_state.active_tool = "Athlete CSV"


# -------------------------
# login page
# -------------------------

if st.session_state.session is None:
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
        submitted = st.form_submit_button(
            "Log in"
        )

    if submitted:
        try:
            session, login_html = login(
                st.session_state.login_username,
                st.session_state.login_password,
            )

            (
                username_display,
                user_id,
            ) = extract_logged_in_user_data(
                login_html
            )

            st.session_state.session = session
            st.session_state.username = (
                username_display
            )
            st.session_state.user_id = user_id

            st.rerun()

        except Exception:
            st.session_state.session = None
            st.session_state.username = None
            st.session_state.user_id = None
            st.session_state.csv_data = None
            st.session_state.comp_income_csv_data = (
                None
            )
            st.session_state.comp_income_name = None
            st.session_state.inc_outputs = None
            st.session_state.inc_timings = None
            st.session_state.inc_country_count = None
            st.session_state.inc_competition_count = (
                None
            )
            st.session_state.inc_latest_season = None

            if (
                "login_username"
                in st.session_state
            ):
                del st.session_state[
                    "login_username"
                ]

            if (
                "login_password"
                in st.session_state
            ):
                del st.session_state[
                    "login_password"
                ]

            st.error("Login failed")
            st.rerun()

    st.stop()


def select_athlete_csv():
    st.session_state.active_tool = (
        "Athlete CSV"
    )
    st.session_state.comp_income_csv_data = None
    st.session_state.comp_income_name = None
    st.session_state.inc_outputs = None
    st.session_state.inc_timings = None


def select_official_comp_income():
    st.session_state.active_tool = (
        "Official Competition Income"
    )
    st.session_state.csv_data = None
    st.session_state.inc_outputs = None
    st.session_state.inc_timings = None


def select_inc_competition_ids():
    st.session_state.active_tool = (
        "INC Competition IDs"
    )
    st.session_state.csv_data = None
    st.session_state.comp_income_csv_data = None
    st.session_state.comp_income_name = None


def clear_csv():
    st.session_state.csv_data = None


def render_athlete_csv_tool():
    if st.button("Create Athlete CSV"):
        st.session_state.csv_data = (
            export_athlete_csv(
                st.session_state.session
            )
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
            comp_id = int(comp_id_str)
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
            placeholder = st.empty()

            def update_progress(
                current,
                total,
                event_id,
            ):
                placeholder.button(
                    (
                        f"Processing event "
                        f"{current}/{total}"
                    ),
                    disabled=True,
                    use_container_width=True,
                )

            try:
                placeholder.button(
                    "Processing event 0/52",
                    disabled=True,
                    use_container_width=True,
                )

                (
                    csv_data,
                    comp_name,
                ) = get_official_comp_income_csv(
                    st.session_state.session,
                    comp_id,
                    progress_callback=(
                        update_progress
                    ),
                )

                placeholder.empty()

                st.session_state[
                    "comp_income_csv_data"
                ] = csv_data

                st.session_state[
                    "comp_income_name"
                ] = comp_name

            except ValueError as e:
                placeholder.empty()

                st.session_state[
                    "comp_income_csv_data"
                ] = None

                st.session_state[
                    "comp_income_name"
                ] = None

                st.error(str(e))

    if (
        st.session_state.comp_income_csv_data
        is not None
    ):
        st.download_button(
            label="Download income CSV",
            data=(
                st.session_state
                .comp_income_csv_data
            ),
            file_name=(
                f"Income "
                f"{st.session_state.comp_income_name}"
                f".csv"
            ),
            mime="text/csv",
        )


def build_inc_viewer_data() -> dict:
    countries = {}

    for output in st.session_state.inc_outputs:
        data = json.loads(
            output["json_data"].decode("utf-8")
        )

        for country_id, country_data in (
            data["countries"].items()
        ):
            if country_id not in countries:
                countries[country_id] = {
                    "name": country_data["name"],
                    "competitions": {},
                }

            countries[country_id][
                "competitions"
            ].update(
                country_data["competitions"]
            )

    return countries


def is_no_club(club: dict) -> bool:
    return (
        club.get("club_id") is None
        and club.get("name") == "No Club"
    )


def build_income_rows(
    clubs: list[dict],
) -> list[dict]:
    regular_clubs = [
        club
        for club in clubs
        if (
            not is_no_club(club)
            and club.get("income", 0) > 0
        )
    ]

    no_club = [
        club
        for club in clubs
        if (
            is_no_club(club)
            and club.get("income", 0) > 0
        )
    ]

    regular_clubs.sort(
        key=lambda club: (
            -club.get("income", 0),
            club.get("name", "").lower(),
        )
    )

    sorted_clubs = regular_clubs + no_club

    return [
        {
            "Rank": index,
            "Club": club["name"],
            "Income": club.get("income", 0),
        }
        for index, club in enumerate(
            sorted_clubs,
            start=1,
        )
    ]


def build_medal_rows(
    clubs: list[dict],
) -> list[dict]:
    def has_medal(club: dict) -> bool:
        return (
            club.get("gold", 0)
            + club.get("silver", 0)
            + club.get("bronze", 0)
            > 0
        )

    regular_clubs = [
        club
        for club in clubs
        if (
            not is_no_club(club)
            and has_medal(club)
        )
    ]

    no_club = [
        club
        for club in clubs
        if (
            is_no_club(club)
            and has_medal(club)
        )
    ]

    regular_clubs.sort(
        key=lambda club: (
            -club.get("gold", 0),
            -club.get("silver", 0),
            -club.get("bronze", 0),
            club.get("name", "").lower(),
        )
    )

    sorted_clubs = regular_clubs + no_club

    return [
        {
            "Rank": index,
            "Club": club["name"],
            "Gold": club.get("gold", 0),
            "Silver": club.get("silver", 0),
            "Bronze": club.get("bronze", 0),
            "Total": (
                club.get("gold", 0)
                + club.get("silver", 0)
                + club.get("bronze", 0)
            ),
        }
        for index, club in enumerate(
            sorted_clubs,
            start=1,
        )
    ]


def render_inc_viewer():
    countries = build_inc_viewer_data()

    if not countries:
        return

    st.markdown("### Viewer")

    country_ids = sorted(
        countries,
        key=lambda country_id: (
            countries[country_id][
                "name"
            ].lower()
        ),
    )

    selected_country_id = st.selectbox(
        "Nation",
        options=country_ids,
        format_func=lambda country_id: (
            countries[country_id]["name"]
        ),
        key="inc_viewer_country",
    )

    country_data = countries[
        selected_country_id
    ]

    seasons = sorted(
        country_data["competitions"],
        key=int,
        reverse=True,
    )

    selected_season = st.selectbox(
        "Season",
        options=seasons,
        key="inc_viewer_season",
    )

    view_type = st.radio(
        "View",
        options=(
            "Income",
            "Medals",
        ),
        horizontal=True,
        key="inc_viewer_type",
    )

    competition_data = (
        country_data["competitions"][
            selected_season
        ]
    )

    clubs = competition_data["clubs"]

    if view_type == "Income":
        rows = build_income_rows(clubs)

        st.dataframe(
            rows,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Rank": st.column_config.NumberColumn(
                    "Rank",
                    format="%d",
                ),
                "Income": (
                    st.column_config.NumberColumn(
                        "Income",
                        format="%d",
                    )
                ),
            },
        )

    else:
        rows = build_medal_rows(clubs)

        st.dataframe(
            rows,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Rank": st.column_config.NumberColumn(
                    "Rank",
                    format="%d",
                ),
                "Gold": st.column_config.NumberColumn(
                    "Gold",
                    format="%d",
                ),
                "Silver": (
                    st.column_config.NumberColumn(
                        "Silver",
                        format="%d",
                    )
                ),
                "Bronze": (
                    st.column_config.NumberColumn(
                        "Bronze",
                        format="%d",
                    )
                ),
                "Total": (
                    st.column_config.NumberColumn(
                        "Total",
                        format="%d",
                    )
                ),
            },
        )


def render_inc_competition_ids_tool():
    if st.button(
        "Get INC competition data"
    ):
        placeholder = st.empty()

        def update_progress(
            current,
            total,
            country_id,
            country_name,
        ):
            placeholder.button(
                (
                    f"Processing "
                    f"{country_name} "
                    f"({current}/{total})"
                ),
                disabled=True,
                use_container_width=True,
            )

        try:
            (
                outputs,
                timings,
                country_count,
                competition_count,
                latest_season,
            ) = get_inc_competitions_json(
                st.session_state.session,
                progress_callback=(
                    update_progress
                ),
            )

            placeholder.empty()

            st.session_state.inc_outputs = (
                outputs
            )
            st.session_state.inc_timings = (
                timings
            )
            st.session_state.inc_country_count = (
                country_count
            )
            st.session_state[
                "inc_competition_count"
            ] = competition_count
            st.session_state.inc_latest_season = (
                latest_season
            )

        except Exception as e:
            placeholder.empty()

            st.session_state.inc_outputs = None
            st.session_state.inc_timings = None
            st.session_state.inc_country_count = None
            st.session_state[
                "inc_competition_count"
            ] = None
            st.session_state.inc_latest_season = None

            st.error(str(e))

    if st.session_state.inc_outputs is None:
        return

    for timing in st.session_state.inc_timings:
        st.write(
            (
                f"{timing['country_name']} "
                f"season "
                f"{st.session_state.inc_latest_season}: "
                f"{timing['elapsed_seconds']:.2f}s"
            )
        )

    st.write(
        (
            f"Found "
            f"{st.session_state.inc_competition_count} "
            f"INC competitions across "
            f"{st.session_state.inc_country_count} "
            f"countries. Latest season: "
            f"{st.session_state.inc_latest_season}."
        )
    )

    for output in st.session_state.inc_outputs:
        st.download_button(
            label=(
                f"Download "
                f"{output['country_name']} JSON"
            ),
            data=output["json_data"],
            file_name=output["file_name"],
            mime="application/json",
            key=(
                f"download_inc_"
                f"{output['country_id']}"
            ),
        )

    render_inc_viewer()


# -------------------------
# tools page
# -------------------------

st.markdown(
    (
        f"### You are signed in as "
        f"**{st.session_state.username}**"
    )
)

if st.button("Logout"):
    sess = st.session_state.session

    if sess is not None:
        sess.get(
            url.LOGOUT_URL,
            timeout=5,
        )

    st.success(
        "Logout successful!"
    )

    time.sleep(2)

    st.session_state.session = None
    st.session_state.username = None
    st.session_state.user_id = None
    st.session_state.csv_data = None
    st.session_state.comp_income_csv_data = None
    st.session_state.comp_income_name = None
    st.session_state.inc_outputs = None
    st.session_state.inc_timings = None
    st.session_state.inc_country_count = None
    st.session_state.inc_competition_count = None
    st.session_state.inc_latest_season = None

    st.rerun()


tool_col1, tool_col2, tool_col3 = st.columns(
    3
)

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


st.markdown(
    f"## {st.session_state.active_tool}"
)

if (
    st.session_state.active_tool
    == "Athlete CSV"
):
    render_athlete_csv_tool()

elif (
    st.session_state.active_tool
    == "Official Competition Income"
):
    render_official_comp_income_tool()

elif (
    st.session_state.active_tool
    == "INC Competition IDs"
):
    render_inc_competition_ids_tool()
