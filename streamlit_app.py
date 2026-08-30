import html
import time

import requests
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
from tools.inc_history_tool import (
    aggregate_medals,
    get_available_seasons,
    get_country_options,
    load_inc_history,
)


# -------------------------
# session state
# -------------------------

if "session" not in st.session_state:
    st.session_state.session = None

if "public_session" not in st.session_state:
    st.session_state.public_session = None

if "guest_mode" not in st.session_state:
    st.session_state.guest_mode = False

if "username" not in st.session_state:
    st.session_state.username = None

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "csv_data" not in st.session_state:
    st.session_state.csv_data = None

if (
    "comp_income_csv_data"
    not in st.session_state
):
    st.session_state.comp_income_csv_data = (
        None
    )

if (
    "comp_income_name"
    not in st.session_state
):
    st.session_state.comp_income_name = None

if "active_tool" not in st.session_state:
    st.session_state.active_tool = (
        "Official Competition Income"
    )


# -------------------------
# login page
# -------------------------

if (
    st.session_state.session is None
    and not st.session_state.guest_mode
):
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

        submitted = (
            st.form_submit_button(
                "Log in"
            )
        )

    if st.button(
        "Use as guest",
        use_container_width=True,
    ):
        st.session_state.guest_mode = True
        st.session_state.active_tool = (
            "Official Competition Income"
        )

        if (
            st.session_state.public_session
            is None
        ):
            st.session_state.public_session = (
                requests.Session()
            )

        st.rerun()

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
            st.session_state.guest_mode = False
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
            st.session_state[
                "comp_income_csv_data"
            ] = None
            st.session_state[
                "comp_income_name"
            ] = None

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


def get_public_request_session():
    if st.session_state.session is not None:
        return st.session_state.session

    if st.session_state.public_session is None:
        st.session_state.public_session = (
            requests.Session()
        )

    return st.session_state.public_session


def select_athlete_csv():
    st.session_state.active_tool = (
        "Athlete CSV"
    )

    st.session_state.comp_income_csv_data = (
        None
    )

    st.session_state.comp_income_name = None


def select_official_comp_income():
    st.session_state.active_tool = (
        "Official Competition Income"
    )

    st.session_state.csv_data = None


def select_inc_medals():
    st.session_state.active_tool = (
        "INC Medal Counts"
    )

    st.session_state.csv_data = None

    st.session_state.comp_income_csv_data = (
        None
    )

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

        submitted = (
            st.form_submit_button(
                "Get income CSV"
            )
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
                    "Processing events",
                    disabled=True,
                    use_container_width=True,
                )

                (
                    csv_data,
                    comp_name,
                ) = get_official_comp_income_csv(
                    get_public_request_session(),
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


def build_medal_rows(
    clubs: list[dict],
) -> list[dict]:
    return [
        {
            "Rank": index,
            "Club": club["name"],
            "Gold": club.get(
                "gold",
                0,
            ),
            "Silver": club.get(
                "silver",
                0,
            ),
            "Bronze": club.get(
                "bronze",
                0,
            ),
            "Total": (
                club.get(
                    "gold",
                    0,
                )
                + club.get(
                    "silver",
                    0,
                )
                + club.get(
                    "bronze",
                    0,
                )
            ),
        }
        for index, club in enumerate(
            clubs,
            start=1,
        )
    ]


def render_medal_table(
    rows: list[dict],
):
    table_rows = []

    for row in rows:
        club_name = html.escape(
            str(row["Club"])
        )

        table_rows.append(
            (
                "<tr>"
                f"<td>{row['Rank']}</td>"
                f"<td>{club_name}</td>"
                f"<td>{row['Gold']}</td>"
                f"<td>{row['Silver']}</td>"
                f"<td>{row['Bronze']}</td>"
                f"<td>{row['Total']}</td>"
                "</tr>"
            )
        )

    table_html = (
        """
<style>
.inc-medal-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}

.inc-medal-table th,
.inc-medal-table td {
    padding: 8px 10px;
    border-bottom: 1px solid rgba(128, 128, 128, 0.25);
}

.inc-medal-table th {
    text-align: left;
    font-weight: 600;
}

.inc-medal-table th:nth-child(1),
.inc-medal-table td:nth-child(1),
.inc-medal-table th:nth-child(3),
.inc-medal-table td:nth-child(3),
.inc-medal-table th:nth-child(4),
.inc-medal-table td:nth-child(4),
.inc-medal-table th:nth-child(5),
.inc-medal-table td:nth-child(5),
.inc-medal-table th:nth-child(6),
.inc-medal-table td:nth-child(6) {
    text-align: right;
}

.inc-medal-table tbody tr:hover {
    background: rgba(128, 128, 128, 0.08);
}
</style>

<table class="inc-medal-table">
<thead>
<tr>
<th>Rank</th>
<th>Club</th>
<th>Gold</th>
<th>Silver</th>
<th>Bronze</th>
<th>Total</th>
</tr>
</thead>
<tbody>
"""
        + "".join(table_rows)
        + """
</tbody>
</table>
"""
    )

    st.markdown(
        table_html,
        unsafe_allow_html=True,
    )


def render_inc_medals_tool():
    try:
        history = load_inc_history()
    except (
        FileNotFoundError,
        ValueError,
    ) as exc:
        st.error(str(exc))
        return

    countries = history["countries"]

    country_ids = (
        get_country_options(
            history
        )
    )

    all_option = "__all__"

    selected_country = st.selectbox(
        "Nation",
        options=[
            all_option,
            *country_ids,
        ],
        format_func=lambda value: (
            "All nations"
            if value == all_option
            else countries[value]["name"]
        ),
        key="inc_medals_country",
    )

    country_id = (
        None
        if selected_country == all_option
        else selected_country
    )

    available_seasons = (
        get_available_seasons(
            history,
            country_id,
        )
    )

    if not available_seasons:
        st.warning(
            "No seasons are available."
        )
        return

    season_col1, season_col2 = (
        st.columns(2)
    )

    with season_col1:
        from_season = st.selectbox(
            "From season",
            options=available_seasons,
            index=0,
            key="inc_medals_from_season",
        )

    with season_col2:
        to_season = st.selectbox(
            "To season",
            options=available_seasons,
            index=0,
            key="inc_medals_to_season",
        )

    clubs = aggregate_medals(
        history,
        country_id,
        from_season,
        to_season,
    )

    if not clubs:
        st.info(
            "No medal results are available for that selection."
        )
        return

    rows = build_medal_rows(
        clubs
    )

    render_medal_table(
        rows
    )


# -------------------------
# tools page
# -------------------------

is_authenticated = (
    st.session_state.session is not None
)

if is_authenticated:
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
        st.session_state.guest_mode = False
        st.session_state.username = None
        st.session_state.user_id = None
        st.session_state.csv_data = None
        st.session_state.comp_income_csv_data = (
            None
        )
        st.session_state.comp_income_name = None
        st.session_state.active_tool = (
            "Official Competition Income"
        )

        st.rerun()

else:
    st.markdown(
        "### Guest"
    )

    if st.button("Sign in"):
        st.session_state.guest_mode = False
        st.session_state.active_tool = (
            "Official Competition Income"
        )
        st.rerun()


if (
    not is_authenticated
    and st.session_state.active_tool
    == "Athlete CSV"
):
    st.session_state.active_tool = (
        "Official Competition Income"
    )


if is_authenticated:
    (
        tool_col1,
        tool_col2,
        tool_col3,
    ) = st.columns(3)

    with tool_col1:
        st.button(
            "Athlete CSV",
            on_click=select_athlete_csv,
        )

    with tool_col2:
        st.button(
            "Official Competition Income",
            on_click=(
                select_official_comp_income
            ),
        )

    with tool_col3:
        st.button(
            "INC Medal Counts",
            on_click=select_inc_medals,
        )

else:
    tool_col1, tool_col2 = (
        st.columns(2)
    )

    with tool_col1:
        st.button(
            "Official Competition Income",
            on_click=(
                select_official_comp_income
            ),
        )

    with tool_col2:
        st.button(
            "INC Medal Counts",
            on_click=select_inc_medals,
        )


st.markdown(
    f"## {st.session_state.active_tool}"
)

if (
    st.session_state.active_tool
    == "Athlete CSV"
    and is_authenticated
):
    render_athlete_csv_tool()

elif (
    st.session_state.active_tool
    == "Official Competition Income"
):
    render_official_comp_income_tool()

elif (
    st.session_state.active_tool
    == "INC Medal Counts"
):
    render_inc_medals_tool()
