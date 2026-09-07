import csv
import html
import io
import json

import streamlit as st
import streamlit.components.v1 as components

from tools.inc_history_tool import (
    aggregate_medals,
    get_available_seasons,
    get_club_nationality_options,
    get_country_options,
    load_inc_history,
)


def build_medal_rows(clubs: list[dict]) -> list[dict]:
    rows = []

    for rank, club in enumerate(clubs, start=1):
        gold = club.get("gold", 0)
        silver = club.get("silver", 0)
        bronze = club.get("bronze", 0)

        rows.append(
            {
                "Rank": rank,
                "Club": club.get("name", ""),
                "Nation": club.get("nation_code", "") or "",
                "Gold": gold,
                "Silver": silver,
                "Bronze": bronze,
                "Total": gold + silver + bronze,
            }
        )

    return rows


def build_medal_copy_text(rows: list[dict]) -> str:
    columns = (
        "Rank",
        "Club",
        "Nation",
        "Gold",
        "Silver",
        "Bronze",
        "Total",
    )

    lines = ["\t".join(columns)]

    for row in rows:
        lines.append(
            "\t".join(
                str(row[column])
                for column in columns
            )
        )

    return "\n".join(lines)


def build_medal_csv(rows: list[dict]) -> bytes:
    columns = (
        "Rank",
        "Club",
        "Nation",
        "Gold",
        "Silver",
        "Bronze",
        "Total",
    )

    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)

    writer.writerow(columns)

    for row in rows:
        writer.writerow(
            row[column]
            for column in columns
        )

    return buffer.getvalue().encode("utf-8-sig")


def render_copy_all_button(rows: list[dict]):
    copy_text = json.dumps(
        build_medal_copy_text(rows)
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
<button id="copyButton">Copy all</button>

<script>
const copyText = {copy_text};
const button = document.getElementById("copyButton");

button.addEventListener("click", async () => {{
    try {{
        await navigator.clipboard.writeText(copyText);
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
    }}

    button.textContent = "Copied!";

    setTimeout(() => {{
        button.textContent = "Copy all";
    }}, 1500);
}});
</script>
</body>
</html>
""",
        height=38,
        scrolling=False,
    )


def render_medal_table(rows: list[dict]):
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


def render_medal_output(
    clubs: list[dict],
    country_name: str,
    from_season: int,
    to_season: int,
):
    rows = build_medal_rows(clubs)

    copy_column, csv_column = st.columns(2)

    with copy_column:
        render_copy_all_button(rows)

    with csv_column:
        st.download_button(
            label="Download as CSV",
            data=build_medal_csv(rows),
            file_name=make_medal_csv_filename(
                country_name,
                from_season,
                to_season,
            ),
            mime="text/csv",
            use_container_width=True,
        )

    render_medal_table(rows)


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
    country_ids = get_country_options(
        history
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

    from_column, to_column = st.columns(2)

    with from_column:
        from_season = st.selectbox(
            "From season",
            options=available_seasons,
            index=0,
            key="inc_medals_from_season",
        )

    with to_column:
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

    nationality_options = (
        get_club_nationality_options(
            clubs
        )
    )
    nationality_names = dict(
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
            f"{nationality_names[code]}"
        ),
        key="inc_medals_club_nationality",
    )

    if selected_nation_code is not None:
        clubs = [
            club
            for club in clubs
            if (
                club.get("nation_code")
                == selected_nation_code
            )
        ]

    if not clubs:
        st.info(
            "No medal results are available for that selection."
        )
        return

    render_medal_output(
        clubs,
        country_name,
        from_season,
        to_season,
    )
