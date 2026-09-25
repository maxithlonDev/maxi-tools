import csv
import time
from pathlib import Path

import streamlit as st

from tools.world_record_club_tool import (
    CLUB_CSV_PATH,
    crawl_wr_clubs,
)


ROOT_DIR = Path(__file__).resolve().parent.parent

NATION_CSV_PATHS = (
    ROOT_DIR
    / "data"
    / "world_records_by_nation_season_20_plus.csv",
    ROOT_DIR
    / "Data"
    / "world_records_by_nation_season_20_plus.csv",
)

VIEW_NATION = "Nation"
VIEW_CONTINENT = "Continent"
VIEW_CLUB = "Club"


MAXITHLON_CONTINENTS = {
    "Am": {
        "Argentina",
        "Bahamas",
        "Barbados",
        "Brasil",
        "Canada",
        "Chile",
        "Colombia",
        "Costa Rica",
        "Ecuador",
        "El Salvador",
        "Jamaica",
        "México",
        "Perú",
        "United States",
        "Uruguay",
        "Venezuela",
    },
    "Eu": {
        "Belarus",
        "België",
        "Bosna i Hercegovina",
        "Bulgaria",
        "Česká republika",
        "Cyprus",
        "Danmark",
        "Deutschland",
        "Eesti",
        "España",
        "France",
        "FYR Makedonija",
        "Great Britain",
        "Hellas",
        "Hrvatska",
        "Ireland",
        "Ísland",
        "Italia",
        "Latvija",
        "Lëtzebuerg",
        "Lietuva",
        "Magyarország",
        "Malta",
        "Nederland",
        "Norge",
        "Österreich",
        "Polska",
        "Portugal",
        "România",
        "Rossiya",
        "Slovenija",
        "Slovensko",
        "Srbija",
        "Suomi",
        "Sverige",
        "Switzerland",
        "Türkiye",
        "Ukrajina",
        "Yisra'el",
    },
    "As": {
        "Al-Jazā'ir",
        "Al-Maghrib",
        "Australia",
        "China",
        "India",
        "Indonesia",
        "Malaysia",
        "Miṣr",
        "New Zealand",
        "Nigeria",
        "Nippon",
        "Pilipinas",
        "Singapore",
        "South Africa",
    },
}


def find_nation_csv_path() -> Path:
    for path in NATION_CSV_PATHS:
        if path.is_file():
            return path

    raise FileNotFoundError(
        (
            "Could not find "
            "world_records_by_nation_season_20_plus.csv "
            "in data/ or Data/."
        )
    )


def load_nation_rows() -> list[dict]:
    path = find_nation_csv_path()

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file
        )

        rows = []

        for row in reader:
            try:
                rank = int(
                    row["Rank"]
                )
                records = int(
                    row["WRs"]
                )
            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

            rows.append(
                {
                    "Rank": rank,
                    "Nation": row.get(
                        "Nation",
                        "",
                    ),
                    "WRs": records,
                }
            )

    return rows


def load_club_rows() -> list[dict]:
    if not CLUB_CSV_PATH.is_file():
        return []

    with CLUB_CSV_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file
        )

        rows = []

        for row in reader:
            try:
                records = int(
                    row["WRs"]
                )
            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

            rank_text = (
                row.get(
                    "Rank",
                    "",
                )
                or ""
            ).strip()

            rank = (
                int(rank_text)
                if rank_text.isdigit()
                else None
            )

            rows.append(
                {
                    "Rank": rank,
                    "Club": (
                        row.get(
                            "Club",
                            "",
                        )
                        or ""
                    ),
                    "WRs": records,
                }
            )

    return rows


def get_maxithlon_continent(
    nation: str,
) -> str | None:
    for (
        continent,
        nations,
    ) in MAXITHLON_CONTINENTS.items():
        if nation in nations:
            return continent

    return None


def build_continent_rows(
    nation_rows: list[dict],
) -> list[dict]:
    counts = {
        "Eu": 0,
        "Am": 0,
        "As": 0,
    }

    for row in nation_rows:
        continent = (
            get_maxithlon_continent(
                row["Nation"]
            )
        )

        if continent is None:
            continue

        counts[
            continent
        ] += row["WRs"]

    sorted_counts = sorted(
        counts.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )

    return [
        {
            "Rank": rank,
            "Continent": continent,
            "WRs": records,
        }
        for rank, (
            continent,
            records,
        ) in enumerate(
            sorted_counts,
            start=1,
        )
    ]


def format_duration(
    seconds: float,
) -> str:
    if seconds < 60:
        return (
            f"{seconds:.1f}s"
        )

    minutes = int(
        seconds // 60
    )

    remaining = int(
        seconds % 60
    )

    return (
        f"{minutes}m "
        f"{remaining}s"
    )


def format_progress(
    status: dict,
    elapsed_seconds: float,
) -> str:
    page_current = status[
        "page_current"
    ]
    page_total = status[
        "page_total"
    ]

    if (
        elapsed_seconds > 0
        and page_current > 0
    ):
        pages_per_second = (
            page_current
            / elapsed_seconds
        )
    else:
        pages_per_second = 0.0

    remaining_pages = max(
        0,
        page_total - page_current,
    )

    if pages_per_second > 0:
        remaining_seconds = (
            remaining_pages
            / pages_per_second
        )
    else:
        remaining_seconds = 0

    if status["phase"] == "history":
        work = (
            f"Event "
            f"{status['event_current']}/"
            f"{status['event_total']}"
            f" · "
            f"{status['event']}"
        )
    else:
        work = (
            f"WR "
            f"{status['record_current']}/"
            f"{status['record_total']}"
            f" · "
            f"{status['event']}"
        )

    return (
        f"{work}"
        f" · "
        f"{page_current}/{page_total} pages"
        f" · "
        f"{pages_per_second:.2f} pages/s"
        f" · "
        f"Elapsed "
        f"{format_duration(elapsed_seconds)}"
        f" · "
        f"ETA ~"
        f"{format_duration(remaining_seconds)}"
    )


def render_nation_table(
    rows: list[dict],
):
    st.dataframe(
        rows,
        hide_index=True,
        use_container_width=True,
        height=900,
        column_config={
            "Rank": (
                st.column_config
                .NumberColumn(
                    "Rank",
                    format="%d",
                    width="small",
                )
            ),
            "Nation": (
                st.column_config
                .TextColumn(
                    "Nation",
                    width="large",
                )
            ),
            "WRs": (
                st.column_config
                .NumberColumn(
                    "WRs",
                    format="%d",
                    width="small",
                )
            ),
        },
    )


def render_continent_table(
    rows: list[dict],
):
    st.dataframe(
        rows,
        hide_index=True,
        use_container_width=True,
        height=220,
        column_config={
            "Rank": (
                st.column_config
                .NumberColumn(
                    "Rank",
                    format="%d",
                    width="small",
                )
            ),
            "Continent": (
                st.column_config
                .TextColumn(
                    "Continent",
                    width="large",
                )
            ),
            "WRs": (
                st.column_config
                .NumberColumn(
                    "WRs",
                    format="%d",
                    width="small",
                )
            ),
        },
    )


def render_club_table(
    rows: list[dict],
):
    st.dataframe(
        rows,
        hide_index=True,
        use_container_width=True,
        height=900,
        column_config={
            "Rank": (
                st.column_config
                .NumberColumn(
                    "Rank",
                    format="%d",
                    width="small",
                )
            ),
            "Club": (
                st.column_config
                .TextColumn(
                    "Club",
                    width="large",
                )
            ),
            "WRs": (
                st.column_config
                .NumberColumn(
                    "WRs",
                    format="%d",
                    width="small",
                )
            ),
        },
    )


def recompute_club_csv():
    progress = st.empty()
    start_time = (
        time.perf_counter()
    )

    def update_progress(
        status: dict,
    ):
        elapsed_seconds = (
            time.perf_counter()
            - start_time
        )

        progress.info(
            format_progress(
                status,
                elapsed_seconds,
            )
        )

    try:
        result = crawl_wr_clubs(
            st.session_state.session,
            progress_callback=(
                update_progress
            ),
        )

        elapsed_seconds = (
            time.perf_counter()
            - start_time
        )

        pages_per_second = (
            result["page_count"]
            / elapsed_seconds
            if elapsed_seconds > 0
            else 0.0
        )

        progress.success(
            (
                f"Saved club CSV"
                f" · "
                f"{result['record_count']} WRs"
                f" · "
                f"{result['page_count']} pages"
                f" · "
                f"{pages_per_second:.2f} pages/s"
                f" · "
                f"{format_duration(elapsed_seconds)}"
            )
        )

        st.session_state[
            "wr_club_last_errors"
        ] = result[
            "errors"
        ]

    except Exception as exc:
        progress.empty()

        st.error(
            str(exc)
        )


@st.fragment
def render_world_record_nation_tool():
    try:
        nation_rows = (
            load_nation_rows()
        )
    except (
        FileNotFoundError,
        OSError,
    ) as exc:
        st.error(
            str(exc)
        )
        return

    if not nation_rows:
        st.warning(
            "The WR by Nation CSV contains no rows."
        )
        return

    total_records = sum(
        row["WRs"]
        for row in nation_rows
    )

    st.caption(
        (
            f"{total_records} world-record "
            "performances since season 20"
        )
    )

    view = st.radio(
        "Count by",
        options=(
            VIEW_NATION,
            VIEW_CONTINENT,
            VIEW_CLUB,
        ),
        index=0,
        horizontal=True,
        key="wr_count_view",
    )

    if view == VIEW_NATION:
        render_nation_table(
            nation_rows
        )
        return

    if view == VIEW_CONTINENT:
        render_continent_table(
            build_continent_rows(
                nation_rows
            )
        )
        return

    if (
        st.session_state.get(
            "session"
        )
        is not None
    ):
        if st.button(
            "Recompute club WR counts",
            use_container_width=True,
            key="wr_recompute_clubs",
        ):
            recompute_club_csv()

    club_rows = load_club_rows()

    if not club_rows:
        st.info(
            (
                "No saved club WR data yet. "
                "Sign in and run the club "
                "recompute once."
            )
        )
        return

    render_club_table(
        club_rows
    )
