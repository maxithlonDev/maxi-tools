import csv
import html
import io
import json
import time

import requests
import streamlit as st
import streamlit.components.v1 as components
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


def is_no_club(
    club: dict,
) -> bool:
    return (
        club.get("club_id") is None
        and club.get("name") == "No Club"
    )


def make_club_key(
    club: dict,
):
    club_id = club.get(
        "club_id"
    )

    if club_id is not None:
        return (
            "id",
            str(club_id),
        )

    return (
        "name",
        club.get(
            "name",
            "",
        ),
    )


def aggregate_medals_with_nationality(
    history: dict,
    country_id,
    first_season: int,
    last_season: int,
) -> list[dict]:
    countries = history.get(
        "countries",
        {},
    )

    minimum_season = min(
        first_season,
        last_season,
    )

    maximum_season = max(
        first_season,
        last_season,
    )

    if country_id is None:
        selected_countries = (
            countries.values()
        )
    else:
        selected_countries = [
            countries.get(
                str(country_id),
                {},
            )
        ]

    aggregated = {}

    for country in selected_countries:
        competitions = country.get(
            "competitions",
            {},
        )

        for (
            season_key,
            competition,
        ) in competitions.items():
            try:
                season = int(
                    season_key
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if not (
                minimum_season
                <= season
                <= maximum_season
            ):
                continue

            for club in competition.get(
                "clubs",
                [],
            ):
                key = make_club_key(
                    club
                )

                if key not in aggregated:
                    aggregated[key] = {
                        "club_id": club.get(
                            "club_id"
                        ),
                        "name": club.get(
                            "name",
                            "",
                        ),
                        "nation_id": club.get(
                            "nation_id"
                        ),
                        "nationality": club.get(
                            "nationality"
                        ),
                        "nation_code": club.get(
                            "nation_code"
                        ),
                        "gold": 0,
                        "silver": 0,
                        "bronze": 0,
                    }
                else:
                    if (
                        aggregated[key].get(
                            "nation_id"
                        )
                        is None
                        and club.get(
                            "nation_id"
                        )
                        is not None
                    ):
                        aggregated[key][
                            "nation_id"
                        ] = club.get(
                            "nation_id"
                        )

                    if (
                        not aggregated[key].get(
                            "nationality"
                        )
                        and club.get(
                            "nationality"
                        )
                    ):
                        aggregated[key][
                            "nationality"
                        ] = club.get(
                            "nationality"
                        )

                    if (
                        not aggregated[key].get(
                            "nation_code"
                        )
                        and club.get(
                            "nation_code"
                        )
                    ):
                        aggregated[key][
                            "nation_code"
                        ] = club.get(
                            "nation_code"
                        )

                aggregated[key]["gold"] += (
                    club.get(
                        "gold",
                        0,
                    )
                )

                aggregated[key]["silver"] += (
                    club.get(
                        "silver",
                        0,
                    )
                )

                aggregated[key]["bronze"] += (
                    club.get(
                        "bronze",
                        0,
                    )
                )

    clubs = [
        club
        for club in aggregated.values()
        if (
            club["gold"]
            or club["silver"]
            or club["bronze"]
        )
    ]

    regular_clubs = [
        club
        for club in clubs
        if not is_no_club(
            club
        )
    ]

    no_club_rows = [
        club
        for club in clubs
        if is_no_club(
            club
        )
    ]

    regular_clubs.sort(
        key=lambda club: (
            -club["gold"],
            -club["silver"],
            -club["bronze"],
            club["name"].casefold(),
            str(
                club.get(
                    "club_id"
                )
                or ""
            ),
        )
    )

    return (
        regular_clubs
        + no_club_rows
    )


def get_club_nationality_options(
    clubs: list[dict],
) -> list[tuple[str, str]]:
    nationalities = {}

    for club in clubs:
        nation_code = club.get(
            "nation_code"
        )

        if not nation_code:
            continue

        nationality = (
            club.get(
                "nationality"
            )
            or nation_code
        )

        nationalities[
            nation_code
        ] = nationality

    return sorted(
        nationalities.items(),
        key=lambda item: (
            item[1].casefold(),
            item[0],
        ),
    )


def build_medal_rows(
    clubs: list[dict],
) -> list[dict]:
    return [
        {
            "Rank": index,
            "Club": club["name"],
            "Nation": club.get(
                "nation_code",
                "",
            )
            or "",
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


def build_medal_copy_text(
    rows: list[dict],
) -> str:
    lines = [
        "\t".join(
            (
                "Rank",
                "Club",
                "Nation",
                "Gold",
                "Silver",
                "Bronze",
                "Total",
            )
        )
    ]

    for row in rows:
        lines.append(
            "\t".join(
                (
                    str(row["Rank"]),
                    str(row["Club"]),
                    str(row["Nation"]),
                    str(row["Gold"]),
                    str(row["Silver"]),
                    str(row["Bronze"]),
                    str(row["Total"]),
                )
            )
        )

    return "\n".join(lines)


def build_medal_csv(
    rows: list[dict],
) -> bytes:
    buffer = io.StringIO(
        newline=""
    )

    writer = csv.writer(buffer)

    writer.writerow(
        (
            "Rank",
            "Club",
            "Nation",
            "Gold",
            "Silver",
            "Bronze",
            "Total",
        )
    )

    for row in rows:
        writer.writerow(
            (
                row["Rank"],
                row["Club"],
                row["Nation"],
                row["Gold"],
                row["Silver"],
                row["Bronze"],
                row["Total"],
            )
        )

    return buffer.getvalue().encode(
        "utf-8-sig"
    )


def render_copy_all_button(
    rows: list[dict],
):
    copy_text = (
        build_medal_copy_text(
            rows
        )
    )

    copy_text_js = json.dumps(
        copy_text
    )

    components.html(
        f"""
<!doctype html>
<html>
<head>
<style>
html,
body {{
    margin: 0;
    padding: 0;
    background: transparent;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}}

button {{
    width: 100%;
    height: 38px;
    border: 1px solid rgba(49, 51, 63, 0.2);
    border-radius: 8px;
    background: transparent;
    color: inherit;
    font-size: 14px;
    cursor: pointer;
}}

button:hover {{
    border-color: rgba(49, 51, 63, 0.4);
}}

button:active {{
    background: rgba(49, 51, 63, 0.05);
}}
</style>
</head>
<body>
<button id="copyButton">
    Copy all
</button>

<script>
const copyText = {copy_text_js};
const button = document.getElementById("copyButton");

button.addEventListener("click", async () => {{
    try {{
        await navigator.clipboard.writeText(copyText);
        button.textContent = "Copied!";
        setTimeout(
            () => {{
                button.textContent = "Copy all";
            }},
            1500
        );
    }} catch (error) {{
        const textarea = document.createElement("textarea");
        textarea.value = copyText;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand("copy");
        textarea.remove();

        button.textContent = "Copied!";
        setTimeout(
            () => {{
                button.textContent = "Copy all";
            }},
            1500
        );
    }}
}});
</script>
</body>
</html>
""",
        height=38,
        scrolling=False,
    )


def render_medal_table(
    rows: list[dict],
):
    table_rows = []

    for row in rows:
        club_name = html.escape(
            str(row["Club"])
        )

        nation = html.escape(
            str(row["Nation"])
        )

        table_rows.append(
            (
                "<tr>"
                f"<td>{row['Rank']}</td>"
                f"<td>{club_name}</td>"
                f"<td>{nation}</td>"
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
.inc-medal-table th:nth-child(4),
.inc-medal-table td:nth-child(4),
.inc-medal-table th:nth-child(5),
.inc-medal-table td:nth-child(5),
.inc-medal-table th:nth-child(6),
.inc-medal-table td:nth-child(6),
.inc-medal-table th:nth-child(7),
.inc-medal-table td:nth-child(7) {
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
<th>Nation</th>
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


def make_medal_csv_filename(
    country_name: str,
    from_season: int,
    to_season: int,
) -> str:
    minimum_season = min(
        from_season,
        to_season,
    )

    maximum_season = max(
        from_season,
        to_season,
    )

    safe_country_name = "".join(
        character
        if (
            character.isalnum()
            or character in (" ", "-", "_")
        )
        else "_"
        for character in country_name
    ).strip()

    if minimum_season == maximum_season:
        return (
            f"INC Medals "
            f"{safe_country_name} "
            f"Season {minimum_season}.csv"
        )

    return (
        f"INC Medals "
        f"{safe_country_name} "
        f"Seasons {minimum_season}-"
        f"{maximum_season}.csv"
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

    country_name = (
        "All Nations"
        if country_id is None
        else countries[country_id]["name"]
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

    clubs = aggregate_medals_with_nationality(
        history,
        country_id,
        from_season,
        to_season,
    )

    nationality_options = (
        get_club_nationality_options(
            clubs
        )
    )

    nationality_by_code = dict(
        nationality_options
    )

    selected_nation_code = st.selectbox(
        "Club nationality",
        options=[
            code
            for code, _
            in nationality_options
        ],
        index=None,
        placeholder="All nationalities",
        format_func=lambda code: (
            f"{code} - "
            f"{nationality_by_code[code]}"
        ),
        key="inc_medals_club_nationality",
    )

    if selected_nation_code is not None:
        clubs = [
            club
            for club in clubs
            if club.get(
                "nation_code"
            )
            == selected_nation_code
        ]

    if not clubs:
        st.info(
            "No medal results are available for that selection."
        )
        return

    rows = build_medal_rows(
        clubs
    )

    action_col1, action_col2 = (
        st.columns(2)
    )

    with action_col1:
        render_copy_all_button(
            rows
        )

    with action_col2:
        st.download_button(
            label="Download as CSV",
            data=build_medal_csv(
                rows
            ),
            file_name=make_medal_csv_filename(
                country_name,
                from_season,
                to_season,
            ),
            mime="text/csv",
            use_container_width=True,
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
